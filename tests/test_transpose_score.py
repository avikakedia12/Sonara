from music21 import note, stream

from transpose_score import INSTRUMENT_REGISTRY, transpose_for_instrument


def _single_note_part(pitch_name: str) -> stream.Part:
    part = stream.Part()
    part.append(note.Note(pitch_name, quarterLength=1.0))
    return part


def test_all_registry_instruments_have_valid_low_high_range():
    for name, (cls, low, high) in INSTRUMENT_REGISTRY.items():
        from music21 import pitch as m21pitch
        assert m21pitch.Pitch(low).ps < m21pitch.Pitch(high).ps, f"{name}: low >= high"


def test_bflat_clarinet_transposes_up_a_major_second():
    # Bb clarinet sounds a major 2nd below written pitch, so a concert C4
    # should be written as D4.
    part = _single_note_part("C4")
    written, out_of_range = transpose_for_instrument(part, "clarinet")

    notes = list(written.recurse().notes)
    assert len(notes) == 1
    assert notes[0].pitch.nameWithOctave == "D4"
    assert out_of_range == []


def test_non_transposing_instrument_keeps_pitch():
    # Piano is a non-transposing instrument -- concert and written pitch match.
    part = _single_note_part("C4")
    written, out_of_range = transpose_for_instrument(part, "piano")

    notes = list(written.recurse().notes)
    assert notes[0].pitch.nameWithOctave == "C4"
    assert out_of_range == []


def test_out_of_range_note_flagged_but_not_altered():
    # Concert C2 -> written D2 for Bb clarinet, below its E3 low end.
    part = _single_note_part("C2")
    written, out_of_range = transpose_for_instrument(part, "clarinet")

    notes = list(written.recurse().notes)
    assert notes[0].pitch.nameWithOctave == "D2"  # not silently octave-shifted
    assert len(out_of_range) == 1
    assert out_of_range[0]["pitch"] == "D2"
    assert out_of_range[0]["direction"] == "below"


def test_out_of_range_above():
    # Concert C7 -> written D7 for Bb clarinet, above its C7 high end.
    part = _single_note_part("C7")
    written, out_of_range = transpose_for_instrument(part, "clarinet")

    assert len(out_of_range) == 1
    assert out_of_range[0]["direction"] == "above"


def test_in_range_note_produces_no_violations():
    part = _single_note_part("C4")
    _, out_of_range = transpose_for_instrument(part, "violin")
    assert out_of_range == []


def test_chord_notes_are_individually_range_checked():
    part = stream.Part()
    from music21 import chord as m21chord
    # Concert C2+C4 chord -> written D2+D4 for clarinet; only D2 is out of range.
    part.append(m21chord.Chord(["C2", "C4"], quarterLength=1.0))
    _, out_of_range = transpose_for_instrument(part, "clarinet")
    assert len(out_of_range) == 1
    assert out_of_range[0]["pitch"] == "D2"
