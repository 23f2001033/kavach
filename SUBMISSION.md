# Kavach: Devpost submission text

Copy-paste ready for the ML Empowerment Build Challenge 2.0. Each heading below maps to a
field on the Devpost project form.

---

## Project name

Kavach

## Elevator pitch

*(Devpost limit: 200 characters)*

> Scam blockers work after the call. Kavach works during it, warning you live, in plain
> words, why a call is a scam and whether the voice is an AI clone. Runs on your device.

## Built with

python, fastapi, pytorch, huggingface-transformers, distilbert, wav2vec2, onnx-runtime,
faster-whisper, scikit-learn, react, vite, web-speech-api, kaggle

## About the project

### Inspiration

In 2025, Indians lost ₹22,495 crore (about $2.7 billion) to cyber fraud across 2.81 million
complaints, up 24% year over year. The attacker's tools keep getting sharper: cloning a
voice now takes as little as 3 to 30 seconds of sampled audio (CERT-In advisory
CIAD-2024-0084), and in June 2026 the Five Eyes alliance warned that voice confirmation
alone can no longer verify who is on a call.

What makes the "digital arrest" scam so effective is not technical sophistication. It is
that a fake police officer, real fear, and an artificial countdown are enough to stop
someone from pausing to think, and the script explicitly instructs the victim not to
consult their family. Existing defenses never reach that moment. Carrier blocklists and
caller ID apps only flag numbers after someone has already been defrauded, which says
nothing about a fresh number running a new script. Nothing protects you during the call
itself, while the manipulation is actually happening. That gap is what Kavach closes.

### What it does

Kavach listens to a phone call, live through your microphone, pasted as a transcript, or
uploaded as a recording, and returns a real-time, explainable verdict built from three
independent AI signals:

1. A fine-tuned DistilBERT model that reads the conversation for social-engineering
   language.
2. A knowledge base of 12 India-specific scam signatures (OTP requests, "digital arrest"
   threats, remote-access app installs, UPI collect-request tricks, secrecy demands and
   more), each carrying a plain-language explanation.
3. A fine-tuned wav2vec2 model that detects AI-cloned or synthetic speech from the audio
   itself.

The three signals combine through noisy-OR fusion into a single risk score, with
hysteresis so the on-screen meter climbs smoothly instead of flickering. When risk crosses
into "high", the app speaks a warning once and shows exactly why, quoting the line from
the transcript that triggered each matched scam sign instead of presenting a black-box
number. Elderly Mode strips the interface down to one gauge, one verdict and one line of
advice, for the people scam callers target hardest. Detection runs entirely on the device.
No external API is required.

### How we built it

We assembled a corpus of 5,943 call transcripts from five open BothBosu HuggingFace
datasets plus 25 India-specific synthetic scenario families we wrote ourselves: digital
arrest, fake KYC, UPI refund traps, courier customs, KBC lottery, army/OLX marketplace
fraud, loan-app extortion, investment fraud, and job, hostel and dating-app advance fees.
Each scam family is paired with a matched benign look-alike call, so the model has to learn
the manipulation pattern rather than scam-adjacent vocabulary. Twenty real scam call
recordings were held out from training entirely, as an honest real-world probe.

We fine-tuned `distilbert-base-uncased` on that corpus, using a sliding 256-token window so
a signal buried in a long call still drives the score, and `facebook/wav2vec2-base` as a
bonafide-versus-spoof classifier on ASVspoof 2019 LA, cross-evaluated on the independently
sourced In-the-Wild dataset. Both were trained entirely on free Kaggle T4 GPU time and
exported to ONNX for fast local inference. A FastAPI backend fuses the text, signature and
voice scores, and a React frontend offers three ways in: live microphone capture via the
Web Speech API, paste-a-transcript, and upload-a-recording transcribed locally with
faster-whisper.

We wrote the end-to-end evaluation harness on day one, covering 30 fresh hand-written
scenarios plus the 20 real held-out calls, and treated every result it produced as
something to react to rather than a formality to pass.

### Challenges we ran into

Four problems cost us the most time, and all four were found by our own testing.

The fusion math was quietly broken. An earlier weighted-average combiner renormalized over
whichever signals were active, and because no audio model existed yet, every request
renormalized to effective weights of text 0.588 and signature 0.412. A maximally confident
text score of 1.0 therefore capped at 0.588, structurally below our 0.65 "high" threshold,
no matter how obvious the scam. Full fusion was catching fewer real scam calls than the
text model alone, 6 out of 20 against the text model's 12, before we found it. Rewriting
it as a noisy-OR combination that excludes absent signals instead of diluting present ones
took full-fusion real-call catch rate from 6/20 to 20/20 in that run.

