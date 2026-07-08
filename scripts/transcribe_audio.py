#!/usr/bin/env python3
"""Transcribe an audio recording into sheet music using a pretrained model.

Uses Spotify's basic-pitch (pretrained polyphonic transcription model) to go
from audio -> MIDI, then music21 to go from MIDI -> notated Score / MusicXML.

No training involved: this is the "use a pretrained model" path for Stage 1
of the pipeline (audio -> sheet music).
"""
import argparse
from pathlib import Path

from basic_pitch.inference import predict
from basic_pitch import ICASSP_2022_MODEL_PATH
from music21 import converter, metadata as m21metadata


def transcribe(audio_path: Path, out_dir: Path, title: str | None = None) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)

    _, midi_data, _ = predict(str(audio_path), model_or_model_path=ICASSP_2022_MODEL_PATH)

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
    args = parser.parse_args()

    musicxml_path = transcribe(args.audio, args.out_dir, args.title)
    print(f"Wrote {musicxml_path}")


if __name__ == "__main__":
    main()
