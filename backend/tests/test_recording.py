"""Tests for POST /analyze/recording (Whisper transcription + text/signature
fusion, kavach/transcribe.py + kavach/api.py).

The end-to-end test synthesizes a real *spoken* WAV using Windows' built-in
System.Speech TTS via PowerShell (no bundled audio fixture needed) and is
marked @pytest.mark.slow because it downloads the faster-whisper model on
first run and does real CPU transcription. It's skipped gracefully wherever
PowerShell/System.Speech TTS or faster-whisper aren't available (e.g. non-
Windows CI), rather than failing the suite.
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kavach import transcribe as transcribe_module
from kavach.api import app
from kavach.audio_model import get_audio_scorer

client = TestClient(app)

AUDIO_MODEL_LOADED = get_audio_scorer().is_loaded

SCAM_LINE = (
    "I am calling from your bank. Your account will be blocked today. "
    "Share the OTP I just sent you immediately."
)

FASTER_WHISPER_AVAILABLE = transcribe_module.WhisperModel is not None


def _synthesize_tts_wav(path: Path) -> bool:
    """Render SCAM_LINE to a real spoken WAV at `path` using Windows'
    System.Speech TTS via PowerShell. Returns False (never raises) if
    PowerShell/TTS isn't available, so the caller can skip gracefully."""
    if sys.platform != "win32" or shutil.which("powershell") is None:
        return False
    script = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.SetOutputToWaveFile('{path}'); "
        f"$s.Speak('{SCAM_LINE}'); "
        "$s.Dispose()"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            check=True,
            capture_output=True,
            timeout=60,
        )
    except Exception:
        return False
    return path.exists() and path.stat().st_size > 0


@pytest.mark.slow
def test_analyze_recording_transcribes_and_flags_scam_wav(tmp_path):
    if not FASTER_WHISPER_AVAILABLE:
        pytest.skip("faster-whisper not installed")

    wav_path = tmp_path / "scam_tts.wav"
    if not _synthesize_tts_wav(wav_path):
        pytest.skip("Windows System.Speech TTS not available on this machine")

    with open(wav_path, "rb") as f:
        resp = client.post(
            "/analyze/recording",
            files={"file": ("scam_tts.wav", f, "audio/wav")},
        )

    assert resp.status_code == 200
    body = resp.json()

    transcript_lower = body["transcript"].lower()
    assert any(kw in transcript_lower for kw in ["otp", "bank", "blocked", "account"]), (
        f"transcript did not contain any expected keyword: {body['transcript']!r}"
    )
    assert body["risk_level"] != "low"
    assert body["duration_seconds"] > 0
    assert body["transcript"].startswith("Caller: ")
    if AUDIO_MODEL_LOADED:
        # models/kavach_audio.onnx + onnxruntime present -> the recording
        # path should fold in a real audio_score (a probability in [0, 1]).
        assert body["audio_score"] is not None
        assert 0.0 <= body["audio_score"] <= 1.0
    else:
        assert body["audio_score"] is None

    print("\n--- Whisper transcript ---")
    print(body["transcript"])
    print("--- Analysis ---")
    print(
        {
            "risk_score": body["risk_score"],
            "risk_level": body["risk_level"],
            "text_score": body["text_score"],
            "language": body["language"],
            "duration_seconds": body["duration_seconds"],
            "audio_score": body["audio_score"],
            "signature_hit_ids": [h["id"] for h in body["signature_hits"]],
        }
    )


def test_analyze_recording_rejects_unsupported_extension(tmp_path):
    bogus = tmp_path / "clip.txt"
    bogus.write_text("not audio")
    with open(bogus, "rb") as f:
        resp = client.post("/analyze/recording", files={"file": ("clip.txt", f, "text/plain")})
    assert resp.status_code == 400
