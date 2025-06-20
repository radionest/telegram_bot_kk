"""Logger configuration for the application."""

import sys
from typing import Any

from loguru import logger


def setup_logger() -> Any:
    """Set up logger configuration.

    Returns:
        Configured logger instance
    """
    # Remove default handler
    logger.remove()

    # Console handler with nice formatting
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True,
    )

    # File handler with rotation
    logger.add(
        "logs/bot_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        encoding="utf-8",
    )

    # Separate error log with full diagnostics
    logger.add(
        "logs/errors_{time}.log",
        rotation="1 week",
        retention="1 month",
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
    )

    return logger


# Configure logger on import
setup_logger()
