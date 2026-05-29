"""
Market Analyzer
================
Combines MT5 data, calculates indicators, and feeds DeepSeek AI
"""
from datetime import datetime
from typing import Optional, Dict, List, Any
import pandas as pd

from config import config
from utils.logger import get_logger
from .indicators import TechnicalIndicators
from .deepseek_client import DeepSeekClient

logger = get_logger(__name__)


class MarketAnalyzer:
    """Comprehensive market analyzer"""

    def __init__(self, mt5_bridge=None, deepseek_client: DeepSeekClient = None):
        self.mt5 = mt5_bridge  # MT5Bridge instance
        self.deepseek = deepseek_client or DeepSeekClient()
        self.indicators = TechnicalIndicators()

    def analyze(self, symbol: str, timeframe: str = None,
                bars_count: int = None, user_id: int = None) -> Dict[str, Any]:
        """
        Comprehensive market analysis

        Args:
            symbol: Asset symbol
            timeframe: Timeframe
            bars_count: Number of candles required
            user_id: User ID (for AI settings)

        Returns:
            Dict: Complete analysis with recommendation
        """
        timeframe = timeframe or config.ai.prediction_timeframe
        bars_count = bars_count or config.ai.max_historical_bars

        logger.info(f"🔍 Analyzing {symbol} on {timeframe}...")

        # 1. Fetch market data from MT5
        market_data = self._fetch_market_data(symbol, timeframe, bars_count)

        if market_data is None:
            return {
                "error": True,
                "message": f"❌ Could not fetch data for {symbol}. Check MT5 connection.",
                "direction": "hold",
                "confidence": 0,
            }

        # 2. Calculate technical indicators
        indicators_data = self.indicators.get_all_indicators(market_data["df"])

        # 3. Prepare analysis payload for DeepSeek
        analysis_payload = {
            "symbol": symbol,
            "timeframe": timeframe,
            "timestamp": datetime.utcnow().isoformat(),
            "indicators": indicators_data,
            "price_summary": {
                "current": market_data["current_price"],
                "open": market_data["open_price"],
                "high": market_data["high_price"],
                "low": market_data["low_price"],
                "spread": market_data.get("spread", 0),
                "change_24h": market_data.get("change_24h", 0),
            },
            "volume": market_data.get("volume", 0),
        }

        # 4. Analyze news if enabled
        news_context = None
        if config.ai.news_check_enabled and user_id:
            from database.db_manager import get_db
            db = get_db()
            ai_cfg = db.get_ai_config(user_id)
            if ai_cfg.news_check_enabled:
                news_context = self._get_news_context(symbol)

        # 5. Call DeepSeek AI
        ai_result = self.deepseek.analyze_market(
            symbol=symbol,
            timeframe=timeframe,
            market_data=analysis_payload,
            news_context=news_context,
        )

        # 6. Merge results
        result = {
            **ai_result,
            "symbol": symbol,
            "timeframe": timeframe,
            "indicators": indicators_data,
            "news_checked": news_context is not None,
        }

        return result

    def quick_scan(self, symbols: List[str] = None) -> List[Dict]:
        """
        Quick scan of multiple assets

        Args:
            symbols: List of symbols (None = all)

        Returns:
            List: Scan results per asset
        """
        if symbols is None:
            symbols = list(config.symbols.keys())

        results = []
        for symbol in symbols:
            try:
                # Quick price fetch only
                if self.mt5:
                    tick = self.mt5.get_tick(symbol)
                    price = tick.get("bid", 0) if tick else 0
                else:
                    price = 0

                results.append({
                    "symbol": symbol,
                    "name": config.symbols.get(symbol, symbol),
                    "price": price,
                    "trend": "sideways",
                })
            except Exception as e:
                logger.warning(f"Quick scan error for {symbol}: {e}")
                results.append({
                    "symbol": symbol,
                    "name": config.symbols.get(symbol, symbol),
                    "price": 0,
                    "error": str(e),
                })

        return results

    def _fetch_market_data(self, symbol: str, timeframe: str,
                           bars_count: int) -> Optional[Dict]:
        """Fetch market data from MT5"""
        if not self.mt5:
            logger.warning("MT5 bridge not connected, using simulated data")
            return self._simulate_market_data(symbol, bars_count)

        try:
            # Fetch candles
            rates = self.mt5.get_rates(symbol, timeframe, bars_count)
            if rates is None or len(rates) == 0:
                logger.warning(f"No rates data for {symbol}")
                return None

            df = pd.DataFrame(rates)
            df.columns = ["time", "open", "high", "low", "close", "tick_volume",
                         "spread", "real_volume"]

            # Get current price
            tick = self.mt5.get_tick(symbol) or {}
            current_price = tick.get("bid", df["close"].iloc[-1])

            # Calculate daily change
            daily_change = (current_price - df["open"].iloc[-1]) / df["open"].iloc[-1] * 100

            return {
                "df": df,
                "current_price": current_price,
                "open_price": float(df["open"].iloc[-1]),
                "high_price": float(df["high"].iloc[-1]),
                "low_price": float(df["low"].iloc[-1]),
                "spread": tick.get("spread", 0),
                "change_24h": round(daily_change, 2),
                "volume": int(df["tick_volume"].sum()),
            }

        except Exception as e:
            logger.error(f"❌ Error fetching market data: {e}")
            return None

    def _simulate_market_data(self, symbol: str, bars: int) -> Dict:
        """Simulate market data for testing (no MT5)"""
        import numpy as np

        # Approximate prices for testing
        base_prices = {
            "XAUUSD": 2345.50,
            "EURUSD": 1.0850,
            "GBPUSD": 1.2650,
            "USDJPY": 151.50,
            "BTCUSD": 67500.00,
        }

        base = base_prices.get(symbol, 1.0)
        volatility = 0.002  # 0.2%

        np.random.seed(hash(symbol) % 2**32)

        # Generate realistic random price movement
        returns = np.random.normal(0, volatility, bars)
        price_path = base * np.exp(np.cumsum(returns))

        # Create candles
        dates = pd.date_range(end=datetime.utcnow(), periods=bars, freq="15min")
        df = pd.DataFrame({
            "time": dates,
            "open": price_path,
            "high": price_path * (1 + np.abs(np.random.normal(0, volatility/2, bars))),
            "low": price_path * (1 - np.abs(np.random.normal(0, volatility/2, bars))),
            "close": price_path * (1 + np.random.normal(0, volatility/3, bars)),
            "tick_volume": np.random.randint(100, 1000, bars),
            "spread": np.full(bars, 2),
            "real_volume": np.random.randint(50, 500, bars),
        })

        current_price = df["close"].iloc[-1]
        daily_change = (current_price - df["open"].iloc[-1]) / df["open"].iloc[-1] * 100

        return {
            "df": df,
            "current_price": current_price,
            "open_price": float(df["open"].iloc[-1]),
            "high_price": float(df["high"].iloc[-1]),
            "low_price": float(df["low"].iloc[-1]),
            "spread": 2,
            "change_24h": round(daily_change, 2),
            "volume": int(df["tick_volume"].sum()),
        }

    def _get_news_context(self, symbol: str) -> Optional[str]:
        """
        Fetch economic news context
        (Can be connected to APIs like ForexFactory or Investing.com)
        """
        # TODO: Connect real news API
        # Currently returns None since no API is connected
        return None
