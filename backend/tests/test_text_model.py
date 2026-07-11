"""Unit tests for kavach/text_model.py's scorer selection, the DistilBERT
scorer, and the EnsembleTextScorer. The DistilBERT-specific tests are skipped
automatically if models/distilbert/model isn't present (e.g. before it's
fetched from Kaggle, or on a machine without torch/transformers installed) --
see DistilBertScorer._load()'s graceful degradation in text_model.py. Tests
that need BOTH DistilBERT and the TF-IDF baseline (to exercise the real
ensemble end-to-end) are separately skipped if either is missing.
"""
import pytest

from kavach import config
from kavach.text_model import (
    BaseTextScorer,
    DistilBertScorer,
    EnsembleTextScorer,
    TfidfLogRegScorer,
    get_text_scorer,
    reset_text_scorer,
)

DISTILBERT_PRESENT = config.DISTILBERT_MODEL_DIR.exists()
BASELINE_PRESENT = config.TEXT_MODEL_PATH.exists()
BOTH_PRESENT = DISTILBERT_PRESENT and BASELINE_PRESENT


class _StubScorer(BaseTextScorer):
    """Minimal fake BaseTextScorer for testing EnsembleTextScorer's combining
    logic in isolation, without needing real model artifacts."""

    def __init__(self, name, loaded, fixed_score=None, raises=False):
        self.name = name
        self._loaded = loaded
        self._fixed_score = fixed_score
        self._raises = raises

    @property
    def is_loaded(self):
        return self._loaded

    def score(self, transcript):
        if self._raises:
            raise RuntimeError("boom")
        return self._fixed_score

DIGITAL_ARREST_TRANSCRIPT = (
    "Caller: This is Inspector Rathore calling from Mumbai Police cyber cell. "
    "A SIM card taken on your Aadhaar was used for illegal activity and an FIR has been registered "
    "against you. This is a matter of national security. You are now under digital arrest. "
    "Do not disconnect this call and do not tell anyone, not even your family. "
    "To verify your innocence, transfer your funds to the secure government account I am sending you, "
    "it will be refunded after RBI verification within ten minutes. "
    "Also read me the OTP that just came to your phone so we can scan your account."
)

BENIGN_DELIVERY_TRANSCRIPT = (
    "Caller: Good afternoon, Blue Dart calling. Your parcel is out for delivery today between 2 PM and "
    "evening. Will someone be home? Receiver: Yes, I'm home. Caller: Great, it's cash on delivery, "
    "1,499 rupees, you can also pay by UPI at the door on the company QR. Receiver: I'll pay by UPI "
    "when you arrive, see you soon. Caller: Thank you, reaching in five minutes."
)


def setup_function():
    reset_text_scorer()


def teardown_function():
    reset_text_scorer()


@pytest.mark.skipif(not DISTILBERT_PRESENT, reason="models/distilbert/model not present")
def test_distilbert_scorer_loads():
    scorer = DistilBertScorer()
    assert scorer.is_loaded
    assert scorer.name == "distilbert"


@pytest.mark.skipif(not DISTILBERT_PRESENT, reason="models/distilbert/model not present")
def test_distilbert_scorer_scores_in_range_and_separates_scam_from_benign():
    scorer = DistilBertScorer()
    scam_score = scorer.score(DIGITAL_ARREST_TRANSCRIPT)
    benign_score = scorer.score(BENIGN_DELIVERY_TRANSCRIPT)

    assert scam_score is not None
    assert benign_score is not None
    assert 0.0 <= scam_score <= 1.0
    assert 0.0 <= benign_score <= 1.0
    assert scam_score > benign_score


@pytest.mark.skipif(not DISTILBERT_PRESENT, reason="models/distilbert/model not present")
def test_distilbert_scorer_returns_none_for_empty_transcript():
    scorer = DistilBertScorer()
    assert scorer.score("") is None
    assert scorer.score("   ") is None


@pytest.mark.skipif(not DISTILBERT_PRESENT, reason="models/distilbert/model not present")
def test_distilbert_scorer_windows_long_transcript():
    """A transcript far longer than max_length tokens should still score in
    [0, 1] via the sliding-window max-probability path (_score_windows)."""
    scorer = DistilBertScorer()
    long_transcript = (DIGITAL_ARREST_TRANSCRIPT + " ") * 30  # comfortably over 512 tokens
    score = scorer.score(long_transcript)
    assert score is not None
    assert 0.0 <= score <= 1.0


