"""
DeepSeek AI Client
==================
Supports models: deepseek-chat, deepseek-reasoner
"""
import json
import re
from typing import Optional, Dict, Any, List
from openai import OpenAI

from config import config
from utils.logger import get_logger

logger = get_logger(__name__)


class DeepSeekClient:
    """DeepSeek API client"""

    SYSTEM_PROMPT = """You are a professional financial markets analyst specializing in Forex and Gold trading.
    
    Your task is to analyze the provided market data and give accurate trading recommendations.

    Respond ONLY with a JSON object in this exact format, no other text:
    {
        "direction": "buy" or "sell" or "hold",
        "confidence": confidence percentage from 0 to 100,
        "reasoning": "brief analysis explanation (2-3 sentences)",
        "entry_price": suggested entry price (number),
        "stop_loss": stop loss price (number),
        "take_profit": take profit price (number)
    }

    Base your analysis on:
    - Technical indicators (RSI, MACD, EMA, Bollinger Bands, ADX)
    - Price action and candlestick patterns
    - Support and resistance levels
    - Overall trend direction
    - Volatility (ATR)

    Be precise and cautious. Only give a recommendation if you are confident about it."""

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
        Analyze market using DeepSeek AI

        Args:
            symbol: Asset symbol (XAUUSD, EURUSD, etc.)
            timeframe: Timeframe (M15, H1, D1)
            market_data: Market data and technical indicators
            news_context: News context (optional)

        Returns:
            Dict: Trading recommendation
        """
        # Build analysis prompt
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

            # Extract JSON from response
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
                "reasoning": f"Analysis error: {str(e)}",
                "entry_price": 0,
                "stop_loss": 0,
                "take_profit": 0,
                "error": str(e),
            }

    def analyze_news_impact(self, news_data: List[Dict]) -> Dict[str, Any]:
        """
        Analyze economic news impact on the market

        Args:
            news_data: List of economic news items

        Returns:
            Dict: News impact analysis
        """
        if not news_data:
            return {"high_impact": False, "reason": "No significant news at this time", "events": []}

        prompt = f"""Analyze the following economic news and determine its impact on Forex and Gold trading:

        {json.dumps(news_data, ensure_ascii=False, indent=2)}

        Respond with JSON only:
        {{
            "high_impact": true/false (are there high-impact news events nearby?),
            "should_pause": true/false (should trading be temporarily paused?),
            "reason": "brief explanation",
            "events": list of impactful events
        }}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional economic news analyst."},
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
            return {"high_impact": False, "reason": f"Error: {e}", "events": []}

    def backtest_signal(self, symbol: str, historical_data: str,
                        expected_result: str) -> Dict[str, Any]:
        """
        Test a signal on historical data (Backtest)

        Args:
            symbol: Asset symbol
            historical_data: Historical market data
            expected_result: Expected outcome

        Returns:
            Dict: Backtest result
        """
        prompt = f"""Analyze the following historical market data for {symbol}:

        {historical_data}

        Based on this data, would you have recommended:
        1. Buy
        2. Sell
        3. Hold (no entry)

        The actual result was: {expected_result}

        Respond with JSON: {{"signal": "buy/sell/hold", "was_correct": true/false, "accuracy_comment": "comment"}}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a trading strategy tester."},
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
        """Build the analysis prompt for DeepSeek"""
        prompt_parts = [
            f"Analyze {symbol} on {timeframe} timeframe.",
            "",
            "📊 Market Data & Technical Indicators:",
            json.dumps(market_data, ensure_ascii=False, indent=2),
        ]

        if news_context:
            prompt_parts.extend([
                "",
                "📰 Economic News Context:",
                news_context,
            ])

        prompt_parts.extend([
            "",
            "⚠️ Remember: Respond with JSON only as specified in the system instructions.",
        ])

        return "\n".join(prompt_parts)

    def _parse_response(self, text: str) -> Dict[str, Any]:
        """Extract JSON from DeepSeek response"""
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try extracting from code blocks
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding any JSON in text
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
            "reasoning": "Could not parse DeepSeek response",
            "entry_price": 0,
            "stop_loss": 0,
            "take_profit": 0,
        }

    def chat(self, user_message: str, system_prompt: str = None) -> str:
        """General chat with DeepSeek (for inquiries)"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt or "You are a smart and professional trading assistant."
                    },
                    {"role": "user", "content": user_message},
                ],
                max_tokens=1500,
                temperature=0.5,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"❌ DeepSeek chat error: {e}")
            return f"Sorry, an error occurred connecting to DeepSeek: {e}"

    def test_connection(self) -> bool:
        """Test DeepSeek API connection"""
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
