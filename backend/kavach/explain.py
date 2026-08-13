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
}

# Thresholds for when a signal is strong enough to name in the explanation
# (independent of the fusion weights in config.py -- these just gate whether
# a signal is worth a plain-language sentence, not how much it contributes to
# risk_score).
TEXT_SUSPICIOUS_THRESHOLD = 0.5
AUDIO_SYNTHETIC_THRESHOLD = 0.5

# See config.FUSION_WEIGHTS["audio"] docstring: a synthetic-sounding voice is
# corroborating context, not proof of a scam by itself -- plenty of
# legitimate calls (bank IVR, clinic/delivery reminders, OTP robocalls) are
# synthetic speech too. The explanation must say so every time it mentions
# the voice, so it never reads as an accusation on its own.
_AUDIO_CAVEAT = (
    "The voice on this call sounds artificially generated (AI-cloned or synthetic). "
    "Note: some genuine automated calls (bank, clinic, or delivery reminders) also use "
    "synthetic voices, so this on its own is not proof of a scam."
)


def _level_phrase(risk_level: str) -> str:
    return _LEVEL_PHRASES.get(risk_level, "This call has been analyzed.")


def compose_rule_based(
    risk_level: str,
    signature_hits: List[dict],
    text_score: Optional[float],
    audio_score: Optional[float] = None,
) -> str:
    """Plain-English explanation built purely from signature hits + scores.

    Two invariants, both regression-tested in tests/test_explain.py:
      1. The headline only ever claims "scam signs" when signature_hits is
         non-empty -- it must never assert strong scam signs and then list
         zero of them (the bug this fixes: an audio-only "high" verdict used
         to print exactly that).
      2. Every "suspicious"/"high" verdict enumerates at least one concrete,
         human-readable reason, whether that reason is a signature hit,
         scam-like phrasing, or an artificial-sounding voice (with the
         caveat above) -- never a bare, unexplained risk level.
    """
    voice_flag = audio_score is not None and audio_score >= AUDIO_SYNTHETIC_THRESHOLD
    content_flag = text_score is not None and text_score >= TEXT_SUSPICIOUS_THRESHOLD

    if risk_level == "low":
        return _level_phrase("low") + " Stay alert if the caller later asks for your OTP/PIN, remote access, or a money transfer."

    severity_word = "strong scam signs" if risk_level == "high" else "some suspicious signs"

    if signature_hits:
        ordered = sorted(signature_hits, key=lambda h: h["severity"], reverse=True)
        n = len(ordered)
        count_phrase = "1 scam sign" if n == 1 else f"{n} scam signs"
        lines = [f"This call shows {severity_word}. It shows {count_phrase} in what was said:"]
        for hit in ordered[:5]:
            lines.append(f"- {hit['explanation']}")
        if n > 5:
            lines.append(f"...and {n - 5} more.")
        if voice_flag:
            lines.append(f"- {_AUDIO_CAVEAT}")
        lines.append("Do not share your OTP/PIN, do not install any remote-access app, and do not transfer money on this call.")
        return "\n".join(lines)

    # No signature hits matched -- never say "scam signs" here since there
    # are none to list. Build the headline from whichever of {content voice}
    # actually drove the score, and always leave at least one concrete
    # reason line.
    label = "high risk" if risk_level == "high" else "worth caution"
    reasons: List[str] = []
    if content_flag:
        reasons.append(
            "- No specific scam phrase was matched, but the way this call is phrased "
            "is similar to known scam calls."
        )
    if voice_flag:
        reasons.append(f"- {_AUDIO_CAVEAT}")
    if not reasons:
        # Neither signal individually cleared its own bar, but the fused
        # score still crossed the suspicious/high threshold from a
        # combination of weaker signals.
        reasons.append(
            "- No single strong signal was found, but a combination of weaker signals "
            "-- the phrasing of the call and characteristics of the caller's voice -- "
            f"add up enough to make this call {label}."
        )

    if content_flag and voice_flag:
        headline = f"This call is {label}: both how it is phrased and the caller's voice are cause for caution."
    elif voice_flag:
        headline = (
            f"This call is {label} mainly because of the caller's voice, not the words used -- "
            "no specific scam phrase or signature was matched in the transcript."
        )
    elif content_flag:
        headline = (
            f"This call is {label}: how it is phrased closely matches known scam calls, "
            "even though no exact scam phrase was matched."
        )
    else:
        headline = f"This call is {label} based on a combination of weaker signals."

    lines = [headline] + reasons
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
    audio_score: Optional[float] = None,
) -> str:
    rule_based = compose_rule_based(risk_level, signature_hits, text_score, audio_score)
    if config.GEMINI_API_KEY:
        return _try_llm_polish(rule_based)
    return rule_based
