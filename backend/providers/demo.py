"""
Demo Market Data Provider

Deterministic provider for reliable hackathon demos.
Returns realistic but controlled Indian stock data.

Key features:
- 10 pre-configured NIFTY 50 stocks with realistic prices
- Controlled scenarios: HIGH, MEDIUM, LOW, NORMAL attention
- Slight randomization on each call to simulate market movement
- NIFTY 50 benchmark data included
- Clearly labeled as "demo" source
"""

import random
import math
from datetime import datetime, timezone, timedelta
from models import StockQuote, MarketStatus
from providers.base import MarketDataProvider

# IST timezone
IST = timezone(timedelta(hours=5, minutes=30))

# -------------------------------------------------------------------
# Demo stock universe with baseline prices and controlled scenarios
# -------------------------------------------------------------------
# Each stock has:
#   base_price:  the "previous observation" price (what user last saw)
#   current_pct: how much it's moved since then (controls the demo narrative)
#   avg_volume:  20-day average daily volume
#   vol_mult:    current volume as multiple of average (>1 = unusual)
#   scenario:    the attention scenario this stock demonstrates
# -------------------------------------------------------------------

DEMO_STOCKS = {
    "RELIANCE.NS": {
        "name": "Reliance Industries",
        "base_price": 2850.0,
        "current_pct": 4.2,
        "avg_volume": 8_500_000,
        "vol_mult": 2.4,
        "day_range_pct": 2.5,
        "market_cap": 19_300_000_000_000,
        "high_52w": 3200.0,
        "low_52w": 2200.0,
        "scenario": "HIGH — price surge + volume spike",
    },
    "TCS.NS": {
        "name": "TCS",
        "base_price": 3750.0,
        "current_pct": -2.1,
        "avg_volume": 3_200_000,
        "vol_mult": 1.8,
        "day_range_pct": 2.0,
        "market_cap": 13_500_000_000_000,
        "high_52w": 4250.0,
        "low_52w": 3100.0,
        "scenario": "MEDIUM — moderate drop + elevated volume",
    },
    "INFY.NS": {
        "name": "Infosys",
        "base_price": 1620.0,
        "current_pct": 6.8,
        "avg_volume": 12_000_000,
        "vol_mult": 2.9,
        "day_range_pct": 3.2,
        "market_cap": 7_200_000_000_000,
        "high_52w": 1950.0,
        "low_52w": 1300.0,
        "scenario": "HIGH — strong rally + volume anomaly + outperformance",
    },
    "HDFCBANK.NS": {
        "name": "HDFC Bank",
        "base_price": 1680.0,
        "current_pct": 0.8,
        "avg_volume": 10_000_000,
        "vol_mult": 0.9,
        "day_range_pct": 0.8,
        "market_cap": 12_800_000_000_000,
        "high_52w": 1880.0,
        "low_52w": 1400.0,
        "scenario": "NORMAL — quiet day",
    },
    "ICICIBANK.NS": {
        "name": "ICICI Bank",
        "base_price": 1250.0,
        "current_pct": 1.2,
        "avg_volume": 15_000_000,
        "vol_mult": 1.1,
        "day_range_pct": 1.0,
        "market_cap": 8_700_000_000_000,
        "high_52w": 1400.0,
        "low_52w": 950.0,
        "scenario": "LOW — slight uptrend, nothing unusual",
    },
    "HINDUNILVR.NS": {
        "name": "Hindustan Unilever",
        "base_price": 2480.0,
        "current_pct": -0.3,
        "avg_volume": 2_500_000,
        "vol_mult": 0.7,
        "day_range_pct": 0.5,
        "market_cap": 5_800_000_000_000,
        "high_52w": 2800.0,
        "low_52w": 2100.0,
        "scenario": "NORMAL — very quiet",
    },
    "BHARTIARTL.NS": {
        "name": "Bharti Airtel",
        "base_price": 1520.0,
        "current_pct": 3.1,
        "avg_volume": 6_000_000,
        "vol_mult": 1.6,
        "day_range_pct": 1.8,
        "market_cap": 9_100_000_000_000,
        "high_52w": 1700.0,
        "low_52w": 1100.0,
        "scenario": "MEDIUM — decent move + slightly elevated volume",
    },
    "ITC.NS": {
        "name": "ITC",
        "base_price": 465.0,
        "current_pct": 0.5,
        "avg_volume": 20_000_000,
        "vol_mult": 1.0,
        "day_range_pct": 0.6,
        "market_cap": 5_800_000_000_000,
        "high_52w": 530.0,
        "low_52w": 380.0,
        "scenario": "NORMAL — flat",
    },
    "SBIN.NS": {
        "name": "State Bank of India",
        "base_price": 820.0,
        "current_pct": -3.5,
        "avg_volume": 25_000_000,
        "vol_mult": 2.2,
        "day_range_pct": 2.8,
        "market_cap": 7_300_000_000_000,
        "high_52w": 950.0,
        "low_52w": 600.0,
        "scenario": "HIGH — sharp decline + high volume",
    },
    "WIPRO.NS": {
        "name": "Wipro",
        "base_price": 465.0,
        "current_pct": 1.8,
        "avg_volume": 8_000_000,
        "vol_mult": 1.3,
        "day_range_pct": 1.2,
        "market_cap": 2_400_000_000_000,
        "high_52w": 550.0,
        "low_52w": 380.0,
        "scenario": "LOW — mild uptick",
    },
}

