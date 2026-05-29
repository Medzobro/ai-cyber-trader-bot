"""
Helper Functions - دوال مساعدة
"""
from datetime import datetime
from typing import Optional


def format_currency(amount: float, decimals: int = 2) -> str:
    """تنسيق المبلغ المالي"""
    sign = "+" if amount > 0 else ""
    return f"{sign}${amount:,.{decimals}f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """تنسيق النسبة المئوية"""
    arrow = "📈" if value > 0 else "📉" if value < 0 else "➡️"
    return f"{arrow} {value:+.{decimals}f}%"


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """تنسيق التاريخ والوقت"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_direction_emoji(direction: str) -> str:
    """الحصول على إيموجي الاتجاه"""
    direction = direction.lower()
    if direction in ("buy", "long", "شراء"):
        return "🟢"
    elif direction in ("sell", "short", "بيع"):
        return "🔴"
    return "⚪"


def calculate_pnl_percentage(pnl: float, balance: float) -> float:
    """حساب نسبة الربح/الخسارة"""
    if balance == 0:
        return 0.0
    return (pnl / balance) * 100


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """قسمة آمنة"""
    if denominator == 0:
        return default
    return numerator / denominator


def mask_string(s: str, visible: int = 4) -> str:
    """إخفاء جزء من النص الحساس"""
    if len(s) <= visible:
        return "*" * len(s)
    return s[:visible] + "*" * (len(s) - visible)
