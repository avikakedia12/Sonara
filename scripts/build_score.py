#!/usr/bin/env python3
"""Convert a MusicNet label CSV into a music21 Score and export MusicXML.

MusicNet label CSV columns: start_time,end_time,instrument,note,start_beat,end_beat,note_value
- start_time/end_time: sample index at 44.1kHz (audio-domain, not used here)
- instrument: MusicNet's instrument code (see INSTRUMENT_MAP)
- note: MIDI pitch number
- start_beat: cumulative beat offset from the start of the piece (notation-domain)
- end_beat: despite the name, this is the note's *duration* in beats, not an
  end position -- e.g. a note can have start_beat=178.5, end_beat=0.875. It's
  a more precise numeric duration than note_value (which is a coarse label
  that doesn't always match a fixed table, e.g. "Whole" notes in this dataset
  aren't always exactly 4.0 beats).
- note_value: duration name, e.g. "Quarter", "Dotted Half", "Eighth" (informational)

We build notation directly from start_beat (offset) and end_beat (duration)
rather than the audio sample times, since that's the metrical information
sheet music needs.
"""
import argparse
import csv
from pathlib import Path

from music21 import stream, note as m21note, instrument as m21instrument, metadata as m21metadata

INSTRUMENT_MAP = {
    1: m21instrument.Piano,
    7: m21instrument.Harpsichord,
    41: m21instrument.Violin,
    42: m21instrument.Viola,
    43: m21instrument.Violoncello,
    44: m21instrument.Contrabass,
    61: m21instrument.Horn,
    69: m21instrument.Oboe,
    71: m21instrument.Bassoon,
    72: m21instrument.Clarinet,
    74: m21instrument.Flute,
}

def find_label_file(data_dir: Path, note_id: str) -> Path:
    candidates = [
        data_dir / f"{note_id}.csv",
        data_dir / "train_labels" / f"{note_id}.csv",
        data_dir / "test_labels" / f"{note_id}.csv",
        data_dir / "musicnet" / "musicnet" / "train_labels" / f"{note_id}.csv",
        data_dir / "musicnet" / "musicnet" / "test_labels" / f"{note_id}.csv",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError(
        f"Could not find label CSV for id {note_id} under {data_dir} "
        f"(looked in: {[str(c) for c in candidates]})"
    )


def load_metadata_title(metadata_csv: Path, note_id: str) -> str:
    if not metadata_csv or not metadata_csv.exists():
        return f"MusicNet #{note_id}"
    with metadata_csv.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["id"] == str(note_id):
                return f'{row["composer"]} - {row["composition"]} ({row["movement"]})'
    return f"MusicNet #{note_id}"


def build_score(label_csv: Path, title: str) -> stream.Score:
    score = stream.Score()
    score.metadata = m21metadata.Metadata()
    score.metadata.title = title

    parts_by_instrument: dict[int, stream.Part] = {}

    with label_csv.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        instrument_code = int(row["instrument"])
        midi_pitch = int(row["note"])
        start_beat = float(row["start_beat"])
        quarter_length = max(float(row["end_beat"]), 0.0625)

        if instrument_code not in parts_by_instrument:
            part = stream.Part()
            instrument_cls = INSTRUMENT_MAP.get(instrument_code)
            part.insert(0, instrument_cls() if instrument_cls else m21instrument.Instrument())
            parts_by_instrument[instrument_code] = part
            score.insert(0, part)

        n = m21note.Note(midi_pitch, quarterLength=quarter_length)
        parts_by_instrument[instrument_code].insert(start_beat, n)

    for part in parts_by_instrument.values():
        part.makeVoices(inPlace=True, fillGaps=False)

    return score


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--id", required=True, help="MusicNet recording id, e.g. 1759")
    parser.add_argument(
        "--data-dir",
        required=True,
        type=Path,
        help="Directory containing the label CSV (or the musicnet/musicnet root)",
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=None,
        help="Path to musicnet_metadata.csv (optional, used for the score title)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output MusicXML path (defaults to <id>.musicxml next to the label CSV)",
    )
    args = parser.parse_args()

    label_csv = find_label_file(args.data_dir, args.id)
    title = load_metadata_title(args.metadata, args.id)
    score = build_score(label_csv, title)

    out_path = args.out or label_csv.with_name(f"{args.id}.musicxml")
    score.write("musicxml", fp=str(out_path))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
