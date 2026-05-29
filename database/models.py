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
