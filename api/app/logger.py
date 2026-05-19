# logger.py
import logging

APPLICATION_LOGGER_NAME = "my_fastapi_app"

# Configure logging (shared across the whole application)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)

# Get the application logger instance.
logger = logging.getLogger(APPLICATION_LOGGER_NAME)

# Optional: Set the log level globally or per module
logger.setLevel(logging.INFO)


def get_logger(*, name: str) -> logging.Logger:
    """Return a module-specific child logger.

    Args:
        name (str): The name of the module.
    """
    return logger.getChild(name)
