"""Fine-tune distilbert-base-uncased for Kavach's social-engineering text classifier.

Designed to run on a free Kaggle/Colab GPU notebook -- see KAGGLE.md in this directory
for the exact steps. Heavy imports (torch/transformers/datasets) are deferred so that
`--help` and `python -m py_compile` work even without them installed; the script prints
install instructions and exits if they're missing when actually invoked.

Truncation strategy: transcripts run long (see data/processed/stats.json), so the
default path truncates each transcript to --max_length (512) tokens. Because the
FastAPI backend scores rolling transcript windows in real time rather than a single
final transcript, pass --windowed to *additionally* train on sliding 256-token windows
(stride 128) of every transcript -- each window inherits its parent record's label.
Val/test/youtube are always evaluated on the plain (non-windowed) 512-token truncation.

Run (on a Kaggle/Colab GPU notebook, from the repo root, after `python -m
data_pipeline.build_corpus`):

    python training/text/train_transformer.py --epochs 3 --batch_size 16 --windowed
"""

import argparse
import json
import sys
from pathlib import Path

# __file__ is undefined when this code is pasted into a notebook cell; fall back
# to the current working directory (assumed to be the repo root in that case).
try:
    ROOT = Path(__file__).resolve().parent.parent.parent
except NameError:
    ROOT = Path.cwd()
DATA_DIR_DEFAULT = ROOT / "data" / "processed"
OUTPUT_DIR_DEFAULT = ROOT / "training" / "text" / "output" / "distilbert"

MODEL_NAME = "distilbert-base-uncased"


