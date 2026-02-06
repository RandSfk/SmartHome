from flask import Flask, jsonify

app = Flask(__name__)

state = {
    "led1": True,
    "led2": False
}

@app.route("/status")
def status():
    return jsonify(state)

app.run(host="0.0.0.0", port=5000)