# NIFTY 50 benchmark
NIFTY_DATA = {
    "base_price": 25200.0,
    "current_pct": 0.85,
}


class DemoProvider(MarketDataProvider):
    """
    Deterministic demo provider.
    Returns realistic Indian market data for reliable hackathon demos.
    """

    def __init__(self):
        # Small jitter seed so demo data slightly varies per session
        # but remains internally consistent within one session
        self._session_seed = random.randint(0, 1000)
        self._jitter_cache: dict[str, float] = {}

    @property
    def source_name(self) -> str:
        return "demo"

    def get_market_status(self) -> MarketStatus:
        """Demo always reports market as open for easy demoing."""
        return MarketStatus.OPEN

    def _get_jitter(self, symbol: str) -> float:
        """
        Get a small consistent jitter for a symbol (±0.3%).
        Same jitter within a session, different across sessions.
        """
        if symbol not in self._jitter_cache:
            r = random.Random(hash(symbol) + self._session_seed)
            self._jitter_cache[symbol] = r.uniform(-0.3, 0.3)
        return self._jitter_cache[symbol]

    def _build_quote(self, symbol: str, stock: dict) -> StockQuote:
        """Build a StockQuote from demo stock configuration."""
        jitter = self._get_jitter(symbol)
        change_pct = stock["current_pct"] + jitter
        base_price = stock["base_price"]
        current_price = round(base_price * (1 + change_pct / 100), 2)

        # Calculate realistic OHLC
        day_range = stock["day_range_pct"] / 100
        prev_close = round(base_price * (1 + (change_pct - stock["day_range_pct"] * 0.3) / 100), 2)
        open_price = round(prev_close * (1 + random.Random(hash(symbol)).uniform(-0.005, 0.005)), 2)
        day_high = round(max(current_price, open_price) * (1 + day_range * 0.3), 2)
        day_low = round(min(current_price, open_price) * (1 - day_range * 0.3), 2)

        # Volume
        avg_vol = stock["avg_volume"]
        current_vol = int(avg_vol * stock["vol_mult"])

        # NIFTY context
        nifty_jitter = self._get_jitter("^NSEI")
        nifty_pct = NIFTY_DATA["current_pct"] + nifty_jitter

        now = datetime.now(IST)

        return StockQuote(
            symbol=symbol,
            display_name=stock["name"],
            price=current_price,
            open_price=open_price,
            previous_close=prev_close,
            day_high=day_high,
            day_low=day_low,
            volume=current_vol,
            avg_volume=avg_vol,
            market_cap=stock.get("market_cap"),
            fifty_two_week_high=stock.get("high_52w"),
            fifty_two_week_low=stock.get("low_52w"),
            timestamp=now.isoformat(),
            source=self.source_name,
            market_status=self.get_market_status(),
        )

    async def get_quote(self, symbol: str) -> StockQuote | None:
        """Get a demo quote for a symbol."""
        # Handle NIFTY benchmark
        if symbol == "^NSEI":
            return self._build_nifty_quote()

        stock = DEMO_STOCKS.get(symbol)
        if stock is None:
            return None

        return self._build_quote(symbol, stock)

    async def get_batch_quotes(self, symbols: list[str]) -> dict[str, StockQuote]:
        """Get demo quotes for multiple symbols."""
        results = {}
        for symbol in symbols:
            quote = await self.get_quote(symbol)
            if quote:
                results[symbol] = quote
        return results

    async def search(self, query: str) -> list[dict]:
        """Search demo stocks by name or symbol."""
        query_lower = query.lower()
        results = []

        for symbol, stock in DEMO_STOCKS.items():
            name_lower = stock["name"].lower()
            symbol_lower = symbol.lower().replace(".ns", "")

            if query_lower in name_lower or query_lower in symbol_lower:
                results.append({
                    "symbol": symbol,
                    "name": stock["name"],
                    "exchange": "NSE",
                    "type": "EQUITY",
                })

        return results

    async def get_benchmark(self) -> StockQuote | None:
        """Get NIFTY 50 demo data."""
        return self._build_nifty_quote()

    def _build_nifty_quote(self) -> StockQuote:
        """Build a NIFTY 50 index quote."""
        jitter = self._get_jitter("^NSEI")
        change_pct = NIFTY_DATA["current_pct"] + jitter
        base = NIFTY_DATA["base_price"]
        current = round(base * (1 + change_pct / 100), 2)
        prev_close = base

        now = datetime.now(IST)

        return StockQuote(
            symbol="^NSEI",
            display_name="NIFTY 50",
            price=current,
            previous_close=prev_close,
            open_price=round(base * 1.002, 2),
            day_high=round(current * 1.003, 2),
            day_low=round(base * 0.998, 2),
            timestamp=now.isoformat(),
            source="demo",
            market_status=MarketStatus.OPEN,
        )


def get_demo_baseline_price(symbol: str) -> float | None:
    """
    Get the baseline price for a demo stock.
    Used by the watchlist service to create initial baselines in demo mode.
    """
    stock = DEMO_STOCKS.get(symbol)
    if stock:
        return stock["base_price"]
    return None
