# Architecture — SignalLens

## System Overview

```
┌──────────────────────────────────────────────────────┐
│                    Frontend (Vanilla JS)              │
│  Dashboard │ Watchlist │ Stock Detail │ Add Stock     │
└─────────────────────┬────────────────────────────────┘
                      │ REST API (JSON)
┌─────────────────────▼────────────────────────────────┐
│                FastAPI Backend                        │
│                                                      │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Watchlist │  │  Change      │  │ Market Data   │  │
│  │ Service   │  │  Engine      │  │ Service       │  │
│  └────┬─────┘  └──────┬───────┘  └───────┬───────┘  │
│       │               │                  │           │
│  ┌────▼───────────────▼──────────────────▼───────┐   │
│  │              Data Access Layer                │   │
│  └────────────────────┬──────────────────────────┘   │
└───────────────────────┬──────────────────────────────┘
                        │
              ┌─────────▼──────────┐
              │   SQLite Database   │
              └────────────────────┘

Market Data Service
       │
       ├── YahooFinanceProvider (live)
       └── DemoProvider (deterministic)
```

## Backend Architecture

### Directory Structure
```
backend/
├── main.py                 # FastAPI app, CORS, startup
├── config.py               # Settings, env vars
├── database.py             # SQLite connection, schema init
├── models.py               # Pydantic models (request/response)
├── providers/
│   ├── base.py             # MarketDataProvider ABC
│   ├── yahoo.py            # Yahoo Finance implementation
│   └── demo.py             # Deterministic demo provider
├── services/
│   ├── market.py           # Market data service (caching, fallback)
│   ├── watchlist.py        # Watchlist CRUD operations
│   └── change_engine.py    # Meaningful change detection
├── routes/
│   ├── watchlist.py        # Watchlist endpoints
│   ├── market.py           # Market data endpoints
│   └── review.py           # Review/acknowledge endpoints
└── tests/
    ├── test_change_engine.py
    ├── test_watchlist.py
    └── test_providers.py
```

### Key Design Decisions

1. **Provider Abstraction**: `MarketDataProvider` ABC with `get_quote()`, `get_batch_quotes()`, `search()`. Implementations for Yahoo Finance and Demo. The market service wraps the provider with caching and fallback logic.

2. **Change Engine as Pure Function**: The change engine takes (baseline_snapshot, current_snapshot, market_context) and returns a ChangeAssessment. No side effects. Fully testable.

3. **Single Database File**: `signallens.db` in the project root. Created on first startup via schema migration in `database.py`.

4. **In-Memory Cache**: Simple dict-based cache with TTL for market data. No Redis needed for hackathon scale.

## Database Schema

```sql
-- The user's watchlist items
CREATE TABLE watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'default',
    symbol TEXT NOT NULL,             -- e.g. "RELIANCE.NS"
    display_name TEXT NOT NULL,       -- e.g. "Reliance Industries"
    added_at TEXT NOT NULL,           -- ISO 8601
    UNIQUE(user_id, symbol)
);

-- Market snapshots (point-in-time captures)
CREATE TABLE snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    price REAL,
    open_price REAL,
    previous_close REAL,
    day_high REAL,
    day_low REAL,
    volume INTEGER,
    avg_volume INTEGER,              -- 20-day average
    market_cap REAL,
    fifty_two_week_high REAL,
    fifty_two_week_low REAL,
    timestamp TEXT NOT NULL,          -- ISO 8601
    source TEXT NOT NULL,             -- "yahoo_finance" | "demo"
    market_status TEXT,               -- "open" | "closed"
    nifty_price REAL,                -- Benchmark at same timestamp
    nifty_change_pct REAL,           -- Benchmark % change
    created_at TEXT NOT NULL
);

-- User's observation baselines
CREATE TABLE baselines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL DEFAULT 'default',
    symbol TEXT NOT NULL,
    snapshot_id INTEGER NOT NULL,     -- References the snapshot that was baseline
    state TEXT NOT NULL DEFAULT 'new', -- new | observing | changed | reviewed
    created_at TEXT NOT NULL,
    reviewed_at TEXT,
    UNIQUE(user_id, symbol),
    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
);

-- Indexes
CREATE INDEX idx_snapshots_symbol ON snapshots(symbol, created_at DESC);
CREATE INDEX idx_baselines_user ON baselines(user_id, symbol);
CREATE INDEX idx_watchlist_user ON watchlist(user_id);
```

### Schema Rationale
- **watchlist**: Simple join table. UNIQUE constraint prevents duplicates.
- **snapshots**: Immutable market data captures. Latest is found by `ORDER BY created_at DESC LIMIT 1`. Historical snapshots support future change timeline features.
- **baselines**: Tracks what the user last saw. References a specific snapshot. State machine: new → observing → changed → reviewed → observing.
- **Benchmark data on snapshots**: NIFTY price/change stored alongside each snapshot to avoid separate lookups for relative comparison.

## Frontend Architecture

