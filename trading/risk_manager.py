"""
Risk Manager - إدارة المخاطر
=============================
يتحكم في المخاطر وإيقاف الخسارة وحماية رأس المال
"""
from typing import Dict, Optional, List, Tuple
from datetime import datetime

from config import config
from utils.logger import get_logger
from database.db_manager import get_db

logger = get_logger(__name__)


class RiskManager:
    """مدير المخاطر"""

    def __init__(self, mt5_bridge=None):
        self.mt5 = mt5_bridge
        self.daily_pnl: Dict[int, float] = {}  # user_id -> daily pnl
        self.daily_trades: Dict[int, int] = {}  # user_id -> trade count
        self.panic_mode: Dict[int, bool] = {}
        self.trading_paused: Dict[int, bool] = {}

    def can_open_trade(self, user_id: int, symbol: str,
                       volume: float, direction: str) -> Tuple[bool, str]:
        """
        التحقق من إمكانية فتح صفقة جديدة

        Returns:
            Tuple[bool, str]: (مسموح, السبب)
        """
        # 1. التحقق من وضع الطوارئ
        if self.panic_mode.get(user_id, False):
            return False, "🚨 وضع الطوارئ مفعل! جميع الصفقات متوقفة."

        # 2. التحقق من الإيقاف المؤقت
        if self.trading_paused.get(user_id, False):
            return False, "⏸️ التداول متوقف مؤقتاً."

        # 3. التحقق من عدد الصفقات المفتوحة
        db = get_db()
        open_count = db.get_open_trades_count(user_id)
        if open_count >= config.trading.max_open_trades:
            return False, f"⚠️ وصلت للحد الأقصى ({config.trading.max_open_trades} صفقات مفتوحة)"

        # 4. التحقق من حجم العقد
        if volume < config.trading.min_lot:
            return False, f"⚠️ حجم اللوت أقل من المسموح ({config.trading.min_lot})"
        if volume > config.trading.max_lot:
            return False, f"⚠️ حجم اللوت أكبر من المسموح ({config.trading.max_lot})"

        # 5. التحقق من الخسارة اليومية
        daily_loss_pct = self._get_daily_loss_percentage(user_id)
        if daily_loss_pct >= config.trading.max_daily_loss:
            return False, f"🛑 تجاوزت الحد الأقصى للخسارة اليومية ({config.trading.max_daily_loss}%)\nتم إيقاف التداول لليوم."

        # 6. التحقق من ساعات التداول
        now = datetime.utcnow()
        if not (config.trading.trading_start_hour <= now.hour <= config.trading.trading_end_hour):
            return False, "🕐 خارج ساعات التداول المحددة."

        # 7. التحقق من اتصال MT5
        if self.mt5 and not self.mt5.is_connected():
            return False, "⚠️ منصة MT5 غير متصلة."

        return True, "✅"

    def calculate_position_size(self, balance: float, risk_percent: float,
                                stop_loss_pips: float, symbol: str) -> float:
        """
        حساب حجم العقد المناسب بناءً على المخاطرة

        Args:
            balance: الرصيد
            risk_percent: نسبة المخاطرة (%)
            stop_loss_pips: عدد نقاط وقف الخسارة
            symbol: رمز الأصل

        Returns:
            float: حجم العقد
        """
        risk_amount = balance * (risk_percent / 100)

        if self.mt5:
            pip_value = self.mt5.calculate_pip_value(symbol, 0.01)
        else:
            pip_value = 10 if "XAU" in symbol else 1

        if stop_loss_pips <= 0 or pip_value <= 0:
            return config.trading.default_lot

        lot_size = risk_amount / (stop_loss_pips * pip_value)

        # تطبيق الحدود
        lot_size = max(config.trading.min_lot, min(lot_size, config.trading.max_lot))

        # تقريب إلى منزلتين عشريتين
        return round(lot_size, 2)

    def calculate_stop_loss(self, symbol: str, direction: str,
                            entry_price: float, pips: int = None) -> float:
        """
        حساب سعر إيقاف الخسارة

        Args:
            symbol: رمز الأصل
            direction: buy/sell
            entry_price: سعر الدخول
            pips: عدد النقاط

        Returns:
            float: سعر وقف الخسارة
        """
        pips = pips or config.trading.stop_loss_pips

        if direction == "buy":
            if "XAU" in symbol:
                return entry_price - (pips * 0.1)
            elif "JPY" in symbol:
                return entry_price - (pips * 0.01)
            else:
                return entry_price - (pips * 0.0001)
        else:
            if "XAU" in symbol:
                return entry_price + (pips * 0.1)
            elif "JPY" in symbol:
                return entry_price + (pips * 0.01)
            else:
                return entry_price + (pips * 0.0001)

    def calculate_take_profit(self, symbol: str, direction: str,
                              entry_price: float, pips: int = None) -> float:
        """
        حساب سعر جني الأرباح
        """
        pips = pips or config.trading.take_profit_pips

        if direction == "buy":
            if "XAU" in symbol:
                return entry_price + (pips * 0.1)
            elif "JPY" in symbol:
                return entry_price + (pips * 0.01)
            else:
                return entry_price + (pips * 0.0001)
        else:
            if "XAU" in symbol:
                return entry_price - (pips * 0.1)
            elif "JPY" in symbol:
                return entry_price - (pips * 0.01)
            else:
                return entry_price - (pips * 0.0001)

    def activate_panic(self, user_id: int) -> int:
        """
        تفعيل زر الطوارئ - إغلاق كل الصفقات

        Returns:
            int: عدد الصفقات المغلقة
        """
        self.panic_mode[user_id] = True
        logger.warning(f"🚨 PANIC MODE activated for user {user_id}")

        closed_count = 0
        if self.mt5:
            closed_count = self.mt5.close_all_positions()

        # تحديث قاعدة البيانات
        db = get_db()
        open_trades = db.get_open_trades(user_id)
        for trade in open_trades:
            db.close_trade(trade.id, 0, 0, 0)

        logger.info(f"🚨 Panic: {closed_count} positions closed")
        return closed_count

    def deactivate_panic(self, user_id: int):
        """إلغاء وضع الطوارئ"""
        self.panic_mode[user_id] = False
        logger.info(f"✅ Panic mode deactivated for user {user_id}")

    def pause_trading(self, user_id: int):
        """إيقاف التداول مؤقتاً"""
        self.trading_paused[user_id] = True
        logger.info(f"⏸️ Trading paused for user {user_id}")

    def resume_trading(self, user_id: int):
        """استئناف التداول"""
        self.trading_paused[user_id] = False
        logger.info(f"▶️ Trading resumed for user {user_id}")

    def get_risk_status(self, user_id: int) -> Dict:
        """
        تقرير حالة المخاطر
        """
        db = get_db()
        open_trades = db.get_open_trades(user_id)
        today_stats = db.get_today_performance(user_id)
        balance = self.mt5.get_balance() if self.mt5 else 42500.0

        daily_loss = self._get_daily_loss_percentage(user_id)
        risk_level = self._calculate_risk_level(daily_loss, len(open_trades))

        return {
            "panic_mode": self.panic_mode.get(user_id, False),
            "trading_paused": self.trading_paused.get(user_id, False),
            "daily_pnl": today_stats["total_pnl"],
            "daily_pnl_pct": daily_loss,
            "open_trades": len(open_trades),
            "max_open_trades": config.trading.max_open_trades,
            "balance": balance,
            "risk_level": risk_level,
            "max_daily_loss": config.trading.max_daily_loss,
        }

    def _get_daily_loss_percentage(self, user_id: int) -> float:
        """حساب نسبة الخسارة اليومية"""
        db = get_db()
        today = db.get_today_performance(user_id)
        balance = self.mt5.get_balance() if self.mt5 else 42500.0
        if balance <= 0:
            return 0
        return (today["total_pnl"] / balance) * 100

    def _calculate_risk_level(self, daily_loss_pct: float,
                              open_trades: int) -> str:
        """حساب مستوى المخاطرة"""
        if self.panic_mode:
            return "🔴 CRITICAL"

        if daily_loss_pct <= -3 or open_trades >= config.trading.max_open_trades:
            return "🟠 HIGH"

        if daily_loss_pct <= -1.5 or open_trades >= config.trading.max_open_trades * 0.7:
            return "🟡 MEDIUM"

        return "🟢 LOW"


# Singleton
_risk_instance: Optional[RiskManager] = None


def get_risk_manager(mt5_bridge=None) -> RiskManager:
    """الحصول على نسخة مدير المخاطر"""
    global _risk_instance
    if _risk_instance is None:
        _risk_instance = RiskManager(mt5_bridge)
    return _risk_instance
