import './StatusChip.css';

export default function StatusChip({ health, reachable }) {
  if (reachable === null) {
    return (
      <span className="status-chip status-chip--pending">
        <span className="status-chip__dot" /> Checking backend...
      </span>
    );
  }

  if (reachable === false) {
    return (
      <span className="status-chip status-chip--down" title="Start the backend with: uvicorn main:app --reload --port 8000 (from backend/)">
        <span className="status-chip__dot" /> Backend unreachable
      </span>
    );
  }

  const textLoaded = !!health?.models?.text;
  const audioLoaded = !!health?.models?.audio;

  return (
    <span
      className={`status-chip ${textLoaded ? 'status-chip--ok' : 'status-chip--partial'}`}
      title={
        textLoaded
          ? 'Text scam-detection model is loaded.'
          : 'Text model not loaded - falling back to signature-only detection. Run training/text/train_baseline.py.'
      }
    >
      <span className="status-chip__dot" />
      Backend online - text {textLoaded ? 'ready' : 'unavailable'}, audio {audioLoaded ? 'ready' : 'unavailable'}
    </span>
  );
}
