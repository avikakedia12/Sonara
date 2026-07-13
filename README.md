# Sonara

Sonara turns an audio recording of a piece of music into Braille sheet music, so a blind musician can read notation from a recording rather than relying on someone to transcribe it by hand.

## Pipeline

Audio goes through several stages, each usable as a standalone script and also exposed as an API endpoint (see [API](#api-scriptsapipy) below):

| Stage | Script | Status |
|---|---|---|
| Transcribe: audio → notated score | `scripts/transcribe_audio.py` | Working |
| Braille: score → Braille Music Code | `scripts/to_braille.py` | Working |
| Transpose: score → transposed score for a target instrument | `scripts/transpose_score.py` | Working |
| Describe: score → structural description (+ optional spoken audio) | `scripts/describe_score.py` | Working |

### 1. Transcribe (`scripts/transcribe_audio.py`)

Audio → notated score, using a pretrained model rather than a custom-trained one:

- [basic-pitch](https://github.com/spotify/basic-pitch) (Spotify's pretrained polyphonic transcription model) converts audio to note events (pitch, onset, duration).
- `librosa` detects the beat grid (tempo + beat times) from the audio.
- [music21](https://web.mit.edu/music21/) quantizes note timings onto that beat grid (so they land on musical durations instead of raw seconds) and writes the result out as MusicXML.

basic-pitch's onset/frame detection thresholds materially affect accuracy, and the right threshold depends on the material (dense chamber music vs. solo instrument) — see [Accuracy work](#accuracy-work) below for how this is handled.

```bash
# Basic transcription, unquantized (raw note timings in seconds — fine for playback, not for notation)
python scripts/transcribe_audio.py path/to/audio.wav --out-dir data/transcribed

# Quantized to a 16th-note grid (subdivisions=4), with a custom title
python scripts/transcribe_audio.py path/to/audio.wav --quantize 4 --title "My Piece"

# Override auto-selected thresholds manually instead of adaptive selection
python scripts/transcribe_audio.py path/to/audio.wav --onset-threshold 0.65 --frame-threshold 0.25
```

Output: `<out-dir>/<audio-stem>.musicxml`.

### 2. Braille (`scripts/to_braille.py`)

MusicXML/MIDI/etc. (or a raw audio file) → Braille Music Code, using music21's built-in Braille transcriber (implements the Music Braille Code spec). Braille music is read one line/voice at a time, so this operates on a single `Part` of the score.

If the input's extension is audio (`.wav`, `.mp3`, `.flac`, `.ogg`, `.m4a`, `.aiff`/`.aif`) it's run through `transcribe_audio.transcribe` first — same accuracy caveats as Stage 1 apply in that case; transcribing from a symbolic score directly is still the guaranteed-accurate path. Use `--transcribe-quantize`/`--onset-threshold`/`--frame-threshold` to control that step (distinct from `--quantize` below, which is the braille rhythm quantization applied to the resulting score either way):

```bash
python scripts/to_braille.py data/sample/1727_clip30.wav --transcribe-quantize 4 --melody-only --out my_piece.brl
```

Raw polyphonic transcriptions (especially from an ML model) are often too dense for the Braille engine to lay out cleanly. Two options handle that:

- `--melody-only` collapses simultaneous notes down to the top-sounding pitch (a "skyline" reduction) before transcribing.
- `--quantize` snaps durations to a rhythmic grid (comma-separated divisors, e.g. `4,3` for 16th-note/triplet).

music21's Braille formatter also breaks on long, unbroken passages (e.g. a tremolo with no rests), since it can't wrap a single atomic note-grouping across lines. To work around that, the score is transcribed in fixed-size beat windows (`--chunk-beats`, default 40), and any window that still fails at the standard 40-cell line width is retried at progressively wider widths (80/160/320) before being reported as failed.

```bash
python scripts/to_braille.py data/transcribed/my_piece.musicxml --melody-only --quantize 4,3 --out my_piece.brl
```

Output: two files next to `--out` (or next to the input if `--out` is omitted):
- `.brl` — Unicode Braille with `% beats N-M` section headers, for reading/debugging.
- `.brf` — ASCII BRF (NABCC-encoded via `scripts/notation_utils.py`), containing *only* braille cells with no comments — the format real embossers and Braille displays expect.

### 3. Transpose (`scripts/transpose_score.py`)

MusicXML/MIDI/etc. (or a raw audio file) + target instrument → transposed MusicXML, range-checked against that instrument. This is a deterministic music-theory operation, not a model — no dataset or training involved, unlike transcription.

The part is normalized to sounding (concert) pitch via `music21`'s `toSoundingPitch` (a no-op if it wasn't already transposed), retargeted to the requested instrument, then converted to that instrument's written pitch via `toWrittenPitch` — which uses `music21`'s built-in transposition interval for the instrument (e.g. B♭ clarinet is written a major 2nd above concert pitch). Notes that fall outside the target instrument's playable range are flagged in the output report but **not** altered — no silent octave-shifting or dropping; that's a judgment call for a human, not something to guess at.

Playable ranges are hand-curated (`INSTRUMENT_REGISTRY` in the script) from standard orchestration references, since `music21`'s built-in `Instrument` classes reliably provide a `lowestNote` but almost never a `highestNote`.

```bash
python scripts/transpose_score.py data/transcribed/my_piece.musicxml --target-instrument clarinet --out my_piece_clarinet.musicxml
```

If the input's extension is audio (`.wav`, `.mp3`, `.flac`, `.ogg`, `.m4a`, `.aiff`/`.aif`) it's run through `transcribe_audio.transcribe` first — same accuracy caveats as Stage 1 apply in that case (see Accuracy work below); transposing a symbolic score directly is still the guaranteed-accurate path:

```bash
python scripts/transpose_score.py data/sample/1727_clip30.wav --target-instrument clarinet --quantize 4
```

Supported instruments: `flute`, `oboe`, `clarinet`, `bassoon`, `alto_sax`, `tenor_sax`, `trumpet`, `horn`, `violin`, `viola`, `cello`, `contrabass`, `piano`, `english_horn`.

### 4. Describe (`scripts/describe_score.py`)

MusicXML/MIDI/etc. (or a raw audio file) → structural text description, at multiple detail levels — meant to orient a blind musician (title, instrumentation, key, time signature, tempo, length) before they read the piece note-by-note in Braille.

- `--level brief`: header, key, time signature, tempo, measure count/duration.
- `--level standard` *(default)*: + per-part pitch range and dynamics used.
- `--level detailed`: + a full measure-by-measure log of every tempo/time-signature/dynamic change.

Key is read from an explicit key signature if the score has one; otherwise it's *estimated* via music21's Krumhansl-Schmuckler key-finding algorithm and labeled `(estimated)` — a best guess, not ground truth, and can be wrong on ambiguous or modulating material. Duration is likewise an estimate (total length ÷ the first tempo marking, ignoring any later tempo changes) — good enough for "about three minutes," not a stopwatch-precise figure.

Same audio-input handling as Braille/Transpose: an audio file extension runs through `transcribe_audio.transcribe` first, with the same accuracy caveats.

```bash
python scripts/describe_score.py data/transcribed/my_piece.musicxml --level detailed
```

`--speak` additionally renders the description to speech audio via [pyttsx3](https://pypi.org/project/pyttsx3/) (offline/local TTS, no network calls, no dataset/training involved — optional dependency, only needed for `--speak`):

```bash
pip install pyttsx3
python scripts/describe_score.py data/transcribed/my_piece.musicxml --speak --tts-out my_piece_description.aiff
```

### 5. Difficulty (`scripts/difficulty_score.py`)

MusicXML/MIDI/etc. (or a raw audio file) → an estimated performance difficulty per part (0-10, mapped to Beginner/Easy/Intermediate/Advanced/Virtuosic), plus the exact numbers behind the rating rather than just a label.

Each factor is a deterministic, rule-based measurement — no ML model, nothing trained on a difficulty-graded corpus:

- **Rhythm** — fastest note value present, tuplet usage, and share of note onsets landing off the beat.
- **Melodic leaps** — average interval between consecutive notes, and how many exceed an octave.
- **Chord density** — share of note-events that are chords, and average chord size.
- **Tempo & pace** — notes/second at the marked tempo (or 120bpm if none is present).
- **Pitch range** — ambitus in semitones.
- **Key signature** — number of sharps/flats.
- **Time signature** — irregular/compound meters and meter changes.

A weighted combination of these gives each part's score; the piece's overall score is its hardest part's. Treat the numbers as "harder than X, easier than Y" signal, not a certified grade level — same spirit as Transpose's hand-curated instrument ranges, not a substitute for a teacher's judgment. Same audio-input handling as Braille/Transpose/Describe: an audio file extension runs through `transcribe_audio.transcribe` first, with the same accuracy caveats.

```bash
python scripts/difficulty_score.py data/transcribed/my_piece.musicxml --out difficulty_report.json
```

## Accuracy work

### Evaluation methodology

`scripts/evaluate_transcription.py` scores a transcription against [MusicNet](https://homes.cs.washington.edu/~thickstn/musicnet.html) ground truth using an accessibility-weighted error taxonomy (`W`) instead of plain precision/recall. The reasoning: a wrong key signature or a systematic octave error makes a piece functionally unusable for a blind musician, while a handful of enharmonic spelling quirks barely matter — but standard F-measure weighs those the same.

| Tier | Weight | Examples |
|---|---|---|
| 1 — Catastrophic | 16 | Wrong key signature; systematic octave errors (affecting a large share of notes) |
| 2 — Severe | 8 | Isolated octave errors; clustered runs (≥3) of missing/extra notes |
| 3 — Moderate | 2 | An isolated missing or extra note |
| 4 — Minor | 1 | Noticeable tempo deviation from the implied ground-truth BPM |

Tempo is always Tier 4 here, regardless of how far off it is — an imprecise tempo marking doesn't block a blind musician from learning notes/rhythm off a Braille score the way a wrong pitch does, so it never escalates under this taxonomy. Several tier items in the full taxonomy (wrong time signature, missing clef, missing accidentals, incorrect rhythm in a motif, missing articulation, incorrect ornament) aren't measurable from MusicNet's flat note-event ground truth and are reported as N/A rather than faked — see the script's docstring for the full breakdown.

`W = 16·catastrophic + 8·severe + 2·moderate + 1·minor`. Standard `mir_eval` onset+pitch F-measure is also printed alongside `W`, to show how two transcriptions with similar F-measure can have very different real-world usability. Enharmonic spelling errors are reported as N/A rather than faked — MIDI pitch numbers (used for note-event comparison) don't carry spelling information (F♯ and G♭ are both 66), so that check would require diffing engraved notation, not raw pitches.

```bash
python scripts/evaluate_transcription.py --ground-truth-csv data/1727.csv --audio data/sample/1727_clip30.wav --max-seconds 30
```

`scripts/build_score.py` separately converts MusicNet's raw label CSVs into reference MusicXML (for inspecting ground truth as notation, not for the `W` scoring itself, which reads the CSV directly):

```bash
python scripts/build_score.py --id 1727 --data-dir archive/musicnet/musicnet --metadata archive/musicnet_metadata.csv
```

### Adaptive threshold selection

basic-pitch's onset/frame detection thresholds have a measured, material-dependent effect on accuracy: raising them above the stock defaults helps on dense, multi-instrument recordings but hurts sparse/solo material. `scripts/notation_utils.py::predict_notes_adaptive` handles this by probing a recording with stock thresholds, estimating its polyphony (average simultaneous notes per onset), and switching to stricter thresholds only if the material looks dense — calibrated against measured MusicNet ground-truth results rather than basic-pitch's stock defaults.

This was investigated further with a broader 7-piece calibration set spanning solo violin, solo piano, piano trio, wind quintet, string quartet, accompanied violin, and piano quintet. The finding: optimal thresholds don't correlate cleanly with polyphony alone (e.g. a wind quintet and a piano quintet at similar polyphony want opposite threshold adjustments), and a more granular per-piece lookup was tested but performed *worse* than the current 2-point heuristic under honest leave-one-out validation. So the current calibration stands — it's a case where a data-starved "smarter" model generalizes worse than a simpler one, not a bug. Improving this further would need either substantially more ground-truth calibration data, a better predictive signal than polyphony (e.g. an instrument/genre classifier), or source-separation preprocessing to reduce polyphony before transcription — all future work.

## API (`scripts/api.py`)

A FastAPI service wrapping the five working pipeline stages as REST endpoints — thin request/response handling only, no logic duplicated from the scripts above.

```bash
uvicorn api:app --reload --port 8000
# interactive docs at http://127.0.0.1:8000/docs
```

| Endpoint | Input | Output |
|---|---|---|
| `POST /transcribe` | audio file *or* `youtube_url` (+ optional `quantize`, `title`, thresholds) | `{musicxml, polyphony, thresholds_used, tempo_bpm, sheet_music_svg, accuracy_note}` |
| `POST /braille` | score file, audio file, *or* `youtube_url` (+ `part_index`, `melody_only`, `quantize`, `chunk_beats`, and if audio: `transcribe_quantize`, thresholds) | `{brl, brf, chunks_transcribed, chunks_total, failed_chunks, accuracy_note if input was audio}` |
| `POST /transpose` | score file, audio file, *or* `youtube_url` + `target_instrument` (+ `part_index`, and if audio: `quantize`, thresholds) | `{musicxml, target_instrument, playable_range, out_of_range_notes, sheet_music_svg, accuracy_note if input was audio}` |
| `POST /describe` | score file, audio file, *or* `youtube_url` (+ `level`, `speak`, and if audio: `transcribe_quantize`, thresholds) | `{description, level, accuracy_note if input was audio, audio_base64 + audio_format if speak=true}` |
| `POST /difficulty` | score file, audio file, *or* `youtube_url` (+ if audio: `transcribe_quantize`, thresholds) | `{overall_score, overall_level, hardest_part, summary, per_part: [{name, score, level, factors}], accuracy_note if input was audio}` |

`/transcribe`'s response always includes `accuracy_note`, since transcription accuracy is best-effort (see Accuracy work below) — the API doesn't let that caveat get silently lost the way a bare file download would. `/braille`, `/transpose`, and `/describe` include the same `accuracy_note` when their input was audio (they transcribe internally first), and omit it when given a symbolic score directly. `/describe`'s `speak=true` requires `pyttsx3` to be installed server-side (see Setup) and returns the rendered speech as base64-encoded AIFF.

Every endpoint accepts a `youtube_url` form field as an alternative to uploading a file (exactly one of the two must be provided) — the audio track is downloaded via `yt-dlp` (`scripts/youtube_input.py`) and fed into the same pipeline as any other audio upload.

`sheet_music_svg` (`/transcribe` and `/transpose`) is the score actually rendered to visual notation -- one SVG string per page, via `scripts/render_score.py` (uses [verovio](https://www.verovio.org/), a lightweight engraving library, so no desktop notation app like MuseScore/LilyPond needs to be installed). Raw, unquantized transcription can render as dense/hard-to-read notation (irregular tuplets and ties); pass `quantize` for cleaner sheet music.

## Setup

```bash
pip install librosa numpy music21 basic-pitch mir_eval fastapi uvicorn python-multipart verovio yt-dlp
```

(`basic-pitch` pulls in `pretty_midi` and a TensorFlow/CoreML/ONNX backend as transitive dependencies, depending on platform. `yt-dlp` is used only for the `youtube_url` input option on the API endpoints — no `ffmpeg` needed, since it downloads the audio-only stream directly; see `scripts/youtube_input.py`.)

`pyttsx3` is an additional, optional dependency needed only for Describe's `--speak`/`speak=true` speech rendering:

```bash
pip install pyttsx3
```

## Tests

```bash
pip install pytest httpx  # httpx is needed by FastAPI's TestClient
pytest
```

Covers the deterministic logic across all five scripts (transpose range-checking, Braille chunking, Describe's text generation, Difficulty's factor scoring, the MusicNet CSV/W-score plumbing) and every API endpoint's request/response contract, using synthetic scores and a faked `transcribe()` so the suite runs in ~2 seconds without invoking real basic-pitch inference. A separate `pytest -m slow` runs three additional true end-to-end tests against real audio transcription (`data/sample/1727_clip30.wav`, several seconds each, skipped by default) — these are the ones that would catch an actual regression in the transcription pipeline itself rather than just its call site. Tests that need `data/sample/` are skipped automatically if that gitignored directory isn't populated locally.

## Layout

```
scripts/     pipeline scripts (see above)
data/        MusicNet ground-truth label CSVs (<id>.csv) + data/sample/ audio and example outputs
archive/     raw MusicNet download (audio, labels, MIDI, metadata) used to regenerate data/
```

## Deployment

`render.yaml` at the repo root is a [Render Blueprint](https://render.com/docs/blueprint-spec) defining two services:

- `sonara-backend` — a Python **web service** (long-running, not serverless: basic-pitch's model load and audio transcription can take a minute or more, which would blow past a serverless function's execution limit) running `uvicorn api:app --app-dir scripts --host 0.0.0.0 --port $PORT`, deps from `requirements.txt` at the repo root.
- `sonara-frontend` — a **static site** built from `frontend/` (`npm install && npm run build`, publishing `frontend/dist`), with SPA-style routing so any path falls back to `index.html`.

To deploy: push to GitHub, then in Render, "New" → "Blueprint" → point it at this repo. Render reads `render.yaml` and provisions both services.

The two services need to know each other's URL:

- `sonara-backend`'s `FRONTEND_ORIGIN` env var must match the frontend's deployed URL (used for CORS — see `scripts/api.py`).
- `sonara-frontend`'s `VITE_API_BASE` build-time env var must match the backend's deployed URL (see `frontend/src/api.js`).

`render.yaml` hardcodes both as `https://sonara-<backend|frontend>.onrender.com`, which is what Render assigns if those service names are available. **If either name is already taken**, Render will suffix it (e.g. `sonara-backend-ab12`) — check the actual assigned URLs after first deploy and update both env vars (in the Render dashboard, or in `render.yaml` + redeploy) to match if they differ.

Known gaps, not yet handled:
- No rate limiting — every endpoint (including the ones that download audio from a `youtube_url`) is open to the public internet once deployed. Worth adding before real traffic.
- `/describe`'s `speak=true` needs `pyttsx3` plus a working OS-level TTS backend (e.g. `espeak` on Linux) — deliberately not installed on the deployed backend (see `requirements.txt`), so `speak=true` will return a clean 422 there rather than working.
- basic-pitch pulls in a TensorFlow/CoreML/ONNX backend depending on platform; on Render's Linux containers this resolves to TensorFlow, which is memory-hungry. If the backend fails to build or crashes under load on Render's free tier, it likely needs a paid instance type with more RAM.

## Status

Early-stage. Transcribe → Braille → Transpose → Describe → Difficulty all work end-to-end on sample audio, with an evaluation harness against real ground truth for transcription accuracy, and an automated `pytest` suite (120 fast tests + 3 slow real-audio integration tests) covering all five scripts and the API.
