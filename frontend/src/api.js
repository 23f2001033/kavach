// Thin client for the Kavach backend API.
//
// Contract (see backend/README.md + backend/kavach/api.py):
//   GET  /health                            -> { status, models: { text, audio } }
//   POST /analyze/text      { transcript }     -> AnalyzeResponse
//   POST /analyze/window    { transcript, session_id } -> AnalyzeResponse (stateful, hysteresis)
//   POST /analyze/recording  multipart file upload      -> RecordingAnalyzeResponse
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
// RecordingAnalyzeResponse extends AnalyzeResponse with:
//   {
//     transcript: string,            // Whisper transcript, "Caller: " prefixed (no diarization, v1)
//     language: string | null,       // detected language code, e.g. "en"
//     audio_score: number | null,    // voice-clone suspicion in [0,1], or null if no audio model loaded
//     duration_seconds: number,
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

// Multipart upload — deliberately doesn't go through request() above, since
// that helper always sets Content-Type: application/json; the browser needs
// to set its own multipart/form-data boundary for a file upload instead.
export async function analyzeRecording(file) {
  const formData = new FormData();
  formData.append('file', file);

  let res;
  try {
    res = await fetch(`${API_URL}/analyze/recording`, { method: 'POST', body: formData });
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
    throw new ApiError(`Backend request to /analyze/recording failed (${res.status})${detail}`);
  }
  return res.json();
}

export { ApiError };
