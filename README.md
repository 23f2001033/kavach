# Kavach 🛡️

**Real-time, explainable scam-call defense — built for the ML Empowerment Build Challenge 2.0.**

Kavach (Sanskrit: "armor") listens to a phone call — live through the mic, pasted as a
transcript, or uploaded as a recording — and fuses three independent AI signals into one
plain-language verdict *while the call is still happening*: a fine-tuned transformer that
reads the conversation for social-engineering patterns, a fine-tuned voice model that
detects AI-cloned/synthetic speech, and a knowledge base of India-specific scam tells. It
runs entirely offline on commodity hardware.

| | |
|---|---|
| **Problem** | ₹22,495 crore (~$2.7B) lost to cyber fraud in India in 2025, 2.81M complaints, +24% YoY |
| **Detection** | 3 signals, noisy-OR fusion, plain-language explanations |
| **Text model** | Fine-tuned DistilBERT, 95% catch rate on 20 real scam calls held out from training |
| **Voice model** | wav2vec2-base, 0.87% EER same-dataset / 19.5% EER cross-dataset (honest, not cherry-picked) |
| **Latency** | Sub-second on CPU for a typical call-length transcript |
| **Privacy** | Core detection runs fully local — zero external API calls required |
| **Tests** | 70 backend tests passing |

---

## The problem

- Indians lost **₹22,495 crore (~$2.7B)** to cyber fraud in 2025 — 2.81 million complaints,
  up 24% year-over-year.
- Voice cloning now needs only **3–30 seconds** of sampled audio to produce a convincing
  clone (CERT-In advisory CIAD-2024-0084).
- In June 2026, the Five Eyes intelligence alliance issued joint guidance that **voice
  confirmation alone can no longer be trusted to verify identity.**
- Existing defenses don't cover this. Carrier-side blocklists and caller-ID apps catch
  *known* numbers reported after the fact — they say nothing about a first-time number
  running a fresh script, and nothing at all about a cloned voice on a call already in
  progress. **Nothing protects you at call time**, while the manipulation is actually
  happening. Kavach is built to fill exactly that gap.

## How Kavach works

```
                    ┌─────────────────────── Browser (React) ───────────────────────┐
  mic (live) ──────►│  Web Speech API (en-IN / hi-IN) ──► rolling transcript window  │
  upload (.wav/.mp3)│                                                                │
                    └─────────────────────────────┬──────────────────────────────────┘
                                                    │  POST /analyze/window|text|recording
                                                    ▼
                    ┌──────────────────────── FastAPI backend ───────────────────────┐
                    │  faster-whisper (recording upload only, local ASR)             │
                    │        │                                                       │
                    │        ▼                                                       │
                    │  ┌────────────────┐ ┌───────────────────┐ ┌──────────────────┐ │
                    │  │ TEXT ENSEMBLE  │ │ SIGNATURE ENGINE  │ │ VOICE FORENSICS   │ │
                    │  │ DistilBERT     │ │ 12 regex rules:   │ │ wav2vec2-base     │ │
                    │  │ (max-pooled    │ │ OTP/PIN request,  │ │ (ONNX) → sigmoid  │ │
                    │  │  256-tok       │ │ digital-arrest,   │ │ over 4s center-   │ │
                    │  │  windows)      │ │ remote-access app,│ │ crop @16kHz →     │ │
                    │  │ OR TF-IDF+     │ │ UPI collect-req,  │ │ P(AI-cloned voice)│ │
                    │  │ LogReg         │ │ secrecy demand,   │ │                   │ │
                    │  │ fallback       │ │ +7 more...        │ │ (recording/live   │ │
                    │  │ → P(scam)      │ │ → hit list         │ │  audio only)      │ │
                    │  └───────┬────────┘ └─────────┬─────────┘ └─────────┬─────────┘ │
                    │          └────────────────────┬┴─────────────────────┘          │
                    │                                ▼                                │
                    │              NOISY-OR FUSION + HYSTERESIS                       │
                    │     risk_score = 1 − Π(1 − sᵢ·wᵢ) over available signals        │
                    │        (absent signal excluded, never dilutes the others)       │
                    │                                │                                │
                    │                                ▼                                │
                    │        rule-based explainer (LLM polish optional, off by        │
                    │        default; detection never depends on it)                  │
                    └────────────────────────────────┬───────────────────────────────┘
                                                       ▼
                    risk gauge · risk_level (low/suspicious/high) · matched scam-sign
                    cards with quoted snippets · one-time spoken warning · Elderly Mode
```

