"""Unit tests for kavach/audio_model.py's OnnxAudioScorer: sigmoid application
over the model's single raw logit, and the fixed-window (center-crop/zero-pad)
convention that matches training/audio/train_audio_deepfake.py::load_waveform
at eval time. The real-model tests are skipped automatically if
models/kavach_audio.onnx or onnxruntime aren't present -- see
OnnxAudioScorer._load()'s graceful degradation in audio_model.py.
"""
import math

import numpy as np
import pytest

from kavach import config
from kavach.audio_model import (
    OnnxAudioScorer,
    _fit_to_window,
    get_audio_scorer,
    reset_audio_scorer,
)

MODEL_PRESENT = config.AUDIO_MODEL_PATH.exists()

try:
    import onnxruntime  # noqa: F401
    ORT_AVAILABLE = True
except ImportError:
    ORT_AVAILABLE = False

REAL_MODEL_AVAILABLE = MODEL_PRESENT and ORT_AVAILABLE


def setup_function():
    reset_audio_scorer()


def teardown_function():
    reset_audio_scorer()


# ------------------------------------------------------------ _fit_to_window
def test_fit_to_window_pads_short_waveform_with_zeros():
    target_len = int(config.AUDIO_MAX_SECONDS * config.AUDIO_SAMPLE_RATE)
    short = np.ones(target_len - 100, dtype="float32")
    out = _fit_to_window(short)
    assert len(out) == target_len
    # original samples preserved at the front, zeros appended at the end
    assert np.array_equal(out[: target_len - 100], short)
    assert np.all(out[target_len - 100:] == 0.0)


def test_fit_to_window_center_crops_long_waveform():
    target_len = int(config.AUDIO_MAX_SECONDS * config.AUDIO_SAMPLE_RATE)
    n = target_len + 200
    long_wave = np.arange(n, dtype="float32")
    out = _fit_to_window(long_wave)
    assert len(out) == target_len
    expected_start = (n - target_len) // 2
    assert np.array_equal(out, long_wave[expected_start:expected_start + target_len])


def test_fit_to_window_leaves_exact_length_waveform_unchanged():
    target_len = int(config.AUDIO_MAX_SECONDS * config.AUDIO_SAMPLE_RATE)
    exact = np.arange(target_len, dtype="float32")
    out = _fit_to_window(exact)
    assert len(out) == target_len
    assert np.array_equal(out, exact)


# ------------------------------------------------------------------- sigmoid
class _FakeOutput:
    """Minimal stand-in for what session.run(...)[0] looks like: a numpy
    array shaped like the model's ['batch'] logits output."""

    def __init__(self, value):
        self._arr = np.array([value], dtype="float32")

    def reshape(self, *shape):
        return self._arr.reshape(*shape)


class _FakeInput:
    name = "input_values"


class _FakeSession:
    """Stub onnxruntime.InferenceSession: records the fed array and returns a
    fixed raw logit, so score()'s sigmoid + windowing logic can be tested
    without a real model."""

    def __init__(self, logit):
        self._logit = logit
        self.last_fed = None

    def get_inputs(self):
        return [_FakeInput()]

    def run(self, output_names, feed):
        self.last_fed = feed["input_values"]
        return [_FakeOutput(self._logit)]


def _scorer_with_fake_session(logit):
    scorer = OnnxAudioScorer(model_path=config.AUDIO_MODEL_PATH)
    scorer._session = _FakeSession(logit)
    return scorer


def test_score_applies_sigmoid_zero_logit_is_half():
    scorer = _scorer_with_fake_session(0.0)
    waveform = np.zeros(int(config.AUDIO_MAX_SECONDS * config.AUDIO_SAMPLE_RATE), dtype="float32")
    score = scorer.score(waveform)
    assert score == pytest.approx(0.5, abs=1e-6)


def test_score_applies_sigmoid_large_positive_logit_is_near_one():
    scorer = _scorer_with_fake_session(10.0)
    waveform = np.zeros(int(config.AUDIO_MAX_SECONDS * config.AUDIO_SAMPLE_RATE), dtype="float32")
    score = scorer.score(waveform)
    expected = 1.0 / (1.0 + math.exp(-10.0))
    assert score == pytest.approx(expected, abs=1e-6)
    assert score > 0.999


def test_score_applies_sigmoid_large_negative_logit_is_near_zero():
    scorer = _scorer_with_fake_session(-10.0)
    waveform = np.zeros(int(config.AUDIO_MAX_SECONDS * config.AUDIO_SAMPLE_RATE), dtype="float32")
    score = scorer.score(waveform)
    assert score < 0.001


def test_score_feeds_a_fixed_window_with_batch_dim_to_the_session():
    scorer = _scorer_with_fake_session(0.0)
    fake_session = scorer._session
    target_len = int(config.AUDIO_MAX_SECONDS * config.AUDIO_SAMPLE_RATE)

    # shorter than the window -> gets padded before being fed to the session
    short = np.ones(1000, dtype="float32")
    scorer.score(short)
    fed = fake_session.last_fed
    assert fed.shape == (1, target_len)

    # longer than the window -> gets center-cropped before being fed
    long_wave = np.ones(target_len * 3, dtype="float32")
    scorer.score(long_wave)
    fed = fake_session.last_fed
    assert fed.shape == (1, target_len)


def test_score_returns_none_when_not_loaded():
    scorer = OnnxAudioScorer(model_path=config.AUDIO_MODEL_PATH)
    scorer._session = None
    assert scorer.score(np.zeros(16000, dtype="float32")) is None


def test_score_returns_none_for_none_waveform():
    scorer = _scorer_with_fake_session(5.0)
    assert scorer.score(None) is None


def test_score_returns_none_on_session_failure():
    class _RaisingSession(_FakeSession):
        def run(self, output_names, feed):
            raise RuntimeError("boom")

    scorer = OnnxAudioScorer(model_path=config.AUDIO_MODEL_PATH)
    scorer._session = _RaisingSession(0.0)
    assert scorer.score(np.zeros(16000, dtype="float32")) is None


# ------------------------------------------------------------- real model
@pytest.mark.skipif(not REAL_MODEL_AVAILABLE, reason="models/kavach_audio.onnx or onnxruntime not present")
def test_real_model_scores_padded_and_cropped_waveforms_in_range():
    reset_audio_scorer()
    scorer = get_audio_scorer()
    assert scorer.is_loaded

    rng = np.random.default_rng(0)
    short_wave = (rng.standard_normal(16000 * 2) * 0.01).astype("float32")  # needs padding
    long_wave = (rng.standard_normal(16000 * 6) * 0.01).astype("float32")  # needs cropping

    short_score = scorer.score(short_wave)
    long_score = scorer.score(long_wave)

    assert short_score is not None
    assert long_score is not None
    assert 0.0 <= short_score <= 1.0
    assert 0.0 <= long_score <= 1.0


@pytest.mark.skipif(not REAL_MODEL_AVAILABLE, reason="models/kavach_audio.onnx or onnxruntime not present")
def test_get_audio_scorer_singleton_is_loaded():
    reset_audio_scorer()
    scorer = get_audio_scorer()
    assert scorer.is_loaded
    assert get_audio_scorer() is scorer  # singleton
