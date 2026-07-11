import './AlertBanner.css';

export default function AlertBanner({ visible }) {
  if (!visible) return null;
  return (
    <div className="alert-banner" role="alert">
      <span className="alert-banner__icon" aria-hidden="true">
        ⚠
      </span>
      This call shows strong signs of a SCAM
    </div>
  );
}
