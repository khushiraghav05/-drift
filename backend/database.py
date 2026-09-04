"""
SignalLens Database Layer
Async SQLite connection and schema management.
"""

import aiosqlite
import os
import logging

from config import settings

logger = logging.getLogger(__name__)

# Resolve DB path relative to backend directory
DB_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), settings.DB_PATH))

SCHEMA_SQL = """
-- User watchlist items
CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'default',
    symbol TEXT NOT NULL,
    display_name TEXT NOT NULL,
    added_at TEXT NOT NULL,
    UNIQUE(user_id, symbol)
);

-- Market data snapshots (point-in-time captures)
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    price REAL,
    open_price REAL,
    previous_close REAL,
    day_high REAL,
    day_low REAL,
    volume INTEGER,
    avg_volume INTEGER,
    market_cap REAL,
    fifty_two_week_high REAL,
    fifty_two_week_low REAL,
    timestamp TEXT NOT NULL,
    source TEXT NOT NULL,
    market_status TEXT,
    nifty_price REAL,
    nifty_change_pct REAL,
    created_at TEXT NOT NULL
);

-- User observation baselines
CREATE TABLE IF NOT EXISTS baselines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'default',
    symbol TEXT NOT NULL,
    snapshot_id INTEGER NOT NULL,
    state TEXT NOT NULL DEFAULT 'new',
    created_at TEXT NOT NULL,
    reviewed_at TEXT,
    UNIQUE(user_id, symbol),
    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_snapshots_symbol ON snapshots(symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_baselines_user ON baselines(user_id, symbol);
CREATE INDEX IF NOT EXISTS idx_watchlist_user ON watchlist(user_id);
"""


async def get_db() -> aiosqlite.Connection:
    """Get a database connection."""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db():
    """Initialize the database schema."""
    logger.info(f"Initializing database at {DB_PATH}")
    db = await get_db()
    try:
        await db.executescript(SCHEMA_SQL)
        await db.commit()
        logger.info("Database schema initialized successfully")
    finally:
        await db.close()


async def close_db(db: aiosqlite.Connection):
    """Close a database connection."""
    await db.close()
