# app.py
from flask import Flask, request, jsonify, render_template_string
import paho.mqtt.client as mqtt
import json
import time
import threading

# ====== CONFIG (ganti kalau perlu) ======
WIFI_SSID = "Wokwi-GUEST"   # (hanya info, Flask ga butuh)
MQTT_BROKER = "maqiatto.com"
MQTT_PORT = 1883
MQTT_USERNAME = "rndxft@gmail.com"
MQTT_PASSWORD = "Testing27"
MQTT_CLIENT_ID = "flask-controller-rndxft-01"
MQTT_TOPIC = "rndxft@gmail.com/smartlamp"
# ========================================

app = Flask(__name__)

# current server-known state (dipakai untuk UI)
state = {"led1": False, "led2": False}

# ---- MQTT client setup ----
mqtt_client = mqtt.Client(client_id=MQTT_CLIENT_ID)


def on_connect(client, userdata, flags, rc):
    print("MQTT connected, rc=", rc)
    # optional: subscribe untuk menerima updates (ESP bisa publish status back)
    client.subscribe(MQTT_TOPIC)


def on_message(client, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        print("MQTT <=", payload)
        data = json.loads(payload)
        # update local state if payload contains led keys
        if isinstance(data, dict):
            if 'led1' in data:
                state['led1'] = bool(data['led1'])
            if 'led2' in data:
                state['led2'] = bool(data['led2'])
    except Exception as e:
        print("Error parsing message:", e)


mqtt_client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message

def mqtt_connect_loop():
    while True:
        try:
            mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
            mqtt_client.loop_start()
            break
        except Exception as e:
            print("MQTT connect failed:", e)
            time.sleep(3)

# Start MQTT connection in background thread so Flask startup is smooth
threading.Thread(target=mqtt_connect_loop, daemon=True).start()

# ---- Helper to publish state ----
def publish_state(payload_dict):
    payload = json.dumps(payload_dict)
    # publish retained so ESP32 receives last known state when it connects
    result = mqtt_client.publish(MQTT_TOPIC, payload, qos=1, retain=True)
    # optional: wait for result
    result.wait_for_publish()
    print("MQTT =>", payload)
    # update local copy
    if 'led1' in payload_dict:
        state['led1'] = bool(payload_dict['led1'])
    if 'led2' in payload_dict:
        state['led2'] = bool(payload_dict['led2'])
    return result.rc == mqtt.MQTT_ERR_SUCCESS

# ---- Flask endpoints ----

# Simple UI
INDEX_HTML = """
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>SmartLamp Controller</title>
    <style>
      body { font-family: system-ui, sans-serif; padding: 30px; }
      .card { display:inline-block; padding:20px; border-radius:8px; box-shadow:0 4px 10px rgba(0,0,0,0.08); margin:10px; }
      button{ padding:10px 14px; margin:6px; cursor:pointer; }
      .on { background: #2ecc71; color: white; border: none; }
      .off { background: #e74c3c; color:white; border:none; }
    </style>
  </head>
  <body>
    <h1>SmartLamp Controller</h1>
    <div id="status">Connecting...</div>

    <div class="card">
      <h3>LED 1</h3>
      <button onclick="setLed('led1', true)" class="on">ON</button>
      <button onclick="setLed('led1', false)" class="off">OFF</button>
      <div>State: <span id="led1_state">-</span></div>
    </div>

    <div class="card">
      <h3>LED 2</h3>
      <button onclick="setLed('led2', true)" class="on">ON</button>
      <button onclick="setLed('led2', false)" class="off">OFF</button>
      <div>State: <span id="led2_state">-</span></div>
    </div>

    <script>
      async function fetchState(){
        try{
          const r = await fetch('/api/state');
          const j = await r.json();
          document.getElementById('led1_state').innerText = j.led1;
          document.getElementById('led2_state').innerText = j.led2;
          document.getElementById('status').innerText = 'Connected to controller';
        }catch(e){
          document.getElementById('status').innerText = 'Failed to contact controller';
        }
      }

      async function setLed(led, value){
        const body = {};
        body[led] = value;
        await fetch('/api/state', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(body)
        });
        await fetchState();
      }

      // poll state every 2s
      fetchState();
      setInterval(fetchState, 2000);
    </script>
  </body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

# Get current known state
@app.route("/api/state", methods=["GET"])
def api_get_state():
    return jsonify(state)

# Set state for one or both leds using JSON body
# Example bodies:
# {"led1": true} or {"led2": false} or {"led1": true, "led2": false}
@app.route("/api/state", methods=["POST"])
def api_set_state():
    try:
        data = request.get_json(force=True)
        if not isinstance(data, dict):
            return jsonify({"ok": False, "error": "JSON object expected"}), 400

        payload = {}
        if 'led1' in data:
            payload['led1'] = bool(data['led1'])
        if 'led2' in data:
            payload['led2'] = bool(data['led2'])

        if not payload:
            return jsonify({"ok": False, "error": "No led1/led2 keys found"}), 400

        ok = publish_state(payload)
        if ok:
            return jsonify({"ok": True, "published": payload})
        else:
            return jsonify({"ok": False, "error": "MQTT publish failed"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# Convenience route to toggle single led using path (optional)
@app.route("/api/led/<led_name>/<action>", methods=["POST"])
def api_led_action(led_name, action):
    if led_name not in ("led1", "led2"):
        return jsonify({"ok": False, "error": "led must be led1 or led2"}), 400
    val = action.lower() in ("on", "1", "true", "t")
    ok = publish_state({led_name: val})
    return jsonify({"ok": ok, "led": led_name, "state": val})

if __name__ == "__main__":
    print("Starting Flask MQTT controller...")
    app.run(host="0.0.0.0", port=5000, debug=True)
