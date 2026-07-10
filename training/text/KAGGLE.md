# Running `train_transformer.py` on Kaggle (free GPU)

`train_transformer.py` fine-tunes `distilbert-base-uncased` on the Kavach corpus. It needs
a GPU and takes a few minutes per epoch on Kaggle's free T4 -- do not attempt this on a
CPU-only laptop. These are the exact steps.

## 1. Push the repo to GitHub

From your machine (once, or whenever you have new commits):

```
git push origin main
```

Kaggle notebooks can `git clone` a public repo directly, or you can attach a private
repo via a GitHub personal access token if the hackathon repo is private.

## 2. Create a Kaggle notebook with GPU enabled

1. Go to https://www.kaggle.com/code -> **New Notebook**.
2. Right sidebar -> **Settings** -> **Accelerator** -> choose **GPU T4 x2** (or **GPU P100**).
3. Right sidebar -> **Settings** -> **Internet** -> toggle **On** (needed to `git clone` and
   to download `distilbert-base-uncased` weights from the HF Hub).

## 3. Clone the repo and install dependencies

In the first notebook cell:

```bash
!git clone https://github.com/<your-username>/<your-repo>.git kavach
%cd kavach
!pip install -q -U transformers datasets accelerate scikit-learn onnx
```

(`torch` is already preinstalled on Kaggle GPU images with CUDA wired up correctly --
do not `pip install torch` on Kaggle, it will usually pull a mismatched CUDA build.)

## 4. Build the data corpus

The processed JSONL files are gitignored (only `stats.json` is committed), so rebuild
them inside the notebook:

```bash
!pip install -q datasets scikit-learn pandas
!python -m data_pipeline.build_corpus
```

This writes `data/processed/{train,val,test,test_real_youtube}.jsonl`.

## 5. Run the fine-tuning script

Plain 512-token truncation:

```bash
!python training/text/train_transformer.py \
    --epochs 3 --batch_size 16 --lr 2e-5 --max_length 512 \
    --output_dir training/text/output/distilbert
```

Or, to also train on sliding 256-token/stride-128 windows (recommended -- this matches
how the backend scores rolling transcript windows live):

```bash
!python training/text/train_transformer.py \
    --epochs 3 --batch_size 16 --lr 2e-5 --max_length 512 --windowed \
    --output_dir training/text/output/distilbert_windowed
```

Watch for the per-epoch val metrics Trainer prints, then the final `test` and
`youtube_real_probe` blocks at the end -- the youtube probe is the honest,
never-trained-on real-world check.

## 6. Download the artifacts

The script writes, under `--output_dir`:

- `model/` -- `pytorch_model.bin`/`model.safetensors` + tokenizer files (fine-tuned DistilBERT)
- `model.onnx` -- ONNX export (opset 17, dynamic batch/sequence axes) for the FastAPI
  ONNX Runtime inference path -- skipped with a printed message if `onnx` isn't installed
- `transformer_metrics.json` -- test + youtube-real metrics, args, per-record youtube probs

Zip and download via the Kaggle notebook's **Output** panel, or:

```bash
!zip -r distilbert_artifacts.zip training/text/output
```

then use the **Data** -> **Output** download button, or `kaggle kernels output` from the
Kaggle CLI. Copy `model.onnx` into `models/` locally (gitignored) and
`transformer_metrics.json` into `training/text/` if you want to commit it alongside
`baseline_metrics.json`.
