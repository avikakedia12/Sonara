import csv

import pytest
from music21 import instrument as m21instrument

from build_score import build_score, find_label_file, load_metadata_title

CSV_HEADER = ["start_time", "end_time", "instrument", "note", "start_beat", "end_beat", "note_value"]


def _write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        writer.writerows(rows)


def test_build_score_creates_one_part_per_instrument(tmp_path):
    csv_path = tmp_path / "1234.csv"
    _write_csv(csv_path, [
        # start_time, end_time (unused, audio-domain), instrument, note (MIDI pitch), start_beat, end_beat (duration), note_value
        [0, 0, 41, 60, 0.0, 1.0, "Quarter"],  # violin, MIDI 60 = C4, at beat 0
        [0, 0, 41, 62, 1.0, 1.0, "Quarter"],  # violin, MIDI 62 = D4, at beat 1
        [0, 0, 1, 67, 0.0, 2.0, "Half"],      # piano, MIDI 67 = G4, at beat 0
    ])

    score = build_score(csv_path, "Test Title")
    assert score.metadata.title == "Test Title"
    assert len(score.parts) == 2

    parts_by_instrument = {}
    for part in score.parts:
        instr = part.getInstrument(returnDefault=False)
        parts_by_instrument[type(instr)] = part

    assert m21instrument.Violin in parts_by_instrument
    assert m21instrument.Piano in parts_by_instrument

    violin_notes = sorted(parts_by_instrument[m21instrument.Violin].recurse().notes, key=lambda n: n.offset)
    assert [n.pitch.midi for n in violin_notes] == [60, 62]
    assert [n.offset for n in violin_notes] == [0.0, 1.0]

    piano_notes = list(parts_by_instrument[m21instrument.Piano].recurse().notes)
    assert piano_notes[0].pitch.midi == 67
    assert piano_notes[0].duration.quarterLength == 2.0


def test_build_score_unknown_instrument_code_gets_generic_instrument(tmp_path):
    csv_path = tmp_path / "1234.csv"
    _write_csv(csv_path, [[0, 0, 999, 60, 0.0, 1.0, "Quarter"]])
    score = build_score(csv_path, "Test")
    assert len(score.parts) == 1


def test_build_score_zero_duration_is_floored(tmp_path):
    # end_beat is the note's duration despite the confusing MusicNet column
    # name -- a 0-length note should still get a minimal playable duration.
    csv_path = tmp_path / "1234.csv"
    _write_csv(csv_path, [[0, 0, 1, 60, 0.0, 0.0, "Sixteenth"]])
    score = build_score(csv_path, "Test")
    note_ = next(score.parts[0].recurse().notes)
    assert note_.duration.quarterLength == pytest.approx(0.0625)


def test_find_label_file_direct(tmp_path):
    (tmp_path / "1727.csv").touch()
    assert find_label_file(tmp_path, "1727") == tmp_path / "1727.csv"


def test_find_label_file_train_labels_subdir(tmp_path):
    (tmp_path / "train_labels").mkdir()
    (tmp_path / "train_labels" / "1727.csv").touch()
    assert find_label_file(tmp_path, "1727") == tmp_path / "train_labels" / "1727.csv"


def test_find_label_file_not_found_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        find_label_file(tmp_path, "9999")


def test_load_metadata_title_found(tmp_path):
    meta_path = tmp_path / "metadata.csv"
    with meta_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "composer", "composition", "movement"])
        writer.writerow(["1727", "Bach", "Cello Suite", "Prelude"])
    assert load_metadata_title(meta_path, "1727") == "Bach - Cello Suite (Prelude)"


def test_load_metadata_title_missing_id_falls_back(tmp_path):
    meta_path = tmp_path / "metadata.csv"
    with meta_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "composer", "composition", "movement"])
        writer.writerow(["1", "Someone", "Something", "I"])
    assert load_metadata_title(meta_path, "1727") == "MusicNet #1727"


def test_load_metadata_title_missing_file_falls_back(tmp_path):
    assert load_metadata_title(tmp_path / "nope.csv", "1727") == "MusicNet #1727"


def test_load_metadata_title_none_path_falls_back():
    assert load_metadata_title(None, "1727") == "MusicNet #1727"
