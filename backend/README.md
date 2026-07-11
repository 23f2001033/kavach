# Kavach backend

FastAPI inference service: signature rule engine, text scam-likelihood scorer,
fusion + hysteresis, and a rule-based (optionally LLM-polished) explainer.

**Design principle:** the core detection path works fully offline. No external
API is required — the text model(s) and the regex signature engine run
entirely locally, and the explainer's rule-based composer always works. An LLM
(Gemini) can *optionally* polish the wording of the explanation if
`GEMINI_API_KEY` is set in the environment; on any failure (missing key, no
network, timeout, bad response) it silently falls back to the rule-based text.
Detection/risk scoring never depends on the LLM at all.

## Run it

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The text scorer prefers the fine-tuned DistilBERT model at
`../models/distilbert/model` (produced by `training/text/train_transformer.py`,
fetched separately — see "Text model" below) and falls back to
`../models/text_baseline.joblib` (produced by `training/text/train_baseline.py`)
if that directory doesn't exist. If neither is present, the service still
starts: `/health` reports `models.text: false`, `text_score` in responses is
`null`, and risk falls back to signature-only detection — it never crashes.

## Endpoints

### `GET /health`
```json
{"status": "ok", "models": {"text": "distilbert", "audio": false}}
```
`models.text` is `"distilbert"` or `"baseline"` depending on which text
scorer loaded, or `false` if neither did (still truthy in the "some model
loaded" case, for backward compatibility with clients checking for truthiness
rather than an exact string).

### `POST /analyze/text`
One-shot analysis of a full transcript (speakers as `"Caller: ... Receiver: ..."`).

Request:
```json
{"transcript": "Caller: You are now under digital arrest. Share your OTP..."}
```

Response:
```json
{
  "risk_score": 0.82,
  "risk_level": "high",
  "text_score": 0.91,
  "signature_hits": [
    {
      "id": "digital_arrest_or_warrant_threat",
      "name": "\"Digital arrest\" / warrant threat",
      "scam_type": "govt_impersonation",
      "severity": 3,
      "explanation": "The caller claimed police/court authority ...",
      "matches": ["... under digital arrest ..."]
    }
  ],
  "explanation": "This call shows strong scam signs. It shows 3 scam signs:\n- ..."
}
```

### `POST /analyze/window`
Stateful variant for the future live-mic mode. Appends `transcript` to an
in-memory rolling buffer keyed by `session_id` (kept to the last ~3000 chars),
re-scores the full rolling window, and applies **hysteresis** so the risk
level doesn't flicker between calls to this endpoint (see Design notes).

Request:
```json
{"transcript": "next chunk of live transcript...", "session_id": "call-abc123"}
```

Response shape is identical to `/analyze/text`. Sessions are in-memory only
(bounded LRU, ~500 sessions) — a process restart clears them, which is fine
for a live-call demo but means this is not a durable store.

### `POST /analyze/recording`
Multipart file upload of a recorded call (`wav`, `mp3`, `m4a`, `ogg`, or
`webm`). Saves the upload to a temp file, transcribes it locally with
faster-whisper (`kavach/transcribe.py`), prepends a single `"Caller: "` label
to the transcript, then runs it through the same text+signature fusion as
`/analyze/text` — and additionally folds in the audio deepfake score if
`models/kavach_audio.onnx` is present (see "Audio model" below).

Request: `multipart/form-data` with one field, `file`.

Response — everything from `/analyze/text` plus:
```json
{
  "risk_score": 0.78,
  "risk_level": "high",
  "text_score": 0.58,
  "signature_hits": [...],
  "explanation": "...",
  "transcript": "Caller: I am calling from your bank. Your account will be blocked today. Share the OTP I just sent you immediately.",
  "language": "en",
  "audio_score": null,
  "duration_seconds": 8.15
}
```

**v1 limitation — no diarization.** faster-whisper returns one continuous
transcript with no speaker separation; the whole thing gets a single
`"Caller: "` prefix rather than distinguishing caller vs. receiver turns like
the hand-written example transcripts elsewhere in this doc. A future version
could add pyannote-style diarization to split turns properly.

The first call to this endpoint in a process's lifetime downloads the
faster-whisper model (`small`, int8, CPU) from Hugging Face Hub — ~464 MB —
and caches it locally; every call after that (in any process, since the
cache is on disk) is fully offline. Model size/device/compute-type are
configurable via `KAVACH_WHISPER_MODEL_SIZE` / `KAVACH_WHISPER_DEVICE` /
`KAVACH_WHISPER_COMPUTE_TYPE` (see `kavach/config.py`). Observed CPU latency
for an 8-second clip with the default "small"/int8 config: ~2s one-time model
load (once cached) + ~6.4s transcription — i.e. faster than real-time on a
typical CPU, but not instant; the endpoint is synchronous.

Unsupported file extensions get `400`; if faster-whisper somehow isn't
installed, the endpoint returns `503` instead of crashing.

## Design notes

- **Signature engine** (`kavach/signatures.py`): a data-driven knowledge base
  of 12 regex-based scam signatures (OTP/PIN/CVV requests, digital-arrest /
  warrant threats, remote-access app requests, UPI collect-request/QR tricks,
  secrecy demands, urgency deadlines, prize/lottery fees, KYC-expiry threats,
  safe-account/RBI transfers, loan-app photo threats, army/CRPF marketplace
  claims, guaranteed-return investment claims). Each hit carries a
  plain-language explanation and matched snippets.

  **Known hard case:** a legitimate bank reminder that says "we never ask for
  your OTP" *mentions* OTP but isn't a request. The OTP signature only fires
  on an imperative request verb (share/tell/read/give/send/confirm/provide)
  next to the term, so that phrasing doesn't match — see the docstring in
  `signatures.py` and `test_signatures.py::test_benign_bank_reminder_with_otp_safety_warning_does_not_flag_otp`.
  This is a v1 regex heuristic, not a semantic understanding of negation — an
  adversarial phrasing that mimics a safety warning while sneaking in a real
  request could still slip past it; closing that gap fully needs the learned
  classifier, not more regex. The fusion layer is tuned so no single signature
  hit can push a benign call to "high" on its own.

