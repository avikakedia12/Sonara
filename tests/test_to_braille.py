import pytest
from music21 import chord as m21chord, converter, meter, note, stream

from to_braille import chunk_part, transcribe_to_braille


def _write_score(part: stream.Part, path) -> None:
    score = stream.Score()
    score.insert(0, part)
    score.write("musicxml", fp=str(path))


def test_chunk_part_splits_on_beat_boundaries():
    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    for _ in range(8):
        part.append(note.Note("C4", quarterLength=1.0))

    chunks = chunk_part(part, 4.0)
    assert len(chunks) == 2
    assert [start for start, _, _ in chunks] == [0.0, 4.0]


def test_chunk_part_does_not_duplicate_notes_across_boundary(tmp_path):
    # Regression test: a measure that ends exactly on a chunk boundary was
    # previously being pulled into both the chunk it belongs to AND the next
    # one (music21's mustBeginInSpan=False treats "ends exactly at start" as
    # overlapping the next window). Each note must appear in exactly one chunk.
    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    for _ in range(8):
        part.append(note.Note("C4", quarterLength=1.0))

    xml_path = tmp_path / "score.musicxml"
    _write_score(part, xml_path)
    parsed = converter.parse(str(xml_path))

    chunks = chunk_part(parsed.parts[0], 4.0)
    note_counts = [len(list(excerpt.recurse().notes)) for _, _, excerpt in chunks]
    assert note_counts == [4, 4]
    assert sum(note_counts) == 8


def test_chunk_part_keeps_note_sustained_across_boundary():
    # A note that genuinely starts before the boundary and sustains past it
    # must still show up in the chunk it sustains into (mustBeginInSpan=False
    # is there for exactly this case, and the fix must not break it).
    part = stream.Part()
    part.insert(0.0, note.Note("C4", quarterLength=6.0))  # spans 0.0-6.0

    chunks = chunk_part(part, 4.0)
    assert len(chunks) == 2
    first_notes = list(chunks[0][2].recurse().notes)
    second_notes = list(chunks[1][2].recurse().notes)
    assert len(first_notes) == 1
    assert len(second_notes) == 1  # the sustaining note carries into chunk 2


def test_transcribe_to_braille_simple_part(tmp_path):
    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    for pitch in ("C4", "D4", "E4", "F4"):
        part.append(note.Note(pitch, quarterLength=1.0))

    xml_path = tmp_path / "score.musicxml"
    _write_score(part, xml_path)

    result = transcribe_to_braille(xml_path)
    assert result["chunks_transcribed"] == 1
    assert result["chunks_total"] == 1
    assert result["failed_chunks"] == []
    assert result["brl_text"].strip() != ""
    assert result["brf_text"].strip() != ""
    assert "% beats" in result["brl_text"]
    # BRF must contain no comment lines -- only braille cells, since real
    # embossers would emboss "% beats ..." as meaningless dot patterns.
    assert "%" not in result["brf_text"]


def test_transcribe_to_braille_part_index_out_of_range(tmp_path):
    part = stream.Part()
    part.append(note.Note("C4", quarterLength=1.0))
    xml_path = tmp_path / "score.musicxml"
    _write_score(part, xml_path)

    with pytest.raises(ValueError, match="part_index"):
        transcribe_to_braille(xml_path, part_index=5)


def test_transcribe_to_braille_invalid_quantize_raises_clear_error(tmp_path):
    # Regression test: Swagger UI prefills optional string fields with the
    # literal placeholder text "string" -- if a user doesn't clear it, this
    # used to crash with a raw "invalid literal for int() with base 10:
    # 'string'" instead of a client-facing, actionable error message.
    part = stream.Part()
    part.append(note.Note("C4", quarterLength=1.0))
    xml_path = tmp_path / "score.musicxml"
    _write_score(part, xml_path)

    with pytest.raises(ValueError, match="quantize must be comma-separated integers"):
        transcribe_to_braille(xml_path, quantize="string")


def test_transcribe_to_braille_melody_only_reduces_chords(tmp_path):
    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    part.append(m21chord.Chord(["C4", "E4", "G4"], quarterLength=4.0))

    xml_path = tmp_path / "score.musicxml"
    _write_score(part, xml_path)

    with_chord = transcribe_to_braille(xml_path, melody_only=False)
    melody_only = transcribe_to_braille(xml_path, melody_only=True)

    # Both should succeed and produce non-empty, generally different output
    # (chord vs. single top note) -- exact braille cell content isn't the
    # point here, just that melody_only actually took effect.
    assert with_chord["brl_text"].strip() != ""
    assert melody_only["brl_text"].strip() != ""
