# Sonara

Sonara turns an audio recording of a piece of music into Braille sheet music, so a blind musician can read notation from a recording rather than relying on someone to transcribe it by hand.

## Pipeline

Audio goes through several stages, each usable as a standalone script today and mapped to a planned API endpoint:

| Stage | Script | Status |
|---|---|---|
| Transcribe: audio → notated score | `scripts/transcribe_audio.py` | Working |
| Braille: score → Braille Music Code | `scripts/to_braille.py` | Working |
| Transpose: score → transposed score for a target instrument | `scripts/transpose_score.py` | Working |
| Describe: score → spoken structural description | *(planned)* | Not started |

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

MusicXML/MIDI/etc. → Braille Music Code, using music21's built-in Braille transcriber (implements the Music Braille Code spec). Braille music is read one line/voice at a time, so this operates on a single `Part` of the score.

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

MusicXML/MIDI/etc. + target instrument → transposed MusicXML, range-checked against that instrument. This is a deterministic music-theory operation, not a model — no dataset or training involved, unlike transcription.

The part is normalized to sounding (concert) pitch via `music21`'s `toSoundingPitch` (a no-op if it wasn't already transposed), retargeted to the requested instrument, then converted to that instrument's written pitch via `toWrittenPitch` — which uses `music21`'s built-in transposition interval for the instrument (e.g. B♭ clarinet is written a major 2nd above concert pitch). Notes that fall outside the target instrument's playable range are flagged in the output report but **not** altered — no silent octave-shifting or dropping; that's a judgment call for a human, not something to guess at.

Playable ranges are hand-curated (`INSTRUMENT_REGISTRY` in the script) from standard orchestration references, since `music21`'s built-in `Instrument` classes reliably provide a `lowestNote` but almost never a `highestNote`.

```bash
python scripts/transpose_score.py data/transcribed/my_piece.musicxml --target-instrument clarinet --out my_piece_clarinet.musicxml
```

Supported instruments: `flute`, `oboe`, `clarinet`, `bassoon`, `alto_sax`, `tenor_sax`, `trumpet`, `horn`, `violin`, `viola`, `cello`, `contrabass`, `piano`, `english_horn`.

### 4. Describe *(planned)*

MusicXML → structural text description → spoken-audio rendering (e.g. via TTS), at multiple detail levels.

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

A FastAPI service wrapping the three working pipeline stages as REST endpoints — thin request/response handling only, no logic duplicated from the scripts above.

```bash
uvicorn api:app --reload --port 8000
# interactive docs at http://127.0.0.1:8000/docs
```

| Endpoint | Input | Output |
|---|---|---|
| `POST /transcribe` | audio file (+ optional `quantize`, `title`, thresholds) | `{musicxml, polyphony, thresholds_used, tempo_bpm, accuracy_note}` |
| `POST /braille` | score file (+ `part_index`, `melody_only`, `quantize`, `chunk_beats`) | `{brl, brf, chunks_transcribed, chunks_total, failed_chunks}` |
| `POST /transpose` | score file + `target_instrument` (+ `part_index`) | `{musicxml, target_instrument, playable_range, out_of_range_notes}` |
| `POST /describe` | score file | `501 Not Implemented` — honest placeholder, not implemented yet |

`/transcribe`'s response always includes `accuracy_note`, since transcription accuracy is best-effort (see Accuracy work below) — the API doesn't let that caveat get silently lost the way a bare file download would.

## Setup

```bash
pip install librosa numpy music21 basic-pitch mir_eval fastapi uvicorn python-multipart
```

(`basic-pitch` pulls in `pretty_midi` and a TensorFlow/CoreML/ONNX backend as transitive dependencies, depending on platform.)

## Layout

```
scripts/     pipeline scripts (see above)
data/        MusicNet ground-truth label CSVs (<id>.csv) + data/sample/ audio and example outputs
archive/     raw MusicNet download (audio, labels, MIDI, metadata) used to regenerate data/
```

## Status

Early-stage. Transcribe → Braille → Transpose all work end-to-end on sample audio, with an evaluation harness against real ground truth for transcription accuracy; describe is not yet implemented.
