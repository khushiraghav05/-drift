"""
Yahoo Finance Market Data Provider

Fetches real market data for Indian stocks (NSE) using the yfinance library.
Handles timeouts, missing data, and malformed responses gracefully.
"""

import yfinance as yf
import logging
from datetime import datetime, timezone
from models import StockQuote, MarketStatus
from providers.base import MarketDataProvider

logger = logging.getLogger(__name__)

# NIFTY 50 index symbol on Yahoo Finance
NIFTY_SYMBOL = "^NSEI"

# Indian market hours (IST): 9:15 AM to 3:30 PM, Mon-Fri
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30


class YahooFinanceProvider(MarketDataProvider):
    """Yahoo Finance implementation for Indian NSE stocks."""

    @property
    def source_name(self) -> str:
        return "yahoo_finance"

    def get_market_status(self) -> MarketStatus:
        """Determine if Indian stock market is currently open."""
        try:
            from datetime import timezone, timedelta
            ist = timezone(timedelta(hours=5, minutes=30))
            now = datetime.now(ist)

            # Weekend check
            if now.weekday() >= 5:
                return MarketStatus.CLOSED

            market_open = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0)
            market_close = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0)

            if now < market_open:
                return MarketStatus.PRE_MARKET
            elif now > market_close:
                return MarketStatus.POST_MARKET
            else:
                return MarketStatus.OPEN
        except Exception:
            return MarketStatus.UNKNOWN

    async def get_quote(self, symbol: str) -> StockQuote | None:
        """Fetch a single stock quote from Yahoo Finance."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            if not info or info.get("regularMarketPrice") is None:
                # Try fast_info as fallback
                try:
                    fast = ticker.fast_info
                    if hasattr(fast, "last_price") and fast.last_price:
                        return StockQuote(
                            symbol=symbol,
                            display_name=info.get("shortName", info.get("longName", symbol.replace(".NS", ""))),
                            price=float(fast.last_price),
                            previous_close=float(fast.previous_close) if hasattr(fast, "previous_close") else None,
                            volume=int(fast.last_volume) if hasattr(fast, "last_volume") else None,
                            market_cap=float(fast.market_cap) if hasattr(fast, "market_cap") else None,
                            fifty_two_week_high=float(fast.year_high) if hasattr(fast, "year_high") else None,
                            fifty_two_week_low=float(fast.year_low) if hasattr(fast, "year_low") else None,
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            source=self.source_name,
                            market_status=self.get_market_status(),
                        )
                except Exception:
                    pass
                logger.warning(f"No data found for symbol: {symbol}")
                return None

            return StockQuote(
                symbol=symbol,
                display_name=info.get("shortName", info.get("longName", symbol.replace(".NS", ""))),
                price=_safe_float(info.get("regularMarketPrice") or info.get("currentPrice")),
                open_price=_safe_float(info.get("regularMarketOpen") or info.get("open")),
                previous_close=_safe_float(info.get("regularMarketPreviousClose") or info.get("previousClose")),
                day_high=_safe_float(info.get("regularMarketDayHigh") or info.get("dayHigh")),
                day_low=_safe_float(info.get("regularMarketDayLow") or info.get("dayLow")),
                volume=_safe_int(info.get("regularMarketVolume") or info.get("volume")),
                avg_volume=_safe_int(info.get("averageDailyVolume10Day") or info.get("averageVolume")),
                market_cap=_safe_float(info.get("marketCap")),
                fifty_two_week_high=_safe_float(info.get("fiftyTwoWeekHigh")),
                fifty_two_week_low=_safe_float(info.get("fiftyTwoWeekLow")),
                timestamp=datetime.now(timezone.utc).isoformat(),
                source=self.source_name,
                market_status=self.get_market_status(),
            )

        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")
            return None

    async def get_batch_quotes(self, symbols: list[str]) -> dict[str, StockQuote]:
        """Fetch quotes for multiple symbols."""
        results = {}
        # yfinance doesn't have great async batch support, so we iterate
        # but use the Tickers object for slight efficiency
        try:
            if not symbols:
                return results

            tickers = yf.Tickers(" ".join(symbols))
            for symbol in symbols:
                try:
                    ticker = tickers.tickers.get(symbol)
                    if ticker is None:
                        continue
                    info = ticker.info
                    if not info or not info.get("regularMarketPrice"):
                        continue

                    results[symbol] = StockQuote(
                        symbol=symbol,
                        display_name=info.get("shortName", info.get("longName", symbol.replace(".NS", ""))),
                        price=_safe_float(info.get("regularMarketPrice") or info.get("currentPrice")),
                        open_price=_safe_float(info.get("regularMarketOpen") or info.get("open")),
                        previous_close=_safe_float(info.get("regularMarketPreviousClose") or info.get("previousClose")),
                        day_high=_safe_float(info.get("regularMarketDayHigh") or info.get("dayHigh")),
                        day_low=_safe_float(info.get("regularMarketDayLow") or info.get("dayLow")),
                        volume=_safe_int(info.get("regularMarketVolume") or info.get("volume")),
                        avg_volume=_safe_int(info.get("averageDailyVolume10Day") or info.get("averageVolume")),
                        market_cap=_safe_float(info.get("marketCap")),
                        fifty_two_week_high=_safe_float(info.get("fiftyTwoWeekHigh")),
                        fifty_two_week_low=_safe_float(info.get("fiftyTwoWeekLow")),
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        source=self.source_name,
                        market_status=self.get_market_status(),
                    )
                except Exception as e:
                    logger.error(f"Error fetching {symbol} in batch: {e}")
                    continue

        except Exception as e:
            logger.error(f"Batch quote fetch failed: {e}")

        return results

    async def search(self, query: str) -> list[dict]:
        """Search for stocks by name or symbol."""
        try:
            # yfinance search
            results = []
            search_results = yf.Ticker(query)

            # Try a broader search approach
            import urllib.parse
            import httpx

            url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(query)}&quotesCount=10&newsCount=0&listsCount=0"
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    data = resp.json()
                    for quote in data.get("quotes", []):
                        # Filter for Indian NSE stocks primarily
                        symbol = quote.get("symbol", "")
                        exchange = quote.get("exchange", "")
                        results.append({
                            "symbol": symbol,
                            "name": quote.get("shortname", quote.get("longname", symbol)),
                            "exchange": exchange,
                            "type": quote.get("quoteType", ""),
                        })

            return results[:10]

        except Exception as e:
            logger.error(f"Search failed for query '{query}': {e}")
            return []

    async def get_benchmark(self) -> StockQuote | None:
        """Get NIFTY 50 index data."""
        return await self.get_quote(NIFTY_SYMBOL)


def _safe_float(value) -> float | None:
    """Safely convert a value to float, returning None for invalid/missing data."""
    if value is None:
        return None
    try:
        result = float(value)
        if result != result:  # NaN check
            return None
        return result
    except (ValueError, TypeError):
        return None


def _safe_int(value) -> int | None:
    """Safely convert a value to int, returning None for invalid/missing data."""
    if value is None:
        return None
    try:
        result = int(float(value))
        if result < 0:
            return None
        return result
    except (ValueError, TypeError):
        return None
