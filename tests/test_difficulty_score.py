from music21 import chord, duration, key as m21key, meter, note, stream, tempo as m21tempo

from difficulty_score import (
    build_difficulty_report,
    get_chord_density_score,
    get_interval_leap_score,
    get_key_complexity_score,
    get_pitch_range_score,
    get_rhythm_score,
    get_tempo_density_score,
    get_time_signature_score,
    level_for_score,
)


def _part(pitches, quarter_length=1.0):
    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    for p in pitches:
        part.append(note.Note(p, quarterLength=quarter_length))
    part.makeMeasures(inPlace=True)
    return part


def test_level_for_score_bands():
    assert level_for_score(0.0) == "Beginner"
    assert level_for_score(1.9) == "Beginner"
    assert level_for_score(2.0) == "Easy"
    assert level_for_score(4.0) == "Intermediate"
    assert level_for_score(6.0) == "Advanced"
    assert level_for_score(9.9) == "Virtuosic"


def test_rhythm_score_scales_with_note_speed():
    slow_score, _ = get_rhythm_score(_part(["C4"] * 8, quarter_length=1.0))
    fast_score, detail = get_rhythm_score(_part(["C4"] * 8, quarter_length=0.125))
    assert fast_score > slow_score
    assert "32nd note" in detail


def test_rhythm_score_no_notes_is_zero():
    score, detail = get_rhythm_score(stream.Part())
    assert score == 0.0
    assert "no notes" in detail


def test_rhythm_score_tuplets_add_difficulty():
    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    for _ in range(6):
        n = note.Note("C4")
        n.duration = duration.Duration(1 / 3)
        part.append(n)
    part.makeMeasures(inPlace=True)
    score, detail = get_rhythm_score(part)
    assert "tuplet" in detail


def test_pitch_range_score_widens_with_span():
    narrow, _ = get_pitch_range_score(_part(["C4", "D4"]))
    wide, detail = get_pitch_range_score(_part(["C2", "C7"]))
    assert wide > narrow
    assert "C2 to C7" in detail


def test_pitch_range_score_no_notes():
    score, detail = get_pitch_range_score(stream.Part())
    assert score == 0.0
    assert "no pitched notes" in detail


def test_interval_leap_score_leaps_score_higher_than_steps():
    stepwise, _ = get_interval_leap_score(_part(["C4", "D4", "E4", "F4"]))
    leapy, detail = get_interval_leap_score(_part(["C2", "C6", "C2", "C6"]))
    assert leapy > stepwise
    assert "octave" in detail


def test_interval_leap_score_single_note():
    score, detail = get_interval_leap_score(_part(["C4"]))
    assert score == 0.0
    assert "not enough notes" in detail


def test_chord_density_score_monophonic_is_zero():
    score, detail = get_chord_density_score(_part(["C4", "D4"]))
    assert score == 0.0
    assert "monophonic" in detail


def test_chord_density_score_reflects_chord_size():
    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    for _ in range(4):
        part.append(chord.Chord(["C4", "E4", "G4", "C5"], quarterLength=1.0))
    part.makeMeasures(inPlace=True)
    score, detail = get_chord_density_score(part)
    assert score > 0
    assert "100%" in detail
    assert "4.0 notes per chord" in detail


def test_tempo_density_score_faster_bpm_scores_higher():
    part = _part(["C4"] * 8, quarter_length=1.0)
    slow, _ = get_tempo_density_score(part, bpm=60.0)
    fast, detail = get_tempo_density_score(part, bpm=240.0)
    assert fast > slow
    assert "240" in detail


def test_key_complexity_score_more_accidentals_scores_higher():
    s_simple = stream.Score()
    p_simple = stream.Part()
    p_simple.insert(0, m21key.Key("C", "major"))
    p_simple.append(note.Note("C4"))
    s_simple.insert(0, p_simple)

    s_complex = stream.Score()
    p_complex = stream.Part()
    p_complex.insert(0, m21key.Key("F#", "major"))
    p_complex.append(note.Note("F#4"))
    s_complex.insert(0, p_complex)

    simple_score, simple_detail = get_key_complexity_score(s_simple)
    complex_score, complex_detail = get_key_complexity_score(s_complex)
    assert complex_score > simple_score
    assert "0 accidental" in simple_detail
    assert "6 accidental" in complex_detail


def test_time_signature_score_irregular_meter_scores_higher():
    s_simple = stream.Score()
    p_simple = stream.Part()
    p_simple.insert(0, meter.TimeSignature("4/4"))
    p_simple.append(note.Note("C4"))
    s_simple.insert(0, p_simple)

    s_irregular = stream.Score()
    p_irregular = stream.Part()
    p_irregular.insert(0, meter.TimeSignature("7/8"))
    p_irregular.append(note.Note("C4"))
    s_irregular.insert(0, p_irregular)

    simple_score, _ = get_time_signature_score(s_simple)
    irregular_score, detail = get_time_signature_score(s_irregular)
    assert irregular_score > simple_score
    assert "7/8" in detail


def test_time_signature_score_no_time_signature():
    s = stream.Score()
    s.insert(0, stream.Part())
    score, detail = get_time_signature_score(s)
    assert score == 0.0
    assert "no time signature" in detail


def test_build_difficulty_report_easy_scale():
    s = stream.Score()
    part = _part(["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"], quarter_length=1.0)
    s.insert(0, part)
    report = build_difficulty_report(s)
    assert report["overall_level"] in ("Beginner", "Easy")
    assert report["hardest_part"] is None  # only one part -- no need to call out which
    assert "Estimated difficulty" in report["summary"]
    assert len(report["per_part"]) == 1
    assert set(report["per_part"][0]["factors"]) == {
        "rhythm", "interval_leaps", "chord_density", "tempo_density", "pitch_range",
        "key_complexity", "time_signature",
    }


def test_build_difficulty_report_multi_part_names_hardest():
    s = stream.Score()
    easy = _part(["C4", "D4", "E4", "F4"], quarter_length=1.0)
    hard = stream.Part()
    hard.insert(0, meter.TimeSignature("4/4"))
    hard.insert(0, m21tempo.MetronomeMark(number=200))
    for p in ("C2", "C6", "E2", "G6"):
        hard.append(note.Note(p, quarterLength=0.125))
    hard.makeMeasures(inPlace=True)
    s.insert(0, easy)
    s.insert(0, hard)

    report = build_difficulty_report(s)
    assert report["hardest_part"] is not None
    hardest_report = next(p for p in report["per_part"] if p["name"] == report["hardest_part"])
    assert report["overall_score"] == hardest_report["score"]
    assert report["overall_score"] == max(p["score"] for p in report["per_part"])
