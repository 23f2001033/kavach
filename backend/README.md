# Kavach backend

FastAPI inference service: signature rule engine, text scam-likelihood scorer,
fusion + hysteresis, and a rule-based (optionally LLM-polished) explainer.

**Design principle:** the core detection path works fully offline. No external
API is required — the TF-IDF+LogisticRegression text model and the regex
signature engine run entirely locally, and the explainer's rule-based composer
always works. An LLM (Gemini) can *optionally* polish the wording of the
explanation if `GEMINI_API_KEY` is set in the environment; on any failure
(missing key, no network, timeout, bad response) it silently falls back to the
rule-based text. Detection/risk scoring never depends on the LLM at all.

## Run it

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The text model is loaded from `../models/text_baseline.joblib` (produced by
`training/text/train_baseline.py`). If it's missing, the service still starts:
`/health` reports `models.text: false`, `text_score` in responses is `null`,
and risk falls back to signature-only detection — it never crashes.

## Endpoints

### `GET /health`
```json
{"status": "ok", "models": {"text": true, "audio": false}}
```

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

- **Text model** (`kavach/text_model.py`): loads `models/text_baseline.joblib`,
  which `training/text/train_baseline.py` saves as
  `{"vectorizer": FeatureUnion, "clf": LogisticRegression, "best_C": float}` —
  **not** a single sklearn `Pipeline`. `TfidfLogRegScorer` handles that shape
  directly (and falls back to treating the artifact as a plain
  `predict_proba`-capable estimator/Pipeline if a future export changes
  shape). `BaseTextScorer` is a small ABC so a future ONNX DistilBERT model
  can be dropped in as a second implementation without touching callers.

- **Audio model** (`kavach/audio_model.py`): stub interface for the
  voice-deepfake ONNX model being trained separately. `onnxruntime` is
  import-guarded and intentionally **not** in `requirements.txt` yet; without
  it (or without `models/kavach_audio.onnx`), `.score()` always returns
  `None` and fusion degrades gracefully.

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
