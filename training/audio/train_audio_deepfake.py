"""Fine-tune facebook/wav2vec2-base for Kavach's voice-deepfake (anti-spoofing) detector.

Binary classification: bonafide(0) vs spoof(1). Trains/dev-selects/evals on ASVspoof 2019
LA, then reports the cross-dataset headline eval on In-the-Wild (a model that only looks
good on ASVspoof and falls apart on In-the-Wild is not useful -- see README "Why").

Designed to run on a free Kaggle GPU notebook -- see KAGGLE.md in this directory for the
exact steps. Heavy imports (torch/transformers/soundfile/librosa/sklearn) are deferred so
that `--help`, `--smoke`, and `python -m py_compile` behave well even in partial
environments; the script prints install instructions and exits if something required is
missing.

Dataset discovery (do NOT hardcode Kaggle's deep mount paths -- they change across
dataset versions): pass --asvspoof_root / --itw_root pointing at (or above) the dataset
directories, and this script globs for the known marker files/dirs:
  - ASVspoof 2019 LA: a directory literally named `ASVspoof2019_LA_cm_protocols` anywhere
    under --asvspoof_root, containing the `*.cm.{train.trn,dev.trl,eval.trl}.txt`
    protocol files (whitespace-separated: speaker_id, utt_id, -, attack_id, key; key is
    `bonafide`/`spoof`). Audio lives in sibling `ASVspoof2019_LA_{train,dev,eval}/flac/
    <utt_id>.flac` directories.
  - In-the-Wild: a file named `meta.csv` anywhere under --itw_root (columns: file,
    speaker, label; label is `bona-fide`/`spoof`), with the .wav files alongside it.
Discovery failures raise a clear error listing what was actually found so you can see
whether the Kaggle dataset mount just uses a different layout than expected.

Run (on a Kaggle GPU notebook, from the repo root -- see KAGGLE.md for full setup):

    python training/audio/train_audio_deepfake.py \\
        --asvspoof_root /kaggle/input/asvpoof-2019-dataset \\
        --itw_root /kaggle/input/release-in-the-wild \\
        --output_dir training/audio/output --epochs 2 --batch_size 16

Smoke test (no downloads beyond the wav2vec2-base checkpoint, CPU-friendly, exercises
the entire loop -- train/eval/metrics/ONNX export -- on tiny synthetic random waveforms):

    python training/audio/train_audio_deepfake.py --smoke
"""

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR_DEFAULT = ROOT / "training" / "audio" / "output"

MODEL_NAME = "facebook/wav2vec2-base"
SAMPLE_RATE = 16000


def parse_args():
    """CLI args. Kept dependency-free so --help works without torch/transformers installed."""
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--asvspoof_root", type=str, default=None,
                    help="path to (or above) the ASVspoof 2019 LA dataset "
                         "(e.g. Kaggle input dir for awsaf49/asvpoof-2019-dataset). "
                         "Required unless --smoke.")
    p.add_argument("--itw_root", type=str, default=None,
                    help="path to (or above) the In-the-Wild dataset "
                         "(e.g. Kaggle input dir for bhaveshkumars/release-in-the-wild). "
                         "Required unless --smoke.")
    p.add_argument("--output_dir", type=str, default=str(OUTPUT_DIR_DEFAULT),
                    help="where to write checkpoints, metrics, ONNX export")
    p.add_argument("--epochs", type=int, default=2)
    p.add_argument("--batch_size", type=int, default=16)
    p.add_argument("--lr", type=float, default=3e-5, help="learning rate for the wav2vec2 backbone")
    p.add_argument("--head_lr", type=float, default=1e-4, help="learning rate for the classification head")
    p.add_argument("--max_seconds", type=float, default=4.0,
                    help="fixed clip length in seconds: random crop in training, center crop at eval")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--freeze_feature_extractor", action=argparse.BooleanOptionalAction, default=True,
                    help="freeze the wav2vec2 CNN feature encoder (not the transformer "
                         "layers); default true, matches common wav2vec2 fine-tuning practice")
    p.add_argument("--limit_train", type=int, default=0,
                    help="cap number of training utterances for quick runs (0 = use all)")
    p.add_argument("--num_workers", type=int, default=0,
                    help="DataLoader worker processes (0 = main process only; safest on Windows/Kaggle)")
    p.add_argument("--smoke", action="store_true",
                    help="run the entire train/eval/metrics/ONNX loop on a tiny in-memory "
                         "synthetic dataset of random waveforms -- no dataset paths needed, "
                         "no downloads beyond the wav2vec2-base checkpoint, CPU-friendly")
    return p.parse_args()


