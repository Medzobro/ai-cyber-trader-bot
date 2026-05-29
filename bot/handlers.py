"""
Telegram Bot Handlers - معالجات البوت
======================================
جميع handlers و callbacks للبوت
"""
import traceback
from datetime import datetime
from typing import Optional, Dict, Any

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

from config import config, get_config
from utils.logger import get_logger
from utils.helpers import format_currency, format_percentage
from database.db_manager import get_db
from .keyboards import Keyboards
from .messages import Messages
from .notifications import NotificationManager

logger = get_logger(__name__)


class TelegramBot:
    """بوت تليجرام الرئيسي"""

    def __init__(self, mt5_bridge=None, risk_manager=None,
                 trade_executor=None, market_analyzer=None,
                 predictor=None):
        self.mt5 = mt5_bridge
        self.risk = risk_manager
        self.executor = trade_executor
        self.analyzer = market_analyzer
        self.predictor = predictor
        self.notifications = NotificationManager()

        # حالات التداول الآلي
        self.auto_trading: Dict[int, bool] = {}

        # مهام التداول المجدولة
        self.scheduled_jobs: Dict[int, Any] = {}

        self.app: Optional[Application] = None
        self.db = get_db()

    async def start(self):
        """بدء البوت"""
        token = config.telegram.bot_token

        if token == "YOUR_TELEGRAM_BOT_TOKEN":
            logger.error("❌ Please set TELEGRAM_BOT_TOKEN in .env file")
            return

        self.app = Application.builder().token(token).build()
        self.notifications.set_app(self.app)

        # تسجيل المعالجات
        self._register_handlers()

        logger.info("✅ Telegram bot started. Waiting for commands...")
        await self.app.run_polling(allowed_updates=Update.ALL_TYPES)

    async def stop(self):
        """إيقاف البوت"""
        if self.app:
            await self.app.stop()
            await self.app.shutdown()
        logger.info("🛑 Bot stopped")

    def _register_handlers(self):
        """تسجيل جميع معالجات الأوامر والأزرار"""
        # Commands
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CommandHandler("analyze", self.cmd_analyze))
        self.app.add_handler(CommandHandler("report", self.cmd_report))
        self.app.add_handler(CommandHandler("settings", self.cmd_settings))
        self.app.add_handler(CommandHandler("panic", self.cmd_panic))

        # Callbacks (inline buttons)
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))

        # Text messages (custom lot, etc.)
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_message
        ))

        # Error handler
        self.app.add_error_handler(self.handle_error)

    # ─── Command Handlers ─────────────────────────

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /start - القائمة الرئيسية"""
        user = update.effective_user
        db = get_db()
        db_user = db.get_or_create_user(
            user.id, user.username, user.first_name
        )

        # إعدادات المستخدم الافتراضية
        lot = db.get_setting(user.id, "lot", str(config.trading.default_lot))
        direction = db.get_setting(user.id, "direction", "both")
        symbol = db.get_setting(user.id, "symbol", config.trading.default_symbol)

        # معلومات الحساب
        balance = self.mt5.get_balance() if self.mt5 else 42500.0
        account_type = "MT5 Real" if self.mt5 and not self.mt5.simulation else "MT5 Demo"

        # أداء اليوم
        today = db.get_today_performance(user.id)
        open_trades = db.get_open_trades_count(user.id)

        # حالة البوت
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
        """أمر /help"""
        await update.message.reply_text(
            Messages.help_message(),
            reply_markup=Keyboards.back_button(),
            parse_mode="Markdown",
        )

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /status"""
        user = update.effective_user
        db = get_db()
        user_id = user.id

        risk_status = self.risk.get_risk_status(user_id) if self.risk else {}
        open_trades_count = db.get_open_trades_count(user_id)

        auto_running = self.auto_trading.get(user_id, False)

        status_text = (
            "📊 **حالة النظام**\n\n"
            f"🔹 **البوت:** {'🟢 يعمل' if self.app else '🔴 متوقف'}\n"
            f"🔹 **التداول الآلي:** {'🟢 مفعل' if auto_running else '🔴 متوقف'}\n"
            f"🔹 **MT5:** {'✅ متصل' if self.mt5 and self.mt5.is_connected() else '🟡 محاكاة'}\n"
            f"🔹 **صفقات مفتوحة:** {open_trades_count}\n"
            f"🔹 **مستوى المخاطرة:** {risk_status.get('risk_level', 'N/A')}\n"
        )

        await update.message.reply_text(
            status_text,
            reply_markup=Keyboards.main_dashboard(),
            parse_mode="Markdown",
        )

    async def cmd_analyze(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /analyze - تحليل السوق الحالي"""
        user = update.effective_user
        user_id = user.id
        db = get_db()

        symbol = db.get_setting(user_id, "symbol", "XAUUSD")
        tf = db.get_setting(user_id, "timeframe", "M15")

        if not self.analyzer:
            await update.message.reply_text("❌ محلل السوق غير مهيأ")
            return

        # إرسال رسالة انتظار
        sent_msg = await update.message.reply_text(
            f"⏳ جاري تحليل {symbol} ({tf}) باستخدام DeepSeek AI...",
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
                f"❌ خطأ في التحليل: {e}",
                reply_markup=Keyboards.back_button(),
            )

    async def cmd_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """أمر /report"""
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
        """أمر /settings"""
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
        """أمر /panic - زر الطوارئ"""
        await update.message.reply_text(
            "🚨 **تحذير: هل أنت متأكد من إغلاق جميع الصفقات المفتوحة؟**\n\n"
            "سيتم إغلاق جميع المراكز فوراً بسعر السوق.",
            reply_markup=Keyboards.confirm_panic(),
            parse_mode="Markdown",
        )

    # ─── Callback Handler ─────────────────────────

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الأزرار الرئيسي"""
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
                    "📊 اختر المؤشر:",
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
                    "🎯 اختر الحد الأدنى لنسبة الثقة:",
                    reply_markup=Keyboards.confidence_levels(),
                )
            elif data.startswith("conf_"):
                await self._handle_confidence_select(query, user_id, data)
            elif data == "ai_model":
                await query.edit_message_text(
                    "🧠 اختر نمط التحليل:",
                    reply_markup=Keyboards.analysis_modes(),
                )
            elif data.startswith("mode_"):
                await self._handle_mode_select(query, user_id, data)
            elif data == "ai_news":
                await self._toggle_news(query, user_id)
            elif data == "ai_timeframe":
                await query.edit_message_text(
                    "⏱️ اختر الإطار الزمني للتحليل:",
                    reply_markup=Keyboards.timeframes(),
                )
            elif data.startswith("tf_"):
                await self._handle_timeframe_select(query, user_id, data)
            elif data == "ai_backtest":
                await self._toggle_backtest(query, user_id)
            elif data == "ai_train":
                await query.edit_message_text(
                    "🚧 جاري تطوير هذه الميزة...\nتدريب نموذج ML على البيانات التاريخية.",
                    reply_markup=Keyboards.back_button("menu_ai"),
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
                    "📅 **أداء اليوم**\n\n"
                    f"💰 الأرباح: {format_currency(daily['total_pnl'])} ({format_percentage(pnl_pct)})\n"
                    f"📊 الصفقات: {daily['total_trades']}\n"
                    f"✅ الرابحة: {daily['winning_trades']}\n"
                    f"❌ الخاسرة: {daily['losing_trades']}\n"
                    f"🎯 نسبة النجاح: {daily['win_rate']:.1f}%"
                )
                await query.edit_message_text(
                    text,
                    reply_markup=Keyboards.reports_menu(),
                    parse_mode="Markdown",
                )
            elif data == "report_all":
                all_time = db.get_all_time_performance(user_id)
                text = (
                    "📈 **الأداء الكلي**\n\n"
                    f"💰 إجمالي الأرباح: {format_currency(all_time['total_pnl'])}\n"
                    f"📊 إجمالي الصفقات: {all_time['total_trades']}\n"
                    f"✅ الرابحة: {all_time['winning_trades']}\n"
                    f"❌ الخاسرة: {all_time['losing_trades']}\n"
                    f"🎯 نسبة النجاح: {all_time['win_rate']:.1f}%"
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
                await query.edit_message_text(
                    "🧪 **وضع المحاكاة (Backtest)**\n\n"
                    "هذه الميزة تسمح بتشغيل استراتيجية التداول على بيانات تاريخية\n"
                    "لتقييم الأداء قبل المخاطرة بأموال حقيقية.\n\n"
                    "🚧 قيد التطوير...",
                    reply_markup=Keyboards.back_button("menu_reports"),
                )

            # Risk Management
            elif data == "menu_risk":
                await self._show_risk_status(query, user_id)
            elif data == "risk_status":
                await self._show_risk_status(query, user_id)
            elif data == "risk_daily_loss":
                await query.edit_message_text(
                    "⚠️ **حد الخسارة اليومية**\n\n"
                    f"الحد الحالي: {config.trading.max_daily_loss}%\n"
                    "عند تجاوز هذا الحد، يتوقف التداول تلقائياً لليوم.\n\n"
                    "🚧 قيد التطوير...",
                    reply_markup=Keyboards.risk_menu(),
                )
            elif data == "risk_max_trades":
                await query.edit_message_text(
                    "📦 **الحد الأعلى للصفقات المفتوحة**\n\n"
                    f"الحد الحالي: {config.trading.max_open_trades} صفقات\n\n"
                    "🚧 قيد التطوير...",
                    reply_markup=Keyboards.risk_menu(),
                )

            # Panic
            elif data == "panic":
                await query.edit_message_text(
                    "🚨 **تحذير: إغلاق كل الصفقات فوراً**\n\n"
                    "سيتم إغلاق جميع المراكز المفتوحة بسعر السوق.",
                    reply_markup=Keyboards.confirm_panic(),
                    parse_mode="Markdown",
                )
            elif data == "panic_confirm":
                if self.risk:
                    closed = self.risk.activate_panic(user_id)
                    if self.mt5:
                        closed = self.mt5.close_all_positions()
                    await query.edit_message_text(
                        f"🚨 **تم تنفيذ أمر الطوارئ!**\n\nتم إغلاق {closed} صفقة بنجاح.\n"
                        "وضع الطوارئ مفعل - التداول متوقف.",
                        reply_markup=Keyboards.back_button(),
                        parse_mode="Markdown",
                    )
                else:
                    await query.edit_message_text(
                        "❌ مدير المخاطر غير مهيأ",
                        reply_markup=Keyboards.back_button(),
                    )

            # Analyze Now
            elif data == "analyze_now":
                await self._handle_analyze_now(query, user_id)

            else:
                await query.edit_message_text(
                    f"⚠️ أمر غير معروف: {data}",
                    reply_markup=Keyboards.back_button(),
                )

        except Exception as e:
            logger.error(f"Callback error: {e}\n{traceback.format_exc()}")
            try:
                await query.edit_message_text(
                    f"❌ حدث خطأ: {e}",
                    reply_markup=Keyboards.back_button(),
                )
            except Exception:
                pass

    # ─── Message Handler ──────────────────────────

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الرسائل النصية"""
        user = update.effective_user
        user_id = user.id
        text = update.message.text.strip()
        db = get_db()

        # إذا كان في انتظار إدخال اللوت المخصص
        if context.user_data.get("awaiting_lot"):
            try:
                lot = float(text)
                if lot < config.trading.min_lot or lot > config.trading.max_lot:
                    await update.message.reply_text(
                        f"⚠️ اللوت يجب أن يكون بين {config.trading.min_lot} و {config.trading.max_lot}",
                        reply_markup=Keyboards.lot_sizes(),
                    )
                    return

                db.set_setting(user_id, "lot", str(lot))
                context.user_data["awaiting_lot"] = False

                symbol = db.get_setting(user_id, "symbol", "XAUUSD")
                direction = db.get_setting(user_id, "direction", "both")

                await update.message.reply_text(
                    f"✅ تم تعيين اللوت إلى: **{lot}**\n\n"
                    + Messages.trading_settings(symbol, lot, direction),
                    reply_markup=Keyboards.trading_setup(),
                    parse_mode="Markdown",
                )
            except ValueError:
                await update.message.reply_text(
                    "❌ يرجى إدخال رقم صحيح. مثال: `0.25`",
                    reply_markup=Keyboards.lot_sizes(),
                )

    # ─── Error Handler ────────────────────────────

    async def handle_error(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """معالج الأخطاء"""
        logger.error(f"Update {update} caused error: {context.error}")
        if context.error:
            logger.error(traceback.format_exception(None, context.error, context.error.__traceback__))

    # ─── Helper Methods ───────────────────────────

    async def _show_dashboard(self, query, user_id: int):
        """عرض لوحة التحكم الرئيسية"""
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
        """عرض إعدادات التداول"""
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
        """عرض إعدادات الذكاء الاصطناعي"""
        db = get_db()
        ai_cfg = db.get_ai_config(user_id)

        text = Messages.ai_settings(
            confidence=ai_cfg.confidence_threshold,
            mode=ai_cfg.analysis_mode,
            news_enabled=ai_cfg.news_check_enabled,
            timeframe=ai_cfg.prediction_timeframe,
            backtest=ai_cfg.backtest_mode,
        )

        await query.edit_message_text(
            text=text,
            reply_markup=Keyboards.ai_config(),
            parse_mode="Markdown",
        )

    async def _show_risk_status(self, query, user_id: int):
        """عرض حالة المخاطر"""
        risk_status = self.risk.get_risk_status(user_id) if self.risk else {}

        text = Messages.risk_status(risk_status)
        await query.edit_message_text(
            text=text,
            reply_markup=Keyboards.risk_menu(),
            parse_mode="Markdown",
        )

    async def _show_reports(self, query, user_id: int):
        """عرض قائمة التقارير"""
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

    # ─── Action Handlers ──────────────────────────

    async def _handle_symbol_select(self, query, user_id: int, data: str):
        """اختيار الأصل"""
        symbol = data.replace("symbol_", "")
        db = get_db()
        db.set_setting(user_id, "symbol", symbol)

        symbol_name = config.symbols.get(symbol, symbol)
        await query.answer(f"✅ تم اختيار {symbol_name}")
        await self._show_trade_settings(query, user_id)

    async def _handle_lot_select(self, query, user_id: int, data: str):
        """اختيار حجم اللوت"""
        lot = float(data.replace("lot_", ""))
        db = get_db()
        db.set_setting(user_id, "lot", str(lot))
        await query.answer(f"✅ اللوت: {lot}")
        await self._show_trade_settings(query, user_id)

    async def _handle_direction_select(self, query, user_id: int, data: str):
        """اختيار اتجاه التداول"""
        direction = data.replace("dir_", "")
        db = get_db()
        db.set_setting(user_id, "direction", direction)

        names = {"buy": "الشراء فقط 🟢", "sell": "البيع فقط 🔴", "both": "الاتجاهين 🔄"}
        await query.answer(f"✅ {names.get(direction, direction)}")
        await self._show_trade_settings(query, user_id)

    async def _handle_auto_start(self, query, user_id: int):
        """تشغيل التداول الآلي"""
        # التحقق من الـ API Key
        if config.deepseek.api_key == "YOUR_DEEPSEEK_API_KEY":
            await query.edit_message_text(
                "❌ **يجب إدخال DeepSeek API Key أولاً**\n\n"
                "1. قم بإنشاء ملف `.env` في مجلد المشروع\n"
                "2. أضف: `DEEPSEEK_API_KEY=sk-xxxxxxxx`\n"
                "3. أعد تشغيل البوت",
                reply_markup=Keyboards.back_button(),
                parse_mode="Markdown",
            )
            return

        if not self.analyzer or not self.executor:
            await query.edit_message_text(
                "❌ مكونات التداول غير مهيأة",
                reply_markup=Keyboards.back_button(),
            )
            return

        self.auto_trading[user_id] = True
        if self.risk:
            self.risk.resume_trading(user_id)

        await query.answer("✅ تم تشغيل التداول الآلي")

        # تنفيذ أول تحليل فوري
        await self._handle_analyze_now(query, user_id, auto_mode=True)

    async def _handle_auto_stop(self, query, user_id: int):
        """إيقاف التداول الآلي"""
        self.auto_trading[user_id] = False
        if self.risk:
            self.risk.pause_trading(user_id)

        await query.answer("⏸️ تم إيقاف التداول الآلي")
        await self._show_dashboard(query, user_id)

    async def _handle_analyze_now(self, query, user_id: int, auto_mode: bool = False):
        """تحليل السوق الآن"""
        db = get_db()
        symbol = db.get_setting(user_id, "symbol", "XAUUSD")
        tf = db.get_setting(user_id, "timeframe", "M15")

        if not self.analyzer:
            await query.edit_message_text(
                "❌ محلل السوق غير مهيأ",
                reply_markup=Keyboards.back_button(),
            )
            return

        await query.edit_message_text(
            f"⏳ جاري تحليل {symbol} ({tf}) باستخدام DeepSeek AI...",
        )

        try:
            # تحليل السوق
            result = self.analyzer.analyze(symbol, tf, user_id=user_id)

            if result.get("error"):
                await query.edit_message_text(
                    f"❌ {result.get('message', 'خطأ')}",
                    reply_markup=Keyboards.main_dashboard(),
                )
                return

            analysis_text = Messages.analysis_result(result)

            # إذا كان التداول الآلي مفعل والثقة كافية
            trade_executed = False
            if auto_mode and self.executor and self.auto_trading.get(user_id):
                confidence = result.get("confidence", 0)
                ai_cfg = db.get_ai_config(user_id)

                if confidence >= ai_cfg.confidence_threshold:
                    trade_result = self.executor.execute_analysis_cycle(
                        user_id, symbol, tf
                    )
                    if trade_result.get("trade_executed"):
                        analysis_text += "\n\n───\n" + trade_result["message"]
                        trade_executed = True

                        # إشعار
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
                f"❌ خطأ: {e}",
                reply_markup=Keyboards.back_button(),
            )

    async def _handle_confidence_select(self, query, user_id: int, data: str):
        """تحديد نسبة الثقة"""
        confidence = float(data.replace("conf_", ""))
        db = get_db()
        db.update_ai_config(user_id, confidence_threshold=confidence)
        await query.answer(f"✅ الحد الأدنى للثقة: {confidence:.0f}%")
        await self._show_ai_config(query, user_id)

    async def _handle_mode_select(self, query, user_id: int, data: str):
        """تحديد نمط التحليل"""
        mode = data.replace("mode_", "")
        db = get_db()
        db.update_ai_config(user_id, analysis_mode=mode)

        names = {
            "predictive": "التحليل التنبئي",
            "news_scanning": "فحص الأخبار",
            "hybrid": "الهجين",
        }
        await query.answer(f"✅ نمط التحليل: {names.get(mode, mode)}")
        await self._show_ai_config(query, user_id)

    async def _toggle_news(self, query, user_id: int):
        """تبديل فحص الأخبار"""
        db = get_db()
        ai_cfg = db.get_ai_config(user_id)
        new_val = not ai_cfg.news_check_enabled
        db.update_ai_config(user_id, news_check_enabled=new_val)
        await query.answer(f"✅ فحص الأخبار: {'مفعل' if new_val else 'معطل'}")
        await self._show_ai_config(query, user_id)

    async def _handle_timeframe_select(self, query, user_id: int, data: str):
        """اختيار الإطار الزمني"""
        tf = data.replace("tf_", "")
        db = get_db()
        db.update_ai_config(user_id, prediction_timeframe=tf)
        await query.answer(f"✅ الإطار الزمني: {tf}")
        await self._show_ai_config(query, user_id)

    async def _toggle_backtest(self, query, user_id: int):
        """تبديل وضع المحاكاة"""
        db = get_db()
        ai_cfg = db.get_ai_config(user_id)
        new_val = not ai_cfg.backtest_mode
        db.update_ai_config(user_id, backtest_mode=new_val)
        await query.answer(f"✅ وضع المحاكاة: {'مفعل' if new_val else 'معطل'}")
        await self._show_ai_config(query, user_id)
