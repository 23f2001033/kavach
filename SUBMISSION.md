# Kavach — Devpost submission text

Copy-paste-ready text for the ML Empowerment Build Challenge 2.0 Devpost submission form.
Section headers below match Devpost's standard project form.

---

## Project name

Kavach

## Elevator pitch

*(max 200 characters)*

> Real-time AI defense against phone scams — fuses voice-clone detection, scam-language
> AI, and India-specific fraud signatures into one explainable verdict, live on the call.

(173 characters)

## Built with

Python, FastAPI, PyTorch, HuggingFace Transformers, DistilBERT, wav2vec2, ONNX Runtime,
faster-whisper, scikit-learn, React, Vite, Web Speech API, Kaggle (T4 GPU training),
Gemini API (optional)

## About the project

### Inspiration

In 2025 alone, Indians lost ₹22,495 crore — about $2.7 billion — to cyber fraud, across
2.81 million complaints, up 24% from the year before. And the tools scammers use just got
sharper: voice cloning now needs only 3 to 30 seconds of sampled audio to produce a
convincing fake (per CERT-In advisory CIAD-2024-0084), and in June 2026 the Five Eyes
intelligence alliance formally warned that voice confirmation alone can no longer be
trusted to verify who's on the other end of a call. What makes the "digital arrest" scam
so effective isn't technical sophistication — it's that a fake police officer, real fear,
and an artificial countdown are enough to stop someone from pausing to think, and the
script explicitly tells the victim not to consult their family. The tools that exist
today — carrier blocklists, caller-ID apps — only catch numbers *after* they've already
been reported. Nothing protects you *during* the call, while the manipulation is actually
happening. That gap is what we built Kavach to close.

### What it does

Kavach listens to a phone call — through your mic live, pasted as a transcript, or
uploaded as a recording — and gives you a real-time, explainable risk verdict by fusing
three independent AI signals: a fine-tuned DistilBERT model that reads the conversation
for social-engineering language, a knowledge base of 12 India-specific scam signatures
(OTP requests, "digital arrest" threats, remote-access app installs, UPI collect-request
tricks, and more) with plain-language explanations, and a fine-tuned wav2vec2 voice model
that detects AI-cloned or synthetic speech from the audio itself. The three signals
combine through noisy-OR fusion into one risk score with hysteresis, so the on-screen
meter climbs smoothly instead of flickering. When risk crosses into "high," the app speaks
a warning once and shows exactly *why* — quoted snippets from the transcript next to each
matched scam sign, not a black-box number. An Elderly Mode strips the UI down to a giant
gauge, a one-line verdict, and one piece of advice, for the demographic that scam callers
target hardest. Everything runs locally — no external API is required for detection.

### How we built it

We assembled a training corpus of 5,943 call transcripts from five open BothBosu
HuggingFace datasets plus 25 India-specific synthetic scenario families we wrote
ourselves — digital arrest, fake KYC, UPI refund traps, courier customs, KBC lottery,
army/OLX marketplace fraud, loan-app extortion, investment fraud, and job/hostel/dating-app
advance fees — each paired with a matched *benign* look-alike call so the model has to
learn the actual manipulation pattern, not just scam-adjacent vocabulary. Twenty real scam
call recordings were held out entirely from training as an honest real-world probe. We
fine-tuned `distilbert-base-uncased` on that corpus (with a sliding 256-token window for
long calls) and `facebook/wav2vec2-base` as a bonafide-vs-spoof classifier on ASVspoof
2019 LA, cross-evaluated on the independently-sourced In-the-Wild dataset — both trained
entirely on free Kaggle T4 GPU time, both exported to ONNX for fast local inference. The
FastAPI backend fuses text, signature, and voice scores through a noisy-OR combiner, and
a React frontend delivers three ways in: live mic capture via the Web Speech API, paste-a-
transcript, and upload-a-recording (transcribed locally with faster-whisper). We wrote an
end-to-end evaluation harness from day one — 30 hand-written fresh scenarios plus the 20
real held-out calls — and treated every result it produced as ground truth to react to,
not a formality to pass.

### Challenges we ran into

