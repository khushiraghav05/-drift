# Implementation Plan — SignalLens

## Milestone Overview

| # | Milestone | Files | Priority |
|---|---|---|---|
| 1 | Project Foundation | config, deps, main.py, database | Critical |
| 2 | Market Data Providers | provider ABC, yahoo, demo | Critical |
| 3 | Database & Watchlist Service | models, CRUD, snapshots | Critical |
| 4 | Change Engine | scoring, signals, explanations | Critical |
| 5 | REST API | all routes | Critical |
| 6 | Frontend Foundation | HTML, CSS design system | Critical |
| 7 | Dashboard & Attention Queue | dashboard.js, attention.js | Critical |
| 8 | Stock Detail & Watchlist View | stockDetail.js, watchlist.js | Important |
| 9 | Data Freshness & Error States | freshness indicators, error UI | Important |
| 10 | Demo Provider Scenarios | realistic demo data | Important |
| 11 | Testing | unit + API tests | Important |
| 12 | Polish & Documentation | README, final review | Important |

---

## Milestone 1: Project Foundation

### Backend Setup
- `backend/requirements.txt` — fastapi, uvicorn, aiosqlite, yfinance, httpx, python-dotenv
- `backend/config.py` — Settings class reading from env: MARKET_PROVIDER, DB_PATH, CORS_ORIGIN, LOG_LEVEL
- `backend/database.py` — async SQLite connection, schema creation on startup
- `backend/main.py` — FastAPI app, CORS middleware, lifespan handler for DB init
- `.env.example` — template env file
- `.gitignore` — .env, *.db, __pycache__, node_modules

### Frontend Setup
- `frontend/index.html` — SPA shell with sections
- `frontend/css/styles.css` — Complete design system (dark theme, typography, spacing, components)
- `frontend/js/app.js` — SPA routing, init
- `frontend/js/api.js` — API client with error handling

---

## Milestone 2: Market Data Providers

- `backend/providers/base.py` — `MarketDataProvider` ABC with `get_quote()`, `get_batch_quotes()`, `search()`, `get_benchmark()`
- `backend/providers/yahoo.py` — Yahoo Finance implementation using `yfinance`. Handles .NS suffix for Indian stocks. Includes error handling, timeouts, missing-data fallbacks.
- `backend/providers/demo.py` — Deterministic demo provider with realistic NIFTY 50 stock data. Each call returns slightly randomized-but-controlled data to simulate market movement.
- `backend/services/market.py` — Market data service wrapping providers: in-memory TTL cache, provider fallback, batch fetching, benchmark (NIFTY 50) tracking.

---

## Milestone 3: Database & Watchlist Service

- `backend/models.py` — Pydantic models: StockQuote, Snapshot, Baseline, WatchlistItem, ChangeAssessment, MarketStatus, DataMeta
- `backend/services/watchlist.py` — Watchlist CRUD: add (with duplicate check + validation), remove, list, snapshot storage, baseline management

---

## Milestone 4: Change Engine

- `backend/services/change_engine.py` — Pure function module:
  - `compute_signal(signal_type, raw_value, config)` → individual signal score (0-100)
  - `assess_change(baseline_snapshot, current_snapshot, market_context)` → ChangeAssessment
  - `generate_explanation(assessment)` → human-readable explanation text
  - Signal configs with documented thresholds
  - Handles missing data gracefully

---

## Milestone 5: REST API

- `backend/routes/watchlist.py` — GET/POST/DELETE /api/watchlist
- `backend/routes/market.py` — GET /api/stock/{symbol}, GET /api/market/status, GET /api/search
- `backend/routes/review.py` — POST /api/review, POST /api/review/{symbol}
- Input validation via Pydantic
- Proper HTTP status codes
- Error responses in consistent format

---

## Milestone 6: Frontend Foundation

- Complete CSS with:
  - Dark theme variables
  - Typography scale (Inter)
  - Card, badge, button, input, modal components
  - Attention level color coding
  - Responsive breakpoints
  - Loading skeleton animations
  - Status dot indicators
- HTML structure: market bar, attention section, watchlist section, modals
- JS utilities: formatters (currency ₹, %, dates), DOM helpers

---

## Milestone 7: Dashboard & Attention Queue

- `frontend/js/components/dashboard.js` — Main view orchestrator, data loading, refresh
- `frontend/js/components/attention.js` — Attention queue cards with score, signals, summary
- `frontend/js/components/marketBar.js` — NIFTY status, market open/closed, data freshness
- Sorting: attention queue sorted by score DESC, watchlist table below

---

## Milestone 8: Stock Detail & Watchlist View

- `frontend/js/components/stockDetail.js` — Modal with: current vs baseline comparison, signal breakdown bars, explanation card, "Mark as reviewed" action
- `frontend/js/components/watchlist.js` — Table with columns: stock, price, change%, attention badge, freshness dot
- `frontend/js/components/addStock.js` — Search modal with debounced search, stock suggestions, add button

---

## Milestone 9: Data Freshness & Error States

- Freshness dots on every data point
- "Data delayed" banners when stale
- Empty state for empty watchlist (welcome message)
- Loading skeletons during data fetch
- Error toasts for API failures
- Offline/degraded mode messaging

---

## Milestone 10: Demo Provider Polish

- 8-10 hardcoded stocks with realistic baseline data
- Simulate baselines at different "previous" prices
- One stock with HIGH attention scenario (INFY: price surge + volume anomaly + outperformance)
- One with MEDIUM (TCS: moderate drop + volatility increase)
- Rest at LOW/NORMAL
- Demo badge displayed prominently

---

## Milestone 11: Testing

### Test files:
- `backend/tests/test_change_engine.py` — Unit tests for all signals, edge cases, missing data
- `backend/tests/test_watchlist.py` — Watchlist CRUD, duplicate detection, baseline management
- `backend/tests/test_providers.py` — Demo provider output validation

### Edge case tests:
- First-ever stock observation (no baseline)
- Duplicate stock addition (expect 409)
- Invalid ticker (expect 404)
- Missing volume data
- Stale market data detection
- Empty watchlist
- Extreme price movement (>50%)
- Zero/negative prices
- All signals missing (score should be 0)
- Market closed scenario

---

## Milestone 12: Polish & Documentation

- `README.md` — Full documentation per spec
- Remove console.logs, dead code, TODOs
- Verify production build
- Final diff review

---

## Verification Plan

### Automated Tests
```bash
# Run from project root
cd backend
pip install -r requirements.txt
python -m pytest tests/ -v
```

### Manual API Testing
```bash
# Start backend
cd backend && uvicorn main:app --reload --port 8000

# Test endpoints
curl http://localhost:8000/api/market/status
curl http://localhost:8000/api/search?q=reliance
curl -X POST http://localhost:8000/api/watchlist -H "Content-Type: application/json" -d '{"symbol":"RELIANCE.NS"}'
curl http://localhost:8000/api/watchlist
curl http://localhost:8000/api/stock/RELIANCE.NS
curl -X POST http://localhost:8000/api/review -H "Content-Type: application/json" -d '{"symbols":["RELIANCE.NS"]}'
curl -X DELETE http://localhost:8000/api/watchlist/RELIANCE.NS
```

### Browser Testing
1. Open `http://localhost:8000` (frontend served by FastAPI)
2. Verify empty state shows welcome message
3. Add 3-4 stocks via search
4. Verify attention queue appears with scored cards
5. Click a stock → verify detail modal with signal breakdown
6. Click "Mark as reviewed" → verify baseline reset
7. Verify market status bar shows freshness
8. Test with MARKET_PROVIDER=demo for reliable demo flow
