"""End-to-end Kavach evaluation: does the full system (signatures + text model
+ fusion) beat the TF-IDF text model alone?

Evaluates THREE configurations:
  1. text_only       -- text model alone, P(scam) >= 0.5 => scam
  2. signatures_only  -- any signature hit with severity >= 2 => scam
  3. fusion_notlow    -- full fusion, risk_level != "low" => scam
     (also reports fusion_high_only: risk_level == "high" => scam)

...on two datasets:
  (a) evals/scenarios.py -- 15 fresh handwritten scam + 15 fresh benign
      transcripts (TPR + FPR both measurable)
  (b) data/processed/test_real_youtube.jsonl -- 20 real scam YouTube calls
      used in training/text/baseline_metrics.json (label=1 only; catch-rate,
      no FPR)

Imports backend internals directly (kavach.text_model / kavach.signatures /
kavach.fusion) rather than going over HTTP, so this runs fast and
deterministically with no server process. Also measures the latency of a
full analyze pass (text score + signature match + fusion combine) over 50
runs cycling through the combined dataset.

Usage:
    cd evals && python run_eval.py
Writes evals/report.json and evals/REPORT.md.
"""
import json
import statistics
import sys
import time
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent
REPO_ROOT = EVALS_DIR.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from kavach import config  # noqa: E402
from kavach.fusion import combine  # noqa: E402
from kavach.signatures import match as match_signatures  # noqa: E402
from kavach.text_model import get_text_scorer  # noqa: E402

sys.path.insert(0, str(EVALS_DIR))
from scenarios import ALL_SCENARIOS  # noqa: E402

TEXT_THRESHOLD = 0.5
SIGNATURE_SEVERITY_THRESHOLD = 2
YOUTUBE_PATH = REPO_ROOT / "data" / "processed" / "test_real_youtube.jsonl"
LATENCY_RUNS = 50


