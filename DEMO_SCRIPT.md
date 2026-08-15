# Kavach — demo video shot script

Target length: **2.5–3 minutes**. Written for a screen recording with voiceover (record
narration live while screen-sharing, or record screen + audio separately and sync in
editing — either works with the tools below).

---

## Pre-recording checklist

1. **Start the backend** in one terminal:
   ```bash
   cd backend
   uvicorn main:app --reload --port 8000
   ```
   Wait for it to say it's running, then hit `http://localhost:8000/health` once in a
   browser tab to confirm `"status": "ok"` and check what `models.text` / `models.audio`
   report — know this before you record so you're not surprised on camera.
2. **Start the frontend** in a second terminal:
   ```bash
   cd frontend
   npm run dev
   ```
3. **Use Chrome** (or Edge) — Live Guard mode needs the Web Speech API, which Firefox/Safari
   don't support.
4. **Grant mic permission** to `localhost:5173` *before* you hit record — click "Start
   listening" once ahead of time so the OS/browser permission prompt doesn't eat time
   on camera, then refresh.
5. **Have tabs open and ready, in this order:**
   - Tab 1: Kavach app, Transcript mode, with the built-in example scam transcript
     already loaded (don't click Analyze yet).
   - Tab 2: Kavach app, Live Guard mode, ready to click "Start listening."
   - Tab 3: Kavach app, Recording Upload mode, with your test recording already
     selected in the file picker (don't click Analyze yet).
   - A window/notes doc with the digital-arrest script text large enough to read aloud
     naturally without sounding like you're reading (see Scene 2 below).
6. **Close notification popups / Slack / email** — anything that could pop up on screen.
7. **Do one full silent dry run** of all three modes right before recording, to warm up
   the faster-whisper model cache (first call downloads ~464MB and is slow) and confirm
   `models.text` / `models.audio` are both loaded so the demo shows real scores, not
   nulls.
8. **Test your mic level and browser tab audio** together if you're narrating live over
   the screen recording — a quick 10-second test recording avoids finding out about a
   silent mic after the full take.

**Suggested free screen-recording tools:** OBS Studio (full control, free, cross-platform),
Windows 11's built-in Xbox Game Bar (`Win+G`, zero install), or ScreenPal / Loom free tier
if you want built-in webcam-in-corner + easy trimming without a separate editor.

## Title cards / slides

Open **`demo_assets/slides.html`** in Chrome — it's a self-contained 5-slide deck styled to
match the app, no internet or design tool needed. Controls:

| Key | Action |
|---|---|
| `→` / `Space` / click | next slide |
| `←` | previous slide |
| `F` | fullscreen (or just press `F11`) |
| `H` | hide the progress dots — **do this before you record** |

The five slides map onto the script as: **1** Kavach title (Scene 1), **2** the ₹22,495
crore stat (Scene 1), **3** the 3–30-second voice-cloning gap (Scene 1), **4** the results
table (Scene 6), **5** the end card with the GitHub link (Scene 6). Numbers on slide 4 are
the real measured ones — if you re-run the evals and they move, update that slide to match.

**Recording tip:** go fullscreen and press `H` first, so no browser chrome, dots, or
keyboard hint appear in the video. Each slide animates in when you land on it, so pause
about half a second after advancing before you start talking.

---

## Shot list

### Scene 1 — The hook (0:00–0:20)

**Screen:** `demo_assets/slides.html` fullscreen — slide 1 (Kavach title), advance to
slide 2 (₹22,495 crore) as you say the number, then slide 3 (voice cloning) — then
alt-tab to the Kavach app landing/header.

**Narration:**
> "In 2025, Indians lost ₹22,495 crore — about $2.7 billion — to cyber fraud. Voice
> cloning now needs just three to thirty seconds of audio to fake a familiar voice. And
> in June 2026, the Five Eyes intelligence alliance said what security researchers
> already knew: voice confirmation alone can no longer verify who's calling you. This is
> Kavach — real-time, explainable scam-call defense that runs while the call is still
> happening."

### Scene 2 — Live Guard flags a scam in real time (0:20–1:05)

**Screen:** Switch to the Live Guard tab. Click "Start listening." Read the digital-arrest
script aloud, at a natural pace, watching the rolling transcript fill in live and the risk
gauge climb.

**Script to read aloud** (a shortened digital-arrest scenario):
> "This is Inspector Sharma from Cyber Crime Cell. Your Aadhaar number has been used in a
> money laundering case. This is a matter of national security — you are now under
> digital arrest. Do not disconnect this call, and do not tell anyone, not even your
> family. Stay on this video call and share the OTP that was just sent to your phone, or
> an FIR will be registered against you within the next ten minutes."

**Narration (overlapping / after):**
> "Watch the gauge — it's climbing as the transcript comes in, live, sentence by
> sentence. No waiting for the call to end."

**On "high" trigger:** let the pulsing red banner and the one-time spoken warning play
out fully on camera — don't cut it short, this is the payoff beat.

> "And there's the warning — spoken once, so it interrupts without becoming noise."

### Scene 3 — Why: the explanation cards (1:05–1:35)

**Screen:** Scroll down to the scam-sign cards under the gauge. Point at (cursor
highlight or slow pan) two or three specific cards.

**Narration:**
> "This isn't a black-box score. Kavach shows exactly why: here, a 'digital arrest'
> threat — there's no such thing, real police never arrest anyone over a phone call —
> and a secrecy demand, telling you not to tell your family. Each card quotes the exact
> line that triggered it."

### Scene 4 — Elderly Mode (1:35–1:55)

**Screen:** Toggle Elderly Mode in the header. The view simplifies to a huge gauge, a
one-line verdict, and one piece of advice.

**Narration:**
> "Scam callers target elderly people hardest, so we built for them specifically —
> Elderly Mode strips everything down to one gauge, one verdict, one line of advice.
> No jargon, no cards to parse under stress."

### Scene 5 — Recording upload + voice-clone detection (1:55–2:30)

**Screen:** Switch to the Recording Upload tab. Click "Analyze recording" on the
pre-selected file. Show the "Transcribing..." state briefly, then the result: gauge,
transcript text, and the voice-clone suspicion line.

**Narration:**
> "You can also upload a recorded call. Kavach transcribes it locally with Whisper, runs
> the same scam-language and signature analysis — and, because we have the actual audio
> here, adds a third signal: a voice-forensics model that checks whether the voice itself
> is AI-cloned or synthetic, not just what was said."

*(If your test file is a synthesized/cloned voice, point out the specific audio-suspicion
percentage on screen here.)*

### Scene 6 — Closing: rigor + privacy (2:30–2:55)

**Screen:** Cut back to `slides.html` — slide 4 (the results grid) while you talk about
the evaluation, then slide 5 (end card with the GitHub link) to close on.

**Narration:**
> "We didn't just build this — we evaluated it honestly. Our own eval suite caught a real
> bug in our fusion logic and an overfitting text model before any judge could, and we
> published the before-and-after numbers instead of hiding them. And every piece of
> detection here — transcription, text scoring, voice forensics — runs completely
> offline, locally, on the machine in front of you. No external API required, no audio
> ever has to leave the device. This is Kavach."

**End card:** Project name, GitHub link (`github.com/23f2001033/kavach`), team/build
challenge name.

---

## Timing summary

| Scene | Time | Cumulative |
|---|---|---|
| 1. Hook | 20s | 0:20 |
| 2. Live Guard flags scam | 45s | 1:05 |
| 3. Explanation cards | 30s | 1:35 |
| 4. Elderly Mode | 20s | 1:55 |
| 5. Recording upload / voice clone | 35s | 2:30 |
| 6. Closing: rigor + privacy | 25s | 2:55 |

Total: **~2:55**, inside the 2.5–3 minute target. If you need to trim, Scene 4 (Elderly
Mode) and the eval-numbers cutaway in Scene 6 are the safest to shorten first — Scenes 2
and 3 are the emotional and technical core and shouldn't be cut.
