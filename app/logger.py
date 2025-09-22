# logger.py
import logging

# Configure logging (shared across the whole application)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# Get a logger instance (module-specific or root)
logger = logging.getLogger("my_fastapi_app")

# Optional: Set the log level globally or per module
logger.setLevel(logging.INFO)
