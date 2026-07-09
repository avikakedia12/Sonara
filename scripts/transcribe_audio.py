#!/usr/bin/env python3
"""Transcribe an audio recording into sheet music using a pretrained model.

Uses Spotify's basic-pitch (pretrained polyphonic transcription model) to go
from audio -> note events, then music21 to go from notes -> notated Score /
MusicXML. No training involved: this is the "use a pretrained model" path for
Stage 1 of the pipeline (audio -> sheet music).

basic-pitch's raw note timings are in seconds and don't land on musical beats,
which is fine for playback (MIDI) but not for notation: without quantization,
downstream steps like the Braille converter fail on non-standard durations.
--quantize detects the beat grid with librosa (tempo + beat times) and snaps
each note's start/duration onto that grid, in beat-fraction subdivisions.

basic-pitch's onset/frame detection thresholds have a real, measured, and
*material-dependent* effect on accuracy (verified against MusicNet ground
truth in evaluate_transcription.py): raising them above the stock defaults
(0.5/0.3 -> 0.65/0.25) took F-measure on a dense 5-instrument piano quintet
from 0.220 to 0.291, but *hurt* a solo piano piece (0.478 -> 0.441). There's
no single best default. By default this script auto-selects: it probes with
stock thresholds, estimates average polyphony (simultaneous notes per onset)
from the result, and only switches to the stricter thresholds if the material
looks dense. Pass --onset-threshold/--frame-threshold to override and skip
the probe.
"""
import argparse
from pathlib import Path

import librosa
import numpy as np
from music21 import converter, metadata as m21metadata, meter, pitch as m21pitch, stream, tempo as m21tempo

from notation_utils import insert_with_ties, predict_notes_adaptive


def estimate_beat_times(audio_path: Path) -> tuple[float, np.ndarray]:
    y, sr = librosa.load(str(audio_path), sr=None, mono=True)
    tempo_bpm, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    if len(beat_times) < 2:
        # No reliable beat detected (e.g. a single sustained tone) -- fall
        # back to a flat grid so quantization still has a scale to work with.
        duration = len(y) / sr
        beat_times = np.arange(0, max(duration, 1.0), 60.0 / 120.0)
        tempo_bpm = 120.0
    return float(np.asarray(tempo_bpm).item()), beat_times


def time_to_beat(t: float, beat_times: np.ndarray) -> float:
    """Map an absolute time (seconds) to a continuous beat position, extrapolating
    past the first/last detected beat using the local beat interval there."""
    if t <= beat_times[0]:
        step = beat_times[1] - beat_times[0]
        return (t - beat_times[0]) / step
    if t >= beat_times[-1]:
        step = beat_times[-1] - beat_times[-2]
        return (len(beat_times) - 1) + (t - beat_times[-1]) / step
    return float(np.interp(t, beat_times, np.arange(len(beat_times))))


def quantize_to_score(midi_data, beat_times: np.ndarray, tempo_bpm: float, subdivisions: int) -> stream.Score:
    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    part.insert(0, m21tempo.MetronomeMark(number=round(tempo_bpm)))

    for instrument in midi_data.instruments:
        for note in sorted(instrument.notes, key=lambda n: n.start):
            start_beat = time_to_beat(note.start, beat_times)
            end_beat = time_to_beat(note.end, beat_times)

            quantized_offset = round(start_beat * subdivisions) / subdivisions
            quantized_length = round((end_beat - start_beat) * subdivisions) / subdivisions
            quantized_length = max(quantized_length, 1.0 / subdivisions)

            insert_with_ties(part, quantized_offset, quantized_length, m21pitch.Pitch(midi=note.pitch))

    part.makeNotation(inPlace=True)
    score = stream.Score()
    score.insert(0, part)
    return score


def transcribe(
    audio_path: Path,
    out_dir: Path,
    title: str | None = None,
    quantize: int | None = None,
    onset_threshold: float | None = None,
    frame_threshold: float | None = None,
) -> dict:
    """Returns a dict: {"path": Path to written MusicXML, "polyphony": float | None,
    "thresholds_used": dict | None, "tempo_bpm": float | None} -- metadata is
    None where it wasn't computed (e.g. thresholds_used when fixed thresholds
    were passed in rather than adaptively selected)."""
    out_dir.mkdir(parents=True, exist_ok=True)

    polyphony = thresholds_used = tempo_bpm = None

    if onset_threshold is None and frame_threshold is None:
        _, polyphony, midi_data, thresholds_used = predict_notes_adaptive(audio_path)
        print(f"Estimated polyphony: {polyphony:.2f} simultaneous notes/onset -> thresholds {thresholds_used}")
    else:
        from basic_pitch.inference import predict
        from basic_pitch import ICASSP_2022_MODEL_PATH

        _, midi_data, _ = predict(
            str(audio_path),
            model_or_model_path=ICASSP_2022_MODEL_PATH,
            onset_threshold=onset_threshold if onset_threshold is not None else 0.5,
            frame_threshold=frame_threshold if frame_threshold is not None else 0.3,
        )

    if quantize:
        tempo_bpm, beat_times = estimate_beat_times(audio_path)
        print(f"Detected tempo: {tempo_bpm:.1f} BPM, {len(beat_times)} beats")
        score = quantize_to_score(midi_data, beat_times, tempo_bpm, quantize)
    else:
        midi_path = out_dir / f"{audio_path.stem}.mid"
        midi_data.write(str(midi_path))
        score = converter.parse(str(midi_path))

    score.metadata = m21metadata.Metadata()
    score.metadata.title = title or audio_path.stem

    musicxml_path = out_dir / f"{audio_path.stem}.musicxml"
    score.write("musicxml", fp=str(musicxml_path))

    return {
        "path": musicxml_path,
        "polyphony": polyphony,
        "thresholds_used": thresholds_used,
        "tempo_bpm": tempo_bpm,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", type=Path, help="Path to input audio file (wav/mp3/etc.)")
    parser.add_argument(
        "--out-dir", type=Path, default=Path("data/transcribed"), help="Output directory"
    )
    parser.add_argument("--title", default=None, help="Score title (defaults to filename)")
    parser.add_argument(
        "--quantize",
        type=int,
        default=None,
        metavar="SUBDIVISIONS",
        help="Snap notes to a detected beat grid, e.g. 4 = sixteenth-note grid (omit for raw unquantized timing)",
    )
    parser.add_argument(
        "--onset-threshold", type=float, default=None,
        help="Fix a specific basic-pitch onset threshold instead of auto-selecting from estimated polyphony",
    )
    parser.add_argument(
        "--frame-threshold", type=float, default=None,
        help="Fix a specific basic-pitch frame threshold instead of auto-selecting from estimated polyphony",
    )
    args = parser.parse_args()

    result = transcribe(
        args.audio, args.out_dir, args.title, args.quantize, args.onset_threshold, args.frame_threshold
    )
    print(f"Wrote {result['path']}")


if __name__ == "__main__":
    main()
