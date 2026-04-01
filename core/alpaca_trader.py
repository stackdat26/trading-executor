import time
import logging
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, TakeProfitRequest, StopLossRequest
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
from config import settings

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 2


def _get_trading_client():
    return TradingClient(
        api_key=settings.ALPACA_KEY,
        secret_key=settings.ALPACA_SECRET,
        paper=True,
    )


def _get_data_client():
    return StockHistoricalDataClient(
        api_key=settings.ALPACA_KEY,
        secret_key=settings.ALPACA_SECRET,
    )


def get_account():
    for attempt in range(MAX_RETRIES):
        try:
            client = _get_trading_client()
            return client.get_account()
        except Exception as e:
            logger.warning(f"get_account attempt {attempt+1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
    logger.error("get_account failed after all retries")
    return None


def get_positions():
    for attempt in range(MAX_RETRIES):
        try:
            client = _get_trading_client()
            return client.get_all_positions()
        except Exception as e:
            logger.warning(f"get_positions attempt {attempt+1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
    logger.error("get_positions failed after all retries")
    return []


def get_open_orders():
    for attempt in range(MAX_RETRIES):
        try:
            client = _get_trading_client()
            from alpaca.trading.requests import GetOrdersRequest
            from alpaca.trading.enums import QueryOrderStatus
            req = GetOrdersRequest(status=QueryOrderStatus.OPEN)
            return client.get_orders(req)
        except Exception as e:
            logger.warning(f"get_open_orders attempt {attempt+1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
    return []


def get_latest_price(symbol: str) -> float | None:
    for attempt in range(MAX_RETRIES):
        try:
            client = _get_data_client()
            req = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quote = client.get_stock_latest_quote(req)
            if symbol in quote:
                q = quote[symbol]
                return float(q.ask_price or q.bid_price or 0)
        except Exception as e:
            logger.warning(f"get_latest_price({symbol}) attempt {attempt+1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
    return None


def place_bracket_order(symbol: str, action: str, qty: float,
                         take_profit_price: float, stop_loss_price: float):
    side = OrderSide.BUY if action.upper() == "BUY" else OrderSide.SELL
    for attempt in range(MAX_RETRIES):
        try:
            client = _get_trading_client()
            req = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=side,
                time_in_force=TimeInForce.DAY,
                order_class="bracket",
                take_profit=TakeProfitRequest(limit_price=round(take_profit_price, 2)),
                stop_loss=StopLossRequest(stop_price=round(stop_loss_price, 2)),
            )
            order = client.submit_order(req)
            logger.info(f"Bracket order placed: {symbol} {action} qty={qty} TP={take_profit_price:.2f} SL={stop_loss_price:.2f} id={order.id}")
            return order
        except Exception as e:
            logger.warning(f"place_bracket_order attempt {attempt+1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
    logger.error(f"place_bracket_order({symbol}) failed after all retries")
    return None


def close_position(symbol: str):
    for attempt in range(MAX_RETRIES):
        try:
            client = _get_trading_client()
            result = client.close_position(symbol)
            logger.info(f"Position closed: {symbol}")
            return result
        except Exception as e:
            logger.warning(f"close_position({symbol}) attempt {attempt+1} failed: {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
    logger.error(f"close_position({symbol}) failed after all retries")
    return None


def calculate_qty(entry_price: float) -> float:
    if entry_price <= 0:
        return 1.0
    qty = settings.POSITION_SIZE_USD / entry_price
    return max(1.0, round(qty, 0))


def calculate_tp_sl(action: str, entry: float, daily_atr: float,
                     signal_tp: float, signal_sl: float) -> tuple[float, float]:
    atr_sl = entry - (daily_atr * settings.ATR_STOP_MULTIPLIER) if action.upper() == "BUY" else entry + (daily_atr * settings.ATR_STOP_MULTIPLIER)
    atr_tp = entry + (daily_atr * settings.ATR_TP_MULTIPLIER) if action.upper() == "BUY" else entry - (daily_atr * settings.ATR_TP_MULTIPLIER)
    tp = signal_tp if signal_tp else atr_tp
    sl = signal_sl if signal_sl else atr_sl
    return round(tp, 2), round(sl, 2)
