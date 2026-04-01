import os
import json
import logging

logger = logging.getLogger(__name__)

ALPACA_BASE_URL = "https://paper-api.alpaca.markets"
ALPACA_KEY = os.environ.get("ALPACA_KEY", "")
ALPACA_SECRET = os.environ.get("ALPACA_SECRET", "")

GOOGLE_SHEETS_CREDS_RAW = os.environ.get("GOOGLE_SHEETS_CREDS", "")
GOOGLE_SHEETS_NAME = "QuantBot Trade Log"

LOG_FILE = "trading_executor.log"

POSITION_SIZE_USD = 1000.0
ATR_STOP_MULTIPLIER = 2.0
ATR_TP_MULTIPLIER = 3.0
MONITOR_INTERVAL_SECONDS = 300
MAX_POSITION_HOURS = 48

DASHBOARD_PORT = 5000
DASHBOARD_HOST = "0.0.0.0"

def get_google_creds():
    if not GOOGLE_SHEETS_CREDS_RAW:
        return None
    try:
        return json.loads(GOOGLE_SHEETS_CREDS_RAW)
    except json.JSONDecodeError:
        logger.error("Failed to parse GOOGLE_SHEETS_CREDS environment variable as JSON")
        return None

def validate_config():
    issues = []
    if not ALPACA_KEY:
        issues.append("ALPACA_KEY not set")
    if not ALPACA_SECRET:
        issues.append("ALPACA_SECRET not set")
    if not GOOGLE_SHEETS_CREDS_RAW:
        issues.append("GOOGLE_SHEETS_CREDS not set — Google Sheets logging disabled")
    return issues
