"""Unit tests for kavach/text_model.py's scorer selection and the DistilBERT
scorer specifically. The DistilBERT tests are skipped automatically if
models/distilbert/model isn't present (e.g. before it's fetched from Kaggle,
or on a machine without torch/transformers installed) -- see
DistilBertScorer._load()'s graceful degradation in text_model.py.
"""
import pytest

from kavach import config
from kavach.text_model import DistilBertScorer, TfidfLogRegScorer, get_text_scorer, reset_text_scorer

DISTILBERT_PRESENT = config.DISTILBERT_MODEL_DIR.exists()

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


@pytest.mark.skipif(not DISTILBERT_PRESENT, reason="models/distilbert/model not present")
def test_get_text_scorer_prefers_distilbert_when_present():
    scorer = get_text_scorer()
    assert scorer.name == "distilbert"
    assert scorer.is_loaded


def test_get_text_scorer_falls_back_to_baseline_when_distilbert_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DISTILBERT_MODEL_DIR", tmp_path / "does-not-exist")
    scorer = get_text_scorer()
    assert isinstance(scorer, TfidfLogRegScorer)
    assert scorer.name == "baseline"
