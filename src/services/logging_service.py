"""
Logging service for UbShot application.

This module provides centralized logging configuration with console and file output.
Log files are stored in ~/.local/share/ubshot/logs/ by default.
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


# Default log directory following XDG Base Directory Specification
DEFAULT_LOG_DIR = Path.home() / ".local" / "share" / "ubshot" / "logs"

# Module-level flag to track if logging has been set up
_logging_initialized = False


def setup_logging(
    log_level: int = logging.INFO,
    log_to_file: bool = True,
    log_dir: Optional[Path] = None,
) -> None:
    """
    Configure the logging system for UbShot.

    Args:
        log_level: The logging level (e.g., logging.DEBUG, logging.INFO).
        log_to_file: Whether to also log to a file.
        log_dir: Directory for log files. Defaults to ~/.local/share/ubshot/logs/

    This function should be called once at application startup.
    """
    global _logging_initialized

    if _logging_initialized:
        return

    # Use default log directory if not specified
    if log_dir is None:
        log_dir = DEFAULT_LOG_DIR

    # Create log format
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Console handler - always enabled
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(log_format, date_format))
    root_logger.addHandler(console_handler)

    # File handler - optional
    if log_to_file:
        try:
            # Create log directory if it doesn't exist
            log_dir.mkdir(parents=True, exist_ok=True)

            # Create log file with date in filename
            log_filename = f"ubshot_{datetime.now().strftime('%Y%m%d')}.log"
            log_path = log_dir / log_filename

            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            file_handler.setLevel(log_level)
            file_handler.setFormatter(logging.Formatter(log_format, date_format))
            root_logger.addHandler(file_handler)

        except (OSError, PermissionError) as e:
            # If we can't create the log file, just log to console
            console_handler.setLevel(logging.WARNING)
            root_logger.warning(f"Could not create log file: {e}. Logging to console only.")

    _logging_initialized = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: The name for the logger, typically __name__ of the calling module.

    Returns:
        A configured Logger instance.

    Usage:
        from services.logging_service import get_logger
        logger = get_logger(__name__)
        logger.info("Application started")
    """
    return logging.getLogger(name)