@pytest.mark.skipif(not BOTH_PRESENT, reason="both models/distilbert/model and models/text_baseline.joblib must be present")
def test_get_text_scorer_prefers_ensemble_when_both_present():
    scorer = get_text_scorer()
    assert scorer.name == "ensemble"
    assert scorer.is_loaded
    assert isinstance(scorer, EnsembleTextScorer)


@pytest.mark.skipif(not DISTILBERT_PRESENT, reason="models/distilbert/model not present")
def test_get_text_scorer_uses_distilbert_alone_when_baseline_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "TEXT_MODEL_PATH", tmp_path / "does-not-exist.joblib")
    scorer = get_text_scorer()
    assert scorer.name == "distilbert"
    assert scorer.is_loaded
    assert isinstance(scorer, DistilBertScorer)


def test_get_text_scorer_falls_back_to_baseline_when_distilbert_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DISTILBERT_MODEL_DIR", tmp_path / "does-not-exist")
    scorer = get_text_scorer()
    assert isinstance(scorer, TfidfLogRegScorer)
    assert scorer.name == "baseline"


def test_get_text_scorer_degrades_when_neither_present(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DISTILBERT_MODEL_DIR", tmp_path / "does-not-exist-distilbert")
    monkeypatch.setattr(config, "TEXT_MODEL_PATH", tmp_path / "does-not-exist.joblib")
    scorer = get_text_scorer()
    assert scorer.is_loaded is False
    assert scorer.score("anything") is None


# ------------------------------------------------------------- EnsembleTextScorer
def test_ensemble_scorer_is_max_of_loaded_sub_scorers():
    ensemble = EnsembleTextScorer([
        _StubScorer("a", loaded=True, fixed_score=0.2),
        _StubScorer("b", loaded=True, fixed_score=0.9),
    ])
    assert ensemble.is_loaded
    assert ensemble.score("some transcript") == pytest.approx(0.9)


def test_ensemble_scorer_ignores_unloaded_sub_scorers():
    ensemble = EnsembleTextScorer([
        _StubScorer("a", loaded=False, fixed_score=0.99),
        _StubScorer("b", loaded=True, fixed_score=0.4),
    ])
    assert ensemble.is_loaded
    assert ensemble.score("some transcript") == pytest.approx(0.4)


def test_ensemble_scorer_not_loaded_when_no_sub_scorer_loaded():
    ensemble = EnsembleTextScorer([
        _StubScorer("a", loaded=False),
        _StubScorer("b", loaded=False),
    ])
    assert ensemble.is_loaded is False
    assert ensemble.score("some transcript") is None


def test_ensemble_scorer_returns_none_when_all_loaded_scorers_return_none():
    ensemble = EnsembleTextScorer([
        _StubScorer("a", loaded=True, fixed_score=None),
        _StubScorer("b", loaded=True, fixed_score=None),
    ])
    assert ensemble.score("some transcript") is None


def test_ensemble_scorer_survives_a_sub_scorer_raising():
    """A sub-scorer that raises should not break the ensemble -- it's treated
    like a None contribution, same graceful-degradation contract as every
    other scorer in this module."""
    ensemble = EnsembleTextScorer([
        _StubScorer("broken", loaded=True, raises=True),
        _StubScorer("fine", loaded=True, fixed_score=0.6),
    ])
    assert ensemble.score("some transcript") == pytest.approx(0.6)


def test_ensemble_scorer_name_is_ensemble():
    assert EnsembleTextScorer([]).name == "ensemble"


@pytest.mark.skipif(not BOTH_PRESENT, reason="both models/distilbert/model and models/text_baseline.joblib must be present")
def test_ensemble_scorer_real_models_score_scam_higher_than_benign():
    """End-to-end with the real DistilBERT + TF-IDF models: the ensemble
    should still clearly separate a scam script from a benign one, same as
    each sub-scorer does alone."""
    ensemble = EnsembleTextScorer([DistilBertScorer(), TfidfLogRegScorer()])
    scam_score = ensemble.score(DIGITAL_ARREST_TRANSCRIPT)
    benign_score = ensemble.score(BENIGN_DELIVERY_TRANSCRIPT)
    assert scam_score is not None
    assert benign_score is not None
    assert 0.0 <= scam_score <= 1.0
    assert 0.0 <= benign_score <= 1.0
    assert scam_score > benign_score
