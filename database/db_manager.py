"""
Database Manager
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
from utils.security import encrypt_api_key, decrypt_api_key, hash_key_for_audit, mask_key
from database.models import (
    Base, User, Trade, Setting, AIConfigModel, DailyPerformance, UserAPIKey,
    TradeStatus, TradeDirection, BacktestResult
)

logger = get_logger(__name__)


class DatabaseManager:
    """Central database manager"""

    def __init__(self, db_path: str = None):
        db_path = db_path or config.database.path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=config.database.echo_sql,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, expire_on_commit=False)
        self._create_tables()

    def _create_tables(self):
        """Create all tables and run lightweight migrations"""
        Base.metadata.create_all(bind=self.engine)
        self._migrate_ai_config()
        logger.info("✅ Database tables created/verified")

    def _migrate_ai_config(self):
        """Add missing columns to ai_configs for existing SQLite databases"""
        from sqlalchemy import inspect
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        if 'ai_configs' not in tables:
            logger.info("🗃️ ai_configs table not found yet; skipping migration")
            return
        columns = [c['name'] for c in inspector.get_columns('ai_configs')]
        if 'news_guard_enabled' not in columns:
            with self.engine.connect() as conn:
                conn.execute("ALTER TABLE ai_configs ADD COLUMN news_guard_enabled BOOLEAN DEFAULT 1")
                logger.info("🗃️ Migration applied: added news_guard_enabled to ai_configs")

    @contextmanager
    def session(self) -> Session:
        """Database session with automatic management"""
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
        """Get or create a user"""
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
                logger.info(f"New user: {first_name} ({telegram_id})")
            return user

    def get_user(self, telegram_id: int) -> Optional[User]:
        """Get a user by telegram ID"""
        with self.session() as sess:
            return sess.query(User).filter(User.telegram_id == telegram_id).first()

    # ─── Settings Management ──────────────────────

    def get_setting(self, user_id: int, key: str, default: str = None) -> Optional[str]:
        """Get a setting value"""
        with self.session() as sess:
            setting = sess.query(Setting).filter(
                Setting.user_id == user_id,
                Setting.key == key
            ).first()
            return setting.value if setting else default

    def set_setting(self, user_id: int, key: str, value: str):
        """Save a setting"""
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
            logger.debug(f"Setting: {key} = {value} for user {user_id}")

    def get_all_settings(self, user_id: int) -> Dict[str, str]:
        """Get all settings for a user"""
        with self.session() as sess:
            settings = sess.query(Setting).filter(
                Setting.user_id == user_id
            ).all()
            return {s.key: s.value for s in settings}

    # ─── AI Config Management ─────────────────────

    def get_ai_config(self, user_id: int) -> AIConfigModel:
        """Get AI configuration"""
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
        """Update AI configuration"""
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
            logger.info(f"AI config updated for user {user_id}")

    # ─── Trade Management ─────────────────────────

    def create_trade(self, user_id: int, symbol: str, direction: str,
                     volume: float, open_price: float, stop_loss: float = None,
                     take_profit: float = None, ticket: int = None,
                     ai_confidence: float = None,
                     ai_reasoning: str = None) -> Trade:
        """Create a new trade"""
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
            logger.info(f"New trade: {symbol} {direction} @ {open_price}")
            return trade

    def close_trade(self, trade_id: int, close_price: float,
                    pnl: float = 0.0, pnl_percentage: float = 0.0,
                    commission: float = 0.0, swap: float = 0.0):
        """Close a trade"""
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
                logger.info(f"Trade #{trade_id} closed: PnL={pnl}")

    def get_open_trades(self, user_id: int) -> List[Trade]:
        """Get open trades"""
        with self.session() as sess:
            return sess.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.status == "open"
            ).all()

    def get_trade_by_id(self, trade_id: int, user_id: int) -> Optional[Trade]:
        """Fetch a single trade by ID (ensures user isolation)"""
        with self.session() as sess:
            return sess.query(Trade).filter(
                Trade.id == trade_id,
                Trade.user_id == user_id,
            ).first()

    def get_open_trades_count(self, user_id: int) -> int:
        """Get open trades count"""
        with self.session() as sess:
            return sess.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.status == "open"
            ).count()

    def get_trades_today(self, user_id: int) -> List[Trade]:
        """Get today's trades"""
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        with self.session() as sess:
            return sess.query(Trade).filter(
                Trade.user_id == user_id,
                Trade.opened_at >= today
            ).all()

    # ─── Performance ──────────────────────────────

    def get_today_performance(self, user_id: int) -> Dict[str, Any]:
        """Calculate today's performance"""
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
        """Calculate all-time performance"""
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

    # ─── Backtest Results ─────────────────────────

    def save_backtest(self, user_id: int, data: Dict[str, Any]) -> int:
        """Save a backtest result and return its ID"""
        with self.session() as sess:
            bt = BacktestResult(
                user_id=user_id,
                symbol=data.get("symbol", ""),
                timeframe=data.get("timeframe", ""),
                strategy=data.get("strategy", "indicators"),
                start_date=data.get("start_date"),
                end_date=data.get("end_date"),
                initial_balance=data.get("initial_balance", 10_000.0),
                final_balance=data.get("final_balance", 10_000.0),
                total_trades=data.get("total_trades", 0),
                winning_trades=data.get("winning_trades", 0),
                losing_trades=data.get("losing_trades", 0),
                win_rate=data.get("win_rate", 0.0),
                profit_factor=data.get("profit_factor", 0.0),
                total_return_pct=data.get("total_return_pct", 0.0),
                max_drawdown_pct=data.get("max_drawdown_pct", 0.0),
                sharpe_ratio=data.get("sharpe_ratio", 0.0),
                sortino_ratio=data.get("sortino_ratio", 0.0),
                avg_trade_return=data.get("avg_trade_return", 0.0),
                avg_win=data.get("avg_win", 0.0),
                avg_loss=data.get("avg_loss", 0.0),
                largest_win=data.get("largest_win", 0.0),
                largest_loss=data.get("largest_loss", 0.0),
                equity_curve=data.get("equity_curve"),
                trades_json=data.get("trades_json"),
            )
            sess.add(bt)
            sess.flush()
            logger.info(f"Backtest #{bt.id} saved for user {user_id}")
            return bt.id

    def get_backtests(self, user_id: int, limit: int = 10) -> list:
        """Get backtest history for a user"""
        with self.session() as sess:
            results = sess.query(BacktestResult).filter(
                BacktestResult.user_id == user_id
            ).order_by(BacktestResult.created_at.desc()).limit(limit).all()
            return results

    def get_backtest_by_id(self, backtest_id: int, user_id: int):
        """Fetch a single backtest by ID (ensures user isolation)"""
        with self.session() as sess:
            return sess.query(BacktestResult).filter(
                BacktestResult.id == backtest_id,
                BacktestResult.user_id == user_id,
            ).first()

    # ─── API Key Management (Encrypted) ────────────

    def store_api_key(self, user_id: int, provider: str, api_key: str,
                      model: str = None) -> Optional[UserAPIKey]:
        """
        Store an encrypted API key for a user.
        The key is AES-256 encrypted before storage.
        
        Args:
            user_id: Telegram user ID
            provider: 'openai', 'gemini', 'claude', or 'deepseek'
            api_key: Plaintext API key (encrypted immediately).
                     If empty, only updates the model without touching the key.
            model: Optional model name
        """
        with self.session() as sess:
            existing = sess.query(UserAPIKey).filter(
                UserAPIKey.user_id == user_id,
                UserAPIKey.provider == provider
            ).first()

            if api_key:
                # New key provided - encrypt and store
                encrypted = encrypt_api_key(api_key)
                key_hash = hash_key_for_audit(api_key)

                if existing:
                    existing.encrypted_key = encrypted
                    existing.key_hash = key_hash
                    existing.model = model or existing.model
                    existing.is_active = True  # Reactivate if previously deleted
                    existing.is_valid = False  # Reset validation on new key
                    existing.validation_message = None
                    existing.updated_at = datetime.utcnow()
                    key_record = existing
                else:
                    key_record = UserAPIKey(
                        user_id=user_id,
                        provider=provider,
                        encrypted_key=encrypted,
                        key_hash=key_hash,
                        model=model,
                    )
                    sess.add(key_record)
                    sess.flush()

                masked = mask_key(api_key)
                logger.info(f"API key stored for user {user_id} | Provider: {provider} | Key: {masked}")
            elif model and existing:
                # Only update model, don't touch the encrypted key
                existing.model = model
                existing.updated_at = datetime.utcnow()
                key_record = existing
                logger.info(f"Model updated for user {user_id}/{provider}: {model}")
            elif model:
                # No existing record, can't set model without a key
                logger.warning(f"Cannot set model without key for user {user_id}/{provider}")
                return None
            else:
                logger.warning(f"No key or model provided for user {user_id}/{provider}")
                return existing

            return key_record

    def get_decrypted_api_key(self, user_id: int, provider: str) -> Optional[str]:
        """
        Get a DECRYPTED API key for temporary use.
        ⚠️ Only use in RAM - never log or store the decrypted value!
        
        Args:
            user_id: Telegram user ID
            provider: AI provider name
            
        Returns:
            Decrypted API key string, or None
        """
        with self.session() as sess:
            record = sess.query(UserAPIKey).filter(
                UserAPIKey.user_id == user_id,
                UserAPIKey.provider == provider,
                UserAPIKey.is_active == True
            ).first()

            if not record or not record.encrypted_key:
                return None

            return decrypt_api_key(record.encrypted_key)

    def get_user_api_keys(self, user_id: int) -> List[Dict]:
        """Get all API key records for a user (masked for display)"""
        with self.session() as sess:
            records = sess.query(UserAPIKey).filter(
                UserAPIKey.user_id == user_id,
                UserAPIKey.is_active == True
            ).all()

            return [{
                "provider": r.provider,
                "model": r.model,
                "is_valid": r.is_valid,
                "last_validated": r.last_validated.isoformat() if r.last_validated else None,
                "validation_message": r.validation_message,
                "key_masked": mask_key("sk-..." if not r.encrypted_key else r.encrypted_key[:20]),
            } for r in records]

    def update_key_validation(self, user_id: int, provider: str,
                              is_valid: bool, message: str = None):
        """Update API key validation status"""
        with self.session() as sess:
            record = sess.query(UserAPIKey).filter(
                UserAPIKey.user_id == user_id,
                UserAPIKey.provider == provider
            ).first()
            if record:
                record.is_valid = is_valid
                record.last_validated = datetime.utcnow()
                record.validation_message = message
                record.updated_at = datetime.utcnow()
                logger.info(f"Key validation updated for user {user_id}/{provider}: valid={is_valid}")

    def delete_api_key(self, user_id: int, provider: str):
        """Deactivate (soft delete) an API key and reset all state"""
        with self.session() as sess:
            record = sess.query(UserAPIKey).filter(
                UserAPIKey.user_id == user_id,
                UserAPIKey.provider == provider
            ).first()
            if record:
                record.is_active = False
                record.encrypted_key = ""  # Wipe encrypted data
                record.key_hash = None
                record.is_valid = False
                record.model = None
                record.validation_message = None
                record.last_validated = None
                record.updated_at = datetime.utcnow()
                logger.info(f"API key deactivated for user {user_id}/{provider}")

    def get_user_provider(self, user_id: int) -> Optional[str]:
        """Get the user's active AI provider (preferred, or first valid key)"""
        with self.session() as sess:
            # Check if user has a preferred provider set
            ai_cfg = sess.query(AIConfigModel).filter(
                AIConfigModel.user_id == user_id
            ).first()
            preferred = ai_cfg.preferred_provider if ai_cfg else None

            if preferred:
                # Verify the preferred provider has a valid key
                record = sess.query(UserAPIKey).filter(
                    UserAPIKey.user_id == user_id,
                    UserAPIKey.provider == preferred,
                    UserAPIKey.is_active == True,
                    UserAPIKey.is_valid == True
                ).first()
                if record:
                    return preferred

            # Fallback: first valid key
            record = sess.query(UserAPIKey).filter(
                UserAPIKey.user_id == user_id,
                UserAPIKey.is_active == True,
                UserAPIKey.is_valid == True
            ).first()
            return record.provider if record else None

    # ─── MT5 Credential Management (Encrypted) ───────

    def store_mt5_credentials(self, user_id: int, login: str = None,
                              password: str = None, server: str = None):
        """Store encrypted MT5 credentials as user settings"""
        if login is not None:
            self.set_setting(user_id, "mt5_login", str(login))
        if password is not None:
            # Encrypt the password before storage
            encrypted = encrypt_api_key(password)
            self.set_setting(user_id, "mt5_password_enc", encrypted)
        if server is not None:
            self.set_setting(user_id, "mt5_server", server)
        logger.info(f"MT5 credentials updated for user {user_id}")

    def get_mt5_credentials(self, user_id: int) -> Dict[str, Optional[str]]:
        """Get decrypted MT5 credentials for a user"""
        login = self.get_setting(user_id, "mt5_login")
        server = self.get_setting(user_id, "mt5_server")
        password_enc = self.get_setting(user_id, "mt5_password_enc")
        password = decrypt_api_key(password_enc) if password_enc else None
        return {
            "login": login,
            "password": password,
            "server": server,
        }

    def get_user_readiness(self, user_id: int) -> Dict[str, Any]:
        """
        Check if user is ready for real trading.
        Returns a checklist of required and optional configurations.
        """
        readiness = {
            "ai_provider": False,
            "ai_provider_name": None,
            "ai_model": None,
            "mt5_configured": False,
            "mt5_login": None,
            "mt5_server": None,
            "trading_mode": None,
            "symbol_selected": False,
            "symbol": None,
            "lot_set": False,
            "lot": None,
            "can_trade": False,
            "warnings": [],
            "errors": [],
        }

        # 1. AI Provider check
        provider = self.get_user_provider(user_id)
        if provider:
            readiness["ai_provider"] = True
            readiness["ai_provider_name"] = provider
            # Get model
            keys = self.get_user_api_keys(user_id)
            for k in keys:
                if k["provider"] == provider:
                    readiness["ai_model"] = k.get("model") or "default"
                    break
        else:
            readiness["errors"].append("❌ No AI provider configured. Go to 🤖 AI Settings → 🔑 AI Provider.")

        # 2. MT5 credentials check
        mt5_creds = self.get_mt5_credentials(user_id)
        trading_mode = self.get_setting(user_id, "trading_mode", "simulation")
        readiness["trading_mode"] = trading_mode

        if trading_mode in ("real", "demo"):
            if mt5_creds["login"] and mt5_creds["password"] and mt5_creds["server"]:
                readiness["mt5_configured"] = True
                readiness["mt5_login"] = mt5_creds["login"]
                readiness["mt5_server"] = mt5_creds["server"]
            else:
                readiness["errors"].append(
                    f"❌ MT5 account not configured for {trading_mode.upper()} mode. "
                    "Go to ⚙️ Trade Setup → 🔧 MT5 Account."
                )
        else:
            # Simulation mode - MT5 not required
            readiness["mt5_configured"] = True  # Not needed

        # 3. Trading settings check
        symbol = self.get_setting(user_id, "symbol", config.trading.default_symbol)
        lot = self.get_setting(user_id, "lot", str(config.trading.default_lot))
        readiness["symbol_selected"] = bool(symbol)
        readiness["symbol"] = symbol
        readiness["lot_set"] = bool(lot)
        readiness["lot"] = lot

        if not readiness["symbol_selected"]:
            readiness["warnings"].append("⚠️ No trading symbol selected. Default will be used.")

        # 4. Overall readiness
        has_errors = len(readiness["errors"]) > 0
        readiness["can_trade"] = readiness["ai_provider"] and not has_errors
        if trading_mode in ("real", "demo") and not readiness["mt5_configured"]:
            readiness["can_trade"] = False

        return readiness


# Singleton
_db_instance: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """Get the database singleton instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance
