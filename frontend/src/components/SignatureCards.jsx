import './SignatureCards.css';

const SEVERITY_LABELS = { 1: 'Low', 2: 'Medium', 3: 'High' };

export default function SignatureCards({ hits }) {
  if (!hits || hits.length === 0) return null;

  return (
    <div className="signature-cards">
      <h3 className="signature-cards__heading">Detected scam signs ({hits.length})</h3>
      <div className="signature-cards__grid">
        {hits.map((hit) => (
          <article key={hit.id} className={`signature-card signature-card--sev${hit.severity}`}>
            <header className="signature-card__header">
              <span className="signature-card__name">{hit.name}</span>
              <span className="signature-card__severity">{SEVERITY_LABELS[hit.severity] || 'Note'}</span>
            </header>
            <p className="signature-card__explanation">{hit.explanation}</p>
            {hit.matches?.[0] && <p className="signature-card__snippet">&ldquo;{hit.matches[0]}&rdquo;</p>}
          </article>
        ))}
      </div>
    </div>
  );
}
