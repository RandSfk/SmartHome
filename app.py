from flask import Flask, jsonify, request, render_template_string

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
        h1 {
            margin-bottom: 20px;
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
            border: none;
            border-radius: 10px;
            cursor: pointer;
            background: #4CAF50;
            color: white;
        }
        button.off {
            background: #555;
        }
    </style>
</head>
<body>
    <h1>Smart Lamp</h1>

    <div class="card">
        <h2>Lampu 1</h2>
        <button onclick="toggle(1)">
            {{ 'ON' if led1 else 'OFF' }}
        </button>
    </div>

    <div class="card">
        <h2>Lampu 2</h2>
        <button onclick="toggle(2)">
            {{ 'ON' if led2 else 'OFF' }}
        </button>
    </div>

<script>
function toggle(id) {
    fetch('/toggle/' + id, { method: 'POST' })
        .then(() => location.reload());
}
</script>

</body>
</html>
"""

@app.route("/")
def dashboard():
    return render_template_string(
        HTML,
        led1=state["led1"],
        led2=state["led2"]
    )

@app.route("/status")
def status():
    return jsonify(state)

@app.route("/toggle/<int:led>", methods=["POST"])
def toggle_led(led):
    if led == 1:
        state["led1"] = not state["led1"]
    elif led == 2:
        state["led2"] = not state["led2"]
    return jsonify(state)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
