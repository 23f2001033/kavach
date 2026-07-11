"""Combine text_score, signature hits, and (optional) audio_score into one
risk_score in [0, 1] plus a discrete risk_level, and a stateful hysteresis
helper for streaming/window use so the on-screen risk meter doesn't flicker.
"""
from typing import Dict, List, Optional

from . import config


def signature_subscore(signature_hits: List[dict]) -> float:
    """Severity-weighted, saturating sum of signature hits -> a sub-score in
    [0, 1]. Saturating means piling up many low-severity hits can't run away
    to an arbitrarily large number; it caps at config.SIGNATURE_SATURATION."""
    if not signature_hits:
        return 0.0
    total = sum(config.SEVERITY_WEIGHTS.get(h["severity"], 0.15) for h in signature_hits)
    return min(total, config.SIGNATURE_SATURATION)


def classify(risk_score: float, thresholds: Optional[dict] = None) -> str:
    """One-shot (non-hysteresis) risk level from a raw score."""
    thresholds = thresholds or config.RISK_THRESHOLDS
    if risk_score >= thresholds["high"]:
        return "high"
    if risk_score >= thresholds["suspicious"]:
        return "suspicious"
    return "low"


def combine(
    text_score: Optional[float] = None,
    signature_hits: Optional[List[dict]] = None,
    audio_score: Optional[float] = None,
    weights: Optional[dict] = None,
) -> Dict:
    """Fuse text / signature / audio signals into a single risk_score in
    [0, 1] plus a one-shot risk_level, via noisy-OR evidence combination:

        risk_score = 1 - PRODUCT_i (1 - s_i * w_i)

    over whichever signals i are actually AVAILABLE this request (a None
    signal is simply excluded from the product -- there is no
    renormalization over the rest). Each s_i is first mapped into [0, 1]
    (text_score used as-is; signature evidence via the severity-weighted
    saturating signature_subscore(); audio used as-is), and w_i is a
    per-signal weight/cap from config.FUSION_WEIGHTS.

    This replaces an earlier weighted-average combiner that renormalized
    over active weights. That structurally diluted the text signal: because
    the signature sub-score was always "active" (0.0 when there were no
    hits) and no audio model is shipped yet, every real request renormalized
    over just {text, signature}, capping risk_score at ~0.588 * text_score
    regardless of how confident the text model was -- below the 'high'
    threshold no matter what. Noisy-OR fixes this structurally:
      - with only text available, risk_score == text_score exactly (weights
        ['text'] defaults to 1.0 -- see test_combine_text_only_equals_text_score).
      - every additional nonzero signal can only raise risk_score (each
        product factor is <= 1), never lower it or dilute what's there.
      - risk_score is monotonic non-decreasing in each individual input.
      - if no signal is available at all, the product is empty (== 1) so
        risk_score == 0.0; `components` is also empty, which callers can use
        as the "no signals seen yet" flag.
    """
    signature_hits = signature_hits or []
    weights = weights or config.FUSION_WEIGHTS
    sig_score = signature_subscore(signature_hits)

    components: Dict[str, float] = {}
    survival = 1.0  # running PRODUCT_i (1 - s_i * w_i)

    if text_score is not None:
        t = max(0.0, min(1.0, text_score))
        components["text"] = t
        survival *= 1.0 - max(0.0, min(1.0, t * weights["text"]))
    if signature_hits:
        components["signature"] = sig_score
        survival *= 1.0 - max(0.0, min(1.0, sig_score * weights["signature"]))
    if audio_score is not None:
        a = max(0.0, min(1.0, audio_score))
        components["audio"] = a
        survival *= 1.0 - max(0.0, min(1.0, a * weights["audio"]))

    risk_score = max(0.0, min(1.0, 1.0 - survival))

    return {
        "risk_score": risk_score,
        "risk_level": classify(risk_score),
        "signature_score": sig_score,
        "components": components,
    }


class HysteresisMeter:
    """Stateful risk-level smoother for streaming/window use.

    A level change is only accepted once the score crosses the relevant
    threshold *plus* a margin, in the direction of travel. E.g. with
    suspicious=0.35, high=0.65, margin=0.05: to go low->suspicious the score
    must reach >=0.40; to fall back suspicious->low it must drop to <=0.30.
    That dead zone stops the meter flickering when the score hovers right at
    a boundary. Call update() once per new score, in temporal order.
    """

    def __init__(self, thresholds: Optional[dict] = None, margin: Optional[float] = None):
        self.thresholds = thresholds or config.RISK_THRESHOLDS
        self.margin = margin if margin is not None else config.HYSTERESIS_MARGIN
        self.level = "low"
        self.last_score = 0.0

    def update(self, risk_score: float) -> str:
        self.last_score = risk_score
        t_susp, t_high, m = self.thresholds["suspicious"], self.thresholds["high"], self.margin

        if self.level == "low":
            if risk_score >= t_high + m:
                self.level = "high"
            elif risk_score >= t_susp + m:
                self.level = "suspicious"
        elif self.level == "suspicious":
            if risk_score >= t_high + m:
                self.level = "high"
            elif risk_score <= t_susp - m:
                self.level = "low"
        elif self.level == "high":
            if risk_score <= t_susp - m:
                self.level = "low"
            elif risk_score <= t_high - m:
                self.level = "suspicious"
        return self.level

    def reset(self) -> None:
        self.level = "low"
        self.last_score = 0.0
