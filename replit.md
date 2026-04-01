# Trading Executor

## Project Overview
Automated paper trading executor that connects to a QuantBot signal bot, places trades on an Alpaca paper trading account, monitors positions, and logs results to Google Sheets automatically. Includes a live dashboard.

## Architecture
- **Language**: Python 3.11
- **Type**: Always-running service with Flask web dashboard
- **Workflow**: Webview on port 5000 (`python main.py`)
- **Deployment**: VM (always-on)

## File Structure
```
trading-executor/
├── main.py                  # Entry point — starts all threads + dashboard
├── requirements.txt
├── config/
│   └── settings.py          # All config loaded from env vars
├── core/
│   ├── alpaca_trader.py     # Alpaca paper trading API calls
│   ├── position_monitor.py  # Monitors open positions for TP/SL/expiry
│   ├── signal_reader.py     # Reads signals.json written by QuantBot
│   └── sheets_logger.py     # Logs trades to Google Sheets
└── dashboard/
    └── app.py               # Flask web dashboard (dark theme)
```

## Key Dependencies
- `alpaca-py` — Alpaca paper trading API client
- `flask` — Dashboard web server
- `gspread` + `google-auth` — Google Sheets integration
- `requests` — HTTP client
- `python-dotenv` — Environment variable management
- `pytz` — Timezone support

## Required Environment Variables
Set these as secrets before running with live data:
- `ALPACA_KEY` — Alpaca API key (paper account)
- `ALPACA_SECRET` — Alpaca secret key (paper account)
- `GOOGLE_SHEETS_CREDS` — Google service account JSON credentials (string)

## Signal Format
QuantBot writes signals to `signals.json` in the format:
```json
{
  "symbol": "NVDA",
  "action": "BUY",
  "entry": 164.71,
  "stop_loss": 154.52,
  "take_profit": 170.71,
  "confidence": 80,
  "daily_atr": 5.20,
  "timestamp": "2026-04-01 19:31:00"
}
```

## Trade Logic
- Position size: $1,000 per trade (paper)
- Stop loss: entry − (ATR × 2.0)
- Take profit: entry + (ATR × 3.0)
- Bracket orders placed immediately after entry
- Positions checked every 5 minutes
- Max hold time: 48 hours (auto-close → EXPIRED)

## Dashboard
- URL: port 5000
- Shows: account value, trade stats, open positions, trade history, equity curve
- Auto-refreshes every 30 seconds
- Dark theme (#0d1117)
