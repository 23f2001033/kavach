"""FastAPI app: health check, one-shot text analysis, stateful "window"
analysis (rolling per-session transcript, hysteresis-smoothed risk level) for
the live-mic streaming mode, and recording-upload analysis (Whisper
transcription + the same text+signature(+audio) fusion).
"""
import logging
import tempfile
import time
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from typing import Dict, List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import config
from .audio_model import get_audio_scorer, load_waveform_16k
from .explain import build_explanation
from .fusion import HysteresisMeter, combine
from .signatures import match as match_signatures
from .text_model import get_text_scorer
from .transcribe import TranscriptionUnavailableError
from .transcribe import transcribe as transcribe_audio

logger = logging.getLogger("kavach.api")

app = FastAPI(title="Kavach Inference API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ALLOW_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------ schemas
class TextAnalyzeRequest(BaseModel):
    transcript: str = Field(..., min_length=1)


class WindowAnalyzeRequest(BaseModel):
    transcript: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)


class SignatureHitOut(BaseModel):
    id: str
    name: str
    scam_type: str
    severity: int
    explanation: str
    matches: List[str]


class AnalyzeResponse(BaseModel):
    risk_score: float
    risk_level: str
    text_score: Optional[float]
    signature_hits: List[SignatureHitOut]
    explanation: str


class RecordingAnalyzeResponse(AnalyzeResponse):
    transcript: str
    language: Optional[str]
    audio_score: Optional[float]
    duration_seconds: float


# ------------------------------------------------------------------ session store
class _Session:
    __slots__ = ("transcript", "meter", "last_seen")

    def __init__(self):
        self.transcript = ""
        self.meter = HysteresisMeter()
        self.last_seen = time.time()


class SessionStore:
    """In-memory rolling-transcript store, keyed by session_id. Bounded LRU so
    a long-running demo doesn't leak memory; each transcript is truncated to
    the last SESSION_MAX_CHARS characters. Not persisted — a process restart
    clears all sessions, which is fine for a live-call demo."""

    def __init__(self, max_sessions: Optional[int] = None):
        self._sessions: "OrderedDict[str, _Session]" = OrderedDict()
        self._lock = Lock()  # reentrant not needed: append() no longer nests get_or_create()
        self._max_sessions = max_sessions or config.SESSION_MAX_COUNT

    def get_or_create(self, session_id: str) -> _Session:
        with self._lock:
            session = self._sessions.pop(session_id, None)
            if session is None:
                session = _Session()
            self._sessions[session_id] = session  # move to MRU end
            if len(self._sessions) > self._max_sessions:
                self._sessions.popitem(last=False)
            return session

    def append(self, session_id: str, chunk: str) -> str:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                session = self.get_or_create(session_id)
            session.transcript = (session.transcript + " " + chunk).strip()[-config.SESSION_MAX_CHARS:]
            session.last_seen = time.time()
            return session.transcript

    def clear(self) -> None:
        """Test helper."""
        with self._lock:
            self._sessions.clear()


_session_store = SessionStore()


def _analyze(transcript: str, meter: Optional[HysteresisMeter] = None) -> AnalyzeResponse:
    text_scorer = get_text_scorer()
    text_score = text_scorer.score(transcript)

    hits = match_signatures(transcript)
    hits_out = [SignatureHitOut(**h) for h in hits]

    audio_scorer = get_audio_scorer()
    audio_score = audio_scorer.score(None)  # no waveform on the text-only path (yet)

    result = combine(text_score=text_score, signature_hits=hits, audio_score=audio_score)
    risk_level = meter.update(result["risk_score"]) if meter is not None else result["risk_level"]

    explanation = build_explanation(risk_level, hits, text_score, transcript)

    return AnalyzeResponse(
        risk_score=result["risk_score"],
        risk_level=risk_level,
        text_score=text_score,
        signature_hits=hits_out,
        explanation=explanation,
    )


@app.get("/health")
def health() -> Dict:
    text_scorer = get_text_scorer()
    return {
        "status": "ok",
        "models": {
            # Backward-compatible: falsy (False) when nothing loaded, truthy
            # when a scorer loaded -- now the scorer's name ("distilbert" |
            # "baseline") instead of a bare bool, so clients can tell which
            # text model is actually serving traffic.
            "text": text_scorer.name if text_scorer.is_loaded else False,
            "audio": get_audio_scorer().is_loaded,
        },
    }


@app.post("/analyze/text", response_model=AnalyzeResponse)
def analyze_text(req: TextAnalyzeRequest) -> AnalyzeResponse:
    return _analyze(req.transcript)


@app.post("/analyze/window", response_model=AnalyzeResponse)
def analyze_window(req: WindowAnalyzeRequest) -> AnalyzeResponse:
    session = _session_store.get_or_create(req.session_id)
    rolling_transcript = _session_store.append(req.session_id, req.transcript)
    return _analyze(rolling_transcript, meter=session.meter)


@app.post("/analyze/recording", response_model=RecordingAnalyzeResponse)
async def analyze_recording(file: UploadFile = File(...)) -> RecordingAnalyzeResponse:
    """Analyze an uploaded call recording: transcribe with Whisper, prepend a
    single "Caller: " speaker label (v1 has no diarization — see
    backend/README.md), run the standard text+signature fusion, and fold in
    the audio deepfake score too if models/kavach_audio.onnx is present.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in config.RECORDING_ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(config.RECORDING_ALLOWED_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{suffix}'. Allowed: {allowed}")

    tmp_path: Optional[Path] = None
    try:
        content = await file.read()
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            transcription = transcribe_audio(str(tmp_path))
        except TranscriptionUnavailableError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        transcript = f"Caller: {transcription['text']}".strip()

        text_scorer = get_text_scorer()
        text_score = text_scorer.score(transcript)

        hits = match_signatures(transcript)
        hits_out = [SignatureHitOut(**h) for h in hits]

        audio_scorer = get_audio_scorer()
        audio_score = None
        if audio_scorer.is_loaded:
            waveform = load_waveform_16k(tmp_path)
            if waveform is not None:
                audio_score = audio_scorer.score(waveform)

        result = combine(text_score=text_score, signature_hits=hits, audio_score=audio_score)
        risk_level = result["risk_level"]
        explanation = build_explanation(risk_level, hits, text_score, transcript)

        return RecordingAnalyzeResponse(
            risk_score=result["risk_score"],
            risk_level=risk_level,
            text_score=text_score,
            signature_hits=hits_out,
            explanation=explanation,
            transcript=transcript,
            language=transcription["language"],
            audio_score=audio_score,
            duration_seconds=transcription["duration_seconds"],
        )
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)
