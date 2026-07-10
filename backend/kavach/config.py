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

# --- optional LLM explainer polish -------------------------------------------
# Core detection/explanation NEVER depends on this (see README design principle).
ENV_GEMINI_API_KEY = "GEMINI_API_KEY"
GEMINI_API_KEY = os.environ.get(ENV_GEMINI_API_KEY)
GEMINI_MODEL_NAME = os.environ.get("KAVACH_GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_TIMEOUT_SECONDS = float(os.environ.get("KAVACH_GEMINI_TIMEOUT_SECONDS", "4.0"))

# --- fusion weights ------------------------------------------------------------
# risk_score = weighted average of whichever of {text, signature, audio} scores
# are actually available (None-signals are dropped and the rest renormalized —
# see kavach/fusion.py). Signature score is always available (0 if no hits).
FUSION_WEIGHTS = {
    "text": float(os.environ.get("KAVACH_W_TEXT", "0.5")),
    "signature": float(os.environ.get("KAVACH_W_SIGNATURE", "0.35")),
    "audio": float(os.environ.get("KAVACH_W_AUDIO", "0.15")),
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

# --- CORS ----------------------------------------------------------------------
CORS_ALLOW_ORIGINS = ["*"]
