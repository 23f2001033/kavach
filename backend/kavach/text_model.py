"""Text scam-likelihood scorer.

Two implementations of `BaseTextScorer` are available:

- `DistilBertScorer` (preferred, see `get_text_scorer()`): loads the
  fine-tuned distilbert-base-uncased classifier produced by
  training/text/train_transformer.py from models/distilbert/model
  (config.json + model.safetensors + tokenizer files). Trained with sliding
  256-token windows (stride 128) up to max_length 512 -- see that script's
  docstring and models/distilbert/transformer_metrics.json for training-time
  metrics (99.8% test accuracy; 17/20 real held-out YouTube scam calls caught
  at threshold 0.5, vs. the TF-IDF baseline's 12/20).
- `TfidfLogRegScorer` (fallback): the original TF-IDF(word 1-2gram + char
  3-5gram) + LogisticRegression baseline produced by
  training/text/train_baseline.py. That script saves a dict
  ``{"vectorizer": FeatureUnion, "clf": LogisticRegression, "best_C": float}``
  to models/text_baseline.joblib — NOT a single sklearn Pipeline — so the
  loader below handles that shape directly, while still accepting a plain
  estimator/Pipeline with .predict_proba([str, ...]) if a future export
  changes shape.

`get_text_scorer()` prefers DistilBERT when models/distilbert/model exists
(and torch/transformers are installed), else falls back to the joblib
baseline, else the baseline's own "not loaded" degradation (score() -> None,
is_loaded=False) — nothing else in the backend needs to change based on
which one loaded; callers only ever see the `BaseTextScorer` interface.
"""
import logging
import warnings
from abc import ABC, abstractmethod
from typing import List, Optional

import joblib

from . import config

logger = logging.getLogger("kavach.text_model")

try:
    import torch  # type: ignore
    from transformers import AutoModelForSequenceClassification, AutoTokenizer  # type: ignore
except ImportError:  # pragma: no cover - exercised whenever torch/transformers aren't installed
    torch = None
    AutoModelForSequenceClassification = None
    AutoTokenizer = None


class BaseTextScorer(ABC):
    """Interface every text scam-scorer must implement."""

    #: short machine-readable name reported by GET /health (e.g. "distilbert",
    #: "baseline"); used by kavach/api.py, not by scoring logic itself.
    name = "unknown"

    @abstractmethod
    def score(self, transcript: str) -> Optional[float]:
        """Return P(scam) in [0, 1], or None if no model is available/loaded."""

    @property
    @abstractmethod
    def is_loaded(self) -> bool:
        ...


class TfidfLogRegScorer(BaseTextScorer):
    """Loads models/text_baseline.joblib. Never raises: if the file is missing
    or malformed, logs+warns clearly at startup and every .score() call simply
    returns None, so the rest of the service (signatures + fusion) keeps
    working with graceful degradation."""

    name = "baseline"

    def __init__(self, model_path=None):
        self.model_path = model_path or config.TEXT_MODEL_PATH
        self._vectorizer = None
        self._clf = None
        self._load()

    def _load(self) -> None:
        if not self.model_path.exists():
            msg = (
                f"[kavach.text_model] STARTUP WARNING: text model not found at "
                f"'{self.model_path}'. Text scoring is DISABLED (score() -> None); "
                f"risk will fall back to signature-only detection. Run "
                f"training/text/train_baseline.py to produce it."
            )
            warnings.warn(msg)
            logger.warning(msg)
            return
        try:
            artifact = joblib.load(self.model_path)
            if isinstance(artifact, dict) and "vectorizer" in artifact and "clf" in artifact:
                self._vectorizer = artifact["vectorizer"]
                self._clf = artifact["clf"]
            elif hasattr(artifact, "predict_proba"):
                # Plain sklearn Pipeline/estimator: transcript strings go straight in.
                self._clf = artifact
            else:
                raise ValueError(f"unrecognized model artifact shape: {type(artifact)!r}")
        except Exception as exc:  # never let a bad artifact crash the service
            msg = f"[kavach.text_model] STARTUP WARNING: failed to load '{self.model_path}': {exc}"
            warnings.warn(msg)
            logger.warning(msg)
            self._vectorizer = None
            self._clf = None

    @property
    def is_loaded(self) -> bool:
        return self._clf is not None

    def score(self, transcript: str) -> Optional[float]:
        if not self.is_loaded or not transcript or not transcript.strip():
            return None
        try:
            X = self._vectorizer.transform([transcript]) if self._vectorizer is not None else [transcript]
            proba = self._clf.predict_proba(X)[0]
            classes = list(getattr(self._clf, "classes_", [0, 1]))
            idx = classes.index(1) if 1 in classes else (len(proba) - 1)
            return float(proba[idx])
        except Exception as exc:
            logger.warning(f"[kavach.text_model] scoring failed: {exc}")
            return None


