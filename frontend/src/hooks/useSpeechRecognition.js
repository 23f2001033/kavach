import { useCallback, useEffect, useRef, useState } from 'react';

function getSpeechRecognitionCtor() {
  if (typeof window === 'undefined') return null;
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

export const SPEECH_RECOGNITION_SUPPORTED = getSpeechRecognitionCtor() !== null;

/**
 * Wraps the browser Web Speech API (continuous + interim results) for the
 * Live Guard mode. Exposes the full rolling transcript plus the current
 * (not-yet-final) interim text, and calls `onFinalChunk(text)` every time a
 * new final segment lands so the caller can push it to /analyze/window.
 *
 * Chrome/Edge only (no Firefox/Safari support as of this writing) -- callers
 * should check SPEECH_RECOGNITION_SUPPORTED and offer a fallback.
 */
export function useSpeechRecognition({ lang = 'en-IN', onFinalChunk } = {}) {
  const [listening, setListening] = useState(false);
  const [finalTranscript, setFinalTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [error, setError] = useState(null);

  const recognitionRef = useRef(null);
  const shouldRunRef = useRef(false); // true while the user wants it running
  const onFinalChunkRef = useRef(onFinalChunk);
  onFinalChunkRef.current = onFinalChunk;

  const buildRecognition = useCallback(() => {
    const Ctor = getSpeechRecognitionCtor();
    if (!Ctor) return null;
    const recognition = new Ctor();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = lang;

    recognition.onresult = (event) => {
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const text = result[0].transcript;
        if (result.isFinal) {
          setFinalTranscript((prev) => (prev ? `${prev} ${text}`.trim() : text.trim()));
          onFinalChunkRef.current?.(text.trim());
        } else {
          interim += text;
        }
      }
      setInterimTranscript(interim);
    };

    recognition.onerror = (event) => {
      setError(event.error || 'unknown-error');
      // 'no-speech' fires often during natural pauses; not fatal, keep running.
      if (event.error === 'not-allowed' || event.error === 'audio-capture' || event.error === 'service-not-allowed') {
        shouldRunRef.current = false;
        setListening(false);
      }
    };

    recognition.onend = () => {
      // Chrome ends the recognizer after periods of silence even in
      // continuous mode; auto-restart if the user hasn't asked to stop.
      if (shouldRunRef.current) {
        try {
          recognition.start();
        } catch {
          // ignore rapid-restart races
        }
      } else {
        setListening(false);
      }
    };

    return recognition;
  }, [lang]);

  const start = useCallback(() => {
    if (!SPEECH_RECOGNITION_SUPPORTED) return;
    setError(null);
    setFinalTranscript('');
    setInterimTranscript('');
    shouldRunRef.current = true;
    const recognition = buildRecognition();
    recognitionRef.current = recognition;
    if (!recognition) return;
    try {
      recognition.start();
      setListening(true);
    } catch (err) {
      setError(err?.message || 'failed-to-start');
    }
  }, [buildRecognition]);

  const stop = useCallback(() => {
    shouldRunRef.current = false;
    recognitionRef.current?.stop();
    setListening(false);
  }, []);

  useEffect(() => {
    // Stop cleanly on unmount (e.g. navigating away from Live Guard).
    return () => {
      shouldRunRef.current = false;
      recognitionRef.current?.stop();
    };
  }, []);

  return {
    supported: SPEECH_RECOGNITION_SUPPORTED,
    listening,
    finalTranscript,
    interimTranscript,
    error,
    start,
    stop,
  };
}
