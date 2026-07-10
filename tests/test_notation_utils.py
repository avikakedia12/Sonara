from music21 import chord as m21chord, note as m21note, stream

from notation_utils import average_polyphony, insert_with_ties, skyline_melody, unicode_braille_to_brf


def test_average_polyphony_empty():
    assert average_polyphony([]) == 0.0


def test_average_polyphony_no_overlap():
    notes = [{"start": 0.0, "end": 1.0}, {"start": 1.0, "end": 2.0}]
    assert average_polyphony(notes) == 1.0


def test_average_polyphony_with_overlap():
    # Two notes sound together at t=0, a third starts alone at t=1 ->
    # (2 + 2 + 1) / 3 simultaneous notes per onset.
    notes = [{"start": 0.0, "end": 1.0}, {"start": 0.0, "end": 1.0}, {"start": 1.0, "end": 2.0}]
    assert average_polyphony(notes) == 5 / 3


def test_unicode_braille_to_brf_known_cells():
    # U+2801 = dot 1 only -> 'A'; U+2800 = no dots -> ' '; U+283F = all 6 dots -> '='
    assert unicode_braille_to_brf("⠁⠀⠿") == "A ="


def test_unicode_braille_to_brf_passes_through_non_braille_chars():
    assert unicode_braille_to_brf("hello\nworld") == "hello\nworld"


def test_insert_with_ties_simple_duration_no_split():
    part = stream.Part()
    insert_with_ties(part, 0.0, 1.0, m21note.Note("C4").pitch)
    notes = list(part.recurse().notes)
    assert len(notes) == 1
    assert notes[0].tie is None
    assert notes[0].duration.quarterLength == 1.0


def test_insert_with_ties_splits_complex_duration():
    part = stream.Part()
    insert_with_ties(part, 0.0, 1.25, m21note.Note("C4").pitch)
    notes = list(part.recurse().notes)
    assert len(notes) == 2
    assert [n.duration.quarterLength for n in notes] == [1.0, 0.25]
    assert notes[0].tie.type == "start"
    assert notes[1].tie.type == "stop"
    assert notes[0].offset == 0.0
    assert notes[1].offset == 1.0


def test_insert_with_ties_rest():
    part = stream.Part()
    insert_with_ties(part, 0.0, 1.0, None)
    elements = list(part.recurse().notesAndRests)
    assert len(elements) == 1
    assert elements[0].isRest


def test_skyline_melody_collapses_chord_to_top_note():
    part = stream.Part()
    part.insert(0.0, m21chord.Chord(["C4", "E4", "G4"], quarterLength=1.0))
    part.insert(1.0, m21note.Note("D4", quarterLength=1.0))

    melody = skyline_melody(part)
    notes = list(melody.recurse().notes)

    assert len(notes) == 2
    assert notes[0].pitch.nameWithOctave == "G4"
    assert notes[1].pitch.nameWithOctave == "D4"


def test_skyline_melody_preserves_rests():
    part = stream.Part()
    part.insert(0.0, m21note.Note("C4", quarterLength=1.0))
    part.insert(1.0, m21note.Rest(quarterLength=1.0))
    part.insert(2.0, m21note.Note("D4", quarterLength=1.0))

    melody = skyline_melody(part)
    elements = list(melody.recurse().notesAndRests)

    assert [e.isRest for e in elements] == [False, True, False]
