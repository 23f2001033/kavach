"""Whisper-based speech-to-text for uploaded call recordings
(POST /analyze/recording in kavach/api.py).

Lazy-loads a faster-whisper (CTranslate2) model on first use, so importing
this module -- and starting the API -- never touches disk/network. The model
size/device/compute-type are configurable via kavach/config.py
(KAVACH_WHISPER_MODEL_SIZE etc). The very first transcription call downloads
the chosen model from Hugging Face Hub and caches it under
~/.cache/huggingface; every call after that runs fully offline.

v1 limitation -- no diarization: faster-whisper returns one continuous
transcript with no speaker labels. The API layer (kavach/api.py) prepends a
single "Caller: " prefix to the whole thing rather than attempting to
separate caller vs. receiver turns -- see backend/README.md.
"""
import logging
from typing import Dict, List, Optional

from . import config

logger = logging.getLogger("kavach.transcribe")

try:
    from faster_whisper import WhisperModel  # type: ignore
except ImportError:  # pragma: no cover - exercised whenever faster-whisper isn't installed
    WhisperModel = None


class TranscriptionUnavailableError(RuntimeError):
    """Raised by transcribe() when faster-whisper isn't installed."""


_default_model: Optional["WhisperModel"] = None


def get_whisper_model():
    """Return the process-wide singleton WhisperModel, loading it (and, on
    first-ever use, downloading it) on demand."""
    global _default_model
    if _default_model is None:
        if WhisperModel is None:
            raise TranscriptionUnavailableError(
                "faster-whisper is not installed; run `pip install -r requirements.txt`."
            )
        logger.info(
            "[kavach.transcribe] loading faster-whisper model '%s' "
            "(device=%s, compute_type=%s) -- first run downloads it.",
            config.WHISPER_MODEL_SIZE, config.WHISPER_DEVICE, config.WHISPER_COMPUTE_TYPE,
        )
        _default_model = WhisperModel(
            config.WHISPER_MODEL_SIZE,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE_TYPE,
        )
    return _default_model


def reset_whisper_model() -> None:
    """Test helper: drop the singleton so the next get_whisper_model() call reloads."""
    global _default_model
    _default_model = None


def transcribe(path: str) -> Dict:
    """Transcribe the audio file at `path` (any container faster-whisper/PyAV
    can decode -- wav/mp3/m4a/ogg/webm/...) into a full transcript + segments.

    Returns:
        {
          "text": str,                # full transcript, whitespace-joined
          "language": str,             # detected language code, e.g. "en"
          "duration_seconds": float,
          "segments": [{"start": float, "end": float, "text": str}, ...],
        }

    Raises TranscriptionUnavailableError if faster-whisper isn't installed.
    """
    model = get_whisper_model()
    segments_iter, info = model.transcribe(path, beam_size=1)

    segments: List[Dict] = []
    text_parts: List[str] = []
    for seg in segments_iter:
        seg_text = seg.text.strip()
        segments.append({"start": float(seg.start), "end": float(seg.end), "text": seg_text})
        if seg_text:
            text_parts.append(seg_text)

    return {
        "text": " ".join(text_parts).strip(),
        "language": info.language,
        "duration_seconds": float(info.duration),
        "segments": segments,
    }
