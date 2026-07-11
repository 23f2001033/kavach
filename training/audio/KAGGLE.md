# Running `train_audio_deepfake.py` on Kaggle (free GPU)

`train_audio_deepfake.py` fine-tunes `facebook/wav2vec2-base` into a bonafide-vs-spoof
(anti-spoofing) classifier on ASVspoof 2019 LA, then reports the honest cross-dataset
headline eval on In-the-Wild. It needs a GPU (a CPU run would take hours) -- these are
the exact Kaggle notebook steps.

## 1. Create a Kaggle notebook and attach both datasets

1. Go to https://www.kaggle.com/code -> **New Notebook**.
2. Right sidebar -> **Add Input** -> search and attach:
   - `awsaf49/asvpoof-2019-dataset` (ASVspoof 2019 LA)
   - `bhaveshkumars/release-in-the-wild` (In-the-Wild)
3. Right sidebar -> **Settings** -> **Accelerator** -> **GPU T4 x2** (or **GPU P100**).
4. Right sidebar -> **Settings** -> **Internet** -> toggle **On** (needed to `git clone`
   and to download `facebook/wav2vec2-base` weights from the HF Hub).

Once attached, the datasets are mounted read-only under `/kaggle/input/asvpoof-2019-dataset/`
and `/kaggle/input/release-in-the-wild/` -- the exact nesting inside each varies by
dataset version, which is why the script *discovers* the protocol/meta files by globbing
instead of hardcoding a deep path (see the module docstring in `train_audio_deepfake.py`
for the discovery rules, and the clear error it raises if the layout doesn't match).

## 2. Clone the repo and install dependencies

In the first notebook cell:

```bash
!git clone https://github.com/23f2001033/kavach.git kavach
%cd kavach
!pip install -q -U transformers soundfile librosa scikit-learn tqdm onnx
```

(`torch` is already preinstalled on Kaggle GPU images with CUDA wired up correctly --
do not `pip install torch` on Kaggle, it will usually pull a mismatched CUDA build.)

## 3. Run the fine-tuning script

```bash
!python training/audio/train_audio_deepfake.py \
    --asvspoof_root /kaggle/input/asvpoof-2019-dataset \
    --itw_root /kaggle/input/release-in-the-wild \
    --output_dir training/audio/output \
    --epochs 2 --batch_size 16 --lr 3e-5 --head_lr 1e-4 --max_seconds 4
```

For a quick sanity run on a subset first (a few minutes), add `--limit_train 2000`.

Watch for the per-epoch `dev_eer`/`dev_auc` line -- the best-by-EER checkpoint (on the
ASVspoof19 LA dev split) is what gets carried into the final evals and saved.

### Expected runtime

ASVspoof 2019 LA train is ~25,380 utterances. On a Kaggle T4, wav2vec2-base fine-tuning
with 4 s clips, batch size 16, feature-extractor frozen, runs roughly **20-35 min/epoch**
(2 epochs ~= **45-70 min total**, plus a few minutes for the final eval/In-the-Wild pass
and model download from the HF Hub the first time). P100 is somewhat faster than T4.
If you're tight on the ~9h/week Kaggle GPU quota, `--limit_train` a subset first to
confirm the pipeline end-to-end before committing to a full run.

## 4. Download the artifacts

The script writes, under `--output_dir` (`training/audio/output/` by default):

- `kavach_audio.pt` -- fine-tuned model `state_dict()` (PyTorch)
- `kavach_audio.onnx` -- ONNX export (opset 17, dynamic time axis) for the FastAPI ONNX
  Runtime inference path -- skipped with a printed message if the export fails (e.g.
  `onnx` not installed); re-run the export separately if needed
- `audio_metrics.json` -- args, best dev EER, and the two headline eval blocks:
  `asvspoof19_eval` (EER/ROC-AUC/accuracy@0.5 on the ASVspoof19 LA eval split) and
  `in_the_wild_cross_dataset` (the same metrics on In-the-Wild -- the number that
  actually matters for "does this generalize")

Zip and download via the Kaggle notebook's **Output** panel, or:

```bash
!zip -r audio_artifacts.zip training/audio/output
```

then use the **Data** -> **Output** download button, or `kaggle kernels output` from the
Kaggle CLI. Locally, place the downloaded files at:

- `models/kavach_audio.onnx` (gitignored -- this is what the FastAPI backend loads)
- `models/kavach_audio.pt` (gitignored -- kept for further fine-tuning/debugging)
- `training/audio/audio_metrics.json` (safe to commit alongside this script, mirrors how
  `training/text/baseline_metrics.json` is tracked)

## 5. Smoke-test first if you're touching the script

Before spending GPU quota, verify the script still runs end-to-end (train/eval/metrics/
ONNX export) on a tiny synthetic in-memory dataset -- no dataset attachment or GPU
needed, runs on CPU in a couple of minutes:

```bash
!python training/audio/train_audio_deepfake.py --smoke
```

