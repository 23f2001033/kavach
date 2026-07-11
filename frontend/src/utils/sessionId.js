// Generate a random per-session id for /analyze/window, e.g. "call-9f2a1c3d".
export function newSessionId() {
  const rand =
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID().slice(0, 12)
      : Math.random().toString(36).slice(2, 14);
  return `call-${rand}`;
}
