"""
Logger Utility - تسجيل الأحداث
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from config import LogConfig


def setup_logger(config: LogConfig) -> logging.Logger:
    """إعداد نظام تسجيل الأحداث"""

    # إنشاء مجلد السجلات إذا لم يكن موجوداً
    log_path = Path(config.file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("CyberTrader")
    logger.setLevel(getattr(logging, config.level.upper(), logging.INFO))

    # تجنب إضافة handlers مكررة
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
    """الحصول على logger"""
    if name:
        return logging.getLogger(f"CyberTrader.{name}")
    return logging.getLogger("CyberTrader")