- **Text model** (`kavach/text_model.py`): `BaseTextScorer` is a small ABC with
  two implementations, selected by `get_text_scorer()`:
  - `DistilBertScorer` (preferred): loads the fine-tuned
    distilbert-base-uncased classifier from `models/distilbert/model`
    (`config.json` + `model.safetensors` + tokenizer files), produced by
    `training/text/train_transformer.py --windowed` and fetched separately
    from Kaggle (not committed — see `.gitignore`). Trained metrics
    (`models/distilbert/transformer_metrics.json`, also gitignored): 99.8%
    test accuracy; 17/20 real held-out YouTube scam calls caught at threshold
    0.5 with very confident probabilities (~0.999), vs. the TF-IDF baseline's
    12/20. Transcripts whose full token encoding fits in 512 tokens are
    scored in one pass; longer ones are split into overlapping 256-token
    windows (stride 128, matching training) and the MAX window P(scam) is
    returned, so a scam signal anywhere in a long call drives the score.
    Import-guarded (`torch`/`transformers`) and directory-guarded like the
    audio model — missing either just disables it and falls through to the
    baseline.
  - `TfidfLogRegScorer` (fallback): loads `models/text_baseline.joblib`,
    which `training/text/train_baseline.py` saves as
    `{"vectorizer": FeatureUnion, "clf": LogisticRegression, "best_C": float}`
    — **not** a single sklearn `Pipeline`. `TfidfLogRegScorer` handles that
    shape directly (and falls back to treating the artifact as a plain
    `predict_proba`-capable estimator/Pipeline if a future export changes
    shape).

  Both degrade gracefully to `score() -> None` / `is_loaded == False` if
  their artifact is missing or fails to load — the rest of the service
  (signatures + fusion) keeps working either way.

- **Audio model** (`kavach/audio_model.py`): stub interface for the
  voice-deepfake ONNX model being trained separately. `onnxruntime` is
  import-guarded and intentionally **not** in `requirements.txt` yet; without
  it (or without `models/kavach_audio.onnx`), `.score()` always returns
  `None` and fusion degrades gracefully. `load_waveform_16k()` in the same
  module decodes an uploaded recording (any format `/analyze/recording`
  accepts) into the 16 kHz mono float32 waveform the scorer expects —
  `soundfile`/`scipy` are also import-guarded (not in `requirements.txt`),
  and containers `soundfile` can't read directly (mp3/m4a/webm) fall back to
  an `ffmpeg` transcode. Any failure anywhere in that chain (missing
  package, missing ffmpeg, bad file) just returns `None`, same as "no audio
  model at all" — `/analyze/recording`'s `audio_score` is `null` either way.

- **Transcription** (`kavach/transcribe.py`): lazy-loads a faster-whisper
  (CTranslate2) model on first use — importing the module never touches
  disk/network. `faster-whisper` **is** a hard dependency (unlike
  `onnxruntime`) since `/analyze/recording` needs it to function at all.

- **Fusion** (`kavach/fusion.py`): `risk_score` is a **noisy-OR** combination
  of whichever of {text, signature, audio} are available —
  `risk_score = 1 - PRODUCT(1 - s_i * w_i)` over the signals present this
  request. A `None` signal is simply excluded from the product (no
  renormalization), so a missing model never crashes the service, never
  zeroes out risk, and — critically — never *dilutes* the signals that ARE
  present. With `text` weighted at 1.0, a text-only reading maps straight
  through (`risk_score == text_score`) and can reach "high" on its own; each
  additional nonzero signal (signature hits, audio) can only push
  `risk_score` up further, never down. (An earlier weighted-average
  combiner renormalized over active weights, which meant an always-active
  0.0 signature sub-score capped every text-only reading at ~0.588 — see
  `evals/REPORT.md` for the full writeup of that bug and the fix.) The
  signature sub-score is a severity-weighted sum of hits, saturating at 1.0
  so many low-severity hits can't run away unboundedly. `HysteresisMeter` is
  a small stateful class (one per session in `/analyze/window`) that only
  changes level once a score clears the threshold **plus a margin**, in the
  direction of travel — this is what stops the on-screen risk meter
  flickering near a boundary.

- **Explainer** (`kavach/explain.py`): rule-based composer is authoritative;
  it lists the plain-language explanation of each matched signature, ordered
  by severity. The optional LLM step (`google-generativeai`, imported lazily)
  only rewords that already-correct text for a non-technical reader — the
  prompt explicitly forbids inventing new facts — and any error is swallowed
  with a fallback to the rule-based text.

## Tests

```bash
cd backend
pytest -v
```

`tests/test_api.py::test_analyze_text_uses_real_model_and_separates_scam_from_benign`
exercises the real joblib model end-to-end and is skipped automatically if
`models/text_baseline.joblib` isn't present (e.g. before running
`training/text/train_baseline.py`).

`tests/test_recording.py::test_analyze_recording_transcribes_and_flags_scam_wav`
is marked `@pytest.mark.slow` (real Whisper transcription, downloads the
model on first run). It synthesizes its own fixture — a real spoken WAV
generated via Windows' built-in `System.Speech` TTS through PowerShell — so
no binary audio fixture is checked into the repo. It skips gracefully
(instead of failing) if `faster-whisper` isn't installed or PowerShell/TTS
isn't available (e.g. non-Windows CI).
