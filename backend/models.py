"""
SignalLens Pydantic Models
Request/response models and internal data structures.
"""

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


# --- Enums ---

class AttentionLevel(str, Enum):
    NORMAL = "normal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class BaselineState(str, Enum):
    NEW = "new"
    OBSERVING = "observing"
    CHANGED = "changed"
    REVIEWED = "reviewed"


class Freshness(str, Enum):
    LIVE = "live"
    DELAYED = "delayed"
    CACHED = "cached"
    STALE = "stale"
    DEMO = "demo"


class MarketStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    PRE_MARKET = "pre_market"
    POST_MARKET = "post_market"
    UNKNOWN = "unknown"


# --- Data Meta ---

class DataMeta(BaseModel):
    timestamp: str
    source: str
    freshness: Freshness
    market_status: MarketStatus = MarketStatus.UNKNOWN
    age_seconds: int = 0


# --- Stock Quote (from provider) ---

class StockQuote(BaseModel):
    symbol: str
    display_name: str = ""
    price: Optional[float] = None
    open_price: Optional[float] = None
    previous_close: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    volume: Optional[int] = None
    avg_volume: Optional[int] = None
    market_cap: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    timestamp: str = ""
    source: str = ""
    market_status: MarketStatus = MarketStatus.UNKNOWN


# --- Snapshot (DB record) ---

class Snapshot(BaseModel):
    id: Optional[int] = None
    symbol: str
    price: Optional[float] = None
    open_price: Optional[float] = None
    previous_close: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    volume: Optional[int] = None
    avg_volume: Optional[int] = None
    market_cap: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    timestamp: str = ""
    source: str = ""
    market_status: Optional[str] = None
    nifty_price: Optional[float] = None
    nifty_change_pct: Optional[float] = None
    created_at: str = ""


# --- Signal Detail ---

class SignalDetail(BaseModel):
    name: str
    raw_value: Optional[float] = None
    signal_score: float = 0.0
    weight: float = 0.0
    weighted_score: float = 0.0
    description: str = ""
    available: bool = True


# --- Change Assessment ---

class ChangeAssessment(BaseModel):
    score: float = 0.0
    level: AttentionLevel = AttentionLevel.NORMAL
    signals: list[SignalDetail] = []
    active_signals: list[str] = []
    summary: str = ""
    explanation: str = ""
    data_quality: Freshness = Freshness.LIVE


# --- Attention Item ---

class AttentionItem(BaseModel):
    symbol: str
    display_name: str
    price: Optional[float] = None
    baseline_price: Optional[float] = None
    change_pct: Optional[float] = None
    attention: ChangeAssessment
    data_meta: DataMeta
    baseline_state: BaselineState = BaselineState.NEW


# --- API Requests ---

class AddStockRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=30)


class ReviewRequest(BaseModel):
    symbols: list[str] = Field(..., min_items=1)


# --- API Responses ---

class WatchlistResponse(BaseModel):
    stocks: list[AttentionItem] = []
    market: Optional[dict] = None


class StockDetailResponse(BaseModel):
    symbol: str
    display_name: str
    current: Optional[dict] = None
    baseline: Optional[dict] = None
    change: Optional[ChangeAssessment] = None
    data_meta: Optional[DataMeta] = None


class AddStockResponse(BaseModel):
    symbol: str
    display_name: str
    added: bool


class SearchResult(BaseModel):
    symbol: str
    name: str
    exchange: str = ""
    type: str = ""


class MarketStatusResponse(BaseModel):
    nifty_price: Optional[float] = None
    nifty_change_pct: Optional[float] = None
    market_status: MarketStatus = MarketStatus.UNKNOWN
    timestamp: str = ""
    source: str = ""
    freshness: Freshness = Freshness.LIVE


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
