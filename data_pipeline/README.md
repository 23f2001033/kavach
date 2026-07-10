# data_pipeline

Assembles the unified Kavach call-transcript corpus.

- `schema.py` — unified record schema, scam-type taxonomy, speaker-alias maps.
- `india_synth.py` — generates India-specific scam calls (digital arrest, fake KYC, UPI
  refund traps, courier customs, KBC lottery, army-OLX, loan-app threats, investment fraud)
  plus matched benign counterparts, via slot-filled multi-turn templates.
- `build_corpus.py` — pulls five BothBosu HuggingFace datasets + the synthetic generator,
  normalizes speakers to `Caller:`/`Receiver:`, dedups, and writes stratified splits.

## Run

```
pip install datasets scikit-learn pandas
python -m data_pipeline.build_corpus     # from the repo root
```

Outputs to `data/processed/`: `train.jsonl`, `val.jsonl`, `test.jsonl`,
`test_real_youtube.jsonl` (20 REAL scam calls, held out — never used in training),
and `stats.json` (committed; the JSONL files are gitignored).
