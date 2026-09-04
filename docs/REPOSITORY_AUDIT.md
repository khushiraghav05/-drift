# Repository & Environment Audit

## Repository State

| Property | Value |
|---|---|
| **Path** | `c:\Users\khush\-drift` |
| **Branch** | `main` |
| **Commits** | None (empty repo) |
| **Remote** | `origin` → `https://github.com/khushiraghav05/-drift.git` |
| **Git User** | Khushi Raghav (`khushiraghav2005@gmail.com`) |

The repository is **completely empty** — no source files, no configuration, no package manifests. Only the `.git` directory exists.

## System Environment

| Tool | Version |
|---|---|
| **Node.js** | v24.13.1 |
| **npm** | 11.8.0 |
| **Python** | 3.13.4 |
| **pip** | 25.1.1 |
| **Docker** | Not available |
| **sqlite3 CLI** | Not available (Python sqlite3 module is available) |
| **OS** | Windows |

## Existing Stack

There is **no existing stack**. The repo has never been committed to. This is a greenfield project.

## Technology Decision

Since there is no pre-existing codebase to preserve, we choose the stack based on hackathon fitness:

| Layer | Choice | Rationale |
|---|---|---|
| **Backend** | **FastAPI (Python)** | Rapid development, async support, automatic OpenAPI docs, excellent for hackathons |
| **Database** | **SQLite** (via `aiosqlite`) | Zero infrastructure, file-based, Python has built-in support, sufficient for demo scale |
| **Frontend** | **Vanilla HTML/CSS/JS** | No build step, instant iteration, full design control, no framework overhead |
| **Market Data** | **Yahoo Finance** (`yfinance`) + Demo provider | Free, reliable enough for Indian stocks (.NS suffix), no API key required |
| **Package Manager** | pip (backend), none needed for frontend (no build) |

## Technical Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Yahoo Finance rate limits / unreliability | Medium | Demo provider as fallback; caching layer; stale-data indicators |
| SQLite concurrency limits | Low | Single-writer is fine for hackathon scale; document what changes at scale |
| No TypeScript on frontend | Low | Keep JS modules small and well-structured |
| Network dependency for live demo | High | Deterministic demo provider that works offline |
| Python sqlite3 has no CLI on this system | Low | Use Python scripts for DB inspection/migration |

## Pre-Implementation Checklist

- [x] Repository inspected — empty, safe to build from scratch
- [x] Remote verified — GitHub repo ready for push
- [x] Git identity configured
- [x] No existing code to preserve
- [x] No environment variables or secrets present
- [x] No `.env` files to protect (will create `.env.example`)
