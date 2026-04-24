"""Logging utilities for the issues pipeline."""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def setup_logging(
    file_path: str,
    *,
    maxBytes: int = (1024**2),
    backupCount: int = 1,
) -> None:
    """
    Set up logging for a script with a rotating file handler.

    This configures logging to write to both stdout and a log file in the same
    directory as the provided script path.

    Args:
        file_path: Path of the script that owns the log file.
        maxBytes: Max size in bytes before log rotation.
        backupCount: Number of rotated backup files to keep.
    """
    script_directory = os.path.dirname(os.path.abspath(file_path))
    log_file_name = os.path.basename(file_path).replace(".py", ".log")
    log_file_path = os.path.join(script_directory, log_file_name)

    rotating_handler = RotatingFileHandler(
        filename=log_file_path,
        maxBytes=maxBytes,
        backupCount=backupCount,
    )

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s - %(levelname)s - %(process)d - "
            "%(threadName)s - %(message)s"
        ),
        handlers=[
            rotating_handler,
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
