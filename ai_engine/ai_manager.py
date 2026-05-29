"""
AI Manager - Factory Pattern
=============================
Multi-provider AI client supporting OpenAI GPT, Google Gemini, Anthropic Claude, and DeepSeek.
Each user brings their own API key and selects their preferred model.
"""
import json
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from enum import Enum

from utils.logger import get_logger
from utils.security import decrypt_api_key

logger = get_logger(__name__)


class AIProvider(str, Enum):
    """Supported AI providers"""
    OPENAI = "openai"
    GEMINI = "gemini"
    CLAUDE = "claude"
    DEEPSEEK = "deepseek"


# Provider metadata for the UI (string keys for easy lookup from callbacks)
PROVIDER_INFO = {
    "openai": {
        "name": "OpenAI GPT",
        "emoji": "🧠",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        "default_model": "gpt-4o-mini",
        "key_prefix": "sk-",
        "key_url": "https://platform.openai.com/api-keys",
    },
    "gemini": {
        "name": "Google Gemini",
        "emoji": "💎",
        "models": ["gemini-2.0-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        "default_model": "gemini-2.0-flash",
        "key_prefix": "AIza",
        "key_url": "https://aistudio.google.com/app/apikey",
    },
    "claude": {
        "name": "Anthropic Claude",
        "emoji": "🔮",
        "models": ["claude-3-5-sonnet-20241022", "claude-3-opus-20240229", "claude-3-haiku-20240307"],
        "default_model": "claude-3-5-sonnet-20241022",
        "key_prefix": "sk-ant-",
        "key_url": "https://console.anthropic.com/settings/keys",
    },
    "deepseek": {
        "name": "DeepSeek AI",
        "emoji": "🤖",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "default_model": "deepseek-chat",
        "key_prefix": "sk-",
        "key_url": "https://platform.deepseek.com/api_keys",
    },
}


class BaseAIClient(ABC):
    """Abstract base for all AI providers"""

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

    def __init__(self, api_key: str, model: str = None):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def analyze(self, symbol: str, timeframe: str, market_data: Dict,
                news_context: Optional[str] = None) -> Dict[str, Any]:
        """Analyze market and return trading recommendation"""
        pass

    @abstractmethod
    def test_connection(self) -> bool:
        """Test the API connection with a lightweight ping"""
        pass

    @abstractmethod
    def get_credit_info(self) -> Dict[str, Any]:
        """Get remaining credits/quota info"""
        pass

    def _parse_json_response(self, text: str) -> Dict[str, Any]:
        """Extract JSON from AI response"""
        # Try direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try code blocks
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Try any JSON object in text
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return {"direction": "hold", "confidence": 0,
                "reasoning": "Could not parse response", "entry_price": 0,
                "stop_loss": 0, "take_profit": 0}


# ─── OpenAI Client ────────────────────────────────────

class OpenAIClient(BaseAIClient):
    """OpenAI GPT client"""

    def __init__(self, api_key: str, model: str = None):
        super().__init__(api_key, model or "gpt-4o-mini")
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key)
        logger.info(f"OpenAI client initialized | Model: {self.model}")

    def analyze(self, symbol, timeframe, market_data, news_context=None):
        prompt = self._build_prompt(symbol, timeframe, market_data, news_context)
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2000,
                temperature=0.3,
            )
            text = response.choices[0].message.content.strip()
            result = self._parse_json_response(text)
            result["model_used"] = self.model
            result["provider"] = "openai"
            return result
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return self._error_result(str(e))

    def test_connection(self) -> bool:
        try:
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return True
        except Exception as e:
            logger.error(f"OpenAI test failed: {e}")
            return False

    def get_credit_info(self) -> Dict:
        return {"provider": "openai", "note": "Check usage at platform.openai.com/usage"}

    def _build_prompt(self, symbol, timeframe, data, news=None):
        parts = [
            f"Analyze {symbol} on {timeframe} timeframe.",
            "", "Market Data:", json.dumps(data, indent=2),
        ]
        if news:
            parts.extend(["", "Economic News:", news])
        return "\n".join(parts)

    def _error_result(self, msg):
        return {"direction": "hold", "confidence": 0, "reasoning": f"Error: {msg}",
                "entry_price": 0, "stop_loss": 0, "take_profit": 0, "error": msg}


