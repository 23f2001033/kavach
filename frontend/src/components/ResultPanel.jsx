import RiskGauge from './RiskGauge.jsx';
import AlertBanner from './AlertBanner.jsx';
import SignatureCards from './SignatureCards.jsx';
import { oneLineAdvice } from '../utils/advice.js';
import './ResultPanel.css';

/** Renders one AnalyzeResponse: gauge + (optional) alert banner + explanation
 * + signature cards. In elderly mode it collapses to gauge + verdict + a
 * single plain-language advice line, in very large high-contrast text. */
export default function ResultPanel({ result, elderlyMode }) {
  if (!result) return null;
  const { risk_score: riskScore, risk_level: riskLevel, signature_hits: hits, explanation } = result;
  const score100 = Math.round((riskScore ?? 0) * 100);

  if (elderlyMode) {
    return (
      <div className="result-panel result-panel--elderly">
        <RiskGauge score={score100} level={riskLevel} size="large" />
        <p className={`result-panel__verdict result-panel__verdict--${riskLevel}`}>
          {riskLevel === 'high' ? 'SCAM WARNING' : riskLevel === 'suspicious' ? 'BE CAREFUL' : 'LOOKS SAFE'}
        </p>
        <p className="result-panel__advice">{oneLineAdvice(riskLevel)}</p>
      </div>
    );
  }

  return (
    <div className="result-panel">
      <AlertBanner visible={riskLevel === 'high'} />
      <div className="result-panel__body">
        <RiskGauge score={score100} level={riskLevel} />
        <div className="result-panel__details">
          <p className="result-panel__explanation">{explanation}</p>
          <SignatureCards hits={hits} />
        </div>
      </div>
    </div>
  );
}
