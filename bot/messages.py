"""
Messages - Message Templates
==============================
All text templates used in the bot
"""
from typing import Dict, Any, List
from datetime import datetime

from config import config
from utils.helpers import format_currency, format_percentage


class Messages:
    """Message templates"""

    # ─── Welcome / Start ──────────────────────────

    @staticmethod
    def welcome(first_name: str = "Trader") -> str:
        """Welcome message"""
        return (
            f"👋 Welcome, {first_name}, to\n"
            f"🤖 AI Cyber-Trader | Intelligent Trading System\n\n"
            f"🚀 I'm a fully automated trading bot powered by "
            f"multiple AI providers for market analysis and trade execution "
            f"on MetaTrader 5.\n\n"
            f"📌 Use the buttons below to control the bot."
        )

    @staticmethod
    def start_guide() -> str:
        """Quick start guide"""
        return (
            "📖 **Quick Start Guide:**\n\n"
            "1️⃣ Go to ⚙️ Trade Setup to choose asset and lot size\n"
            "2️⃣ Go to 🤖 AI Settings → 🔑 AI Provider to set your API key\n"
            "3️⃣ Press 🚀 Start Auto Trading to begin analysis & execution\n"
            "4️⃣ Monitor trades from 📈 Performance Reports\n\n"
            "⚠️ You can use OpenAI, Gemini, Claude, or DeepSeek with your own key"
        )

    # ─── Dashboard ────────────────────────────────

    @staticmethod
    def dashboard(bot_status: str = "🟢 ONLINE",
                  account: str = "MT5 - Demo",
                  balance: float = 42500.0,
                  daily_pnl: float = 0.0,
                  symbol: str = "XAUUSD",
                  auto_running: bool = False,
                  open_trades: int = 0) -> str:
        """Main dashboard"""

        # Asset name
        symbol_name = config.symbols.get(symbol, symbol)

        # Auto trading status
        auto_status = "🟢 Active" if auto_running else "🔴 Stopped"

        # Format profit/loss
        pnl_formatted = format_currency(daily_pnl)
        pnl_pct = (daily_pnl / balance * 100) if balance > 0 else 0
        pnl_pct_formatted = format_percentage(pnl_pct)

        return (
            "══════════════════════\n"
            "🤖 **AI Cyber-Trader | Intelligent Trading**\n"
            "══════════════════════\n\n"
            f"🔹 **Bot Status:** {bot_status}\n"
            f"🔹 **Auto Trading:** {auto_status}\n"
            f"🔹 **Account:** {account}\n"
            f"🔹 **Balance:** {format_currency(balance)}\n"
            f"🔹 **Today's P&L:** {pnl_formatted} ({pnl_pct_formatted})\n"
            f"🔹 **Selected Asset:** {symbol_name} ({symbol})\n"
            f"🔹 **Open Positions:** {open_trades}\n\n"
            "📊 Use the buttons below to control the bot"
        )

    # ─── Trading Settings ─────────────────────────

    @staticmethod
    def trading_settings(symbol: str = "XAUUSD",
                         lot: float = 0.01,
                         direction: str = "both") -> str:
        """Current trading settings"""
        symbol_name = config.symbols.get(symbol, symbol)

        direction_names = {
            "buy": "🟢 Buy Only",
            "sell": "🔴 Sell Only",
            "both": "🔄 Both Directions",
        }

        return (
            "⚙️ **Current Trade Settings**\n\n"
            f"🏆 **Asset:** {symbol_name} ({symbol})\n"
            f"📦 **Lot Size:** {lot}\n"
            f"📊 **Trade Mode:** {direction_names.get(direction, direction)}\n\n"
            "Choose what to change:"
        )

    @staticmethod
    def enter_custom_lot() -> str:
        """Custom lot input prompt"""
        return (
            "✏️ **Enter desired lot size:**\n\n"
            "Example: `0.25` or `0.05`\n"
            f"Allowed range: {config.trading.min_lot} - {config.trading.max_lot}"
        )

    # ─── AI Settings ──────────────────────────────

    @staticmethod
    def ai_settings(confidence: float = 70.0,
                    mode: str = "predictive",
                    news_enabled: bool = True,
                    timeframe: str = "M15",
                    backtest: bool = False,
                    provider: str = "deepseek",
                    news_guard_enabled: bool = True) -> str:
        """AI configuration settings"""
        mode_names = {
            "predictive": "🧠 Predictive Analysis",
            "news_scanning": "📰 News Scanning",
            "hybrid": "🔀 Hybrid (Analysis + News)",
        }

        provider_names = {
            "deepseek": "🤖 DeepSeek AI",
            "openai": "🧠 OpenAI GPT",
            "gemini": "💎 Google Gemini",
            "claude": "🔮 Anthropic Claude",
        }

        provider_display = provider_names.get(provider, provider.title())

        return (
            "🤖 **AI Configuration**\n\n"
            f"🔑 **AI Provider:** {provider_display}\n"
            f"📊 **Analysis Mode:** {mode_names.get(mode, mode)}\n"
            f"🎯 **Confidence Threshold:** {confidence:.0f}%\n"
            f"⏱️ **Timeframe:** {timeframe}\n"
            f"📰 **News Check:** {'✅ Enabled' if news_enabled else '❌ Disabled'}\n"
            f"🛡️ **NewsGuard Auto-Close:** {'✅ Enabled' if news_guard_enabled else '❌ Disabled'}\n"
            f"🧪 **Backtest Mode:** {'✅ Enabled' if backtest else '❌ Disabled'}\n\n"
            "Choose what to change:"
        )

    # ─── AI Provider Management ───────────────────

    @staticmethod
    def provider_select() -> str:
        """AI provider selection screen"""
        return (
            "🔑 **AI Provider & API Key Management**\n\n"
            "Choose your AI provider. You can set your own API key "
            "for any provider — your key is **AES-256 encrypted** "
            "in the database and only decrypted in memory during analysis.\n\n"
            "**Available providers:**\n"
            "🧠 **OpenAI GPT** — GPT-4o, GPT-4-turbo\n"
            "💎 **Google Gemini** — Gemini 1.5 Pro\n"
            "🔮 **Anthropic Claude** — Claude 3.5 Sonnet\n"
            "🤖 **DeepSeek AI** — deepseek-chat\n\n"
            "Select a provider to configure:"
        )

    @staticmethod
    def api_key_prompt(provider: str) -> str:
        """Prompt for API key entry"""
        provider_names = {
            "deepseek": "🤖 DeepSeek AI",
            "openai": "🧠 OpenAI GPT",
            "gemini": "💎 Google Gemini",
            "claude": "🔮 Anthropic Claude",
        }
        name = provider_names.get(provider, provider.title())

        key_urls = {
            "deepseek": "https://platform.deepseek.com/api_keys",
            "openai": "https://platform.openai.com/api-keys",
            "gemini": "https://aistudio.google.com/app/apikey",
            "claude": "https://console.anthropic.com/settings/keys",
        }
        url = key_urls.get(provider, "")

        return (
            f"🔑 **Set API Key for {name}**\n\n"
            f"Please send your API key as a message.\n"
            f"Get your key from: {url}\n\n"
            f"⚠️ **Security:** Your key will be AES-256 encrypted "
            f"before storage and only held in memory during analysis.\n\n"
            f"Type /cancel to abort."
        )

    @staticmethod
    def api_key_set(provider: str, model: str = "") -> str:
        """Confirmation that API key was set"""
        provider_names = {
            "deepseek": "🤖 DeepSeek AI",
            "openai": "🧠 OpenAI GPT",
            "gemini": "💎 Google Gemini",
            "claude": "🔮 Anthropic Claude",
        }
        name = provider_names.get(provider, provider.title())
        msg = f"✅ **API Key Saved!**\n\nProvider: **{name}**\n🔒 Key: AES-256 encrypted"
        if model:
            msg += f"\n📦 Model: {model}"
        return msg

    @staticmethod
    def api_key_removed(provider: str) -> str:
        """Confirmation that API key was removed"""
        provider_names = {
            "deepseek": "🤖 DeepSeek AI",
            "openai": "🧠 OpenAI GPT",
            "gemini": "💎 Google Gemini",
            "claude": "🔮 Anthropic Claude",
        }
        name = provider_names.get(provider, provider.title())
        return f"🗑️ API key for **{name}** has been removed."

    @staticmethod
    def api_key_validating(provider: str) -> str:
        """Validating API key message"""
        provider_names = {
            "deepseek": "🤖 DeepSeek AI",
            "openai": "🧠 OpenAI GPT",
            "gemini": "💎 Google Gemini",
            "claude": "🔮 Anthropic Claude",
        }
        name = provider_names.get(provider, provider.title())
        return f"⏳ Validating API key for **{name}**..."

    @staticmethod
    def api_key_valid(provider: str) -> str:
        """API key validation success"""
        provider_names = {
            "deepseek": "🤖 DeepSeek AI",
            "openai": "🧠 OpenAI GPT",
            "gemini": "💎 Google Gemini",
            "claude": "🔮 Anthropic Claude",
        }
        name = provider_names.get(provider, provider.title())
        return f"✅ **Key Valid!**\n\n**{name}** API key is working correctly.\nYou're ready to trade!"

    @staticmethod
    def api_key_invalid(provider: str, error: str = "") -> str:
        """API key validation failure"""
        provider_names = {
            "deepseek": "🤖 DeepSeek AI",
            "openai": "🧠 OpenAI GPT",
            "gemini": "💎 Google Gemini",
            "claude": "🔮 Anthropic Claude",
        }
        name = provider_names.get(provider, provider.title())
        msg = f"❌ **Key Invalid!**\n\n**{name}** API key validation failed."
        if error:
            msg += f"\n⚠️ Error: {error}"
        msg += "\n\nPlease check your key and try again."
        return msg

    @staticmethod
    def provider_model_select(provider: str) -> str:
        """Model selection for a provider"""
        provider_names = {
            "deepseek": "🤖 DeepSeek AI",
            "openai": "🧠 OpenAI GPT",
            "gemini": "💎 Google Gemini",
            "claude": "🔮 Anthropic Claude",
        }
        name = provider_names.get(provider, provider.title())
        return f"📦 **Select Model for {name}**\n\nChoose a model to use for market analysis:"

    @staticmethod
    def provider_status(keys_status: list) -> str:
        """Show which API keys are configured"""
        lines = ["🔑 **API Keys Status**\n"]
        icon_map = {
            "deepseek": "🤖",
            "openai": "🧠",
            "gemini": "💎",
            "claude": "🔮",
        }
        for ks in keys_status:
            provider = ks.get("provider", "unknown")
            icon = icon_map.get(provider, "🔑")
            if ks.get("has_key"):
                lines.append(f"{icon} **{ks.get('name', provider)}:** ✅ Key set | Model: {ks.get('model', 'default')}")
            else:
                lines.append(f"{icon} **{ks.get('name', provider)}:** ❌ No key")
        lines.append("\nTap a provider above to manage its key.")
        return "\n".join(lines)

    # ─── Trade Notification ───────────────────────

    @staticmethod
    def trade_opened(trade: Dict[str, Any]) -> str:
        """Trade opened notification"""
        direction_emoji = "🟢" if trade.get("direction") == "buy" else "🔴"
        direction_name = "BUY" if trade.get("direction") == "buy" else "SELL"

        return (
            "🔔 **Alert: New AI Trade Executed!**\n\n"
            f"📥 **Type:** {direction_emoji} {direction_name}\n"
            f"🏆 **Asset:** {trade.get('symbol', 'N/A')}\n"
            f"🎯 **Entry Price:** {trade.get('open_price', 0)}\n"
            f"🛡️ **Stop Loss (SL):** {trade.get('stop_loss', 0)}\n"
            f"💰 **Take Profit (TP):** {trade.get('take_profit', 0)}\n"
            f"📦 **Volume:** {trade.get('volume', 0)} lots\n"
            f"🧠 **AI Confidence:** {trade.get('confidence', 0):.1f}%\n"
            f"🕐 **Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

    @staticmethod
    def trade_closed(trade: Dict[str, Any]) -> str:
        """Trade closed notification"""
        pnl = trade.get("pnl", 0)
        pnl_emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "⚪"

        return (
            "📢 **Alert: Trade Closed**\n\n"
            f"🏆 **Asset:** {trade.get('symbol', 'N/A')}\n"
            f"📥 **Type:** {trade.get('direction', 'N/A')}\n"
            f"🎯 **Close Price:** {trade.get('close_price', 0)}\n"
            f"💰 **Profit/Loss:** {pnl_emoji} ${pnl:,.2f}\n"
            f"🕐 **Time:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )

    # ─── Reports ──────────────────────────────────

    @staticmethod
    def performance_report(daily: Dict[str, Any],
                           all_time: Dict[str, Any],
                           balance: float = 42500.0) -> str:
        """Performance report"""
        pnl_pct = (daily["total_pnl"] / balance * 100) if balance > 0 else 0

        return (
            "══════════════════════\n"
            "📊 **Performance & Earnings Report**\n"
            "══════════════════════\n\n"
            "📅 **Today's Performance:**\n"
            f"   💰 P&L: {format_currency(daily['total_pnl'])} "
            f"({format_percentage(pnl_pct)})\n"
            f"   📊 Trades: {daily['total_trades']}\n"
            f"   ✅ Winners: {daily['winning_trades']}\n"
            f"   ❌ Losers: {daily['losing_trades']}\n"
            f"   🎯 Win Rate: {daily['win_rate']:.1f}%\n\n"
            "📈 **All-Time Performance:**\n"
            f"   💰 Total P&L: {format_currency(all_time['total_pnl'])}\n"
            f"   📊 Total Trades: {all_time['total_trades']}\n"
            f"   🎯 Win Rate: {all_time['win_rate']:.1f}%\n"
        )

    @staticmethod
    def recent_trades(trades: list) -> str:
        """Recent trades list"""
        if not trades:
            return "📋 No recent trades."

        lines = ["📋 **Last 10 Trades:**\n"]
        for t in trades[:10]:
            pnl = t.pnl or 0
            pnl_emoji = "🟢" if pnl > 0 else "🔴"
            direction = "BUY" if t.direction == "buy" else "SELL"
            lines.append(
                f"{pnl_emoji} {t.symbol} | {direction} | "
                f"${pnl:+.2f} | {t.opened_at.strftime('%H:%M')}"
            )

        text = "\n".join(lines)
        # Telegram message limit safety
        return text[:3800] + "\n..." if len(text) > 3800 else text

    # ─── Risk Status ──────────────────────────────

    @staticmethod
    def risk_status(status: Dict[str, Any]) -> str:
        """Risk management status"""
        risk_emoji = {
            "🟢 LOW": "🟢 Low ✓",
            "🟡 MEDIUM": "🟡 Medium ⚠",
            "🟠 HIGH": "🟠 High ⚠️",
            "🔴 CRITICAL": "🔴 Critical 🚨",
        }

        risk_level = status.get("risk_level", "🟢 LOW")
        risk_display = risk_emoji.get(risk_level, risk_level)

        panic = "🚨 ACTIVE" if status.get("panic_mode") else "✅ Inactive"
        paused = "⏸️ Paused" if status.get("trading_paused") else "▶️ Running"

        return (
            "🔒 **Risk Management**\n\n"
            f"📊 **Risk Level:** {risk_display}\n"
            f"💰 **Today's P&L:** {format_currency(status.get('daily_pnl', 0))}\n"
            f"📉 **Daily Loss %:** {status.get('daily_pnl_pct', 0):+.2f}%\n"
            f"📊 **Open Positions:** {status.get('open_trades', 0)}/{status.get('max_open_trades', 3)}\n"
            f"💵 **Balance:** {format_currency(status.get('balance', 0))}\n"
            f"🚨 **Panic Mode:** {panic}\n"
            f"⏯️ **Trading Status:** {paused}\n\n"
            f"⚠️ Max Daily Loss Limit: {status.get('max_daily_loss', 5)}%"
        )

    # ─── Analysis Result ──────────────────────────

    @staticmethod
    def top5_result(results: List[Dict[str, Any]]) -> str:
        """Top 5 Forex opportunities message"""
        if not results:
            return "❌ No trading opportunities found at the moment."

        lines = [
            "🏆 **Top 5 Forex Opportunities**\n",
            "══════════════════════",
            "",
        ]

        for i, r in enumerate(results, 1):
            direction_emoji = {"buy": "🟢", "sell": "🔴", "hold": "⚪"}.get(r["direction"], "⚪")
            direction_text = {"buy": "BUY", "sell": "SELL", "hold": "HOLD"}.get(r["direction"], r["direction"].upper())

            change_emoji = "📈" if r.get("change_24h", 0) > 0 else "📉" if r.get("change_24h", 0) < 0 else "➡️"

            lines.append(
                f"{i}. **{r['name']}** ({r['symbol']})\n"
                f"   {direction_emoji} **{direction_text}** | 🎯 Confidence: {r['confidence']:.1f}%\n"
                f"   💵 Price: {r['current_price']} | {change_emoji} 24h: {r.get('change_24h', 0):+.2f}%\n"
                f"   📊 RSI: {r.get('rsi', 'N/A')} | ADX: {r.get('adx', 'N/A')} | Trend: {r['trend'].title()}"
            )
            if r["direction"] != "hold":
                lines.append(
                    f"   🎯 Entry: {r['entry_price']} | 🛡️ SL: {r['stop_loss']} | 💰 TP: {r['take_profit']}"
                )
            lines.append("")

        lines.extend([
            "══════════════════════",
            "",
            "⚠️ These are indicator-based signals. Always confirm with your own analysis.",
        ])

        text = "\n".join(lines)
        return text[:3900] + "\n..." if len(text) > 3900 else text

    @staticmethod
    def analysis_result(result: Dict[str, Any]) -> str:
        """Market analysis result"""
        if result.get("error"):
            return f"❌ {result.get('message', 'Analysis error')}"

        direction = result.get("direction", "hold")
        direction_display = {
            "buy": "🟢 BUY",
            "sell": "🔴 SELL",
            "hold": "⏸️ HOLD",
        }.get(direction, direction)

        confidence = result.get("confidence", 0)
        reasoning = result.get("reasoning", "No analysis available")
        # Truncate long reasoning to stay within Telegram limits
        if len(reasoning) > 800:
            reasoning = reasoning[:797] + "..."

        indicators = result.get("indicators", {})

        text = (
            "🔍 **Market Analysis - AI**\n\n"
            f"🏆 **Asset:** {result.get('symbol', 'N/A')}\n"
            f"⏱️ **Timeframe:** {result.get('timeframe', 'N/A')}\n"
            f"💵 **Current Price:** {indicators.get('current_price', 'N/A')}\n\n"
            f"📊 **Recommendation:** {direction_display}\n"
            f"🎯 **Confidence:** {confidence:.1f}%\n"
            f"📝 **Analysis:** {reasoning}\n\n"
            f"📈 **RSI:** {indicators.get('rsi', 'N/A')}\n"
            f"📉 **Trend:** {indicators.get('trend', 'N/A')}\n"
            f"📊 **ADX:** {indicators.get('adx', 'N/A')}\n\n"
            f"🕐 {result.get('timestamp', '')}"
        )
        return text[:3900] + "\n..." if len(text) > 3900 else text

    # ─── General ──────────────────────────────────

    @staticmethod
    def error(message: str = "An unexpected error occurred") -> str:
        """Generic error message"""
        return f"❌ {message}"

    @staticmethod
    def success(message: str = "Operation completed successfully") -> str:
        """Success message"""
        return f"✅ {message}"

    @staticmethod
    def info(message: str) -> str:
        """Info message"""
        return f"ℹ️ {message}"

    @staticmethod
    def loading() -> str:
        """Loading message"""
        return "⏳ Processing... please wait"

    # ─── Backtest ─────────────────────────────────

    @staticmethod
    def backtest_config(symbol: str = "XAUUSD", timeframe: str = "D1",
                        strategy: str = "indicators") -> str:
        """Backtest configuration screen"""
        strategy_names = {
            "indicators": "📊 Indicator Strategy (Fast / Free)",
            "ai": "🧠 AI Strategy (Slow / Costs API Credits)",
        }
        return (
            "🧪 **Backtest Configuration**\n\n"
            "Test your trading strategy on historical data before risking real money.\n\n"
            f"🏆 **Asset:** {symbol}\n"
            f"⏱️ **Timeframe:** {timeframe}\n"
            f"🧮 **Strategy:** {strategy_names.get(strategy, strategy)}\n\n"
            "Tap the buttons below to adjust settings, then press **▶️ Run Backtest**"
        )

    @staticmethod
    def backtest_running(symbol: str, timeframe: str, strategy: str) -> str:
        """Message shown while backtest is running"""
        return (
            f"⏳ **Running Backtest...**\n\n"
            f"🏆 Asset: {symbol}\n"
            f"⏱️ Timeframe: {timeframe}\n"
            f"🧮 Strategy: {strategy.title()}\n\n"
            "Analyzing historical bars and simulating trades. Please wait..."
        )

    @staticmethod
    def help_message() -> str:
        """Help message"""
        return (
            "📖 **AI Cyber-Trader Bot User Guide**\n\n"
            "**Basic Commands:**\n"
            "/start - Display main dashboard\n"
            "/help - This message\n"
            "/status - Bot & position status\n"
            "/analyze - Analyze current market\n"
            "/report - Performance report\n"
            "/settings - Quick settings\n"
            "/panic - Close all positions\n\n"
            "**For inquiries:** Contact the developer"
        )
