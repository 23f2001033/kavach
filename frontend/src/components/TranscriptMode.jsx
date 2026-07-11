import { useState } from 'react';
import { analyzeText, ApiError } from '../api.js';
import { EXAMPLE_LEGIT_TRANSCRIPT, EXAMPLE_SCAM_TRANSCRIPT } from '../data/exampleTranscripts.js';
import ResultPanel from './ResultPanel.jsx';
import './TranscriptMode.css';

export default function TranscriptMode({ elderlyMode }) {
  const [transcript, setTranscript] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAnalyze = async () => {
    if (!transcript.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeText(transcript.trim());
      setResult(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Analysis failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="transcript-mode">
      {!elderlyMode && (
        <div className="transcript-mode__examples">
          <button type="button" onClick={() => setTranscript(EXAMPLE_SCAM_TRANSCRIPT)}>
            Load example scam
          </button>
          <button type="button" onClick={() => setTranscript(EXAMPLE_LEGIT_TRANSCRIPT)}>
            Load example legit
          </button>
        </div>
      )}
      <textarea
        className="transcript-mode__textarea"
        placeholder='Paste a call transcript, e.g. "Caller: ... Receiver: ..."'
        value={transcript}
        onChange={(e) => setTranscript(e.target.value)}
        rows={elderlyMode ? 6 : 10}
      />
      <button
        type="button"
        className="transcript-mode__analyze-btn"
        onClick={handleAnalyze}
        disabled={loading || !transcript.trim()}
      >
        {loading ? 'Analyzing...' : 'Analyze transcript'}
      </button>
      {error && <p className="transcript-mode__error">{error}</p>}
      <ResultPanel result={result} elderlyMode={elderlyMode} />
    </div>
  );
}
