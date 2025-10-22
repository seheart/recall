#!/usr/bin/env python3
"""
Logging configuration for Recall system
"""
import logging
import os
import sys
from pathlib import Path


def get_logger(name: str = "recall") -> logging.Logger:
    """
    Get or create a logger with console and file handlers

    Args:
        name: Logger name (typically __name__ of calling module)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        logger.setLevel(logging.INFO)

        # Console handler with colored output
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)

        # Simple format for console (mimics current print style)
        console_formatter = logging.Formatter("%(message)s")
        console_handler.setFormatter(console_formatter)

        # File handler for detailed logs
        log_dir = Path.home() / ".local" / "share" / "recall" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_dir / "recall.log")
        file_handler.setLevel(logging.DEBUG)

        # Detailed format for file logs
        file_formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)

        # Add handlers
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

    return logger


def set_log_level(level: str) -> None:
    """
    Set the log level for all recall loggers

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    log_level = level_map.get(level.upper(), logging.INFO)
    logging.getLogger("recall").setLevel(log_level)

    # Also update console handler level
    for handler in logging.getLogger("recall").handlers:
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
            handler.setLevel(log_level)
