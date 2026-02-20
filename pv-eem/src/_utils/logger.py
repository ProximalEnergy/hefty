import logging
import os
import sys
import warnings

from dotenv import load_dotenv


def setup_logger(
    *,
    level: int = logging.INFO,
    environment: str | None = None,
) -> logging.Logger:
    """Configure the root logger to emit logs to stdout."""
    # Universal config
    logging.captureWarnings(True)
    warnings.simplefilter("always")

    # Create logger
    logger = logging.getLogger()
    load_dotenv()
    if environment is None:
        environment = os.getenv("ENVIRONMENT")

    match environment:
        case "PROD" | "DEV" | "VALIDATE":
            logger.setLevel(level)
        case _:
            logger.setLevel(logging.WARNING)

    warnings_logger = logging.getLogger("py.warnings")
    warnings_logger.setLevel(logging.WARNING)

    # Create formatters
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    has_stdout_handler = any(
        isinstance(handler, logging.StreamHandler)
        and getattr(handler, "stream", None) is sys.stdout
        for handler in logger.handlers
    )
    if not has_stdout_handler:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger


if __name__ == "__main__":
    setup_logger()
