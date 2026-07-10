"""Text scam-likelihood scorer.

v1 implementation loads the TF-IDF(word 1-2gram + char 3-5gram) + Logistic
Regression baseline produced by training/text/train_baseline.py. That script
saves a dict ``{"vectorizer": FeatureUnion, "clf": LogisticRegression,
"best_C": float}`` to models/text_baseline.joblib — NOT a single sklearn
Pipeline — so the loader below handles that shape directly, while still
accepting a plain estimator/Pipeline with .predict_proba([str, ...]) if a
future export changes shape.

A small ABC (`BaseTextScorer`) is the seam a future ONNX DistilBERT model
drops into: implement `.score(transcript) -> Optional[float]` and
`.is_loaded`, then swap what `get_text_scorer()` constructs (e.g. behind a
config flag) — nothing else in the backend needs to change.
"""
import logging
import warnings
from abc import ABC, abstractmethod
from typing import Optional

import joblib

from . import config

logger = logging.getLogger("kavach.text_model")


class BaseTextScorer(ABC):
    """Interface every text scam-scorer must implement."""

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


_default_scorer: Optional[BaseTextScorer] = None


def get_text_scorer() -> BaseTextScorer:
    """Process-wide singleton, lazily constructed (so import time stays cheap
    and tests can monkeypatch config.TEXT_MODEL_PATH before first use)."""
    global _default_scorer
    if _default_scorer is None:
        _default_scorer = TfidfLogRegScorer()
    return _default_scorer


def reset_text_scorer() -> None:
    """Test helper: drop the singleton so the next get_text_scorer() reloads."""
    global _default_scorer
    _default_scorer = None
