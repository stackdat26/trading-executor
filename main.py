import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Trading Executor starting up...")
    logger.info("Connect to QuantBot signal source, Alpaca paper trading, and Google Sheets logging.")
    logger.info("Configure your API keys and settings to begin automated trading.")
    logger.info("Trading Executor is ready. Waiting for configuration...")


if __name__ == "__main__":
    main()
