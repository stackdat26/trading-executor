# Trading Executor

## Project Overview
Automated paper trading executor that connects to the QuantBot signal bot, places trades on an Alpaca paper trading account, monitors positions, and logs results to Google Sheets automatically.

## Architecture
- **Language**: Python 3.11
- **Type**: Always-running background service (no frontend)
- **Workflow**: Console (`python main.py`)
- **Deployment**: VM (always-on)

## Key Dependencies
- `alpaca-trade-api` — Alpaca paper trading API client
- `gspread` + `google-auth` — Google Sheets integration for logging
- `requests` — HTTP client for QuantBot signal source
- `python-dotenv` — Environment variable management
- `schedule` — Job scheduling
- `websocket-client` — WebSocket connections for live data

## Configuration
API keys and credentials should be stored as environment secrets:
- `ALPACA_API_KEY` — Alpaca API key
- `ALPACA_SECRET_KEY` — Alpaca secret key
- `ALPACA_BASE_URL` — Alpaca base URL (paper trading endpoint)
- `QUANTBOT_API_KEY` — QuantBot signal bot API key
- `GOOGLE_SHEETS_CREDENTIALS` — Google service account JSON credentials

## Project Structure
- `main.py` — Entry point
- `requirements.txt` — Python dependencies
