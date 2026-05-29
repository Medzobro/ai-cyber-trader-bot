"""
Helper Functions
"""
from datetime import datetime
from typing import Optional


def format_currency(amount: float, decimals: int = 2) -> str:
    """Format currency amount"""
    sign = "+" if amount > 0 else ""
    return f"{sign}${amount:,.{decimals}f}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format percentage value"""
    arrow = "📈" if value > 0 else "📉" if value < 0 else "➡️"
    return f"{arrow} {value:+.{decimals}f}%"


def format_timestamp(dt: Optional[datetime] = None) -> str:
    """Format timestamp"""
    if dt is None:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def get_direction_emoji(direction: str) -> str:
    """Get direction emoji"""
    direction = direction.lower()
    if direction in ("buy", "long"):
        return "🟢"
    elif direction in ("sell", "short"):
        return "🔴"
    return "⚪"


def calculate_pnl_percentage(pnl: float, balance: float) -> float:
    """Calculate PnL percentage"""
    if balance == 0:
        return 0.0
    return (pnl / balance) * 100


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division"""
    if denominator == 0:
        return default
    return numerator / denominator


def mask_string(s: str, visible: int = 4) -> str:
    """Mask sensitive string, showing only first few characters"""
    if len(s) <= visible:
        return "*" * len(s)
    return s[:visible] + "*" * (len(s) - visible)
