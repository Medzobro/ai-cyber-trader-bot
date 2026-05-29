"""
AI Predictor - متنبئ الذكاء الاصطناعي
====================================
يدمج بين المؤشرات الفنية و ML و DeepSeek للتوقع
"""
from typing import Dict, Optional, List
from datetime import datetime
import numpy as np

from config import config
from utils.logger import get_logger
from database.db_manager import get_db
from .deepseek_client import DeepSeekClient
from .indicators import TechnicalIndicators

logger = get_logger(__name__)

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False
    logger.warning("XGBoost not installed, ML predictions disabled")

try:
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class AIPredictor:
    """متنبئ متكامل يجمع بين DeepSeek AI و ML"""

    def __init__(self, deepseek_client: DeepSeekClient = None):
        self.deepseek = deepseek_client or DeepSeekClient()
        self.indicators = TechnicalIndicators()
        self.ml_model = None
        self.scaler = None
        self.is_trained = False

    def predict(self, symbol: str, market_data: Dict,
                user_id: Optional[int] = None) -> Dict:
        """
        التنبؤ بحركة السوق

        Args:
            symbol: رمز الأصل
            market_data: بيانات السوق من MarketAnalyzer
            user_id: معرف المستخدم

        Returns:
            Dict: توصية التداول
        """
        # 1. جلب إعدادات AI للمستخدم
        confidence_threshold = config.ai.confidence_threshold
        if user_id:
            db = get_db()
            ai_cfg = db.get_ai_config(user_id)
            confidence_threshold = ai_cfg.confidence_threshold

        # 2. تحليل DeepSeek AI
        indicators = market_data.get("indicators", {})

        # 3. تحليل ML (إذا متاح)
        ml_prediction = self._ml_predict(indicators)

        # 4. تحليل مبسط مبدئي (قبل DeepSeek)
        preliminary = self._preliminary_analysis(indicators)

        # 5. دمج النتائج
        result = {
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
            "current_price": indicators.get("current_price", 0),
            "ai_analysis": market_data.get("direction", "hold"),
            "ai_confidence": market_data.get("confidence", 0),
            "ai_reasoning": market_data.get("reasoning", ""),
            "ml_prediction": ml_prediction,
            "preliminary": preliminary,
            "confidence_threshold": confidence_threshold,
            "passed_threshold": (market_data.get("confidence", 0) >= confidence_threshold),
            "entry_price": market_data.get("entry_price", 0),
            "stop_loss": market_data.get("stop_loss", 0),
            "take_profit": market_data.get("take_profit", 0),
        }

        # 6. تعديل نقاط الدخول/الخروج إذا لم يحددها DeepSeek
        self._adjust_entry_exit(result, indicators)

        return result

    def _preliminary_analysis(self, indicators: Dict) -> Dict:
        """
        تحليل مبدئي سريع (بدون AI)

        يعطي إشارة سريعة بناءً على المؤشرات فقط
        """
        signals = []
        score = 0  # -100 to +100

        rsi = indicators.get("rsi")
        if rsi is not None:
            if rsi < 30:
                signals.append("RSI: تشبع بيع (شراء)")
                score += 20
            elif rsi > 70:
                signals.append("RSI: تشبع شراء (بيع)")
                score -= 20
            else:
                score += (50 - rsi) * 0.5  # ميل طفيف

        macd_hist = indicators.get("macd_histogram")
        if macd_hist is not None:
            if macd_hist > 0:
                signals.append("MACD: إيجابي")
                score += 15
            else:
                signals.append("MACD: سلبي")
                score -= 15

        trend = indicators.get("trend")
        if trend == "up":
            signals.append("الاتجاه: صاعد")
            score += 20
        elif trend == "down":
            signals.append("الاتجاه: هابط")
            score -= 20

        adx = indicators.get("adx")
        if adx is not None:
            if adx > 25:
                signals.append(f"ADX: اتجاه قوي ({adx:.0f})")
                score += 10 * (1 if score > 0 else -1)
            else:
                signals.append(f"ADX: سوق متذبذب ({adx:.0f})")

        bb_percent = indicators.get("bb_percent")
        if bb_percent is not None:
            if bb_percent < 0.1:
                signals.append("BB: السعر عند الحد السفلي (شراء محتمل)")
                score += 15
            elif bb_percent > 0.9:
                signals.append("BB: السعر عند الحد العلوي (بيع محتمل)")
                score -= 15

        candlestick = indicators.get("candlestick_patterns", [])
        for pattern in candlestick:
            if "Bullish" in pattern:
                score += 10
                signals.append(f"نمط: {pattern}")
            elif "Bearish" in pattern:
                score -= 10
                signals.append(f"نمط: {pattern}")
            else:
                signals.append(f"نمط: {pattern}")

        # تحديد الاتجاه المبدئي
        if score > 25:
            direction = "buy"
        elif score < -25:
            direction = "sell"
        else:
            direction = "hold"

        # تحويل score إلى نسبة ثقة تقريبية
        confidence = min(abs(score), 95)

        return {
            "direction": direction,
            "score": score,
            "confidence": round(confidence, 1),
            "signals": signals,
            "signal_count": len(signals),
        }

    def _ml_predict(self, indicators: Dict) -> Optional[Dict]:
        """
        تنبؤ باستخدام نموذج ML (XGBoost)

        ملاحظة: يحتاج تدريب مسبق على بيانات تاريخية
        """
        if not HAS_XGBOOST or not self.is_trained:
            return None

        try:
            # استخراج features
            features = np.array([[
                indicators.get("rsi", 50),
                indicators.get("macd_histogram", 0),
                indicators.get("adx", 20),
                indicators.get("stoch_k", 50),
                indicators.get("bb_percent", 0.5),
                1 if indicators.get("trend") == "up" else (
                    -1 if indicators.get("trend") == "down" else 0
                ),
                indicators.get("atr", 0),
            ]])

            if self.scaler:
                features = self.scaler.transform(features)

            proba = self.ml_model.predict_proba(features)[0]
            # افتراض: classes = [down, hold, up]
            if len(proba) == 3:
                label = ["sell", "hold", "buy"][np.argmax(proba)]
                confidence = np.max(proba) * 100
            else:
                label = "hold"
                confidence = 0

            return {
                "direction": label,
                "confidence": round(confidence, 1),
                "probabilities": [round(p * 100, 1) for p in proba],
            }
        except Exception as e:
            logger.warning(f"ML prediction error: {e}")
            return None

    def train_ml_model(self, historical_data: List[Dict]):
        """
        تدريب نموذج ML على بيانات تاريخية

        Args:
            historical_data: قائمة صفقات تاريخية مع مؤشراتها
        """
        if not HAS_XGBOOST:
            logger.warning("XGBoost not installed, cannot train")
            return

        if len(historical_data) < 50:
            logger.warning("Need at least 50 historical trades for training")
            return

        try:
            X, y = [], []
            for trade in historical_data:
                ind = trade.get("indicators", {})
                X.append([
                    ind.get("rsi", 50),
                    ind.get("macd_histogram", 0),
                    ind.get("adx", 20),
                    ind.get("stoch_k", 50),
                    ind.get("bb_percent", 0.5),
                    1 if ind.get("trend") == "up" else (
                        -1 if ind.get("trend") == "down" else 0
                    ),
                    ind.get("atr", 0),
                ])
                # 0=sell, 1=hold, 2=buy
                direction_map = {"sell": 0, "hold": 1, "buy": 2}
                y.append(direction_map.get(trade.get("result", "hold"), 1))

            X = np.array(X)
            y = np.array(y)

            self.scaler = StandardScaler()
            X = self.scaler.fit_transform(X)

            self.ml_model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=4,
                learning_rate=0.1,
                objective="multi:softprob",
                num_class=3,
                random_state=42,
            )
            self.ml_model.fit(X, y)
            self.is_trained = True

            logger.info(f"✅ ML model trained on {len(historical_data)} samples")

        except Exception as e:
            logger.error(f"❌ ML training error: {e}")

    def _adjust_entry_exit(self, result: Dict, indicators: Dict):
        """
        تعديل وحساب نقاط الدخول والخروج إذا لم يحددها AI
        """
        current_price = indicators.get("current_price", result.get("current_price", 0))
        atr = indicators.get("atr", current_price * 0.01)

        direction = result.get("ai_analysis", "hold")

        # إذا لم يحدد DeepSeek نقاط دخول/خروج
        if result.get("entry_price", 0) <= 0:
            result["entry_price"] = current_price

        if result.get("stop_loss", 0) <= 0:
            if direction == "buy":
                result["stop_loss"] = current_price - (atr * 1.5)
            elif direction == "sell":
                result["stop_loss"] = current_price + (atr * 1.5)
            else:
                result["stop_loss"] = 0

        if result.get("take_profit", 0) <= 0:
            if direction == "buy":
                result["take_profit"] = current_price + (atr * 2.5)
            elif direction == "sell":
                result["take_profit"] = current_price - (atr * 2.5)
            else:
                result["take_profit"] = 0

        result["entry_price"] = round(result["entry_price"], 5)
        result["stop_loss"] = round(result["stop_loss"], 5)
        result["take_profit"] = round(result["take_profit"], 5)
