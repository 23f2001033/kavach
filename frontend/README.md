# Kavach frontend

Vite + React single-page app for Kavach: a live mic "Guard" mode, a paste-a-transcript
mode, an upload-a-recording mode, an animated risk gauge, and an elderly-friendly
simplified view. Plain CSS, no UI framework, no external CDNs/fonts — everything
ships from this folder.

## Dev workflow

1. Start the backend first (from `backend/`):
   ```bash
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --reload --port 8000
   ```
2. In another terminal, install and run the frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
3. Open the printed local URL (usually `http://localhost:5173`).

The frontend talks to the backend at `VITE_API_URL` (default `http://localhost:8000`).
Copy `.env.example` to `.env.local` and change it if your backend runs elsewhere.

## Browser support

**Live Guard mode requires Chrome or Edge** (desktop or Android) — it uses the
`SpeechRecognition` / `webkitSpeechRecognition` Web Speech API, which Firefox and
Safari don't implement. If the API isn't available, the app shows a notice and
points the user at **Transcript mode**, which works in any modern browser.

## Demo script suggestion

1. Open the app, confirm the status chip shows the backend online and the text
   model loaded (start `uvicorn` first if it says "unreachable").
2. **Transcript mode** — click "Load example scam", hit Analyze: gauge sweeps to
   red/"high", the alert banner appears, and the scam-sign cards list out
   digital-arrest / OTP-request / secrecy-demand signatures with matched
   snippets. Click "Load example legit" to show the same benign bank-reminder
   call scoring "low" despite mentioning OTP.
3. **Live Guard mode** — click "Start listening", pick a language (en-IN by
   default), and read the example scam script aloud (or have a phone call
   playing near the mic). Watch the rolling transcript fill in and the gauge
   climb in real time; when it crosses into "high" you'll see the pulsing red
   banner, hear a spoken warning once, and see the scam-sign cards populate.
4. **Upload Recording mode** — pick a `.wav`/`.mp3`/`.m4a`/`.ogg`/`.webm` file
   of a recorded call and hit "Analyze recording". The button shows
   "Transcribing... first run downloads the speech model" while the backend
   runs Whisper (the very first call on a fresh backend downloads the model,
   ~464 MB, so that first run takes noticeably longer). Once done you get the
   same gauge/explanation/scam-sign-card view as Transcript mode, plus the
   raw transcript text and a "Voice-clone analysis: N% suspicion" line (or
   "Voice-clone model: not yet loaded" until the ONNX audio model ships).
5. Toggle **Elderly mode** in the header to show the simplified huge-font
   gauge + verdict + one-line advice view (voice alerts stay on).

## How Live Guard polling works

- `useSpeechRecognition` wraps the Web Speech API with `continuous: true,
  interimResults: true`, tracking a rolling **final** transcript plus the
  current **interim** (not-yet-finalized) text, and auto-restarts if Chrome
  silently ends the recognizer after a pause.
- A random `session_id` (`call-xxxxxxxx`) is generated per Live Guard session
  and reused for every request so the backend's stateful rolling window /
  hysteresis (`POST /analyze/window`) sees one continuous call.
- Every time a **final** speech result lands, that new text is POSTed to
  `/analyze/window` immediately.
- In parallel, a 2.5s timer flushes any **interim** text that hasn't been
  finalized yet (so the risk meter doesn't stall waiting on punctuation/pause
  detection) — only the new suffix since the last flush is sent, and the
  tracker resets whenever a final result supersedes it, to keep duplication in
  the rolling window minimal.
- Each response updates the gauge, explanation, and scam-sign cards; a
  `risk_level: "high"` transition (edge-triggered, not every poll) triggers one
  spoken `speechSynthesis` warning via `useVoiceAlert`.

## API contract notes

Built against `backend/kavach/api.py` directly (see `backend/README.md`). One
adaptation from the original spec: signature hits carry a `matches: string[]`
field (not a singular `snippet`) — the UI renders `matches[0]` as the "matched
snippet" on each scam-sign card.

`POST /analyze/recording` is a `multipart/form-data` upload (not JSON), so
`analyzeRecording()` in `api.js` bypasses the shared `request()` helper (which
always sets `Content-Type: application/json`) and lets the browser set its
own multipart boundary.

## Project structure

```
src/
  api.js                    fetch client for /health, /analyze/text, /analyze/window, /analyze/recording
  hooks/
    useHealth.js             polls GET /health
    useSpeechRecognition.js  Web Speech API wrapper (continuous + interim)
    useVoiceAlert.js         speaks once on risk_level -> "high" transitions
  components/
    Header.jsx / StatusChip.jsx      brand, tagline, elderly-mode toggle, backend status
    ModeTabs.jsx                     Live Guard / Transcript mode / Upload Recording switch
    LiveGuard.jsx                    mic mode: language picker, transcript, chunk POSTing
    TranscriptMode.jsx               paste-a-transcript + example loaders
    RecordingMode.jsx                file upload -> /analyze/recording, shows transcript + voice-clone line
    ResultPanel.jsx                  shared result rendering (full or elderly-simplified)
    RiskGauge.jsx                    SVG arc gauge (0-100, animated, colour-coded)
    AlertBanner.jsx / SignatureCards.jsx
    Footer.jsx
  data/exampleTranscripts.js  built-in example scam + legit transcripts
  utils/sessionId.js, advice.js
```
