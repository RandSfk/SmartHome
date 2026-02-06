from flask import Flask, jsonify, render_template_string, request
import paho.mqtt.client as mqtt
import json
import threading
import time

# ======================
# CONFIG
# ======================
MQTT_BROKER = "maqiatto.com"
MQTT_PORT = 1883
MQTT_USERNAME = "rndxft@gmail.com"
MQTT_PASSWORD = "Testing27"

# Topics: follow MaQiaTTo requirement (username prefix)
BASE_TOPIC = "rndxft@gmail.com/smartlamp"
CMD_TOPIC = f"{BASE_TOPIC}/cmd"       # publish commands here
STATUS_TOPIC = f"{BASE_TOPIC}/status" # device publishes status here (retain)

MQTT_CLIENT_ID = "flask-dashboard-1"

# ======================
# FLASK + STATE
# ======================
app = Flask(__name__)

state = {
    "led1": False,
    "led2": False
}
state_lock = threading.Lock()

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Smart Lamp Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial, sans-serif; background:#111; color:#fff; display:flex; flex-direction:column; align-items:center; padding-top:40px; }
        h1 { margin-bottom: 20px; }
        .card { background:#222; padding:20px; border-radius:12px; width:320px; margin-bottom:12px; text-align:center; }
        button { width:100%; padding:14px; font-size:18px; border-radius:10px; border:none; cursor:pointer; }
        .on { background:#4CAF50; color:white; }
        .off { background:#555; color:white; }
        .row { display:flex; gap:8px; }
        .small { padding:8px; font-size:14px; }
    </style>
</head>
<body>
    <h1>Smart Lamp (MQTT Remote)</h1>

    <div class="card">
        <h2>Lampu 1</h2>
        <div class="row">
            <button class="small on" onclick="setOne(1,true)">ON</button>
            <button class="small off" onclick="setOne(1,false)">OFF</button>
            <button class="{{ 'on' if led1 else 'off' }}" style="flex:1" onclick="toggle(1)">{{ 'ON' if led1 else 'OFF' }}</button>
        </div>
    </div>

    <div class="card">
        <h2>Lampu 2</h2>
        <div class="row">
            <button class="small on" onclick="setOne(2,true)">ON</button>
            <button class="small off" onclick="setOne(2,false)">OFF</button>
            <button class="{{ 'on' if led2 else 'off' }}" style="flex:1" onclick="toggle(2)">{{ 'ON' if led2 else 'OFF' }}</button>
        </div>
    </div>

    <div class="card">
        <h2>All</h2>
        <div class="row">
            <button class="small on" onclick="setAll(true)">ALL ON</button>
            <button class="small off" onclick="setAll(false)">ALL OFF</button>
            <button class="small off" onclick="refresh()">REFRESH</button>
        </div>
        <p id="statusline"></p>
    </div>

<script>
function toggle(id){
    fetch('/toggle/' + id, {method:'POST'})
        .then(r => r.json()).then(updateUI);
}
function setOne(id, val){
    fetch('/set', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify(id===1?{led1:val}:{led2:val})
    }).then(r => r.json()).then(updateUI);
}
function setAll(val){
    fetch('/set', {
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({led1:val, led2:val})
    }).then(r => r.json()).then(updateUI);
}
function refresh(){
    fetch('/status').then(r=>r.json()).then(updateUI);
}
function updateUI(data){
    document.getElementById('statusline').innerText = 'Status: ' + JSON.stringify(data);
    setTimeout(()=>location.reload(), 300); // small refresh to update buttons
}
</script>
</body>
</html>
"""

# ======================
# MQTT CLIENT SETUP
# ======================
client = mqtt.Client(client_id=MQTT_CLIENT_ID, clean_session=True)
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

def on_connect(clientc, userdata, flags, rc):
    print("MQTT connected with rc:", rc)
    # subscribe to status topic so we can reflect real device state in UI
    clientc.subscribe(STATUS_TOPIC, qos=1)
    # request retained state by publishing nothing (not necessary) —
    # device should have retained last status on STATUS_TOPIC

def on_message(clientc, userdata, msg):
    try:
        payload = msg.payload.decode('utf-8')
        print("MQTT message", msg.topic, payload)
        data = json.loads(payload)
        with state_lock:
            # update only keys present
            if isinstance(data, dict):
                if 'led1' in data:
                    state['led1'] = bool(data['led1'])
                if 'led2' in data:
                    state['led2'] = bool(data['led2'])
    except Exception as e:
        print("Failed to parse status payload:", e)

client.on_connect = on_connect
client.on_message = on_message

def mqtt_background_connect_loop():
    while True:
        try:
            if not client.is_connected():
                print("Attempting MQTT connect...")
                client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
                client.loop_start()
            # stay here and sleep; if connection lost, loop continues and tries again
        except Exception as e:
            print("MQTT connect error:", e)
        time.sleep(5)

# start background thread for mqtt connect/reconnect
t = threading.Thread(target=mqtt_background_connect_loop, daemon=True)
t.start()

# ======================
# FLASK ROUTES
# ======================
@app.route("/")
def dashboard():
    with state_lock:
        return render_template_string(HTML, led1=state["led1"], led2=state["led2"])

@app.route("/status", methods=["GET"])
def get_status():
    with state_lock:
        return jsonify(state)

@app.route("/toggle/<int:led>", methods=["POST"])
def toggle_led(led):
    with state_lock:
        if led == 1:
            new = not state["led1"]
            state["led1"] = new
            payload = json.dumps({"led1": new})
        elif led == 2:
            new = not state["led2"]
            state["led2"] = new
            payload = json.dumps({"led2": new})
        else:
            return jsonify({"error": "invalid led"}), 400

    # publish command (QoS=1)
    try:
        client.publish(CMD_TOPIC, payload, qos=1, retain=False)
    except Exception as e:
        print("Publish error:", e)

    # optimistic update: also publish status for retain so device/logging sees current desired state
    try:
        with state_lock:
            s = json.dumps(state)
        client.publish(STATUS_TOPIC, s, qos=1, retain=True)
    except Exception as e:
        print("Status publish error:", e)

    return jsonify(state)

@app.route("/set", methods=["POST"])
def set_route():
    try:
        body = request.get_json(force=True)
    except Exception:
        return jsonify({"error": "invalid json"}), 400

    changed = {}
    with state_lock:
        if "led1" in body:
            state["led1"] = bool(body["led1"])
            changed["led1"] = state["led1"]
        if "led2" in body:
            state["led2"] = bool(body["led2"])
            changed["led2"] = state["led2"]

    if not changed:
        return jsonify({"error": "no led in payload"}), 400

    payload = json.dumps(changed)
    try:
        client.publish(CMD_TOPIC, payload, qos=1, retain=False)
    except Exception as e:
        print("Publish error:", e)

    # publish retained status
    try:
        with state_lock:
            s = json.dumps(state)
        client.publish(STATUS_TOPIC, s, qos=1, retain=True)
    except Exception as e:
        print("Status publish error:", e)

    return jsonify(state)

# ======================
# RUN
# ======================
if __name__ == "__main__":
    # small delay so background thread can attempt initial connect before serving
    time.sleep(1)
    app.run(host="0.0.0.0", port=5000, debug=True)
