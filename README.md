# QuantBot Trading Executor

> Automated paper trading executor that connects to the QuantBot signal bot, places trades on an Alpaca paper account, and logs every result to Google Sheets — fully hands-free.

Executor Dashboard: https://trading-executor-e0gy.onrender.com/

---

## How It Works

```
QuantBot Signal Bot
        │
        │  POST /api/signals  (polled every 10s)
        ▼
Trading Executor
        │
        ├──▶  Alpaca Paper Account
        │         • Market order placed
        │         • Bracket order set (TP + SL)
        │         • Position monitored every 5 min
        │
        ├──▶  Google Sheets
        │         • Every closed trade logged automatically
        │         • Columns: Date, Symbol, Entry, Exit, PnL, Outcome...
        │
        └──▶  Live Dashboard (port 5000)
                  • Account value, win rate, open positions
                  • Trade history, equity curve
                  • Auto-refreshes every 30 seconds
```

The executor polls the QuantBot signal bot endpoint every **10 seconds**. When a new signal arrives, it calculates position size ($1,000 per trade), places a market order on Alpaca, and immediately attaches a bracket order with stop loss and take profit levels derived from the signal's ATR. Every 5 minutes it checks all open positions — if price hits TP or SL, or the position has been open more than 48 hours, it closes and logs the result.

---

## Features

- **Fully automated** — zero manual intervention required after setup
- **Webhook signal polling** — reads live signals from the QuantBot bot every 10 seconds
- **Bracket orders** — TP and SL placed immediately after every entry
- **Smart position sizing** — $1,000 per trade, quantity calculated from entry price
- **Position monitoring** — checks every 5 minutes for TP hit, SL hit, or 48h expiry
- **Google Sheets logging** — every trade auto-logged with full details and PnL
- **Local CSV fallback** — trades saved locally if Google Sheets is unavailable
- **Live dashboard** — dark-themed Flask app showing account stats, positions and equity curve
- **Graceful error handling** — retries on API failures, warns on config issues
- **Paper trading only** — hardcoded to Alpaca paper endpoint, never touches live funds

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Trading API | [Alpaca](https://alpaca.markets) (`alpaca-py`) |
| Signal Source | QuantBot webhook endpoint |
| Logging | Google Sheets API (`gspread`) |
| Dashboard | Flask + Chart.js |
| Auth | Google Service Account (OAuth2) |
| Scheduling | Native Python threads |

---

## File Structure

```
trading-executor/
├── main.py                     # Entry point — starts all threads + dashboard
├── requirements.txt
├── config/
│   └── settings.py             # All config loaded from environment variables
├── core/
│   ├── alpaca_trader.py        # Alpaca API — orders, positions, account
│   ├── position_monitor.py     # Monitors open positions for TP/SL/expiry
│   ├── signal_reader.py        # Polls QuantBot webhook for new signals
│   └── sheets_logger.py        # Logs closed trades to Google Sheets
└── dashboard/
    └── app.py                  # Flask web dashboard (dark theme, auto-refresh)
```

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/your-username/trading-executor.git
cd trading-executor
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set environment variables

| Variable | Description |
|---|---|
| `ALPACA_KEY` | Alpaca paper trading API key |
| `ALPACA_SECRET` | Alpaca paper trading secret key |
| `GOOGLE_SHEETS_CREDS` | Full JSON string of your Google service account key file |
| `GOOGLE_SHEET_ID` | ID of your Google Sheet (found in the sheet URL) |

> Get your Alpaca keys from [app.alpaca.markets](https://app.alpaca.markets) under **Paper Trading → API Keys**.
>
> For Google Sheets: create a service account in Google Cloud Console, enable the Sheets and Drive APIs, download the JSON key, and share your sheet with the service account email.

### 4. Run

```bash
python main.py
```

Dashboard available at `http://localhost:5000`

---

## Roadmap

- [x] Alpaca paper trading integration
- [x] Automated signal reading from QuantBot
- [x] Bracket orders with TP and SL
- [x] Position monitoring every 5 minutes
- [x] Google Sheets auto logging
- [x] Live dashboard
- [x] Live trading integration
- [ ] Multi-broker support
- [ ] Performance analytics

---

## QuantBot Ecosystem

This project is part of a larger suite of algorithmic trading tools:

| Repo | Description |
|---|---|
| [trading-bot](https://github.com/stackdat26/trading-bot) | The core signal generation bot — scans markets and outputs signals |
| [trading-screener](https://github.com/stackdat26/trading-screener) | Market screener that filters symbols by technical conditions |
| **trading-executor** | This repo — receives signals and executes trades automatically |

---

## Author

Built by a 17-year-old quant trader passionate about algorithmic trading, market microstructure, and building systems that trade while you sleep.

---

## License

MIT — do whatever you want with it.
