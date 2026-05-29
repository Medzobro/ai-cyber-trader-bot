"""
Database Manager - مدير قاعدة البيانات
"""
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from config import config
from utils.logger import get_logger
from .models import (
    Base, User, Trade, Setting, AIConfigModel, DailyPerformance,
    TradeStatus, TradeDirection
)

logger = get_logger(__name__)


class DatabaseManager:
    """مدير قاعدة البيانات المركزي"""

    def __init__(self, db_path: str = None):
        db_path = db_path or config.database.path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=config.database.echo_sql,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)
        self._create_tables()

    def _create_tables(self):
        """إنشاء الجداول"""
        Base.metadata.create_all(bind=self.engine)
        logger.info("✅ Database tables created/verified")

    @contextmanager
    def session(self) -> Session:
        """جلسة قاعدة بيانات مع إدارة تلقائية"""
        sess = self.SessionLocal()
        try:
            yield sess
            sess.commit()
        except Exception:
            sess.rollback()
            raise
        finally:
            sess.close()

    # ─── User Management ──────────────────────────

    def get_or_create_user(self, telegram_id: int, username: str = None,
                           first_name: str = None) -> User:
        """جلب أو إنشاء مستخدم"""
        with self.session() as sess:
            user = sess.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                )
                sess.add(user)
                sess.flush()
                logger.info(f"👤 New user: {first_name} ({telegram_id})")
            return user

    def get_user(self, telegram_id: int) -> Optional[User]:
        """جلب مستخدم"""
        with self.session() as sess:
            return sess.query(User).filter(User.telegram_id == telegram_id).first()

    # ─── Settings Management ──────────────────────

    def get_setting(self, user_id: int, key: str, default: str = None) -> Optional[str]:
        """جلب إعداد"""
        with self.session() as sess:
            setting = sess.query(Setting).filter(
                Setting.user_id == user_id,
                Setting.key == key
            ).first()
            return setting.value if setting else default

    def set_setting(self, user_id: int, key: str, value: str):
        """حفظ إعداد"""
        with self.session() as sess:
            setting = sess.query(Setting).filter(
                Setting.user_id == user_id,
                Setting.key == key
            ).first()
            if setting:
                setting.value = value
                setting.updated_at = datetime.utcnow()
            else:
                setting = Setting(user_id=user_id, key=key, value=value)
                sess.add(setting)
            logger.debug(f"⚙️ Setting: {key} = {value} for user {user_id}")

    def get_all_settings(self, user_id: int) -> Dict[str, str]:
        """جلب كل الإعدادات"""
        with self.session() as sess:
            settings = sess.query(Setting).filter(
                Setting.user_id == user_id
            ).all()
            return {s.key: s.value for s in settings}

    # ─── AI Config Management ─────────────────────

    def get_ai_config(self, user_id: int) -> AIConfigModel:
        """جلب إعدادات الذكاء الاصطناعي"""
        with self.session() as sess:
            ai_cfg = sess.query(AIConfigModel).filter(
                AIConfigModel.user_id == user_id
            ).first()
            if not ai_cfg:
                ai_cfg = AIConfigModel(user_id=user_id)
                sess.add(ai_cfg)
                sess.flush()
            return ai_cfg

    def update_ai_config(self, user_id: int, **kwargs):
        """تحديث إعدادات الذكاء الاصطناعي"""
        with self.session() as sess:
            ai_cfg = sess.query(AIConfigModel).filter(
                AIConfigModel.user_id == user_id
            ).first()
            if not ai_cfg:
                ai_cfg = AIConfigModel(user_id=user_id, **kwargs)
                sess.add(ai_cfg)
            else:
                for key, value in kwargs.items():
                    if hasattr(ai_cfg, key):
                        setattr(ai_cfg, key, value)
                ai_cfg.updated_at = datetime.utcnow()
            logger.info(f"🤖 AI config updated for user {user_id}")

    # ─── Trade Management ─────────────────────────

    def create_trade(self, user_id: int, symbol: str, direction: str,
                     volume: float, open_price: float, stop_loss: float = None,
                     take_profit: float = None, ticket: int = None,
                     ai_confidence: float = None,
                     ai_reasoning: str = None) -> Trade:
        """إنشاء صفقة جديدة"""
        with self.session() as sess:
            trade = Trade(
                user_id=user_id,
                symbol=symbol,
                direction=direction,
                volume=volume,
                open_price=open_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                ticket=ticket,
                ai_confidence=ai_confidence,
                ai_reasoning=ai_reasoning,
                status="open",
            )
            sess.add(trade)
            sess.flush()
            logger.info(f"📊 New trade: {symbol} {direction} @ {open_price}")
            return trade

    def close_trade(self, trade_id: int, close_price: float,
                    pnl: float = 0.0, pnl_percentage: float = 0.0,
                    commission: float = 0.0, swap: float = 0.0):
        """إغلاق صفقة"""
        with self.session() as sess:
            trade = sess.query(Trade).filter(Trade.id == trade_id).first()
            if trade:
                trade.close_price = close_price
                trade.pnl = pnl
                trade.pnl_percentage = pnl_percentage
                trade.commission = commission
                trade.swap = swap
                trade.status = "closed"
                trade.closed_at = datetime.utcnow()
                logger.info(f"📊 Trade #{trade_id} closed: PnL={pnl}")

    def get_open_trades(self, user_id: int) -> List[Trade]:
        """جلب الصفقات المفتوحة"""
        with self.session() as sess:
            return sess.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.status == "open"
            ).all()

    def get_open_trades_count(self, user_id: int) -> int:
        """عدد الصفقات المفتوحة"""
        with self.session() as sess:
            return sess.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.status == "open"
            ).count()

    def get_trades_today(self, user_id: int) -> List[Trade]:
        """جلب صفقات اليوم"""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        with self.session() as sess:
            return sess.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.opened_at >= today
            ).all()

    # ─── Performance ──────────────────────────────

    def get_today_performance(self, user_id: int) -> Dict[str, Any]:
        """حساب أداء اليوم"""
        with self.session() as sess:
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            trades = sess.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.opened_at >= today,
                Trade.status == "closed"
            ).all()

            total_pnl = sum(t.pnl or 0 for t in trades)
            total_trades = len(trades)
            winning = sum(1 for t in trades if (t.pnl or 0) > 0)
            losing = sum(1 for t in trades if (t.pnl or 0) < 0)

            return {
                "total_pnl": total_pnl,
                "total_trades": total_trades,
                "winning_trades": winning,
                "losing_trades": losing,
                "win_rate": (winning / total_trades * 100) if total_trades > 0 else 0,
            }

    def get_all_time_performance(self, user_id: int) -> Dict[str, Any]:
        """حساب الأداء الكلي"""
        with self.session() as sess:
            result = sess.query(
                func.count(Trade.id).label("total"),
                func.sum(Trade.pnl).label("total_pnl"),
                func.sum(
                    func.case((Trade.pnl > 0, 1), else_=0)
                ).label("wins"),
            ).filter(
                Trade.user_id == user_id,
                Trade.status == "closed"
            ).first()

            total = result.total or 0
            wins = result.wins or 0
            total_pnl = result.total_pnl or 0.0

            return {
                "total_trades": total,
                "total_pnl": total_pnl,
                "winning_trades": wins,
                "losing_trades": total - wins,
                "win_rate": (wins / total * 100) if total > 0 else 0,
            }


# Singleton
_db_instance: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """الحصول على نسخة قاعدة البيانات"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance
