"""
Market Data Service

Wraps the market data provider with:
- In-memory TTL caching
- Provider fallback (returns cached data if provider fails)
- Benchmark (NIFTY 50) tracking
- Data freshness metadata
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from models import StockQuote, DataMeta, Freshness, MarketStatus
from providers.base import MarketDataProvider
from config import settings

logger = logging.getLogger(__name__)


class CacheEntry:
    """A cached value with expiry."""
    __slots__ = ("value", "expires_at", "fetched_at")

    def __init__(self, value, ttl: int):
        self.value = value
        self.fetched_at = time.time()
        self.expires_at = self.fetched_at + ttl

    @property
    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    @property
    def age_seconds(self) -> int:
        return int(time.time() - self.fetched_at)


class MarketService:
    """High-level market data service with caching and metadata."""

    def __init__(self, provider: MarketDataProvider):
        self.provider = provider
        self._cache: dict[str, CacheEntry] = {}
        self._benchmark_cache: CacheEntry | None = None

    def _get_ttl(self) -> int:
        """Get cache TTL based on market status."""
        status = self.provider.get_market_status()
        if status == MarketStatus.OPEN:
            return settings.CACHE_TTL_LIVE
        return settings.CACHE_TTL_CLOSED

    def _get_freshness(self, age_seconds: int) -> Freshness:
        """Determine data freshness from age."""
        if self.provider.source_name == "demo":
            return Freshness.DEMO
        if age_seconds < settings.FRESHNESS_LIVE:
            return Freshness.LIVE
        elif age_seconds < settings.FRESHNESS_DELAYED:
            return Freshness.DELAYED
        elif age_seconds < settings.FRESHNESS_CACHED:
            return Freshness.CACHED
        else:
            return Freshness.STALE

    def build_data_meta(self, quote: StockQuote | None, age_seconds: int = 0) -> DataMeta:
        """Build data metadata for a quote."""
        return DataMeta(
            timestamp=quote.timestamp if quote else datetime.now(timezone.utc).isoformat(),
            source=quote.source if quote else self.provider.source_name,
            freshness=self._get_freshness(age_seconds),
            market_status=quote.market_status if quote else self.provider.get_market_status(),
            age_seconds=age_seconds,
        )

    async def get_quote(self, symbol: str) -> tuple[StockQuote | None, DataMeta]:
        """
        Get a stock quote with caching and fallback.
        Returns (quote, metadata) — quote may be from cache if provider fails.
        """
        cached = self._cache.get(symbol)

        # Return fresh cache hit
        if cached and not cached.is_expired:
            meta = self.build_data_meta(cached.value, cached.age_seconds)
            return cached.value, meta

        # Try to fetch fresh data
        try:
            quote = await self.provider.get_quote(symbol)
            if quote and quote.price is not None:
                ttl = self._get_ttl()
                self._cache[symbol] = CacheEntry(quote, ttl)
                meta = self.build_data_meta(quote, 0)
                return quote, meta
        except Exception as e:
            logger.error(f"Provider failed for {symbol}: {e}")

        # Fallback to stale cache
        if cached:
            logger.warning(f"Using stale cache for {symbol} (age: {cached.age_seconds}s)")
            meta = self.build_data_meta(cached.value, cached.age_seconds)
            return cached.value, meta

        # No data at all
        meta = self.build_data_meta(None, 0)
        return None, meta

    async def get_batch_quotes(self, symbols: list[str]) -> dict[str, tuple[StockQuote, DataMeta]]:
        """
        Get quotes for multiple symbols efficiently.
        Uses cache where available, fetches remaining from provider.
        """
        results = {}
        to_fetch = []

        # Check cache first
        for symbol in symbols:
            cached = self._cache.get(symbol)
            if cached and not cached.is_expired:
                meta = self.build_data_meta(cached.value, cached.age_seconds)
                results[symbol] = (cached.value, meta)
            else:
                to_fetch.append(symbol)

        # Fetch uncached symbols
        if to_fetch:
            try:
                quotes = await self.provider.get_batch_quotes(to_fetch)
                ttl = self._get_ttl()
                for symbol, quote in quotes.items():
                    if quote and quote.price is not None:
                        self._cache[symbol] = CacheEntry(quote, ttl)
                        meta = self.build_data_meta(quote, 0)
                        results[symbol] = (quote, meta)
            except Exception as e:
                logger.error(f"Batch fetch failed: {e}")

            # Fallback: use stale cache for any still-missing symbols
            for symbol in to_fetch:
                if symbol not in results:
                    cached = self._cache.get(symbol)
                    if cached:
                        meta = self.build_data_meta(cached.value, cached.age_seconds)
                        results[symbol] = (cached.value, meta)

        return results

    async def get_benchmark(self) -> tuple[StockQuote | None, DataMeta]:
        """Get NIFTY 50 benchmark data with caching."""
        if self._benchmark_cache and not self._benchmark_cache.is_expired:
            meta = self.build_data_meta(self._benchmark_cache.value, self._benchmark_cache.age_seconds)
            return self._benchmark_cache.value, meta

        try:
            quote = await self.provider.get_benchmark()
            if quote and quote.price is not None:
                ttl = self._get_ttl()
                self._benchmark_cache = CacheEntry(quote, ttl)
                meta = self.build_data_meta(quote, 0)
                return quote, meta
        except Exception as e:
            logger.error(f"Benchmark fetch failed: {e}")

        if self._benchmark_cache:
            meta = self.build_data_meta(self._benchmark_cache.value, self._benchmark_cache.age_seconds)
            return self._benchmark_cache.value, meta

        meta = self.build_data_meta(None, 0)
        return None, meta

    async def search(self, query: str) -> list[dict]:
        """Search for stocks."""
        try:
            return await self.provider.search(query)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
