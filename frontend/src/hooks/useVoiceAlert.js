import { useEffect, useRef } from 'react';

const WARNING_TEXT = 'Warning. This call shows strong signs of a scam. Do not share your OTP or make any payment.';

/** Speaks a short warning once each time riskLevel *becomes* "high" (edge
 * triggered, not on every render/poll) via window.speechSynthesis. */
export function useVoiceAlert(riskLevel, enabled = true) {
  const previousLevel = useRef(riskLevel);

  useEffect(() => {
    const escalatedToHigh = riskLevel === 'high' && previousLevel.current !== 'high';
    previousLevel.current = riskLevel;

    if (!enabled || !escalatedToHigh) return;
    if (typeof window === 'undefined' || !window.speechSynthesis) return;

    const utterance = new SpeechSynthesisUtterance(WARNING_TEXT);
    utterance.rate = 0.95;
    window.speechSynthesis.cancel(); // don't stack multiple warnings
    window.speechSynthesis.speak(utterance);
  }, [riskLevel, enabled]);
}
