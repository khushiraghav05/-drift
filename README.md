SignalLens

A Watchlist That Explains What Changed

SignalLens is a smart market watchlist designed to answer one simple question:

"What meaningfully changed since I last checked?"

Traditional watchlists show prices and percentage changes, but users still have to manually scan every stock and decide what deserves attention. SignalLens turns the watchlist into a personal market change-detection system by remembering previous observations, detecting meaningful changes, prioritizing them, and explaining why they matter.

🚀 Why SignalLens?

Markets generate a huge amount of information. A user may have several stocks in their watchlist, but not every movement is worth their attention.

SignalLens focuses on change, context, and prioritization rather than simply displaying market data.

The core experience is:

CHECK → REMEMBER → DETECT → PRIORITIZE → EXPLAIN → REVIEW

When a user returns to the application, SignalLens helps them quickly understand what changed while they were away.

✨ Key Features

📌 Smart Watchlist

Create and manage a personalized stock watchlist.

Persist watchlist state across sessions.

View current stock information and movement.

🔎 Meaningful Change Detection

SignalLens evaluates changes using available market signals such as:

Price movement

Volume anomalies

Volatility

Movement relative to a market benchmark

Previous user-specific observations/baselines

The goal is to distinguish meaningful changes from normal market noise.

🎯 Explainable Attention Score

Stocks can be prioritized using an explainable Attention Score.

Instead of simply saying that a stock changed, SignalLens can show the factors contributing to its attention level.

This makes the system easier to understand and avoids treating the score as a black box.

🕐 "While You Were Away"

When the user returns, SignalLens highlights meaningful changes since their previous check.

This transforms a static watchlist into a persistent market-awareness tool.

✅ Review & Catch-Up

Users can review detected changes and mark them as reviewed.

Once there is nothing meaningful left to review, SignalLens can communicate:

You're caught up.

📊 Market Context

Where benchmark information is available, stock movement can be viewed relative to broader market movement.

This helps distinguish:

A stock moving with the market

A stock moving significantly more than the market

A stock behaving differently from the broader market

🛡️ Data Trust

SignalLens is designed to avoid presenting uncertain information as reliable live data.

The application can communicate data states such as:

Fresh

Delayed

Stale

Unavailable

🧪 Deterministic Demo Mode

The project includes a deterministic demo market-data provider so the core experience can be demonstrated reliably without depending on unpredictable external market conditions.

🏗️ Architecture

SignalLens uses a lightweight architecture designed for a hackathon MVP while keeping the core responsibilities separated.

                    ┌─────────────────────┐
                    │      Frontend       │
                    │   HTML / CSS / JS   │
                    └──────────┬──────────┘
                               │
                               │ HTTP / API
                               ▼
                    ┌─────────────────────┐
                    │     FastAPI App     │
                    ├─────────────────────┤
                    │ Watchlist Routes    │
                    │ Market Routes       │
                    │ Review Routes       │
                    └──────────┬──────────┘
                               │
                ┌──────────────┼──────────────┐
                ▼              ▼              ▼
        ┌──────────────┐ ┌────────────┐ ┌──────────────┐
        │ Watchlist    │ │  Change    │ │   Market     │
        │ Service      │ │  Engine    │ │   Provider   │
        └──────────────┘ └────────────┘ └──────────────┘
                │              │              │
                └──────────────┼──────────────┘
                               ▼
                    ┌─────────────────────┐
                    │       SQLite        │
                    │ Watchlist /         │
                    │ Snapshots /         │
                    │ Baselines / Review  │
                    └─────────────────────┘

Main Components

Frontend

Interactive web interface

Watchlist management

Change summaries

Attention indicators

Review interactions

FastAPI Backend

API endpoints

Watchlist operations

Market data access

Review state management

Change Engine

Evaluates market observations

Detects meaningful changes

Produces explainable attention information

Database

SQLite for lightweight local persistence

Stores watchlist, market snapshots, baselines, and review-related state

Provider Layer

Abstracts market data access

Includes deterministic demo data for reliable demonstrations

🛠️ Technology Stack

Python

FastAPI

SQLite

HTML

CSS

JavaScript

REST-style API communication

⚙️ Getting Started

Prerequisites

Make sure you have:

Python 3.11+ recommended

Git

1. Clone the repository

git clone https://github.com/khushiraghav05/-drift.git
cd -drift

2. Create a virtual environment

Windows:

python -m venv .venv
.venv\Scripts\activate

macOS/Linux:

python3 -m venv .venv
source .venv/bin/activate

3. Install dependencies

pip install -r requirements.txt

4. Start the application

python -m uvicorn backend.main:app --reload --port 8000

5. Open SignalLens

Open:

http://localhost:8000

🧪 Demo Flow

A simple way to demonstrate SignalLens:

Open the application.

Add stocks to your watchlist.

Observe the initial market state.

Run/use the deterministic demo scenario.

Return to the dashboard.

Open "While You Were Away".

Observe stocks that experienced meaningful changes.

Open the explanation for an attention score.

Compare the stock movement with available market context.

Mark changes as reviewed.

Demonstrate the "You're Caught Up" state.

The demo is designed to show the difference between a traditional watchlist and a watchlist that remembers and explains change.

🔐 Data & Reliability

SignalLens is designed with unreliable market-data conditions in mind.

The application should distinguish between different data-quality states instead of silently treating all values as current.

Important principles include:

Do not present stale data as live.

Surface delayed or unavailable information.

Isolate failures where possible so one unavailable stock does not break the entire watchlist.

Keep business logic such as meaningful-change detection on the backend.

Use deterministic demo data when reliability is more important than live-market variability.

📈 Scalability Considerations

The MVP uses SQLite for simplicity and fast local development, but the architecture separates market-data access, watchlist logic, change detection, and persistence.

For a production-scale deployment, the architecture can evolve toward:

PostgreSQL or another production database

Shared market-data caching

Provider rate-limit management

Background market-data ingestion

Per-user watchlist and baseline isolation

Indexed database queries

Batched market-data requests

Horizontal API scaling

A key scalability principle is to avoid repeatedly fetching the same market information independently for every user.

🔮 Future Scope

Potential future improvements include:

Live market-data providers

Cloud deployment

Multi-user authentication

Personalized notification/alerting

Advanced event and news context

More sophisticated anomaly detection

Portfolio integration

Mobile/PWA support

Production-grade caching and background processing

💡 What Makes SignalLens Different?

A traditional watchlist answers:

"What is the price of this stock?"

SignalLens aims to answer:

"What changed since I last looked, how unusual is it, and why should I care?"

That shift—from displaying information to remembering, prioritizing, and explaining change—is the core idea behind SignalLens.

⚠️ Disclaimer

SignalLens is a hackathon prototype intended for demonstration and experimentation.

It is not financial advice and should not be used as the sole basis for investment decisions.

👥 Project

SignalLens
Built for the Groww CODE 2026 Hackathon.

Repository: https://github.com/khushiraghav05/-drift