# ─── Gemini Client ────────────────────────────────────

class GeminiClient(BaseAIClient):
    """Google Gemini client"""

    def __init__(self, api_key: str, model: str = None):
        super().__init__(api_key, model or "gemini-2.0-flash")
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.genai = genai
            self.gmodel = genai.GenerativeModel(self.model)
        except ImportError:
            self.gmodel = None
            logger.warning("google-generativeai not installed. Gemini unavailable.")
        logger.info(f"Gemini client initialized | Model: {self.model}")

    def analyze(self, symbol, timeframe, market_data, news_context=None):
        if not self.gmodel:
            return self._error_result("Gemini SDK not installed")
        prompt = (
            f"{self.SYSTEM_PROMPT}\n\n"
            f"Analyze {symbol} on {timeframe}:\n"
            f"{json.dumps(market_data, indent=2)}\n"
            + (f"\nNews: {news_context}" if news_context else "")
        )
        try:
            response = self.gmodel.generate_content(prompt)
            text = response.text.strip()
            result = self._parse_json_response(text)
            result["model_used"] = self.model
            result["provider"] = "gemini"
            return result
        except Exception as e:
            # Check for rate limit / quota errors
            error_str = str(e).lower()
            if "quota" in error_str or "rate" in error_str or "exceeded" in error_str:
                logger.error(f"Gemini rate/quota limit: {e}")
                return {"direction": "hold", "confidence": 0,
                        "reasoning": "Gemini API quota exceeded. Please check your billing.",
                        "entry_price": 0, "stop_loss": 0, "take_profit": 0,
                        "error": "QUOTA_EXCEEDED", "should_stop": True}
            logger.error(f"Gemini error: {e}")
            return self._error_result(str(e))

    def test_connection(self) -> bool:
        if not self.gmodel:
            return False
        try:
            response = self.gmodel.generate_content("Respond with: OK")
            return bool(response.text)
        except Exception as e:
            logger.error(f"Gemini test failed: {e}")
            return False

    def get_credit_info(self) -> Dict:
        return {"provider": "gemini", "note": "Check quota at aistudio.google.com"}

    def _error_result(self, msg):
        return {"direction": "hold", "confidence": 0, "reasoning": f"Error: {msg}",
                "entry_price": 0, "stop_loss": 0, "take_profit": 0, "error": msg}


# ─── Claude Client ────────────────────────────────────

class ClaudeClient(BaseAIClient):
    """Anthropic Claude client"""

    def __init__(self, api_key: str, model: str = None):
        super().__init__(api_key, model or "claude-3-5-sonnet-20241022")
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
        except ImportError:
            self.client = None
            logger.warning("anthropic not installed. Claude unavailable.")
        logger.info(f"Claude client initialized | Model: {self.model}")

    def analyze(self, symbol, timeframe, market_data, news_context=None):
        if not self.client:
            return self._error_result("Anthropic SDK not installed")
        prompt = (
            f"Analyze {symbol} on {timeframe}:\n"
            f"{json.dumps(market_data, indent=2)}\n"
            + (f"\nNews: {news_context}" if news_context else "")
        )
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.3,
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            text = response.content[0].text.strip()
            result = self._parse_json_response(text)
            result["model_used"] = self.model
            result["provider"] = "claude"
            return result
        except Exception as e:
            logger.error(f"Claude error: {e}")
            return self._error_result(str(e))

    def test_connection(self) -> bool:
        if not self.client:
            return False
        try:
            self.client.messages.create(
                model=self.model, max_tokens=10,
                messages=[{"role": "user", "content": "ping"}],
            )
            return True
        except Exception as e:
            logger.error(f"Claude test failed: {e}")
            return False

    def get_credit_info(self) -> Dict:
        return {"provider": "claude", "note": "Check usage at console.anthropic.com"}


