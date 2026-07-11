import { useState } from 'react';
import { analyzeRecording, ApiError } from '../api.js';
import ResultPanel from './ResultPanel.jsx';
import './RecordingMode.css';

const ACCEPTED_EXTENSIONS = '.wav,.mp3,.m4a,.ogg,.webm';

export default function RecordingMode({ elderlyMode }) {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleFileChange = (e) => {
    setFile(e.target.files?.[0] ?? null);
    setResult(null);
    setError(null);
  };

  const handleAnalyze = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const data = await analyzeRecording(file);
      setResult(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Analysis failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="recording-mode">
      {!elderlyMode && (
        <p className="recording-mode__hint">
          Upload a recorded call (wav, mp3, m4a, ogg, or webm). It's transcribed locally with
          Whisper speech-to-text, then analyzed the same way as a pasted transcript.
        </p>
      )}
      <input
        type="file"
        accept={`${ACCEPTED_EXTENSIONS},audio/*`}
        className="recording-mode__file-input"
        onChange={handleFileChange}
      />
      <button
        type="button"
        className="recording-mode__analyze-btn"
        onClick={handleAnalyze}
        disabled={loading || !file}
      >
        {loading ? 'Transcribing... first run downloads the speech model' : 'Analyze recording'}
      </button>
      {error && <p className="recording-mode__error">{error}</p>}
      {result && (
        <div className="recording-mode__transcript">
          <h3 className="recording-mode__transcript-heading">Transcript</h3>
          <p className="recording-mode__transcript-text">{result.transcript}</p>
          <p className="recording-mode__voice-clone">
            {result.audio_score != null
              ? `Voice-clone analysis: ${Math.round(result.audio_score * 100)}% suspicion`
              : 'Voice-clone model: not yet loaded'}
          </p>
        </div>
      )}
      <ResultPanel result={result} elderlyMode={elderlyMode} />
    </div>
  );
}
