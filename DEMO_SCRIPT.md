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

The six slides map onto the script as: **1** Kavach title (Scene 1), **2** what it does
(Scene 1), **3** the ₹22,495 crore stat (Scene 2), **4** the voice-cloning gap (Scene 2),
**5** the results table (Scene 7), **6** the end card with the GitHub link (Scene 7).
Numbers on slide 5 are the real measured ones — if you re-run the evals and they move,
update that slide to match.

**Recording tip:** go fullscreen and press `H` first, so no browser chrome, dots, or
keyboard hint appear in the video. Each slide animates in when you land on it, so pause
about half a second after advancing before you start talking.

---

## Shot list

### Scene 1 — What it is (0:00–0:14)

Say what the thing *is* before you say why it matters. A judge watching their fortieth
submission needs something concrete to hang the statistics on, and you have about ten
seconds to give it to them. No jargon here — no "fusion", no model names, nothing that
needs a second sentence to explain.

**Screen:** `demo_assets/slides.html` fullscreen — slide 1 (Kavach title), then advance to
slide 2 (what it does) as you start the second sentence.

**Narration:**
> "This is Kavach. It listens to a phone call while it's happening, and tells you — in
> plain words — whether you're being scammed, and exactly why. It can even tell when the
> voice on the other end is an AI clone. And all of it runs on your own device."

### Scene 2 — Why it matters (0:14–0:30)

**Screen:** Slide 3 (₹22,495 crore) as you say the number, then slide 4 (voice cloning)
— then alt-tab to the Kavach app.

**Narration:**
> "It matters because in 2025, Indians lost ₹22,495 crore — about $2.7 billion — to cyber
> fraud. Cloning someone's voice now takes as little as three seconds of audio. And your
> phone's blocklist only knows about numbers that have already claimed a victim. Nothing
> protects you during the call itself. Let me show you."

### Scene 3 — Live Guard flags a scam in real time (0:30–1:12)

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

### Scene 4 — Why: the explanation cards (1:12–1:38)

**Screen:** Scroll down to the scam-sign cards under the gauge. Point at (cursor
highlight or slow pan) two or three specific cards.

**Narration:**
> "This isn't a black-box score. Kavach shows exactly why: here, a 'digital arrest'
> threat — there's no such thing, real police never arrest anyone over a phone call —
> and a secrecy demand, telling you not to tell your family. Each card quotes the exact
> line that triggered it."

### Scene 5 — Elderly Mode (1:38–1:54)

**Screen:** Toggle Elderly Mode in the header. The view simplifies to a huge gauge, a
one-line verdict, and one piece of advice.

**Narration:**
> "Scam callers target elderly people hardest, so we built for them specifically —
> Elderly Mode strips everything down to one gauge, one verdict, one line of advice.
> No jargon, no cards to parse under stress."

### Scene 6 — Recording upload + voice-clone detection (1:54–2:26)

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

### Scene 7 — Closing: rigor + privacy (2:26–2:52)

**Screen:** Cut back to `slides.html` — slide 5 (the results grid) while you talk about
the evaluation, then slide 6 (end card with the GitHub link) to close on.

**Narration:**
> "We didn't just build this — we tested it honestly. Our own evaluation suite found five
> real bugs in our system before any judge could: fusion math that was quietly weakening
> our best signal, a model that looked perfect on synthetic data and wasn't, and a voice
> detector confident enough to call a clinic's appointment reminder a scam. We fixed all
> five and published the before-and-after numbers instead of burying them. And every part
> of the detection — transcription, text scoring, voice forensics — runs offline, on the
> machine in front of you. No API keys, no audio ever leaving the device. This is Kavach."

**End card:** Project name, GitHub link (`github.com/23f2001033/kavach`), team/build
challenge name.

---

## Timing summary

| Scene | Time | Cumulative |
|---|---|---|
| 1. What it is | 14s | 0:14 |
| 2. Why it matters | 16s | 0:30 |
| 3. Live Guard flags scam | 42s | 1:12 |
| 4. Explanation cards | 26s | 1:38 |
| 5. Elderly Mode | 16s | 1:54 |
| 6. Recording upload / voice clone | 32s | 2:26 |
| 7. Closing: rigor + privacy | 26s | 2:52 |

Total: **~2:52**, inside the 2.5–3 minute target. If you need to trim, Scene 5 (Elderly
Mode) and the results cutaway in Scene 7 are the safest to shorten first — Scenes 3 and 4
are the emotional and technical core and shouldn't be cut. **Do not trim Scene 1**: the
first ten seconds decide whether a judge watches the rest with attention or with one eye.

### Optional Scene 6b — the call it *doesn't* panic about (+15s)

If you can spare the time, upload `demo_assets/demo_benign_call.wav` right after Scene 6
and let it land on "suspicious" rather than "high":

> "And here's a real clinic appointment reminder — also a synthetic voice, because most
> automated calls are. Kavach notices the voice, says so honestly, and still doesn't call
> it a scam. Getting that right matters as much as catching the scam: an app that cries
> wolf at every robocall is an app people switch off."

This is worth more to a technical judge than a second scam that lights up red — it shows
you designed for false positives, which is the difference between a demo and a product.
