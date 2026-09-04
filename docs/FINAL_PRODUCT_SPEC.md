# Final Product Specification — SignalLens

## Product Definition

**SignalLens** is a market watchlist with memory. Instead of just showing current stock prices, it tracks what the user last saw, detects what meaningfully changed, and presents a prioritized attention queue with transparent explanations.

## Core Product Loop

```
CHECK → REMEMBER → DETECT → PRIORITIZE → EXPLAIN → REVIEW
```

1. **CHECK**: User adds stocks to their watchlist
2. **REMEMBER**: System records a "baseline snapshot" — what the user last observed
3. **DETECT**: When the user returns, the system compares current data against the baseline
4. **PRIORITIZE**: Changes are scored and ranked by significance
5. **EXPLAIN**: Each change gets a transparent explanation card
6. **REVIEW**: User can acknowledge changes, resetting the baseline

## Information Architecture

### Page 1: Dashboard (Home)
- **Market Status Bar**: Market open/closed, NIFTY 50 level + change, data freshness
- **Attention Queue**: Top stocks ranked by change significance (card format)
- **Watchlist Table**: All stocks with price, change-since-baseline, attention level

### Page 2: Stock Detail (Modal or Slide-over)
- Current price + baseline comparison
- Change signals breakdown (why this attention level)
- Market context (vs NIFTY)
- Volume / volatility context
- Action: Acknowledge / Dismiss

### Page 3: Add Stock (Modal)
- Search by name or symbol
- Duplicate protection
- Shows current price before adding

## Baseline Model

### When is the baseline captured?
- **Initial**: When a stock is first added to watchlist → first market snapshot becomes baseline
- **Reset**: When user clicks "Mark as reviewed" on a stock or on the entire dashboard
- **Auto-cooldown**: Baseline doesn't reset just because the user loads the page. They must explicitly acknowledge.

### Baseline state machine:
```
NEW → OBSERVING → CHANGED → REVIEWED → OBSERVING
         ↑                      ↓
         └──────────────────────┘
```

- `NEW`: Stock just added, no baseline yet. First snapshot becomes baseline.
- `OBSERVING`: Has a baseline. No meaningful change detected.
- `CHANGED`: Meaningful change detected since baseline. Shows attention card.
- `REVIEWED`: User acknowledged the change. Current snapshot becomes new baseline. Transitions back to OBSERVING.

## Meaningful Change Engine

### Signals (each scored 0-100)

| Signal | What It Measures | Weight | Threshold for signal |
|---|---|---|---|
| **Price Movement** | `abs(price_change_pct)` since baseline | 30% | >1% = starts scoring, >5% = max |
| **Volume Anomaly** | `current_volume / avg_volume_20d` ratio | 25% | >1.5x = starts scoring, >3x = max |
| **Volatility Change** | Change in stock's recent price range relative to baseline period | 15% | Uses ATR or high-low range comparison |
| **Market Relative** | Stock's move minus benchmark (NIFTY) move over same period | 20% | >1.5% divergence = starts scoring |
| **Gap Signal** | Difference between previous close and current open | 10% | >1% gap = starts scoring |

### Composite Score
```
score = (price_signal × 0.30) + (volume_signal × 0.25) + (volatility_signal × 0.15) + (relative_signal × 0.20) + (gap_signal × 0.10)
```

### Attention Levels
| Score Range | Level | Meaning |
|---|---|---|
| 0-20 | **Normal** | No meaningful change |
| 21-45 | **Low** | Minor changes, worth knowing |
| 46-70 | **Medium** | Notable changes, should review |
| 71-100 | **High** | Significant changes, needs attention |

### Why these weights?
- **Price (30%)**: The most direct signal, but alone it's what every watchlist shows
- **Volume (25%)**: Volume anomalies are the strongest indicator of unusual activity. A 2% move on 3x volume is far more significant than a 2% move on normal volume
- **Market Relative (20%)**: Eliminates noise from broad market moves. If everything is up 3%, a stock up 3% isn't interesting
- **Volatility (15%)**: Context for whether this movement is unusual *for this stock*
- **Gap (10%)**: Gaps indicate overnight information that the market is digesting

### Signal Scoring Functions
Each signal uses a clamped linear scale:
```
signal_value = clamp((raw_value - threshold_min) / (threshold_max - threshold_min), 0, 1) × 100
```

### False Positive Mitigation
- A stock with only price movement but normal volume gets a lower score (max ~30)
- Multiple signals must fire together for "High" attention
- Market-wide moves are filtered via the relative signal

### Missing Data Handling
- If a signal can't be computed (e.g., no volume data), it contributes 0 to the score
- The score is NOT renormalized — missing data makes the score conservative
- Missing signals are flagged in the explanation

## Data Trust Model

Every piece of market data carries metadata:

```json
{
  "timestamp": "2026-09-04T15:30:00+05:30",
  "source": "yahoo_finance",
  "freshness": "live",     // "live" | "delayed" | "cached" | "stale" | "demo"
  "market_status": "open", // "open" | "closed" | "pre_market" | "post_market"
  "age_seconds": 45
}
```

### Freshness Rules
| Age | Status |
|---|---|
| <5 min | `live` |
| 5-15 min | `delayed` |
| 15-60 min | `cached` |
| >60 min | `stale` |
| Demo provider | Always `demo` |

### UI Indicators
- **Live**: Green dot
- **Delayed**: Yellow dot + "Delayed X min"
- **Cached/Stale**: Orange/Red dot + timestamp
- **Demo**: Purple dot + "Demo data"

## API Design

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/watchlist` | Get user's watchlist with current data + change assessment |
| `POST` | `/api/watchlist` | Add stock to watchlist |
| `DELETE` | `/api/watchlist/{symbol}` | Remove stock from watchlist |
| `GET` | `/api/stock/{symbol}` | Detailed stock data + change breakdown |
| `POST` | `/api/review` | Mark changes as reviewed (reset baseline) |
| `POST` | `/api/review/{symbol}` | Mark specific stock as reviewed |
| `GET` | `/api/market/status` | Market status + benchmark data |
| `GET` | `/api/search?q=` | Search for stocks |

## Demo Mode

A deterministic demo provider that simulates realistic Indian market data:
- ~8-10 pre-configured stocks (RELIANCE, TCS, INFY, HDFCBANK, etc.)
- Controlled scenarios: one stock with high attention (volume spike + price surge), one with medium (relative outperformance), most with normal movement
- Can be activated via environment variable `MARKET_PROVIDER=demo`
- Clearly labeled in the UI with a "Demo Data" badge

## Single-User Design

For hackathon simplicity:
- One default user (user_id = "default")
- Schema supports multi-user (user_id column on watchlist)
- No authentication implemented
- TODO for production: auth layer

## What We're Intentionally NOT Building

| Feature | Reason |
|---|---|
| Real-time WebSocket updates | Adds complexity, no demo value — manual refresh is fine |
| User authentication | Not core to the product insight |
| Push notifications | Out of scope for web demo |
| News integration | Unreliable free news APIs; would add noise not signal |
| Charting library | Mini sparklines only if time permits; full charts aren't the product |
| Mobile app | Responsive web is sufficient |
| Multi-device sync | Single-user model handles this via the backend |
