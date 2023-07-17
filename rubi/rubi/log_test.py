import logging
import requests
from logging_config import get_logs

logger = logging.getLogger(__name__)

# Configure the logger
logging.basicConfig(level=logging.DEBUG)

# Log some events
logger.debug("Debug message")
logger.info("Informational message")
logger.warning("Warning message")
logger.error("Error message")

# Retrieve the logs
logs = get_logs()

# Send logs to the Flask app API endpoint
url = "http://localhost:5000/api/logs"  # Update the URL if necessary
response = requests.post(url, json={"logs": logs})
print(response.text)