class DistilBertScorer(BaseTextScorer):
    """Loads the fine-tuned distilbert-base-uncased classifier from
    models/distilbert/model (training/text/train_transformer.py output).
    Never raises: if torch/transformers aren't installed, or the directory is
    missing/malformed, logs+warns clearly at startup and every .score() call
    simply returns None -- same graceful-degradation contract as
    TfidfLogRegScorer.

    Tokenization/scoring matches the model's training procedure (windowed,
    256-token/stride-128, max_length 512, see train_transformer.py):
      - transcripts whose full token encoding fits within max_length are
        scored in one forward pass (truncation=True, max_length=512) --
        this covers the plain, non-windowed training case exactly.
      - longer transcripts are split into overlapping window_size-token
        windows (stride window_stride) of the un-truncated token sequence,
        each wrapped in [CLS]/[SEP] like at training time, scored
        independently, and the MAX window P(scam) is returned -- a strong
        scam signal anywhere in a long call should not be averaged away by
        calmer surrounding conversation.
    Softmax is applied over the 2 logits; index 1 is P(scam) (label=1=scam
    throughout training/text/*).
    """

    name = "distilbert"

    def __init__(
        self,
        model_dir=None,
        max_length: Optional[int] = None,
        window_size: Optional[int] = None,
        window_stride: Optional[int] = None,
    ):
        self.model_dir = model_dir or config.DISTILBERT_MODEL_DIR
        self.max_length = max_length or config.DISTILBERT_MAX_LENGTH
        self.window_size = window_size or config.DISTILBERT_WINDOW_SIZE
        self.window_stride = window_stride or config.DISTILBERT_WINDOW_STRIDE
        self._tokenizer = None
        self._model = None
        self._load()

    def _load(self) -> None:
        if torch is None or AutoTokenizer is None:
            logger.info(
                "[kavach.text_model] torch/transformers not installed; DistilBERT scoring disabled "
                "(falling back to the TF-IDF baseline if available)."
            )
            return
        if not self.model_dir.exists():
            logger.info(
                f"[kavach.text_model] no DistilBERT model at '{self.model_dir}'; DistilBERT scoring "
                "disabled (falling back to the TF-IDF baseline if available)."
            )
            return
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(str(self.model_dir))
            model = AutoModelForSequenceClassification.from_pretrained(str(self.model_dir))
            model.eval()
            self._model = model
        except Exception as exc:  # never let a bad artifact crash the service
            msg = f"[kavach.text_model] STARTUP WARNING: failed to load DistilBERT from '{self.model_dir}': {exc}"
            warnings.warn(msg)
            logger.warning(msg)
            self._tokenizer = None
            self._model = None

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def score(self, transcript: str) -> Optional[float]:
        if not self.is_loaded or not transcript or not transcript.strip():
            return None
        try:
            with torch.no_grad():
                full_ids = self._tokenizer(transcript, truncation=False)["input_ids"]
                if len(full_ids) <= self.max_length:
                    return self._score_encoding(
                        self._tokenizer(
                            transcript, truncation=True, max_length=self.max_length, return_tensors="pt",
                        )
                    )
                return self._score_windows(
                    self._tokenizer(transcript, add_special_tokens=False, truncation=False)["input_ids"]
                )
        except Exception as exc:
            logger.warning(f"[kavach.text_model] scoring failed: {exc}")
            return None

    def _score_encoding(self, encoding) -> float:
        encoding.pop("token_type_ids", None)
        logits = self._model(**encoding).logits
        probs = torch.softmax(logits, dim=-1)[0]
        return float(probs[1].item())

    def _score_windows(self, body_ids: List[int]) -> Optional[float]:
        """Score overlapping window_size-token windows (stride window_stride)
        of the un-truncated token id sequence and return the MAX P(scam)
        across windows -- matches the sliding-window training procedure and
        means a scam signal anywhere in a long call drives the score."""
        cls_id, sep_id = self._tokenizer.cls_token_id, self._tokenizer.sep_token_id
        window_probs = []
        n = len(body_ids)
        start = 0
        while start < n:
            chunk = body_ids[start:start + self.window_size]
            if not chunk:
                break
            input_ids = [cls_id] + chunk + [sep_id]
            encoding = {
                "input_ids": torch.tensor([input_ids]),
                "attention_mask": torch.tensor([[1] * len(input_ids)]),
            }
            window_probs.append(self._score_encoding(encoding))
            if start + self.window_size >= n:
                break
            start += self.window_stride
        return max(window_probs) if window_probs else None


_default_scorer: Optional[BaseTextScorer] = None


def get_text_scorer() -> BaseTextScorer:
    """Process-wide singleton, lazily constructed (so import time stays cheap
    and tests can monkeypatch config.TEXT_MODEL_PATH/DISTILBERT_MODEL_DIR
    before first use).

    Selection order: prefer the fine-tuned DistilBERT scorer if
    models/distilbert/model exists (and torch/transformers are installed);
    else fall back to the TF-IDF+LogReg baseline; if THAT is also missing,
    the baseline instance itself degrades gracefully (is_loaded=False,
    score() -> None) so callers never need a third branch."""
    global _default_scorer
    if _default_scorer is None:
        distilbert_scorer = DistilBertScorer()
        _default_scorer = distilbert_scorer if distilbert_scorer.is_loaded else TfidfLogRegScorer()
    return _default_scorer


def reset_text_scorer() -> None:
    """Test helper: drop the singleton so the next get_text_scorer() reloads."""
    global _default_scorer
    _default_scorer = None
