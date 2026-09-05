# 📈 Automated Market Scanner Suite (Stocks & Crypto)

A lightweight, production-ready Python scanner suite designed for automated technical market analysis. It scans top global equities and cryptocurrency pairs, identifies key technical setups (RSI oversold conditions, trend alignments, and demand candle/pinbar patterns), and sends structured, interactive HTML alerts directly to Telegram.

Engineered to run seamlessly via **GitHub Actions** (100% serverless) or on any local/cloud Linux server via standard cron jobs.

---

## ✨ Key Features

### 📊 Stock Scanner (`stock_scanner.py`)
* **Multi-Currency Market Data**: Powered by `yfinance` for reliable stock tracking across USD, EUR, and GBP assets.
* **Daily Timeframe Focus**: Scans daily candles (1D) to filter out intraday market noise and false signals.
* **Technical Indicators**:
  * **1D RSI (14)**: Measures momentum and overbought/oversold levels.
  * **200 EMA**: Identifies major trend direction (Above / Below 200 EMA).
* **Interactive Charts**: Generates clean, clickable TradingView hyperlinks for instant chart navigation.

### 🪙 Crypto Scanner (`crypto_scanner.py`)
* **Exchange Integration**: Powered by `ccxt` connected directly to public exchange endpoints (Kraken Spot).
* **Multi-Timeframe Strategy**:
  * **4H RSI (14)**: Fast execution timeframe for swing trading setups.
  * **4H Bullish Pinbar Detection**: Identifies demand rejection wicks ($\ge 50\%$ lower wick ratio).
  * **1D 200 SMA**: High-timeframe trend filter.
* **Daily Market Digest**: Automatically compiles and sends a clean daily market summary at 21:00 (Europe/London).
* **Volume Analytics**: Measures 4H volume relative to the 20-period moving average to spot volume spikes.

---

## 📁 Project Structure

```text
├── .github/
│   └── workflows/          # GitHub Actions automated workflow schedules
├── .env.example            # Environment variable template for setup
├── .gitignore              # Protects sensitive local credentials & cache
├── README.md               # Documentation and setup guide
├── requirements.txt        # Python package dependencies
├── crypto_scanner.py       # Asynchronous Crypto market scanner
└── stock_scanner.py        # Asynchronous Stock market scanner
