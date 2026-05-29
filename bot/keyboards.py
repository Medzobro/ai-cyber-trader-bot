"""
Inline Keyboards - Interactive Keyboards
==========================================
All inline keyboards for the bot
"""
from typing import List, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import config


class Keyboards:
    """Interactive keyboard builder"""

    # ─── Main Dashboard ───────────────────────────

    @staticmethod
    def main_dashboard() -> InlineKeyboardMarkup:
        """Main dashboard menu"""
        buttons = [
            [
                InlineKeyboardButton("🚀 Start Auto Trading", callback_data="auto_start"),
                InlineKeyboardButton("🛑 Pause", callback_data="auto_stop"),
            ],
            [
                InlineKeyboardButton("🤖 AI Settings", callback_data="menu_ai"),
                InlineKeyboardButton("⚙️ Trade Setup", callback_data="menu_trade"),
            ],
            [
                InlineKeyboardButton("📈 Performance Reports", callback_data="menu_reports"),
                InlineKeyboardButton("🔒 Risk Management", callback_data="menu_risk"),
            ],
            [
                InlineKeyboardButton("📊 Analyze Market Now", callback_data="analyze_now"),
                InlineKeyboardButton("🔄 Refresh", callback_data="refresh"),
            ],
            [
                InlineKeyboardButton("🚨 Close All Positions Now", callback_data="panic"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def trading_controls(auto_running: bool = False) -> InlineKeyboardMarkup:
        """Trading control buttons"""
        buttons = [
            [
                InlineKeyboardButton(
                    "🚀 Start Auto Trading" if not auto_running else "✅ Auto Trading Active",
                    callback_data="auto_start" if not auto_running else "auto_status"
                ),
            ],
            [
                InlineKeyboardButton("🛑 Pause", callback_data="auto_stop"),
            ],
            [
                InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    # ─── Trading Setup ────────────────────────────

    @staticmethod
    def trading_setup() -> InlineKeyboardMarkup:
        """Trading setup menu"""
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
                InlineKeyboardButton("📊 Indices", callback_data="symbols_indices"),
            ],
            [
                InlineKeyboardButton("⬅️ Back", callback_data="main_menu"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def indices_symbols() -> InlineKeyboardMarkup:
        """Index symbols"""
        buttons = [
            [
                InlineKeyboardButton("📊 US30", callback_data="symbol_US30"),
                InlineKeyboardButton("📈 NAS100", callback_data="symbol_NAS100"),
            ],
            [
                InlineKeyboardButton("⬅️ Back to Setup", callback_data="menu_trade"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def lot_sizes() -> InlineKeyboardMarkup:
        """Lot size selection"""
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
            InlineKeyboardButton("✏️ Custom Lot Size", callback_data="lot_custom"),
        ])
        buttons.append([
            InlineKeyboardButton("⬅️ Back to Setup", callback_data="menu_trade"),
        ])

        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def trade_direction() -> InlineKeyboardMarkup:
        """Trade direction selection"""
        buttons = [
            [
                InlineKeyboardButton("🟢 Buy Only", callback_data="dir_buy"),
                InlineKeyboardButton("🔴 Sell Only", callback_data="dir_sell"),
            ],
            [
                InlineKeyboardButton("🔄 Both Directions", callback_data="dir_both"),
            ],
            [
                InlineKeyboardButton("⬅️ Back to Setup", callback_data="menu_trade"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    # ─── AI Configuration ─────────────────────────

    @staticmethod
    def ai_config(news_guard_enabled: bool = True) -> InlineKeyboardMarkup:
        """AI configuration menu"""
        news_guard_label = "🛡️ NewsGuard: ON" if news_guard_enabled else "🛡️ NewsGuard: OFF"
        buttons = [
            [
                InlineKeyboardButton("🔑 AI Provider & API Key", callback_data="ai_provider"),
            ],
            [
                InlineKeyboardButton("🧠 Analysis Model", callback_data="ai_model"),
                InlineKeyboardButton("🎯 Confidence Level", callback_data="ai_confidence"),
            ],
            [
                InlineKeyboardButton("📰 News Check", callback_data="ai_news"),
                InlineKeyboardButton("⏱️ Timeframe", callback_data="ai_timeframe"),
            ],
            [
                InlineKeyboardButton(news_guard_label, callback_data="ai_newsguard"),
                InlineKeyboardButton("🧪 Backtest Mode", callback_data="ai_backtest"),
            ],
            [
                InlineKeyboardButton("📊 Train ML Model", callback_data="ai_train"),
            ],
            [
                InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="main_menu"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    # ─── AI Provider Selection ────────────────────

    @staticmethod
    def ai_providers() -> InlineKeyboardMarkup:
        """AI provider selection menu"""
        buttons = [
            [
                InlineKeyboardButton("🧠 OpenAI GPT", callback_data="provider_openai"),
                InlineKeyboardButton("💎 Google Gemini", callback_data="provider_gemini"),
            ],
            [
                InlineKeyboardButton("🔮 Anthropic Claude", callback_data="provider_claude"),
                InlineKeyboardButton("🤖 DeepSeek AI", callback_data="provider_deepseek"),
            ],
            [
                InlineKeyboardButton("🔙 View My Keys", callback_data="provider_status"),
            ],
            [
                InlineKeyboardButton("⬅️ Back", callback_data="menu_ai"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def provider_setup(provider: str, provider_name: str) -> InlineKeyboardMarkup:
        """Setup menu for a specific AI provider"""
        buttons = [
            [
                InlineKeyboardButton("🔑 Set API Key", callback_data=f"setkey_{provider}"),
            ],
            [
                InlineKeyboardButton("✅ Validate Key", callback_data=f"validate_{provider}"),
            ],
            [
                InlineKeyboardButton("🧠 Choose Model", callback_data=f"model_{provider}"),
            ],
            [
                InlineKeyboardButton("🗑️ Remove Key", callback_data=f"delkey_{provider}"),
            ],
            [
                InlineKeyboardButton("⬅️ Back to Providers", callback_data="ai_provider"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def provider_models(provider: str, models: list) -> InlineKeyboardMarkup:
        """Model selection for a provider"""
        buttons = []
        for model in models:
            buttons.append([
                InlineKeyboardButton(f"📦 {model}", callback_data=f"setmodel_{provider}_{model}"),
            ])
        buttons.append([
            InlineKeyboardButton("⬅️ Back", callback_data=f"provider_{provider}"),
        ])
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def confidence_levels() -> InlineKeyboardMarkup:
        """Confidence threshold levels"""
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
            InlineKeyboardButton("⬅️ Back", callback_data="menu_ai"),
        ])
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def analysis_modes() -> InlineKeyboardMarkup:
        """Analysis mode selection"""
        buttons = [
            [
                InlineKeyboardButton("🧠 Predictive Analysis", callback_data="mode_predictive"),
            ],
            [
                InlineKeyboardButton("📰 News Scanning", callback_data="mode_news_scanning"),
            ],
            [
                InlineKeyboardButton("🔀 Hybrid (Both)", callback_data="mode_hybrid"),
            ],
            [
                InlineKeyboardButton("⬅️ Back", callback_data="menu_ai"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def timeframes() -> InlineKeyboardMarkup:
        """Timeframe selection"""
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
                InlineKeyboardButton("⬅️ Back", callback_data="menu_ai"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    # ─── Reports ──────────────────────────────────

    @staticmethod
    def reports_menu() -> InlineKeyboardMarkup:
        """Reports menu"""
        buttons = [
            [
                InlineKeyboardButton("📊 Today's Performance", callback_data="report_today"),
                InlineKeyboardButton("📈 All-Time Performance", callback_data="report_all"),
            ],
            [
                InlineKeyboardButton("📋 Recent Trades", callback_data="report_recent"),
            ],
            [
                InlineKeyboardButton("🧪 Backtest Report", callback_data="report_backtest"),
            ],
            [
                InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="main_menu"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    # ─── Risk Management ──────────────────────────

    @staticmethod
    def risk_menu() -> InlineKeyboardMarkup:
        """Risk management menu"""
        buttons = [
            [
                InlineKeyboardButton("📊 Risk Status", callback_data="risk_status"),
            ],
            [
                InlineKeyboardButton("⚠️ Daily Loss Limit", callback_data="risk_daily_loss"),
                InlineKeyboardButton("📦 Max Open Positions", callback_data="risk_max_trades"),
            ],
            [
                InlineKeyboardButton("🚨 Close All Positions Now", callback_data="panic"),
            ],
            [
                InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="main_menu"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    # ─── Utility ──────────────────────────────────

    @staticmethod
    def back_button(target: str = "main_menu", label: str = "⬅️ Back") -> InlineKeyboardMarkup:
        """Back button only"""
        return InlineKeyboardMarkup([
            [InlineKeyboardButton(label, callback_data=target)]
        ])

    @staticmethod
    def confirm_panic() -> InlineKeyboardMarkup:
        """Panic button confirmation"""
        buttons = [
            [
                InlineKeyboardButton("✅ Yes, Close All", callback_data="panic_confirm"),
                InlineKeyboardButton("❌ Cancel", callback_data="main_menu"),
            ],
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def confirm(message: str = "Are you sure?",
                yes_callback: str = "confirm_yes",
                no_callback: str = "main_menu") -> InlineKeyboardMarkup:
        """Generic confirmation"""
        buttons = [
            [
                InlineKeyboardButton("✅ Yes", callback_data=yes_callback),
                InlineKeyboardButton("❌ No", callback_data=no_callback),
            ],
        ]
        return InlineKeyboardMarkup(buttons)
