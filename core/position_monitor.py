import logging
import time
from datetime import datetime, timezone
from core import alpaca_trader, sheets_logger

logger = logging.getLogger(__name__)

_tracked_positions: dict = {}


def register_position(symbol: str, signal: dict, order):
    _tracked_positions[symbol] = {
        "symbol": symbol,
        "direction": signal.get("action", "BUY").upper(),
        "entry": float(signal.get("entry", 0)),
        "stop_loss": float(signal.get("stop_loss", 0)),
        "take_profit": float(signal.get("take_profit", 0)),
        "confidence": signal.get("confidence", ""),
        "qty": 0,
        "open_time": datetime.now(timezone.utc),
        "order_id": str(order.id) if order else "",
        "notes": "",
    }
    logger.info(f"Position registered for monitoring: {symbol}")


def update_qty(symbol: str, qty: float):
    if symbol in _tracked_positions:
        _tracked_positions[symbol]["qty"] = qty


def check_all_positions():
    positions = alpaca_trader.get_positions()
    live_symbols = {p.symbol for p in positions}

    for symbol in list(_tracked_positions.keys()):
        if symbol not in live_symbols:
            logger.info(f"Position {symbol} no longer open — removing from tracking")
            del _tracked_positions[symbol]

    for position in positions:
        symbol = position.symbol
        current_price = float(position.current_price or 0)
        entry_price = float(position.avg_entry_price or 0)
        qty = float(position.qty or 0)

        meta = _tracked_positions.get(symbol)
        if not meta:
            meta = {
                "symbol": symbol,
                "direction": "BUY" if float(position.qty) > 0 else "SELL",
                "entry": entry_price,
                "stop_loss": 0,
                "take_profit": 0,
                "confidence": "",
                "qty": qty,
                "open_time": datetime.now(timezone.utc),
                "order_id": "",
                "notes": "auto-detected",
            }
            _tracked_positions[symbol] = meta

        meta["qty"] = qty
        take_profit = meta.get("take_profit", 0)
        stop_loss = meta.get("stop_loss", 0)
        open_time = meta.get("open_time", datetime.now(timezone.utc))
        hours_open = (datetime.now(timezone.utc) - open_time).total_seconds() / 3600

        outcome = None
        notes = ""

        if take_profit and current_price >= take_profit and meta["direction"] == "BUY":
            outcome = "WIN"
            notes = f"TP hit at {current_price:.2f}"
        elif take_profit and current_price <= take_profit and meta["direction"] == "SELL":
            outcome = "WIN"
            notes = f"TP hit at {current_price:.2f}"
        elif stop_loss and current_price <= stop_loss and meta["direction"] == "BUY":
            outcome = "LOSS"
            notes = f"SL hit at {current_price:.2f}"
        elif stop_loss and current_price >= stop_loss and meta["direction"] == "SELL":
            outcome = "LOSS"
            notes = f"SL hit at {current_price:.2f}"
        elif hours_open >= 48:
            outcome = "EXPIRED"
            notes = f"Max hold time exceeded ({hours_open:.1f}h)"

        if outcome:
            logger.info(f"Closing {symbol}: {outcome} — {notes}")
            result = alpaca_trader.close_position(symbol)
            if result:
                duration_str = f"{hours_open:.1f}h"
                trade_record = {
                    **meta,
                    "exit_price": current_price,
                    "outcome": outcome,
                    "duration": duration_str,
                    "notes": notes,
                }
                sheets_logger.log_trade(trade_record)
                del _tracked_positions[symbol]


def get_tracked_positions() -> dict:
    return dict(_tracked_positions)


def get_position_summary() -> list[dict]:
    positions = alpaca_trader.get_positions()
    summary = []
    for p in positions:
        symbol = p.symbol
        meta = _tracked_positions.get(symbol, {})
        entry = float(p.avg_entry_price or 0)
        current = float(p.current_price or 0)
        pnl_pct = float(p.unrealized_plpc or 0) * 100
        pnl_dollar = float(p.unrealized_pl or 0)
        open_time = meta.get("open_time")
        hours_open = 0
        if open_time:
            hours_open = (datetime.now(timezone.utc) - open_time).total_seconds() / 3600

        summary.append({
            "symbol": symbol,
            "direction": "BUY" if float(p.qty) > 0 else "SELL",
            "qty": float(p.qty),
            "entry": round(entry, 2),
            "current_price": round(current, 2),
            "take_profit": meta.get("take_profit", 0),
            "stop_loss": meta.get("stop_loss", 0),
            "pnl_pct": round(pnl_pct, 2),
            "pnl_dollar": round(pnl_dollar, 2),
            "hours_open": round(hours_open, 1),
            "confidence": meta.get("confidence", ""),
        })
    return summary
