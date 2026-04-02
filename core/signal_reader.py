import os
import logging
import requests
from datetime import datetime
from config import settings

logger = logging.getLogger(__name__)

SIGNALS_ENDPOINT = os.environ.get(
    "SIGNALS_ENDPOINT",
    "https://7e0d7807-49d3-4fdf-930b-d209de8955e9-00-95e76zodt574.janeway.replit.dev/api/signals"
)
REQUEST_TIMEOUT = 10

_last_processed_timestamp: str | None = None
_processed_keys: set = set()


def _signal_key(signal: dict) -> str:
    return f"{signal.get('symbol')}_{signal.get('timestamp')}_{signal.get('action')}"


def _parse_timestamp(ts: str | None) -> datetime | None:
    if not ts:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ"):
        try:
            return datetime.strptime(ts, fmt)
        except ValueError:
            continue
    return None


def read_new_signals() -> list[dict]:
    global _last_processed_timestamp

    try:
        response = requests.get(SIGNALS_ENDPOINT, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.ConnectionError:
        logger.warning(f"Cannot reach signal bot at {SIGNALS_ENDPOINT} — will retry")
        return []
    except requests.exceptions.Timeout:
        logger.warning("Signal endpoint timed out — will retry")
        return []
    except requests.exceptions.HTTPError as e:
        logger.warning(f"Signal endpoint returned error: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error polling signals: {e}")
        return []

    if isinstance(data, dict):
        signals = [data]
    elif isinstance(data, list):
        signals = data
    else:
        logger.warning("Unexpected signal response format")
        return []

    if not signals:
        return []

    new_signals = []
    for sig in signals:
        if not _validate_signal(sig):
            continue

        key = _signal_key(sig)
        if key in _processed_keys:
            continue

        sig_ts = _parse_timestamp(sig.get("timestamp"))
        last_ts = _parse_timestamp(_last_processed_timestamp)

        if last_ts and sig_ts and sig_ts <= last_ts:
            continue

        _processed_keys.add(key)
        if sig_ts:
            if not last_ts or sig_ts > last_ts:
                _last_processed_timestamp = sig.get("timestamp")

        logger.info(f"New signal received from bot: {sig.get('action')} {sig.get('symbol')} @ {sig.get('entry')} (conf={sig.get('confidence')}%)")
        new_signals.append(sig)

    return new_signals


def _validate_signal(signal: dict) -> bool:
    required = ["symbol", "action", "entry"]
    for field in required:
        if field not in signal:
            logger.warning(f"Signal missing required field '{field}': {signal}")
            return False
    if signal["action"].upper() not in ("BUY", "SELL"):
        logger.warning(f"Signal has invalid action: {signal['action']}")
        return False
    try:
        if float(signal["entry"]) <= 0:
            raise ValueError
    except (ValueError, TypeError):
        logger.warning(f"Signal has invalid entry price: {signal.get('entry')}")
        return False
    return True


def get_endpoint() -> str:
    return SIGNALS_ENDPOINT


def get_last_processed_timestamp() -> str | None:
    return _last_processed_timestamp


def get_processed_count() -> int:
    return len(_processed_keys)
