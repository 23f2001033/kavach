# Kavach — Build Plan (July 11 → July 30, 2026)

Deadline: **July 30, 2026, 9:00 PM PDT** (July 31, 9:30 AM IST). Judging: Technical 30% ·
Creativity 20% · Impact 20% · UX 15% · Presentation 15%.

## Architecture

```
                 ┌─────────────────────────── Browser (PWA) ───────────────────────────┐
 mic / upload ──►│ audio chunks ──► WebSocket ──► risk meter · live transcript · alerts │
                 └──────────────────────────────────────────────────────────────────────┘
                                        │
                 ┌──────────────────── FastAPI backend ─────────────────────┐
                 │ faster-whisper (streaming ASR)                           │
                 │ ┌──────────────┐  ┌───────────────────┐  ┌─────────────┐ │
                 │ │ Voice        │  │ Social-engineering │  │ Signature   │ │
                 │ │ forensics    │  │ text classifier    │  │ matcher     │ │
                 │ │ (wav2vec2 →  │  │ (DistilBERT-class  │  │ (rules +    │ │
                 │ │  ONNX)       │  │  → ONNX)           │  │  retrieval) │ │
                 │ └──────┬───────┘  └─────────┬─────────┘  └──────┬──────┘ │
                 │        └──────────── fusion & calibration ──────┘        │
                 │                     │                                    │
                 │        explainer / verifier agents (LLM optional)        │
                 └──────────────────────────────────────────────────────────┘
```

- Core path is fully local/offline (ONNX Runtime, CPU). LLM (free-tier Gemini/Groq, pluggable)
  only enriches explanations; a rule-based explainer is the always-works fallback.
- Fusion: per-window scores → calibrated logistic fusion → hysteresis so the risk meter is
  stable, with per-signal attribution for explainability.

## Phases

### Phase 1 — Data (Jul 11–14) ✅ done Jul 11
- [x] Text corpus: BothBosu scam-conversation family (incl. 20 real YouTube calls held out);
      normalized unified JSONL schema; dedup; stratified splits (4,983/623/623).
      (FredZhang7/all-scam-spam skipped — email/SMS domain mismatch for call transcripts.)
- [x] India-specific synthetic scripts (digital arrest, fake KYC, UPI refund, courier customs,
      KBC lottery, army-OLX, loan-app, investment) + matched legitimate counterparts.
- [x] Audio: training script discovers ASVspoof 2019 LA + In-the-Wild on Kaggle mounts
      (2021 DF dropped — eval-only set, 34 GB; In-the-Wild is the cross-dataset eval).

### Phase 2 — Models (Jul 15–19) — scripts ready Jul 11, training runs pending
- [x] TF-IDF + LogReg baseline trained locally (honest finding: 12/20 on real calls).
- [x] Voice forensics training script: wav2vec2-base on ASVspoof19-LA, cross-eval In-the-Wild,
      ONNX export; smoke-tested end-to-end on CPU. → RUN ON KAGGLE (training/audio/KAGGLE.md)
- [x] Text classifier script: DistilBERT, sliding-window option, ONNX export.
      → RUN ON KAGGLE (training/text/KAGGLE.md)
- [ ] Drop trained artifacts into models/, integrate DistilBERT + audio ONNX scorers, re-run evals.

### Phase 3 — Product (Jul 20–24) — largely done Jul 11
- [x] FastAPI backend: /analyze/text, /analyze/window (rolling sessions + hysteresis),
      signature KB (12+ India-specific signatures), noisy-OR fusion, rule-based explainer
      (optional LLM polish behind env var). 41 tests.
- [x] Frontend: live mic via Web Speech API (en-IN/hi-IN), animated SVG risk gauge, one-time
      voice alerts, signature cards, elderly mode, example transcripts.
- [~] Recording upload + faster-whisper transcription (in progress).
- [ ] Verifier agent (claim extraction → KB lookup) — optional stretch, only if time allows.

### Phase 4 — Rigor (Jul 25–27) — started early, ongoing
- [x] Eval suite: 30 fresh scenarios (15 scam / 15 benign, Hinglish included) + 20 real calls,
      3-config comparison, latency (5 ms median). Caught + fixed fusion dilution bug.
- [ ] Cross-dataset audio report (after Kaggle run); re-run text evals with DistilBERT.
- [ ] Threshold calibration once DistilBERT lands (baseline is poorly calibrated near 0.5).

### Phase 5 — Submission (Jul 28–30)
- [ ] 2–3 min demo video: live cloned-voice call gets flagged mid-sentence.
- [ ] Devpost writeup, screenshots, architecture diagram. Submit **early** on Jul 29.

## Prize categories targeted
Best Overall · Most Impactful · Best Use of ML · Conversational AI · Best Web AI App · Data-Driven Insights
