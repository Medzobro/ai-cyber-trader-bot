"""
Trade Executor
===============
Manages trade lifecycle from analysis to execution
"""
from typing import Dict, Optional
from datetime import datetime

from config import config
from utils.logger import get_logger
from database.db_manager import get_db
from ai_engine.predictor import AIPredictor
from ai_engine.market_analyzer import MarketAnalyzer
from .mt5_bridge import MT5Bridge
from .risk_manager import RiskManager

logger = get_logger(__name__)


class TradeExecutor:
    """Main trade executor"""

    def __init__(self, mt5: MT5Bridge = None, risk_manager: RiskManager = None,
                 predictor: AIPredictor = None, analyzer: MarketAnalyzer = None):
        self.mt5 = mt5
        self.risk = risk_manager
        self.predictor = predictor
        self.analyzer = analyzer

    def execute_analysis_cycle(self, user_id: int, symbol: str = None,
                               timeframe: str = None) -> Dict:
        """
        Full analysis cycle: Analyze → Predict → Execute

        Returns:
            Dict: Cycle result
        """
        symbol = symbol or config.trading.default_symbol
        timeframe = timeframe or config.ai.prediction_timeframe

        db = get_db()
        ai_cfg = db.get_ai_config(user_id)

        result = {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": datetime.utcnow().isoformat(),
            "action": "none",
            "trade_executed": False,
            "message": "",
        }

        # 1. Risk check
        can_trade, reason = self.risk.can_open_trade(
            user_id, symbol, config.trading.default_lot,
            db.get_setting(user_id, "direction", "both")
        )

        if not can_trade:
            result["message"] = reason
            result["action"] = "blocked"
            return result

        # 2. Market analysis
        if self.analyzer:
            market_analysis = self.analyzer.analyze(symbol, timeframe, user_id=user_id)
        else:
            result["message"] = "⚠️ Market analyzer not initialized"
            return result

        if market_analysis.get("error"):
            result["message"] = market_analysis["message"]
            return result

        # 3. AI prediction
        if self.predictor:
            prediction = self.predictor.predict(symbol, market_analysis, user_id)
        else:
            result["message"] = "⚠️ Predictor not initialized"
            return result

        # 4. Check confidence threshold
        confidence = prediction.get("ai_confidence", 0)
        threshold = ai_cfg.confidence_threshold

        if confidence < threshold:
            result["action"] = "low_confidence"
            result["message"] = (
                f"📉 Confidence ({confidence:.1f}%) below threshold "
                f"({threshold:.0f}%). No trade opened."
            )
            result["prediction"] = prediction
            return result

        # 5. Get user trading settings
        lot_setting = db.get_setting(user_id, "lot", str(config.trading.default_lot))
        volume = float(lot_setting)
        direction_setting = db.get_setting(user_id, "direction", "both")
        ai_direction = prediction.get("ai_analysis", "hold")

        # Check direction match
        if direction_setting == "buy" and ai_direction != "buy":
            result["action"] = "direction_mismatch"
            result["message"] = "🔴 Settings allow BUY only."
            return result
        if direction_setting == "sell" and ai_direction != "sell":
            result["action"] = "direction_mismatch"
            result["message"] = "🟢 Settings allow SELL only."
            return result

        if ai_direction == "hold":
            result["action"] = "hold"
            result["message"] = f"⏸️ AI recommendation: HOLD.\n{market_analysis.get('reasoning', '')}"
            return result

        # 6. Calculate SL/TP
        entry_price = prediction.get("entry_price", 0)
        stop_loss = prediction.get("stop_loss", 0)
        take_profit = prediction.get("take_profit", 0)

        # 7. Execute trade
        if self.mt5:
            ticket = self.mt5.place_order(
                symbol=symbol,
                order_type=ai_direction,
                volume=volume,
                price=entry_price,
                sl=stop_loss,
                tp=take_profit,
                comment="AI Cyber-Trader",
            )
        else:
            # Simulation
            ticket = None

        # 8. Save trade to database
        trade = db.create_trade(
            user_id=user_id,
            symbol=symbol,
            direction=ai_direction,
            volume=volume,
            open_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            ticket=ticket,
            ai_confidence=confidence,
            ai_reasoning=market_analysis.get("reasoning", ""),
        )

        result["action"] = "executed"
        result["trade_executed"] = True
        result["message"] = (
            f"✅ New trade opened!\n\n"
            f"📥 Type: {'BUY 🟢' if ai_direction == 'buy' else 'SELL 🔴'}\n"
            f"🏆 Asset: {symbol}\n"
            f"🎯 Entry Price: {entry_price}\n"
            f"🛡️ Stop Loss: {stop_loss}\n"
            f"💰 Take Profit: {take_profit}\n"
            f"📦 Volume: {volume} lots\n"
            f"🧠 AI Confidence: {confidence:.1f}%"
        )
        result["trade"] = {
            "id": trade.id,
            "ticket": ticket,
            "symbol": symbol,
            "direction": ai_direction,
            "volume": volume,
            "open_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "confidence": confidence,
        }
        result["prediction"] = prediction

        logger.info(
            f"📊 Trade executed: {symbol} {ai_direction} "
            f"@ {entry_price} | Confidence: {confidence:.1f}%"
        )

        return result

    def execute_manual_trade(self, user_id: int, symbol: str, direction: str,
                             volume: float, sl: float = 0, tp: float = 0) -> Dict:
        """
        Execute a manual trade (directly from user)

        Returns:
            Dict: Execution result
        """
        result = {
            "success": False,
            "message": "",
            "trade": None,
        }

        # 1. Risk check
        can_trade, reason = self.risk.can_open_trade(
            user_id, symbol, volume, direction
        )
        if not can_trade:
            result["message"] = reason
            return result

        # 2. Get current price
        if self.mt5:
            tick = self.mt5.get_tick(symbol)
            if not tick:
                result["message"] = f"❌ Could not fetch price for {symbol}"
                return result
            entry_price = tick["ask"] if direction == "buy" else tick["bid"]
        else:
            entry_price = 2345.50 if symbol == "XAUUSD" else 1.0850

        # 3. Calculate SL/TP if not specified
        if not sl:
            sl = self.risk.calculate_stop_loss(symbol, direction, entry_price)
        if not tp:
            tp = self.risk.calculate_take_profit(symbol, direction, entry_price)

        # 4. Execute trade
        if self.mt5:
            ticket = self.mt5.place_order(
                symbol=symbol,
                order_type=direction,
                volume=volume,
                price=entry_price,
                sl=sl,
                tp=tp,
                comment="AI Cyber-Trader Manual",
            )
        else:
            ticket = None

        # 5. Save to database
        db = get_db()
        trade = db.create_trade(
            user_id=user_id,
            symbol=symbol,
            direction=direction,
            volume=volume,
            open_price=entry_price,
            stop_loss=sl,
            take_profit=tp,
            ticket=ticket,
        )

        result["success"] = True
        result["message"] = (
            f"✅ Manual trade opened!\n"
            f"📥 {direction.upper()} | {symbol}\n"
            f"🎯 Price: {entry_price}\n"
            f"📦 Volume: {volume} lots"
        )
        result["trade"] = {
            "id": trade.id,
            "ticket": ticket,
            "symbol": symbol,
            "direction": direction,
            "volume": volume,
            "open_price": entry_price,
            "stop_loss": sl,
            "take_profit": tp,
        }

        return result

    def close_trade_by_id(self, trade_id: int, user_id: int) -> Dict:
        """Close a specific trade by ID"""
        db = get_db()
        trade = None

        # Close in MT5 first
        if self.mt5 and trade and trade.ticket:
            self.mt5.close_position(trade.ticket, trade.symbol)

        # Update database
        close_price = 0
        if self.mt5:
            tick = self.mt5.get_tick(trade.symbol if trade else "XAUUSD")
            close_price = tick["bid"] if tick else 0

        db.close_trade(trade_id, close_price, 0, 0)

        return {"success": True, "message": "✅ Trade closed successfully"}


# Singleton
_executor_instance: Optional[TradeExecutor] = None


def get_executor(mt5=None, risk=None, predictor=None,
                 analyzer=None) -> TradeExecutor:
    """Get TradeExecutor singleton instance"""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = TradeExecutor(mt5, risk, predictor, analyzer)
    return _executor_instance
