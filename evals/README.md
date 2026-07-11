# Kavach evals

Honest end-to-end evaluation of the Kavach text pipeline: it compares the TF-IDF text
model alone, the signature rule engine alone, and the full fusion system on two
datasets — 30 fresh, hand-written call transcripts (`scenarios.py`, 15 scam + 15
benign, written specifically to avoid any phrasing overlap with
`data_pipeline/india_synth.py`) and the 20 real scam calls in
`data/processed/test_real_youtube.jsonl` — reporting TPR/FPR, per-record scores, and
in-process latency, so the project has a real answer (not a vibe) to "does the full
system beat the text model alone, and at what false-positive cost?" See
`REPORT.md` for the results and honest discussion, and `report.json` for the raw
per-record data.

## How to run

```bash
cd evals
python run_eval.py
```

This imports `backend/kavach` directly (no HTTP server needed) and requires
`models/text_baseline.joblib` to exist for the text-model configs to be meaningful
(run `training/text/train_baseline.py` first if it's missing; the script still runs
without it, but `text_score` will be `null` everywhere and a warning is printed).
It writes `evals/report.json` and `evals/REPORT.md`.