All model inference — transcription, text scoring, voice forensics — runs locally via
ONNX Runtime / PyTorch / faster-whisper. An LLM (Gemini) can *optionally* reword the
explanation for readability if `GEMINI_API_KEY` is set; it never sees the raw audio,
never decides the risk score, and the rule-based explainer is a fully-functional fallback
if it's absent, times out, or errors.

## The three signals

**1. Text ensemble — reads the conversation for social engineering.**
A fine-tuned DistilBERT classifier (preferred) or a TF-IDF+LogisticRegression baseline
(automatic fallback if the transformer isn't installed) scores the transcript for
scam-likely language. Transcripts longer than 512 tokens are split into overlapping
256-token windows (stride 128) and the maximum window score is used, so a scam signal
buried anywhere in a long call still drives the score — matching how the model was
trained rather than silently truncating.

**2. Signature engine — 12 India-specific scam tells.**
A pure-data knowledge base (`backend/kavach/signatures.py`) of regex rules tuned to
real Indian scam scripts, each carrying a plain-language explanation and matched
snippets for the UI: OTP/PIN/CVV requests, "digital arrest"/warrant threats, remote-access
app installs (AnyDesk/TeamViewer), UPI collect-request/QR tricks, secrecy/isolation
demands, artificial urgency, prize/lottery upfront fees, KYC-expiry threats, fake
"safe account"/RBI transfers, loan-app photo blackmail, army/CRPF marketplace fraud, and
guaranteed-return investment claims. The OTP rule is deliberately guarded against a known
false-positive — a bank's "we never ask for your OTP" safety reminder — by requiring an
imperative request verb next to the term, not just the word itself.

**3. Voice forensics — detects AI-cloned/synthetic speech.**
A wav2vec2-base model fine-tuned as a bonafide-vs-spoof classifier on ASVspoof 2019 LA,
exported to ONNX. At inference it center-crops (zero-pads if shorter) the uploaded/live
waveform to the trained 4-second window at 16kHz, runs it through the model, and applies
sigmoid to the single output logit to get P(AI-generated voice). Only active on the
recording-upload and live-mic paths, where real audio (not just a transcript) is available.

**Fusion: noisy-OR, not weighted average.** `risk_score = 1 − Π(1 − sᵢ·wᵢ)` over whichever
signals are actually available this request. A missing signal (e.g. no audio on a
text-only request) is *excluded* from the product — it is never averaged in as a zero,
so it can never drag a confident reading down. See "What our evaluation caught" below for
why this matters — it's not a design choice we made in a vacuum, it's a bug the eval
suite found and forced us to fix.

## Results

All numbers below are from [`evals/REPORT.md`](evals/REPORT.md) / [`evals/report.json`](evals/report.json)
(text pipeline) and [`models/audio_metrics.json`](models/audio_metrics.json) (voice model)
— reproducible by running `python evals/run_eval.py` and the Kaggle training notebooks.

### Text pipeline — 15 fresh scam scenarios + 15 fresh benign scenarios (never used in training)

| Configuration | Catch rate (TPR) | False "high" alarms on benign (FPR) |
|---|---|---|
| Text ensemble alone | **15/15 (100%)** | 3/15 (20.0%) |
| Signature rules alone | 2/15 (13.3%) | 0/15 (0.0%) |
| Full fusion (any non-"low" reading) | **15/15 (100%)** | 4/15 (26.7%) |
| Full fusion (strict "high" only) | 14/15 (93.3%) | 3/15 (20.0%) |

### Text pipeline — 20 real scam-call recordings held out from all training

| Configuration | Catch rate |
|---|---|
| Text ensemble alone | **19/20 (95.0%)** |
| Signature rules alone | 4/20 (20.0%) |
| Full fusion (non-"low") | **19/20 (95.0%)** |
| Full fusion (strict "high") | **19/20 (95.0%)** |

For reference, the original TF-IDF+LogisticRegression baseline — trained before the
synthetic corpus was hardened with 10 additional scenario families — caught only 12/20
(60%) of these same real calls, which is the gap that motivated fine-tuning DistilBERT in
the first place. That same baseline, retrained on the now-hardened corpus (see
[`training/text/baseline_metrics.json`](training/text/baseline_metrics.json)), currently
reads 11/20 (55%) — two borderline calls moved from just above the 0.5 threshold to just
below it. Either number is well behind DistilBERT's 19/20.

### Voice forensics (wav2vec2-base, ONNX)

| Eval set | EER | ROC-AUC | Accuracy @ 0.5 | n |
|---|---|---|---|---|
| ASVspoof 2019 LA (same-distribution eval) | **0.87%** | 0.998 | 92.5% | 71,237 |
| In-the-Wild (**cross-dataset**, honest generalization check) | **19.5%** | 0.905 | 55.4% | 31,779 |

Trained on 25,380 utterances, 2 epochs, `facebook/wav2vec2-base` with a frozen feature
extractor, batch size 16, on a free Kaggle T4 GPU. The same-distribution number is
excellent; the cross-dataset number is reported honestly because it's the one that
predicts real-world behavior, and a 0.87%-EER headline with no cross-dataset check would
be misleading marketing, not an eval.

### Latency

In-process (no HTTP overhead), cycling through all 50 scenario + real-call transcripts:
**546 ms median, 3.59 s p95** (the tail is driven entirely by the longest real calls,
which trigger multi-window DistilBERT scoring). A single realistic ~244-word call
transcript scores in **~298 ms median** on CPU alone — comfortably inside a live-call
budget. `POST /analyze/recording` additionally pays a one-time faster-whisper transcription
cost (~6.4s for an 8-second clip on CPU, "small"/int8 config) plus a one-time ~464MB model
download on first use.

## What our evaluation caught

The eval suite isn't a rubber stamp — it caught four real problems during development,
in the order we found them:

1. **The TF-IDF baseline looked perfect and wasn't.** It scored 100% accuracy on the
   synthetic held-out test set — a red flag, not a win — and then only caught 12/20 (60%)
   of real scam calls (the pre-corpus-hardening baseline, in effect at the time). That gap
   between synthetic-test performance and real-call performance is what motivated
   fine-tuning DistilBERT instead of shipping the baseline. (The same TF-IDF baseline,
   retrained since on the hardened corpus, currently reads 11/20 — see
   [`training/text/baseline_metrics.json`](training/text/baseline_metrics.json) — still
   well behind DistilBERT.)
2. **Fusion was silently diluting the text signal.** An earlier weighted-average combiner
   renormalized over whichever signals were active. Since no audio model existed yet at
   the time, every request renormalized to `{text: 0.588, signature: 0.412}` — so even a
   maximally confident text score of 1.0 capped out at 0.588, structurally below the 0.65
   "high" threshold. Full fusion was catching *fewer* real scams than the text model
   alone (6/20 vs. the then-current 12/20 pre-hardening baseline) before this was found.
   The fix — noisy-OR combination with no renormalization — took real-call catch rate
   from 6/20 to 19/20.
3. **DistilBERT overfit and confidently missed real scenarios.** After swapping in the
   fine-tuned transformer, it went sharply polarized on the 15 fresh handwritten
   scenarios — outputs near 0.000 or 1.000, rarely in between — and confidently scored
   several genuine scam scripts near zero (the deepfake-grandchild-emergency and
   rental-deposit-advance scenarios, among others) that the simpler baseline had at least
   landed in an ambiguous middle. Fixed by keeping the text ensemble (DistilBERT primary,
   TF-IDF fallback) and hardening the training corpus with 10 additional scenario
   families, including adversarial benign look-alikes designed specifically to probe this
   failure mode.
4. **Two-to-three benign look-alike calls still trigger a false "high."** A genuine
   bank fraud-alert yes/no call and a customer-care callback request both score "high" on
   text alone, because their phrasing statistically resembles scam scripts. This is a
   known, documented limitation — not hidden in a footnote. It is the direct cost of
   fixing problem #2: once text evidence is no longer diluted, an overconfident text
   score on a benign call is no longer diluted either. Recalibration (temperature scaling
   or a lower text weight) is listed under Future Work below.

We think shipping this section is more convincing than shipping a report with no failures
in it.

## Quickstart

**Requirements:** Python 3.10+, Node 18+, ~2GB disk for models (DistilBERT + wav2vec2-base
+ faster-whisper's downloaded weights).

```bash
# 1. Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev
# open the printed local URL (usually http://localhost:5173)
```

**Live Guard mode requires Chrome or Edge** (desktop or Android) — it uses the
`SpeechRecognition` Web Speech API, which Firefox/Safari don't implement. Transcript-paste
mode works in any modern browser.

**Models are gitignored, not committed** (`models/distilbert/`, `*.onnx`, `*.joblib` —
see `.gitignore`). The service still starts and degrades gracefully without them
(`/health` reports which models loaded; missing text/audio scoring just falls through to
whatever signal *is* available). To get the real models:

- **Trained models**: run the Kaggle notebooks — `training/text/kaggle_train_text.ipynb`
  (DistilBERT, free T4, a few minutes/epoch) and `training/audio/kaggle_train_audio.ipynb`
  (wav2vec2-base, free T4, ~20–35 min/epoch) — then download the artifacts into `models/`
  per the instructions in `training/text/KAGGLE.md` and `training/audio/KAGGLE.md`.
- **Fastest path to *something* running**: `python training/text/train_baseline.py`
  trains the TF-IDF+LogReg fallback locally in ~22 seconds (CPU, no GPU needed).

```bash
# Rebuild the training corpus (JSONL files are gitignored; only stats.json is committed)
python -m data_pipeline.build_corpus

# Run the backend test suite
cd backend && pytest -v

# Re-run the end-to-end eval suite (writes evals/report.json + evals/REPORT.md)
cd evals && python run_eval.py
```

## Repository layout

```
data_pipeline/   Corpus assembly: 5 BothBosu HuggingFace datasets + 25 India-specific
                 synthetic scenario families (scam + matched benign look-alikes)
training/        Kaggle-notebook-friendly training scripts (text: DistilBERT + TF-IDF
                 baseline; audio: wav2vec2-base voice-deepfake detector)
backend/         FastAPI inference server — signatures, text scoring, fusion,
                 hysteresis, transcription, rule-based/LLM-optional explainer
frontend/        React app — Live Guard, Transcript mode, Recording upload,
                 animated risk gauge, Elderly Mode
evals/           End-to-end evaluation harness + the honest results report
models/          Trained model artifacts (gitignored except audio_metrics.json)
```

See `backend/README.md`, `frontend/README.md`, and `data_pipeline/README.md` for
component-level detail — API contracts, request/response shapes, and dev workflow.

## Limitations & future work

- **Benign false positives at "high."** 2–3 benign look-alikes (bank fraud-alert calls,
  customer-care callbacks) still score "high" on text alone (documented above).
  Recalibration (temperature scaling on DistilBERT's logits, or a lower text fusion
  weight) is the next step, not shipped yet.
- **Signature engine is a fixed regex vocabulary.** It cannot generalize to a
  well-written advance-fee scam that never says OTP, AnyDesk, or "digital arrest" — by
  construction, several fresh scam scenarios (rental-deposit advance, matrimonial
  premium-unlock, job-advance-fee) are invisible to it and rely entirely on the text
  ensemble.
  Real YouTube calls (US-centric SSN/tech-support/prize scripts) are outside the
  signature engine's India-tuned vocabulary almost entirely (4/20).
- **No speaker diarization.** `POST /analyze/recording` transcribes the whole call as one
  block via faster-whisper and labels it all "Caller:" — a future version could add
  pyannote-style diarization to separate caller/receiver turns properly.
- **Voice forensics cross-dataset EER (19.5%)** is honest but not production-grade on its
  own; it contributes as one signal in fusion, not a standalone gate. More diverse
  training data (multiple TTS/vocoder families, more languages) is the path to lowering it.
- **LLM explanation polish is optional and off by default** — a good next step for the
  product (not the detection core) is default-enabling it behind a free-tier key with a
  clear "why" trail, while keeping the rule-based fallback as-is.

## Credits & datasets

- **BothBosu scam-conversation family** (HuggingFace) — scam-dialogue, multi-agent,
  single-agent, scammer-conversation, and youtube-scam-conversations subsets — the
  backbone of the text training corpus and the 20 real held-out scam calls.
- **ASVspoof 2019 LA** — voice-spoofing training/eval data for the voice forensics model.
- **In-the-Wild (Release-in-the-Wild)** — cross-dataset generalization eval for the
  voice forensics model, sourced independently of ASVspoof.
- **India-specific synthetic corpus** (`data_pipeline/india_synth.py`) — 25 slot-filled
  scenario families covering digital arrest, fake KYC, UPI refund traps, courier customs,
  KBC lottery, army/OLX marketplace fraud, loan-app extortion, investment fraud,
  job/hostel/dating-app advance fees, and matched legitimate look-alikes, written for
  this project.
- **`distilbert-base-uncased`** (HuggingFace/Google) and **`facebook/wav2vec2-base`** —
  base checkpoints fine-tuned for this project.
- CERT-In advisory CIAD-2024-0084 (voice-cloning sample-length warning) and the June 2026
  Five Eyes joint guidance on voice-based identity verification — cited for context, not
  affiliated with this project.

Built for the [ML Empowerment Build Challenge 2.0](https://ml-empowerment-2.devpost.com/).
Everything was trained on free compute (Kaggle T4 GPU), fully reproducible via the
committed notebooks.
