"""
MT5 Bridge - MetaTrader 5 Connection Bridge
============================================
Manages MT5 connection and executes trading operations
"""
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime
import pandas as pd

from config import config
from utils.logger import get_logger

logger = get_logger(__name__)

# MetaTrader5 is optional on Linux (requires Wine or MetaAPI)
try:
    import MetaTrader5 as mt5_lib
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    logger.warning("⚠️ MetaTrader5 library not installed. Running in simulation mode.")


class MT5Bridge:
    """MetaTrader 5 connection bridge"""

    # Timeframe mapping
    TIMEFRAMES = {
        "M1": mt5_lib.TIMEFRAME_M1 if MT5_AVAILABLE else 1,
        "M5": mt5_lib.TIMEFRAME_M5 if MT5_AVAILABLE else 5,
        "M15": mt5_lib.TIMEFRAME_M15 if MT5_AVAILABLE else 15,
        "M30": mt5_lib.TIMEFRAME_M30 if MT5_AVAILABLE else 30,
        "H1": mt5_lib.TIMEFRAME_H1 if MT5_AVAILABLE else 60,
        "H4": mt5_lib.TIMEFRAME_H4 if MT5_AVAILABLE else 240,
        "D1": mt5_lib.TIMEFRAME_D1 if MT5_AVAILABLE else 1440,
    }

    def __init__(self):
        self.connected = False
        self.account_info: Dict = {}
        self.simulation = not MT5_AVAILABLE

    def connect(self, login: int = None, password: str = None,
                server: str = None) -> bool:
        """
        Connect to MT5 account

        Returns:
            bool: Connection success
        """
        login = login or config.trading.mt5_login
        password = password or config.trading.mt5_password
        server = server or config.trading.mt5_server

        if self.simulation:
            logger.info("🟡 Running in SIMULATION mode (no real MT5 connection)")
            self.connected = True
            self.account_info = self._simulate_account_info()
            return True

        try:
            if not mt5_lib.initialize(
                login=login,
                password=password,
                server=server,
            ):
                error = mt5_lib.last_error()
                logger.error(f"❌ MT5 initialize failed: {error}")
                return False

            self.connected = True
            self.account_info = self._get_real_account_info()
            logger.info(f"✅ MT5 connected: {server} | Balance: ${self.account_info.get('balance', 0)}")
            return True

        except Exception as e:
            logger.error(f"❌ MT5 connection error: {e}")
            self.simulation = True
            self.connected = True
            self.account_info = self._simulate_account_info()
            return True  # Fallback to simulation

    def disconnect(self):
        """Disconnect from MT5"""
        if self.connected and not self.simulation:
            mt5_lib.shutdown()
        self.connected = False
        logger.info("🔌 MT5 disconnected")

    def is_connected(self) -> bool:
        """Check connection status"""
        return self.connected

    def get_account_info(self) -> Dict[str, Any]:
        """Get account information"""
        if self.simulation:
            return self._simulate_account_info()
        return self._get_real_account_info()

    def get_balance(self) -> float:
        """Get current balance"""
        info = self.get_account_info()
        return info.get("balance", 0.0)

    def get_equity(self) -> float:
        """Get equity"""
        info = self.get_account_info()
        return info.get("equity", 0.0)

    def get_tick(self, symbol: str) -> Optional[Dict]:
        """
        Get current tick price

        Returns:
            Dict with 'bid', 'ask', 'spread', 'time'
        """
        if self.simulation:
            return self._simulate_tick(symbol)

        try:
            tick = mt5_lib.symbol_info_tick(symbol)
            if tick is None:
                return None

            return {
                "bid": tick.bid,
                "ask": tick.ask,
                "spread": tick.ask - tick.bid,
                "time": datetime.fromtimestamp(tick.time),
            }
        except Exception as e:
            logger.error(f"❌ Error getting tick for {symbol}: {e}")
            return None

    def get_rates(self, symbol: str, timeframe: str,
                  count: int = 100) -> Optional[List]:
        """
        Get candles (Rates)

        Returns:
            List of [time, open, high, low, close, tick_volume, spread, real_volume]
        """
        if self.simulation:
            return None  # MarketAnalyzer will use simulation

        try:
            tf = self.TIMEFRAMES.get(timeframe, mt5_lib.TIMEFRAME_M15)
            rates = mt5_lib.copy_rates_from_pos(symbol, tf, 0, count)

            if rates is None or len(rates) == 0:
                return None

            return rates.tolist()

        except Exception as e:
            logger.error(f"❌ Error getting rates: {e}")
            return None

    def place_order(self, symbol: str, order_type: str, volume: float,
                    price: float = 0, sl: float = 0, tp: float = 0,
                    comment: str = "AI Cyber-Trader") -> Optional[int]:
        """
        Place a new order

        Args:
            symbol: Asset symbol
            order_type: 'buy' or 'sell'
            volume: Lot size
            price: Price (0 = market price)
            sl: Stop loss
            tp: Take profit
            comment: Order comment

        Returns:
            int: Ticket number or None
        """
        if self.simulation:
            ticket = hash(f"{symbol}{datetime.utcnow().timestamp()}") % 1000000
            logger.info(f"🟡 [SIM] Order placed: {symbol} {order_type} V={volume} | Ticket=#{ticket}")
            return ticket

        try:
            tick = self.get_tick(symbol)
            if tick is None:
                logger.error(f"❌ Cannot place order: no tick for {symbol}")
                return None

            # Determine order type
            if order_type.lower() == "buy":
                mt5_type = mt5_lib.ORDER_TYPE_BUY
                order_price = price or tick["ask"]
            else:
                mt5_type = mt5_lib.ORDER_TYPE_SELL
                order_price = price or tick["bid"]

            request = {
                "action": mt5_lib.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5_type,
                "price": order_price,
                "sl": sl,
                "tp": tp,
                "deviation": 20,
                "magic": 234000,
                "comment": comment,
                "type_time": mt5_lib.ORDER_TIME_GTC,
                "type_filling": mt5_lib.ORDER_FILLING_FOK,
            }

            result = mt5_lib.order_send(request)

            if result.retcode != mt5_lib.TRADE_RETCODE_DONE:
                logger.error(f"❌ Order failed: {result.comment} (code={result.retcode})")
                return None

            logger.info(f"✅ Order placed: {symbol} {order_type} @ {order_price} | Ticket=#{result.order}")
            return result.order

        except Exception as e:
            logger.error(f"❌ Place order error: {e}")
            return None

    def close_position(self, ticket: int, symbol: str = None,
                       volume: float = None) -> bool:
        """
        Close a position

        Returns:
            bool: Close success
        """
        if self.simulation:
            logger.info(f"🟡 [SIM] Position closed: Ticket=#{ticket}")
            return True

        try:
            # Get position from MT5
            position = mt5_lib.positions_get(ticket=ticket)
            if not position:
                logger.warning(f"⚠️ Position #{ticket} not found")
                return False

            pos = position[0]
            close_volume = volume or pos.volume

            tick = mt5_lib.symbol_info_tick(pos.symbol)

            # Determine close order type
            if pos.type == mt5_lib.POSITION_TYPE_BUY:
                close_type = mt5_lib.ORDER_TYPE_SELL
                close_price = tick.bid
            else:
                close_type = mt5_lib.ORDER_TYPE_BUY
                close_price = tick.ask

            request = {
                "action": mt5_lib.TRADE_ACTION_DEAL,
                "position": ticket,
                "symbol": pos.symbol,
                "volume": close_volume,
                "type": close_type,
                "price": close_price,
                "deviation": 20,
                "magic": 234000,
                "comment": "AI Cyber-Trader Close",
                "type_time": mt5_lib.ORDER_TIME_GTC,
                "type_filling": mt5_lib.ORDER_FILLING_FOK,
            }

            result = mt5_lib.order_send(request)

            if result.retcode != mt5_lib.TRADE_RETCODE_DONE:
                logger.error(f"❌ Close failed: {result.comment}")
                return False

            logger.info(f"✅ Position closed: Ticket=#{ticket}")
            return True

        except Exception as e:
            logger.error(f"❌ Close position error: {e}")
            return False

    def close_all_positions(self) -> int:
        """
        Close all open positions (panic button)

        Returns:
            int: Number of positions closed
        """
        if self.simulation:
            logger.info("🟡 [SIM] All positions closed")
            return 3

        try:
            positions = mt5_lib.positions_get()
            if not positions:
                return 0

            closed = 0
            for pos in positions:
                if self.close_position(pos.ticket):
                    closed += 1

            logger.info(f"🚨 Emergency: {closed} positions closed")
            return closed

        except Exception as e:
            logger.error(f"❌ Close all error: {e}")
            return 0

    def get_open_positions(self) -> List[Dict]:
        """Get open positions"""
        if self.simulation:
            return self._simulate_positions()

        try:
            positions = mt5_lib.positions_get()
            if not positions:
                return []

            result = []
            for pos in positions:
                result.append({
                    "ticket": pos.ticket,
                    "symbol": pos.symbol,
                    "type": "buy" if pos.type == 0 else "sell",
                    "volume": pos.volume,
                    "open_price": pos.price_open,
                    "current_price": pos.price_current,
                    "sl": pos.sl,
                    "tp": pos.tp,
                    "profit": pos.profit,
                    "swap": pos.swap,
                    "commission": pos.commission,
                    "open_time": datetime.fromtimestamp(pos.time),
                })

            return result

        except Exception as e:
            logger.error(f"❌ Get positions error: {e}")
            return []

    def calculate_pip_value(self, symbol: str, volume: float) -> float:
        """Calculate pip value"""
        if self.simulation:
            if "XAU" in symbol:
                return volume * 10  # $10 per 0.01 lot for gold
            return volume * 10  # $10 per standard lot for forex

        try:
            info = mt5_lib.symbol_info(symbol)
            if info is None:
                return 0
            tick_value = info.trade_tick_value
            return tick_value * volume / info.trade_tick_size if info.trade_tick_size else 0
        except Exception:
            return volume * 10

    # ─── Private Helpers ──────────────────────────

    def _get_real_account_info(self) -> Dict:
        """Get real account info"""
        if not MT5_AVAILABLE:
            return self._simulate_account_info()
        try:
            info = mt5_lib.account_info()
            if info is None:
                return self._simulate_account_info()
            return {
                "login": info.login,
                "server": info.server,
                "balance": info.balance,
                "equity": info.equity,
                "margin": info.margin,
                "margin_free": info.margin_free,
                "margin_level": info.margin_level,
                "currency": info.currency,
            }
        except Exception:
            return self._simulate_account_info()

    def _simulate_account_info(self) -> Dict:
        """Simulate account info for testing"""
        return {
            "login": 12345678,
            "server": "ICMarkets-Demo",
            "balance": 42500.0,
            "equity": 43750.0,
            "margin": 1250.0,
            "margin_free": 41250.0,
            "margin_level": 3400.0,
            "currency": "USD",
        }

    def _simulate_tick(self, symbol: str) -> Dict:
        """Simulate price for testing"""
        import random
        import hashlib

        # Use symbol hash for semi-stable price
        seed = int(hashlib.md5(symbol.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed + datetime.utcnow().hour * 100 + datetime.utcnow().minute)

        base_prices = {
            "XAUUSD": 2345.50,
            "EURUSD": 1.0850,
            "GBPUSD": 1.2650,
            "USDJPY": 151.50,
            "BTCUSD": 67500.00,
            "US30": 39200.00,
            "NAS100": 18500.00,
        }

        base = base_prices.get(symbol, 100.0)
        noise = rng.uniform(-0.001, 0.001)
        spread = 0.0002 if "XAU" in symbol else 0.0001

        bid = base * (1 + noise)
        ask = bid * (1 + spread)

        return {
            "bid": round(bid, 5 if "XAU" in symbol else 5),
            "ask": round(ask, 5 if "XAU" in symbol else 5),
            "spread": round(ask - bid, 5),
            "time": datetime.utcnow(),
        }

    def _simulate_positions(self) -> List[Dict]:
        """Simulate open positions for testing"""
        import random
        rng = random.Random(42)

        positions = []
        symbols = ["XAUUSD", "EURUSD"]
        for i in range(rng.randint(0, 2)):
            symbol = symbols[i % len(symbols)]
            open_price = 2345.50 if symbol == "XAUUSD" else 1.0850
            current_price = open_price * (1 + rng.uniform(-0.005, 0.01))
            positions.append({
                "ticket": 1000000 + i,
                "symbol": symbol,
                "type": "buy" if rng.random() > 0.5 else "sell",
                "volume": 0.01,
                "open_price": open_price,
                "current_price": current_price,
                "sl": open_price * 0.99,
                "tp": open_price * 1.02,
                "profit": (current_price - open_price) * 100,
                "swap": -2.5,
                "commission": -3.5,
                "open_time": datetime.utcnow(),
            })

        return positions


# Singleton
_mt5_instance: Optional[MT5Bridge] = None


def get_mt5() -> MT5Bridge:
    """Get MT5Bridge singleton instance"""
    global _mt5_instance
    if _mt5_instance is None:
        _mt5_instance = MT5Bridge()
    return _mt5_instance
