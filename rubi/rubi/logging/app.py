from flask import Flask, render_template
import logging
from io import StringIO

app = Flask(__name__)

# Create an in-memory stream to store logs
log_stream = StringIO()

# Configure logging to use the in-memory stream
log_handler = logging.StreamHandler(log_stream)
log_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log_handler.setFormatter(formatter)

# Create a logger for the Flask application and add the log handler
logger = app.logger
logger.addHandler(log_handler)


@app.route("/")
def index():
    # Get the logs from the in-memory stream
    logs = log_stream.getvalue().strip().split("\n")

    return render_template("index.html", logs=logs)


if __name__ == "__main__":
    app.run()
