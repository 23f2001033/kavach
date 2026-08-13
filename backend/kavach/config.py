"""Central configuration: model paths, fusion weights, thresholds, env-var names.

Everything here is overridable via environment variables so the service can be
tuned without a code change. Defaults are chosen for the v1 stack (TF-IDF +
LogisticRegression text model, regex signature engine, no audio model yet) and
should be revisited once the ONNX text/audio models land.
"""
import os
from pathlib import Path

# --- paths -------------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent

ENV_MODELS_DIR = "KAVACH_MODELS_DIR"
MODELS_DIR = Path(os.environ.get(ENV_MODELS_DIR, str(REPO_ROOT / "models")))

TEXT_MODEL_PATH = MODELS_DIR / "text_baseline.joblib"
AUDIO_MODEL_PATH = MODELS_DIR / "kavach_audio.onnx"

# Fine-tuned DistilBERT text scorer (training/text/train_transformer.py). When
# this directory exists (config.json + model.safetensors + tokenizer files),
# it is preferred over the TF-IDF+LogReg baseline -- see
# kavach/text_model.py::get_text_scorer(). Not committed to git (see
# .gitignore); fetched separately from Kaggle training output.
DISTILBERT_MODEL_DIR = MODELS_DIR / "distilbert" / "model"
DISTILBERT_MAX_LENGTH = int(os.environ.get("KAVACH_DISTILBERT_MAX_LENGTH", "512"))
DISTILBERT_WINDOW_SIZE = int(os.environ.get("KAVACH_DISTILBERT_WINDOW_SIZE", "256"))
DISTILBERT_WINDOW_STRIDE = int(os.environ.get("KAVACH_DISTILBERT_WINDOW_STRIDE", "128"))

# --- optional LLM explainer polish -------------------------------------------
# Core detection/explanation NEVER depends on this (see README design principle).
ENV_GEMINI_API_KEY = "GEMINI_API_KEY"
GEMINI_API_KEY = os.environ.get(ENV_GEMINI_API_KEY)
GEMINI_MODEL_NAME = os.environ.get("KAVACH_GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_TIMEOUT_SECONDS = float(os.environ.get("KAVACH_GEMINI_TIMEOUT_SECONDS", "4.0"))

# --- fusion weights ------------------------------------------------------------
# Noisy-OR evidence combination (see kavach/fusion.py):
#   risk_score = 1 - PRODUCT_i (1 - s_i * w_i)
# over whichever of {text, signature, audio} are actually AVAILABLE this
# request. A signal that is None (model not loaded, no audio yet, ...) is
# simply excluded from the product -- there is no renormalization, so an
# absent signal can never dilute the ones that ARE present. Each w_i below is
# a per-signal weight/cap: it discounts how much a single fully-confident
# reading of that channel alone can contribute. text=1.0 means a maximally
# confident text_score alone maps straight through to risk_score (no
# structural ceiling). signature=0.85 discounts the regex engine slightly
# since it is noisier/coarser than a learned score. audio=0.45 is
# deliberately capped BELOW the "high" threshold (0.65, see RISK_THRESHOLDS
# below) but ABOVE the "suspicious" one (0.35): "this voice sounds
# synthetic" is corroborating context, not proof of a scam on its own -- a
# huge fraction of legitimate calls (bank IVR, clinic/delivery reminders,
# OTP-readout robocalls) are synthetic speech too. With audio=0.45, a
# maximally-confident synthetic-voice reading ALONE noisy-ORs straight
# through to risk_score == 0.45 (see fusion.combine: with only one signal
# present, risk_score == that signal's score * its weight), which lands on
# "suspicious" ("this voice sounds artificial -- be careful") and can never
# alone reach "high". Combined with suspicious/scammy content it still
# escalates decisively, e.g. text=0.9 + audio=1.0 -> noisy-OR ==
# 1 - (1-0.9)*(1-0.45) = 0.945 -> "high". Previously this was 0.9, which let
# voice-only readings force "high" regardless of what was actually said --
# see backend/README.md's Fusion section and the regression tests in
# tests/test_fusion.py (test_audio_only_max_confidence_does_not_reach_high /
# test_audio_high_plus_text_high_still_reaches_high) for the bug this fixes.
FUSION_WEIGHTS = {
    "text": float(os.environ.get("KAVACH_W_TEXT", "1.0")),
    "signature": float(os.environ.get("KAVACH_W_SIGNATURE", "0.85")),
    "audio": float(os.environ.get("KAVACH_W_AUDIO", "0.45")),
}

# Per-hit severity -> contribution to the signature sub-score (1=low, 2=medium,
# 3=high), summed then saturated at SIGNATURE_SATURATION so many low-severity
# hits can't out-weigh a couple of high-severity ones indefinitely.
SEVERITY_WEIGHTS = {1: 0.12, 2: 0.22, 3: 0.35}
SIGNATURE_SATURATION = 1.0

# --- risk levels & hysteresis --------------------------------------------------
RISK_THRESHOLDS = {
    "suspicious": float(os.environ.get("KAVACH_T_SUSPICIOUS", "0.35")),
    "high": float(os.environ.get("KAVACH_T_HIGH", "0.65")),
}
# A level change is only accepted once the score crosses the relevant threshold
# by this extra margin, in the direction of travel — keeps the risk meter from
# flickering when the score hovers near a boundary. See kavach/fusion.py.
HYSTERESIS_MARGIN = float(os.environ.get("KAVACH_HYSTERESIS_MARGIN", "0.05"))

# --- /analyze/window session store --------------------------------------------
SESSION_MAX_CHARS = int(os.environ.get("KAVACH_SESSION_MAX_CHARS", "3000"))
SESSION_MAX_COUNT = int(os.environ.get("KAVACH_SESSION_MAX_COUNT", "500"))

# --- speech-to-text (POST /analyze/recording, kavach/transcribe.py) -----------
# faster-whisper (CTranslate2) model config. "small" + int8 CPU is the v1
# default: a reasonable accuracy/latency/RAM tradeoff on CPU-only hardware. The
# very first transcription call downloads the model from Hugging Face Hub and
# caches it locally (~/.cache/huggingface); every call after that is local.
WHISPER_MODEL_SIZE = os.environ.get("KAVACH_WHISPER_MODEL_SIZE", "small")
WHISPER_DEVICE = os.environ.get("KAVACH_WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.environ.get("KAVACH_WHISPER_COMPUTE_TYPE", "int8")

# Recording upload: accepted container formats for POST /analyze/recording.
RECORDING_ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".webm"}

# --- audio deepfake model (kavach/audio_model.py, training/audio/train_audio_deepfake.py) ---
# The ONNX model (models/kavach_audio.onnx) was trained on fixed-length
# AUDIO_MAX_SECONDS windows at AUDIO_SAMPLE_RATE -- random-crop during
# training, center-crop (zero-padded if shorter) at eval time -- and has
# never seen any other input length. OnnxAudioScorer.score() must match that
# eval-time convention exactly (see train_audio_deepfake.py::load_waveform).
AUDIO_MAX_SECONDS = float(os.environ.get("KAVACH_AUDIO_MAX_SECONDS", "4.0"))
AUDIO_SAMPLE_RATE = int(os.environ.get("KAVACH_AUDIO_SAMPLE_RATE", "16000"))

# --- CORS ----------------------------------------------------------------------
CORS_ALLOW_ORIGINS = ["*"]
