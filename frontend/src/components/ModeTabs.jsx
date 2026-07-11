import './ModeTabs.css';

export default function ModeTabs({ mode, onChange }) {
  return (
    <div className="mode-tabs" role="tablist" aria-label="Analysis mode">
      <button
        type="button"
        role="tab"
        aria-selected={mode === 'live'}
        className={`mode-tabs__tab ${mode === 'live' ? 'is-active' : ''}`}
        onClick={() => onChange('live')}
      >
        Live Guard
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={mode === 'transcript'}
        className={`mode-tabs__tab ${mode === 'transcript' ? 'is-active' : ''}`}
        onClick={() => onChange('transcript')}
      >
        Transcript mode
      </button>
      <button
        type="button"
        role="tab"
        aria-selected={mode === 'recording'}
        className={`mode-tabs__tab ${mode === 'recording' ? 'is-active' : ''}`}
        onClick={() => onChange('recording')}
      >
        Upload Recording
      </button>
    </div>
  );
}