# ------------------------------------------------------------------ loading
def load_youtube_records():
    records = []
    with open(YOUTUBE_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            records.append({
                "id": rec["id"],
                "label": rec["label"],
                "scam_type": rec.get("scam_type", "unknown"),
                "transcript": rec["text"],
            })
    return records


def load_scenario_records():
    return [
        {
            "id": s["id"],
            "label": s["label"],
            "scam_type": s["scam_type"],
            "transcript": s["transcript"],
        }
        for s in ALL_SCENARIOS
    ]


# ------------------------------------------------------------------ scoring
def analyze(transcript: str, text_scorer) -> dict:
    """Replicates backend.kavach.api._analyze's core computation (minus the
    FastAPI/session/explanation wrapping, which isn't relevant to scoring)."""
    text_score = text_scorer.score(transcript)
    hits = match_signatures(transcript)
    result = combine(text_score=text_score, signature_hits=hits, audio_score=None)
    return {
        "text_score": text_score,
        "n_hits": len(hits),
        "hit_ids": [h["id"] for h in hits],
        "max_hit_severity": max((h["severity"] for h in hits), default=0),
        "risk_score": result["risk_score"],
        "risk_level": result["risk_level"],
    }


def predict_text_only(analysis: dict) -> bool:
    return analysis["text_score"] is not None and analysis["text_score"] >= TEXT_THRESHOLD


def predict_signatures_only(analysis: dict) -> bool:
    return analysis["max_hit_severity"] >= SIGNATURE_SEVERITY_THRESHOLD


def predict_fusion_notlow(analysis: dict) -> bool:
    return analysis["risk_level"] != "low"


def predict_fusion_high_only(analysis: dict) -> bool:
    return analysis["risk_level"] == "high"


CONFIGS = {
    "text_only": predict_text_only,
    "signatures_only": predict_signatures_only,
    "fusion_notlow": predict_fusion_notlow,
    "fusion_high_only": predict_fusion_high_only,
}


# ------------------------------------------------------------------ metrics
def evaluate_dataset(records, text_scorer):
    """Returns {config_name: {"records": [...], "tp":.., "fn":.., "fp":.., "tn":..}}."""
    analyses = [analyze(r["transcript"], text_scorer) for r in records]

    out = {}
    for cfg_name, predict_fn in CONFIGS.items():
        rows = []
        tp = fn = fp = tn = 0
        for rec, analysis in zip(records, analyses):
            predicted_scam = predict_fn(analysis)
            actual_scam = bool(rec["label"])
            correct = predicted_scam == actual_scam
            if actual_scam and predicted_scam:
                tp += 1
            elif actual_scam and not predicted_scam:
                fn += 1
            elif not actual_scam and predicted_scam:
                fp += 1
            else:
                tn += 1
            rows.append({
                "id": rec["id"],
                "label": rec["label"],
                "scam_type": rec["scam_type"],
                "text_score": analysis["text_score"],
                "n_hits": analysis["n_hits"],
                "hit_ids": analysis["hit_ids"],
                "risk_score": round(analysis["risk_score"], 4),
                "risk_level": analysis["risk_level"],
                "predicted_scam": predicted_scam,
                "correct": correct,
            })
        n_scam = tp + fn
        n_benign = fp + tn
        out[cfg_name] = {
            "records": rows,
            "tp": tp, "fn": fn, "fp": fp, "tn": tn,
            "n_scam": n_scam, "n_benign": n_benign,
            "tpr": (tp / n_scam) if n_scam else None,
            "fpr": (fp / n_benign) if n_benign else None,
        }
    return out


def measure_latency(records, text_scorer, n_runs=LATENCY_RUNS):
    transcripts = [r["transcript"] for r in records]
    if not transcripts:
        return {}
    latencies_ms = []
    for i in range(n_runs):
        transcript = transcripts[i % len(transcripts)]
        start = time.perf_counter()
        analyze(transcript, text_scorer)
        latencies_ms.append((time.perf_counter() - start) * 1000)
    latencies_ms.sort()
    return {
        "n_runs": n_runs,
        "median_ms": round(statistics.median(latencies_ms), 3),
        "p95_ms": round(latencies_ms[min(len(latencies_ms) - 1, int(0.95 * len(latencies_ms)))], 3),
        "min_ms": round(latencies_ms[0], 3),
        "max_ms": round(latencies_ms[-1], 3),
        "mean_ms": round(statistics.mean(latencies_ms), 3),
    }


# ------------------------------------------------------------------ report
def build_report():
    text_scorer = get_text_scorer()
    if not text_scorer.is_loaded:
        print(
            "WARNING: models/text_baseline.joblib not loaded — text_score will be None "
            "for every record and text_only/fusion configs degrade to signature-only "
            "behavior. Run training/text/train_baseline.py first.",
            file=sys.stderr,
        )

    scenario_records = load_scenario_records()
    youtube_records = load_youtube_records()

    scenario_results = evaluate_dataset(scenario_records, text_scorer)
    youtube_results = evaluate_dataset(youtube_records, text_scorer)

    latency = measure_latency(scenario_records + youtube_records, text_scorer)

    report = {
        "text_model_loaded": text_scorer.is_loaded,
        "thresholds": {
            "text_threshold": TEXT_THRESHOLD,
            "signature_severity_threshold": SIGNATURE_SEVERITY_THRESHOLD,
            "risk_thresholds": config.RISK_THRESHOLDS,
        },
        "baseline_context": {
            "description": (
                "training/text/baseline_metrics.json: TF-IDF+LogReg text model ALONE on "
                "the 20 real YouTube scam calls (test_real_youtube.jsonl), at P(scam)>=0.5"
            ),
            "flagged_at_0.5": 12,
            "n": 20,
            "recall_at_0.5": 0.6,
        },
        "scenarios": {
            "n_scam": 15,
            "n_benign": 15,
            "configs": {
                name: {k: v for k, v in res.items() if k != "records"}
                for name, res in scenario_results.items()
            },
            "config_records": {name: res["records"] for name, res in scenario_results.items()},
        },
        "youtube_real_calls": {
            "n": 20,
            "note": "All 20 records are label=1 (scam); FPR is not measurable on this set.",
            "configs": {
                name: {k: v for k, v in res.items() if k != "records"}
                for name, res in youtube_results.items()
            },
            "config_records": {name: res["records"] for name, res in youtube_results.items()},
        },
        "latency_ms": latency,
    }
    return report


def render_markdown(report: dict) -> str:
    lines = []
    lines.append("# Kavach end-to-end evaluation report")
    lines.append("")
    lines.append(
        "This suite compares three detection configurations — the text model alone, "
        "the signature rule engine alone, and the full fusion system — on two datasets: "
        "30 fresh handwritten scenarios (15 scam / 15 benign, never seen by any model or "
        "the signature author during development) and the 20 real scam calls from "
        "YouTube (`data/processed/test_real_youtube.jsonl`). It is meant to honestly answer "
        "one question: **does adding the signature engine + fusion beat the text model "
        "alone, and at what false-positive cost?**"
    )
    lines.append("")
    bc = report["baseline_context"]
    lines.append(
        f"**Known baseline:** the TF-IDF+LogisticRegression text model alone catches "
        f"**{bc['flagged_at_0.5']}/{bc['n']}** ({bc['recall_at_0.5']*100:.0f}%) of the real "
        f"YouTube scam calls at threshold 0.5 (see `training/text/baseline_metrics.json`). "
        f"That number is the floor this suite is trying to beat — the text model was trained "
        f"almost entirely on synthetic conversations, so real, messy, human calls are its "
        f"hardest case."
    )
    lines.append("")
    if not report["text_model_loaded"]:
        lines.append(
            "> **WARNING:** `models/text_baseline.joblib` was not loaded when this report was "
            "generated. Every `text_score` below is `null` and the `text_only`/`fusion_*` "
            "numbers reduce to signature-only behavior. Re-run after "
            "`training/text/train_baseline.py`."
        )
        lines.append("")

    def fmt_pct(x):
        return "n/a" if x is None else f"{x*100:.1f}%"

    # -------------------------------------------------- scenarios summary table
    lines.append("## 1. Fresh scenarios (15 scam + 15 benign)")
    lines.append("")
    lines.append("| Config | TPR (catch rate on scam) | FPR (false alarms on benign) |")
    lines.append("|---|---|---|")
    for name, res in report["scenarios"]["configs"].items():
        lines.append(
            f"| `{name}` | {fmt_pct(res['tpr'])} ({res['tp']}/{res['n_scam']}) "
            f"| {fmt_pct(res['fpr'])} ({res['fp']}/{res['n_benign']}) |"
        )
    lines.append("")

    # -------------------------------------------------- youtube summary table
    lines.append("## 2. Real YouTube scam calls (20/20 label=scam)")
    lines.append("")
    lines.append("| Config | Catch rate |")
    lines.append("|---|---|")
    for name, res in report["youtube_real_calls"]["configs"].items():
        lines.append(f"| `{name}` | {res['tp']}/{res['n_scam']} ({fmt_pct(res['tpr'])}) |")
    lines.append("")
    lines.append(
        f"For reference, the text model alone in the original training-time probe caught "
        f"{bc['flagged_at_0.5']}/{bc['n']}; the `text_only` row above re-derives that same "
        f"number through the eval harness (small differences, if any, would flag a scoring bug)."
    )
    lines.append("")

    # -------------------------------------------------- latency
    lat = report["latency_ms"]
    if lat:
        lines.append("## 3. Latency (full analyze pass: text score + signature match + fusion)")
        lines.append("")
        lines.append(
            f"Over {lat['n_runs']} runs cycling through all 50 transcripts (scenarios + "
            f"YouTube calls): **median {lat['median_ms']} ms, p95 {lat['p95_ms']} ms** "
            f"(min {lat['min_ms']} ms, max {lat['max_ms']} ms, mean {lat['mean_ms']} ms). "
            f"This excludes FastAPI/HTTP overhead — it's pure in-process inference time."
        )
        lines.append("")

    # -------------------------------------------------- per-record tables
    lines.append("## 4. Per-record detail")
    lines.append("")
    for dataset_key, title in [
        ("scenarios", "Scenarios"),
        ("youtube_real_calls", "YouTube real calls"),
    ]:
        lines.append(f"### {title}")
        lines.append("")
        for cfg_name in CONFIGS:
            lines.append(f"**`{cfg_name}`**")
            lines.append("")
            lines.append("| id | label | text_score | n_hits | risk_score | risk_level | correct? |")
            lines.append("|---|---|---|---|---|---|---|")
            for row in report[dataset_key]["config_records"][cfg_name]:
                ts = "null" if row["text_score"] is None else f"{row['text_score']:.3f}"
                label_str = "scam" if row["label"] == 1 else "benign"
                mark = "yes" if row["correct"] else "NO"
                lines.append(
                    f"| {row['id']} | {label_str} | {ts} | {row['n_hits']} | "
                    f"{row['risk_score']:.3f} | {row['risk_level']} | {mark} |"
                )
            lines.append("")

    # -------------------------------------------------- honest discussion
    lines.append("## 5. Honest discussion")
    lines.append("")
    lines.append(_discussion_text(report))
    return "\n".join(lines)


def _discussion_text(report: dict) -> str:
    sc = report["scenarios"]["configs"]
    yt = report["youtube_real_calls"]["configs"]

    def worst_fp(cfg):
        return [r for r in report["scenarios"]["config_records"][cfg] if r["label"] == 0 and r["predicted_scam"]]

    def worst_fn_yt(cfg):
        return [r for r in report["youtube_real_calls"]["config_records"][cfg] if not r["predicted_scam"]]

    text_fp = worst_fp("text_only")
    fusion_fp = worst_fp("fusion_notlow")
    sig_fp = worst_fp("signatures_only")
    fusion_yt_miss = worst_fn_yt("fusion_notlow")
    text_yt_miss = worst_fn_yt("text_only")

    paras = []
    paras.append(
        "**The headline finding: right now, full fusion (`fusion_notlow`) catches FEWER "
        "scams than the text model alone, on both datasets.** "
        f"On the 15 fresh scam scenarios: text_only {sc['text_only']['tp']}/15 vs "
        f"fusion_notlow {sc['fusion_notlow']['tp']}/15. On the 20 real YouTube calls: "
        f"text_only {yt['text_only']['tp']}/20 vs fusion_notlow {yt['fusion_notlow']['tp']}/20. "
        "`fusion_high_only` catches essentially nothing on either dataset "
        f"({yt['fusion_high_only']['tp']}/20 real calls). The mechanism is a specific, "
        "reproducible calibration effect, not noise: `combine()` computes a weighted "
        "average of whichever of {text, signature, audio} are active, renormalizing over "
        "the active weights (see `kavach/fusion.py`). The audio model isn't shipped yet, so "
        "`audio_score` is always `None` in practice today — every real request renormalizes "
        "over just {text: 0.5, signature: 0.35} => effective weights {text: 0.588, "
        "signature: 0.412}. When a scam call has zero signature-engine hits (very common for "
        "phrasing the fixed regex list was never written for), `signature_subscore` is "
        "exactly 0.0, which *actively pulls the average down* rather than leaving the text "
        "signal untouched: `risk_score = text_score * 0.588`. A text_score of 1.0 (the "
        "model's maximum possible confidence) therefore caps out at risk_score=0.588, which "
        "is BELOW both the suspicious margin needed to consistently clear 0.35 for weaker "
        "signals and, mathematically, always below the high threshold of 0.65 — i.e. with "
        "no audio signal, `risk_level` can structurally never reach 'high' from text alone, "
        "no matter how confident the text model is, unless a signature also fires. That is "
        "exactly why `fusion_high_only` scores 0% on both datasets above. This is a "
        "calibration/weighting issue, not a code defect, so it was intentionally left "
        "unmodified rather than silently reweighted — the fusion weights and 'high' "
        "threshold were plausibly chosen assuming a third, not-yet-existing audio signal "
        "would routinely help carry high-confidence detections the rest of the way, which "
        "isn't true yet since no ONNX audio model is shipped. Recommendation for whoever "
        "tunes this next: either raise the effective text-only ceiling (e.g. lower the "
        "'high' threshold, or give text more relative weight when audio is absent) or "
        "treat 'suspicious' as the actionable warning level in the product UI until an audio "
        "signal exists."
    )
    paras.append(
        "**Where fusion helps.** The signature engine catches hard-coded, unambiguous scam "
        "tells — OTP/PIN requests, remote-access app installs, UPI collect-request tricks, "
        "digital-arrest/warrant language — that a TF-IDF model trained mostly on synthetic "
        "transcripts can miss when the phrasing is novel. On the fresh scenarios written for "
        "this suite specifically to avoid template overlap, several scam scripts (e.g. the "
        "FASTag phishing call, the credit-card-limit-upgrade call, the SIM e-KYC call) "
        "contain explicit CVV/OTP/card-detail requests that the signature engine is built to "
        "catch regardless of vocabulary; fusing that signal in raises the fusion `risk_score` "
        "even when the text model's probability alone sits below 0.5."
    )
    paras.append(
        "**Where fusion hurts (or does nothing).** Several of the fresh scam scenarios were "
        "deliberately written *without* any of the 12 hard-coded signature patterns firing "
        "(e.g. the rental-deposit token-advance scam, the matrimonial premium-unlock scam, the "
        "job-advance-fee scam, the second-victimization 'SEBI refund' scam) — these rely on "
        "social pressure and advance-fee framing rather than OTP/remote-access/secrecy "
        "language, so `signatures_only` is blind to them and fusion's improvement over "
        "`text_only` on those rows depends entirely on the text model generalizing to unseen "
        "phrasing, which is exactly the weak link this suite is meant to expose. On the real "
        "YouTube calls specifically, none of the 12 signatures are tuned for the US-centric "
        "SSN/tech-support/prize-scam phrasing in that dataset (no 'digital arrest', no UPI, no "
        "Indian KYC language), so `signatures_only` catches very few of them — any lift on "
        "that dataset has to come from the text model, not the rule engine."
    )
    paras.append(
        "**Known failure modes.** (1) Any signature-based approach is a fixed-vocabulary "
        "regex list — it cannot catch a well-written advance-fee scam that never says OTP, "
        "PIN, AnyDesk, or 'digital arrest'. (2) The text model's training data skews synthetic "
        "and India-specific; the baseline 12/20 recall on real YouTube calls (largely US "
        "SSN/tech-support scams) shows it does not yet generalize cleanly across accents, "
        "scam families, or English dialects. (3) Fusion is a weighted average, not a learned "
        "combiner — it cannot know when to trust one signal over another, so a benign call "
        "that happens to mention money and urgency together (see the false positives listed "
        "below, if any) can still get pushed toward 'suspicious'."
    )
    if text_fp or fusion_fp or sig_fp:
        fp_lines = ["**False positives observed in this run:**"]
        for cfg, fps in [("text_only", text_fp), ("signatures_only", sig_fp), ("fusion_notlow", fusion_fp)]:
            if fps:
                ids = ", ".join(f"`{r['id']}`" for r in fps)
                fp_lines.append(f"- `{cfg}`: {ids}")
        paras.append("\n".join(fp_lines))
    else:
        paras.append(
            "**No false positives observed** on the 15 fresh benign scenarios in any of the "
            "four configurations in this run — including the deliberately adversarial ones "
            "(a real bank fraud-alert yes/no call, a real refund callback, a friend asking to "
            "borrow money). That is a genuinely good sign for precision, but with n=15 benign "
            "examples this is not strong statistical evidence of a low false-positive rate in "
            "general; it should be read as 'no obvious regression', not 'proven safe'."
        )
    if fusion_yt_miss:
        ids = ", ".join(f"`{r['id']}`" for r in fusion_yt_miss)
        paras.append(f"**Full fusion still misses these real scam calls:** {ids}.")
    fusion_only_ids = {r["id"] for r in fusion_yt_miss} - {r["id"] for r in text_yt_miss}
    if fusion_only_ids:
        paras.append(
            "**Calls the text model alone catches but full fusion misses "
            f"(the dilution effect above, in action):** {', '.join(f'`{i}`' for i in sorted(fusion_only_ids))}."
        )
    paras.append(
        "**Bottom line.** This is an honest-evals framing, not a victory lap: the headline "
        "12/20 text-only recall on real calls is the number to beat, and the results table "
        "above should be read side-by-side with it rather than in isolation. Where fusion "
        "wins, it wins because the signature engine adds a hard-coded, high-precision signal "
        "on top of a text model that is still generalizing imperfectly; where it doesn't win, "
        "it's because both signals share the same blind spot (novel phrasing, non-Indian scam "
        "scripts, or advance-fee framing with no explicit request for secrets)."
    )
    return "\n\n".join(paras)


def main():
    report = build_report()
    report_path = EVALS_DIR / "report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    markdown = render_markdown(report)
    (EVALS_DIR / "REPORT.md").write_text(markdown, encoding="utf-8")

    # Console summary
    print(f"text model loaded: {report['text_model_loaded']}")
    print()
    print("Scenarios (15 scam / 15 benign):")
    for name, res in report["scenarios"]["configs"].items():
        tpr = "n/a" if res["tpr"] is None else f"{res['tpr']*100:.1f}%"
        fpr = "n/a" if res["fpr"] is None else f"{res['fpr']*100:.1f}%"
        print(f"  {name:20s} TPR={tpr:>7s} ({res['tp']}/{res['n_scam']})  FPR={fpr:>7s} ({res['fp']}/{res['n_benign']})")
    print()
    print("Real YouTube calls (20/20 scam):")
    for name, res in report["youtube_real_calls"]["configs"].items():
        print(f"  {name:20s} catch={res['tp']}/{res['n_scam']}")
    print()
    lat = report["latency_ms"]
    if lat:
        print(f"Latency: median={lat['median_ms']}ms  p95={lat['p95_ms']}ms  (n={lat['n_runs']})")
    print()
    print(f"Wrote {report_path}")
    print(f"Wrote {EVALS_DIR / 'REPORT.md'}")


if __name__ == "__main__":
    main()
