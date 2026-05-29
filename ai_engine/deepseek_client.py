"""
DeepSeek AI Client - عميل الذكاء الاصطناعي DeepSeek
=====================================================
يدعم نماذج: deepseek-chat, deepseek-reasoner
"""
import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI

from config import config
from utils.logger import get_logger

logger = get_logger(__name__)


class DeepSeekClient:
    """عميل التواصل مع DeepSeek API"""

    SYSTEM_PROMPT = """أنت محلل أسواق مالية محترف ومتخصص في تحليل تداول الفوركس والذهب.
    
    مهمتك هي تحليل بيانات السوق المقدمة وإعطاء توصيات تداول دقيقة.

    يجب أن يكون ردك بصيغة JSON فقط بدون أي نص آخر، بهذا الشكل:
    {
        "direction": "buy" أو "sell" أو "hold",
        "confidence": نسبة الثقة من 0 إلى 100,
        "reasoning": "شرح مختصر للتحليل بالعربية (جملتين إلى ثلاث)",
        "entry_price": سعر الدخول المقترح (رقم),
        "stop_loss": سعر إيقاف الخسارة (رقم),
        "take_profit": سعر جني الأرباح (رقم)
    }

    قم بالتحليل بناءً على:
    - المؤشرات الفنية (RSI, MACD, EMA, Bollinger Bands, ADX)
    - حركة السعر وأنماط الشموع
    - مستويات الدعم والمقاومة
    - الاتجاه العام (ترند)
    - التقلبات (ATR)

    كن دقيقاً وحذراً. لا تعطي توصية إلا إذا كنت واثقاً منها."""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or config.deepseek.api_key
        self.model = model or config.deepseek.model
        self.base_url = config.deepseek.base_url
        self.max_tokens = config.deepseek.max_tokens
        self.temperature = config.deepseek.temperature

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        logger.info(f"🤖 DeepSeek client initialized | Model: {self.model}")

    def analyze_market(self, symbol: str, timeframe: str,
                       market_data: Dict[str, Any],
                       news_context: Optional[str] = None) -> Dict[str, Any]:
        """
        تحليل السوق باستخدام DeepSeek AI

        Args:
            symbol: رمز الأصل (XAUUSD, EURUSD, etc.)
            timeframe: الإطار الزمني (M15, H1, D1)
            market_data: بيانات السوق والمؤشرات الفنية
            news_context: سياق الأخبار (اختياري)

        Returns:
            Dict: توصية التداول
        """
        # بناء prompt التحليل
        prompt = self._build_analysis_prompt(symbol, timeframe, market_data, news_context)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature,
            )

            result_text = response.choices[0].message.content.strip()
            logger.debug(f"DeepSeek raw response: {result_text}")

            # استخراج JSON من الرد
            analysis = self._parse_response(result_text)
            analysis["raw_response"] = result_text
            analysis["model_used"] = self.model
            analysis["timestamp"] = market_data.get("timestamp", "")

            logger.info(
                f"📊 AI Analysis: {symbol} | "
                f"Direction: {analysis.get('direction')} | "
                f"Confidence: {analysis.get('confidence')}%"
            )

            return analysis

        except Exception as e:
            logger.error(f"❌ DeepSeek API error: {e}")
            return {
                "direction": "hold",
                "confidence": 0,
                "reasoning": f"خطأ في التحليل: {str(e)}",
                "entry_price": 0,
                "stop_loss": 0,
                "take_profit": 0,
                "error": str(e),
            }

    def analyze_news_impact(self, news_data: List[Dict]) -> Dict[str, Any]:
        """
        تحليل تأثير الأخبار الاقتصادية على السوق

        Args:
            news_data: قائمة الأخبار الاقتصادية

        Returns:
            Dict: تحليل تأثير الأخبار
        """
        if not news_data:
            return {"high_impact": False, "reason": "لا توجد أخبار مهمة حالياً", "events": []}

        prompt = f"""حلل الأخبار الاقتصادية التالية وحدد مدى تأثيرها على تداول الفوركس والذهب:

        {json.dumps(news_data, ensure_ascii=False, indent=2)}

        رد بصيغة JSON فقط:
        {{
            "high_impact": true/false (هل هناك أخبار عالية التأثير قريبة؟),
            "should_pause": true/false (هل يجب إيقاف التداول مؤقتاً؟),
            "reason": "شرح مختصر بالعربية",
            "events": قائمة بالأخبار المؤثرة
        }}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "أنت محلل أخبار اقتصادية محترف."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=1000,
                temperature=0.2,
            )

            result = self._parse_response(response.choices[0].message.content.strip())
            logger.info(f"📰 News analysis: High impact={'Yes' if result.get('high_impact') else 'No'}")
            return result

        except Exception as e:
            logger.error(f"❌ News analysis error: {e}")
            return {"high_impact": False, "reason": f"خطأ: {e}", "events": []}

    def backtest_signal(self, symbol: str, historical_data: str,
                        expected_result: str) -> Dict[str, Any]:
        """
        اختبار إشارة على بيانات تاريخية (Backtest)

        Args:
            symbol: رمز الأصل
            historical_data: بيانات تاريخية
            expected_result: النتيجة المتوقعة

        Returns:
            Dict: نتيجة الاختبار
        """
        prompt = f"""قم بتحليل بيانات السوق التاريخية التالية لـ {symbol}:

        {historical_data}

        بناءً على هذه البيانات، هل كانت ستوصي بـ:
        1. شراء (buy)
        2. بيع (sell)
        3. عدم الدخول (hold)

        النتيجة الفعلية كانت: {expected_result}

        رد بصيغة JSON: {{"signal": "buy/sell/hold", "was_correct": true/false, "accuracy_comment": "تعليق"}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "أنت مختبر استراتيجيات تداول."},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=500,
                temperature=0.1,
            )

            return self._parse_response(response.choices[0].message.content.strip())

        except Exception as e:
            logger.error(f"❌ Backtest error: {e}")
            return {"error": str(e)}

    def _build_analysis_prompt(self, symbol: str, timeframe: str,
                               market_data: Dict, news_context: Optional[str]) -> str:
        """بناء نص التحليل لـ DeepSeek"""
        prompt_parts = [
            f"قم بتحليل {symbol} على الإطار الزمني {timeframe}.",
            "",
            "📊 بيانات السوق والمؤشرات الفنية:",
            json.dumps(market_data, ensure_ascii=False, indent=2),
        ]

        if news_context:
            prompt_parts.extend([
                "",
                "📰 سياق الأخبار الاقتصادية:",
                news_context,
            ])

        prompt_parts.extend([
            "",
            "⚠️ تذكر: رد بصيغة JSON فقط كما هو محدد في تعليمات النظام.",
        ])

        return "\n".join(prompt_parts)

    def _parse_response(self, text: str) -> Dict[str, Any]:
        """استخراج JSON من رد DeepSeek"""
        # محاولة استخراج JSON مباشرة
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # محاولة استخراج JSON من بين علامات الكود
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # محاولة إيجاد JSON في النص
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        logger.warning(f"⚠️ Could not parse JSON from response: {text[:200]}")
        return {
            "direction": "hold",
            "confidence": 0,
            "reasoning": "تعذر تحليل الرد من DeepSeek",
            "entry_price": 0,
            "stop_loss": 0,
            "take_profit": 0,
        }

    def chat(self, user_message: str, system_prompt: str = None) -> str:
        """محادثة عامة مع DeepSeek (للاستفسارات)"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt or "أنت مساعد تداول ذكي ومحترف."
                    },
                    {"role": "user", "content": user_message},
                ],
                max_tokens=1500,
                temperature=0.5,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"❌ DeepSeek chat error: {e}")
            return f"عذراً، حدث خطأ في الاتصال بـ DeepSeek: {e}"

    def test_connection(self) -> bool:
        """اختبار الاتصال بـ DeepSeek API"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello, respond with 'OK'."}],
                max_tokens=10,
            )
            return bool(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"❌ DeepSeek connection test failed: {e}")
            return False
