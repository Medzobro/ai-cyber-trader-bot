"""
Market Analyzer
================
Combines MT5 data, calculates indicators, and feeds AI (multi-provider via AIManager)
"""
from datetime import datetime
from typing import Optional, Dict, List, Any
import pandas as pd

from config import config
from utils.logger import get_logger
from .indicators import TechnicalIndicators
from .ai_manager import AIManager

logger = get_logger(__name__)


class MarketAnalyzer:
    """Comprehensive market analyzer with multi-provider AI support"""

    def __init__(self, mt5_bridge=None, ai_manager: AIManager = None,
                 news_scraper=None):
        self.mt5 = mt5_bridge  # MT5Bridge instance
        self.ai_manager = ai_manager  # AIManager (factory)
        self.news_scraper = news_scraper  # NewsScraper instance
        self.indicators = TechnicalIndicators()

    def analyze(self, symbol: str, timeframe: str = None,
                bars_count: int = None, user_id: int = None) -> Dict[str, Any]:
        """
        Comprehensive market analysis using the user's chosen AI provider.

        Args:
            symbol: Asset symbol
            timeframe: Timeframe
            bars_count: Number of candles required
            user_id: User ID (for AI provider settings + API key)

        Returns:
            Dict: Complete analysis with recommendation
        """
        timeframe = timeframe or config.ai.prediction_timeframe
        bars_count = bars_count or config.ai.max_historical_bars

        logger.info(f"Analyzing {symbol} on {timeframe}...")

        # 1. Fetch market data from MT5
        market_data = self._fetch_market_data(symbol, timeframe, bars_count)

        if market_data is None:
            return {
                "error": True,
                "message": f"Could not fetch data for {symbol}. Check MT5 connection.",
                "direction": "hold",
                "confidence": 0,
            }

        # 2. Calculate technical indicators
        indicators_data = self.indicators.get_all_indicators(market_data["df"])

        # 3. Prepare analysis payload for AI
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

        # 4. Fetch news context (if news scraper is available)
        news_context = None
        if self.news_scraper:
            try:
                # Check if AI config has news enabled
                if user_id:
                    from database.db_manager import get_db
                    db = get_db()
                    ai_cfg = db.get_ai_config(user_id)
                    if ai_cfg.news_check_enabled:
                        news_context = self.news_scraper.format_news_context(symbol)
                        if news_context:
                            logger.debug(f"News context: {news_context[:100]}...")
            except Exception as e:
                logger.warning(f"News fetch error: {e}")

        # 5. Get the user's AI client via AIManager (multi-provider)
        ai_result = self._call_ai(symbol, timeframe, analysis_payload,
                                  news_context, user_id)

        # 6. Merge results
        result = {
            **ai_result,
            "symbol": symbol,
            "timeframe": timeframe,
            "indicators": indicators_data,
            "news_checked": news_context is not None,
        }

        return result

    def _call_ai(self, symbol: str, timeframe: str,
                 market_data: Dict, news_context: Optional[str],
                 user_id: Optional[int]) -> Dict:
        """
        Call the appropriate AI provider for the user.

        Uses AIManager factory to create the correct client based on
        the user's stored provider and API key.
        """
        if not self.ai_manager:
            # Fallback: try old DeepSeekClient
            try:
                from .deepseek_client import DeepSeekClient
                client = DeepSeekClient()
                return client.analyze_market(
                    symbol=symbol, timeframe=timeframe,
                    market_data=market_data, news_context=news_context,
                )
            except Exception as e:
                logger.error(f"AI fallback error: {e}")
                return self._error_result(f"AI not available: {e}")

        if not user_id:
            return self._error_result("User ID required for AI analysis")

        try:
            from database.db_manager import get_db
            from utils.security import decrypt_api_key

            db = get_db()

            # Get user's active AI provider
            provider = db.get_user_provider(user_id)
            if not provider:
                return self._error_result(
                    "No AI provider configured. Please set up your API key in AI Settings."
                )

            # Get decrypted API key (in RAM only - never logged)
            api_key = db.get_decrypted_api_key(user_id, provider)
            if not api_key:
                return self._error_result(
                    f"API key for {provider} not found. Please set your key in AI Settings."
                )

            # Get user's preferred model
            provider_record = None
            user_keys = db.get_user_api_keys(user_id)
            for k in user_keys:
                if k["provider"] == provider:
                    provider_record = k
                    break
            model = provider_record.get("model") if provider_record else None

            # Create AI client via factory
            client = AIManager.get_client(provider, api_key, model)

            # Analyze with news context if available
            return client.analyze(symbol, timeframe, market_data, news_context)

        except Exception as e:
            # Check for rate limit / quota errors
            error_str = str(e).lower()
            if any(kw in error_str for kw in ("quota", "rate limit", "exceeded",
                                               "insufficient", "billing")):
                logger.error(f"AI quota/rate limit for user {user_id}: {e}")
                return {
                    "direction": "hold", "confidence": 0,
                    "reasoning": f"AI quota exceeded. Please check your billing: {e}",
                    "entry_price": 0, "stop_loss": 0, "take_profit": 0,
                    "error": "QUOTA_EXCEEDED", "should_stop": True,
                }

            logger.error(f"AI analysis error for user {user_id}: {e}")
            return self._error_result(f"AI error: {e}")

    def _error_result(self, message: str) -> Dict:
        """Create an error result"""
        return {
            "error": True,
            "message": message,
            "direction": "hold",
            "confidence": 0,
            "reasoning": message,
            "entry_price": 0,
            "stop_loss": 0,
            "take_profit": 0,
        }

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
            logger.error(f"Error fetching market data: {e}")
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
