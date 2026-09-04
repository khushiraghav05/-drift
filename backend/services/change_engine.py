"""
Meaningful Change Engine

The core differentiator of SignalLens.

This module is a PURE FUNCTION — no side effects, no database access.
It takes a baseline snapshot, current snapshot, and market context,
and returns a ChangeAssessment with score, signals, and explanation.

Signal Weights (documented rationale):
- Price (30%):  Most direct signal, but every watchlist shows this
- Volume (25%): Strongest unusual-activity indicator
- Relative (20%): Filters noise from broad market moves
- Volatility (15%): Context for whether move is unusual for THIS stock
- Gap (10%): Overnight information the market is digesting

Scoring: Each signal uses a clamped linear scale:
  signal = clamp((raw - min_threshold) / (max_threshold - min_threshold), 0, 1) × 100

Missing data: Contributes 0 to the score. Score is NOT renormalized.
This makes the score conservative when data is incomplete.
"""

from models import (
    Snapshot, ChangeAssessment, SignalDetail,
    AttentionLevel, Freshness,
)
from config import settings


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a value between lo and hi."""
    return max(lo, min(hi, value))


def compute_price_signal(baseline: Snapshot, current: Snapshot) -> SignalDetail:
    """
    Price Movement Signal (weight: 30%)

    Measures: absolute percentage change from baseline price to current price.
    Rationale: Most fundamental signal, but alone it's what every watchlist shows.

    Thresholds:
    - <1%: no signal (normal intraday noise)
    - 1-5%: linear scale
    - >5%: maximum signal
    """
    if baseline.price is None or current.price is None or baseline.price == 0:
        return SignalDetail(
            name="price", weight=0.30,
            description="Price data unavailable", available=False,
        )

    change_pct = abs((current.price - baseline.price) / baseline.price * 100)
    direction = "+" if current.price >= baseline.price else ""
    actual_pct = (current.price - baseline.price) / baseline.price * 100

    raw_score = clamp(
        (change_pct - settings.PRICE_THRESHOLD_MIN) /
        (settings.PRICE_THRESHOLD_MAX - settings.PRICE_THRESHOLD_MIN)
    ) * 100

    return SignalDetail(
        name="price",
        raw_value=round(actual_pct, 2),
        signal_score=round(raw_score, 1),
        weight=0.30,
        weighted_score=round(raw_score * 0.30, 1),
        description=f"Price {direction}{actual_pct:.1f}% since baseline (₹{baseline.price:,.0f} → ₹{current.price:,.0f})",
        available=True,
    )


def compute_volume_signal(current: Snapshot) -> SignalDetail:
    """
    Volume Anomaly Signal (weight: 25%)

    Measures: current volume as a multiple of 20-day average volume.
    Rationale: Volume anomalies are the strongest indicator of unusual activity.
    A 2% move on 3x volume is far more significant than a 2% move on normal volume.

    Thresholds:
    - <1.5x: no signal (normal trading)
    - 1.5-3x: linear scale
    - >3x: maximum signal
    """
    if current.volume is None or current.avg_volume is None or current.avg_volume == 0:
        return SignalDetail(
            name="volume", weight=0.25,
            description="Volume data unavailable", available=False,
        )

    ratio = current.volume / current.avg_volume

    raw_score = clamp(
        (ratio - settings.VOLUME_THRESHOLD_MIN) /
        (settings.VOLUME_THRESHOLD_MAX - settings.VOLUME_THRESHOLD_MIN)
    ) * 100

    return SignalDetail(
        name="volume",
        raw_value=round(ratio, 2),
        signal_score=round(raw_score, 1),
        weight=0.25,
        weighted_score=round(raw_score * 0.25, 1),
        description=f"Volume is {ratio:.1f}× average" if ratio >= 1.5 else f"Volume is normal ({ratio:.1f}× average)",
        available=True,
    )


def compute_volatility_signal(baseline: Snapshot, current: Snapshot) -> SignalDetail:
    """
    Volatility Change Signal (weight: 15%)

    Measures: current day range (high-low) relative to baseline day range.
    Rationale: Contextualizes whether the current movement is unusual for THIS stock.

    Thresholds:
    - <1.3x baseline range: no signal
    - 1.3-2.5x: linear scale
    - >2.5x: maximum signal
    """
    # Current day range
    if current.day_high is None or current.day_low is None or current.price is None:
        return SignalDetail(
            name="volatility", weight=0.15,
            description="Volatility data unavailable", available=False,
        )

    current_range = current.day_high - current.day_low
    if current.price == 0:
        return SignalDetail(
            name="volatility", weight=0.15,
            description="Invalid price data", available=False,
        )

    current_range_pct = (current_range / current.price) * 100

    # Baseline day range (use baseline's high-low if available, else use a default)
    if baseline.day_high is not None and baseline.day_low is not None and baseline.price and baseline.price > 0:
        baseline_range = baseline.day_high - baseline.day_low
        baseline_range_pct = (baseline_range / baseline.price) * 100
    else:
        # Default assumption: 1% daily range
        baseline_range_pct = 1.0

    if baseline_range_pct == 0:
        baseline_range_pct = 0.5  # Avoid division by zero

    ratio = current_range_pct / baseline_range_pct

    raw_score = clamp(
        (ratio - settings.VOLATILITY_THRESHOLD_MIN) /
        (settings.VOLATILITY_THRESHOLD_MAX - settings.VOLATILITY_THRESHOLD_MIN)
    ) * 100

    desc = "Elevated" if ratio >= 1.5 else "Normal"
    return SignalDetail(
        name="volatility",
        raw_value=round(ratio, 2),
        signal_score=round(raw_score, 1),
        weight=0.15,
        weighted_score=round(raw_score * 0.15, 1),
        description=f"Volatility is {desc.lower()} ({ratio:.1f}× baseline range)",
        available=True,
    )


def compute_relative_signal(baseline: Snapshot, current: Snapshot) -> SignalDetail:
    """
    Market Relative Signal (weight: 20%)

    Measures: stock's movement minus the benchmark (NIFTY 50) movement.
    Rationale: A stock up 3% in a 3% market rally isn't interesting.
    A stock up 3% in a flat market IS interesting.

    Thresholds:
    - <1.5% divergence: no signal
    - 1.5-5%: linear scale
    - >5%: maximum signal
    """
    if (current.price is None or baseline.price is None or
            baseline.price == 0 or current.nifty_change_pct is None):
        return SignalDetail(
            name="relative", weight=0.20,
            description="Market context data unavailable", available=False,
        )

    stock_change_pct = (current.price - baseline.price) / baseline.price * 100
    nifty_change = current.nifty_change_pct

    divergence = abs(stock_change_pct - nifty_change)

    raw_score = clamp(
        (divergence - settings.RELATIVE_THRESHOLD_MIN) /
        (settings.RELATIVE_THRESHOLD_MAX - settings.RELATIVE_THRESHOLD_MIN)
    ) * 100

    if stock_change_pct > nifty_change:
        desc = f"Outperforming NIFTY by {divergence:.1f}%"
    else:
        desc = f"Underperforming NIFTY by {divergence:.1f}%"

    return SignalDetail(
        name="relative",
        raw_value=round(stock_change_pct - nifty_change, 2),
        signal_score=round(raw_score, 1),
        weight=0.20,
        weighted_score=round(raw_score * 0.20, 1),
        description=desc,
        available=True,
    )


def compute_gap_signal(current: Snapshot) -> SignalDetail:
    """
    Gap Signal (weight: 10%)

    Measures: difference between previous close and today's open.
    Rationale: Gaps indicate overnight information the market is pricing in.

    Thresholds:
    - <1% gap: no signal
    - 1-3%: linear scale
    - >3%: maximum signal
    """
    if current.previous_close is None or current.open_price is None or current.previous_close == 0:
        return SignalDetail(
            name="gap", weight=0.10,
            description="Gap data unavailable", available=False,
        )

    gap_pct = abs((current.open_price - current.previous_close) / current.previous_close * 100)

    raw_score = clamp(
        (gap_pct - settings.GAP_THRESHOLD_MIN) /
        (settings.GAP_THRESHOLD_MAX - settings.GAP_THRESHOLD_MIN)
    ) * 100

    direction = "up" if current.open_price > current.previous_close else "down"

    return SignalDetail(
        name="gap",
        raw_value=round(gap_pct, 2),
        signal_score=round(raw_score, 1),
        weight=0.10,
        weighted_score=round(raw_score * 0.10, 1),
        description=f"Gap {direction} {gap_pct:.1f}% from previous close" if gap_pct >= 1.0 else f"No significant gap ({gap_pct:.1f}%)",
        available=True,
    )


def score_to_attention_level(score: float) -> AttentionLevel:
    """Convert a composite score to an attention level."""
    if score <= settings.ATTENTION_NORMAL:
        return AttentionLevel.NORMAL
    elif score <= settings.ATTENTION_LOW:
        return AttentionLevel.LOW
    elif score <= settings.ATTENTION_MEDIUM:
        return AttentionLevel.MEDIUM
    else:
        return AttentionLevel.HIGH


def generate_explanation(
    signals: list[SignalDetail],
    level: AttentionLevel,
    display_name: str,
    current: Snapshot,
    baseline: Snapshot,
) -> str:
    """
    Generate a human-readable explanation for the change assessment.
    No AI fluff — specific, data-driven sentences.
    """
    if level == AttentionLevel.NORMAL:
        return f"{display_name} has shown normal movement since your last check."

    parts = []
    price_signal = next((s for s in signals if s.name == "price" and s.available), None)
    volume_signal = next((s for s in signals if s.name == "volume" and s.available), None)
    relative_signal = next((s for s in signals if s.name == "relative" and s.available), None)
    volatility_signal = next((s for s in signals if s.name == "volatility" and s.available), None)

    # Price context
    if price_signal and price_signal.signal_score > 0:
        direction = "rose" if (price_signal.raw_value or 0) > 0 else "fell"
        parts.append(f"{display_name} {direction} {abs(price_signal.raw_value or 0):.1f}% since your last check")

    # Volume context
    if volume_signal and volume_signal.signal_score > 0:
        parts.append(f"on {volume_signal.raw_value:.1f}× normal volume")

    # Relative context
    if relative_signal and relative_signal.signal_score > 0:
        parts.append(f"while {relative_signal.description.lower()}")

    # Volatility context
    if volatility_signal and volatility_signal.signal_score > 20:
        parts.append(f"with elevated volatility")

    if not parts:
        return f"{display_name} has had minor changes since your last check."

    explanation = ". ".join([
        " ".join(parts[:2]),
        *parts[2:]
    ]).strip()

    if not explanation.endswith("."):
        explanation += "."

    # Add significance note for HIGH
    if level == AttentionLevel.HIGH:
        explanation += f" This movement is significantly larger than {display_name}'s recent normal range."

    return explanation


def generate_summary(signals: list[SignalDetail], current: Snapshot, baseline: Snapshot) -> str:
    """Generate a short one-line summary for the attention queue."""
    parts = []

    price_signal = next((s for s in signals if s.name == "price" and s.available), None)
    if price_signal and price_signal.raw_value is not None:
        sign = "+" if price_signal.raw_value > 0 else ""
        parts.append(f"{sign}{price_signal.raw_value:.1f}%")

    volume_signal = next((s for s in signals if s.name == "volume" and s.available), None)
    if volume_signal and volume_signal.signal_score > 0 and volume_signal.raw_value:
        parts.append(f"Vol {volume_signal.raw_value:.1f}×")

    relative_signal = next((s for s in signals if s.name == "relative" and s.available), None)
    if relative_signal and relative_signal.signal_score > 0:
        parts.append(relative_signal.description)

    return " · ".join(parts) if parts else "Normal movement"


def assess_change(
    baseline: Snapshot,
    current: Snapshot,
    data_quality: Freshness = Freshness.LIVE,
    display_name: str = "",
) -> ChangeAssessment:
    """
    Main entry point: assess meaningful changes between baseline and current.

    This is a PURE FUNCTION — no side effects.

    Args:
        baseline: The snapshot from the user's last observation
        current: The current market snapshot
        data_quality: Freshness of the current data
        display_name: Human-readable stock name for explanations

    Returns:
        ChangeAssessment with score, level, signals, and explanation
    """
    # Compute all signals
    signals = [
        compute_price_signal(baseline, current),
        compute_volume_signal(current),
        compute_volatility_signal(baseline, current),
        compute_relative_signal(baseline, current),
        compute_gap_signal(current),
    ]

    # Composite score: sum of weighted scores
    composite = sum(s.weighted_score for s in signals)
    composite = round(min(composite, 100), 1)  # Cap at 100

    level = score_to_attention_level(composite)

    # Active signals (those that actually contributed)
    active = [s.name for s in signals if s.available and s.signal_score > 0]

    # Generate human-readable content
    summary = generate_summary(signals, current, baseline)
    explanation = generate_explanation(signals, level, display_name or current.symbol, current, baseline)

    return ChangeAssessment(
        score=composite,
        level=level,
        signals=signals,
        active_signals=active,
        summary=summary,
        explanation=explanation,
        data_quality=data_quality,
    )
