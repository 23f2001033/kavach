"""Builds the user-facing explanation.

The rule-based composer below is the always-works path and is what every
response is built from. An OPTIONAL LLM polish pass can rephrase it more
naturally when GEMINI_API_KEY is set — it only rewords the already-computed,
already-correct rule-based text (it is never allowed to introduce facts, and
the prompt says so); ANY failure (import error, no network, timeout, quota,
bad response) falls back silently to the rule-based text. Detection and
explanation never depend on an external API — see README's design principle.
"""
import logging
from typing import List, Optional

from . import config

logger = logging.getLogger("kavach.explain")

_LEVEL_PHRASES = {
    "low": "This call does not show clear scam signs so far.",
    "suspicious": "This call shows some suspicious signs.",
    "high": "This call shows strong scam signs.",
}


def _level_phrase(risk_level: str) -> str:
    return _LEVEL_PHRASES.get(risk_level, "This call has been analyzed.")


def compose_rule_based(risk_level: str, signature_hits: List[dict], text_score: Optional[float]) -> str:
    """Plain-English explanation built purely from signature hits + scores."""
    if not signature_hits:
        base = _level_phrase(risk_level)
        if risk_level == "low":
            return base + " Stay alert if the caller later asks for your OTP/PIN, remote access, or a money transfer."
        if text_score is not None and text_score >= 0.5:
            return (
                base + " No specific scam phrase was matched yet, but the way this call is phrased "
                "is similar to known scam calls. Be cautious."
            )
        return base

    ordered = sorted(signature_hits, key=lambda h: h["severity"], reverse=True)
    n = len(ordered)
    count_phrase = "1 scam sign" if n == 1 else f"{n} scam signs"
    lines = [f"{_level_phrase(risk_level)} It shows {count_phrase}:"]
    for hit in ordered[:5]:
        lines.append(f"- {hit['explanation']}")
    if n > 5:
        lines.append(f"...and {n - 5} more.")
    lines.append("Do not share your OTP/PIN, do not install any remote-access app, and do not transfer money on this call.")
    return "\n".join(lines)


def _try_llm_polish(rule_based_text: str) -> str:
    """Best-effort LLM rewrite of the rule-based text. Returns rule_based_text
    unchanged on ANY failure — this must never be the thing that breaks a
    response."""
    try:
        import google.generativeai as genai  # guarded, optional dependency

        genai.configure(api_key=config.GEMINI_API_KEY)
        model = genai.GenerativeModel(config.GEMINI_MODEL_NAME)
        prompt = (
            "Rewrite the following scam-call warning in simple, plain English for an "
            "elderly, non-technical reader. Keep every factual claim EXACTLY as given, "
            "do not invent or add new facts, keep it short (at most 5 short lines).\n\n"
            f"Warning:\n{rule_based_text}"
        )
        response = model.generate_content(
            prompt,
            request_options={"timeout": config.GEMINI_TIMEOUT_SECONDS},
        )
        polished = (getattr(response, "text", "") or "").strip()
        return polished if polished else rule_based_text
    except Exception as exc:
        logger.info(f"[kavach.explain] LLM polish skipped ({exc}); using rule-based explanation.")
        return rule_based_text


def build_explanation(
    risk_level: str,
    signature_hits: List[dict],
    text_score: Optional[float],
    transcript: str = "",
) -> str:
    rule_based = compose_rule_based(risk_level, signature_hits, text_score)
    if config.GEMINI_API_KEY:
        return _try_llm_polish(rule_based)
    return rule_based