def check_heavy_imports(need_audio_libs):
    """Fail fast with install instructions if required packages aren't available."""
    missing = []
    for pkg in ("torch", "transformers", "sklearn", "numpy", "tqdm"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if need_audio_libs:
        for pkg in ("soundfile", "librosa"):
            try:
                __import__(pkg)
            except ImportError:
                missing.append(pkg)
    if missing:
        print(f"Missing required package(s): {', '.join(missing)}")
        print()
        print("This script needs a GPU environment (Kaggle free tier) for real training, "
              "or a plain CPU env for --smoke. Install with:")
        print("  pip install torch transformers soundfile librosa scikit-learn numpy tqdm onnx")
        print()
        print("See training/audio/KAGGLE.md for the exact Kaggle notebook setup.")
        sys.exit(1)


# --------------------------------------------------------------------------------------
# Dataset discovery + parsing
# --------------------------------------------------------------------------------------

def discover_asvspoof(root):
    """Locate the ASVspoof2019 LA protocol dir + per-split protocol files + flac audio dirs
    under `root`, without assuming a fixed nesting depth (Kaggle dataset mounts vary)."""
    root = Path(root)
    if not root.exists():
        raise FileNotFoundError(f"--asvspoof_root {root} does not exist")

    protocol_dirs = [p for p in root.rglob("ASVspoof2019_LA_cm_protocols") if p.is_dir()]
    if not protocol_dirs:
        found_dirs = sorted({p.name for p in root.rglob("*") if p.is_dir()})
        raise FileNotFoundError(
            f"Could not find a directory named 'ASVspoof2019_LA_cm_protocols' under "
            f"{root}.\nDirectory names found under --asvspoof_root "
            f"(up to 60): {found_dirs[:60]}\n"
            "Expected the standard ASVspoof2019 LA layout: a "
            "*_cm_protocols dir with the .txt protocol files, and sibling "
            "ASVspoof2019_LA_{train,dev,eval} dirs each containing a flac/ subdir."
        )
    protocols_dir = protocol_dirs[0]
    la_root = protocols_dir.parent

    split_protocol_glob = {
        "train": "*.cm.train.trn.txt",
        "dev": "*.cm.dev.trl.txt",
        "eval": "*.cm.eval.trl.txt",
    }
    splits = {}
    for split, pattern in split_protocol_glob.items():
        matches = sorted(protocols_dir.glob(pattern))
        if not matches:
            # be defensive: some mirrors rename/rearrange suffixes slightly
            matches = sorted(p for p in protocols_dir.glob("*.txt") if split in p.name.lower())
        if not matches:
            raise FileNotFoundError(
                f"Could not find a '{split}' protocol file (expected pattern "
                f"'{pattern}') in {protocols_dir}.\n"
                f"Files present: {sorted(p.name for p in protocols_dir.glob('*.txt'))}"
            )
        protocol_file = matches[0]

        audio_dirs = [p for p in la_root.rglob(f"ASVspoof2019_LA_{split}") if p.is_dir()]
        if not audio_dirs:
            raise FileNotFoundError(
                f"Could not find audio directory 'ASVspoof2019_LA_{split}' under {la_root}.\n"
                f"Entries under {la_root}: {sorted(p.name for p in la_root.iterdir())}"
            )
        flac_dir = audio_dirs[0] / "flac"
        if not flac_dir.is_dir():
            flac_candidates = [p for p in audio_dirs[0].rglob("flac") if p.is_dir()]
            if not flac_candidates:
                raise FileNotFoundError(
                    f"Found audio dir {audio_dirs[0]} but no nested 'flac' directory inside it."
                )
            flac_dir = flac_candidates[0]
        splits[split] = {"protocol": protocol_file, "flac_dir": flac_dir}
    return splits


def parse_asvspoof_protocol(protocol_path, flac_dir):
    """Parse a whitespace-separated ASVspoof2019 LA CM protocol file into
    [{"path", "label", "utt_id"}]. label: 0=bonafide, 1=spoof."""
    items = []
    with open(protocol_path, encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if len(parts) < 5:
                continue
            utt_id = parts[1]
            key = parts[-1].strip().lower()
            if key not in ("bonafide", "spoof"):
                continue
            items.append({
                "path": str(flac_dir / f"{utt_id}.flac"),
                "label": 0 if key == "bonafide" else 1,
                "utt_id": utt_id,
            })
    if not items:
        raise ValueError(
            f"Parsed 0 usable (bonafide/spoof) rows from {protocol_path}; check the file format."
        )
    return items


def discover_itw(root):
    """Locate In-the-Wild's meta.csv under `root` (Kaggle mount layout varies)."""
    root = Path(root)
    if not root.exists():
        raise FileNotFoundError(f"--itw_root {root} does not exist")
    meta_files = sorted(root.rglob("meta.csv"))
    if not meta_files:
        found = sorted({p.name for p in root.rglob("*") if p.is_file()})
        raise FileNotFoundError(
            f"Could not find 'meta.csv' under {root}.\n"
            f"File names found under --itw_root (up to 60): {found[:60]}\n"
            "Expected the In-the-Wild release layout: meta.csv (columns file, speaker, "
            "label) with .wav files in the same directory."
        )
    meta_path = meta_files[0]
    return meta_path, meta_path.parent


def parse_itw(meta_path, audio_dir):
    """Parse In-the-Wild's meta.csv into [{"path", "label"}]. label: 0=bona-fide, 1=spoof."""
    items = []
    with open(meta_path, encoding="utf-8", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
        except csv.Error:
            dialect = csv.excel  # default comma-separated
        reader = csv.DictReader(f, dialect=dialect)
        reader.fieldnames = [h.strip().lower() for h in (reader.fieldnames or [])]
        for row in reader:
            row = {k.strip().lower(): (v.strip() if v else v) for k, v in row.items() if k}
            label_raw = (row.get("label") or "").lower()
            if label_raw not in ("bona-fide", "spoof"):
                continue
            fname = row.get("file") or ""
            if not fname:
                continue
            if not Path(fname).suffix:
                fname = fname + ".wav"
            items.append({
                "path": str(audio_dir / fname),
                "label": 0 if label_raw == "bona-fide" else 1,
            })
    if not items:
        raise ValueError(
            f"Parsed 0 usable (bona-fide/spoof) rows from {meta_path}; check column names "
            f"(expected 'file' and 'label')."
        )
    return items


def make_smoke_items(n, seed_offset, sample_rate, max_seconds):
    """Tiny in-memory synthetic dataset: random waveforms, alternating labels, already
    fixed-length so --smoke never touches soundfile/librosa or the network beyond HF Hub."""
    import numpy as np

    rng = np.random.default_rng(1000 + seed_offset)
    length = int(max_seconds * sample_rate)
    items = []
    for i in range(n):
        wav = (rng.standard_normal(length).astype("float32")) * 0.05
        items.append({"waveform": wav, "label": i % 2})
    return items


# --------------------------------------------------------------------------------------
# Audio loading + torch Dataset
# --------------------------------------------------------------------------------------

def load_waveform(path, max_seconds, train, rng, target_sr=SAMPLE_RATE):
    """Load an audio file, resample to target_sr mono, then random-crop (train) or
    center-crop (eval) to a fixed max_seconds length, padding with zeros if shorter."""
    import numpy as np
    import soundfile as sf

    try:
        wav, sr = sf.read(path, dtype="float32", always_2d=False)
    except Exception:
        import librosa
        wav, sr = librosa.load(path, sr=None, mono=True)

    wav = np.asarray(wav, dtype="float32")
    if wav.ndim > 1:
        wav = wav.mean(axis=1)
    if sr != target_sr:
        import librosa
        wav = librosa.resample(wav, orig_sr=sr, target_sr=target_sr)

    target_len = int(max_seconds * target_sr)
    if len(wav) < target_len:
        wav = np.pad(wav, (0, target_len - len(wav)))
    elif len(wav) > target_len:
        if train:
            start = int(rng.integers(0, len(wav) - target_len + 1))
        else:
            start = (len(wav) - target_len) // 2
        wav = wav[start:start + target_len]
    return wav.astype("float32")


def make_dataset_class():
    """Build the torch Dataset class lazily (needs torch installed)."""
    import numpy as np
    import torch
    from torch.utils.data import Dataset

    class SpoofAudioDataset(Dataset):
        def __init__(self, items, max_seconds, train, seed=0):
            self.items = items
            self.max_seconds = max_seconds
            self.train = train
            self.rng = np.random.default_rng(seed)

        def __len__(self):
            return len(self.items)

        def __getitem__(self, idx):
            item = self.items[idx]
            if "waveform" in item:
                wav = item["waveform"]
            else:
                wav = load_waveform(item["path"], self.max_seconds, self.train, self.rng)
            return torch.from_numpy(wav), float(item["label"])

    return SpoofAudioDataset


def collate_batch(batch):
    import torch
    waveforms = torch.stack([b[0] for b in batch])
    labels = torch.tensor([b[1] for b in batch], dtype=torch.float32)
    return waveforms, labels


# --------------------------------------------------------------------------------------
# Model
# --------------------------------------------------------------------------------------

def build_model(freeze_feature_extractor, dropout=0.1):
    import torch.nn as nn
    from transformers import Wav2Vec2Model

    class Wav2Vec2SpoofClassifier(nn.Module):
        def __init__(self):
            super().__init__()
            self.wav2vec2 = Wav2Vec2Model.from_pretrained(MODEL_NAME)
            if freeze_feature_extractor:
                self.wav2vec2.feature_extractor._freeze_parameters()
            self.dropout = nn.Dropout(dropout)
            self.classifier = nn.Linear(self.wav2vec2.config.hidden_size, 1)

        def forward(self, input_values):
            hidden = self.wav2vec2(input_values).last_hidden_state  # (B, T, H)
            pooled = hidden.mean(dim=1)  # mean-pool over time
            logits = self.classifier(self.dropout(pooled)).squeeze(-1)  # (B,)
            return logits

    return Wav2Vec2SpoofClassifier()


# --------------------------------------------------------------------------------------
# Metrics
# --------------------------------------------------------------------------------------

def compute_eer(labels, scores):
    """Equal Error Rate from the ROC curve: the point where the false-positive rate
    equals the false-negative rate (1 - true-positive rate). `scores` = predicted P(spoof)."""
    import numpy as np
    from sklearn.metrics import roc_curve

    fpr, tpr, _ = roc_curve(labels, scores)
    fnr = 1 - tpr
    idx = int(np.nanargmin(np.abs(fnr - fpr)))
    eer = float((fpr[idx] + fnr[idx]) / 2.0)
    return eer


def evaluate_split(model, loader, device):
    """Run inference over a loader, return (metrics_dict, labels, scores)."""
    import numpy as np
    import torch
    from sklearn.metrics import accuracy_score, roc_auc_score

    model.eval()
    all_labels, all_scores = [], []
    with torch.no_grad():
        for waveforms, labels in loader:
            waveforms = waveforms.to(device)
            logits = model(waveforms)
            probs = torch.sigmoid(logits).cpu().numpy()
            all_scores.extend(probs.tolist())
            all_labels.extend(labels.numpy().tolist())

    all_labels = np.array(all_labels)
    all_scores = np.array(all_scores)
    preds = (all_scores >= 0.5).astype(int)

    if len(set(all_labels.tolist())) > 1:
        auc = float(roc_auc_score(all_labels, all_scores))
        eer = compute_eer(all_labels, all_scores)
    else:
        # degenerate (e.g. tiny smoke set with only one class in a split) -- can't
        # define ROC-based metrics, report neutral placeholders instead of crashing
        auc, eer = 0.5, 0.5
    metrics = {
        "eer": eer,
        "roc_auc": auc,
        "accuracy_at_0.5": float(accuracy_score(all_labels, preds)),
        "n": int(len(all_labels)),
    }
    return metrics


# --------------------------------------------------------------------------------------
# ONNX export
# --------------------------------------------------------------------------------------

def export_onnx(model, output_dir, max_seconds, sample_rate=SAMPLE_RATE):
    """Export the fine-tuned model to ONNX (opset 17, dynamic time axis) for the FastAPI
    backend's ONNX Runtime inference path. Guarded: a missing `onnx` package (or any
    export failure) must not fail the overall training run."""
    try:
        import torch

        onnx_path = Path(output_dir) / "kavach_audio.onnx"
        model.eval()
        model_cpu = model.to("cpu")
        dummy = torch.zeros(1, int(max_seconds * sample_rate))
        torch.onnx.export(
            model_cpu,
            (dummy,),
            str(onnx_path),
            input_names=["input_values"],
            output_names=["logits"],
            dynamic_axes={
                "input_values": {0: "batch", 1: "time"},
                "logits": {0: "batch"},
            },
            opset_version=17,
            dynamo=False,  # classic TorchScript-based exporter: predictable opset,
                            # no rich console reporting (which can crash on Windows'
                            # cp1252 console when torch's dynamo exporter tries to
                            # print unicode checkmarks)
        )
        print(f"exported ONNX model -> {onnx_path}")
    except Exception as e:  # noqa: BLE001 -- export is best-effort, never fatal
        print(f"ONNX export skipped ({type(e).__name__}: {e}).")
        print("Install `onnx` (pip install onnx) and re-run export separately if needed.")


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------

def main():
    args = parse_args()
    if not args.smoke and (not args.asvspoof_root or not args.itw_root):
        print("--asvspoof_root and --itw_root are required unless --smoke is set.")
        sys.exit(1)

    check_heavy_imports(need_audio_libs=not args.smoke)

    import numpy as np
    import torch
    from torch.utils.data import DataLoader
    from tqdm import tqdm
    from transformers import set_seed

    set_seed(args.seed)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_amp = device.type == "cuda"
    print(f"device={device} mixed_precision={use_amp}")

    epochs = args.epochs
    batch_size = args.batch_size
    max_seconds = args.max_seconds

    if args.smoke:
        print("SMOKE MODE: synthetic in-memory dataset, no dataset paths / downloads "
              "beyond the wav2vec2-base checkpoint.")
        # Keep it fast on CPU: short clips, tiny sets, exactly 2 optimizer steps.
        max_seconds = min(max_seconds, 2.0)
        batch_size = min(batch_size, 4)
        epochs = 1
        train_items = make_smoke_items(8, 0, SAMPLE_RATE, max_seconds)
        dev_items = make_smoke_items(4, 1, SAMPLE_RATE, max_seconds)
        eval19_items = make_smoke_items(4, 2, SAMPLE_RATE, max_seconds)
        itw_items = make_smoke_items(4, 3, SAMPLE_RATE, max_seconds)
    else:
        print(f"discovering ASVspoof 2019 LA under {args.asvspoof_root} ...")
        asv_splits = discover_asvspoof(args.asvspoof_root)
        train_items = parse_asvspoof_protocol(asv_splits["train"]["protocol"], asv_splits["train"]["flac_dir"])
        if args.limit_train:
            train_items = train_items[:args.limit_train]
        dev_items = parse_asvspoof_protocol(asv_splits["dev"]["protocol"], asv_splits["dev"]["flac_dir"])
        eval19_items = parse_asvspoof_protocol(asv_splits["eval"]["protocol"], asv_splits["eval"]["flac_dir"])
        print(f"  train={len(train_items)} dev={len(dev_items)} eval={len(eval19_items)}")

        print(f"discovering In-the-Wild under {args.itw_root} ...")
        meta_path, itw_audio_dir = discover_itw(args.itw_root)
        itw_items = parse_itw(meta_path, itw_audio_dir)
        print(f"  in-the-wild={len(itw_items)} (meta: {meta_path})")

    DatasetCls = make_dataset_class()
    train_ds = DatasetCls(train_items, max_seconds, train=True, seed=args.seed)
    dev_ds = DatasetCls(dev_items, max_seconds, train=False, seed=args.seed)
    eval19_ds = DatasetCls(eval19_items, max_seconds, train=False, seed=args.seed)
    itw_ds = DatasetCls(itw_items, max_seconds, train=False, seed=args.seed)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,
                               num_workers=args.num_workers, collate_fn=collate_batch)
    dev_loader = DataLoader(dev_ds, batch_size=batch_size, shuffle=False,
                             num_workers=args.num_workers, collate_fn=collate_batch)
    eval19_loader = DataLoader(eval19_ds, batch_size=batch_size, shuffle=False,
                                num_workers=args.num_workers, collate_fn=collate_batch)
    itw_loader = DataLoader(itw_ds, batch_size=batch_size, shuffle=False,
                             num_workers=args.num_workers, collate_fn=collate_batch)

    print(f"loading model: {MODEL_NAME} (freeze_feature_extractor={args.freeze_feature_extractor})")
    model = build_model(args.freeze_feature_extractor).to(device)

    backbone_params = list(model.wav2vec2.parameters())
    head_params = list(model.classifier.parameters())
    optimizer = torch.optim.AdamW([
        {"params": backbone_params, "lr": args.lr},
        {"params": head_params, "lr": args.head_lr},
    ])
    loss_fn = torch.nn.BCEWithLogitsLoss()
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)

    max_smoke_steps = 2 if args.smoke else None
    best_eer = float("inf")
    best_state = None

    for epoch in range(1, epochs + 1):
        model.train()
        running_loss, n_steps = 0.0, 0
        pbar = tqdm(train_loader, desc=f"epoch {epoch}/{epochs}")
        for step, (waveforms, labels) in enumerate(pbar):
            if max_smoke_steps is not None and step >= max_smoke_steps:
                break
            waveforms, labels = waveforms.to(device), labels.to(device)
            optimizer.zero_grad()
            with torch.amp.autocast("cuda", enabled=use_amp):
                logits = model(waveforms)
                loss = loss_fn(logits, labels)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            running_loss += loss.item()
            n_steps += 1
            pbar.set_postfix(loss=running_loss / max(n_steps, 1))

        dev_metrics = evaluate_split(model, dev_loader, device)
        print(f"epoch {epoch}: train_loss={running_loss / max(n_steps, 1):.4f} "
              f"dev_eer={dev_metrics['eer']:.4f} dev_auc={dev_metrics['roc_auc']:.4f} "
              f"dev_acc={dev_metrics['accuracy_at_0.5']:.4f}")

        if dev_metrics["eer"] <= best_eer:
            best_eer = dev_metrics["eer"]
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    if best_state is not None:
        model.load_state_dict(best_state)
    model.to(device)

    print("final eval: ASVspoof2019 LA eval split")
    eval19_metrics = evaluate_split(model, eval19_loader, device)
    print(eval19_metrics)

    print("final eval: In-the-Wild (cross-dataset headline)")
    itw_metrics = evaluate_split(model, itw_loader, device)
    print(itw_metrics)

    metrics = {
        "model": MODEL_NAME,
        "args": vars(args),
        "n_train": len(train_items),
        "n_dev": len(dev_items),
        "n_eval19": len(eval19_items),
        "n_itw": len(itw_items),
        "best_dev_eer": best_eer,
        "asvspoof19_eval": eval19_metrics,
        "in_the_wild_cross_dataset": itw_metrics,
    }
    metrics_path = output_dir / "audio_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)
    print(f"saved metrics -> {metrics_path}")

    model_path = output_dir / "kavach_audio.pt"
    torch.save(model.state_dict(), model_path)
    print(f"saved model state_dict -> {model_path}")

    export_onnx(model, output_dir, max_seconds)

    print("\n=== SUMMARY ===")
    print(f"best dev EER: {best_eer:.4f}")
    print(f"ASVspoof19 eval: EER={eval19_metrics['eer']:.4f} AUC={eval19_metrics['roc_auc']:.4f}")
    print(f"In-the-Wild (cross-dataset): EER={itw_metrics['eer']:.4f} AUC={itw_metrics['roc_auc']:.4f}")
    print(f"model saved to {model_path}")


if __name__ == "__main__":
    main()
