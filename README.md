<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/python-3.10+-green" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
  <img src="https://img.shields.io/badge/ai-DeepSeek-purple" alt="DeepSeek AI">
</p>

<h1 align="center">🤖 AI Cyber-Trader Bot</h1>
<h3 align="center">Intelligent Trading Telegram Bot powered by DeepSeek AI & MetaTrader 5</h3>

<p align="center">
  <strong>A fully automated trading system combining AI-driven market analysis with MT5 execution — all from an interactive Telegram interface</strong>
</p>

---

## 📑 Table of Contents

- [📋 Overview](#-overview)
- [✨ Features](#-features)
- [🏗️ Architecture](#️-architecture)
- [📦 Requirements](#-requirements)
- [🚀 Installation](#-installation)
- [⚙️ Configuration](#️-configuration)
- [🎮 Running the Bot](#-running-the-bot)
- [📱 Bot Commands](#-bot-commands)
- [🤖 AI Configuration](#-ai-configuration)
- [🔒 Risk Management](#-risk-management)
- [📂 File Structure](#-file-structure)
- [🛠️ Tech Stack](#️-tech-stack)
- [⚠️ Important Notes](#️-important-notes)
- [🐛 Troubleshooting](#-troubleshooting)
- [🔮 Roadmap](#-roadmap)
- [📄 License](#-license)

---

## 📋 Overview

**AI Cyber-Trader Bot** is a professional Telegram bot that serves as an intelligent control panel for managing and executing automated trading operations (Forex/Gold/Indices) on **MetaTrader 5**, powered by **DeepSeek AI** for market analysis and decision-making.

The system consists of three core components:

| Component | Description |
|-----------|-------------|
| 📱 **Frontend** | Fully interactive Telegram interface with inline keyboards |
| 🧠 **Backend & AI** | Python server running continuous analysis with DeepSeek AI + technical indicators |
| 🔗 **Execution Bridge** | Direct connection to MT5 for high-speed order execution |

---

## ✨ Features

### 🎛️ Complete Telegram Dashboard
- Interactive main dashboard with inline buttons
- Real-time balance, daily P&L, and open positions display
- Auto-refresh functionality

### 🧠 AI Engine
- **DeepSeek API** integration for market analysis
- Multiple analysis modes (Predictive, News Scanning, Hybrid)
- Comprehensive technical indicators (RSI, MACD, Bollinger, ADX, ATR, Stochastic)
- **XGBoost** & **Scikit-Learn** support for ML predictions
- Configurable confidence thresholds (60% - 90%)

### 💹 Multi-Asset Support
| Symbol | Asset |
|--------|-------|
| XAUUSD | 🏆 Gold |
| EURUSD | 💶 EUR/USD |
| GBPUSD | 💷 GBP/USD |
| USDJPY | 💴 USD/JPY |
| BTCUSD | ₿ Bitcoin |
| US30 | 📊 Dow Jones |
| NAS100 | 📈 Nasdaq |

### 🔒 Advanced Risk Management
- **Panic Button** 🚨 — instant close all positions
- Daily loss limit (auto-stop)
- Max open positions cap
- Automatic position size calculation
- Risk levels (Low 🟢, Medium 🟡, High 🟠, Critical 🔴)

### 📊 Performance & Reports
- Daily and all-time performance reports
- Trade history with profit/loss tracking
- Win rate statistics
- Instant push notifications for trade open/close

### 🔄 Simulation Mode
- Full functionality **without a real MT5 connection**
- Realistic market data simulation for testing
- Perfect for trying all features risk-free

---

## 🏗️ Architecture

```
ai-cyber-trader-bot/
│
├── 🧠 ai_engine/              # AI & ML Engine
│   ├── deepseek_client.py     # DeepSeek API Client
│   ├── indicators.py          # Technical Indicators (RSI, MACD, ADX...)
│   ├── market_analyzer.py     # Market Analyzer (data + AI)
│   └── predictor.py           # AI + ML Predictor (XGBoost)
│
├── 🤖 bot/                    # Telegram Bot
│   ├── handlers.py            # Command & Callback Handlers
│   ├── keyboards.py           # Inline Keyboards
│   ├── messages.py            # Message Templates
│   └── notifications.py       # Push Notification Manager
│
├── 💹 trading/                # Trading System
│   ├── mt5_bridge.py          # MetaTrader 5 Bridge
│   ├── risk_manager.py        # Risk Manager
│   └── trade_executor.py      # Trade Executor
│
├── 🗄️ database/               # Database
│   ├── models.py              # SQLAlchemy Models
│   └── db_manager.py          # Database Manager
│
├── 🛠️ utils/                  # Utilities
│   ├── logger.py              # Logging System
│   └── helpers.py             # Helper Functions
│
├── ⚙️ config.py               # Central Configuration
├── 🚀 main.py                 # Entry Point
├── 📦 requirements.txt        # Dependencies
└── 📄 .env.example            # Environment Variables Template
```

---

## 📦 Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| **Python** | 3.10+ | ⚠️ Required |
| **pip** | Latest | For package installation |
| **MetaTrader 5** | Any | Optional (for live trading) |
| **DeepSeek API Key** | — | From [platform.deepseek.com](https://platform.deepseek.com) |
| **Telegram Bot Token** | — | From [@BotFather](https://t.me/BotFather) |

> ℹ️ On **Linux**, the MetaTrader5 library requires **Wine** to run. You can use simulation mode instead.

---

## 🚀 Installation

### Step 1️⃣: Clone the Repository

```bash
git clone https://github.com/Medzobro/ai-cyber-trader-bot.git
cd ai-cyber-trader-bot
```

### Step 2️⃣: Create & Activate Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate:
# Linux / macOS:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### Step 3️⃣: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4️⃣: Configure Environment Variables

```bash
cp .env.example .env
nano .env    # or use any text editor
```

Fill in the required API keys (see [Configuration](#️-configuration) below).

### Step 5️⃣: Get Required API Keys

#### 🤖 Telegram Bot Token:
1. Open Telegram and chat with [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Choose a name and username for your bot
4. Copy the token you receive

#### 🧠 DeepSeek API Key:
1. Sign up at [platform.deepseek.com](https://platform.deepseek.com)
2. Navigate to API Keys
3. Create a new key and copy it

#### 💹 MT5 Credentials (Optional):
- `MT5_LOGIN`: Your trading account number
- `MT5_PASSWORD`: Your trading account password
- `MT5_SERVER`: Broker server name (e.g., `ICMarkets-Demo`)

---

## ⚙️ Configuration

Edit the `.env` file with your credentials:

```env
# ─── Telegram ───────────────────────────────────
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_IDS=123456789

# ─── DeepSeek AI ────────────────────────────────
DEEPSEEK_API_KEY=sk-your-deepseek-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# ─── MetaTrader 5 ───────────────────────────────
MT5_LOGIN=12345678
MT5_PASSWORD=your_mt5_password
MT5_SERVER=ICMarkets-Demo

# ─── Database ───────────────────────────────────
DB_PATH=data/trader_bot.db
```

---

## 🎮 Running the Bot

### Direct Run:

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Start the bot
python3 main.py
```

You'll see the startup banner:

```
╔══════════════════════════════════════════╗
║     🤖 AI Cyber-Trader Bot v1.0.0       ║
║   Intelligent Trading System - DeepSeek AI ║
╚══════════════════════════════════════════╝
```

### Run as Background Service (Linux):

```bash
# Using nohup
nohup python3 main.py > logs/bot.log 2>&1 &

# Or using screen/tmux
screen -S trader
python3 main.py
# CTRL+A, D to detach
```

### Run with Docker (coming soon):

```bash
docker-compose up -d
```

---

## 📱 Bot Commands

After starting the bot, find it on Telegram and use these commands:

| Command | Function |
|---------|----------|
| `/start` | Display the main dashboard |
| `/help` | Help guide and command list |
| `/status` | Bot status and current positions |
| `/analyze` | Analyze current market using AI |
| `/report` | View performance & earnings report |
| `/settings` | View current settings |
| `/panic` | 🚨 Emergency — close all positions |

### Interactive Dashboard Buttons:

```
┌──────────────────────────────────────────┐
│ 🚀 Start Auto Trading   │ 🛑 Pause        │
├──────────────────────────────────────────┤
│ 🤖 AI Settings          │ ⚙️ Trade Setup   │
├──────────────────────────────────────────┤
│ 📈 Performance Reports  │ 🔒 Risk Mgmt     │
├──────────────────────────────────────────┤
│ 📊 Analyze Market Now   │ 🔄 Refresh       │
├──────────────────────────────────────────┤
│        🚨 Close All Positions Now          │
└──────────────────────────────────────────┘
```

---

## 🤖 AI Configuration

### Analysis Modes:

| Mode | Description |
|------|-------------|
| 🧠 **Predictive Analysis** | Predict next candle direction using technical indicators & mathematical models |
| 📰 **News Scanning** | Fetch economic news and auto-pause trading before high-impact events |
| 🔀 **Hybrid** | Combine predictive analysis with news scanning |

### Confidence Thresholds:

| Level | Description |
|-------|-------------|
| **60%** | Relaxed — more signals, higher risk |
| **70%** | Balanced (default) |
| **80%** | Conservative — only strong signals |
| **90%** | Very cautious — fewest trades |

### Supported Technical Indicators:

- 📊 **RSI** — Relative Strength Index (Overbought/Oversold)
- 📈 **MACD** — Moving Average Convergence Divergence
- 📉 **EMA/SMA** — Moving Averages (9, 20, 50, 200)
- 📊 **Bollinger Bands** — Volatility bands
- 📐 **ADX** — Average Directional Index
- 📏 **ATR** — Average True Range (volatility)
- 🎯 **Stochastic** — Stochastic Oscillator
- 🕯️ **Candlestick Patterns** — Doji, Hammer, Shooting Star, Engulfing

---

## 🔒 Risk Management

### Risk Levels:

| Level | Meaning | Action |
|-------|---------|--------|
| 🟢 **Low** | Normal trading | Standard monitoring |
| 🟡 **Medium** | Minor losses | Active monitoring |
| 🟠 **High** | Significant losses | Reduce positions |
| 🔴 **Critical** | Limit exceeded | Auto-stop trading |

### Protection Limits:

- ⚠️ **Max Daily Loss:** 5% (configurable)
- 📦 **Max Open Positions:** 3
- 🛡️ **Auto Stop Loss:** 500 pips
- 💰 **Auto Take Profit:** 800 pips
- 🚨 **Panic Button:** Instant close all positions

---

## 📂 File Structure

```
ai-cyber-trader-bot/
│
├── main.py                          # 🚀 Main entry point
├── config.py                        # ⚙️ Central configuration (dataclass)
├── requirements.txt                 # 📦 Dependencies list
├── .env.example                     # 🔑 Environment variables template
├── .gitignore                       # 🙈 Git ignore rules
├── README.md                        # 📖 This file
│
├── ai_engine/                       # 🧠 AI & ML Engine
│   ├── __init__.py
│   ├── deepseek_client.py           #   - DeepSeek API Client (OpenAI-compatible)
│   ├── indicators.py                #   - 8 Technical Indicators + Candlestick Patterns
│   ├── market_analyzer.py           #   - Market Analysis + Data Simulation
│   └── predictor.py                 #   - AI Prediction + XGBoost ML
│
├── bot/                             # 🤖 Telegram Interface
│   ├── __init__.py
│   ├── handlers.py                  #   - 7 Command Handlers + 30+ Callback Handlers
│   ├── keyboards.py                 #   - 15 Interactive Inline Keyboards
│   ├── messages.py                  #   - 15+ Message Templates
│   └── notifications.py            #   - Push Notifications + Broadcast
│
├── trading/                         # 💹 Trading System
│   ├── __init__.py
│   ├── mt5_bridge.py               #   - MT5 Connection + Full Simulation Mode
│   ├── risk_manager.py             #   - 7 Risk Checks + Panic Mode
│   └── trade_executor.py           #   - Automated + Manual Execution
│
├── database/                        # 🗄️ Database
│   ├── __init__.py
│   ├── models.py                   #   - 5 Tables (Users, Trades, Settings, AI, Performance)
│   └── db_manager.py               #   - CRUD Manager with Context Manager
│
└── utils/                           # 🛠️ Utilities
    ├── __init__.py
    ├── logger.py                    #   - Centralized Logging System
    └── helpers.py                   #   - Currency & Percentage Formatting
```

---

## 🛠️ Tech Stack

| Technology | Usage |
|------------|-------|
| **Python 3.10+** | Core programming language |
| **python-telegram-bot** | Telegram Bot API (Async) |
| **OpenAI SDK** | DeepSeek API communication |
| **SQLAlchemy** | Database ORM |
| **SQLite** | Local database |
| **Pandas & NumPy** | Data processing & indicators |
| **Scikit-Learn** | ML preprocessing |
| **XGBoost** | Advanced ML model |
| **MetaTrader5** | Trading platform bridge |
| **APScheduler** | Periodic task scheduling |
| **python-dotenv** | Environment variable management |

---

## ⚠️ Important Notes

### 🔐 Security:
- **Never share your `.env` file** — it's already in `.gitignore`
- Use strong passwords for your MT5 account
- Keep a backup of your `.env` file

### 💰 Trading:
- ⚠️ **Always start with a Demo account first**
- Test the strategy for at least a week before going live
- Never risk more than you can afford to lose
- Automated trading is not 100% guaranteed

### 🖥️ Operating System:
- **Windows:** Full functionality with real MT5
- **Linux:** Works in simulation mode (or with Wine for MT5)
- **Mac:** Works in simulation mode

### 🔄 Simulation Mode:
If no MT5 connection is available, the bot automatically runs in **simulation mode**:
- Generates realistic market data for testing
- Executes virtual trades
- Perfect for exploring all features risk-free

---

## 🐛 Troubleshooting

<details>
<summary><b>❌ Error: TELEGRAM_BOT_TOKEN not set</b></summary>

Make sure you created the `.env` file and added the correct token:
```bash
cp .env.example .env
nano .env  # Add TELEGRAM_BOT_TOKEN=your_bot_token
```
</details>

<details>
<summary><b>❌ Error: Invalid DeepSeek API Key</b></summary>

- Verify the key in `.env`: `DEEPSEEK_API_KEY=sk-...`
- Make sure you have credits in your DeepSeek account
- Test the connection manually at [platform.deepseek.com](https://platform.deepseek.com)
</details>

<details>
<summary><b>❌ MetaTrader5 import failed</b></summary>

This is normal on Linux. The bot will automatically run in simulation mode.
For live trading on Linux, you need Wine + MT5 or MetaAPI.
</details>

<details>
<summary><b>❌ Error: sqlite3.OperationalError</b></summary>

Make sure the `data/` directory exists and is writable:
```bash
mkdir -p data logs
chmod 755 data logs
```
</details>

---

## 🔮 Roadmap

- [ ] Historical data backtesting system
- [ ] MetaAPI support for cloud servers
- [ ] Real economic news integration (ForexFactory API)
- [ ] Web Dashboard
- [ ] Docker & docker-compose support
- [ ] Email notifications
- [ ] Multi-user support with permissions
- [ ] Trading strategy sharing & cloning

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  <strong>⚡ Built by <a href="https://github.com/Medzobro">Medzobro</a> | 2025 ⚡</strong>
</p>

<p align="center">
  <sub>🤖 AI Cyber-Trader Bot — Because Smart Trading Starts Here</sub>
</p>
