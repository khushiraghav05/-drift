"""
Watchlist Service

Handles:
- Watchlist CRUD (add, remove, list)
- Snapshot storage and retrieval
- Baseline management (state machine: new → observing → changed → reviewed)
- Change assessment orchestration
"""

import logging
from datetime import datetime, timezone

from database import get_db, close_db
from models import (
    Snapshot, AttentionItem, ChangeAssessment, DataMeta,
    BaselineState, Freshness, AttentionLevel,
)
from services.change_engine import assess_change
from services.market import MarketService

logger = logging.getLogger(__name__)


class WatchlistService:
    """Manages the user's watchlist and change detection."""

    def __init__(self, market_service: MarketService):
        self.market = market_service

    async def get_watchlist(self, user_id: str = "default") -> list[AttentionItem]:
        """
        Get the full watchlist with current data and change assessments.
        This is the main dashboard endpoint.
        """
        db = await get_db()
        try:
            # Get all watchlist items
            cursor = await db.execute(
                "SELECT symbol, display_name FROM watchlist WHERE user_id = ? ORDER BY added_at",
                (user_id,)
            )
            rows = await cursor.fetchall()

            if not rows:
                return []

            symbols = [row["symbol"] for row in rows]
            name_map = {row["symbol"]: row["display_name"] for row in rows}

            # Batch fetch current quotes
            quotes = await self.market.get_batch_quotes(symbols)

            # Get benchmark for relative context
            benchmark, bench_meta = await self.market.get_benchmark()
            nifty_price = benchmark.price if benchmark else None
            nifty_change_pct = None
            if benchmark and benchmark.previous_close and benchmark.price:
                nifty_change_pct = round(
                    (benchmark.price - benchmark.previous_close) / benchmark.previous_close * 100, 2
                )

            items = []
            for symbol in symbols:
                display_name = name_map[symbol]

                if symbol not in quotes:
                    # No data available
                    items.append(AttentionItem(
                        symbol=symbol,
                        display_name=display_name,
                        attention=ChangeAssessment(),
                        data_meta=DataMeta(
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            source=self.market.provider.source_name,
                            freshness=Freshness.STALE,
                            age_seconds=0,
                        ),
                        baseline_state=BaselineState.NEW,
                    ))
                    continue

                quote, data_meta = quotes[symbol]

                # Store current snapshot
                snapshot_id = await self._store_snapshot(
                    db, symbol, quote, nifty_price, nifty_change_pct
                )

                # Get or create baseline
                baseline = await self._get_baseline(db, user_id, symbol)

                if baseline is None:
                    # First observation — set current as baseline
                    await self._set_baseline(db, user_id, symbol, snapshot_id, BaselineState.NEW)
                    items.append(AttentionItem(
                        symbol=symbol,
                        display_name=display_name,
                        price=quote.price,
                        baseline_price=quote.price,
                        change_pct=0.0,
                        attention=ChangeAssessment(
                            summary="Just added — this is your baseline",
                            explanation=f"{display_name} was just added to your watchlist. This snapshot is your baseline for future comparisons.",
                        ),
                        data_meta=data_meta,
                        baseline_state=BaselineState.NEW,
                    ))
                else:
                    # Have baseline — compute change
                    current_snapshot = self._quote_to_snapshot(
                        quote, nifty_price, nifty_change_pct
                    )

                    assessment = assess_change(
                        baseline=baseline,
                        current=current_snapshot,
                        data_quality=data_meta.freshness,
                        display_name=display_name,
                    )

                    # Determine baseline state
                    state = await self._get_baseline_state(db, user_id, symbol)
                    if assessment.level != AttentionLevel.NORMAL and state != BaselineState.REVIEWED:
                        state = BaselineState.CHANGED
                        await self._update_baseline_state(db, user_id, symbol, state)
                    elif state == BaselineState.NEW:
                        state = BaselineState.OBSERVING
                        await self._update_baseline_state(db, user_id, symbol, state)

                    change_pct = None
                    if baseline.price and quote.price:
                        change_pct = round(
                            (quote.price - baseline.price) / baseline.price * 100, 2
                        )

                    items.append(AttentionItem(
                        symbol=symbol,
                        display_name=display_name,
                        price=quote.price,
                        baseline_price=baseline.price,
                        change_pct=change_pct,
                        attention=assessment,
                        data_meta=data_meta,
                        baseline_state=state,
                    ))

            await db.commit()
            return items

        finally:
            await close_db(db)

    async def add_stock(self, symbol: str, display_name: str, user_id: str = "default") -> bool:
        """
        Add a stock to the watchlist.
        Returns True if added, raises ValueError if duplicate.
        """
        db = await get_db()
        try:
            # Check for duplicate
            cursor = await db.execute(
                "SELECT id FROM watchlist WHERE user_id = ? AND symbol = ?",
                (user_id, symbol)
            )
            if await cursor.fetchone():
                raise ValueError(f"Stock {symbol} is already in your watchlist")

            now = datetime.now(timezone.utc).isoformat()
            await db.execute(
                "INSERT INTO watchlist (user_id, symbol, display_name, added_at) VALUES (?, ?, ?, ?)",
                (user_id, symbol, display_name, now)
            )
            await db.commit()
            logger.info(f"Added {symbol} to watchlist for user {user_id}")
            return True
        finally:
            await close_db(db)

    async def remove_stock(self, symbol: str, user_id: str = "default") -> bool:
        """Remove a stock from the watchlist. Returns True if found and removed."""
        db = await get_db()
        try:
            cursor = await db.execute(
                "DELETE FROM watchlist WHERE user_id = ? AND symbol = ?",
                (user_id, symbol)
            )
            # Also clean up baseline
            await db.execute(
                "DELETE FROM baselines WHERE user_id = ? AND symbol = ?",
                (user_id, symbol)
            )
            await db.commit()
            removed = cursor.rowcount > 0
            if removed:
                logger.info(f"Removed {symbol} from watchlist for user {user_id}")
            return removed
        finally:
            await close_db(db)

    async def review_stocks(self, symbols: list[str], user_id: str = "default") -> int:
        """
        Mark stocks as reviewed — resets their baseline to the latest snapshot.

        If symbols contains "all", review all stocks in the watchlist.
        Returns the number of stocks reviewed.
        """
        db = await get_db()
        try:
            if "all" in symbols:
                cursor = await db.execute(
                    "SELECT symbol FROM watchlist WHERE user_id = ?", (user_id,)
                )
                rows = await cursor.fetchall()
                symbols = [row["symbol"] for row in rows]

            now = datetime.now(timezone.utc).isoformat()
            count = 0

            for symbol in symbols:
                # Get the latest snapshot for this symbol
                cursor = await db.execute(
                    "SELECT id FROM snapshots WHERE symbol = ? ORDER BY created_at DESC LIMIT 1",
                    (symbol,)
                )
                row = await cursor.fetchone()
                if not row:
                    continue

                snapshot_id = row["id"]

                # Update or create baseline
                await db.execute("""
                    INSERT INTO baselines (user_id, symbol, snapshot_id, state, created_at, reviewed_at)
                    VALUES (?, ?, ?, 'reviewed', ?, ?)
                    ON CONFLICT(user_id, symbol) DO UPDATE SET
                        snapshot_id = ?,
                        state = 'reviewed',
                        reviewed_at = ?
                """, (user_id, symbol, snapshot_id, now, now, snapshot_id, now))
                count += 1

            await db.commit()
            logger.info(f"Reviewed {count} stocks for user {user_id}")
            return count
        finally:
            await close_db(db)

    async def get_stock_detail(self, symbol: str, user_id: str = "default") -> dict | None:
        """Get detailed stock data with full change breakdown."""
        quote, data_meta = await self.market.get_quote(symbol)
        if not quote:
            return None

        benchmark, _ = await self.market.get_benchmark()
        nifty_price = benchmark.price if benchmark else None
        nifty_change_pct = None
        if benchmark and benchmark.previous_close and benchmark.price:
            nifty_change_pct = round(
                (benchmark.price - benchmark.previous_close) / benchmark.previous_close * 100, 2
            )

        db = await get_db()
        try:
            # Store snapshot
            snapshot_id = await self._store_snapshot(db, symbol, quote, nifty_price, nifty_change_pct)

            # Get baseline
            baseline = await self._get_baseline(db, user_id, symbol)

            current_snapshot = self._quote_to_snapshot(quote, nifty_price, nifty_change_pct)

            if baseline is None:
                baseline = current_snapshot  # No baseline yet

            assessment = assess_change(
                baseline=baseline,
                current=current_snapshot,
                data_quality=data_meta.freshness,
                display_name=quote.display_name,
            )

            await db.commit()

            return {
                "symbol": symbol,
                "display_name": quote.display_name,
                "current": current_snapshot.model_dump(),
                "baseline": baseline.model_dump(),
                "change": assessment.model_dump(),
                "data_meta": data_meta.model_dump(),
            }
        finally:
            await close_db(db)

    # --- Internal helpers ---

    async def _store_snapshot(self, db, symbol: str, quote, nifty_price, nifty_change_pct) -> int:
        """Store a market snapshot and return its ID."""
        now = datetime.now(timezone.utc).isoformat()
        cursor = await db.execute("""
            INSERT INTO snapshots (
                symbol, price, open_price, previous_close,
                day_high, day_low, volume, avg_volume,
                market_cap, fifty_two_week_high, fifty_two_week_low,
                timestamp, source, market_status,
                nifty_price, nifty_change_pct, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            symbol, quote.price, quote.open_price, quote.previous_close,
            quote.day_high, quote.day_low, quote.volume, quote.avg_volume,
            quote.market_cap, quote.fifty_two_week_high, quote.fifty_two_week_low,
            quote.timestamp, quote.source, quote.market_status.value if quote.market_status else None,
            nifty_price, nifty_change_pct, now,
        ))
        return cursor.lastrowid

    async def _get_baseline(self, db, user_id: str, symbol: str) -> Snapshot | None:
        """Get the baseline snapshot for a stock."""
        cursor = await db.execute("""
            SELECT s.* FROM baselines b
            JOIN snapshots s ON b.snapshot_id = s.id
            WHERE b.user_id = ? AND b.symbol = ?
        """, (user_id, symbol))
        row = await cursor.fetchone()
        if not row:
            return None

        return Snapshot(
            id=row["id"],
            symbol=row["symbol"],
            price=row["price"],
            open_price=row["open_price"],
            previous_close=row["previous_close"],
            day_high=row["day_high"],
            day_low=row["day_low"],
            volume=row["volume"],
            avg_volume=row["avg_volume"],
            market_cap=row["market_cap"],
            fifty_two_week_high=row["fifty_two_week_high"],
            fifty_two_week_low=row["fifty_two_week_low"],
            timestamp=row["timestamp"],
            source=row["source"],
            market_status=row["market_status"],
            nifty_price=row["nifty_price"],
            nifty_change_pct=row["nifty_change_pct"],
            created_at=row["created_at"],
        )

    async def _set_baseline(self, db, user_id: str, symbol: str, snapshot_id: int, state: BaselineState):
        """Set or update the baseline for a stock."""
        now = datetime.now(timezone.utc).isoformat()
        await db.execute("""
            INSERT INTO baselines (user_id, symbol, snapshot_id, state, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, symbol) DO UPDATE SET
                snapshot_id = ?, state = ?, created_at = ?
        """, (user_id, symbol, snapshot_id, state.value, now, snapshot_id, state.value, now))

    async def _get_baseline_state(self, db, user_id: str, symbol: str) -> BaselineState:
        """Get the current baseline state for a stock."""
        cursor = await db.execute(
            "SELECT state FROM baselines WHERE user_id = ? AND symbol = ?",
            (user_id, symbol)
        )
        row = await cursor.fetchone()
        if not row:
            return BaselineState.NEW
        return BaselineState(row["state"])

    async def _update_baseline_state(self, db, user_id: str, symbol: str, state: BaselineState):
        """Update the baseline state."""
        await db.execute(
            "UPDATE baselines SET state = ? WHERE user_id = ? AND symbol = ?",
            (state.value, user_id, symbol)
        )

    def _quote_to_snapshot(self, quote, nifty_price=None, nifty_change_pct=None) -> Snapshot:
        """Convert a StockQuote to a Snapshot model."""
        return Snapshot(
            symbol=quote.symbol,
            price=quote.price,
            open_price=quote.open_price,
            previous_close=quote.previous_close,
            day_high=quote.day_high,
            day_low=quote.day_low,
            volume=quote.volume,
            avg_volume=quote.avg_volume,
            market_cap=quote.market_cap,
            fifty_two_week_high=quote.fifty_two_week_high,
            fifty_two_week_low=quote.fifty_two_week_low,
            timestamp=quote.timestamp,
            source=quote.source,
            market_status=quote.market_status.value if quote.market_status else None,
            nifty_price=nifty_price,
            nifty_change_pct=nifty_change_pct,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
