import logging
import json
from datetime import datetime
from config import settings

logger = logging.getLogger(__name__)

_sheet = None
_disabled = False

HEADERS = [
    "Date", "Time", "Symbol", "Direction", "Confidence",
    "Entry", "Stop", "Target", "Exit Price", "Outcome",
    "PnL %", "PnL $", "Duration", "Notes",
]


def _get_sheet():
    global _sheet, _disabled
    if _disabled:
        return None
    if _sheet is not None:
        return _sheet

    creds_data = settings.get_google_creds()
    if not creds_data:
        logger.warning("Google Sheets credentials not available — logging disabled")
        _disabled = True
        return None

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(creds_data, scopes=scopes)
        gc = gspread.authorize(creds)

        try:
            spreadsheet = gc.open(settings.GOOGLE_SHEETS_NAME)
        except gspread.SpreadsheetNotFound:
            spreadsheet = gc.create(settings.GOOGLE_SHEETS_NAME)
            logger.info(f"Created new Google Sheet: {settings.GOOGLE_SHEETS_NAME}")

        _sheet = spreadsheet.sheet1

        existing = _sheet.row_values(1)
        if existing != HEADERS:
            _sheet.clear()
            _sheet.append_row(HEADERS)
            logger.info("Initialized Google Sheet headers")

        return _sheet

    except Exception as e:
        logger.error(f"Failed to connect to Google Sheets: {e}")
        _disabled = True
        return None


def log_trade(trade: dict):
    sheet = _get_sheet()

    entry = float(trade.get("entry", 0))
    exit_price = float(trade.get("exit_price", 0))
    direction = trade.get("direction", "BUY").upper()

    if direction == "BUY":
        pnl_pct = ((exit_price - entry) / entry * 100) if entry else 0
        pnl_dollar = (exit_price - entry) * float(trade.get("qty", 0))
    else:
        pnl_pct = ((entry - exit_price) / entry * 100) if entry else 0
        pnl_dollar = (entry - exit_price) * float(trade.get("qty", 0))

    now = datetime.now()
    row = [
        now.strftime("%Y-%m-%d"),
        now.strftime("%H:%M:%S"),
        trade.get("symbol", ""),
        direction,
        trade.get("confidence", ""),
        round(entry, 4),
        round(float(trade.get("stop_loss", 0)), 4),
        round(float(trade.get("take_profit", 0)), 4),
        round(exit_price, 4),
        trade.get("outcome", ""),
        round(pnl_pct, 2),
        round(pnl_dollar, 2),
        trade.get("duration", ""),
        trade.get("notes", ""),
    ]

    if sheet:
        try:
            sheet.append_row(row)
            logger.info(f"Trade logged to Google Sheets: {trade.get('symbol')} {trade.get('outcome')}")
        except Exception as e:
            logger.error(f"Failed to append row to Google Sheets: {e}")
            _log_local_fallback(row)
    else:
        _log_local_fallback(row)


def _log_local_fallback(row: list):
    try:
        with open("trades_fallback.csv", "a") as f:
            line = ",".join(str(v) for v in row)
            f.write(line + "\n")
        logger.info("Trade logged to local fallback CSV")
    except Exception as e:
        logger.error(f"Failed to write to local fallback CSV: {e}")


def get_all_trades() -> list[dict]:
    sheet = _get_sheet()
    if not sheet:
        return _load_local_fallback_trades()

    try:
        rows = sheet.get_all_records()
        return rows
    except Exception as e:
        logger.error(f"Failed to read trades from Google Sheets: {e}")
        return _load_local_fallback_trades()


def _load_local_fallback_trades() -> list[dict]:
    import os
    trades = []
    if not os.path.exists("trades_fallback.csv"):
        return trades
    try:
        with open("trades_fallback.csv", "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) == len(HEADERS):
                    trades.append(dict(zip(HEADERS, parts)))
    except Exception as e:
        logger.error(f"Failed to read local fallback CSV: {e}")
    return trades
