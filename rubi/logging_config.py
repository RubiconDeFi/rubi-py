import logging
from io import StringIO
import requests

# Create an in-memory stream to store logs
log_stream = StringIO()

# flag to enable API endpoint
api_enabled = True


class APILogHandler(logging.Handler):
    def emit(self, record):
        if api_enabled:
            log_entry = self.format(record)
            # send log to flask
            url = "http://localhost:5000/api/logs"
            requests.post(url, json={"logs": [log_entry]})


# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

api_log_handler = APILogHandler()
api_log_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
api_log_handler.setFormatter(formatter)

logger.addHandler(api_log_handler)

# # Function to retrieve the captured logs
# def get_logs():
#     logs = log_stream.getvalue().strip().split("\n")
#     log_stream.seek(0)
#     log_stream.truncate()
#     return logs
