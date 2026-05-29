"""
Inline Keyboards - لوحات المفاتيح التفاعلية
============================================
جميع الأزرار المضمنة (Inline Keyboards) للبوت
"""
from typing import List, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import config


class Keyboards:
    """منشئ لوحات المفاتيح التفاعلية"""

    # ─── Main Dashboard ───────────────────────────

    @staticmethod
    def main_dashboard() -> InlineKeyboardMarkup:
        """القائمة الرئيسية"""
        buttons = [
            [
                InlineKeyboardButton("🚀 تشغيل التداول الآلي", callback_data="auto_start"),
                InlineKeyboardButton("🛑 إيقاف مؤقت", callback_data="auto_stop"),
            ],
            [
                InlineKeyboardButton("🤖 إعدادات الذكاء الاصطناعي", callback_data="menu_ai"),
                InlineKeyboardButton("⚙️ إعدادات الصفقات", callback_data="menu_trade"),
            ],
            [
                InlineKeyboardButton("📈 تقارير الأداء", callback_data="menu_reports"),
                InlineKeyboardButton("🔒 إدارة المخاطر", callback_data="menu_risk"),
            ],
            [
                InlineKeyboardButton("📊 تحليل السوق الآن", callback_data="analyze_now"),
                InlineKeyboardButton("🔄 تحديث", callback_data="refresh"),
            ],
            [
                InlineKeyboardButton("🚨 إغلاق كل الصفقات فوراً", callback_data="panic"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def trading_controls(auto_running: bool = False) -> InlineKeyboardMarkup:
        """أزرار التحكم بالتداول"""
        buttons = [
            [
                InlineKeyboardButton(
                    "🚀 تشغيل التداول الآلي" if not auto_running else "✅ التداول الآلي يعمل",
                    callback_data="auto_start" if not auto_running else "auto_status"
                ),
            ],
            [
                InlineKeyboardButton("🛑 إيقاف مؤقت", callback_data="auto_stop"),
            ],
            [
                InlineKeyboardButton("🔙 العودة للرئيسية", callback_data="main_menu"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    # ─── Trading Setup ────────────────────────────

    @staticmethod
    def trading_setup() -> InlineKeyboardMarkup:
        """قائمة إعدادات التداول"""
        buttons = [
            [
                InlineKeyboardButton("🏆 XAUUSD", callback_data="symbol_XAUUSD"),
                InlineKeyboardButton("💶 EURUSD", callback_data="symbol_EURUSD"),
            ],
            [
                InlineKeyboardButton("💷 GBPUSD", callback_data="symbol_GBPUSD"),
                InlineKeyboardButton("💴 USDJPY", callback_data="symbol_USDJPY"),
            ],
            [
                InlineKeyboardButton("₿ BTCUSD", callback_data="symbol_BTCUSD"),
            ],
            [
                InlineKeyboardButton("📊 مؤشرات", callback_data="symbols_indices"),
            ],
            [
                InlineKeyboardButton("⬅️ العودة", callback_data="main_menu"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def indices_symbols() -> InlineKeyboardMarkup:
        """أزواج المؤشرات"""
        buttons = [
            [
                InlineKeyboardButton("📊 US30", callback_data="symbol_US30"),
                InlineKeyboardButton("📈 NAS100", callback_data="symbol_NAS100"),
            ],
            [
                InlineKeyboardButton("⬅️ العودة للإعدادات", callback_data="menu_trade"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def lot_sizes() -> InlineKeyboardMarkup:
        """اختيار حجم اللوت"""
        buttons = []
        row = []
        for lot in config.lot_presets:
            row.append(InlineKeyboardButton(
                f"📦 {lot}", callback_data=f"lot_{lot}"
            ))
            if len(row) == 3:
                buttons.append(row)
                row = []

        if row:
            buttons.append(row)

        buttons.append([
            InlineKeyboardButton("✏️ كتابة لوت مخصص", callback_data="lot_custom"),
        ])
        buttons.append([
            InlineKeyboardButton("⬅️ العودة للإعدادات", callback_data="menu_trade"),
        ])

        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def trade_direction() -> InlineKeyboardMarkup:
        """اختيار اتجاه التداول"""
        buttons = [
            [
                InlineKeyboardButton("🟢 الشراء فقط", callback_data="dir_buy"),
                InlineKeyboardButton("🔴 البيع فقط", callback_data="dir_sell"),
            ],
            [
                InlineKeyboardButton("🔄 الاتجاهين معاً", callback_data="dir_both"),
            ],
            [
                InlineKeyboardButton("⬅️ العودة للإعدادات", callback_data="menu_trade"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    # ─── AI Configuration ─────────────────────────

    @staticmethod
    def ai_config() -> InlineKeyboardMarkup:
        """إعدادات الذكاء الاصطناعي"""
        buttons = [
            [
                InlineKeyboardButton("🧠 نموذج التحليل", callback_data="ai_model"),
                InlineKeyboardButton("🎯 نسبة الثقة", callback_data="ai_confidence"),
            ],
            [
                InlineKeyboardButton("📰 فحص الأخبار", callback_data="ai_news"),
                InlineKeyboardButton("⏱️ الإطار الزمني", callback_data="ai_timeframe"),
            ],
            [
                InlineKeyboardButton("🧪 وضع المحاكاة", callback_data="ai_backtest"),
            ],
            [
                InlineKeyboardButton("📊 تدريب ML", callback_data="ai_train"),
            ],
            [
                InlineKeyboardButton("⬅️ العودة للرئيسية", callback_data="main_menu"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def confidence_levels() -> InlineKeyboardMarkup:
        """مستويات نسبة الثقة"""
        buttons = []
        row = []
        for level in config.confidence_presets:
            row.append(InlineKeyboardButton(
                f"🎯 {level}%", callback_data=f"conf_{level}"
            ))
            if len(row) == 2:
                buttons.append(row)
                row = []

        if row:
            buttons.append(row)

        buttons.append([
            InlineKeyboardButton("⬅️ العودة", callback_data="menu_ai"),
        ])
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def analysis_modes() -> InlineKeyboardMarkup:
        """أنماط التحليل"""
        buttons = [
            [
                InlineKeyboardButton("🧠 التحليل التنبئي الذكي", callback_data="mode_predictive"),
            ],
            [
                InlineKeyboardButton("📰 فحص الأخبار الفوري", callback_data="mode_news_scanning"),
            ],
            [
                InlineKeyboardButton("🔀 هجين (الاثنين معاً)", callback_data="mode_hybrid"),
            ],
            [
                InlineKeyboardButton("⬅️ العودة", callback_data="menu_ai"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def timeframes() -> InlineKeyboardMarkup:
        """الإطارات الزمنية"""
        buttons = [
            [
                InlineKeyboardButton("M5", callback_data="tf_M5"),
                InlineKeyboardButton("M15", callback_data="tf_M15"),
                InlineKeyboardButton("M30", callback_data="tf_M30"),
            ],
            [
                InlineKeyboardButton("H1", callback_data="tf_H1"),
                InlineKeyboardButton("H4", callback_data="tf_H4"),
                InlineKeyboardButton("D1", callback_data="tf_D1"),
            ],
            [
                InlineKeyboardButton("⬅️ العودة", callback_data="menu_ai"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    # ─── Reports ──────────────────────────────────

    @staticmethod
    def reports_menu() -> InlineKeyboardMarkup:
        """قائمة التقارير"""
        buttons = [
            [
                InlineKeyboardButton("📊 أداء اليوم", callback_data="report_today"),
                InlineKeyboardButton("📈 الأداء الكلي", callback_data="report_all"),
            ],
            [
                InlineKeyboardButton("📋 آخر الصفقات", callback_data="report_recent"),
            ],
            [
                InlineKeyboardButton("🧪 تقرير المحاكاة", callback_data="report_backtest"),
            ],
            [
                InlineKeyboardButton("⬅️ العودة للرئيسية", callback_data="main_menu"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    # ─── Risk Management ──────────────────────────

    @staticmethod
    def risk_menu() -> InlineKeyboardMarkup:
        """قائمة إدارة المخاطر"""
        buttons = [
            [
                InlineKeyboardButton("📊 حالة المخاطر", callback_data="risk_status"),
            ],
            [
                InlineKeyboardButton("⚠️ حد الخسارة اليومية", callback_data="risk_daily_loss"),
                InlineKeyboardButton("📦 الحد الأعلى للصفقات", callback_data="risk_max_trades"),
            ],
            [
                InlineKeyboardButton("🚨 إغلاق كل الصفقات فوراً", callback_data="panic"),
            ],
            [
                InlineKeyboardButton("⬅️ العودة للرئيسية", callback_data="main_menu"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    # ─── Utility ──────────────────────────────────

    @staticmethod
    def back_button(target: str = "main_menu", label: str = "⬅️ العودة") -> InlineKeyboardMarkup:
        """زر العودة فقط"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(label, callback_data=target)]
        ])

    @staticmethod
    def confirm_panic() -> InlineKeyboardMarkup:
        """تأكيد زر الطوارئ"""
        buttons = [
            [
                InlineKeyboardButton("✅ نعم، أغلق الكل", callback_data="panic_confirm"),
                InlineKeyboardButton("❌ إلغاء", callback_data="main_menu"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def confirm(message: str = "هل أنت متأكد؟",
                yes_callback: str = "confirm_yes",
                no_callback: str = "main_menu") -> InlineKeyboardMarkup:
        """تأكيد عام"""
        buttons = [
            [
                InlineKeyboardButton("✅ نعم", callback_data=yes_callback),
                InlineKeyboardButton("❌ لا", callback_data=no_callback),
            ],
        ]
        return InlineKeyboardMarkup(buttons)
