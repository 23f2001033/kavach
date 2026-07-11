import { useEffect, useRef, useState } from 'react';
import { getHealth } from '../api.js';

/** Polls GET /health periodically and reports backend + model status. */
export function useHealth(pollMs = 15000) {
  const [health, setHealth] = useState(null); // { status, models: { text, audio } }
  const [reachable, setReachable] = useState(null); // null = unknown yet
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;

    async function check() {
      try {
        const data = await getHealth();
        if (!mounted.current) return;
        setHealth(data);
        setReachable(true);
      } catch {
        if (!mounted.current) return;
        setReachable(false);
        setHealth(null);
      }
    }

    check();
    const id = setInterval(check, pollMs);
    return () => {
      mounted.current = false;
      clearInterval(id);
    };
  }, [pollMs]);

  return { health, reachable };
}
