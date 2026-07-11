import { useState } from 'react';
import Header from './components/Header.jsx';
import Footer from './components/Footer.jsx';
import ModeTabs from './components/ModeTabs.jsx';
import LiveGuard from './components/LiveGuard.jsx';
import TranscriptMode from './components/TranscriptMode.jsx';
import { useHealth } from './hooks/useHealth.js';
import './App.css';

export default function App() {
  const [mode, setMode] = useState('live');
  const [elderlyMode, setElderlyMode] = useState(false);
  const { health, reachable } = useHealth();

  return (
    <div className={`app ${elderlyMode ? 'app--elderly' : ''}`}>
      <Header
        health={health}
        reachable={reachable}
        elderlyMode={elderlyMode}
        onToggleElderlyMode={() => setElderlyMode((v) => !v)}
      />
      <main className="app__main">
        {!elderlyMode && <ModeTabs mode={mode} onChange={setMode} />}
        {mode === 'live' ? <LiveGuard elderlyMode={elderlyMode} /> : <TranscriptMode elderlyMode={elderlyMode} />}
      </main>
      <Footer />
    </div>
  );
}
