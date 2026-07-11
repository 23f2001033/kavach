"""Interface stub for the voice-deepfake ONNX model (trained separately, see
training/audio/...). `onnxruntime` is intentionally NOT a hard dependency of
this backend yet — it's import-guarded here and kept out of requirements.txt
until the audio phase lands, so the service installs and runs fully without
it. When models/kavach_audio.onnx exists AND onnxruntime is installed,
OnnxAudioScorer loads it; otherwise .score() always returns None and the
fusion layer degrades gracefully (see kavach/fusion.py).

`load_waveform_16k()` below decodes an uploaded recording (any container
POST /analyze/recording accepts) into the 16 kHz mono float32 waveform this
scorer expects, for the recording-upload path in kavach/api.py. `soundfile`
and `scipy` are also import-guarded and NOT in requirements.txt — same spirit
as onnxruntime: without them (or without ffmpeg on PATH for containers
libsndfile can't read directly, e.g. mp3/m4a/webm), waveform loading simply
returns None and audio_score degrades to null, same as no model at all.
"""
import logging
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from shutil import which
from typing import Optional

from . import config

logger = logging.getLogger("kavach.audio_model")

try:
    import onnxruntime as ort  # type: ignore
except ImportError:  # pragma: no cover - exercised whenever onnxruntime isn't installed
    ort = None

try:
    import numpy as np  # type: ignore
except ImportError:  # pragma: no cover
    np = None

try:
    import soundfile as sf  # type: ignore
except ImportError:  # pragma: no cover - exercised whenever soundfile isn't installed
    sf = None


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


def _resample(data, src_sr: int, target_sr: int):
    """Resample a 1-D float32 array from src_sr to target_sr. Prefers
    scipy.signal.resample_poly (polyphase, good quality); falls back to plain
    numpy linear interpolation if scipy isn't installed, which is good enough
    for a deepfake-detector's input -- this is not an audio-quality product."""
    if src_sr == target_sr:
        return data
    try:
        from math import gcd

        from scipy.signal import resample_poly  # type: ignore

        g = gcd(src_sr, target_sr)
        return resample_poly(data, target_sr // g, src_sr // g).astype("float32")
    except ImportError:
        # No scipy: cheap linear-interpolation resample.
        duration = len(data) / float(src_sr)
        n_target = int(round(duration * target_sr))
        src_x = np.linspace(0.0, duration, num=len(data), endpoint=False)
        dst_x = np.linspace(0.0, duration, num=n_target, endpoint=False)
        return np.interp(dst_x, src_x, data).astype("float32")


def load_waveform_16k(path, target_sr: int = 16000) -> Optional["np.ndarray"]:
    """Decode an uploaded recording at `path` into a 16 kHz mono float32
    waveform for OnnxAudioScorer.score(). Returns None (never raises) if
    numpy/soundfile aren't installed, or if the file can't be decoded --
    callers should treat that exactly like "no audio model": audio_score
    stays null.

    libsndfile (via soundfile) reads wav/flac/ogg directly. For containers it
    can't read (mp3/m4a/webm), we shell out to ffmpeg -- already required for
    this project -- to transcode to a temp 16 kHz mono wav first.
    """
    if np is None or sf is None:
        logger.info("[kavach.audio_model] numpy/soundfile not installed; audio waveform decode disabled.")
        return None

    def _read(p) -> Optional[tuple]:
        try:
            data, sr = sf.read(str(p), dtype="float32", always_2d=False)
            return data, sr
        except Exception:
            return None

    result = _read(path)
    if result is None:
        if which("ffmpeg") is None:
            logger.warning("[kavach.audio_model] soundfile couldn't decode '%s' and ffmpeg isn't on PATH.", path)
            return None
        tmp_wav = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_wav = tmp.name
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(path), "-ar", str(target_sr), "-ac", "1", tmp_wav],
                check=True, capture_output=True, timeout=60,
            )
            result = _read(tmp_wav)
        except Exception as exc:
            logger.warning(f"[kavach.audio_model] ffmpeg transcode of '{path}' failed: {exc}")
            result = None
        finally:
            if tmp_wav is not None:
                Path(tmp_wav).unlink(missing_ok=True)
        if result is None:
            return None

    data, sr = result
    data = np.asarray(data, dtype="float32")
    if data.ndim > 1:
        data = data.mean(axis=1).astype("float32")
    if sr != target_sr:
        data = _resample(data, sr, target_sr)
    return data
