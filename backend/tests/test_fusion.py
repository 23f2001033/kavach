"""Fusion tests: monotonicity, graceful None handling, signature saturation,
and hysteresis (no flicker near a threshold, correct up/down transitions).
"""
import pytest

from kavach import config
from kavach.fusion import HysteresisMeter, classify, combine, signature_subscore

HIGH_HIT = {"id": "x", "severity": 3}
MED_HIT = {"id": "y", "severity": 2}
LOW_HIT = {"id": "z", "severity": 1}


# ------------------------------------------------------------------ combine()
def test_combine_all_none_degrades_to_zero_risk():
    result = combine(text_score=None, signature_hits=None, audio_score=None)
    assert result["risk_score"] == 0.0
    assert result["risk_level"] == "low"


def test_combine_handles_missing_text_and_audio():
    # Only signature hits available; must not crash and must reflect them.
    result = combine(text_score=None, signature_hits=[HIGH_HIT], audio_score=None)
    assert result["risk_score"] > 0.0
    assert "text" not in result["components"]
    assert "audio" not in result["components"]
    assert result["components"]["signature"] == signature_subscore([HIGH_HIT])


def test_combine_monotonic_in_text_score():
    scores = []
    for t in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        result = combine(text_score=t, signature_hits=[], audio_score=None)
        scores.append(result["risk_score"])
    assert scores == sorted(scores), "risk_score must not decrease as text_score increases"
    assert scores[0] < scores[-1]


def test_combine_monotonic_in_signature_hits():
    r0 = combine(text_score=0.1, signature_hits=[])
    r1 = combine(text_score=0.1, signature_hits=[LOW_HIT])
    r2 = combine(text_score=0.1, signature_hits=[LOW_HIT, MED_HIT])
    r3 = combine(text_score=0.1, signature_hits=[LOW_HIT, MED_HIT, HIGH_HIT])
    assert r0["risk_score"] <= r1["risk_score"] <= r2["risk_score"] <= r3["risk_score"]


def test_signature_subscore_saturates():
    many_hits = [HIGH_HIT] * 10
    assert signature_subscore(many_hits) == config.SIGNATURE_SATURATION
    assert signature_subscore([]) == 0.0


def test_combine_all_signals_present():
    result = combine(text_score=0.9, signature_hits=[HIGH_HIT, MED_HIT], audio_score=0.9)
    assert set(result["components"]) == {"text", "signature", "audio"}
    assert result["risk_level"] == "high"
    assert 0.0 <= result["risk_score"] <= 1.0


def test_classify_thresholds():
    assert classify(0.0) == "low"
    assert classify(config.RISK_THRESHOLDS["suspicious"]) == "suspicious"
    assert classify(config.RISK_THRESHOLDS["high"]) == "high"
    assert classify(1.0) == "high"


# ------------------------------------------------------------ HysteresisMeter
def test_hysteresis_no_flicker_when_oscillating_at_boundary():
    """Scores hovering right at the suspicious threshold (within the margin)
    should not flip the level back and forth."""
    meter = HysteresisMeter()
    t_susp = config.RISK_THRESHOLDS["suspicious"]
    m = config.HYSTERESIS_MARGIN
    seq = [t_susp - 0.01, t_susp + 0.01, t_susp - 0.02, t_susp + 0.02, t_susp - 0.01]
    levels = [meter.update(s) for s in seq]
    # None of these small oscillations (all within +/- m of the threshold) should
    # ever reach "suspicious" starting from "low".
    assert all(level == "low" for level in levels), levels
    assert t_susp + m > max(seq)  # sanity: oscillation genuinely stayed inside the dead zone


def test_hysteresis_transitions_up_and_down_with_margin():
    meter = HysteresisMeter()
    t_susp = config.RISK_THRESHOLDS["suspicious"]
    t_high = config.RISK_THRESHOLDS["high"]
    m = config.HYSTERESIS_MARGIN

    assert meter.update(0.0) == "low"
    # Crossing threshold but not clearing the margin: should stay low.
    assert meter.update(t_susp + m / 2) == "low"
    # Clearing threshold + margin: should move up.
    assert meter.update(t_susp + m + 0.01) == "suspicious"
    # Dropping back below just the raw threshold, but not below threshold - margin: stays.
    assert meter.update(t_susp - m / 2) == "suspicious"
    # Dropping below threshold - margin: falls back to low.
    assert meter.update(t_susp - m - 0.01) == "low"

    # Jump straight to high from low when score is far beyond both thresholds.
    assert meter.update(t_high + m + 0.05) == "high"
    # Falling to just below high - margin (but still above suspicious+margin): -> suspicious.
    mid = (t_susp + t_high) / 2
    assert meter.update(mid) == "suspicious"
    # Falling below suspicious - margin -> low.
    assert meter.update(t_susp - m - 0.01) == "low"


def test_hysteresis_reset():
    meter = HysteresisMeter()
    meter.update(0.99)
    assert meter.level == "high"
    meter.reset()
    assert meter.level == "low"
    assert meter.last_score == 0.0


def test_hysteresis_independent_instances():
    """Two HysteresisMeter instances (e.g. two call sessions) must not share state."""
    m1, m2 = HysteresisMeter(), HysteresisMeter()
    m1.update(0.99)
    assert m1.level == "high"
    assert m2.level == "low"


if __name__ == "__main__":
    pytest.main([__file__])
