"""
Backtest Report Formatter
==========================
Converts BacktestResult into human-readable Telegram messages.
"""
from typing import Dict, Any
from datetime import datetime

from utils.helpers import format_currency, format_percentage


class BacktestReport:
    """Formatter for backtest results"""

    @staticmethod
    def summary(result: Any) -> str:
        """Main backtest summary message"""
        if not result.success:
            return f"❌ **Backtest Failed**\n\n{result.message}"

        # Win/loss color
        pnl_emoji = "🟢" if result.total_return_pct >= 0 else "🔴"

        # Strategy label
        strategy_label = "📊 Indicator Strategy" if result.strategy == "indicators" else "🧠 AI Strategy"

        start_str = result.start_date.strftime("%Y-%m-%d") if result.start_date else "N/A"
        end_str = result.end_date.strftime("%Y-%m-%d") if result.end_date else "N/A"

        text = (
            "══════════════════════\n"
            "🧪 **Backtest Report**\n"
            "══════════════════════\n\n"
            f"🏆 **Asset:** {result.symbol}\n"
            f"⏱️ **Timeframe:** {result.timeframe}\n"
            f"📅 **Period:** {start_str} → {end_str}\n"
            f"🧮 **Strategy:** {strategy_label}\n\n"
            "─── Performance ───\n"
            f"{pnl_emoji} **Total Return:** {format_percentage(result.total_return_pct)}\n"
            f"💰 **Final Balance:** {format_currency(result.final_balance)}\n"
            f"📊 **Total Trades:** {result.total_trades}\n"
            f"✅ **Winners:** {result.winning_trades}\n"
            f"❌ **Losers:** {result.losing_trades}\n"
            f"🎯 **Win Rate:** {result.win_rate:.1f}%\n\n"
            "─── Risk Metrics ───\n"
            f"📉 **Max Drawdown:** {format_percentage(result.max_drawdown_pct)}\n"
            f"⚖️ **Profit Factor:** {result.profit_factor:.2f}\n"
            f"📈 **Sharpe Ratio:** {result.sharpe_ratio:.2f}\n"
            f"📉 **Sortino Ratio:** {result.sortino_ratio:.2f}\n\n"
            "─── Trade Stats ───\n"
            f"💵 **Avg Trade:** {format_currency(result.avg_trade_return)}\n"
            f"🟢 **Avg Win:** {format_currency(result.avg_win)}\n"
            f"🔴 **Avg Loss:** {format_currency(result.avg_loss)}\n"
            f"🏆 **Largest Win:** {format_currency(result.largest_win)}\n"
            f"💔 **Largest Loss:** {format_currency(result.largest_loss)}\n\n"
            f"🕐 Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC"
        )
        return text[:3900] + "\n..." if len(text) > 3900 else text

    @staticmethod
    def trade_list(result: Any, max_trades: int = 10) -> str:
        """List of individual trades"""
        if not result.trades:
            return "📋 No trades executed during backtest."

        lines = [f"📋 **Last {max_trades} Trades:**\n"]
        for t in result.trades[-max_trades:]:
            pnl_emoji = "🟢" if t.pnl > 0 else "🔴" if t.pnl < 0 else "⚪"
            direction = "BUY" if t.direction == "buy" else "SELL"
            exit_map = {"tp": "TP", "sl": "SL", "close": "Close"}
            exit_label = exit_map.get(t.exit_reason, t.exit_reason)
            lines.append(
                f"{pnl_emoji} #{t.id} | {direction} | "
                f"{t.open_price}→{t.close_price} | "
                f"${t.pnl:+.2f} | {exit_label}"
            )

        return "\n".join(lines)

    @staticmethod
    def no_backtests() -> str:
        """Message when no backtests exist"""
        return (
            "🧪 **Backtest History**\n\n"
            "No backtests found.\n\n"
            "Run your first backtest from 🤖 AI Settings → 🧪 Backtest."
        )

    @staticmethod
    def history_list(backtests: list) -> str:
        """Formatted list of past backtests"""
        if not backtests:
            return BacktestReport.no_backtests()

        lines = ["🧪 **Backtest History**\n"]
        for b in backtests[:10]:
            pnl_emoji = "🟢" if b.total_return_pct >= 0 else "🔴"
            strategy = b.strategy.replace("_", " ").title()
            date_str = b.created_at.strftime("%Y-%m-%d %H:%M") if b.created_at else ""
            lines.append(
                f"{pnl_emoji} #{b.id} | {b.symbol}/{b.timeframe} | "
                f"{strategy} | {format_percentage(b.total_return_pct)} | "
                f"{b.total_trades} trades | {date_str}"
            )

        return "\n".join(lines)
