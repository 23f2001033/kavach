"""API tests via FastAPI's TestClient. The /analyze/text end-to-end test uses
the real joblib model at models/text_baseline.joblib when present, and is
skipped otherwise (e.g. a fresh checkout before training/text/train_baseline.py
has been run) so the suite still passes offline/CI without the (gitignored)
model artifact.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from kavach import config
from kavach.api import app, _session_store
from kavach.audio_model import get_audio_scorer
from kavach.text_model import get_text_scorer

client = TestClient(app)

MODEL_PRESENT = config.TEXT_MODEL_PATH.exists() or config.DISTILBERT_MODEL_DIR.exists()
EXPECTED_TEXT_SCORER_NAME = get_text_scorer().name if get_text_scorer().is_loaded else False
EXPECTED_AUDIO_LOADED = get_audio_scorer().is_loaded

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
    _session_store.clear()


# ------------------------------------------------------------------- /health
def test_health_reports_model_status():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    # Backward-compatible: truthy iff a text scorer loaded, exact name otherwise
    # ("distilbert" preferred, "baseline" fallback, False if neither is present).
    assert bool(body["models"]["text"]) is MODEL_PRESENT
    assert body["models"]["text"] == EXPECTED_TEXT_SCORER_NAME
    # True iff models/kavach_audio.onnx + onnxruntime are both present -- see
    # OnnxAudioScorer._load()'s graceful degradation in kavach/audio_model.py.
    assert body["models"]["audio"] is EXPECTED_AUDIO_LOADED


# --------------------------------------------------------------- /analyze/text
def test_analyze_text_digital_arrest_is_flagged_high_risk():
    resp = client.post("/analyze/text", json={"transcript": DIGITAL_ARREST_TRANSCRIPT})
    assert resp.status_code == 200
    body = resp.json()
    assert body["risk_level"] == "high"
    assert body["risk_score"] >= config.RISK_THRESHOLDS["high"]
    hit_ids = {h["id"] for h in body["signature_hits"]}
    assert "digital_arrest_or_warrant_threat" in hit_ids
    assert "otp_pin_cvv_request" in hit_ids
    assert "secrecy_demand" in hit_ids
    assert body["explanation"]  # non-empty, human-readable


def test_analyze_text_benign_delivery_is_not_high_risk():
    resp = client.post("/analyze/text", json={"transcript": BENIGN_DELIVERY_TRANSCRIPT})
    assert resp.status_code == 200
    body = resp.json()
    assert body["risk_level"] != "high"


def test_analyze_text_rejects_empty_transcript():
    resp = client.post("/analyze/text", json={"transcript": ""})
    assert resp.status_code == 422  # pydantic min_length validation


@pytest.mark.skipif(not MODEL_PRESENT, reason="models/text_baseline.joblib not present")
def test_analyze_text_uses_real_model_and_separates_scam_from_benign():
    """End-to-end with the real TF-IDF+LogReg baseline: a digital-arrest scam
    transcript should score meaningfully higher than a benign delivery call."""
    scam_resp = client.post("/analyze/text", json={"transcript": DIGITAL_ARREST_TRANSCRIPT}).json()
    benign_resp = client.post("/analyze/text", json={"transcript": BENIGN_DELIVERY_TRANSCRIPT}).json()

    assert scam_resp["text_score"] is not None
    assert benign_resp["text_score"] is not None
    assert scam_resp["text_score"] > benign_resp["text_score"]
    assert scam_resp["risk_score"] > benign_resp["risk_score"]
    assert scam_resp["risk_level"] == "high"
    assert benign_resp["risk_level"] in ("low", "suspicious")


# ------------------------------------------------------------- /analyze/window
def test_analyze_window_accumulates_rolling_transcript():
    session_id = str(uuid.uuid4())
    r1 = client.post(
        "/analyze/window",
        json={"transcript": "Caller: Hello, this is your bank calling about your account.", "session_id": session_id},
    ).json()
    assert r1["risk_level"] in ("low", "suspicious", "high")

    r2 = client.post(
        "/analyze/window",
        json={"transcript": "Please share your OTP and PIN immediately, do not tell your family.", "session_id": session_id},
    ).json()
    hit_ids = {h["id"] for h in r2["signature_hits"]}
    assert "otp_pin_cvv_request" in hit_ids
    assert "secrecy_demand" in hit_ids
    # Risk should escalate once scam signals arrive in the rolling window.
    assert r2["risk_score"] >= r1["risk_score"]


def test_analyze_window_sessions_are_isolated():
    s1, s2 = str(uuid.uuid4()), str(uuid.uuid4())
    client.post("/analyze/window", json={"transcript": "digital arrest, share your otp now", "session_id": s1})
    r2 = client.post(
        "/analyze/window",
        json={"transcript": "Hello, just calling to confirm your appointment tomorrow.", "session_id": s2},
    ).json()
    hit_ids = {h["id"] for h in r2["signature_hits"]}
    assert "digital_arrest_or_warrant_threat" not in hit_ids
    assert "otp_pin_cvv_request" not in hit_ids


def test_analyze_window_hysteresis_holds_level_on_small_dips():
    """Once a session's risk meter climbs to 'high' on a strong scam window, a
    single mildly-worded follow-up turn shouldn't instantly snap it back down."""
    session_id = str(uuid.uuid4())
    client.post("/analyze/window", json={"transcript": DIGITAL_ARREST_TRANSCRIPT, "session_id": session_id})
    r2 = client.post(
        "/analyze/window",
        json={"transcript": "Okay sir, I understand.", "session_id": session_id},
    ).json()
    # The rolling transcript still contains the full scam script, so risk should
    # remain elevated (hysteresis + rolling window both work in the caller's favor here).
    assert r2["risk_level"] in ("suspicious", "high")
