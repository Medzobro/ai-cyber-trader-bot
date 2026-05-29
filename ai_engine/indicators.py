"""
Technical Indicators - المؤشرات الفنية
======================================
حساب المؤشرات الفنية باستخدام pandas و numpy
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from utils.logger import get_logger

logger = get_logger(__name__)


class TechnicalIndicators:
    """حساب المؤشرات الفنية للتداول"""

    @staticmethod
    def rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """
        مؤشر القوة النسبية (RSI)

        RSI > 70: تشبع شراء (Overbought)
        RSI < 30: تشبع بيع (Oversold)
        """
        delta = prices.diff()
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)

        avg_gain = gain.ewm(com=period - 1, adjust=False).mean()
        avg_loss = loss.ewm(com=period - 1, adjust=False).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - (100 / (1 + rs))
        return rsi

    @staticmethod
    def macd(prices: pd.Series, fast: int = 12, slow: int = 26,
             signal: int = 9) -> Dict[str, pd.Series]:
        """
        مؤشر MACD (المتوسط المتحرك المتقارب المتباعد)

        Returns:
            Dict with 'macd', 'signal', 'histogram'
        """
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line

        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram,
        }

    @staticmethod
    def ema(prices: pd.Series, period: int) -> pd.Series:
        """المتوسط المتحرك الأسي (EMA)"""
        return prices.ewm(span=period, adjust=False).mean()

    @staticmethod
    def sma(prices: pd.Series, period: int) -> pd.Series:
        """المتوسط المتحرك البسيط (SMA)"""
        return prices.rolling(window=period).mean()

    @staticmethod
    def bollinger_bands(prices: pd.Series, period: int = 20,
                        std_dev: float = 2.0) -> Dict[str, pd.Series]:
        """
        مؤشر بولينجر (Bollinger Bands)

        Returns:
            Dict with 'upper', 'middle', 'lower', 'bandwidth', 'percent_b'
        """
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()

        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        bandwidth = (upper - lower) / middle * 100
        percent_b = (prices - lower) / (upper - lower)

        return {
            "upper": upper,
            "middle": middle,
            "lower": lower,
            "bandwidth": bandwidth,
            "percent_b": percent_b,
        }

    @staticmethod
    def atr(high: pd.Series, low: pd.Series, close: pd.Series,
            period: int = 14) -> pd.Series:
        """
        متوسط المدى الحقيقي (ATR) - مقياس التقلب
        """
        prev_close = close.shift(1)

        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.ewm(span=period, adjust=False).mean()

        return atr

    @staticmethod
    def adx(high: pd.Series, low: pd.Series, close: pd.Series,
            period: int = 14) -> Dict[str, pd.Series]:
        """
        مؤشر متوسط الحركة الاتجاهية (ADX)

        ADX > 25: اتجاه قوي
        ADX < 20: سوق متذبذب

        Returns:
            Dict with 'adx', 'plus_di', 'minus_di'
        """
        prev_high = high.shift(1)
        prev_low = low.shift(1)
        prev_close = close.shift(1)

        up_move = high - prev_high
        down_move = prev_low - low

        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

        plus_dm = pd.Series(plus_dm, index=high.index)
        minus_dm = pd.Series(minus_dm, index=high.index)

        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs()
        ], axis=1).max(axis=1)

        atr = tr.ewm(span=period, adjust=False).mean()

        plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)

        dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
        adx = dx.ewm(span=period, adjust=False).mean()

        return {
            "adx": adx,
            "plus_di": plus_di,
            "minus_di": minus_di,
        }

    @staticmethod
    def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                   k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """
        مؤشر ستوكاستيك (Stochastic Oscillator)

        Returns:
            Dict with 'k', 'd'
        """
        lowest_low = low.rolling(window=k_period).min()
        highest_high = high.rolling(window=k_period).max()

        k = 100 * (close - lowest_low) / (highest_high - lowest_low)
        d = k.rolling(window=d_period).mean()

        return {"k": k, "d": d}

    @staticmethod
    def support_resistance(high: pd.Series, low: pd.Series, close: pd.Series,
                           window: int = 20, threshold: float = 0.02) -> Dict:
        """
        تحديد مستويات الدعم والمقاومة

        Returns:
            Dict with 'support', 'resistance', 'pivot'
        """
        # استخدام أعلى وأدنى نقاط في النافذة
        resistance_levels = []
        support_levels = []

        for i in range(window, len(high) - window):
            if high.iloc[i] == high.iloc[i-window:i+window+1].max():
                resistance_levels.append(high.iloc[i])
            if low.iloc[i] == low.iloc[i-window:i+window+1].min():
                support_levels.append(low.iloc[i])

        # تجميع المستويات القريبة
        def cluster_levels(levels: List[float], threshold: float) -> List[float]:
            if not levels:
                return []
            levels = sorted(set(levels))
            clusters = [[levels[0]]]
            for lvl in levels[1:]:
                if lvl - clusters[-1][-1] <= threshold * lvl:
                    clusters[-1].append(lvl)
                else:
                    clusters.append([lvl])
            return [np.mean(c) for c in clusters]

        resistance = cluster_levels(resistance_levels, threshold)
        support = cluster_levels(support_levels, threshold)
        pivot = (close.iloc[-1] + high.iloc[-1] + low.iloc[-1]) / 3

        return {
            "support": support,
            "resistance": resistance,
            "pivot": pivot,
        }

    @staticmethod
    def trend_direction(prices: pd.Series, short_period: int = 20,
                        long_period: int = 50) -> str:
        """
        تحديد اتجاه الترند

        Returns: 'up', 'down', 'sideways'
        """
        if len(prices) < long_period:
            return "sideways"

        ema_short = prices.ewm(span=short_period, adjust=False).mean()
        ema_long = prices.ewm(span=long_period, adjust=False).mean()

        if ema_short.iloc[-1] > ema_long.iloc[-1] * 1.001:
            return "up"
        elif ema_short.iloc[-1] < ema_long.iloc[-1] * 0.999:
            return "down"
        else:
            return "sideways"

    @staticmethod
    def candlestick_pattern(open_: pd.Series, high: pd.Series,
                            low: pd.Series, close: pd.Series) -> List[str]:
        """
        اكتشاف أنماط الشموع

        Returns: قائمة بالأنماط المكتشفة
        """
        patterns = []

        if len(close) < 3:
            return patterns

        body = (close - open_).abs()
        upper_shadow = high - close.clip(lower=open_)
        lower_shadow = open_.clip(lower=close) - low

        # Doji (شمعة دوجي)
        last_body = body.iloc[-1]
        last_range = high.iloc[-1] - low.iloc[-1]
        if last_range > 0 and last_body / last_range < 0.1:
            patterns.append("Doji ⏸️")

        # Hammer (المطرقة)
        last_lower = lower_shadow.iloc[-1]
        if last_range > 0 and last_lower > last_body * 2 and upper_shadow.iloc[-1] < last_body * 0.5:
            patterns.append("Hammer 🔨")

        # Shooting Star (النجمة الهابطة)
        last_upper = upper_shadow.iloc[-1]
        if last_range > 0 and last_upper > last_body * 2 and lower_shadow.iloc[-1] < last_body * 0.5:
            patterns.append("Shooting Star ⭐")

        # Engulfing (الابتلاع)
        if len(body) >= 2:
            prev_body = body.iloc[-2]
            prev_close = close.iloc[-2]
            prev_open = open_.iloc[-2]
            curr_close = close.iloc[-1]
            curr_open = open_.iloc[-1]

            # Bullish Engulfing
            if (prev_close < prev_open and
                curr_close > curr_open and
                curr_close > prev_open and
                curr_open < prev_close):
                patterns.append("Bullish Engulfing 🟢")

            # Bearish Engulfing
            if (prev_close > prev_open and
                curr_close < curr_open and
                curr_close < prev_open and
                curr_open > prev_close):
                patterns.append("Bearish Engulfing 🔴")

        return patterns

    def get_all_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        حساب جميع المؤشرات من DataFrame

        Args:
            df: DataFrame مع أعمدة 'open', 'high', 'low', 'close', 'volume' (اختياري)

        Returns:
            Dict: جميع المؤشرات كقيم مفردة (أحدث قيمة)
        """
        close = df["close"]
        high = df["high"]
        low = df["low"]
        open_ = df["open"]

        # RSI
        rsi_val = self.rsi(close).iloc[-1]

        # MACD
        macd_data = self.macd(close)
        macd_val = macd_data["macd"].iloc[-1]
        signal_val = macd_data["signal"].iloc[-1]
        histogram_val = macd_data["histogram"].iloc[-1]

        # Moving Averages
        ema_9 = self.ema(close, 9).iloc[-1]
        ema_20 = self.ema(close, 20).iloc[-1]
        sma_50 = self.sma(close, 50).iloc[-1]
        sma_200 = self.sma(close, 200).iloc[-1] if len(close) >= 200 else None

        # Bollinger Bands
        bb_data = self.bollinger_bands(close)
        bb_upper = bb_data["upper"].iloc[-1]
        bb_middle = bb_data["middle"].iloc[-1]
        bb_lower = bb_data["lower"].iloc[-1]
        bb_percent = bb_data["percent_b"].iloc[-1]

        # ATR
        atr_val = self.atr(high, low, close).iloc[-1]

        # ADX
        adx_data = self.adx(high, low, close)
        adx_val = adx_data["adx"].iloc[-1]

        # Stochastic
        stoch_data = self.stochastic(high, low, close)
        stoch_k = stoch_data["k"].iloc[-1]

        # Support & Resistance
        sr_data = self.support_resistance(high, low, close)

        # Trend
        trend = self.trend_direction(close)

        # Candlestick patterns
        patterns = self.candlestick_pattern(open_, high, low, close)

        current_price = close.iloc[-1]

        return {
            "current_price": round(current_price, 5),
            "rsi": round(rsi_val, 2) if not np.isnan(rsi_val) else None,
            "macd": round(macd_val, 5) if not np.isnan(macd_val) else None,
            "macd_signal": round(signal_val, 5) if not np.isnan(signal_val) else None,
            "macd_histogram": round(histogram_val, 5) if not np.isnan(histogram_val) else None,
            "ema_9": round(ema_9, 5) if not np.isnan(ema_9) else None,
            "ema_20": round(ema_20, 5) if not np.isnan(ema_20) else None,
            "sma_50": round(sma_50, 5) if not np.isnan(sma_50) else None,
            "sma_200": round(sma_200, 5) if sma_200 and not np.isnan(sma_200) else None,
            "bb_upper": round(bb_upper, 5) if not np.isnan(bb_upper) else None,
            "bb_middle": round(bb_middle, 5) if not np.isnan(bb_middle) else None,
            "bb_lower": round(bb_lower, 5) if not np.isnan(bb_lower) else None,
            "bb_percent": round(bb_percent, 4) if not np.isnan(bb_percent) else None,
            "atr": round(atr_val, 5) if not np.isnan(atr_val) else None,
            "adx": round(adx_val, 2) if not np.isnan(adx_val) else None,
            "stoch_k": round(stoch_k, 2) if not np.isnan(stoch_k) else None,
            "support_levels": [round(s, 5) for s in sr_data["support"][:3]],
            "resistance_levels": [round(r, 5) for r in sr_data["resistance"][:3]],
            "pivot": round(sr_data["pivot"], 5),
            "trend": trend,
            "candlestick_patterns": patterns,
            "bars_analyzed": len(df),
        }
