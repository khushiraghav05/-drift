"""
Market Data Provider — Abstract Base Class

All market data providers implement this interface.
The application never talks to Yahoo Finance, demo, or any
other provider directly — it goes through a MarketDataProvider.
"""

from abc import ABC, abstractmethod
from models import StockQuote, MarketStatus


class MarketDataProvider(ABC):
    """Abstract interface for market data sources."""

    @abstractmethod
    async def get_quote(self, symbol: str) -> StockQuote | None:
        """
        Get a single stock quote.
        Returns None if the symbol is not found or data is unavailable.
        """
        pass

    @abstractmethod
    async def get_batch_quotes(self, symbols: list[str]) -> dict[str, StockQuote]:
        """
        Get quotes for multiple symbols at once.
        Returns a dict mapping symbol -> StockQuote.
        Missing symbols are omitted from the result.
        """
        pass

    @abstractmethod
    async def search(self, query: str) -> list[dict]:
        """
        Search for stocks by name or symbol.
        Returns a list of dicts with keys: symbol, name, exchange, type.
        """
        pass

    @abstractmethod
    async def get_benchmark(self) -> StockQuote | None:
        """
        Get the benchmark index data (NIFTY 50).
        Returns None if unavailable.
        """
        pass

    @abstractmethod
    def get_market_status(self) -> MarketStatus:
        """
        Get current market status (open/closed).
        """
        pass

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of this provider for data attribution."""
        pass
