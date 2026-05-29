<p align="center">
  <img src="https://img.shields.io/badge/version-2.0.0-blue" alt="Version">
  <img src="https://img.shields.io/badge/python-3.10+-green" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-orange" alt="License">
  <img src="https://img.shields.io/badge/AI-Multi--Provider-purple" alt="Multi-Provider AI">
</p>

<h1 align="center">🤖 AI Cyber-Trader Bot</h1>
<h3 align="center">Intelligent Trading Telegram Bot powered by Multi-Provider AI & MetaTrader 5</h3>

<p align="center">
  <strong>A fully automated, multi-tenant trading system combining AI-driven market analysis with MT5 execution — all from an interactive Telegram interface</strong>
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
- [🛡️ NewsGuard Protection](#️-newsguard-protection)
- [🔒 Risk Management](#-risk-management)
- [📂 File Structure](#-file-structure)
- [🛠️ Tech Stack](#️-tech-stack)
- [⚠️ Important Notes](#️-important-notes)
- [🐛 Troubleshooting](#-troubleshooting)
- [🔮 Roadmap](#-roadmap)
- [📄 License](#-license)

---

## 📋 Overview

**AI Cyber-Trader Bot v2.0** is a professional, multi-tenant Telegram bot that serves as an intelligent control panel for managing and executing automated trading operations (Forex/Gold/Indices) on **MetaTrader 5**.

Unlike single-tenant bots, **every user brings their own AI API key** and selects their preferred provider. All data is fully isolated per user (`telegram_id` as primary key) and API keys are **AES-256 encrypted** at rest.

The system consists of three core components:

| Component | Description |
|-----------|-------------|
| 📱 **Frontend** | Fully interactive Telegram interface with inline keyboards |
| 🧠 **Backend & AI** | Python server with multi-provider AI via Factory Pattern |
| 🔗 **Execution Bridge** | Direct connection to MT5 for high-speed order execution |

---

## ✨ Features

### 🎛️ Complete Telegram Dashboard
- Interactive main dashboard with inline buttons
- Real-time balance, daily P&L, and open positions display
- Auto-refresh functionality

### 🧠 Multi-Provider AI Engine (Factory Pattern)
Each user chooses their own AI provider and brings their own API key:

| Provider | Models |
|----------|--------|
| 🧠 **OpenAI GPT** | GPT-4o, GPT-4o-mini, GPT-4-turbo |
| 💎 **Google Gemini** | Gemini 2.0 Flash, Gemini 1.5 Pro |
| 🔮 **Anthropic Claude** | Claude 3.5 Sonnet, Claude 3 Opus |
| 🤖 **DeepSeek AI** | deepseek-chat, deepseek-reasoner |

- Multiple analysis modes (Predictive, News Scanning, Hybrid)
- Comprehensive technical indicators (RSI, MACD, Bollinger, ADX, ATR, Stochastic)
- **XGBoost** & **Scikit-Learn** support for ML predictions
- Configurable confidence thresholds (60% - 90%)

### 🛡️ NewsGuard — News-Driven Auto-Close
- Monitors high-impact economic news every 5 minutes
- **Automatically closes open positions** before volatile events (NFP, CPI, FOMC...)
- Pauses auto-trading during news storms
- **Per-user ON/OFF toggle** in AI Settings

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
- **Mandatory SL/TP** — no trade opens without Stop Loss & Take Profit
- Daily loss limit (auto-stop)
- Max open positions cap
- Automatic position size calculation
- Risk levels (Low 🟢, Medium 🟡, High 🟠, Critical 🔴)

### 🔐 Security
- **AES-256 encryption** for all user API keys (Fernet + PBKDF2)
- Keys are **only decrypted in RAM** during API calls, then discarded
- SHA-256 audit hashes for key tracking
- Multi-tenant database isolation per `telegram_id`

### 📊 Performance & Reports
- Daily and all-time performance reports
- Trade history with profit/loss tracking
- Win rate statistics
- Instant push notifications for trade open/close/NewsGuard alerts

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
│   ├── ai_manager.py          # Factory Pattern for 4 AI providers
│   ├── market_analyzer.py     # Market Analyzer (data + AI)
│   ├── indicators.py          # 8+ Technical Indicators
│   ├── news_scraper.py        # Economic News + ForexFactory
│   └── predictor.py           # AI + XGBoost ML Predictor
│
├── 🤖 bot/                    # Telegram Bot
│   ├── handlers.py            # 7 Commands + 30+ Callback Handlers
│   ├── keyboards.py           # 15+ Interactive Inline Keyboards
│   ├── messages.py            # 15+ Message Templates
│   └── notifications.py       # Push Notifications + Broadcast
│
├── 💹 trading/                # Trading System
│   ├── mt5_bridge.py          # MT5 Connection + Simulation Mode
│   ├── risk_manager.py        # Risk Manager + Panic Mode
│   ├── trade_executor.py      # Automated + Manual Execution
│   └── news_guard.py          # 🛡️ News-Driven Auto-Close
│
├── 🗄️ database/               # Database
│   ├── models.py              # 6 Tables (Users, Trades, Settings, AI, Performance, API Keys)
│   └── db_manager.py          # CRUD + AES-256 Encryption + Migrations
│
├── 🛠️ utils/                  # Utilities
│   ├── logger.py              # Centralized Logging
│   ├── helpers.py             # Formatting Helpers
│   └── security.py            # AES-256 + Hashing
│
├── ⚙️ config.py               # Central Configuration (dataclasses)
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
| **AI API Key** | — | User's own key (OpenAI, Gemini, Claude, or DeepSeek) |
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

#### 🧠 AI Provider API Key (User-managed):
Each user sets their own key inside the bot, but you can set server defaults in `.env`:

| Provider | URL |
|----------|-----|
| DeepSeek | https://platform.deepseek.com |
| OpenAI | https://platform.openai.com/api-keys |
| Gemini | https://aistudio.google.com/app/apikey |
| Claude | https://console.anthropic.com/settings/keys |

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

# ─── Encryption (CRITICAL: change in production!) ──
ENCRYPTION_SECRET=your-64-char-random-secret-here

# ─── AI Provider Defaults (optional server fallbacks) ──
DEEPSEEK_API_KEY=sk-...
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=AIza...
CLAUDE_API_KEY=sk-ant-...

# ─── MetaTrader 5 ───────────────────────────────
MT5_LOGIN=12345678
MT5_PASSWORD=your_mt5_password
MT5_SERVER=ICMarkets-Demo

# ─── Database ───────────────────────────────────
DB_PATH=data/trader_bot.db
```

> ⚠️ **Security:** Never commit `.env` to git. It is already in `.gitignore`.

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
╔══════════════════════════════════════════════╗
║     🤖 AI Cyber-Trader Bot v2.0.0          ║
║  Multi-Provider AI Trading (Multi-Tenant)   ║
║  OpenAI | Gemini | Claude | DeepSeek        ║
╚══════════════════════════════════════════════╝
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

### Setting Up Your AI Provider:
1. Go to **🤖 AI Settings**
2. Tap **🔑 AI Provider & API Key**
3. Select your preferred provider (OpenAI, Gemini, Claude, DeepSeek)
4. Tap **🔑 Set API Key** and send your key
5. Tap **✅ Validate Key** to confirm it works

> 🔒 Your key is **AES-256 encrypted** before storage and only held in memory during analysis.

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

## 🛡️ NewsGuard Protection

**NewsGuard** is an intelligent shield that monitors economic news and protects your account:

- 🔍 Scans for high-impact events (NFP, CPI, FOMC, GDP...) every **5 minutes**
- ⏰ Triggers when news is **imminent within 15 minutes**
- 🔒 **Auto-closes all open positions** for the affected symbol
- ⏸️ **Pauses auto-trading** until the event passes
- 📱 Sends an instant alert with closed positions & P&L
- 🎛️ **Per-user toggle** — enable/disable from 🤖 AI Settings

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
- 🛡️ **Auto Stop Loss:** Dynamic ATR-based (mandatory)
- 💰 **Auto Take Profit:** Dynamic ATR-based (mandatory)
- 🚨 **Panic Button:** Instant close all positions
- 🛡️ **NewsGuard:** Auto-close before high-impact news

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
│   ├── ai_manager.py                #   - Factory Pattern (OpenAI/Gemini/Claude/DeepSeek)
│   ├── indicators.py                #   - 8+ Technical Indicators + Candlestick Patterns
│   ├── market_analyzer.py           #   - Market Analysis + Data Simulation
│   ├── news_scraper.py              #   - Economic News (ForexFactory + Simulation)
│   └── predictor.py                 #   - AI Prediction + XGBoost ML
│
├── bot/                             # 🤖 Telegram Interface
│   ├── __init__.py
│   ├── handlers.py                  #   - 7 Commands + 30+ Callback Handlers
│   ├── keyboards.py                 #   - 15+ Interactive Inline Keyboards
│   ├── messages.py                  #   - 15+ Message Templates
│   └── notifications.py             #   - Push Notifications + Broadcast
│
├── trading/                         # 💹 Trading System
│   ├── __init__.py
│   ├── mt5_bridge.py                #   - MT5 Connection + Full Simulation Mode
│   ├── risk_manager.py              #   - 7 Risk Checks + Panic Mode
│   ├── trade_executor.py            #   - Automated + Manual Execution
│   └── news_guard.py                #   - 🛡️ News-Driven Auto-Close
│
├── database/                        # 🗄️ Database
│   ├── __init__.py
│   ├── models.py                    #   - 6 Tables (Users, Trades, Settings, AI, Performance, API Keys)
│   └── db_manager.py                #   - CRUD + Encryption + Auto-Migrations
│
└── utils/                           # 🛠️ Utilities
    ├── __init__.py
    ├── logger.py                    #   - Centralized Logging System
    ├── helpers.py                   #   - Currency & Percentage Formatting
    └── security.py                  #   - AES-256 + PBKDF2 + Hashing
```

---

## 🛠️ Tech Stack

| Technology | Usage |
|------------|-------|
| **Python 3.10+** | Core programming language |
| **python-telegram-bot** | Telegram Bot API (Async) |
| **OpenAI SDK** | OpenAI & DeepSeek API communication |
| **SQLAlchemy** | Database ORM |
| **SQLite** | Local database |
| **Pandas & NumPy** | Data processing & indicators |
| **Scikit-Learn** | ML preprocessing |
| **XGBoost** | Advanced ML model |
| **MetaTrader5** | Trading platform bridge |
| **APScheduler** | Periodic task scheduling (NewsGuard) |
| **cryptography** | AES-256 encryption |
| **python-dotenv** | Environment variable management |

---

## ⚠️ Important Notes

### 🔐 Security:
- **Never share your `.env` file** — it's already in `.gitignore`
- **Change `ENCRYPTION_SECRET`** in production to a random 64-character string
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
<summary><b>❌ Error: Invalid AI API Key</b></summary>

- Verify the key in the bot's 🤖 AI Settings
- Make sure you have credits in your AI account
- Test the connection using the ✅ Validate Key button
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

<details>
<summary><b>❌ NewsGuard not appearing</b></summary>

Make sure you have open positions. NewsGuard only activates when:
1. You have **open trades**
2. **NewsGuard is enabled** in 🤖 AI Settings
3. **High-impact news** is imminent within 15 minutes
</details>

---

## 🔮 Roadmap

- [x] Multi-provider AI support (OpenAI, Gemini, Claude, DeepSeek)
- [x] AES-256 encrypted API key storage
- [x] NewsGuard — auto-close on high-impact news
- [x] NewsGuard per-user toggle
- [ ] Historical data backtesting system
- [ ] MetaAPI support for cloud servers
- [ ] Real-time economic news WebSocket feed
- [ ] Web Dashboard
- [ ] Docker & docker-compose support
- [ ] Email notifications
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
