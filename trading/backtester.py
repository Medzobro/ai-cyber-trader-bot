"""
Backtester Engine
=================
Strategy backtesting on historical data using indicators and optional AI.
Supports real data via yfinance with synthetic fallback.
"""
import json
import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from config import config
from utils.logger import get_logger
from ai_engine.indicators import TechnicalIndicators
from ai_engine.predictor import AIPredictor
from trading.risk_manager import RiskManager

logger = get_logger(__name__)

# Symbol → yfinance ticker mapping
YF_TICKERS = {
    "XAUUSD": "GC=F",
    "EURUSD": "EURUSD=X",
    "GBPUSD": "GBPUSD=X",
    "USDJPY": "USDJPY=X",
    "BTCUSD": "BTC-USD",
    "US30": "^DJI",
    "NAS100": "^IXIC",
}

# Symbol → contract size (units per lot)
CONTRACT_SIZE = {
    "XAUUSD": 100,      # 100 oz per lot
    "EURUSD": 100_000,
    "GBPUSD": 100_000,
    "USDJPY": 100_000,
    "BTCUSD": 1,
    "US30": 1,
    "NAS100": 1,
}

# Timeframe → yfinance interval
YF_INTERVALS = {
    "M5": "5m",
    "M15": "15m",
    "M30": "30m",
    "H1": "1h",
    "H4": "4h",
    "D1": "1d",
}

# Minimum bars required for indicator warm-up
MIN_BARS = 250


@dataclass
class SimulatedTrade:
    """A single simulated trade"""
    id: int
    symbol: str
    direction: str          # buy | sell
    open_bar: int
    open_price: float
    volume: float
    stop_loss: float
    take_profit: float
    close_bar: Optional[int] = None
    close_price: Optional[float] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    exit_reason: str = ""   # tp | sl | close


@dataclass
class BacktestResult:
    """Backtest result container"""
    success: bool = True
    message: str = ""

    symbol: str = ""
    timeframe: str = ""
    strategy: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    initial_balance: float = 10_000.0
    final_balance: float = 10_000.0

    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_return_pct: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    avg_trade_return: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0

    equity_curve: List[float] = field(default_factory=list)
    trades: List[SimulatedTrade] = field(default_factory=list)
    equity_timestamps: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "strategy": self.strategy,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "initial_balance": self.initial_balance,
            "final_balance": self.final_balance,
            "total_return_pct": self.total_return_pct,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate,
            "profit_factor": self.profit_factor,
            "max_drawdown_pct": self.max_drawdown_pct,
            "sharpe_ratio": self.sharpe_ratio,
            "sortino_ratio": self.sortino_ratio,
            "avg_trade_return": self.avg_trade_return,
            "avg_win": self.avg_win,
            "avg_loss": self.avg_loss,
            "largest_win": self.largest_win,
            "largest_loss": self.largest_loss,
        }


