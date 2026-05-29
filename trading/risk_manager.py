"""
Risk Manager
=============
Controls risk, stop loss, and capital protection
"""
from typing import Dict, Optional, List, Tuple
from datetime import datetime

from config import config
from utils.logger import get_logger
from database.db_manager import get_db

logger = get_logger(__name__)


class RiskManager:
    """Risk manager"""

    def __init__(self, mt5_bridge=None):
        self.mt5 = mt5_bridge
        self.daily_pnl: Dict[int, float] = {}  # user_id -> daily pnl
        self.daily_trades: Dict[int, int] = {}  # user_id -> trade count
        self.panic_mode: Dict[int, bool] = {}
        self.trading_paused: Dict[int, bool] = {}

    def can_open_trade(self, user_id: int, symbol: str,
                       volume: float, direction: str,
                       stop_loss: float = 0, take_profit: float = 0) -> Tuple[bool, str]:
        """
        Check if a new trade can be opened.
        
        MANDATORY: SL and TP are required and enforced.

        Returns:
            Tuple[bool, str]: (allowed, reason)
        """
        # 0. MANDATORY: Stop Loss and Take Profit required
        if stop_loss <= 0:
            return False, "❌ Stop Loss (SL) is MANDATORY. Cannot open trade without SL."
        if take_profit <= 0:
            return False, "❌ Take Profit (TP) is MANDATORY. Cannot open trade without TP."
        
        # Validate SL/TP direction
        if direction == "buy":
            if stop_loss >= take_profit:
                return False, "❌ For BUY: SL must be below TP."
        elif direction == "sell":
            if stop_loss <= take_profit:
                return False, "❌ For SELL: SL must be above TP."
        # 1. Check panic mode
        if self.panic_mode.get(user_id, False):
            return False, "🚨 Panic mode active! All trading stopped."

        # 2. Check paused status
        if self.trading_paused.get(user_id, False):
            return False, "⏸️ Trading is paused."

        # 3. Check open positions count
        db = get_db()
        open_count = db.get_open_trades_count(user_id)
        if open_count >= config.trading.max_open_trades:
            return False, f"⚠️ Max open positions reached ({config.trading.max_open_trades})"

        # 4. Check lot size
        if volume < config.trading.min_lot:
            return False, f"⚠️ Lot size below minimum ({config.trading.min_lot})"
        if volume > config.trading.max_lot:
            return False, f"⚠️ Lot size exceeds maximum ({config.trading.max_lot})"

        # 5. Check daily loss
        daily_loss_pct = self._get_daily_loss_percentage(user_id)
        if daily_loss_pct >= config.trading.max_daily_loss:
            return False, f"🛑 Max daily loss limit reached ({config.trading.max_daily_loss}%)\nTrading stopped for today."

        # 6. Check trading hours
        now = datetime.utcnow()
        if not (config.trading.trading_start_hour <= now.hour <= config.trading.trading_end_hour):
            return False, "🕐 Outside trading hours."

        # 7. Check MT5 connection
        if self.mt5 and not self.mt5.is_connected():
            return False, "⚠️ MT5 platform not connected."

        return True, "✅"

    def calculate_position_size(self, balance: float, risk_percent: float,
                                stop_loss_pips: float, symbol: str) -> float:
        """
        Calculate appropriate position size based on risk

        Args:
            balance: Account balance
            risk_percent: Risk percentage (%)
            stop_loss_pips: Stop loss in pips
            symbol: Asset symbol

        Returns:
            float: Lot size
        """
        risk_amount = balance * (risk_percent / 100)

        if self.mt5:
            pip_value = self.mt5.calculate_pip_value(symbol, 0.01)
        else:
            pip_value = 10 if "XAU" in symbol else 1

        if stop_loss_pips <= 0 or pip_value <= 0:
            return config.trading.default_lot

        lot_size = risk_amount / (stop_loss_pips * pip_value)

        # Apply limits
        lot_size = max(config.trading.min_lot, min(lot_size, config.trading.max_lot))

        # Round to 2 decimal places
        return round(lot_size, 2)

    def calculate_stop_loss(self, symbol: str, direction: str,
                            entry_price: float, pips: int = None,
                            atr_value: float = None) -> float:
        """
        Calculate stop loss price dynamically.
        Uses ATR-based calculation if ATR value is provided (preferred),
        otherwise falls back to pip-based calculation.

        Args:
            symbol: Asset symbol
            direction: buy/sell
            entry_price: Entry price
            pips: Number of pips (fallback)
            atr_value: ATR value for dynamic calculation

        Returns:
            float: Stop loss price
        """
        if atr_value and atr_value > 0:
            # ATR-based: SL = entry ± (ATR × 1.5)
            sl_distance = atr_value * 1.5
            if direction == "buy":
                return round(entry_price - sl_distance, 5)
            else:
                return round(entry_price + sl_distance, 5)
        
        # Fallback to pip-based
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
                              entry_price: float, pips: int = None,
                              atr_value: float = None) -> float:
        """Calculate take profit price dynamically (ATR-based preferred)"""
        if atr_value and atr_value > 0:
            # ATR-based: TP = entry ± (ATR × 2.5) - better risk/reward
            tp_distance = atr_value * 2.5
            if direction == "buy":
                return round(entry_price + tp_distance, 5)
            else:
                return round(entry_price - tp_distance, 5)
        
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
        Activate panic mode - close all positions

        Returns:
            int: Number of positions closed
        """
        self.panic_mode[user_id] = True
        logger.warning(f"🚨 PANIC MODE activated for user {user_id}")

        closed_count = 0
        if self.mt5:
            closed_count = self.mt5.close_all_positions()

        # Update database
        db = get_db()
        open_trades = db.get_open_trades(user_id)
        for trade in open_trades:
            db.close_trade(trade.id, 0, 0, 0)

        logger.info(f"🚨 Panic: {closed_count} positions closed")
        return closed_count

    def deactivate_panic(self, user_id: int):
        """Deactivate panic mode"""
        self.panic_mode[user_id] = False
        logger.info(f"✅ Panic mode deactivated for user {user_id}")

    def pause_trading(self, user_id: int):
        """Pause trading"""
        self.trading_paused[user_id] = True
        logger.info(f"⏸️ Trading paused for user {user_id}")

    def resume_trading(self, user_id: int):
        """Resume trading"""
        self.trading_paused[user_id] = False
        logger.info(f"▶️ Trading resumed for user {user_id}")

    def get_risk_status(self, user_id: int) -> Dict:
        """Get risk status report"""
        db = get_db()
        open_trades = db.get_open_trades(user_id)
        today_stats = db.get_today_performance(user_id)
        balance = self.mt5.get_balance() if self.mt5 else 42500.0

        daily_loss = self._get_daily_loss_percentage(user_id)
        risk_level = self._calculate_risk_level(user_id, daily_loss, len(open_trades))

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
        """Calculate daily loss percentage"""
        db = get_db()
        today = db.get_today_performance(user_id)
        balance = self.mt5.get_balance() if self.mt5 else 42500.0
        if balance <= 0:
            return 0
        return (today["total_pnl"] / balance) * 100

    def _calculate_risk_level(self, user_id: int, daily_loss_pct: float,
                              open_trades: int) -> str:
        """Calculate risk level for a specific user"""
        if self.panic_mode.get(user_id, False):
            return "🔴 CRITICAL"

        if daily_loss_pct <= -3 or open_trades >= config.trading.max_open_trades:
            return "🟠 HIGH"

        if daily_loss_pct <= -1.5 or open_trades >= config.trading.max_open_trades * 0.7:
            return "🟡 MEDIUM"

        return "🟢 LOW"


# Singleton
_risk_instance: Optional[RiskManager] = None


def get_risk_manager(mt5_bridge=None) -> RiskManager:
    """Get RiskManager singleton instance"""
    global _risk_instance
    if _risk_instance is None:
        _risk_instance = RiskManager(mt5_bridge)
    return _risk_instance
