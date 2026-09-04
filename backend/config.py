"""
SignalLens Configuration
Reads settings from environment variables with sensible defaults.
"""

import os
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))


class Settings:
    """Application settings from environment variables."""

    MARKET_PROVIDER: str = os.getenv("MARKET_PROVIDER", "demo")
    DB_PATH: str = os.getenv("DB_PATH", "../signallens.db")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGIN: str = os.getenv("CORS_ORIGIN", "http://localhost:8000")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Cache TTL (seconds)
    CACHE_TTL_LIVE: int = 60       # 1 min when market is open
    CACHE_TTL_CLOSED: int = 300    # 5 min when market is closed

    # Data freshness thresholds (seconds)
    FRESHNESS_LIVE: int = 300       # <5 min = live
    FRESHNESS_DELAYED: int = 900    # 5-15 min = delayed
    FRESHNESS_CACHED: int = 3600    # 15-60 min = cached
    # >60 min = stale

    # Change engine thresholds
    PRICE_THRESHOLD_MIN: float = 1.0    # % — below this, no price signal
    PRICE_THRESHOLD_MAX: float = 5.0    # % — at this, price signal is max
    VOLUME_THRESHOLD_MIN: float = 1.5   # ratio — below this, no volume signal
    VOLUME_THRESHOLD_MAX: float = 3.0   # ratio — at this, volume signal is max
    VOLATILITY_THRESHOLD_MIN: float = 1.3  # ratio of current to baseline volatility
    VOLATILITY_THRESHOLD_MAX: float = 2.5
    RELATIVE_THRESHOLD_MIN: float = 1.5  # % divergence from benchmark
    RELATIVE_THRESHOLD_MAX: float = 5.0
    GAP_THRESHOLD_MIN: float = 1.0      # % gap
    GAP_THRESHOLD_MAX: float = 3.0

    # Attention levels
    ATTENTION_NORMAL: int = 20
    ATTENTION_LOW: int = 45
    ATTENTION_MEDIUM: int = 70
    # Above ATTENTION_MEDIUM = HIGH


settings = Settings()
