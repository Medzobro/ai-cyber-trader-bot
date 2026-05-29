#!/usr/bin/env python3
"""
AI Cyber-Trader Bot - نقطة الدخول الرئيسية
==========================================
بوت تليجرام للتداول الذكي باستخدام DeepSeek AI
"""
import asyncio
import signal
import sys
import os

# إضافة المسار إلى PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import config, get_config
from utils.logger import setup_logger, get_logger
from database.db_manager import DatabaseManager, get_db
from ai_engine.deepseek_client import DeepSeekClient
from ai_engine.market_analyzer import MarketAnalyzer
from ai_engine.predictor import AIPredictor
from trading.mt5_bridge import MT5Bridge, get_mt5
from trading.risk_manager import RiskManager, get_risk_manager
from trading.trade_executor import TradeExecutor, get_executor
from bot.handlers import TelegramBot


def print_banner():
    """عرض شعار البوت"""
    banner = """
    ╔══════════════════════════════════════════╗
    ║     🤖 AI Cyber-Trader Bot v1.0.0       ║
    ║     نظام التداول الذكي - DeepSeek AI     ║
    ╚══════════════════════════════════════════╝
    """
    print(banner)


def setup_components():
    """تجهيز جميع مكونات النظام"""
    logger = get_logger("Setup")

    # 1. قاعدة البيانات
    logger.info("📦 Initializing database...")
    db = get_db()
    logger.info("✅ Database ready")

    # 2. DeepSeek AI
    logger.info("🤖 Initializing DeepSeek AI...")
    deepseek = DeepSeekClient()

    if config.deepseek.api_key != "YOUR_DEEPSEEK_API_KEY":
        if deepseek.test_connection():
            logger.info("✅ DeepSeek AI connected")
        else:
            logger.warning("⚠️ DeepSeek AI connection failed - check API key")
    else:
        logger.warning("⚠️ DEEPSEEK_API_KEY not set. AI features disabled.")

    # 3. MT5 Bridge
    logger.info("🔗 Connecting to MT5...")
    mt5 = get_mt5()
    connected = mt5.connect()

    if connected:
        account = mt5.get_account_info()
        logger.info(
            f"✅ MT5 {'Connected' if not mt5.simulation else 'SIMULATION'}: "
            f"Balance=${account.get('balance', 0):,.2f}"
        )
    else:
        logger.error("❌ Failed to connect to MT5")

    # 4. Risk Manager
    logger.info("🛡️ Initializing risk manager...")
    risk = get_risk_manager(mt5)
    logger.info("✅ Risk manager ready")

    # 5. Market Analyzer
    logger.info("📊 Initializing market analyzer...")
    analyzer = MarketAnalyzer(mt5, deepseek)
    logger.info("✅ Market analyzer ready")

    # 6. AI Predictor
    logger.info("🧠 Initializing AI predictor...")
    predictor = AIPredictor(deepseek)
    logger.info("✅ Predictor ready")

    # 7. Trade Executor
    logger.info("💼 Initializing trade executor...")
    executor = get_executor(mt5, risk, predictor, analyzer)
    logger.info("✅ Trade executor ready")

    # 8. Telegram Bot
    logger.info("📱 Initializing Telegram bot...")
    bot = TelegramBot(mt5, risk, executor, analyzer, predictor)
    logger.info("✅ Bot ready")

    return bot


async def main():
    """الدالة الرئيسية"""
    print_banner()

    # إعداد نظام التسجيل
    log_config = config.log
    os.makedirs(os.path.dirname(log_config.file), exist_ok=True)
    logger = setup_logger(log_config)
    logger.info("=" * 50)
    logger.info("Starting AI Cyber-Trader Bot...")
    logger.info("=" * 50)

    # تجهيز المكونات
    try:
        bot = setup_components()
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        raise

    # معالج الإيقاف الآمن
    def signal_handler(sig, frame):
        logger.info("\n🛑 Shutting down...")
        if bot.mt5:
            bot.mt5.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # تشغيل البوت
    logger.info("🚀 Starting bot polling...")
    logger.info("=" * 50)

    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("\n🛑 Interrupted")
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
        raise
    finally:
        if bot:
            await bot.stop()
        if bot.mt5:
            bot.mt5.disconnect()
        logger.info("👋 Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
