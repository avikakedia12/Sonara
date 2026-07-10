import sys
import types

import pytest
from music21 import dynamics, key as m21key, meter, metadata, note, stream, tempo as m21tempo

from describe_score import (
    build_description,
    estimate_duration_seconds,
    format_duration,
    get_ambitus,
    get_dynamics,
    get_key,
    get_measure_count,
    get_tempos,
    get_time_signatures,
    get_title_composer,
    speak_description,
)


def _scored_part(pitches, quarter_length=1.0):
    part = stream.Part()
    for p in pitches:
        part.append(note.Note(p, quarterLength=quarter_length))
    return part


@pytest.fixture
def synthetic_score():
    s = stream.Score()
    s.metadata = metadata.Metadata()
    s.metadata.title = "Test Piece"
    s.metadata.composer = "Ada Lovelace"

    part = stream.Part()
    part.insert(0, meter.TimeSignature("3/4"))
    part.insert(0, m21tempo.MetronomeMark(number=90))
    part.insert(0, dynamics.Dynamic("p"))
    part.append(note.Note("C4", quarterLength=1))
    part.append(note.Note("D4", quarterLength=1))
    part.append(note.Note("E4", quarterLength=1))
    part.insert(12, meter.TimeSignature("4/4"))
    part.insert(12, m21tempo.MetronomeMark(number=140))
    part.insert(12, dynamics.Dynamic("ff"))
    part.append(note.Note("G5", quarterLength=1))
    part.makeMeasures(inPlace=True)
    s.insert(0, part)
    return s


def test_get_title_composer(synthetic_score):
    assert get_title_composer(synthetic_score) == ("Test Piece", "Ada Lovelace")


def test_get_title_composer_missing_metadata():
    s = stream.Score()
    assert get_title_composer(s) == (None, None)


def test_get_key_explicit():
    s = stream.Score()
    part = stream.Part()
    part.insert(0, m21key.Key("B-", "major"))
    part.append(note.Note("B-4"))
    s.insert(0, part)
    key_str, estimated = get_key(s)
    assert key_str == "B- major"
    assert estimated is False


def test_get_key_falls_back_to_estimation():
    s = stream.Score()
    part = _scored_part(["C4", "E4", "G4", "C5", "G4", "E4", "C4"])
    s.insert(0, part)
    key_str, estimated = get_key(s)
    assert estimated is True
    assert "major" in key_str or "minor" in key_str


def test_get_time_signatures_dedupes_consecutive_identical(synthetic_score):
    sigs = get_time_signatures(synthetic_score)
    assert [s for _, s in sigs] == ["3/4", "4/4"]


def test_get_tempos_dedupes_consecutive_identical(synthetic_score):
    tempos = get_tempos(synthetic_score)
    assert [round(bpm) for _, bpm in tempos] == [90, 140]


def test_get_measure_count(synthetic_score):
    assert get_measure_count(synthetic_score) == 5


def test_get_measure_count_no_measures():
    s = stream.Score()
    s.insert(0, stream.Part())
    assert get_measure_count(s) is None


def test_estimate_duration_seconds_uses_first_tempo():
    s = stream.Score()
    part = _scored_part(["C4"] * 4, quarter_length=1.0)  # 4 quarter notes
    s.insert(0, part)
    tempos = [(1, 120.0)]
    # 4 quarter notes at 120bpm = 2 seconds
    assert estimate_duration_seconds(s, tempos) == pytest.approx(2.0)


def test_estimate_duration_seconds_defaults_to_120bpm_with_no_tempo():
    s = stream.Score()
    part = _scored_part(["C4"] * 4, quarter_length=1.0)
    s.insert(0, part)
    assert estimate_duration_seconds(s, []) == pytest.approx(2.0)


def test_format_duration():
    assert format_duration(0) == "0:00"
    assert format_duration(65) == "1:05"
    assert format_duration(184) == "3:04"


def test_get_ambitus():
    part = _scored_part(["C4", "G5", "A2", "D4"])
    assert get_ambitus(part) == ("A2", "G5")


def test_get_ambitus_no_notes():
    assert get_ambitus(stream.Part()) is None


def test_get_dynamics(synthetic_score):
    part = synthetic_score.parts[0]
    dyn = get_dynamics(part)
    assert [v for _, v in dyn] == ["p", "ff"]


def test_build_description_brief_level(synthetic_score):
    text = build_description(synthetic_score, "brief")
    assert "Test Piece by Ada Lovelace" in text
    assert "Key:" in text
    assert "time signature 3/4" in text
    assert "tempo marking 90 BPM" in text
    assert "5 measures" in text
    # brief must not include per-part range/dynamics detail
    assert "range" not in text
    assert "dynamics used" not in text


def test_build_description_standard_level_adds_range_and_dynamics(synthetic_score):
    text = build_description(synthetic_score, "standard")
    assert "range C4 to G5" in text
    assert "dynamics used: ff, p" in text
    assert "2 time signature changes" in text
    assert "2 tempo changes" in text
    # standard must not include the full measure-by-measure change log
    assert "Time signature changes --" not in text


def test_build_description_detailed_level_adds_change_log(synthetic_score):
    text = build_description(synthetic_score, "detailed")
    assert "Time signature changes -- measure 1: 3/4, measure 5: 4/4." in text
    assert "Tempo changes -- measure 1: 90 BPM, measure 5: 140 BPM." in text
    assert "dynamic markings -- measure 1: p, measure 5: ff." in text


def test_build_description_untitled_piece_with_no_metadata():
    s = stream.Score()
    part = _scored_part(["C4"])
    s.insert(0, part)
    text = build_description(s, "brief")
    assert text.startswith("Untitled piece.")


def test_speak_description_uses_pyttsx3(tmp_path, monkeypatch):
    calls = {}

    class FakeEngine:
        def save_to_file(self, text, path):
            calls["save"] = (text, path)

        def runAndWait(self):
            calls["ran"] = True

    fake_module = types.SimpleNamespace(init=lambda: FakeEngine())
    monkeypatch.setitem(sys.modules, "pyttsx3", fake_module)

    out_path = tmp_path / "out.aiff"
    result = speak_description("hello world", out_path)

    assert result == out_path
    assert calls["save"] == ("hello world", str(out_path))
    assert calls["ran"] is True


def test_speak_description_missing_pyttsx3_raises_actionable_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "pyttsx3", None)  # forces ImportError on `import pyttsx3`
    with pytest.raises(RuntimeError, match="pyttsx3"):
        speak_description("hi", "unused")
