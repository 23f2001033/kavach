import './RiskGauge.css';

const LEVEL_COLORS = {
  low: '#22c55e',
  suspicious: '#f59e0b',
  high: '#ef4444',
};

const LEVEL_LABELS = {
  low: 'Low risk',
  suspicious: 'Suspicious',
  high: 'High risk - likely scam',
};

const CX = 100;
const CY = 104;
const R = 80;
const ARC_LENGTH = Math.PI * R; // half-circle circumference

/**
 * Animated SVG arc gauge, 0-100, coloured by risk level. A semi-circle track
 * plus a progress arc (stroke-dasharray trick) and a rotating needle, both
 * CSS-transitioned so score changes sweep smoothly instead of jumping.
 */
export default function RiskGauge({ score = 0, level = 'low', size = 'normal' }) {
  const clamped = Math.max(0, Math.min(100, score));
  const fraction = clamped / 100;
  const color = LEVEL_COLORS[level] || LEVEL_COLORS.low;
  const label = LEVEL_LABELS[level] || LEVEL_LABELS.low;

  const dashOffset = ARC_LENGTH * (1 - fraction);
  const needleAngle = (fraction - 0.5) * 180; // -90deg .. +90deg

  return (
    <div className={`risk-gauge risk-gauge--${size}`} role="img" aria-label={`Risk score ${Math.round(clamped)} of 100, ${label}`}>
      <svg viewBox="0 0 200 130" className="risk-gauge__svg">
        <path
          d={`M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${CX + R} ${CY}`}
          className="risk-gauge__track"
        />
        <path
          d={`M ${CX - R} ${CY} A ${R} ${R} 0 0 1 ${CX + R} ${CY}`}
          className="risk-gauge__progress"
          style={{
            stroke: color,
            strokeDasharray: ARC_LENGTH,
            strokeDashoffset: dashOffset,
          }}
        />
        <g className="risk-gauge__needle" style={{ transform: `rotate(${needleAngle}deg)`, transformOrigin: `${CX}px ${CY}px` }}>
          <line x1={CX} y1={CY} x2={CX} y2={CY - R + 14} />
          <circle cx={CX} cy={CY} r="7" />
        </g>
      </svg>
      <div className="risk-gauge__readout">
        <span className="risk-gauge__score" style={{ color }}>
          {Math.round(clamped)}
        </span>
        <span className="risk-gauge__label" style={{ color }}>
          {label}
        </span>
      </div>
    </div>
  );
}
