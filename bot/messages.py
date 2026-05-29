"""
Messages - نصوص الرسائل والقوالب
==================================
جميع قوالب النصوص المستخدمة في البوت
"""
from typing import Dict, Any
from datetime import datetime

from config import config
from utils.helpers import format_currency, format_percentage


class Messages:
    """قوالب الرسائل"""

    # ─── Welcome / Start ──────────────────────────

    @staticmethod
    def welcome(first_name: str = "المتداول") -> str:
        """رسالة الترحيب"""
        return (
            f"👋 أهلاً بك يا {first_name} في\n"
            f"🤖 نظام التداول الذكي | AI Cyber-Trader\n\n"
            f"🚀 أنا بوت تداول آلي متكامل يعمل بالذكاء الاصطناعي "
            f"(DeepSeek AI) لتحليل الأسواق واتخاذ قرارات التداول "
            f"على منصة MetaTrader 5.\n\n"
            f"📌 استخدم الأزرار أدناه للتحكم الكامل بالبوت."
        )

    @staticmethod
    def start_guide() -> str:
        """دليل البدء السريع"""
        return (
            "📖 **دليل البدء السريع:**\n\n"
            "1️⃣ اذهب إلى ⚙️ إعدادات الصفقات واختر الأصل وحجم اللوت\n"
            "2️⃣ اذهب إلى 🤖 إعدادات الذكاء الاصطناعي واضبط الاستراتيجية\n"
            "3️⃣ اضغط 🚀 تشغيل التداول الآلي لبدء التحليل والتنفيذ\n"
            "4️⃣ راقب الصفقات من 📈 تقارير الأداء\n\n"
            "⚠️ تأكد من إدخال API Key الخاص بـ DeepSeek في ملف `.env`"
        )

    # ─── Dashboard ────────────────────────────────

    @staticmethod
    def dashboard(bot_status: str = "🟢 يعمل الآن (ONLINE)",
                  account: str = "MT5 - Demo",
                  balance: float = 42500.0,
                  daily_pnl: float = 0.0,
                  symbol: str = "XAUUSD",
                  auto_running: bool = False,
                  open_trades: int = 0) -> str:
        """لوحة التحكم الرئيسية"""

        # اسم الأصل
        symbol_name = config.symbols.get(symbol, symbol)

        # حالة التداول الآلي
        auto_status = "🟢 مفعل" if auto_running else "🔴 متوقف"

        # تنسيق الأرباح
        pnl_formatted = format_currency(daily_pnl)
        pnl_pct = (daily_pnl / balance * 100) if balance > 0 else 0
        pnl_pct_formatted = format_percentage(pnl_pct)

        return (
            "══════════════════════\n"
            "🤖 **نظام التداول الذكي | AI Cyber-Trader**\n"
            "══════════════════════\n\n"
            f"🔹 **حالة البوت:** {bot_status}\n"
            f"🔹 **التداول الآلي:** {auto_status}\n"
            f"🔹 **الحساب المتصل:** {account}\n"
            f"🔹 **الرصيد الحالي:** {format_currency(balance)}\n"
            f"🔹 **أرباح اليوم:** {pnl_formatted} ({pnl_pct_formatted})\n"
            f"🔹 **الأصل المختار:** {symbol_name} ({symbol})\n"
            f"🔹 **صفقات مفتوحة:** {open_trades}\n\n"
            "📊 استخدم الأزرار أدناه للتحكم"
        )

    # ─── Trading Settings ─────────────────────────

    @staticmethod
    def trading_settings(symbol: str = "XAUUSD",
                         lot: float = 0.01,
                         direction: str = "both") -> str:
        """إعدادات التداول الحالية"""
        symbol_name = config.symbols.get(symbol, symbol)

        direction_names = {
            "buy": "🟢 الشراء فقط",
            "sell": "🔴 البيع فقط",
            "both": "🔄 الاتجاهين معاً",
        }

        return (
            "⚙️ **إعدادات الصفقات الحالية**\n\n"
            f"🏆 **الأصل:** {symbol_name} ({symbol})\n"
            f"📦 **حجم اللوت:** {lot}\n"
            f"📊 **نوع العمليات:** {direction_names.get(direction, direction)}\n\n"
            "اختر ما تريد تغييره:"
        )

    @staticmethod
    def enter_custom_lot() -> str:
        """طلب إدخال لوت مخصص"""
        return (
            "✏️ **أدخل حجم اللوت المطلوب:**\n\n"
            "مثال: `0.25` أو `0.05`\n"
            f"النطاق المسموح: {config.trading.min_lot} - {config.trading.max_lot}"
        )

    # ─── AI Settings ──────────────────────────────

    @staticmethod
    def ai_settings(confidence: float = 70.0,
                    mode: str = "predictive",
                    news_enabled: bool = True,
                    timeframe: str = "M15",
                    backtest: bool = False) -> str:
        """إعدادات الذكاء الاصطناعي"""
        mode_names = {
            "predictive": "🧠 التحليل التنبئي الذكي",
            "news_scanning": "📰 فحص الأخبار الفوري",
            "hybrid": "🔀 هجين (تحليل + أخبار)",
        }

        return (
            "🤖 **إعدادات الذكاء الاصطناعي**\n\n"
            f"🧠 **النموذج:** DeepSeek AI (deepseek-chat)\n"
            f"📊 **نمط التحليل:** {mode_names.get(mode, mode)}\n"
            f"🎯 **الحد الأدنى للثقة:** {confidence:.0f}%\n"
            f"⏱️ **الإطار الزمني:** {timeframe}\n"
            f"📰 **فحص الأخبار:** {'✅ مفعل' if news_enabled else '❌ معطل'}\n"
            f"🧪 **وضع المحاكاة:** {'✅ مفعل' if backtest else '❌ معطل'}\n\n"
            "اختر ما تريد تغييره:"
        )

    # ─── Trade Notification ───────────────────────

    @staticmethod
    def trade_opened(trade: Dict[str, Any]) -> str:
        """إشعار فتح صفقة"""
        direction_emoji = "🟢" if trade.get("direction") == "buy" else "🔴"
        direction_name = "شراء (BUY)" if trade.get("direction") == "buy" else "بيع (SELL)"

        return (
            "🔔 **تنبيه: صفقة جديدة من الذكاء الاصطناعي!**\n\n"
            f"📥 **النوع:** {direction_emoji} {direction_name}\n"
            f"🏆 **الأصل:** {trade.get('symbol', 'N/A')}\n"
            f"🎯 **سعر الدخول:** {trade.get('open_price', 0)}\n"
            f"🛡️ **إيقاف الخسارة (SL):** {trade.get('stop_loss', 0)}\n"
            f"💰 **جني الأرباح (TP):** {trade.get('take_profit', 0)}\n"
            f"📦 **الحجم:** {trade.get('volume', 0)} لوت\n"
            f"🧠 **نسبة ثقة النموذج:** {trade.get('confidence', 0):.1f}%\n"
            f"🕐 **الوقت:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

    @staticmethod
    def trade_closed(trade: Dict[str, Any]) -> str:
        """إشعار إغلاق صفقة"""
        pnl = trade.get("pnl", 0)
        pnl_emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"

        return (
            "📢 **تنبيه: تم إغلاق صفقة**\n\n"
            f"🏆 **الأصل:** {trade.get('symbol', 'N/A')}\n"
            f"📥 **النوع:** {trade.get('direction', 'N/A')}\n"
            f"🎯 **سعر الإغلاق:** {trade.get('close_price', 0)}\n"
            f"💰 **الربح/الخسارة:** {pnl_emoji} ${pnl:,.2f}\n"
            f"🕐 **الوقت:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

    # ─── Reports ──────────────────────────────────

    @staticmethod
    def performance_report(daily: Dict[str, Any],
                           all_time: Dict[str, Any],
                           balance: float = 42500.0) -> str:
        """تقرير الأداء"""
        pnl_pct = (daily["total_pnl"] / balance * 100) if balance > 0 else 0

        return (
            "══════════════════════\n"
            "📊 **تقارير الأداء والأرباح**\n"
            "══════════════════════\n\n"
            "📅 **أداء اليوم:**\n"
            f"   💰 الأرباح: {format_currency(daily['total_pnl'])} "
            f"({format_percentage(pnl_pct)})\n"
            f"   📊 الصفقات: {daily['total_trades']}\n"
            f"   ✅ الرابحة: {daily['winning_trades']}\n"
            f"   ❌ الخاسرة: {daily['losing_trades']}\n"
            f"   🎯 نسبة النجاح: {daily['win_rate']:.1f}%\n\n"
            "📈 **الأداء الكلي:**\n"
            f"   💰 إجمالي الأرباح: {format_currency(all_time['total_pnl'])}\n"
            f"   📊 إجمالي الصفقات: {all_time['total_trades']}\n"
            f"   🎯 نسبة النجاح: {all_time['win_rate']:.1f}%\n"
        )

    @staticmethod
    def recent_trades(trades: list) -> str:
        """آخر الصفقات"""
        if not trades:
            return "📋 لا توجد صفقات حديثة."

        lines = ["📋 **آخر 10 صفقات:**\n"]
        for t in trades[:10]:
            pnl = t.pnl or 0
            pnl_emoji = "🟢" if pnl > 0 else "🔴"
            direction = "شراء" if t.direction == "buy" else "بيع"
            lines.append(
                f"{pnl_emoji} {t.symbol} | {direction} | "
                f"${pnl:+.2f} | {t.opened_at.strftime('%H:%M')}"
            )

        return "\n".join(lines)

    # ─── Risk Status ──────────────────────────────

    @staticmethod
    def risk_status(status: Dict[str, Any]) -> str:
        """حالة المخاطر"""
        risk_emoji = {
            "🟢 LOW": "🟢 منخفضة ✓",
            "🟡 MEDIUM": "🟡 متوسطة ⚠",
            "🟠 HIGH": "🟠 مرتفعة ⚠️",
            "🔴 CRITICAL": "🔴 حرجة 🚨",
        }

        risk_level = status.get("risk_level", "🟢 LOW")
        risk_display = risk_emoji.get(risk_level, risk_level)

        panic = "🚨 مفعل" if status.get("panic_mode") else "✅ غير مفعل"
        paused = "⏸️ متوقف" if status.get("trading_paused") else "▶️ يعمل"

        return (
            "🔒 **إدارة المخاطر**\n\n"
            f"📊 **مستوى المخاطرة:** {risk_display}\n"
            f"💰 **أرباح اليوم:** {format_currency(status.get('daily_pnl', 0))}\n"
            f"📉 **نسبة الخسارة اليومية:** {status.get('daily_pnl_pct', 0):+.2f}%\n"
            f"📊 **صفقات مفتوحة:** {status.get('open_trades', 0)}/{status.get('max_open_trades', 3)}\n"
            f"💵 **الرصيد:** {format_currency(status.get('balance', 0))}\n"
            f"🚨 **وضع الطوارئ:** {panic}\n"
            f"⏯️ **حالة التداول:** {paused}\n\n"
            f"⚠️ الحد الأقصى للخسارة اليومية: {status.get('max_daily_loss', 5)}%"
        )

    # ─── Analysis Result ──────────────────────────

    @staticmethod
    def analysis_result(result: Dict[str, Any]) -> str:
        """نتيجة تحليل السوق"""
        if result.get("error"):
            return f"❌ {result.get('message', 'خطأ في التحليل')}"

        direction = result.get("direction", "hold")
        direction_display = {
            "buy": "🟢 شراء (BUY)",
            "sell": "🔴 بيع (SELL)",
            "hold": "⏸️ انتظار (HOLD)",
        }.get(direction, direction)

        confidence = result.get("confidence", 0)
        reasoning = result.get("reasoning", "لا يوجد تحليل")

        indicators = result.get("indicators", {})

        return (
            "🔍 **تحليل السوق - AI DeepSeek**\n\n"
            f"🏆 **الأصل:** {result.get('symbol', 'N/A')}\n"
            f"⏱️ **الإطار:** {result.get('timeframe', 'N/A')}\n"
            f"💵 **السعر الحالي:** {indicators.get('current_price', 'N/A')}\n\n"
            f"📊 **التوصية:** {direction_display}\n"
            f"🎯 **نسبة الثقة:** {confidence:.1f}%\n"
            f"📝 **التحليل:** {reasoning}\n\n"
            f"📈 **RSI:** {indicators.get('rsi', 'N/A')}\n"
            f"📉 **الاتجاه:** {indicators.get('trend', 'N/A')}\n"
            f"📊 **ADX:** {indicators.get('adx', 'N/A')}\n\n"
            f"🕐 {result.get('timestamp', '')}"
        )

    # ─── General ──────────────────────────────────

    @staticmethod
    def error(message: str = "حدث خطأ غير متوقع") -> str:
        """رسالة خطأ عامة"""
        return f"❌ {message}"

    @staticmethod
    def success(message: str = "تمت العملية بنجاح") -> str:
        """رسالة نجاح"""
        return f"✅ {message}"

    @staticmethod
    def info(message: str) -> str:
        """رسالة معلومات"""
        return f"ℹ️ {message}"

    @staticmethod
    def loading() -> str:
        """رسالة انتظار"""
        return "⏳ جاري المعالجة... يرجى الانتظار"

    @staticmethod
    def help_message() -> str:
        """رسالة المساعدة"""
        return (
            "📖 **دليل استخدام بوت التداول الذكي**\n\n"
            "**الأوامر الأساسية:**\n"
            "/start - عرض لوحة التحكم الرئيسية\n"
            "/help - هذه الرسالة\n"
            "/status - حالة البوت والصفقات\n"
            "/analyze - تحليل السوق الحالي\n"
            "/report - تقرير الأداء\n"
            "/settings - الإعدادات السريعة\n"
            "/panic - إغلاق كل الصفقات\n\n"
            "**للاستفسارات:** تواصل مع المطور"
        )
