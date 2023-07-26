from logging_config import logger

from dotenv import load_dotenv
import os

# get url path if supplied
load_dotenv()
api_enabled = bool(os.getenv("LOGGING_URL"))
print(api_enabled)

# Log some events
logger.debug("Debug message")
logger.info("Informational message")
logger.warning("Warning message")
logger.error("Error message")