def parse_args():
    """CLI args. Kept dependency-free so --help works without torch/transformers installed."""
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--data_dir", type=str, default=str(DATA_DIR_DEFAULT),
                    help="dir containing train/val/test/test_real_youtube JSONL (default: data/processed)")
    p.add_argument("--output_dir", type=str, default=str(OUTPUT_DIR_DEFAULT),
                    help="where to write checkpoints, model, tokenizer, metrics, ONNX export")
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch_size", type=int, default=16)
    p.add_argument("--lr", type=float, default=2e-5)
    p.add_argument("--max_length", type=int, default=512)
    p.add_argument("--windowed", action="store_true",
                    help="also train on sliding 256-token/stride-128 windows of each transcript "
                         "(inheriting the parent label), matching real-time rolling-window inference")
    p.add_argument("--window_size", type=int, default=256)
    p.add_argument("--window_stride", type=int, default=128)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def check_heavy_imports():
    """Fail fast with install instructions if torch/transformers/datasets aren't available."""
    missing = []
    for pkg in ("torch", "transformers", "datasets"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Missing required package(s) for transformer fine-tuning: {', '.join(missing)}")
        print()
        print("This script needs a GPU environment (Kaggle/Colab free tier). Install with:")
        print("  pip install torch transformers datasets accelerate scikit-learn")
        print()
        print("See training/text/KAGGLE.md for the exact Kaggle notebook setup.")
        sys.exit(1)


def load_jsonl(path):
    """Load a JSONL file of unified-schema records into a list of dicts."""
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def tokenize_with_windows(record, tokenizer, max_length, windowed, window_size, window_stride):
    """Tokenize one record into one or more training examples.

    Always includes the standard max_length-truncated encoding of the full transcript.
    If windowed, also slices the full token sequence into overlapping windows of
    window_size tokens (stride window_stride), each wrapped with [CLS]/[SEP] and
    inheriting the parent's label -- this is what lets the model see snippet-level
    context matching how the backend scores rolling transcript windows live.
    """
    full = tokenizer(record["text"], truncation=True, max_length=max_length)
    # distilbert's forward doesn't consume token_type_ids; drop it so every example
    # (full-text and windowed) has the same keys (input_ids, attention_mask, label).
    full.pop("token_type_ids", None)
    examples = [{**full, "label": record["label"]}]

    if windowed:
        body_ids = tokenizer(record["text"], add_special_tokens=False)["input_ids"]
        cls_id, sep_id = tokenizer.cls_token_id, tokenizer.sep_token_id
        start = 0
        while start < len(body_ids):
            chunk = body_ids[start:start + window_size]
            if len(chunk) < 8:  # drop tiny tail windows with no real signal
                break
            input_ids = [cls_id] + chunk + [sep_id]
            examples.append({
                "input_ids": input_ids,
                "attention_mask": [1] * len(input_ids),
                "label": record["label"],
            })
            if start + window_size >= len(body_ids):
                break
            start += window_stride
    return examples


def prepare_split(path, tokenizer, max_length, windowed, window_size, window_stride):
    """Load a JSONL split and expand it into a tokenized HF Dataset of examples."""
    from datasets import Dataset

    records = load_jsonl(path)
    examples = []
    for r in records:
        examples.extend(tokenize_with_windows(r, tokenizer, max_length, windowed, window_size, window_stride))
    return Dataset.from_list(examples)


def make_compute_metrics():
    """Build a compute_metrics callback for Trainer (accuracy/precision/recall/F1/ROC-AUC)."""
    import torch
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        probs = torch.softmax(torch.tensor(logits), dim=-1)[:, 1].numpy()
        preds = (probs >= 0.5).astype(int)
        return {
            "accuracy": accuracy_score(labels, preds),
            "precision": precision_score(labels, preds, zero_division=0),
            "recall": recall_score(labels, preds, zero_division=0),
            "f1": f1_score(labels, preds, zero_division=0),
            "roc_auc": roc_auc_score(labels, probs) if len(set(labels)) > 1 else 0.0,
        }

    return compute_metrics


def export_onnx(model, tokenizer, output_dir, max_length):
    """Export the fine-tuned model to ONNX (opset 17, dynamic batch/sequence axes) for the
    FastAPI backend's ONNX Runtime inference path. Guarded: a missing `onnx` package (or
    any export failure) must not fail the overall training run."""
    try:
        import torch

        onnx_path = Path(output_dir) / "model.onnx"
        model.eval()
        dummy = tokenizer(
            "dummy scam call transcript for onnx export tracing",
            return_tensors="pt", truncation=True, max_length=max_length, padding="max_length",
        )
        torch.onnx.export(
            model,
            (dummy["input_ids"], dummy["attention_mask"]),
            str(onnx_path),
            input_names=["input_ids", "attention_mask"],
            output_names=["logits"],
            dynamic_axes={
                "input_ids": {0: "batch", 1: "sequence"},
                "attention_mask": {0: "batch", 1: "sequence"},
                "logits": {0: "batch"},
            },
            opset_version=17,
        )
        print(f"exported ONNX model -> {onnx_path}")
    except Exception as e:  # noqa: BLE001 -- export is best-effort, never fatal
        print(f"ONNX export skipped ({type(e).__name__}: {e}).")
        print("Install `onnx` (pip install onnx) and re-run export separately if needed.")


def main():
    args = parse_args()
    check_heavy_imports()

    import torch
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        DataCollatorWithPadding,
        Trainer,
        TrainingArguments,
        set_seed,
    )

    set_seed(args.seed)
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"loading tokenizer/model: {MODEL_NAME}")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME, num_labels=2)

    print("building datasets ...")
    train_ds = prepare_split(data_dir / "train.jsonl", tokenizer, args.max_length,
                              args.windowed, args.window_size, args.window_stride)
    val_ds = prepare_split(data_dir / "val.jsonl", tokenizer, args.max_length,
                            False, args.window_size, args.window_stride)
    test_ds = prepare_split(data_dir / "test.jsonl", tokenizer, args.max_length,
                             False, args.window_size, args.window_stride)
    youtube_ds = prepare_split(data_dir / "test_real_youtube.jsonl", tokenizer, args.max_length,
                                False, args.window_size, args.window_stride)
    print(f"train={len(train_ds)} examples (windowed={args.windowed}) "
          f"val={len(val_ds)} test={len(test_ds)} youtube_real={len(youtube_ds)}")

    collator = DataCollatorWithPadding(tokenizer=tokenizer)

    training_args = TrainingArguments(
        output_dir=str(output_dir / "checkpoints"),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size * 2,
        learning_rate=args.lr,
        eval_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        logging_steps=50,
        report_to="none",
        seed=args.seed,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=collator,
        compute_metrics=make_compute_metrics(),
    )

    print("training ...")
    trainer.train()

    print("final eval: test.jsonl")
    test_metrics = trainer.evaluate(test_ds, metric_key_prefix="test")
    print(test_metrics)

    print("final eval: test_real_youtube.jsonl (real-world probe)")
    youtube_metrics = trainer.evaluate(youtube_ds, metric_key_prefix="youtube")
    print(youtube_metrics)

    youtube_records = load_jsonl(data_dir / "test_real_youtube.jsonl")
    yt_predictions = trainer.predict(youtube_ds)
    yt_probs = torch.softmax(torch.tensor(yt_predictions.predictions), dim=-1)[:, 1].numpy()
    youtube_per_record = [
        {"id": r["id"], "scam_type": r["scam_type"], "prob_scam": float(p), "flagged": bool(p >= 0.5)}
        for r, p in zip(youtube_records, yt_probs)
    ]
    flagged = sum(1 for r in youtube_per_record if r["flagged"])

    metrics = {
        "model": MODEL_NAME,
        "args": vars(args),
        "n_train_examples": len(train_ds),
        "n_val_examples": len(val_ds),
        "n_test_examples": len(test_ds),
        "test": test_metrics,
        "youtube_real_probe": {
            **youtube_metrics,
            "n": len(youtube_ds),
            "flagged_at_0.5": flagged,
            "recall_at_0.5": flagged / len(youtube_ds) if len(youtube_ds) else None,
            "records": youtube_per_record,
        },
    }
    metrics_path = output_dir / "transformer_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print(f"saved metrics -> {metrics_path}")

    print("saving model + tokenizer ...")
    model_dir = output_dir / "model"
    trainer.save_model(str(model_dir))
    tokenizer.save_pretrained(str(model_dir))

    export_onnx(model, tokenizer, output_dir, args.max_length)

    print("\n=== SUMMARY ===")
    print(f"test metrics: {test_metrics}")
    print(f"youtube real probe: {flagged}/{len(youtube_ds)} flagged at threshold 0.5")
    print(f"model saved to {model_dir}")


if __name__ == "__main__":
    main()
