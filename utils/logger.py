"""
Logger Utility
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from config import LogConfig


def setup_logger(config: LogConfig) -> logging.Logger:
    """Setup the logging system"""

    # Create log directory if it doesn't exist
    log_path = Path(config.file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("CyberTrader")
    logger.setLevel(getattr(logging, config.level.upper(), logging.INFO))

    # Avoid duplicate handlers
    if logger.handlers:
        return logger

    # Format
    formatter = logging.Formatter(config.format)

    # File handler
    file_handler = logging.FileHandler(config.file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Get a logger instance"""
    if name:
        return logging.getLogger(f"CyberTrader.{name}")
    return logging.getLogger("CyberTrader")
