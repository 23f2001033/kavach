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
    [0, 1] plus a one-shot risk_level.

    Degrades gracefully: any signal that is None (model not loaded, no audio
    chunk yet, ...) is simply dropped and the remaining weights renormalized,
    so the service never crashes or silently zeroes out risk just because one
    modality is unavailable. The signature sub-score is always available
    (0.0 if there are no hits) so there is always at least one active signal.
    """
    signature_hits = signature_hits or []
    weights = weights or config.FUSION_WEIGHTS
    sig_score = signature_subscore(signature_hits)

    components = {"signature": sig_score}
    active_weights = {"signature": weights["signature"]}
    if text_score is not None:
        components["text"] = max(0.0, min(1.0, text_score))
        active_weights["text"] = weights["text"]
    if audio_score is not None:
        components["audio"] = max(0.0, min(1.0, audio_score))
        active_weights["audio"] = weights["audio"]

    total_weight = sum(active_weights.values())
    if total_weight <= 0:
        risk_score = sig_score
    else:
        risk_score = sum(components[k] * active_weights[k] for k in active_weights) / total_weight
    risk_score = max(0.0, min(1.0, risk_score))

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
