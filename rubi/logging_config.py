import logging
from io import StringIO
import requests
import sys
from dotenv import load_dotenv
import os

# get url path if supplied
load_dotenv()
api_enabled = bool(os.getenv("LOGGING_URL"))

# Create an in-memory stream to store logs
# TODO: do i need this?
log_stream = StringIO()


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
logger.addHandler(logging.StreamHandler(sys.stdout))
