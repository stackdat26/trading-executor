import json
import os
import logging
from datetime import datetime
from config import settings

logger = logging.getLogger(__name__)

_processed_signals: set = set()


def _signal_key(signal: dict) -> str:
    return f"{signal.get('symbol')}_{signal.get('timestamp')}_{signal.get('action')}"


def read_new_signals() -> list[dict]:
    path = settings.SIGNALS_FILE
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r") as f:
            content = f.read().strip()
        if not content:
            return []

        data = json.loads(content)
        if isinstance(data, dict):
            signals = [data]
        elif isinstance(data, list):
            signals = data
        else:
            logger.warning("signals.json has unexpected format")
            return []

        new_signals = []
        for sig in signals:
            key = _signal_key(sig)
            if key not in _processed_signals:
                if _validate_signal(sig):
                    _processed_signals.add(key)
                    new_signals.append(sig)
                else:
                    logger.warning(f"Invalid signal skipped: {sig}")

        return new_signals

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse signals.json: {e}")
        return []
    except Exception as e:
        logger.error(f"Error reading signals.json: {e}")
        return []


def _validate_signal(signal: dict) -> bool:
    required = ["symbol", "action", "entry"]
    for field in required:
        if field not in signal:
            logger.warning(f"Signal missing required field: {field}")
            return False
    if signal["action"].upper() not in ("BUY", "SELL"):
        logger.warning(f"Signal has invalid action: {signal['action']}")
        return False
    if not isinstance(signal["entry"], (int, float)) or signal["entry"] <= 0:
        logger.warning(f"Signal has invalid entry price: {signal['entry']}")
        return False
    return True


def mark_processed(signal: dict):
    _processed_signals.add(_signal_key(signal))


def get_processed_count() -> int:
    return len(_processed_signals)


def write_sample_signal():
    sample = {
        "symbol": "NVDA",
        "action": "BUY",
        "entry": 164.71,
        "stop_loss": 154.52,
        "take_profit": 170.71,
        "confidence": 80,
        "daily_atr": 5.20,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(settings.SIGNALS_FILE, "w") as f:
        json.dump(sample, f, indent=2)
    logger.info(f"Sample signal written to {settings.SIGNALS_FILE}")
