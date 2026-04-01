import threading
import logging
import sys
from config import settings
from config.settings import validate_config
from core import signal_reader, position_monitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.LOG_FILE),
    ],
)
logger = logging.getLogger(__name__)

import time
from core import alpaca_trader, sheets_logger


def process_signal(signal: dict):
    from core import alpaca_trader, position_monitor
    symbol = signal["symbol"]
    action = signal["action"].upper()
    entry = float(signal["entry"])
    daily_atr = float(signal.get("daily_atr", 0))
    signal_tp = float(signal.get("take_profit", 0))
    signal_sl = float(signal.get("stop_loss", 0))

    logger.info(f"Processing signal: {action} {symbol} @ {entry}")
    qty = alpaca_trader.calculate_qty(entry)
    take_profit, stop_loss = alpaca_trader.calculate_tp_sl(action, entry, daily_atr, signal_tp, signal_sl)
    order = alpaca_trader.place_bracket_order(symbol, action, qty, take_profit, stop_loss)
    if order:
        position_monitor.register_position(symbol, {**signal, "take_profit": take_profit, "stop_loss": stop_loss}, order)
        position_monitor.update_qty(symbol, qty)
        logger.info(f"Order placed: {symbol} qty={qty} TP={take_profit} SL={stop_loss}")
    else:
        logger.error(f"Failed to place order for {symbol}")


def signal_loop():
    logger.info(f"Signal reader polling {signal_reader.get_endpoint()} every 10s")
    while True:
        try:
            for sig in signal_reader.read_new_signals():
                try:
                    process_signal(sig)
                except Exception as e:
                    logger.error(f"Error processing signal: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Signal loop error: {e}", exc_info=True)
        time.sleep(10)


def monitor_loop():
    logger.info(f"Position monitor checking every {settings.MONITOR_INTERVAL_SECONDS}s")
    while True:
        try:
            position_monitor.check_all_positions()
        except Exception as e:
            logger.error(f"Monitor loop error: {e}", exc_info=True)
        time.sleep(settings.MONITOR_INTERVAL_SECONDS)


def start_background_threads():
    issues = validate_config()
    for issue in issues:
        logger.warning(f"Config: {issue}")

    t1 = threading.Thread(target=signal_loop, daemon=True, name="SignalReader")
    t2 = threading.Thread(target=monitor_loop, daemon=True, name="PositionMonitor")
    t1.start()
    t2.start()
    logger.info("Background threads started")


start_background_threads()

from dashboard.app import app
