// Thin client for the Kavach backend API.
//
// Contract (see backend/README.md + backend/kavach/api.py):
//   GET  /health                            -> { status, models: { text, audio } }
//   POST /analyze/text   { transcript }     -> AnalyzeResponse
//   POST /analyze/window { transcript, session_id } -> AnalyzeResponse (stateful, hysteresis)
//
// AnalyzeResponse:
//   {
//     risk_score: number (0..1),
//     risk_level: "low" | "suspicious" | "high",
//     text_score: number | null,
//     signature_hits: [{ id, name, scam_type, severity, explanation, matches: string[] }],
//     explanation: string,
//   }
//
// Note: the API contract doc mentions an optional `snippet` field on signature
// hits, but the live backend (backend/kavach/api.py::SignatureHitOut) returns
// `matches: string[]` instead. We render the first entry of `matches` as the
// "matched snippet" on signature cards.

export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiError extends Error {
  constructor(message, cause) {
    super(message);
    this.name = 'ApiError';
    this.cause = cause;
  }
}

async function request(path, options) {
  let res;
  try {
    res = await fetch(`${API_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
  } catch (err) {
    throw new ApiError(`Could not reach the Kavach backend at ${API_URL}. Is it running?`, err);
  }
  if (!res.ok) {
    let detail = '';
    try {
      const body = await res.json();
      detail = body?.detail ? ` - ${JSON.stringify(body.detail)}` : '';
    } catch {
      // ignore body parse errors
    }
    throw new ApiError(`Backend request to ${path} failed (${res.status})${detail}`);
  }
  return res.json();
}

export function getHealth() {
  return request('/health', { method: 'GET' });
}

export function analyzeText(transcript) {
  return request('/analyze/text', {
    method: 'POST',
    body: JSON.stringify({ transcript }),
  });
}

export function analyzeWindow(transcript, sessionId) {
  return request('/analyze/window', {
    method: 'POST',
    body: JSON.stringify({ transcript, session_id: sessionId }),
  });
}

export { ApiError };