# ─── DeepSeek Client (wraps existing) ─────────────────

class DeepSeekClientV2(BaseAIClient):
    """DeepSeek client (updated to work with the factory)"""

    def __init__(self, api_key: str, model: str = None):
        super().__init__(api_key, model or "deepseek-chat")
        from openai import OpenAI
        self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
        logger.info(f"DeepSeek client initialized | Model: {self.model}")

    def analyze(self, symbol, timeframe, market_data, news_context=None):
        prompt = (
            f"Analyze {symbol} on {timeframe}:\n"
            f"{json.dumps(market_data, indent=2)}\n"
            + (f"\nNews: {news_context}" if news_context else "")
        )
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=2000,
                temperature=0.3,
            )
            text = response.choices[0].message.content.strip()
            result = self._parse_json_response(text)
            result["model_used"] = self.model
            result["provider"] = "deepseek"
            return result
        except Exception as e:
            logger.error(f"DeepSeek error: {e}")
            return self._error_result(str(e))

    def test_connection(self) -> bool:
        try:
            self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=5,
            )
            return True
        except Exception as e:
            logger.error(f"DeepSeek test failed: {e}")
            return False

    def get_credit_info(self) -> Dict:
        return {"provider": "deepseek", "note": "Check balance at platform.deepseek.com"}


# ─── Factory ──────────────────────────────────────────

class AIManager:
    """
    Factory Pattern AI Manager.
    
    Routes analysis requests to the correct provider based on user settings.
    Each user's API key is encrypted in the DB, decrypted momentarily in RAM,
    used for the API call, and then discarded.
    """

    # Client mapping
    _CLIENTS = {
        AIProvider.OPENAI: OpenAIClient,
        AIProvider.GEMINI: GeminiClient,
        AIProvider.CLAUDE: ClaudeClient,
        AIProvider.DEEPSEEK: DeepSeekClientV2,
    }

    @classmethod
    def get_client(cls, provider: str, api_key: str, model: str = None) -> BaseAIClient:
        """
        Create AI client based on provider.
        
        Args:
            provider: 'openai', 'gemini', 'claude', or 'deepseek'
            api_key: Decrypted API key (plaintext, for RAM use only)
            model: Optional model override
            
        Returns:
            BaseAIClient instance
            
        Raises:
            ValueError: Unknown provider
        """
        provider = AIProvider(provider)
        client_class = cls._CLIENTS.get(provider)
        if client_class is None:
            raise ValueError(f"Unknown AI provider: {provider}")
        return client_class(api_key, model)

    @classmethod
    def validate_key(cls, provider: str, api_key: str) -> Dict[str, Any]:
        """
        Validate an API key by making a lightweight ping request.
        
        Args:
            provider: AI provider name
            api_key: Decrypted API key to validate
            
        Returns:
            Dict with 'valid', 'provider', 'message', 'model'
        """
        provider = AIProvider(provider)
        info = PROVIDER_INFO.get(provider.value, {})
        try:
            client = cls.get_client(provider, api_key)
            is_valid = client.test_connection()
            credit_info = client.get_credit_info() if is_valid else {}

            return {
                "valid": is_valid,
                "provider": provider.value,
                "provider_name": info.get("name", provider.value),
                "message": "✅ API key is valid" if is_valid else "❌ Invalid API key",
                "credit": credit_info,
            }
        except Exception as e:
            return {
                "valid": False,
                "provider": provider.value,
                "message": f"❌ Validation error: {str(e)}",
            }

    @classmethod
    def get_available_providers(cls) -> List[Dict]:
        """Get list of all available AI providers for the UI"""
        return [
            {
                "id": pid,
                "name": info["name"],
                "emoji": info["emoji"],
                "models": info["models"],
                "default_model": info["default_model"],
                "key_url": info["key_url"],
            }
            for pid, info in PROVIDER_INFO.items()
        ]
