# Kavach 🛡️ — Real-Time AI Scam-Call Defense

**Kavach** (Sanskrit: "armor") is an explainable, real-time defense system against phone scams —
the ₹22,495 crore/year fraud epidemic in India. It listens to a call (live mic or recording)
and fuses three independent signals into one plain-language verdict:

1. **Voice forensics** — a fine-tuned self-supervised speech model detects AI-cloned /
   synthetic voices (trained on ASVspoof 2021 + In-the-Wild, with honest cross-dataset evals).
2. **Social-engineering detection** — live transcription feeds a classifier trained to spot
   manipulation patterns: digital-arrest scripts, fake-KYC urgency, UPI refund traps,
   authority impersonation, isolation tactics.
3. **Verifier agents** — cross-check claims made by the caller against a scam-signature
   knowledge base and explain *why* a call is suspicious, in language your grandparents understand.

**Design principle: the core detection path requires zero external APIs.** Models run locally
(ONNX). LLM agents only *enhance* explanations when available — detection never depends on them.

## Why

- Indians lost **₹22,495 crore (~$2.7B)** to cyber fraud in 2025 (2.81M complaints, +24% YoY).
- Voice cloning now needs only **3–30 seconds** of audio (CERT-In advisory CIAD-2024-0084).
- Five Eyes joint guidance (June 2026): voice confirmation alone can no longer verify identity.
- There is still no good **consumer-side, call-time** defense. Kavach is that missing layer.

## Repository layout

```
data_pipeline/   Assemble the unified scam-conversation corpus (open datasets + India-specific synthesis)
training/        Colab/Kaggle notebooks & scripts for model training (free-tier GPU friendly)
backend/         FastAPI inference server: transcription, scoring, fusion, agents
frontend/        Web app: live mic mode, risk meter, explanations, elderly-friendly UI
evals/           Evaluation suites and the cross-dataset generalization report
```

## Status

🚧 Built for the [ML Empowerment Build Challenge 2.0](https://ml-empowerment-2.devpost.com/) — in active development, submission July 30, 2026.
