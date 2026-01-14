"""
Centralized logging configuration for the backend.
Provides structured logging with proper levels and formatting.
"""

import logging
import sys
from datetime import datetime

# Create logger
logger = logging.getLogger("e-leiloes")
logger.setLevel(logging.DEBUG)

# Prevent duplicate handlers
if not logger.handlers:
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)

    # Format: timestamp - level - message
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def log_info(message: str):
    """Log info level message"""
    logger.info(message)


def log_warning(message: str):
    """Log warning level message"""
    logger.warning(message)


def log_error(message: str, exc: Exception = None):
    """Log error level message with optional exception"""
    if exc:
        logger.error(f"{message}: {type(exc).__name__}: {exc}")
    else:
        logger.error(message)


def log_debug(message: str):
    """Log debug level message"""
    logger.debug(message)


def log_exception(message: str):
    """Log exception with full traceback"""
    logger.exception(message)
