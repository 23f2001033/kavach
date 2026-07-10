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

### Phase 1 — Data (Jul 11–14)
- [ ] Text corpus: BothBosu scam-conversation family (incl. YouTube real calls), FredZhang7/all-scam-spam,
      legit-call sources; normalize to unified JSONL schema; dedup; stratified splits.
- [ ] India-specific synthetic scripts (digital arrest, fake KYC, UPI refund, courier, electricity,
      OLX army-officer, loan-app) + matched legitimate counterparts (real bank/courier calls) to
      prevent the classifier learning "phone call ⇒ scam".
- [ ] Audio: Kaggle notebook pulls ASVspoof 2021 (LA/DF) + In-the-Wild; manifest builder.

### Phase 2 — Models (Jul 15–19)
- [ ] Voice forensics: fine-tune wav2vec2-base (or WavLM-base) binary head on ASVspoof21-DF,
      eval on In-the-Wild (cross-dataset = the headline eval). Export ONNX int8.
- [ ] Text classifier: fine-tune DistilBERT/DeBERTa-v3-small on corpus, multi-task
      (scam y/n + scam-type + tactic tags). Export ONNX int8.
- [ ] Calibration + fusion on held-out validation.

### Phase 3 — Product (Jul 20–24)
- [ ] FastAPI backend: WebSocket streaming, faster-whisper, ONNX inference, fusion, signature KB.
- [ ] Agents: verifier (claim extraction → KB lookup) + explainer (LLM w/ rule fallback).
- [ ] Frontend: live mic demo, animated risk meter, plain-language warnings, elderly mode
      (huge text, red/green, voice alert), family SMS/WhatsApp share stub, recording upload.

### Phase 4 — Rigor (Jul 25–27)
- [ ] Eval suite: cross-dataset audio report, text classifier ablations, end-to-end scripted
      scenario tests (10+ scam scripts incl. voice-cloned audio, 10+ benign calls), latency numbers.
- [ ] Tests for backend; error handling; README/docs polish.

### Phase 5 — Submission (Jul 28–30)
- [ ] 2–3 min demo video: live cloned-voice call gets flagged mid-sentence.
- [ ] Devpost writeup, screenshots, architecture diagram. Submit **early** on Jul 29.

## Prize categories targeted
Best Overall · Most Impactful · Best Use of ML · Conversational AI · Best Web AI App · Data-Driven Insights
