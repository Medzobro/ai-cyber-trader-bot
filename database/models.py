"""
Database Models
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, Enum, create_engine
)
from sqlalchemy.orm import declarative_base, sessionmaker
import enum

Base = declarative_base()


class TradeDirection(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class TradeStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class AIMode(str, enum.Enum):
    PREDICTIVE = "predictive"
    NEWS_SCANNING = "news_scanning"
    HYBRID = "hybrid"


class User(Base):
    """Users table"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<User(id={self.telegram_id}, name={self.first_name})>"


class Trade(Base):
    """Trades table"""
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    ticket = Column(Integer, nullable=True, comment="MT5 ticket number")

    # Trade details
    symbol = Column(String(20), nullable=False, index=True)
    direction = Column(String(10), nullable=False)  # buy / sell
    volume = Column(Float, nullable=False)
    open_price = Column(Float, nullable=False)
    close_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)

    # Results
    pnl = Column(Float, nullable=True, default=0.0)
    pnl_percentage = Column(Float, nullable=True, default=0.0)
    commission = Column(Float, nullable=True, default=0.0)
    swap = Column(Float, nullable=True, default=0.0)

    # Status
    status = Column(String(20), default="open")  # open / closed / cancelled
    ai_confidence = Column(Float, nullable=True, comment="AI confidence percentage (%)")
    ai_reasoning = Column(Text, nullable=True, comment="AI reasoning/analysis")

    # Timestamps
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Trade(symbol={self.symbol}, direction={self.direction}, pnl={self.pnl})>"


class Setting(Base):
    """Settings table"""
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Setting(user={self.user_id}, key={self.key})>"


class AIConfigModel(Base):
    """AI configuration per user"""
    __tablename__ = "ai_configs"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True, nullable=False, index=True)

    confidence_threshold = Column(Float, default=70.0)
    analysis_mode = Column(String(30), default="predictive")
    news_check_enabled = Column(Boolean, default=True)
    backtest_mode = Column(Boolean, default=False)
    prediction_timeframe = Column(String(10), default="M15")
    preferred_provider = Column(String(30), default=None, comment="User's preferred AI provider: openai, gemini, claude, deepseek")
    news_guard_enabled = Column(Boolean, default=True, comment="Enable/disable NewsGuard auto-close on high-impact news")

    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<AIConfig(user={self.user_id}, threshold={self.confidence_threshold}%)>"


class DailyPerformance(Base):
    """Daily performance table"""
    __tablename__ = "daily_performance"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    date = Column(DateTime, nullable=False, index=True)

    starting_balance = Column(Float, default=0.0)
    ending_balance = Column(Float, default=0.0)
    total_pnl = Column(Float, default=0.0)
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<DailyPerformance(date={self.date}, pnl={self.total_pnl})>"


class UserAPIKey(Base):
    """Encrypted user API keys for AI providers"""
    __tablename__ = "user_api_keys"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    provider = Column(String(30), nullable=False)  # openai, gemini, claude, deepseek
    encrypted_key = Column(Text, nullable=False)  # AES-256 encrypted
    key_hash = Column(String(64), nullable=True)  # SHA256 hash for audit (non-reversible)
    model = Column(String(50), nullable=True)  # User's chosen model
    is_active = Column(Boolean, default=True)
    is_valid = Column(Boolean, default=False)  # Last validation result
    last_validated = Column(DateTime, nullable=True)
    validation_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UserAPIKey(user={self.user_id}, provider={self.provider}, valid={self.is_valid})>"


class BacktestResult(Base):
    """Stored backtest results"""
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)

    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    strategy = Column(String(50), nullable=False, default="indicators")

    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)

    initial_balance = Column(Float, default=10_000.0)
    final_balance = Column(Float, default=10_000.0)

    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    total_return_pct = Column(Float, default=0.0)
    max_drawdown_pct = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    sortino_ratio = Column(Float, default=0.0)
    avg_trade_return = Column(Float, default=0.0)
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    largest_win = Column(Float, default=0.0)
    largest_loss = Column(Float, default=0.0)

    equity_curve = Column(Text, nullable=True)   # JSON list
    trades_json = Column(Text, nullable=True)      # JSON list

    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return (
            f"<BacktestResult(id={self.id}, symbol={self.symbol}, "
            f"return={self.total_return_pct:.2f}%, trades={self.total_trades})>"
        )
