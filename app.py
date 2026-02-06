from flask import Flask, jsonify, render_template_string
import paho.mqtt.client as mqtt

# ======================
# MQTT CONFIG
# ======================
MQTT_BROKER = "maqiatto.com"
MQTT_PORT = 1883
MQTT_USERNAME = "rndxft@gmail.com"
MQTT_PASSWORD = "Testing27"
MQTT_TOPIC = "smartlamp"

client = mqtt.Client(client_id="flask-dashboard")
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

# ======================
# FLASK CONFIG
# ======================
app = Flask(__name__)

state = {
    "led1": False,
    "led2": False
}

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Smart Lamp Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #111;
            color: #fff;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding-top: 40px;
        }
        .card {
            background: #222;
            padding: 20px;
            border-radius: 12px;
            width: 280px;
            margin-bottom: 15px;
            text-align: center;
        }
        button {
            width: 100%;
            padding: 14px;
            font-size: 18px;
            border-radius: 10px;
            border: none;
            cursor: pointer;
        }
        .on {
            background: #4CAF50;
            color: white;
        }
        .off {
            background: #555;
            color: white;
        }
    </style>
</head>
<body>

<h1>Smart Lamp</h1>

<div class="card">
    <h2>Lampu 1</h2>
    <button class="{{ 'on' if led1 else 'off' }}" onclick="toggle(1)">
        {{ 'ON' if led1 else 'OFF' }}
    </button>
</div>

<div class="card">
    <h2>Lampu 2</h2>
    <button class="{{ 'on' if led2 else 'off' }}" onclick="toggle(2)">
        {{ 'ON' if led2 else 'OFF' }}
    </button>
</div>

<script>
function toggle(id){
    fetch('/toggle/' + id, {method:'POST'})
    .then(() => location.reload())
}
</script>

</body>
</html>
"""

# ======================
# ROUTES
# ======================
@app.route("/")
def dashboard():
    return render_template_string(
        HTML,
        led1=state["led1"],
        led2=state["led2"]
    )

@app.route("/toggle/<int:led>", methods=["POST"])
def toggle_led(led):
    if led == 1:
        state["led1"] = not state["led1"]
        payload = "LED1_ON" if state["led1"] else "LED1_OFF"
    elif led == 2:
        state["led2"] = not state["led2"]
        payload = "LED2_ON" if state["led2"] else "LED2_OFF"
    else:
        return jsonify({"error": "invalid led"}), 400

    client.publish(MQTT_TOPIC, payload)
    return jsonify(state)

# ======================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
