# Product Critique — SignalLens

## The Hard Question: Is This Actually Different?

### What a normal watchlist does:
Shows a list of stocks with current price, daily % change, and maybe a sparkline. Updates in real-time. User scrolls through the list to notice what moved.

### What SignalLens claims to do:
Remembers what the user last saw and surfaces what meaningfully changed — prioritized by significance, not alphabetical order.

### Is that genuinely useful?

**Yes, but only if the "meaningful change" signal is actually better than what the user could do by glancing at percentages.**

A user looking at a normal watchlist with 15 stocks can scan percentage changes in about 5 seconds. SignalLens adds value only when:

1. The watchlist is large enough that scanning is tedious (>15 stocks)
2. The "meaningful" assessment is smarter than a simple sort-by-% — i.e., it factors in volume, volatility context, and relative market movement
3. The "since you last checked" framing adds context a real-time view doesn't provide

**Verdict: The core idea is sound, but we must avoid over-designing the scoring to the point where it appears like fake AI.**

## Brutal Critique by Feature

| Feature | Value | Risk | Decision |
|---|---|---|---|
| **Change Memory** (baseline tracking) | HIGH — this is the core differentiator | Complexity in defining "what counts as the user having seen it" | Keep. Define a clear, simple baseline model |
| **Meaningful Change Score** | HIGH — but only if transparent | Score feels like fake AI if not explainable | Keep. Use simple weighted signals. Show formula |
| **Attention Queue** | MEDIUM — useful UX, but essentially "sort by score" | Risks being a glorified sort | Keep. Value is in the framing + explanations, not just sorting |
| **Change Cards** | HIGH — this is where product insight shows | Could become generic text templates | Keep. Make explanations specific to the actual data |
| **Market Context** (relative movement) | HIGH — this is the single most impressive signal | Requires benchmark data (NIFTY 50) which adds complexity | Keep. This is what separates us from "just showing %" |
| **Data Trust indicators** | MEDIUM — shows engineering maturity | Easy to over-do | Keep simple: timestamp + freshness badge |
| **Change History** | LOW for demo | Adds DB complexity, hard to demo in 3 min | Simplify: show on stock detail page, don't make it a separate page |
| **Demo Mode** | CRITICAL — the demo must work reliably | If it looks canned, judges will dismiss it | Make demo data feel natural. Use it as fallback, not primary |

## Features That Should Be Removed

1. **Separate "Change History" page** → Fold into stock detail view
2. **Complex authentication** → Use a single default user for hackathon; design the schema to support multi-user but don't implement auth
3. **Real-time WebSocket updates** → Polling or manual refresh is fine. Real-time adds complexity without demo value
4. **Elaborate settings/configuration** → Hard-code sensible defaults

## What Would a Judge Question?

1. "How is this different from sorting by percentage change?"
   - **Answer**: We factor in volume anomalies, volatility context, and performance relative to the benchmark. A stock up 2% with 3x normal volume during a flat market is more interesting than a stock up 3% during a broad rally.

2. "Is the 'meaningful change' score actually meaningful?"
   - **Answer**: Every signal is transparent. The user can see exactly why a stock scored 82: price moved +4.2%, volume was 2.4x average, and it outperformed NIFTY by 3.1%. No black box.

3. "What happens when your data provider fails?"
   - **Answer**: We show the last cached data with a clear staleness indicator. The demo provider can take over entirely for offline demos.

4. "How does the baseline work? When does it reset?"
   - **Answer**: The baseline records a snapshot when the user views the dashboard. It only resets when they explicitly acknowledge changes or after a configurable cooldown. We don't re-alert on the same change repeatedly.

5. "Does this scale?"
   - **Answer**: We document the scaling constraints of SQLite and discuss what would change (PostgreSQL, Redis caching, background workers for snapshot collection).

## Which Features Demonstrate Hackathon Criteria?

| Criterion | Strongest Feature |
|---|---|
| **Engineering Depth** | Market data provider abstraction + Change Engine as testable module |
| **Product Thinking** | Relative market context (stock vs benchmark) + baseline memory |
| **Resilience** | Stale data handling + provider fallback + data trust indicators |
| **Originality** | The core loop: Check → Remember → Detect → Prioritize → Explain |
| **Code Quality** | Clean separation: provider → engine → API → UI |
