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

Default onset/frame thresholds are tuned above basic-pitch's stock defaults
(onset 0.5->0.65, frame 0.3->0.25). On a dense multi-instrument recording
(MusicNet #1727, a Schubert piano quintet), this raised note transcription
F-measure from 0.220 to 0.291 against MusicNet's ground truth -- mostly by
cutting spurious note detections (precision 0.197 -> 0.316) with recall
roughly unchanged. See evaluate_transcription.py. Override with
--onset-threshold/--frame-threshold if working with sparser material (e.g.
solo instrument), where the stock defaults may do better.
"""
import argparse
from pathlib import Path

import librosa
import numpy as np
from music21 import converter, metadata as m21metadata, meter, pitch as m21pitch, stream, tempo as m21tempo

from notation_utils import insert_with_ties


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
    onset_threshold: float = 0.65,
    frame_threshold: float = 0.25,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)

    from basic_pitch.inference import predict
    from basic_pitch import ICASSP_2022_MODEL_PATH

    _, midi_data, _ = predict(
        str(audio_path),
        model_or_model_path=ICASSP_2022_MODEL_PATH,
        onset_threshold=onset_threshold,
        frame_threshold=frame_threshold,
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

    return musicxml_path


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
        "--onset-threshold", type=float, default=0.65,
        help="basic-pitch onset detection threshold (default tuned for dense/multi-instrument audio; stock default is 0.5)",
    )
    parser.add_argument(
        "--frame-threshold", type=float, default=0.25,
        help="basic-pitch frame detection threshold (default tuned for dense/multi-instrument audio; stock default is 0.3)",
    )
    args = parser.parse_args()

    musicxml_path = transcribe(
        args.audio, args.out_dir, args.title, args.quantize, args.onset_threshold, args.frame_threshold
    )
    print(f"Wrote {musicxml_path}")


if __name__ == "__main__":
    main()
