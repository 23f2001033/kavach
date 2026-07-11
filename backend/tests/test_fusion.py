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
    # Empty `components` doubles as the "no signals seen at all" flag.
    assert result["components"] == {}


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


def test_combine_monotonic_in_audio_score():
    scores = []
    for a in [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]:
        result = combine(text_score=0.1, signature_hits=[], audio_score=a)
        scores.append(result["risk_score"])
    assert scores == sorted(scores), "risk_score must not decrease as audio_score increases"
    assert scores[0] < scores[-1]


# ---------------------------------------------------- noisy-OR properties
def test_combine_text_only_equals_text_score():
    """Property (a): with ONLY text available (no signature hits, no audio),
    risk_score must equal text_score exactly -- no dilution. This only holds
    because config.FUSION_WEIGHTS['text'] defaults to 1.0; if that default
    ever changes this test should be revisited alongside it."""
    assert config.FUSION_WEIGHTS["text"] == 1.0
    for t in [0.0, 0.1, 0.37, 0.588, 0.65, 0.9, 1.0]:
        result = combine(text_score=t, signature_hits=[], audio_score=None)
        assert result["risk_score"] == pytest.approx(t)


def test_combine_text_alone_can_reach_high():
    """Regression test for the dilution bug: a confident text_score alone
    (no signature hits, no audio) must be able to clear the 'high' threshold.
    Under the old weighted-average combiner this was structurally impossible
    (capped at ~0.588) no matter how confident the text model was."""
    result = combine(text_score=1.0, signature_hits=[], audio_score=None)
    assert result["risk_score"] == pytest.approx(1.0)
    assert result["risk_level"] == "high"

    result = combine(text_score=0.9, signature_hits=[], audio_score=None)
    assert result["risk_level"] == "high"


def test_combine_adding_nonzero_signature_strictly_increases_risk():
    """Property (b): adding any nonzero second signal must strictly increase
    risk_score relative to text alone (as long as the text-only score isn't
    already saturated at 1.0)."""
    text_only = combine(text_score=0.5, signature_hits=[], audio_score=None)
    with_sig = combine(text_score=0.5, signature_hits=[LOW_HIT], audio_score=None)
    assert with_sig["risk_score"] > text_only["risk_score"]


def test_combine_adding_nonzero_audio_strictly_increases_risk():
    text_only = combine(text_score=0.5, signature_hits=[], audio_score=None)
    with_audio = combine(text_score=0.5, signature_hits=[], audio_score=0.3)
    assert with_audio["risk_score"] > text_only["risk_score"]


def test_combine_noisy_or_formula_matches_hand_computation():
    """Pin the exact noisy-OR arithmetic so a future refactor can't silently
    drift back toward an averaging scheme."""
    w = config.FUSION_WEIGHTS
    text_score, audio_score = 0.6, 0.4
    hits = [HIGH_HIT, MED_HIT]  # severities 3, 2 -> 0.35 + 0.22 = 0.57
    sig_score = signature_subscore(hits)
    assert sig_score == pytest.approx(0.57)

    expected = 1.0 - (
        (1.0 - text_score * w["text"])
        * (1.0 - sig_score * w["signature"])
        * (1.0 - audio_score * w["audio"])
    )
    result = combine(text_score=text_score, signature_hits=hits, audio_score=audio_score)
    assert result["risk_score"] == pytest.approx(expected)


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
