#!/usr/bin/env python3
"""
AI Cyber-Trader Bot - Main Entry Point
=======================================
Telegram bot for intelligent trading powered by multi-provider AI
(OpenAI GPT, Google Gemini, Anthropic Claude, DeepSeek AI)
"""
import asyncio
import signal
import sys
import os

# Add project root to PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config, get_config
from utils.logger import setup_logger, get_logger
from database.db_manager import DatabaseManager, get_db
from ai_engine.ai_manager import AIManager
from ai_engine.market_analyzer import MarketAnalyzer
from ai_engine.predictor import AIPredictor
from ai_engine.news_scraper import NewsScraper, get_news_scraper
from trading.mt5_bridge import MT5Bridge, get_mt5
from trading.metaapi_bridge import MetaAPIBridge, get_metaapi_bridge
from trading.risk_manager import RiskManager, get_risk_manager
from trading.trade_executor import TradeExecutor, get_executor
from bot.handlers import TelegramBot


def print_banner():
    """Display startup banner"""
    banner = """
    ╔══════════════════════════════════════════════╗
    ║     🤖 AI Cyber-Trader Bot v2.0.0          ║
    ║  Multi-Provider AI Trading (Multi-Tenant)   ║
    ║  OpenAI | Gemini | Claude | DeepSeek        ║
    ╚══════════════════════════════════════════════╝
    """
    print(banner)


def setup_components():
    """Setup all system components"""
    logger = get_logger("Setup")

    # 1. Database
    logger.info("Initializing database...")
    db = get_db()
    logger.info("Database ready")

    # 2. AI Manager (Factory Pattern - multi-provider)
    logger.info("Initializing AI Manager (Factory Pattern)...")
    providers = AIManager.get_available_providers()
    logger.info(
        f"AI providers available: "
        + ", ".join(p["name"] for p in providers)
    )

    # 3. News Scraper
    logger.info("Initializing News Scraper...")
    news_scraper = get_news_scraper()
    logger.info("News scraper ready")

    # 4. Trading Bridge (MT5 native → MetaAPI.cloud → Simulation)
    logger.info("Connecting to trading bridge...")
    mt5 = get_mt5()
    connected = mt5.connect()

    if connected and not mt5.simulation:
        account = mt5.get_account_info()
        logger.info(
            f"✅ MT5 Native Connected | Balance=${account.get('balance', 0):,.2f}"
        )
    else:
        # MT5 native not available — try MetaAPI.cloud for Linux VPS
        logger.info("MT5 native unavailable, trying MetaAPI.cloud...")
        meta_cfg = config.metaapi
        if meta_cfg.token and meta_cfg.account_id:
            meta = get_metaapi_bridge(
                token=meta_cfg.token,
                account_id=meta_cfg.account_id,
                region=meta_cfg.region,
            )
            meta_connected = meta.connect()
            if meta_connected:
                mt5 = meta  # Replace with MetaAPI bridge (same interface)
                account = mt5.get_account_info()
                logger.info(
                    f"✅ MetaAPI.cloud Connected | Account={account.get('login')} | "
                    f"Balance=${account.get('balance', 0):,.2f}"
                )
            else:
                logger.warning("MetaAPI.cloud connection failed, falling back to simulation")
        else:
            logger.warning("MetaAPI.cloud not configured, running in SIMULATION mode")

    # 5. Risk Manager
    logger.info("Initializing risk manager...")
    risk = get_risk_manager(mt5)
    logger.info("Risk manager ready")

    # 6. Market Analyzer (uses AIManager factory + NewsScraper)
    logger.info("Initializing market analyzer...")
    analyzer = MarketAnalyzer(mt5, ai_manager=AIManager, news_scraper=news_scraper)
    logger.info("Market analyzer ready")

    # 7. AI Predictor (uses AIManager internally)
    logger.info("Initializing AI predictor...")
    predictor = AIPredictor()
    logger.info("Predictor ready")

    # 8. Trade Executor
    logger.info("Initializing trade executor...")
    executor = get_executor(mt5, risk, predictor, analyzer)
    logger.info("Trade executor ready")

    # 9. Telegram Bot
    logger.info("Initializing Telegram bot...")
    bot = TelegramBot(mt5, risk, executor, analyzer, predictor, news_scraper)
    logger.info("Bot ready")

    return bot


async def main():
    """Main async entry point"""
    print_banner()

    # Setup logging
    log_config = config.log
    os.makedirs(os.path.dirname(log_config.file), exist_ok=True)
    logger = setup_logger(log_config)
    logger.info("=" * 50)
    logger.info("Starting AI Cyber-Trader Bot v2.0...")
    logger.info("=" * 50)

    # Initialize components
    try:
        bot = setup_components()
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        raise

    # Start the bot
    logger.info("Starting bot polling...")
    logger.info("=" * 50)

    try:
        await bot.start()

        # Keep the event loop running until a signal is received
        stop_event = asyncio.Event()

        def _signal_handler(sig):
            logger.info(f"Received signal {sig.name}, shutting down...")
            stop_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: _signal_handler(s))

        await stop_event.wait()
    except KeyboardInterrupt:
        logger.info("\nInterrupted")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        raise
    finally:
        if bot:
            await bot.stop()
        if bot.mt5:
            bot.mt5.disconnect()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)
