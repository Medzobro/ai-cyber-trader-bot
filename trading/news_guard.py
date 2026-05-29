"""
NewsGuard - News-Driven Auto-Close System
==========================================
Monitors economic news events and automatically closes open positions
when high-impact news is imminent (within 15 minutes).
Also pauses auto-trading to protect the account during volatile events.
"""
from datetime import datetime
from typing import Dict, List, Any, Optional

from config import config
from utils.logger import get_logger
from utils.helpers import format_currency
from database.db_manager import get_db
from ai_engine.news_scraper import NewsScraper, get_news_scraper
from .mt5_bridge import MT5Bridge
from .risk_manager import RiskManager

logger = get_logger(__name__)


class NewsGuard:
    """
    Protects user accounts by monitoring news and auto-closing positions.
    """

    # How many minutes before a high-impact event to trigger protection
    IMMINENT_THRESHOLD_MINUTES = 15

    # How often to check (used by the scheduler caller)
    CHECK_INTERVAL_MINUTES = 5

    def __init__(self,
                 news_scraper: NewsScraper = None,
                 mt5_bridge: MT5Bridge = None,
                 risk_manager: RiskManager = None):
        self.news_scraper = news_scraper or get_news_scraper()
        self.mt5 = mt5_bridge
        self.risk = risk_manager

    async def check_and_protect(self, user_id: int,
                                notifications=None) -> Dict[str, Any]:
        """
        Check news for the user's active symbol and protect if needed.

        Returns:
            Dict with action taken, positions_closed, reason, events
        """
        db = get_db()

        # 1. Get user's current symbol and settings
        symbol = db.get_setting(user_id, "symbol", config.trading.default_symbol)
        ai_cfg = db.get_ai_config(user_id)

        # If user disabled news check or NewsGuard, skip
        if not ai_cfg.news_check_enabled:
            return {"action": "skipped", "reason": "News check disabled"}
        if not getattr(ai_cfg, "news_guard_enabled", True):
            return {"action": "skipped", "reason": "NewsGuard disabled by user"}

        # 2. Check if user has any open trades
        open_count = db.get_open_trades_count(user_id)
        if open_count == 0:
            return {"action": "none", "reason": "No open positions"}

        # 3. Fetch news for this symbol's currency
        news_result = self.news_scraper.should_pause_trading(symbol)
        events = news_result.get("events", [])

        if not news_result.get("should_pause"):
            return {
                "action": "none",
                "reason": news_result.get("reason", "No imminent high-impact news"),
                "events": events,
            }

        # 4. High-impact news is imminent — PROTECT!
        logger.warning(
            f"🚨 NEWSGUARD triggered for user {user_id} | "
            f"Symbol: {symbol} | Reason: {news_result['reason']}"
        )

        # 5. Close all open positions (with internal error guard)
        positions_closed = 0
        closed_trades_details = []

        try:
            open_trades = db.get_open_trades(user_id)
            for trade in open_trades:
                # Close specific ticket in MT5 if available (multi-tenant safe)
                mt5_closed = False
                if self.mt5 and trade.ticket:
                    mt5_closed = self.mt5.close_position(
                        ticket=trade.ticket,
                        symbol=trade.symbol,
                        volume=trade.volume,
                    )

                # Get current price for PnL calculation
                tick = self.mt5.get_tick(trade.symbol) if self.mt5 else None
                close_price = tick["bid"] if tick else trade.open_price
                pnl = self._calculate_pnl(
                    trade.direction, trade.open_price, close_price, trade.volume, trade.symbol
                )

                db.close_trade(trade.id, close_price, pnl=pnl, pnl_percentage=0)
                closed_trades_details.append({
                    "symbol": trade.symbol,
                    "direction": trade.direction,
                    "volume": trade.volume,
                    "pnl": pnl,
                    "mt5_closed": mt5_closed,
                })
                positions_closed += 1

        except Exception as e:
            logger.error(f"NewsGuard close-sequence error for user {user_id}: {e}")
            # Still try to pause trading even if close partially failed

        # 6. Pause auto trading
        if self.risk:
            self.risk.pause_trading(user_id)

        # 7. Build alert message
        events_text = "\n".join(
            f"🔴 {e.get('title', 'Unknown')} ({e.get('time_str', '')})"
            for e in events[:3]
        )

        total_pnl = sum(t["pnl"] for t in closed_trades_details)

        result = {
            "action": "protected",
            "reason": news_result["reason"],
            "events": events,
            "positions_closed": positions_closed,
            "closed_trades": closed_trades_details,
            "total_pnl": total_pnl,
            "symbol": symbol,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 8. Send notification if manager available
        if notifications:
            await self._send_alert(notifications, user_id, result)

        logger.info(
            f"✅ NewsGuard completed for user {user_id}: "
            f"{positions_closed} positions closed | PnL: {total_pnl:+.2f}"
        )

        return result

    async def _send_alert(self, notifications, user_id: int, result: Dict):
        """Send news-driven close alert to user"""
        try:
            msg = self._build_alert_message(result)
            await notifications.send_alert(user_id, "warning", msg)
        except Exception as e:
            logger.error(f"Failed to send NewsGuard alert to {user_id}: {e}")

    def _calculate_pnl(self, direction: str, open_price: float,
                       close_price: float, volume: float, symbol: str) -> float:
        """Calculate PnL using pip value for the symbol"""
        price_diff = close_price - open_price
        if direction == "sell":
            price_diff = -price_diff

        if self.mt5:
            try:
                pip_value = self.mt5.calculate_pip_value(symbol, volume)
                # Determine pip size from MT5 symbol info or symbol name
                pip_size = self._get_pip_size(symbol)
                raw_pips = price_diff / pip_size
                return raw_pips * pip_value
            except Exception:
                pass

        # Fallback: simple price difference (best-effort)
        return price_diff * volume * 100

    @staticmethod
    def _get_pip_size(symbol: str) -> float:
        """Return pip size for a symbol (JPY=0.01, XAU=0.1, indices=1.0, others=0.0001)"""
        symbol = symbol.upper()
        if "JPY" in symbol:
            return 0.01
        if any(s in symbol for s in ("XAU", "XAG", "GOLD", "SILVER")):
            return 0.1
        if any(s in symbol for s in ("US30", "NAS100", "SPX", "DJ", "NDX", "UK100", "GER40")):
            return 1.0
        if "BTC" in symbol:
            return 1.0
        return 0.0001

    @staticmethod
    def _build_alert_message(result: Dict) -> str:
        """Build the alert message text"""
        total_pnl = result.get("total_pnl", 0)
        pnl_emoji = "🟢" if total_pnl > 0 else "🔴" if total_pnl < 0 else "⚪"

        lines = [
            "🚨 **NewsGuard Protection Activated!**\n",
            f"**Reason:** {result.get('reason', 'High-impact news imminent')}",
            f"**Asset:** {result.get('symbol', 'N/A')}",
            f"**Positions Closed:** {result.get('positions_closed', 0)}",
            f"**Total P&L:** {pnl_emoji} ${total_pnl:+.2f}",
            "",
            "📰 **Triggering Events:**",
        ]

        for event in result.get("events", [])[:3]:
            lines.append(
                f"🔴 {event.get('title', 'Unknown')} — "
                f"{event.get('time_str', 'Soon')}"
            )

        lines.extend([
            "",
            "⏸️ Auto-trading has been paused.",
            "✅ Your account is protected.",
            "",
            "You can resume trading manually when the news event passes.",
        ])

        return "\n".join(lines)

    async def scan_all_users(self, notifications=None) -> List[Dict]:
        """
        Scan all active users and protect those with imminent news.
        Called periodically by the scheduler.
        """
        db = get_db()

        # Get all users who have open trades
        # (We query distinct user_ids from open trades)
        from database.models import Trade
        from sqlalchemy import distinct

        with db.session() as sess:
            active_user_ids = [
                row[0] for row in
                sess.query(distinct(Trade.user_id))
                .filter(Trade.status == "open")
                .all()
            ]

        results = []
        for user_id in active_user_ids:
            try:
                result = await self.check_and_protect(user_id, notifications)
                if result.get("action") == "protected":
                    results.append(result)
            except Exception as e:
                logger.error(f"NewsGuard error for user {user_id}: {e}")

        if results:
            logger.info(f"NewsGuard scan complete: {len(results)} users protected")
        else:
            logger.debug("NewsGuard scan: no users needed protection")

        return results
