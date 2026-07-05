"""
Custom logging setup for RetailSense AI using Python's standard logging module.
"""
from __future__ import annotations

import logging
import sys
from src.config import settings

# Color codes for terminal logging
COLOR_CODES = {
    "DEBUG": "\033[36m",     # Cyan
    "INFO": "\033[32m",      # Green
    "WARNING": "\033[33m",   # Yellow
    "ERROR": "\033[31m",     # Red
    "CRITICAL": "\033[41m\033[37m", # Red background, white text
}
RESET_CODE = "\033[0m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter to inject ANSI colors in stream logs."""

    def format(self, record: logging.LogRecord) -> str:
        color = COLOR_CODES.get(record.levelname, "")
        message = super().format(record)
        if color:
            return f"{color}{message}{RESET_CODE}"
        return message


def get_logger(name: str) -> logging.Logger:
    """Get customized logger with stdout and file handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(settings.log_level)

    # Prevent duplicate handlers if already configured
    if logger.handlers:
        return logger

    # Log formats
    stream_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_format = logging.Formatter(
        "%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console Handler (colored)
    console_handler = logging.StreamHandler(sys.stderr)
    colored_formatter = ColoredFormatter(
        "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(colored_formatter)
    logger.addHandler(console_handler)

    # File Handler (normal text)
    try:
        file_handler = logging.FileHandler(settings.log_file, encoding="utf-8")
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not set up file logger due to: {e}", file=sys.stderr)

    return logger


# Global logger instance
logger = get_logger("retailsense")
