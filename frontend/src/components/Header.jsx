import StatusChip from './StatusChip.jsx';
import './Header.css';

const ShieldIcon = () => (
  <svg viewBox="0 0 64 64" className="header__shield" aria-hidden="true">
    <path fill="currentColor" d="M32 3 8 12v18c0 16 10.5 27.5 24 31 13.5-3.5 24-15 24-31V12L32 3z" opacity="0.18" />
    <path fill="currentColor" d="M32 10 15 16.5v13.2c0 12.9 8.4 22.2 17 25.2 8.6-3 17-12.3 17-25.2V16.5L32 10z" opacity="0.35" />
    <path fill="currentColor" d="m28 33.5-5.5-5.5-3.5 3.5L28 40.5l17-17-3.5-3.5z" />
  </svg>
);

export default function Header({ health, reachable, elderlyMode, onToggleElderlyMode }) {
  return (
    <header className="header">
      <div className="header__brand">
        <ShieldIcon />
        <div>
          <h1 className="header__title">Kavach</h1>
          <p className="header__tagline">Your armor against scam calls</p>
        </div>
      </div>
      <div className="header__actions">
        <StatusChip health={health} reachable={reachable} />
        <button
          type="button"
          className={`header__elderly-toggle ${elderlyMode ? 'is-active' : ''}`}
          onClick={onToggleElderlyMode}
          aria-pressed={elderlyMode}
        >
          {elderlyMode ? 'Elderly mode: ON' : 'Elderly mode'}
        </button>
      </div>
    </header>
  );
}
