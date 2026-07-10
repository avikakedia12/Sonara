import csv

import pytest

from evaluate_transcription import (
    cluster_by_time,
    implied_tempo_bpm,
    load_ground_truth_notes,
    match_notes,
    standard_f_measure,
)

CSV_HEADER = ["start_time", "end_time", "instrument", "note", "start_beat", "end_beat", "note_value"]


def _write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        writer.writerows(rows)


def test_match_notes_exact_pitch_match():
    ref = [{"start": 0.0, "end": 1.0, "pitch": 60}]
    est = [{"start": 0.0, "end": 1.0, "pitch": 60}]
    pitch_matches, octave_matches, missing, extra = match_notes(ref, est)
    assert pitch_matches == [(0, 0)]
    assert octave_matches == []
    assert missing == []
    assert extra == []


def test_match_notes_octave_error():
    ref = [{"start": 0.0, "end": 1.0, "pitch": 60}]
    est = [{"start": 0.0, "end": 1.0, "pitch": 72}]  # same pitch class, +1 octave
    pitch_matches, octave_matches, missing, extra = match_notes(ref, est)
    assert pitch_matches == []
    assert octave_matches == [(0, 0)]


def test_match_notes_missing_and_extra():
    ref = [{"start": 0.0, "end": 1.0, "pitch": 60}]
    est = [{"start": 5.0, "end": 6.0, "pitch": 67}]  # too far away to match
    pitch_matches, octave_matches, missing, extra = match_notes(ref, est)
    assert pitch_matches == []
    assert octave_matches == []
    assert missing == ref
    assert extra == est


def test_match_notes_respects_onset_tolerance():
    ref = [{"start": 0.0, "end": 1.0, "pitch": 60}]
    est = [{"start": 0.5, "end": 1.5, "pitch": 60}]
    # default onset_tolerance=0.1, dt=0.5 -> no match
    pitch_matches, _, missing, extra = match_notes(ref, est)
    assert pitch_matches == []
    assert missing == ref
    assert extra == est

    # widen tolerance -> matches
    pitch_matches, _, missing, extra = match_notes(ref, est, onset_tolerance=0.6)
    assert pitch_matches == [(0, 0)]
    assert missing == []
    assert extra == []


def test_cluster_by_time_groups_close_events():
    items = [{"start": 0.0}, {"start": 0.2}, {"start": 0.4}, {"start": 5.0}]
    clusters = cluster_by_time(items, gap=0.5)
    assert len(clusters) == 2
    assert len(clusters[0]) == 3
    assert len(clusters[1]) == 1


def test_cluster_by_time_empty():
    assert cluster_by_time([]) == []


def test_standard_f_measure_perfect_match():
    notes = [{"start": 0.0, "end": 1.0, "pitch": 60}, {"start": 1.0, "end": 2.0, "pitch": 64}]
    scores = standard_f_measure(notes, notes)
    assert scores["precision"] == pytest.approx(1.0)
    assert scores["recall"] == pytest.approx(1.0)
    assert scores["f_measure"] == pytest.approx(1.0)


def test_standard_f_measure_no_overlap():
    ref = [{"start": 0.0, "end": 1.0, "pitch": 60}]
    est = [{"start": 10.0, "end": 11.0, "pitch": 72}]
    scores = standard_f_measure(ref, est)
    assert scores["f_measure"] == pytest.approx(0.0)


def test_load_ground_truth_notes_converts_samples_to_seconds(tmp_path):
    csv_path = tmp_path / "gt.csv"
    # 44100 samples = 1.0 second
    _write_csv(csv_path, [[44100, 88200, 41, 60, 0.0, 1.0, "Quarter"]])
    notes = load_ground_truth_notes(csv_path, max_seconds=None)
    assert len(notes) == 1
    assert notes[0]["start"] == pytest.approx(1.0)
    assert notes[0]["end"] == pytest.approx(2.0)
    assert notes[0]["pitch"] == 60


def test_load_ground_truth_notes_respects_max_seconds(tmp_path):
    csv_path = tmp_path / "gt.csv"
    _write_csv(csv_path, [
        [0, 44100, 41, 60, 0.0, 1.0, "Quarter"],        # start at t=0
        [44100 * 10, 44100 * 11, 41, 62, 10.0, 1.0, "Quarter"],  # start at t=10
    ])
    notes = load_ground_truth_notes(csv_path, max_seconds=5.0)
    assert len(notes) == 1
    assert notes[0]["pitch"] == 60


def test_implied_tempo_bpm(tmp_path):
    csv_path = tmp_path / "gt.csv"
    _write_csv(csv_path, [
        [0, 0, 1, 60, 0.0, 1.0, "Quarter"],
        [44100, 0, 1, 62, 2.0, 1.0, "Quarter"],  # 1 second later, 2 beats later -> 120bpm
        [44100 * 2, 0, 1, 64, 4.0, 1.0, "Quarter"],
    ])
    bpm = implied_tempo_bpm(csv_path, max_seconds=None)
    assert bpm == pytest.approx(120.0)


def test_implied_tempo_bpm_insufficient_data(tmp_path):
    csv_path = tmp_path / "gt.csv"
    _write_csv(csv_path, [[0, 0, 1, 60, 0.0, 1.0, "Quarter"]])
    assert implied_tempo_bpm(csv_path, max_seconds=None) is None
