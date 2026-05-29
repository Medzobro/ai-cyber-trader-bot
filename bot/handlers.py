"""
Telegram Bot Handlers
======================
All command handlers and callbacks for the bot
"""
import traceback
from datetime import datetime
from typing import Optional, Dict, Any

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import config, get_config
from utils.logger import get_logger
from utils.helpers import format_currency, format_percentage
from database.db_manager import get_db
from ai_engine.ai_manager import AIManager, PROVIDER_INFO
from trading.news_guard import NewsGuard
from trading.backtester import Backtester
from trading.backtest_report import BacktestReport
from .keyboards import Keyboards
from .messages import Messages
from .notifications import NotificationManager

logger = get_logger(__name__)


class TelegramBot:
    """Main Telegram bot"""

    def __init__(self, mt5_bridge=None, risk_manager=None,
                 trade_executor=None, market_analyzer=None,
                 predictor=None, news_scraper=None):
        self.mt5 = mt5_bridge
        self.risk = risk_manager
        self.executor = trade_executor
        self.analyzer = market_analyzer
        self.predictor = predictor
        self.news_scraper = news_scraper
        self.notifications = NotificationManager()
        self.news_guard = NewsGuard(
            news_scraper=news_scraper,
            mt5_bridge=mt5_bridge,
            risk_manager=risk_manager,
        )
        self.backtester = Backtester(predictor=predictor)

        # Auto trading states
        self.auto_trading: Dict[int, bool] = {}

        # Scheduled trading jobs
        self.scheduled_jobs: Dict[int, Any] = {}

        self.app: Optional[Application] = None
        self.db = get_db()

        # Background scheduler for NewsGuard + Auto-Trading
        self._scheduler = None
        self._auto_trading_interval = 5  # minutes between auto-trade cycles

    async def start(self):
        """Start the bot"""
        token = config.telegram.bot_token

        if token == "YOUR_TELEGRAM_BOT_TOKEN":
            logger.error("Please set TELEGRAM_BOT_TOKEN in .env file")
            return

        self.app = Application.builder().token(token).build()
        self.notifications.set_app(self.app)

        # Register handlers
        self._register_handlers()

        # Start NewsGuard periodic protection scan
        self._start_news_guard_scheduler()

        # Start auto-trading scheduler
        self._start_auto_trading_scheduler()

        logger.info("Telegram bot started. Waiting for commands...")
        await self.app.run_polling(allowed_updates=Update.ALL_TYPES)

    async def stop(self):
        """Stop the bot"""
        if self._scheduler:
            self._scheduler.shutdown(wait=False)
            logger.info("Schedulers stopped")
        if self.app:
            await self.app.stop()
            await self.app.shutdown()
        logger.info("Bot stopped")

    def _start_news_guard_scheduler(self):
        """Start the periodic NewsGuard protection scan"""
        try:
            if not self._scheduler:
                self._scheduler = AsyncIOScheduler()
            self._scheduler.add_job(
                self._periodic_news_check,
                "interval",
                minutes=NewsGuard.CHECK_INTERVAL_MINUTES,
                id="news_guard_scan",
                replace_existing=True,
            )
            if not self._scheduler.running:
                self._scheduler.start()
            logger.info(
                f"🛡️ NewsGuard scheduler started | "
                f"Interval: {NewsGuard.CHECK_INTERVAL_MINUTES}min"
            )
        except Exception as e:
            logger.error(f"Failed to register NewsGuard scheduler: {e}")

    def _start_auto_trading_scheduler(self):
        """Start the periodic auto-trading cycle scheduler"""
        try:
            if not self._scheduler:
                self._scheduler = AsyncIOScheduler()
            self._scheduler.add_job(
                self._periodic_auto_trade,
                "interval",
                minutes=self._auto_trading_interval,
                id="auto_trade_scan",
                replace_existing=True,
            )
            if not self._scheduler.running:
                self._scheduler.start()
            logger.info(
                f"🤖 Auto-trading scheduler started | "
                f"Interval: {self._auto_trading_interval}min"
            )
        except Exception as e:
            logger.error(f"Failed to start auto-trading scheduler: {e}")

    async def _periodic_auto_trade(self):
        """Periodic background job: run auto-trading for all active users"""
        try:
            active_users = [uid for uid, active in self.auto_trading.items() if active]
            if not active_users:
                return

            if not self.analyzer or not self.executor:
                logger.warning("Auto-trade skipped: analyzer or executor not initialized")
                return

            logger.info(f"🤖 Auto-trade scan: {len(active_users)} active users")
            for user_id in active_users:
                try:
                    if not self.auto_trading.get(user_id):
                        continue
                    if self.risk and self.risk.trading_paused.get(user_id):
                        continue

                    db = get_db()
                    symbol = db.get_setting(user_id, "symbol", config.trading.default_symbol)
                    tf = db.get_setting(user_id, "timeframe", config.ai.prediction_timeframe)

                    # Analyze market
                    result = self.analyzer.analyze(symbol, tf, user_id=user_id)
                    if result.get("error") or result.get("should_stop"):
                        if result.get("should_stop"):
                            self.auto_trading[user_id] = False
                            if self.risk:
                                self.risk.pause_trading(user_id)
                            await self.notifications.send_alert(
                                user_id, "warning",
                                f"🚨 Auto-trading paused: {result.get('reasoning', 'API quota exceeded')}"
                            )
                        continue

                    confidence = result.get("confidence", 0)
                    ai_cfg = db.get_ai_config(user_id)
                    if confidence < ai_cfg.confidence_threshold:
                        continue

                    # Execute trade using pre-computed analysis (no double-analysis)
                    trade_result = self.executor.execute_from_analysis(
                        user_id, symbol, tf, result
                    )
                    if trade_result.get("trade_executed"):
                        await self.notifications.send_trade_opened(
                            user_id, trade_result["trade"]
                        )
                except Exception as e:
                    logger.error(f"Auto-trade error for user {user_id}: {e}")
        except Exception as e:
            logger.error(f"Auto-trade periodic error: {e}")

    async def _periodic_news_check(self):
        """Periodic background job: scan all users for imminent news"""
        try:
            results = await self.news_guard.scan_all_users(
                notifications=self.notifications
            )
            if results:
                total_closed = sum(r.get("positions_closed", 0) for r in results)
                logger.info(
                    f"🛡️ NewsGuard scan: {len(results)} users protected, "
                    f"{total_closed} positions closed"
                )
        except Exception as e:
            logger.error(f"NewsGuard periodic check error: {e}")

    def _register_handlers(self):
        """Register all command and callback handlers"""
        # Commands
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("analyze", self.cmd_analyze))
        self.app.add_handler(CommandHandler("report", self.cmd_report))
        self.app.add_handler(CommandHandler("settings", self.cmd_settings))
        self.app.add_handler(CommandHandler("panic", self.cmd_panic))
        self.app.add_handler(CommandHandler("top5", self.cmd_top5))
        self.app.add_handler(CommandHandler("cancel", self.cmd_cancel))

        # Callbacks (inline buttons)
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))

        # Text messages (custom lot, API keys, etc.)
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_message
        ))

        # Error handler
        self.app.add_error_handler(self.handle_error)

    # ─── Command Handlers ─────────────────────────

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/start command - Main dashboard"""
        user = update.effective_user
        db = get_db()
        db_user = db.get_or_create_user(
            user.id, user.username, user.first_name
        )

        # Default user settings
        lot = db.get_setting(user.id, "lot", str(config.trading.default_lot))
        direction = db.get_setting(user.id, "direction", "both")
        symbol = db.get_setting(user.id, "symbol", config.trading.default_symbol)

        # Account info
        balance = self.mt5.get_balance() if self.mt5 else 42500.0
        account_type = "MT5 Real" if self.mt5 and not self.mt5.simulation else "MT5 Demo"

        # Today's performance
        today = db.get_today_performance(user.id)
        open_trades = db.get_open_trades_count(user.id)

        # Bot status
        auto_running = self.auto_trading.get(user.id, False)
        bot_status = "🟢 ONLINE" if self.mt5 and self.mt5.is_connected() else "🟡 SIMULATION"

        dashboard_text = Messages.dashboard(
            bot_status=bot_status,
            account=account_type,
            balance=balance,
            daily_pnl=today["total_pnl"],
            symbol=symbol,
            auto_running=auto_running,
            open_trades=open_trades,
        )

        await update.message.reply_text(
            text=dashboard_text,
            reply_markup=Keyboards.main_dashboard(),
            parse_mode="Markdown",
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/help command"""
        await update.message.reply_text(
            Messages.help_message(),
            reply_markup=Keyboards.back_button(),
            parse_mode="Markdown",
        )

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/status command"""
        user = update.effective_user
        db = get_db()
        user_id = user.id

        risk_status = self.risk.get_risk_status(user_id) if self.risk else {}
        open_trades_count = db.get_open_trades_count(user_id)

        auto_running = self.auto_trading.get(user_id, False)

        status_text = (
            "📊 **System Status**\n\n"
            f"🔹 **Bot:** {'🟢 Running' if self.app else '🔴 Stopped'}\n"
            f"🔹 **Auto Trading:** {'🟢 Active' if auto_running else '🔴 Stopped'}\n"
            f"🔹 **MT5:** {'✅ Connected' if self.mt5 and self.mt5.is_connected() else '🟡 Simulation'}\n"
            f"🔹 **Open Positions:** {open_trades_count}\n"
            f"🔹 **Risk Level:** {risk_status.get('risk_level', 'N/A')}\n"
        )

        await update.message.reply_text(
            status_text,
            reply_markup=Keyboards.main_dashboard(),
            parse_mode="Markdown",
        )

    async def cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/analyze command - Analyze current market"""
        user = update.effective_user
        user_id = user.id
        db = get_db()

        symbol = db.get_setting(user_id, "symbol", "XAUUSD")
        tf = db.get_setting(user_id, "timeframe", "M15")

        if not self.analyzer:
            await update.message.reply_text("❌ Market analyzer not initialized")
            return

        # Send waiting message
        sent_msg = await update.message.reply_text(
            f"⏳ Analyzing {symbol} ({tf}) with AI...",
        )

        try:
            result = self.analyzer.analyze(symbol, tf, user_id=user_id)
            analysis_text = Messages.analysis_result(result)

            await sent_msg.edit_text(
                text=analysis_text,
                reply_markup=Keyboards.back_button("main_menu"),
                parse_mode="Markdown",
            )

        except Exception as e:
            logger.error(f"Analysis error: {e}")
            await sent_msg.edit_text(
                f"❌ Analysis error: {e}",
                reply_markup=Keyboards.back_button(),
            )

    async def cmd_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/report command"""
        user = update.effective_user
        db = get_db()
        user_id = user.id

        daily = db.get_today_performance(user_id)
        all_time = db.get_all_time_performance(user_id)
        balance = self.mt5.get_balance() if self.mt5 else 42500.0

        report_text = Messages.performance_report(daily, all_time, balance)

        await update.message.reply_text(
            report_text,
            reply_markup=Keyboards.reports_menu(),
            parse_mode="Markdown",
        )

    async def cmd_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/settings command"""
        user = update.effective_user
        db = get_db()
        user_id = user.id

        symbol = db.get_setting(user_id, "symbol", "XAUUSD")
        lot = db.get_setting(user_id, "lot", str(config.trading.default_lot))
        direction = db.get_setting(user_id, "direction", "both")

        settings_text = Messages.trading_settings(symbol, float(lot), direction)

        await update.message.reply_text(
            settings_text,
            reply_markup=Keyboards.trading_setup(),
            parse_mode="Markdown",
        )

    async def cmd_panic(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/panic command - Emergency close all"""
        await update.message.reply_text(
            "🚨 **WARNING: Are you sure you want to close ALL open positions?**\n\n"
            "All positions will be closed immediately at market price.",
            reply_markup=Keyboards.confirm_panic(),
            parse_mode="Markdown",
        )

    async def cmd_top5(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/top5 command - Show top 5 Forex opportunities"""
        user = update.effective_user
        user_id = user.id

        if not self.analyzer:
            await update.message.reply_text("❌ Market analyzer not initialized")
            return

        sent_msg = await update.message.reply_text(
            "🏆 Scanning Top 5 Forex opportunities...",
        )

        try:
            results = self.analyzer.analyze_top5(user_id=user_id)
            top5_text = Messages.top5_result(results)

            await sent_msg.edit_text(
                text=top5_text,
                reply_markup=Keyboards.back_button("main_menu"),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Top5 error: {e}")
            await sent_msg.edit_text(
                f"❌ Top 5 error: {e}",
                reply_markup=Keyboards.back_button(),
            )

    async def cmd_cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """/cancel - Cancel current input operation"""
        context.user_data.pop("awaiting_lot", None)
        context.user_data.pop("awaiting_api_key", None)
        context.user_data.pop("api_key_provider", None)
        await update.message.reply_text(
            "✅ Operation cancelled.",
            reply_markup=Keyboards.main_dashboard(),
        )

    # ─── Callback Handler ─────────────────────────

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Main callback handler for all inline buttons"""
        query = update.callback_query
        await query.answer()

        user = query.from_user
        user_id = user.id
        data = query.data

        db = get_db()
        db.get_or_create_user(user_id, user.username, user.first_name)

        try:
            # Navigation
            if data == "main_menu":
                await self._show_dashboard(query, user_id)
            elif data == "refresh":
                await self._show_dashboard(query, user_id)

            # Trading Setup
            elif data.startswith("symbol_"):
                await self._handle_symbol_select(query, user_id, data)
            elif data.startswith("lot_"):
                await self._handle_lot_select(query, user_id, data)
            elif data == "lot_custom":
                await query.edit_message_text(
                    Messages.enter_custom_lot(),
                    reply_markup=Keyboards.back_button("menu_trade"),
                )
                context.user_data["awaiting_lot"] = True
            elif data.startswith("dir_"):
                await self._handle_direction_select(query, user_id, data)
            elif data == "symbols_indices":
                await query.edit_message_text(
                    "📊 Select Index:",
                    reply_markup=Keyboards.indices_symbols(),
                )

            # Trading Controls
            elif data == "auto_start":
                await self._handle_auto_start(query, user_id)
            elif data == "auto_stop":
                await self._handle_auto_stop(query, user_id)

            # AI Config
            elif data == "menu_ai":
                await self._show_ai_config(query, user_id)
            elif data == "ai_confidence":
                await query.edit_message_text(
                    "🎯 Select minimum confidence threshold:",
                    reply_markup=Keyboards.confidence_levels(),
                )
            elif data.startswith("conf_"):
                await self._handle_confidence_select(query, user_id, data)
            elif data == "ai_model":
                await query.edit_message_text(
                    "🧠 Select analysis mode:",
                    reply_markup=Keyboards.analysis_modes(),
                )
            elif data.startswith("mode_"):
                await self._handle_mode_select(query, user_id, data)
            elif data == "ai_news":
                await self._toggle_news(query, user_id)
            elif data == "ai_timeframe":
                await query.edit_message_text(
                    "⏱️ Select analysis timeframe:",
                    reply_markup=Keyboards.timeframes(),
                )
            elif data.startswith("tf_"):
                await self._handle_timeframe_select(query, user_id, data)
            elif data == "ai_newsguard":
                await self._toggle_newsguard(query, user_id)
            elif data == "menu_backtest":
                await self._show_backtest_menu(query, user_id)
            elif data == "backtest_pick_symbol":
                await query.edit_message_text(
                    "🏆 Select asset for backtest:",
                    reply_markup=Keyboards.backtest_symbols(),
                )
            elif data == "backtest_pick_tf":
                await query.edit_message_text(
                    "⏱️ Select timeframe for backtest:",
                    reply_markup=Keyboards.backtest_timeframes(),
                )
            elif data == "backtest_pick_strategy":
                await query.edit_message_text(
                    "🧮 Select strategy for backtest:",
                    reply_markup=Keyboards.backtest_strategies(),
                )
            elif data.startswith("backtest_symbol_"):
                await self._handle_backtest_symbol(query, user_id, data)
            elif data.startswith("backtest_tf_"):
                await self._handle_backtest_tf(query, user_id, data)
            elif data.startswith("backtest_strategy_"):
                await self._handle_backtest_strategy(query, user_id, data)
            elif data == "backtest_run":
                await self._run_backtest(query, user_id)
            elif data == "backtest_history":
                await self._show_backtest_history(query, user_id)
            elif data.startswith("backtest_view_"):
                await self._view_backtest(query, user_id, data)
            elif data == "ai_train":
                await query.edit_message_text(
                    "🚧 This feature is under development...\nTraining ML model on historical data.",
                    reply_markup=Keyboards.back_button("menu_ai"),
                )

            # ─── AI Provider Management ─────────────────

            elif data == "ai_provider":
                await query.edit_message_text(
                    Messages.provider_select(),
                    reply_markup=Keyboards.ai_providers(),
                    parse_mode="Markdown",
                )

            elif data == "provider_status":
                await self._show_provider_status(query, user_id)

            # Provider selection → show setup menu
            elif data.startswith("provider_") and not data.startswith("provider_status"):
                provider = data.replace("provider_", "")
                info = PROVIDER_INFO.get(provider, {})
                provider_name = info.get("name", provider.title()) if isinstance(info, dict) else provider.title()
                await query.edit_message_text(
                    Messages.api_key_prompt(provider),
                    reply_markup=Keyboards.provider_setup(provider, provider_name),
                    parse_mode="Markdown",
                )

            # Set API key → prompt user to send the key
            elif data.startswith("setkey_"):
                provider = data.replace("setkey_", "")
                context.user_data["awaiting_api_key"] = True
                context.user_data["api_key_provider"] = provider
                info = PROVIDER_INFO.get(provider, {})
                provider_name = info.get("name", provider.title()) if isinstance(info, dict) else provider.title()
                await query.edit_message_text(
                    Messages.api_key_prompt(provider),
                    reply_markup=Keyboards.back_button(f"provider_{provider}"),
                    parse_mode="Markdown",
                )

            # Validate API key
            elif data.startswith("validate_"):
                provider = data.replace("validate_", "")
                await self._handle_validate_key(query, user_id, provider)

            # Delete API key
            elif data.startswith("delkey_"):
                provider = data.replace("delkey_", "")
                db.delete_api_key(user_id, provider)
                await query.answer("🗑️ Key removed")
                info = PROVIDER_INFO.get(provider, {})
                provider_name = info.get("name", provider.title()) if isinstance(info, dict) else provider.title()
                await query.edit_message_text(
                    Messages.api_key_removed(provider),
                    reply_markup=Keyboards.provider_setup(provider, provider_name),
                    parse_mode="Markdown",
                )

            # Show model selection for a provider
            elif data.startswith("model_"):
                provider = data.replace("model_", "")
                info = PROVIDER_INFO.get(provider, {})
                if isinstance(info, dict):
                    models = info.get("models", ["default"])
                else:
                    models = ["default"]
                await query.edit_message_text(
                    Messages.provider_model_select(provider),
                    reply_markup=Keyboards.provider_models(provider, models),
                    parse_mode="Markdown",
                )

            # Set specific model for a provider
            elif data.startswith("setmodel_"):
                parts = data.split("_", 2)  # setmodel_PROVIDER_MODEL
                if len(parts) >= 3:
                    provider = parts[1]
                    model = parts[2]
                    db.store_api_key(user_id, provider, "", model=model)
                    # Also set this as the preferred provider
                    db.update_ai_config(user_id, preferred_provider=provider)
                    await query.answer(f"✅ Model: {model} — set as active provider")
                    info = PROVIDER_INFO.get(provider, {})
                    provider_name = info.get("name", provider.title()) if isinstance(info, dict) else provider.title()
                    await query.edit_message_text(
                        Messages.api_key_set(provider, model=model),
                        reply_markup=Keyboards.provider_setup(provider, provider_name),
                        parse_mode="Markdown",
                    )

            # Trade Setup Menu
            elif data == "menu_trade":
                await self._show_trade_settings(query, user_id)

            # Reports
            elif data == "menu_reports":
                await self._show_reports(query, user_id)
            elif data == "report_today":
                daily = db.get_today_performance(user_id)
                balance = self.mt5.get_balance() if self.mt5 else 42500.0
                pnl_pct = (daily["total_pnl"] / balance * 100) if balance > 0 else 0
                text = (
                    "📅 **Today's Performance**\n\n"
                    f"💰 P&L: {format_currency(daily['total_pnl'])} ({format_percentage(pnl_pct)})\n"
                    f"📊 Trades: {daily['total_trades']}\n"
                    f"✅ Winners: {daily['winning_trades']}\n"
                    f"❌ Losers: {daily['losing_trades']}\n"
                    f"🎯 Win Rate: {daily['win_rate']:.1f}%"
                )
                await query.edit_message_text(
                    text,
                    reply_markup=Keyboards.reports_menu(),
                    parse_mode="Markdown",
                )
            elif data == "report_all":
                all_time = db.get_all_time_performance(user_id)
                text = (
                    "📈 **All-Time Performance**\n\n"
                    f"💰 Total P&L: {format_currency(all_time['total_pnl'])}\n"
                    f"📊 Total Trades: {all_time['total_trades']}\n"
                    f"✅ Winners: {all_time['winning_trades']}\n"
                    f"❌ Losers: {all_time['losing_trades']}\n"
                    f"🎯 Win Rate: {all_time['win_rate']:.1f}%"
                )
                await query.edit_message_text(
                    text,
                    reply_markup=Keyboards.reports_menu(),
                    parse_mode="Markdown",
                )
            elif data == "report_recent":
                trades = db.get_trades_today(user_id)
                text = Messages.recent_trades(trades)
                await query.edit_message_text(
                    text,
                    reply_markup=Keyboards.reports_menu(),
                )
            elif data == "report_backtest":
                await self._show_backtest_history(query, user_id)

            # Risk Management
            elif data == "menu_risk":
                await self._show_risk_status(query, user_id)
            elif data == "risk_status":
                await self._show_risk_status(query, user_id)
            elif data == "risk_daily_loss":
                await query.edit_message_text(
                    "⚠️ **Daily Loss Limit**\n\n"
                    f"Current limit: {config.trading.max_daily_loss}%\n"
                    "When this limit is exceeded, trading stops automatically for the day.\n\n"
                    "🚧 Under development...",
                    reply_markup=Keyboards.risk_menu(),
                )
            elif data == "risk_max_trades":
                await query.edit_message_text(
                    "📦 **Max Open Positions**\n\n"
                    f"Current limit: {config.trading.max_open_trades} positions\n\n"
                    "🚧 Under development...",
                    reply_markup=Keyboards.risk_menu(),
                )

            # Panic
            elif data == "panic":
                await query.edit_message_text(
                    "🚨 **WARNING: Close ALL Positions Immediately**\n\n"
                    "All open positions will be closed at market price.",
                    reply_markup=Keyboards.confirm_panic(),
                    parse_mode="Markdown",
                )
            elif data == "panic_confirm":
                closed = 0
                if self.risk:
                    closed = self.risk.activate_panic(user_id)
                elif self.mt5:
                    closed = self.mt5.close_all_positions()
                await query.edit_message_text(
                    f"🚨 **Emergency order executed!**\n\n{closed} position(s) closed successfully.\n"
                    "Panic mode active - trading stopped.",
                    reply_markup=Keyboards.back_button(),
                    parse_mode="Markdown",
                )

            # Top 5 Forex
            elif data == "top5_forex":
                await self._handle_top5(query, user_id)

            # Analyze Now
            elif data == "analyze_now":
                await self._handle_analyze_now(query, user_id)

            else:
                await query.edit_message_text(
                    f"⚠️ Unknown command: {data}",
                    reply_markup=Keyboards.back_button(),
                )

        except Exception as e:
            logger.error(f"Callback error: {e}\n{traceback.format_exc()}")
            try:
                await query.edit_message_text(
                    f"❌ An error occurred: {e}",
                    reply_markup=Keyboards.back_button(),
                )
            except Exception:
                pass

    # ─── Message Handler ──────────────────────────

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Text message handler"""
        user = update.effective_user
        user_id = user.id
        text = update.message.text.strip()
        db = get_db()

        # If awaiting custom lot input
        if context.user_data.get("awaiting_lot"):
            await self._handle_custom_lot(update, context, user_id, text)
            return

        # If awaiting API key input
        if context.user_data.get("awaiting_api_key"):
            await self._handle_api_key_input(update, context, user_id, text)
            return

        # Default response
        await update.message.reply_text(
            "Use the buttons below or type a command:\n"
            "/start - Main menu | /help - Help | /analyze - Analysis",
            reply_markup=Keyboards.main_dashboard(),
        )

    async def _handle_custom_lot(self, update, context, user_id: int, text: str):
        """Handle custom lot size input"""
        db = get_db()
        try:
            lot = float(text)
            if lot < config.trading.min_lot or lot > config.trading.max_lot:
                await update.message.reply_text(
                    f"⚠️ Lot must be between {config.trading.min_lot} and {config.trading.max_lot}",
                    reply_markup=Keyboards.lot_sizes(),
                )
                return

            db.set_setting(user_id, "lot", str(lot))
            context.user_data["awaiting_lot"] = False

            symbol = db.get_setting(user_id, "symbol", "XAUUSD")
            direction = db.get_setting(user_id, "direction", "both")

            await update.message.reply_text(
                f"✅ Lot size set to: **{lot}**\n\n"
                + Messages.trading_settings(symbol, lot, direction),
                reply_markup=Keyboards.trading_setup(),
                parse_mode="Markdown",
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Please enter a valid number. Example: `0.25`",
                reply_markup=Keyboards.lot_sizes(),
            )

    async def _handle_api_key_input(self, update, context, user_id: int, text: str):
        """Handle API key input from user"""
        db = get_db()
        provider = context.user_data.get("api_key_provider", "deepseek")

        # Clear the awaited state
        context.user_data["awaiting_api_key"] = False
        context.user_data["api_key_provider"] = None

        info = PROVIDER_INFO.get(provider, {})
        provider_name = info.get("name", provider.title()) if isinstance(info, dict) else provider.title()

        # Store the encrypted key
        try:
            db.store_api_key(user_id, provider, text)

            # Auto-validate
            await update.message.reply_text(
                f"🔑 Key received for **{provider_name}**\n⏳ Validating...",
                parse_mode="Markdown",
            )

            # Validate in background
            decrypted = db.get_decrypted_api_key(user_id, provider)
            if decrypted:
                try:
                    result = AIManager.validate_key(provider, decrypted)
                    db.update_key_validation(
                        user_id, provider,
                        is_valid=result.get("valid", False),
                        message=result.get("message", "")
                    )

                    if result.get("valid"):
                        await update.message.reply_text(
                            Messages.api_key_valid(provider),
                            reply_markup=Keyboards.provider_setup(provider, provider_name),
                            parse_mode="Markdown",
                        )
                    else:
                        await update.message.reply_text(
                            Messages.api_key_invalid(provider, result.get("message", "")),
                            reply_markup=Keyboards.provider_setup(provider, provider_name),
                            parse_mode="Markdown",
                        )
                except Exception as e:
                    logger.error(f"Validation error for {provider}: {e}")
                    await update.message.reply_text(
                        Messages.api_key_invalid(provider, str(e)),
                        reply_markup=Keyboards.provider_setup(provider, provider_name),
                        parse_mode="Markdown",
                    )
            else:
                await update.message.reply_text(
                    f"❌ Could not decrypt the stored key for verification.\n"
                    f"Please check your encryption secret in .env.",
                    reply_markup=Keyboards.back_button(f"provider_{provider}"),
                )

        except Exception as e:
            logger.error(f"API key storage error: {e}")
            await update.message.reply_text(
                f"❌ Error saving key: {e}",
                reply_markup=Keyboards.back_button(f"provider_{provider}"),
            )

    # ─── Error Handler ────────────────────────────

    async def handle_error(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Error handler"""
        logger.error(f"Update {update} caused error: {context.error}")
        if context.error:
            logger.error(traceback.format_exception(None, context.error, context.error.__traceback__))

    # ─── Helper Methods ───────────────────────────

    async def _show_dashboard(self, query, user_id: int):
        """Show main dashboard"""
        db = get_db()
        symbol = db.get_setting(user_id, "symbol", "XAUUSD")

        balance = self.mt5.get_balance() if self.mt5 else 42500.0
        account_type = "MT5 Real" if self.mt5 and not self.mt5.simulation else "MT5 Demo"
        today = db.get_today_performance(user_id)
        open_trades = db.get_open_trades_count(user_id)
        auto_running = self.auto_trading.get(user_id, False)
        bot_status = "🟢 ONLINE" if self.mt5 and self.mt5.is_connected() else "🟡 SIMULATION"

        text = Messages.dashboard(
            bot_status=bot_status,
            account=account_type,
            balance=balance,
            daily_pnl=today["total_pnl"],
            symbol=symbol,
            auto_running=auto_running,
            open_trades=open_trades,
        )

        await query.edit_message_text(
            text=text,
            reply_markup=Keyboards.main_dashboard(),
            parse_mode="Markdown",
        )

    async def _show_trade_settings(self, query, user_id: int):
        """Show trading settings"""
        db = get_db()
        symbol = db.get_setting(user_id, "symbol", "XAUUSD")
        lot = float(db.get_setting(user_id, "lot", str(config.trading.default_lot)))
        direction = db.get_setting(user_id, "direction", "both")

        text = Messages.trading_settings(symbol, lot, direction)
        await query.edit_message_text(
            text=text,
            reply_markup=Keyboards.trading_setup(),
            parse_mode="Markdown",
        )

    async def _show_ai_config(self, query, user_id: int):
        """Show AI configuration"""
        db = get_db()
        ai_cfg = db.get_ai_config(user_id)

        # Detect active provider
        provider = db.get_user_provider(user_id) or "deepseek"

        text = Messages.ai_settings(
            confidence=ai_cfg.confidence_threshold,
            mode=ai_cfg.analysis_mode,
            news_enabled=ai_cfg.news_check_enabled,
            timeframe=ai_cfg.prediction_timeframe,
            backtest=ai_cfg.backtest_mode,
            provider=provider,
            news_guard_enabled=ai_cfg.news_guard_enabled,
        )

        await query.edit_message_text(
            text=text,
            reply_markup=Keyboards.ai_config(news_guard_enabled=ai_cfg.news_guard_enabled),
            parse_mode="Markdown",
        )

    async def _show_risk_status(self, query, user_id: int):
        """Show risk status"""
        risk_status = self.risk.get_risk_status(user_id) if self.risk else {}

        text = Messages.risk_status(risk_status)
        await query.edit_message_text(
            text=text,
            reply_markup=Keyboards.risk_menu(),
            parse_mode="Markdown",
        )

    async def _show_reports(self, query, user_id: int):
        """Show reports menu"""
        db = get_db()
        daily = db.get_today_performance(user_id)
        all_time = db.get_all_time_performance(user_id)
        balance = self.mt5.get_balance() if self.mt5 else 42500.0

        text = Messages.performance_report(daily, all_time, balance)
        await query.edit_message_text(
            text=text,
            reply_markup=Keyboards.reports_menu(),
            parse_mode="Markdown",
        )

    async def _show_provider_status(self, query, user_id: int):
        """Show API key status for all providers"""
        db = get_db()
        api_keys = db.get_user_api_keys(user_id)

        # Build status for each provider
        keys_status = []
        for provider_id, info in PROVIDER_INFO.items():
            provider_key = next(
                (k for k in api_keys if k["provider"] == provider_id),
                None
            )
            keys_status.append({
                "provider": provider_id,
                "name": info["name"],
                "has_key": provider_key is not None and provider_key.get("is_valid", False),
                "model": provider_key.get("model", "default") if provider_key else "N/A",
            })

        text = Messages.provider_status(keys_status)
        await query.edit_message_text(
            text=text,
            reply_markup=Keyboards.ai_providers(),
            parse_mode="Markdown",
        )

    # ─── Action Handlers ──────────────────────────

    async def _handle_symbol_select(self, query, user_id: int, data: str):
        """Handle symbol selection"""
        symbol = data.replace("symbol_", "")

        # Validate symbol against whitelist
        if symbol not in config.symbols:
            await query.answer("❌ Invalid symbol selected")
            return

        db = get_db()
        db.set_setting(user_id, "symbol", symbol)

        symbol_name = config.symbols.get(symbol, symbol)
        await query.answer(f"✅ Selected: {symbol_name}")
        await self._show_trade_settings(query, user_id)

    async def _handle_lot_select(self, query, user_id: int, data: str):
        """Handle lot size selection"""
        lot = float(data.replace("lot_", ""))
        db = get_db()
        db.set_setting(user_id, "lot", str(lot))
        await query.answer(f"✅ Lot: {lot}")
        await self._show_trade_settings(query, user_id)

    async def _handle_direction_select(self, query, user_id: int, data: str):
        """Handle direction selection"""
        direction = data.replace("dir_", "")
        db = get_db()
        db.set_setting(user_id, "direction", direction)

        names = {"buy": "Buy Only 🟢", "sell": "Sell Only 🔴", "both": "Both Directions 🔄"}
        await query.answer(f"✅ {names.get(direction, direction)}")
        await self._show_trade_settings(query, user_id)

    async def _handle_auto_start(self, query, user_id: int):
        """Start auto trading"""
        # Check if any API key is configured
        db = get_db()
        provider = db.get_user_provider(user_id)

        if not provider:
            await query.edit_message_text(
                "❌ **No AI Provider configured!**\n\n"
                "Please set up your AI provider first:\n"
                "1️⃣ Go to 🤖 AI Settings\n"
                "2️⃣ Tap 🔑 AI Provider & API Key\n"
                "3️⃣ Select a provider and enter your API key",
                reply_markup=Keyboards.back_button("menu_ai"),
                parse_mode="Markdown",
            )
            return

        if not self.analyzer or not self.executor:
            await query.edit_message_text(
                "❌ Trading components not initialized",
                reply_markup=Keyboards.back_button(),
            )
            return

        self.auto_trading[user_id] = True
        # Do NOT blindly resume trading — if risk paused the user (daily loss / panic),
        # can_open_trade in the next cycle will block appropriately.
        # Only resume if we know it was a manual pause, not a system pause.
        if self.risk and self.risk.trading_paused.get(user_id) and not self.risk.panic_mode.get(user_id):
            self.risk.resume_trading(user_id)

        await query.answer("✅ Auto trading started")

        # Run first cycle immediately using background scheduler logic
        # (avoids blocking the UI with a full analysis cycle here)
        await query.edit_message_text(
            "🚀 Auto trading is now active!\n\n"
            "The bot will analyze and trade automatically every 5 minutes.\n"
            "You can pause anytime with the 🛑 Pause button.",
            reply_markup=Keyboards.main_dashboard(),
            parse_mode="Markdown",
        )

    async def _handle_auto_stop(self, query, user_id: int):
        """Stop auto trading"""
        self.auto_trading[user_id] = False
        if self.risk:
            self.risk.pause_trading(user_id)

        await query.answer("⏸️ Auto trading paused")
        await self._show_dashboard(query, user_id)

    async def _handle_top5(self, query, user_id: int):
        """Handle Top 5 Forex button"""
        if not self.analyzer:
            await query.edit_message_text(
                "❌ Market analyzer not initialized",
                reply_markup=Keyboards.back_button(),
            )
            return

        await query.edit_message_text(
            "🏆 Scanning Top 5 Forex opportunities...",
        )

        try:
            results = self.analyzer.analyze_top5(user_id=user_id)
            top5_text = Messages.top5_result(results)

            await query.edit_message_text(
                text=top5_text,
                reply_markup=Keyboards.back_button("main_menu"),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Top5 callback error: {e}")
            await query.edit_message_text(
                f"❌ Top 5 error: {e}",
                reply_markup=Keyboards.back_button(),
            )

    async def _handle_analyze_now(self, query, user_id: int, auto_mode: bool = False):
        """Analyze market now"""
        db = get_db()
        symbol = db.get_setting(user_id, "symbol", "XAUUSD")
        tf = db.get_setting(user_id, "timeframe", "M15")

        if not self.analyzer:
            await query.edit_message_text(
                "❌ Market analyzer not initialized",
                reply_markup=Keyboards.back_button(),
            )
            return

        await query.edit_message_text(
            f"⏳ Analyzing {symbol} ({tf}) with AI...",
        )

        try:
            # Analyze market
            result = self.analyzer.analyze(symbol, tf, user_id=user_id)

            if result.get("error"):
                await query.edit_message_text(
                    f"❌ {result.get('message', 'Error')}",
                    reply_markup=Keyboards.main_dashboard(),
                )
                return

            analysis_text = Messages.analysis_result(result)

            # If auto trading is active and confidence is sufficient
            trade_executed = False
            if auto_mode and self.executor and self.auto_trading.get(user_id):
                # Check for quota/rate limit errors that should stop trading
                if result.get("should_stop") or result.get("error") == "QUOTA_EXCEEDED":
                    self.auto_trading[user_id] = False
                    if self.risk:
                        self.risk.pause_trading(user_id)
                    analysis_text += (
                        "\n\n───\n"
                        "⚠️ **Trading auto-paused!**\n"
                        f"{result.get('reasoning', 'API quota or rate limit exceeded.')}\n"
                        "Please check your billing and update your API key."
                    )
                    await query.edit_message_text(
                        text=analysis_text,
                        reply_markup=Keyboards.main_dashboard(),
                        parse_mode="Markdown",
                    )
                    # Send urgent notification
                    await self.notifications.send_alert(
                        user_id,
                        "warning",
                        "Trading Paused - API Quota Exceeded\n\n"
                        f"Your AI provider quota has been reached. "
                        f"Please update your API key or billing.\n\n"
                        f"Go to 🤖 AI Settings → 🔑 AI Provider to update."
                    )
                    return

                confidence = result.get("confidence", 0)
                ai_cfg = db.get_ai_config(user_id)

                if confidence >= ai_cfg.confidence_threshold:
                    # Use execute_from_analysis to avoid double-analysis
                    trade_result = self.executor.execute_from_analysis(
                        user_id, symbol, tf, result
                    )
                    if trade_result.get("trade_executed"):
                        analysis_text += "\n\n───\n" + trade_result["message"]
                        trade_executed = True

                        # Send notification
                        if trade_result.get("trade"):
                            await self.notifications.send_trade_opened(
                                user_id, trade_result["trade"]
                            )

            keyboard = Keyboards.main_dashboard() if not auto_mode else Keyboards.back_button("main_menu")

            await query.edit_message_text(
                text=analysis_text,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )

        except Exception as e:
            logger.error(f"Analysis error: {e}")
            await query.edit_message_text(
                f"❌ Error: {e}",
                reply_markup=Keyboards.back_button(),
            )

    async def _handle_validate_key(self, query, user_id: int, provider: str):
        """Validate an API key"""
        db = get_db()

        # Show validating message
        info = PROVIDER_INFO.get(provider, {})
        provider_name = info.get("name", provider.title()) if isinstance(info, dict) else provider.title()

        await query.edit_message_text(
            Messages.api_key_validating(provider),
            parse_mode="Markdown",
        )

        try:
            decrypted = db.get_decrypted_api_key(user_id, provider)
            if not decrypted:
                await query.edit_message_text(
                    Messages.api_key_invalid(provider, "No API key found. Please set your key first."),
                    reply_markup=Keyboards.provider_setup(provider, provider_name),
                    parse_mode="Markdown",
                )
                return

            result = AIManager.validate_key(provider, decrypted)
            db.update_key_validation(
                user_id, provider,
                is_valid=result.get("valid", False),
                message=result.get("message", "")
            )

            if result.get("valid"):
                await query.edit_message_text(
                    Messages.api_key_valid(provider),
                    reply_markup=Keyboards.provider_setup(provider, provider_name),
                    parse_mode="Markdown",
                )
            else:
                await query.edit_message_text(
                    Messages.api_key_invalid(provider, result.get("message", "")),
                    reply_markup=Keyboards.provider_setup(provider, provider_name),
                    parse_mode="Markdown",
                )

        except Exception as e:
            logger.error(f"Key validation error: {e}")
            await query.edit_message_text(
                Messages.api_key_invalid(provider, str(e)),
                reply_markup=Keyboards.provider_setup(provider, provider_name),
                parse_mode="Markdown",
            )

    async def _handle_confidence_select(self, query, user_id: int, data: str):
        """Handle confidence threshold selection"""
        confidence = float(data.replace("conf_", ""))
        db = get_db()
        db.update_ai_config(user_id, confidence_threshold=confidence)
        await query.answer(f"✅ Min confidence: {confidence:.0f}%")
        await self._show_ai_config(query, user_id)

    async def _handle_mode_select(self, query, user_id: int, data: str):
        """Handle analysis mode selection"""
        mode = data.replace("mode_", "")
        db = get_db()
        db.update_ai_config(user_id, analysis_mode=mode)

        names = {
            "predictive": "Predictive Analysis",
            "news_scanning": "News Scanning",
            "hybrid": "Hybrid",
        }
        await query.answer(f"✅ Analysis mode: {names.get(mode, mode)}")
        await self._show_ai_config(query, user_id)

    async def _toggle_news(self, query, user_id: int):
        """Toggle news checking"""
        db = get_db()
        ai_cfg = db.get_ai_config(user_id)
        new_val = not ai_cfg.news_check_enabled
        db.update_ai_config(user_id, news_check_enabled=new_val)
        await query.answer(f"✅ News check: {'Enabled' if new_val else 'Disabled'}")
        await self._show_ai_config(query, user_id)

    async def _handle_timeframe_select(self, query, user_id: int, data: str):
        """Handle timeframe selection"""
        tf = data.replace("tf_", "")
        db = get_db()
        db.update_ai_config(user_id, prediction_timeframe=tf)
        await query.answer(f"✅ Timeframe: {tf}")
        await self._show_ai_config(query, user_id)

    async def _toggle_newsguard(self, query, user_id: int):
        """Toggle NewsGuard auto-close on high-impact news"""
        db = get_db()
        ai_cfg = db.get_ai_config(user_id)
        new_val = not ai_cfg.news_guard_enabled
        db.update_ai_config(user_id, news_guard_enabled=new_val)
        await query.answer(f"🛡️ NewsGuard: {'Enabled' if new_val else 'Disabled'}")
        await self._show_ai_config(query, user_id)

    # ─── Backtest Helpers ─────────────────────────

    async def _show_backtest_menu(self, query, user_id: int):
        """Show backtest configuration menu"""
        db = get_db()
        symbol = db.get_setting(user_id, "backtest_symbol", "XAUUSD")
        tf = db.get_setting(user_id, "backtest_timeframe", "D1")
        strategy = db.get_setting(user_id, "backtest_strategy", "indicators")

        text = Messages.backtest_config(symbol, tf, strategy)
        await query.edit_message_text(
            text=text,
            reply_markup=Keyboards.backtest_menu(symbol, tf, strategy),
            parse_mode="Markdown",
        )

    async def _handle_backtest_symbol(self, query, user_id: int, data: str):
        """Handle backtest symbol selection"""
        symbol = data.replace("backtest_symbol_", "")
        db = get_db()
        db.set_setting(user_id, "backtest_symbol", symbol)
        await query.answer(f"✅ Asset: {symbol}")
        await self._show_backtest_menu(query, user_id)

    async def _handle_backtest_tf(self, query, user_id: int, data: str):
        """Handle backtest timeframe selection"""
        tf = data.replace("backtest_tf_", "")
        db = get_db()
        db.set_setting(user_id, "backtest_timeframe", tf)
        await query.answer(f"✅ Timeframe: {tf}")
        await self._show_backtest_menu(query, user_id)

    async def _handle_backtest_strategy(self, query, user_id: int, data: str):
        """Handle backtest strategy selection"""
        strategy = data.replace("backtest_strategy_", "")
        db = get_db()
        db.set_setting(user_id, "backtest_strategy", strategy)
        await query.answer(f"✅ Strategy: {strategy.title()}")
        await self._show_backtest_menu(query, user_id)

    async def _run_backtest(self, query, user_id: int):
        """Run the backtest and display results"""
        import asyncio
        from functools import partial

        db = get_db()
        symbol = db.get_setting(user_id, "backtest_symbol", "XAUUSD")
        tf = db.get_setting(user_id, "backtest_timeframe", "D1")
        strategy = db.get_setting(user_id, "backtest_strategy", "indicators")

        # Validate symbol
        if symbol not in config.symbols:
            await query.answer("❌ Invalid symbol")
            return

        await query.edit_message_text(
            Messages.backtest_running(symbol, tf, strategy),
            parse_mode="Markdown",
        )

        try:
            # Run CPU-intensive backtest in thread pool to avoid blocking Telegram bot
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None,
                partial(
                    self.backtester.run,
                    symbol=symbol,
                    timeframe=tf,
                    strategy=strategy,
                    start_days=365,
                    initial_balance=10_000.0,
                    volume=0.1,
                    user_id=user_id,
                ),
            )

            if not result.success:
                await query.edit_message_text(
                    f"❌ Backtest failed:\n\n{result.message}",
                    reply_markup=Keyboards.back_button("menu_backtest"),
                    parse_mode="Markdown",
                )
                return

            # Save to database
            db_data = Backtester.serialize_for_db(result)
            db.save_backtest(user_id, db_data)

            # Show result
            report_text = BacktestReport.summary(result)
            await query.edit_message_text(
                text=report_text,
                reply_markup=Keyboards.back_button("menu_backtest"),
                parse_mode="Markdown",
            )

        except Exception as e:
            logger.error(f"Backtest error: {e}")
            await query.edit_message_text(
                f"❌ Backtest error: {e}",
                reply_markup=Keyboards.back_button("menu_backtest"),
                parse_mode="Markdown",
            )

    async def _show_backtest_history(self, query, user_id: int):
        """Show backtest history"""
        db = get_db()
        backtests = db.get_backtests(user_id, limit=10)

        if not backtests:
            text = BacktestReport.no_backtests()
            await query.edit_message_text(
                text=text,
                reply_markup=Keyboards.back_button("menu_reports"),
                parse_mode="Markdown",
            )
            return

        text = BacktestReport.history_list(backtests)
        await query.edit_message_text(
            text=text,
            reply_markup=Keyboards.backtest_history(backtests),
            parse_mode="Markdown",
        )

    async def _view_backtest(self, query, user_id: int, data: str):
        """View a specific backtest result"""
        try:
            backtest_id = int(data.replace("backtest_view_", ""))
        except ValueError:
            await query.edit_message_text(
                "❌ Invalid backtest ID.",
                reply_markup=Keyboards.back_button("backtest_history"),
                parse_mode="Markdown",
            )
            return

        db = get_db()
        bt = db.get_backtest_by_id(backtest_id, user_id)

        if not bt:
            await query.edit_message_text(
                "❌ Backtest not found.",
                reply_markup=Keyboards.back_button("backtest_history"),
                parse_mode="Markdown",
            )
            return

        # Reconstruct minimal result for display
        from trading.backtester import BacktestResult as BTR
        result = BTR(
            success=True,
            symbol=bt.symbol,
            timeframe=bt.timeframe,
            strategy=bt.strategy,
            start_date=bt.start_date,
            end_date=bt.end_date,
            initial_balance=bt.initial_balance,
            final_balance=bt.final_balance,
            total_trades=bt.total_trades,
            winning_trades=bt.winning_trades,
            losing_trades=bt.losing_trades,
            win_rate=bt.win_rate,
            profit_factor=bt.profit_factor,
            total_return_pct=bt.total_return_pct,
            max_drawdown_pct=bt.max_drawdown_pct,
            sharpe_ratio=bt.sharpe_ratio,
            sortino_ratio=bt.sortino_ratio,
            avg_trade_return=bt.avg_trade_return,
            avg_win=bt.avg_win,
            avg_loss=bt.avg_loss,
            largest_win=bt.largest_win,
            largest_loss=bt.largest_loss,
        )

        report_text = BacktestReport.summary(result)
        await query.edit_message_text(
            text=report_text,
            reply_markup=Keyboards.back_button("backtest_history"),
            parse_mode="Markdown",
        )
