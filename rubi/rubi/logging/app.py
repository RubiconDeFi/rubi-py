from flask import Flask, render_template, jsonify, request
import logging_config

app = Flask(__name__)

app.config["DEBUG"] = True
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

# in memory list to store logs instead of file
logs = []


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/logs", methods=["GET"])
def get_logs():
    return jsonify(logs)


@app.route("/api/logs", methods=["POST"])
def receive_logs():
    new_logs = request.json.get("logs")
    if new_logs:
        logs.extend(new_logs)
    return "Logs received"


if __name__ == "__main__":
    app.run(debug=True)