The audio dataset ate two training days for a boring reason. The public Kaggle mirror of
In-the-Wild ships the audio without the `meta.csv` label file the official release
includes, and a second mirror sorted the same files into `real/` and `fake/` folders
instead. Our script assumed the documented layout and crashed at the evaluation step. We
tracked down and shipped a verified copy of the 31,779-row label file into our own repo,
and taught the loader to fall back to folder-name labels. Only then did the 19.5%
cross-dataset EER we report mean anything.

We lost a completed 94-minute training run. The wav2vec2 model finished training on Kaggle
and then the process crashed during post-training evaluation, before the weights were ever
written to disk. We changed the script to save the model artifact immediately after
training and before any evaluation, so an eval-time crash can never again destroy a
finished run.

The last one surfaced with barely a day left, while preparing the demo video. We uploaded a
recording of an entirely benign clinic appointment reminder that happened to use a
text-to-speech voice, and Kavach called it a scam with 0.92 confidence. The text model had
scored it correctly and no signature had fired, but the voice-forensics signal alone
carried enough weight to force a "high" verdict, and the explanation beneath it claimed
"strong scam signs" while listing none. It was the right bug to find late, because it
exposed a wrong assumption rather than a wrong line of code. A synthetic voice is not
evidence of fraud. Bank IVRs, clinic reminders and delivery notifications are all synthetic
speech, and an app that shrieks at every one of them teaches the elderly users we built it
for to ignore it. We reweighted the voice signal so that on its own it can only reach
"suspicious", corroborating context rather than proof, while a synthetic voice combined
with scam content still fires "high" immediately.

### Accomplishments that we're proud of

Our own testing found five real bugs before any judge could: a fusion-math dilution bug, an
overfitting text model, a training pipeline that could silently lose a finished run, a
baseline number that looked too good to be true, and a voice signal that flagged legitimate
robocalls as fraud. We fixed all five and kept the honest before-and-after numbers in the
report rather than quietly overwriting them.

On results, our text ensemble catches 19 of 20 real, never-before-seen scam call
recordings, against a TF-IDF baseline that catches 11 of 20 on the same corpus. Our voice
model reaches a 0.87% equal error rate on same-distribution data, and we published its much
harder 19.5% cross-dataset number rather than hiding it. The entire detection pipeline,
transcription, text scoring and voice forensics, runs offline with zero required external
API calls, which matters for a tool meant to serve people who may neither trust nor afford
a cloud service listening to their phone calls.

### What we learned

The most valuable thing we built was not a model. It was the habit of writing the
evaluation harness before trusting any result, and of treating a suspiciously perfect
number as a warning rather than a win. Our TF-IDF baseline scored 100% on the synthetic
test set and then caught barely half of the real calls.

We learned that fusing weak signals is harder than it looks. "Just average them" is an easy
way to build a system that performs worse than its own best component, and we only caught
that because we measured text-alone performance as a baseline to beat instead of treating
it as one configuration among many.

We also learned how differently India-targeted scams work from the tech-support scams most
detection tools were built around. "Digital arrest" scripts use isolation and video-call
pressure specifically to stop a victim from consulting anyone, and loan-app blackmail and
army/OLX marketplace fraud pull on entirely different psychological levers.

### What's next for Kavach

Recalibrating the text ensemble's confidence, through temperature scaling or a lower fusion
weight, to close the three benign false positives at "high" that our evaluation report
documents openly. Adding speaker diarization to the recording endpoint so caller and
receiver turns are separated instead of merged into one block. Expanding voice-forensics
training across more TTS and vocoder families and more languages, to bring the
cross-dataset error rate down. And building an on-device mobile version, so Kavach can sit
on the actual call path rather than in a browser tab.

---

## Submission checklist

**Repository:** https://github.com/23f2001033/kavach

**Demo video: upload to YouTube, not Google Drive.** Devpost embeds YouTube inline, so a
judge watches without leaving the page. A Drive link makes them click through, wait on a
preview that often fails for large files, and sometimes hit a permissions wall. Any of
those can cost you the view.

1. Upload and set visibility to **Public**.
2. Answer **"No, it's not made for kids"**. That setting disables embedding and would
   break the Devpost player.
3. Title it `Kavach: real-time AI scam-call defense (ML Empowerment Build Challenge 2.0)`
   and put the repo link in the description.
4. Open the URL in an incognito window to confirm it plays before you submit.
5. Paste the URL into Devpost's video field.

**Prize categories to enter:** Best Overall Project, Most Impactful Project, Best Use of
Machine Learning, Best Web AI App, Most Innovative, Most Scalable.
