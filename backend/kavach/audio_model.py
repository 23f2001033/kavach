"""Interface stub for the voice-deepfake ONNX model (trained separately, see
training/audio/...). `onnxruntime` is intentionally NOT a hard dependency of
this backend yet — it's import-guarded here and kept out of requirements.txt
until the audio phase lands, so the service installs and runs fully without
it. When models/kavach_audio.onnx exists AND onnxruntime is installed,
OnnxAudioScorer loads it; otherwise .score() always returns None and the
fusion layer degrades gracefully (see kavach/fusion.py).
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional

from . import config

logger = logging.getLogger("kavach.audio_model")

try:
    import onnxruntime as ort  # type: ignore
except ImportError:  # pragma: no cover - exercised whenever onnxruntime isn't installed
    ort = None


class BaseAudioScorer(ABC):
    """Interface every audio deepfake-scorer must implement."""

    @abstractmethod
    def score(self, waveform) -> Optional[float]:
        """Return P(synthetic/cloned voice) in [0, 1], or None if unavailable."""

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        ...


class OnnxAudioScorer(BaseAudioScorer):
    def __init__(self, model_path=None):
        self.model_path = model_path or config.AUDIO_MODEL_PATH
        self._session = None
        self._load()

    def _load(self) -> None:
        if ort is None:
            logger.info("[kavach.audio_model] onnxruntime not installed; audio scoring disabled.")
            return
        if not self.model_path.exists():
            logger.info(f"[kavach.audio_model] no audio model at '{self.model_path}'; audio scoring disabled.")
            return
        try:
            self._session = ort.InferenceSession(str(self.model_path))
        except Exception as exc:
            logger.warning(f"[kavach.audio_model] failed to load '{self.model_path}': {exc}")
            self._session = None

    @property
    def is_loaded(self) -> bool:
        return self._session is not None

    def score(self, waveform) -> Optional[float]:
        if not self.is_loaded or waveform is None:
            return None
        try:
            input_name = self._session.get_inputs()[0].name
            outputs = self._session.run(None, {input_name: waveform})
            return float(outputs[0].reshape(-1)[0])
        except Exception as exc:
            logger.warning(f"[kavach.audio_model] scoring failed: {exc}")
            return None


_default_scorer: Optional[BaseAudioScorer] = None


def get_audio_scorer() -> BaseAudioScorer:
    global _default_scorer
    if _default_scorer is None:
        _default_scorer = OnnxAudioScorer()
    return _default_scorer


def reset_audio_scorer() -> None:
    """Test helper: drop the singleton so the next get_audio_scorer() reloads."""
    global _default_scorer
    _default_scorer = None
