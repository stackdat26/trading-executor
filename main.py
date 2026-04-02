import logging
import sys
import time
import threading
from datetime import datetime
from config import settings
from config.settings import validate_config
from core import alpaca_trader, signal_reader, position_monitor
from dashboard.app import run_dashboard

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.LOG_FILE),
    ],
)
logger = logging.getLogger(__name__)


INDEX_TO_ETF = {
    "^IXIC": "QQQ",
    "^GSPC": "SPY",
    "^DJI": "DIA",
    "^RUT": "IWM",
    "^VIX": "VIXY",
}


def process_signal(signal: dict):
    raw_symbol = signal["symbol"]
    symbol = INDEX_TO_ETF.get(raw_symbol, raw_symbol)
    if symbol != raw_symbol:
        logger.info(f"Mapped index symbol {raw_symbol} → {symbol}")
    action = signal["action"].upper()
    index_entry = float(signal["entry"])
    daily_atr = float(signal.get("daily_atr", 0))
    signal_tp = float(signal.get("take_profit", 0))
    signal_sl = float(signal.get("stop_loss", 0))

    # When symbol was mapped from an index, fetch the real ETF price and
    # rescale TP/SL by the same percentage distance from the index entry.
    if symbol != raw_symbol:
        etf_price = alpaca_trader.get_latest_price(symbol)
        if not etf_price:
            logger.error(f"Could not fetch live price for {symbol}, skipping signal")
            return
        entry = etf_price
        if index_entry > 0:
            if signal_tp:
                signal_tp = round(etf_price * (signal_tp / index_entry), 2)
            if signal_sl:
                signal_sl = round(etf_price * (signal_sl / index_entry), 2)
        logger.info(f"Rescaled prices for {symbol}: entry={entry:.2f} TP={signal_tp} SL={signal_sl}")
    else:
        entry = index_entry

    logger.info(f"Processing signal: {action} {symbol} @ {entry} (ATR={daily_atr}, conf={signal.get('confidence')}%)")

    qty = alpaca_trader.calculate_qty(entry)
    take_profit, stop_loss = alpaca_trader.calculate_tp_sl(action, entry, daily_atr, signal_tp, signal_sl)

    order = alpaca_trader.place_bracket_order(symbol, action, qty, take_profit, stop_loss)
    if order:
        position_monitor.register_position(symbol, {**signal, "take_profit": take_profit, "stop_loss": stop_loss}, order)
        position_monitor.update_qty(symbol, qty)
        logger.info(f"Order placed successfully for {symbol}: qty={qty}, TP={take_profit}, SL={stop_loss}")
    else:
        logger.error(f"Failed to place order for {symbol}")


def signal_loop():
    logger.info(f"Signal reader started — polling {signal_reader.get_endpoint()} every 10s")
    while True:
        try:
            new_signals = signal_reader.read_new_signals()
            for sig in new_signals:
                try:
                    process_signal(sig)
                except Exception as e:
                    logger.error(f"Error processing signal {sig.get('symbol')}: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Signal loop error: {e}", exc_info=True)
        time.sleep(10)


def monitor_loop():
    logger.info(f"Position monitor started — checking every {settings.MONITOR_INTERVAL_SECONDS}s")
    while True:
        try:
            position_monitor.check_all_positions()
        except Exception as e:
            logger.error(f"Monitor loop error: {e}", exc_info=True)
        time.sleep(settings.MONITOR_INTERVAL_SECONDS)


def main():
    logger.info("=" * 60)
    logger.info("  QuantBot Trading Executor starting up")
    logger.info(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    issues = validate_config()
    if issues:
        for issue in issues:
            logger.warning(f"Config warning: {issue}")

    signal_thread = threading.Thread(target=signal_loop, daemon=True, name="SignalReader")
    signal_thread.start()

    monitor_thread = threading.Thread(target=monitor_loop, daemon=True, name="PositionMonitor")
    monitor_thread.start()

    logger.info("Background threads started — launching dashboard")
    run_dashboard()


if __name__ == "__main__":
    main()
