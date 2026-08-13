"""Explainer regression tests.

Covers the "audio alone forces a false 'strong scam signs' claim" bug:
the rule-based composer used to have no branch for the audio signal at all,
so an audio-only "high"/"suspicious" verdict printed a headline claiming
scam signs while enumerating zero of them. See kavach/explain.py and
kavach/fusion.py / kavach/config.py (FUSION_WEIGHTS["audio"]) for the fix.
"""
import pytest

from kavach.explain import compose_rule_based

HIGH_HIT = {"id": "x", "severity": 3, "explanation": "Asked for your OTP."}


def _reason_lines(explanation: str):
    return [ln for ln in explanation.splitlines() if ln.strip().startswith("-")]


# --------------------------------------------------------------- headline honesty
def test_never_claims_scam_signs_with_no_signature_hits_high():
    explanation = compose_rule_based("high", [], text_score=0.1, audio_score=0.99)
    assert "scam signs" not in explanation.lower()


def test_never_claims_scam_signs_with_no_signature_hits_suspicious():
    explanation = compose_rule_based("suspicious", [], text_score=0.1, audio_score=0.6)
    assert "scam signs" not in explanation.lower()


def test_signature_hits_present_may_say_scam_signs():
    explanation = compose_rule_based("high", [HIGH_HIT], text_score=0.9, audio_score=None)
    assert "scam signs" in explanation.lower()
    assert "1 scam sign" in explanation


# --------------------------------------------------------- audio-only explanation
def test_audio_only_high_confidence_names_the_voice_and_caveats_it():
    """This is exactly the reported bug scenario: no signature hits, low
    text_score, high audio_score. The explanation must (a) not lie about scam
    signs, (b) name the voice as the reason, and (c) caveat that synthetic
    voices alone aren't proof of a scam (bank/clinic/delivery robocalls)."""
    explanation = compose_rule_based("suspicious", [], text_score=0.18, audio_score=0.999)
    lower = explanation.lower()
    assert "scam signs" not in lower
    assert "voice" in lower
    assert "synthetic" in lower or "artificial" in lower
    # Honest caveat that a synthetic voice alone isn't proof of a scam.
    assert "not proof" in lower or "also use" in lower
    assert _reason_lines(explanation), "audio-only suspicious verdict must enumerate a concrete reason"


def test_audio_only_reason_present_even_at_high_level():
    explanation = compose_rule_based("high", [], text_score=None, audio_score=1.0)
    assert _reason_lines(explanation)
    assert "voice" in explanation.lower()


# ------------------------------------------------------ non-empty reasons invariant
@pytest.mark.parametrize("risk_level", ["suspicious", "high"])
def test_non_low_verdicts_always_enumerate_a_reason(risk_level):
    # No signature hits, no strong text signal, no strong audio signal --
    # the fused score must still be explainable if this level was reached.
    explanation = compose_rule_based(risk_level, [], text_score=0.2, audio_score=0.3)
    assert _reason_lines(explanation), f"{risk_level} verdict produced no concrete reasons:\n{explanation}"


def test_low_verdict_unaffected_by_audio():
    explanation = compose_rule_based("low", [], text_score=0.1, audio_score=0.9)
    assert "does not show clear scam signs" in explanation.lower()


if __name__ == "__main__":
    pytest.main([__file__])