### Directory Structure
```
frontend/
├── index.html              # Single page
├── css/
│   └── styles.css          # Complete stylesheet
├── js/
│   ├── app.js              # App initialization, routing
│   ├── api.js              # Backend API client
│   ├── components/
│   │   ├── dashboard.js    # Dashboard view
│   │   ├── watchlist.js    # Watchlist table
│   │   ├── attention.js    # Attention queue cards
│   │   ├── stockDetail.js  # Stock detail modal
│   │   ├── addStock.js     # Add stock modal
│   │   ├── marketBar.js    # Market status bar
│   │   └── freshness.js    # Data freshness indicators
│   └── utils/
│       ├── formatters.js   # Number/currency/date formatting
│       └── dom.js          # DOM helper utilities
└── assets/
    └── logo.svg            # SignalLens logo
```

### Design System
- **Colors**: Dark theme (financial product convention). Key palette:
  - Background: `#0a0e17` (dark navy)
  - Surface: `#111827` / `#1f2937`
  - Text: `#f9fafb` / `#9ca3af`
  - Positive: `#10b981` (green)
  - Negative: `#ef4444` (red)
  - Attention High: `#f59e0b` (amber)
  - Attention Medium: `#6366f1` (indigo)
  - Accent: `#3b82f6` (blue)
- **Typography**: Inter (Google Fonts) — clean fintech look
- **Spacing**: 4px base unit, consistent rhythm
- **Borders**: 1px `#1f2937`, rounded 8-12px

## API Contracts

### GET /api/watchlist
```json
{
  "stocks": [
    {
      "symbol": "RELIANCE.NS",
      "display_name": "Reliance Industries",
      "price": 2970.50,
      "baseline_price": 2850.00,
      "change_pct": 4.23,
      "attention": {
        "score": 82,
        "level": "high",
        "signals": ["price_move", "volume_anomaly", "market_outperformance"],
        "summary": "Price +4.2%, Volume 2.4x normal, Outperforming NIFTY"
      },
      "data_meta": {
        "timestamp": "2026-09-04T15:30:00+05:30",
        "freshness": "live",
        "source": "yahoo_finance",
        "market_status": "open"
      },
      "baseline_state": "changed"
    }
  ],
  "market": {
    "nifty_price": 25450.30,
    "nifty_change_pct": 0.85,
    "market_status": "open",
    "timestamp": "2026-09-04T15:30:00+05:30"
  }
}
```

### POST /api/watchlist
```json
// Request
{ "symbol": "RELIANCE.NS" }

// Response: 201 Created
{ "symbol": "RELIANCE.NS", "display_name": "Reliance Industries", "added": true }

// Response: 409 Conflict
{ "error": "Stock already in watchlist" }

// Response: 404 Not Found
{ "error": "Symbol not found" }
```

### GET /api/stock/{symbol}
```json
{
  "symbol": "RELIANCE.NS",
  "display_name": "Reliance Industries",
  "current": { /* full snapshot */ },
  "baseline": { /* baseline snapshot */ },
  "change": {
    "score": 82,
    "level": "high",
    "signals": {
      "price": { "value": 4.23, "signal_score": 75, "description": "Price moved +4.23% since baseline" },
      "volume": { "value": 2.4, "signal_score": 70, "description": "Volume is 2.4x 20-day average" },
      "volatility": { "value": 0.15, "signal_score": 20, "description": "Slightly elevated" },
      "relative": { "value": 3.38, "signal_score": 90, "description": "Outperforming NIFTY by +3.38%" },
      "gap": { "value": 0.5, "signal_score": 10, "description": "Minor gap" }
    },
    "explanation": "Reliance changed meaningfully since your last check. Price accelerated +4.2% while volume surged to 2.4x normal. This stock is significantly outperforming the broader market.",
    "data_quality": "fresh"
  }
}
```

### POST /api/review
```json
// Request — review all
{ "symbols": ["all"] }
// Request — review specific
{ "symbols": ["RELIANCE.NS", "TCS.NS"] }

// Response
{ "reviewed": 2 }
```

## Caching Strategy

- **Market data**: TTL-based in-memory cache (60s for live, 300s for closed market)
- **Batch fetching**: When loading watchlist, fetch all quotes in one provider call
- **Baseline snapshots**: Loaded from DB once per request, no cache needed (small data)

## Error Handling Strategy

| Scenario | Backend Response | Frontend Display |
|---|---|---|
| Provider timeout | Return cached data + stale flag | Show data with "Delayed" badge |
| Provider down | Return cached data or 503 | Show cached data or "Data unavailable" |
| Invalid symbol | 404 | "Stock not found" message |
| Duplicate add | 409 | "Already in your watchlist" |
| DB error | 500 + log | "Something went wrong" + retry button |
| Empty watchlist | 200 with empty array | Welcome state: "Add your first stock" |
| Malformed provider data | Skip bad fields, use nulls | Show available data, mark missing |

## Security Considerations

- Input validation on all endpoints (Pydantic models)
- SQL parameterization (not string concatenation)
- No secrets in code — env vars via `.env`
- CORS restricted to frontend origin
- No user auth (documented as future work)

## Scalability Notes (Not Implemented, Documented)

| Current | At Scale |
|---|---|
| SQLite | PostgreSQL with read replicas |
| In-memory cache | Redis with pub/sub for cache invalidation |
| Inline snapshot fetching | Background worker + job queue |
| Single process | Multiple workers behind load balancer |
| Per-request change calculation | Pre-computed change scores updated on snapshot arrival |
| Client polling | WebSocket for real-time updates |

## Observability

- Python `logging` module with structured logs
- Request/response logging middleware
- Provider call timing
- Change engine computation timing
- Error tracking with tracebacks
