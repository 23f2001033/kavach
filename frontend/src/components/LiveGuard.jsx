import { useCallback, useEffect, useRef, useState } from 'react';
import { useSpeechRecognition } from '../hooks/useSpeechRecognition.js';
import { useVoiceAlert } from '../hooks/useVoiceAlert.js';
import { analyzeWindow, ApiError } from '../api.js';
import { newSessionId } from '../utils/sessionId.js';
import ResultPanel from './ResultPanel.jsx';
import './LiveGuard.css';

const LANGUAGES = [
  { code: 'en-IN', label: 'English (India)' },
  { code: 'hi-IN', label: 'Hindi' },
  { code: 'en-US', label: 'English (US)' },
];

const INTERIM_FLUSH_MS = 2500;

export default function LiveGuard({ elderlyMode }) {
  const [lang, setLang] = useState('en-IN');
  const [result, setResult] = useState(null);
  const [analyzeError, setAnalyzeError] = useState(null);
  const sessionIdRef = useRef(newSessionId());
  const lastSentInterimRef = useRef('');

  const sendChunk = useCallback((text) => {
    if (!text || !text.trim()) return;
    analyzeWindow(text.trim(), sessionIdRef.current)
      .then((data) => {
        setResult(data);
        setAnalyzeError(null);
      })
      .catch((err) => {
        setAnalyzeError(err instanceof ApiError ? err.message : 'Analysis failed.');
      });
  }, []);

  const handleFinalChunk = useCallback(
    (text) => {
      lastSentInterimRef.current = '';
      sendChunk(text);
    },
    [sendChunk],
  );

  const { supported, listening, finalTranscript, interimTranscript, error, start, stop } =
    useSpeechRecognition({ lang, onFinalChunk: handleFinalChunk });

  // Every ~2.5s, if there's interim (not-yet-final) text we haven't sent yet,
  // flush the new portion so the risk meter doesn't wait on a final result.
  useEffect(() => {
    if (!listening) return;
    const id = setInterval(() => {
      const current = interimTranscript;
      const already = lastSentInterimRef.current;
      if (!current || current === already) return;
      const delta = current.startsWith(already) ? current.slice(already.length) : current;
      lastSentInterimRef.current = current;
      sendChunk(delta);
    }, INTERIM_FLUSH_MS);
    return () => clearInterval(id);
  }, [listening, interimTranscript, sendChunk]);

  useVoiceAlert(result?.risk_level, true);

  const handleStart = () => {
    sessionIdRef.current = newSessionId();
    lastSentInterimRef.current = '';
    setResult(null);
    setAnalyzeError(null);
    start();
  };

  if (!supported) {
    return (
      <div className="live-guard live-guard--unsupported">
        <p className="live-guard__unsupported-notice">
          Your browser doesn&apos;t support live speech recognition. Please use{' '}
          <strong>Google Chrome</strong> or <strong>Microsoft Edge</strong> for Live Guard mode, or
          switch to <strong>Transcript mode</strong> to paste a call transcript instead.
        </p>
      </div>
    );
  }

  return (
    <div className="live-guard">
      <div className="live-guard__controls">
        <label className="live-guard__lang-label">
          Language
          <select value={lang} onChange={(e) => setLang(e.target.value)} disabled={listening}>
            {LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
        </label>
        {!listening ? (
          <button type="button" className="live-guard__btn live-guard__btn--start" onClick={handleStart}>
            Start listening
          </button>
        ) : (
          <button type="button" className="live-guard__btn live-guard__btn--stop" onClick={stop}>
            Stop
          </button>
        )}
        {listening && (
          <span className="live-guard__rec-dot" aria-label="Listening">
            <span className="live-guard__rec-pulse" /> Listening...
          </span>
        )}
      </div>

      {error && error !== 'no-speech' && (
        <p className="live-guard__error">Speech recognition issue: {error}</p>
      )}
      {analyzeError && <p className="live-guard__error">{analyzeError}</p>}

      {!elderlyMode && (
        <div className="live-guard__transcript" aria-live="polite">
          <h3 className="live-guard__transcript-heading">Live transcript</h3>
          <p className="live-guard__transcript-text">
            {finalTranscript || <span className="live-guard__placeholder">Say something, or the call audio will appear here...</span>}{' '}
            <span className="live-guard__interim">{interimTranscript}</span>
          </p>
        </div>
      )}

      <ResultPanel result={result} elderlyMode={elderlyMode} />
    </div>
  );
}
