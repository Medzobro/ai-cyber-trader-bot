"""
AI Cyber-Trader Bot - Configuration
====================================
All centralized project settings
"""
import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class TelegramConfig:
    """Telegram bot settings"""
    bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
    admin_ids: List[int] = field(default_factory=lambda: [
        int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x
    ])


@dataclass
class DeepSeekConfig:
    """DeepSeek AI settings"""
    api_key: str = os.getenv("DEEPSEEK_API_KEY", "YOUR_DEEPSEEK_API_KEY")
    base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    max_tokens: int = 2000
    temperature: float = 0.3


@dataclass
class GitHubConfig:
    """GitHub API settings"""
    token: str = os.getenv("GITHUB_TOKEN", "")
    base_url: str = os.getenv("GITHUB_BASE_URL", "https://api.github.com")
    username: str = os.getenv("GITHUB_USERNAME", "")


@dataclass
class TradingConfig:
    """Trading settings"""
    # MT5 Connection
    mt5_login: int = int(os.getenv("MT5_LOGIN", "0"))
    mt5_password: str = os.getenv("MT5_PASSWORD", "")
    mt5_server: str = os.getenv("MT5_SERVER", "ICMarkets-Demo")

    # Default trading parameters
    default_symbol: str = "XAUUSD"
    default_lot: float = 0.01
    default_direction: str = "both"  # buy, sell, both
    max_lot: float = 1.0
    min_lot: float = 0.01

    # Risk Management
    max_daily_loss: float = 5.0  # percentage
    max_open_trades: int = 3
    stop_loss_pips: int = 500
    take_profit_pips: int = 800
    trailing_stop_pips: int = 300

    # Trading hours (UTC)
    trading_start_hour: int = 0
    trading_end_hour: int = 23


@dataclass
class AIConfig:
    """AI settings - Multi-provider"""
    confidence_threshold: float = 70.0  # minimum confidence threshold (%)
    analysis_mode: str = "predictive"  # predictive, news_scanning, hybrid
    news_check_enabled: bool = True
    backtest_mode: bool = False
    prediction_timeframe: str = "M15"  # M5, M15, H1, H4, D1
    max_historical_bars: int = 1000
    
    # Multi-provider defaults (users can override with their own keys)
    default_provider: str = "deepseek"  # openai, gemini, claude, deepseek
    
    # Encryption
    encryption_secret: str = os.getenv(
        "ENCRYPTION_SECRET",
        "ai-cyber-trader-default-secret-change-in-production"
    )
    
    indicators: List[str] = field(default_factory=lambda: [
        "RSI", "MACD", "EMA", "Bollinger", "ATR", "ADX", "Stochastic"
    ])


@dataclass
class DatabaseConfig:
    """Database settings"""
    path: str = os.getenv("DB_PATH", "data/trader_bot.db")
    echo_sql: bool = False


@dataclass
class LogConfig:
    """Logging settings"""
    level: str = "INFO"
    file: str = "logs/trader_bot.log"
    format: str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


# ─── Main Configuration ────────────────────────────────

@dataclass
class Config:
    """Main project configuration"""
    telegram: TelegramConfig = field(default_factory=TelegramConfig)
    deepseek: DeepSeekConfig = field(default_factory=DeepSeekConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    log: LogConfig = field(default_factory=LogConfig)

    # Supported trading symbols
    symbols: Dict[str, str] = field(default_factory=lambda: {
        "XAUUSD": "🏆 Gold",
        "EURUSD": "💶 EUR/USD",
        "GBPUSD": "💷 GBP/USD",
        "USDJPY": "💴 USD/JPY",
        "BTCUSD": "₿ Bitcoin",
        "US30": "📊 Dow Jones",
        "NAS100": "📈 NASDAQ",
    })

    # Lot size presets
    lot_presets: List[float] = field(default_factory=lambda: [
        0.01, 0.05, 0.10, 0.30, 0.50, 1.0
    ])

    # AI confidence presets
    confidence_presets: List[int] = field(default_factory=lambda: [
        60, 70, 80, 90
    ])


# Singleton
config = Config()


def get_config() -> Config:
    """Get the main config singleton"""
    return config