Three debugging stories stick out. First, our eval suite caught the fusion math itself
being broken: an earlier weighted-average combiner renormalized over whichever signals
were active, and since no audio model existed yet at the time, every real request
renormalized to effective weights of `{text: 0.588, signature: 0.412}` — so even a
maximally confident text score of 1.0 capped out at 0.588, structurally below our 0.65
"high" threshold, no matter how obvious the scam. Full fusion was catching *fewer* real
scam calls than the text model alone (6/20 vs. the then-current pre-corpus-hardening
TF-IDF baseline of 12/20) before we found this. We rewrote it
as a noisy-OR combination that excludes absent signals from the product instead of
diluting present ones, which took full-fusion real-call catch rate from 6/20 to 20/20 in
that run. Second, the audio side ate two full training days for a boring reason: the
public Kaggle mirror of the In-the-Wild cross-dataset ships the audio without the
`meta.csv` label file the official release includes, and a later mirror sorted the same
files into `real/` and `fake/` folders instead. Our training script assumed the documented
layout, so it crashed at the evaluation step rather than silently scoring against
nothing. We tracked down and shipped a verified copy of the 31,779-row label file into our
own repo, and taught the loader to fall back to folder-name labels — only then did the
19.5% cross-dataset EER we report actually mean anything. Third, we lost a completed
94-minute wav2vec2 training run
on Kaggle to a crash during the post-training eval step — the checkpoint existed in memory
but was never written to disk before the crash took the process down. We fixed the script
to save the model artifact immediately after training, *before* running any evaluation, so
a crash during eval can never again cost us the actual trained weights. And the last one
we caught with barely a day left, while preparing the demo video: we uploaded a recording
of a completely benign clinic appointment reminder that happened to be a text-to-speech
voice, and Kavach called it a scam with 0.92 confidence. The text model had scored it
correctly and no scam signature had fired — but our voice-forensics signal carried enough
weight to force a "high" verdict on its own, and the explanation underneath it claimed
"strong scam signs" while listing none. It was the right bug to find late, because it
exposed a wrong assumption rather than a wrong line of code: a synthetic voice is not
evidence of fraud. Bank IVRs, clinic reminders, and delivery notifications are all
synthetic speech, and an app that shrieks at every one of them teaches exactly the elderly
users we built this for to ignore it. We reweighted the voice signal so that on its own it
can only reach "suspicious" — corroborating context, not proof — while a synthetic voice
*plus* scam content still fires "high" immediately.

### Accomplishments we're proud of

We're proud that our own testing found five real bugs in our system before any judge could
— a fusion-math dilution bug, an overfitting text model, a training pipeline that could
silently lose a finished run, a suspiciously perfect baseline number, and a voice signal
that flagged legitimate robocalls as fraud — and that we fixed all five and kept the
honest before/after numbers in the report instead of quietly overwriting them. We're
proud that our text ensemble catches 19 of 20 real, never-before-seen scam call recordings
(up from a TF-IDF baseline that catches 11/20 on the current hardened training corpus, and
caught 12/20 on the original pre-hardening corpus), that our voice model achieves a 0.87%
error rate on
same-distribution data *and* that we reported its harder 19.5% cross-dataset number
instead of hiding it, and that the entire detection pipeline — transcription, text
scoring, voice forensics — runs completely offline with zero required external API calls,
which matters for a tool meant to work for people who may not trust (or afford) a
cloud-dependent app watching their calls.

### What we learned

The most valuable thing we built wasn't a model — it was the habit of writing the eval
harness before trusting any result, and of treating a suspiciously perfect number (our
TF-IDF baseline hit 100% accuracy on synthetic test data) as a warning sign rather than a
win. We learned that fusing multiple weak signals is genuinely harder than it looks —
"just average them" is an easy way to accidentally build a system that's worse than its
best single component, and we only found that because we measured text-alone performance
as a baseline to beat, not just a config to include. We also learned a lot about the
specific mechanics of India-targeted scams while writing the synthetic corpus — how
"digital arrest" scripts use isolation and video-call pressure specifically to prevent a
victim from consulting anyone, and how loan-app blackmail and army/OLX marketplace fraud
exploit very different psychological levers than the classic tech-support scam most
existing scam-detection tools were built around.

### What's next

Recalibrating the text ensemble's confidence (temperature scaling, or a lower fusion
weight) to close the 2–3 remaining benign false positives at "high" that our own eval
report documents honestly rather than hides; adding speaker diarization to
`/analyze/recording` so caller and receiver turns are separated instead of one merged
block; expanding voice-forensics training data across more TTS/vocoder families and
languages to bring the cross-dataset EER down; and building an on-device mobile version
so Kavach can sit on the actual phone call path, not just a browser tab.

## Suggested prize categories

- Best Overall Project
- Most Impactful Project
- Best Use of Machine Learning
- Best Web AI App
- Most Innovative
- Most Scalable