class Backtester:
    """
    Bar-by-bar backtest engine.

    Supports two signal strategies:
      - "indicators": Fast, free. Uses AIPredictor._preliminary_analysis().
      - "ai": Slow, costs API credits. Uses full MarketAnalyzer + AI provider.
    """

    def __init__(self, predictor: AIPredictor = None,
                 risk_manager: RiskManager = None):
        self.predictor = predictor or AIPredictor()
        self.risk = risk_manager
        self.indicators = TechnicalIndicators()

    # ─── Public API ───────────────────────────────

    def run(self, symbol: str, timeframe: str = "D1",
            strategy: str = "indicators",
            start_days: int = 365,
            initial_balance: float = 10_000.0,
            volume: float = 0.1,
            commission_per_lot: float = 10.0,
            user_id: int = None) -> BacktestResult:
        """
        Run a complete backtest.

        Args:
            symbol: Trading symbol (e.g., XAUUSD)
            timeframe: M5, M15, M30, H1, H4, D1
            strategy: "indicators" or "ai"
            start_days: How many days of history to fetch
            initial_balance: Starting capital
            volume: Lot size per trade
            user_id: For AI strategy API key lookup

        Returns:
            BacktestResult
        """
        # Cap start_days for yfinance intraday limits
        capped_start_days = start_days
        if timeframe in ("M5", "M15", "M30", "H1"):
            capped_start_days = min(start_days, 60)
        elif timeframe == "H4":
            capped_start_days = min(start_days, 60)

        logger.info(
            f"🧪 Backtest started: {symbol}/{timeframe} | "
            f"Strategy={strategy} | Days={capped_start_days}"
        )

        result = BacktestResult(
            symbol=symbol,
            timeframe=timeframe,
            strategy=strategy,
            initial_balance=initial_balance,
        )

        # 1. Fetch data
        df = self._fetch_data(symbol, timeframe, capped_start_days)
        if df is None or len(df) < MIN_BARS:
            result.success = False
            result.message = (
                f"❌ Insufficient data for backtest. "
                f"Got {len(df) if df is not None else 0} bars, need {MIN_BARS}."
            )
            logger.error(result.message)
            return result

        result.start_date = df.index[0].to_pydatetime()
        result.end_date = df.index[-1].to_pydatetime()

        # 2. Simulate
        try:
            result = self._simulate(
                df=df,
                result=result,
                strategy=strategy,
                volume=volume,
                commission_per_lot=commission_per_lot,
                user_id=user_id,
            )
        except Exception as e:
            logger.error(f"Backtest simulation error: {e}")
            result.success = False
            result.message = f"Simulation error: {e}"
            return result

        # 3. Calculate metrics
        self._calculate_metrics(result)

        logger.info(
            f"🧪 Backtest complete: {result.total_trades} trades | "
            f"Return={result.total_return_pct:.2f}% | "
            f"WinRate={result.win_rate:.1f}% | "
            f"MaxDD={result.max_drawdown_pct:.2f}%"
        )
        return result

    # ─── Data Fetching ────────────────────────────

    def _fetch_data(self, symbol: str, timeframe: str,
                    start_days: int) -> Optional[pd.DataFrame]:
        """Fetch historical OHLCV data."""
        # Try yfinance first
        df = self._fetch_yfinance(symbol, timeframe, start_days)
        if df is not None and len(df) >= MIN_BARS:
            return df

        # Fallback: synthetic data
        logger.warning("yfinance unavailable or returned insufficient data; using synthetic fallback")
        return self._generate_synthetic_data(symbol, timeframe, start_days)

    def _fetch_yfinance(self, symbol: str, timeframe: str,
                        start_days: int) -> Optional[pd.DataFrame]:
        """Fetch from Yahoo Finance via yfinance."""
        try:
            import yfinance as yf
        except ImportError:
            return None

        ticker = YF_TICKERS.get(symbol, symbol)
        interval = YF_INTERVALS.get(timeframe, "1d")

        # yfinance intraday limits: 5m/15m/30m/1h = max 60 days; 4h not supported directly
        if interval == "4h":
            # Fetch 1h and resample to 4h
            period = min(start_days, 60)
            df = yf.download(ticker, period=f"{period}d", interval="1h", progress=False)
            if df is None or df.empty:
                return None
            df = df.resample("4h").agg({
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            }).dropna()
        else:
            period = f"{start_days}d" if start_days <= 60 else f"{min(start_days, 730)}d"
            df = yf.download(ticker, period=period, interval=interval, progress=False)

        if df is None or df.empty:
            return None

        # Standardize column names (yfinance returns MultiIndex sometimes)
        df.columns = [c.lower() for c in df.columns]
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # Ensure required columns exist
        for col in ["open", "high", "low", "close"]:
            if col not in df.columns:
                logger.warning(f"yfinance data missing column: {col}")
                return None

        # Rename to match our convention
        df = df.rename(columns={
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
        })
        df["volume"] = df.get("volume", 0)

        return df

    def _generate_synthetic_data(self, symbol: str, timeframe: str,
                                 start_days: int) -> pd.DataFrame:
        """Generate realistic synthetic OHLCV data with trend regimes."""
        np.random.seed(hash(symbol + timeframe) % 2**32)

        # Determine bar count and volatility from symbol
        base_prices = {
            "XAUUSD": 2345.0,
            "EURUSD": 1.0850,
            "GBPUSD": 1.2650,
            "USDJPY": 151.50,
            "BTCUSD": 67500.0,
            "US30": 39000.0,
            "NAS100": 16800.0,
        }
        base = base_prices.get(symbol, 100.0)
        volatility = 0.0015 if symbol in ("EURUSD", "GBPUSD", "USDJPY") else 0.003
        if symbol == "BTCUSD":
            volatility = 0.015

        # Number of bars
        if timeframe == "D1":
            bars = start_days
            freq = "D"
        elif timeframe == "H4":
            bars = start_days * 6
            freq = "4h"
        elif timeframe == "H1":
            bars = start_days * 24
            freq = "h"
        elif timeframe in ("M15", "M30"):
            bars_per_day = 24 * 4 if timeframe == "M15" else 24 * 2
            bars = start_days * bars_per_day
            freq = "15min" if timeframe == "M15" else "30min"
        elif timeframe == "M5":
            bars = start_days * 24 * 12
            freq = "5min"
        else:
            bars = start_days
            freq = "D"

        bars = max(bars, MIN_BARS)

        # Create regimes: bull (positive drift), bear (negative drift), sideways
        # Split into ~3-5 regimes
        regime_count = max(3, bars // 60)
        regime_lengths = np.random.multinomial(bars, [1.0 / regime_count] * regime_count)
        regime_drifts = np.random.choice([-0.0008, -0.0003, 0.0001, 0.0005, 0.0010], size=regime_count)

        returns = []
        for length, drift in zip(regime_lengths, regime_drifts):
            returns.extend(np.random.normal(drift, volatility, length))
        returns = np.array(returns)

        price_path = base * np.exp(np.cumsum(returns))

        dates = pd.date_range(end=datetime.utcnow(), periods=bars, freq=freq)

        # Generate OHLC around close
        noise_high = np.abs(np.random.normal(0, volatility * 0.6, bars))
        noise_low = np.abs(np.random.normal(0, volatility * 0.6, bars))
        noise_open = np.random.normal(0, volatility * 0.3, bars)

        close = price_path
        high = close * (1 + noise_high)
        low = close * (1 - noise_low)
        open_ = close * (1 + noise_open)
        # Ensure OHLC consistency
        high = np.maximum(high, np.maximum(open_, close))
        low = np.minimum(low, np.minimum(open_, close))

        df = pd.DataFrame({
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": np.random.randint(100, 5000, bars),
        }, index=dates)

        return df

    # ─── Simulation ───────────────────────────────

    def _simulate(self, df: pd.DataFrame, result: BacktestResult,
                  strategy: str, volume: float, commission_per_lot: float,
                  user_id: int) -> BacktestResult:
        """Bar-by-bar walk-forward simulation."""
        balance = result.initial_balance
        equity = balance
        equity_curve = [balance]
        equity_timestamps = [df.index[0].isoformat()]

        trades: List[SimulatedTrade] = []
        open_trade: Optional[SimulatedTrade] = None
        trade_id = 0

        # Pre-calculate contract size
        contract_size = CONTRACT_SIZE.get(result.symbol, 100_000)

        for i in range(MIN_BARS, len(df)):
            bar = df.iloc[i]
            prev_bar = df.iloc[i - 1]
            timestamp = df.index[i]

            # Update equity curve every bar (mark-to-market for open trade)
            if open_trade:
                mark_price = bar["close"]
                if open_trade.direction == "buy":
                    unrealized = (mark_price - open_trade.open_price) * volume * contract_size
                else:
                    unrealized = (open_trade.open_price - mark_price) * volume * contract_size
                equity = balance + unrealized
            else:
                equity = balance

            equity_curve.append(equity)
            equity_timestamps.append(timestamp.isoformat())

            # Check SL/TP for open trade using current bar's high/low
            if open_trade:
                exited = False
                exit_price = None
                exit_reason = ""

                if open_trade.direction == "buy":
                    # SL hit first if low <= SL
                    if bar["low"] <= open_trade.stop_loss:
                        exited = True
                        exit_price = open_trade.stop_loss
                        exit_reason = "sl"
                    elif bar["high"] >= open_trade.take_profit:
                        exited = True
                        exit_price = open_trade.take_profit
                        exit_reason = "tp"
                else:  # sell
                    if bar["high"] >= open_trade.stop_loss:
                        exited = True
                        exit_price = open_trade.stop_loss
                        exit_reason = "sl"
                    elif bar["low"] <= open_trade.take_profit:
                        exited = True
                        exit_price = open_trade.take_profit
                        exit_reason = "tp"

                if exited:
                    # Calculate PnL
                    if open_trade.direction == "buy":
                        price_diff = exit_price - open_trade.open_price
                    else:
                        price_diff = open_trade.open_price - exit_price

                    pnl = price_diff * volume * contract_size
                    pnl_pct = (pnl / result.initial_balance) * 100

                    open_trade.close_bar = i
                    open_trade.close_price = exit_price
                    # Deduct commission (round-trip: open + close)
                    commission = commission_per_lot * volume
                    pnl -= commission

                    open_trade.pnl = pnl
                    open_trade.pnl_pct = (pnl / result.initial_balance) * 100
                    open_trade.exit_reason = exit_reason

                    balance += pnl
                    trades.append(open_trade)
                    open_trade = None

            # Generate signal if no open trade
            if not open_trade:
                signal = self._get_signal(df, i, strategy, result.symbol, user_id)
                direction = signal.get("direction", "hold")
                confidence = signal.get("confidence", 0)

                min_confidence = 20 if strategy == "indicators" else 50
                if direction in ("buy", "sell") and confidence >= min_confidence:
                    entry_price = bar["close"]
                    sl = signal.get("stop_loss", 0)
                    tp = signal.get("take_profit", 0)

                    if sl <= 0 or tp <= 0:
                        # Fallback SL/TP via predictor
                        indicators = signal.get("_indicators", {})
                        atr = indicators.get("atr", entry_price * 0.01)
                        if direction == "buy":
                            sl = entry_price - (atr * 1.5)
                            tp = entry_price + (atr * 2.5)
                        else:
                            sl = entry_price + (atr * 1.5)
                            tp = entry_price - (atr * 2.5)

                    trade_id += 1
                    open_trade = SimulatedTrade(
                        id=trade_id,
                        symbol=result.symbol,
                        direction=direction,
                        open_bar=i,
                        open_price=round(entry_price, 5),
                        volume=volume,
                        stop_loss=round(sl, 5),
                        take_profit=round(tp, 5),
                    )

        # Close any remaining open trade at last price
        if open_trade:
            last_price = df["close"].iloc[-1]
            if open_trade.direction == "buy":
                price_diff = last_price - open_trade.open_price
            else:
                price_diff = open_trade.open_price - last_price

            # Deduct commission for final close
            commission = commission_per_lot * volume
            pnl = price_diff * volume * contract_size - commission
            pnl_pct = (pnl / result.initial_balance) * 100

            open_trade.close_bar = len(df) - 1
            open_trade.close_price = round(last_price, 5)
            open_trade.pnl = pnl
            open_trade.pnl_pct = pnl_pct
            open_trade.exit_reason = "close"
            trades.append(open_trade)
            balance += pnl

        result.final_balance = balance
        result.equity_curve = equity_curve
        result.equity_timestamps = equity_timestamps
        result.trades = trades
        return result

    def _get_signal(self, df: pd.DataFrame, i: int, strategy: str,
                    symbol: str, user_id: int) -> Dict[str, Any]:
        """Generate a trading signal for bar i."""
        df_slice = df.iloc[:i + 1]

        # Compute indicators
        indicators = self.indicators.get_all_indicators(df_slice)

        # Build minimal market_data dict for predictor
        market_data = {
            "indicators": indicators,
            "direction": "hold",
            "confidence": 0,
            "entry_price": 0,
            "stop_loss": 0,
            "take_profit": 0,
        }

        if strategy == "ai":
            # Full AI prediction (requires API key; expensive)
            prediction = self.predictor.predict(symbol, market_data, user_id)
            return {
                "direction": prediction.get("ai_analysis", "hold"),
                "confidence": prediction.get("ai_confidence", 0),
                "stop_loss": prediction.get("stop_loss", 0),
                "take_profit": prediction.get("take_profit", 0),
                "_indicators": indicators,
            }
        else:
            # Indicator-only (fast, free)
            prelim = self.predictor._preliminary_analysis(indicators)
            direction = prelim.get("direction", "hold")
            confidence = prelim.get("confidence", 0)

            # Build a temporary result dict for SL/TP calculation
            temp_result = {
                "ai_analysis": direction,
                "entry_price": 0,
                "stop_loss": 0,
                "take_profit": 0,
                "current_price": indicators.get("current_price", 0),
            }
            self.predictor._adjust_entry_exit(temp_result, indicators)

            return {
                "direction": direction,
                "confidence": confidence,
                "stop_loss": temp_result.get("stop_loss", 0),
                "take_profit": temp_result.get("take_profit", 0),
                "_indicators": indicators,
            }

    # ─── Metrics ──────────────────────────────────

    def _calculate_metrics(self, result: BacktestResult):
        """Calculate performance metrics from simulation results."""
        trades = result.trades
        result.total_trades = len(trades)

        if result.total_trades == 0:
            result.message = "No trades were generated during the backtest period."
            return

        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl < 0]
        result.winning_trades = len(wins)
        result.losing_trades = len(losses)
        result.win_rate = (result.winning_trades / result.total_trades * 100) if result.total_trades > 0 else 0

        total_profit = sum(t.pnl for t in wins)
        total_loss = abs(sum(t.pnl for t in losses))
        result.profit_factor = (total_profit / total_loss) if total_loss > 0 else float("inf")
        result.total_return_pct = ((result.final_balance - result.initial_balance) / result.initial_balance) * 100

        result.avg_win = (total_profit / len(wins)) if wins else 0
        result.avg_loss = (total_loss / len(losses)) if losses else 0
        result.avg_trade_return = (sum(t.pnl for t in trades) / len(trades))
        result.largest_win = max((t.pnl for t in wins), default=0)
        result.largest_loss = min((t.pnl for t in losses), default=0)

        # Max drawdown
        peak = result.initial_balance
        max_dd = 0
        for val in result.equity_curve:
            if val > peak:
                peak = val
            dd = (peak - val) / peak
            if dd > max_dd:
                max_dd = dd
        result.max_drawdown_pct = max_dd * 100

        # Sharpe ratio (daily returns approximation)
        returns = []
        for i in range(1, len(result.equity_curve)):
            r = (result.equity_curve[i] - result.equity_curve[i - 1]) / result.equity_curve[i - 1]
            returns.append(r)

        if len(returns) > 1:
            avg_ret = np.mean(returns)
            std_ret = np.std(returns)
            # Annualized Sharpe (assume 252 trading days)
            periods_per_day = self._periods_per_day(result.timeframe)
            if std_ret > 0 and periods_per_day > 0:
                result.sharpe_ratio = (avg_ret / std_ret) * math.sqrt(periods_per_day * 252)
            else:
                result.sharpe_ratio = 0

            # Sortino (downside deviation only)
            downside = [r for r in returns if r < 0]
            downside_std = np.std(downside) if downside else 0
            if downside_std > 0 and periods_per_day > 0:
                result.sortino_ratio = (avg_ret / downside_std) * math.sqrt(periods_per_day * 252)
            else:
                result.sortino_ratio = 0

    @staticmethod
    def _periods_per_day(timeframe: str) -> int:
        """Approximate number of bars per trading day for annualization."""
        mapping = {
            "M5": 24 * 12,
            "M15": 24 * 4,
            "M30": 24 * 2,
            "H1": 24,
            "H4": 6,
            "D1": 1,
        }
        return mapping.get(timeframe, 1)

    # ─── Utility ──────────────────────────────────

    @staticmethod
    def serialize_for_db(result: BacktestResult) -> Dict[str, Any]:
        """Serialize result for database storage."""
        return {
            **result.to_dict(),
            "equity_curve": json.dumps(result.equity_curve[:500]),  # Limit stored size
            "trades_json": json.dumps([
                {
                    "id": t.id,
                    "direction": t.direction,
                    "open_price": t.open_price,
                    "close_price": t.close_price,
                    "pnl": t.pnl,
                    "pnl_pct": t.pnl_pct,
                    "exit_reason": t.exit_reason,
                }
                for t in result.trades
            ]),
        }
