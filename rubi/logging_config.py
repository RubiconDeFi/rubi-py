import logging
from io import StringIO

# Create an in-memory stream to store logs
log_stream = StringIO()

# Configure logging to use the in-memory stream
log_handler = logging.StreamHandler(log_stream)
log_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler.setFormatter(formatter)

# Configure logging for the root logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(log_handler)

# Function to retrieve the captured logs
def get_logs():
    return log_stream.getvalue().strip().split('\n')
