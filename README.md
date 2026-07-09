# Sonara

Sonara turns an audio recording of a piece of music into Braille sheet music, so a blind musician can read notation from a recording rather than relying on someone to transcribe it by hand.

## Pipeline

Audio goes through several stages, each usable as a standalone script today and mapped to a planned API endpoint:

1. **Transcribe** (`scripts/transcribe_audio.py`) — audio → notated score. Uses Spotify's [basic-pitch](https://github.com/spotify/basic-pitch) (pretrained polyphonic transcription) to get note events, `librosa` to detect the beat grid, and [music21](https://web.mit.edu/music21/) to quantize those notes onto it and emit MusicXML. No training involved — this is the pretrained-model path, not a custom-trained one.
2. **Braille** (`scripts/to_braille.py`) — MusicXML → Braille Music Code. Uses `music21`'s built-in Braille transcriber, chunked into beat windows (music21's formatter is unreliable on long, unbroken passages) and exported as both annotated `.brl` and embosser-ready ASCII `.brf` (NABCC-encoded, via `scripts/notation_utils.py`).
3. **Transpose** *(planned)* — MusicXML + target instrument → transposed MusicXML/BRF, range-checked against the instrument.
4. **Describe** *(planned)* — MusicXML → structural text description → spoken-audio rendering.

## Accuracy work

`scripts/evaluate_transcription.py` scores a transcription against [MusicNet](https://homes.cs.washington.edu/~thickstn/musicnet.html) ground truth using an accessibility-weighted error taxonomy (`W`) instead of plain precision/recall — the idea being that a wrong key signature or a systematic octave error makes a piece functionally unusable for a blind musician, while a handful of enharmonic spelling quirks barely matter, and standard F-measure treats those the same. `scripts/build_score.py` converts MusicNet's raw label CSVs into reference MusicXML for this comparison.

Note-decoding parameters (onset/frame thresholds, `melodia_trick`, minimum note length) are chosen adaptively per recording in `scripts/notation_utils.py::predict_notes_adaptive` based on estimated polyphony, calibrated against measured ground-truth results rather than basic-pitch's stock defaults.

## Layout

```
scripts/     pipeline scripts (see above)
data/        MusicNet ground-truth label CSVs + sample audio/output for evaluation
archive/     raw MusicNet download (audio, labels, MIDI, metadata)
```

## Status

Early-stage. The transcribe → Braille path works end-to-end on sample audio; transpose and describe are not yet implemented.
