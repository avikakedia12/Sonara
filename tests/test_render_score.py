from music21 import meter, note, stream

from render_score import render_to_svg_pages


def _simple_musicxml(tmp_path):
    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    for pitch in ("C4", "D4", "E4", "F4"):
        part.append(note.Note(pitch, quarterLength=1.0))
    score = stream.Score()
    score.insert(0, part)

    xml_path = tmp_path / "simple.musicxml"
    score.write("musicxml", fp=str(xml_path))
    return xml_path


def test_render_to_svg_pages_produces_svg(tmp_path):
    xml_path = _simple_musicxml(tmp_path)

    pages = render_to_svg_pages(xml_path)

    assert len(pages) == 1
    assert pages[0].strip().startswith("<?xml") or "<svg" in pages[0]


def test_render_to_svg_pages_raises_on_invalid_file(tmp_path):
    bad_path = tmp_path / "not_musicxml.musicxml"
    bad_path.write_text("this is not valid MusicXML", encoding="utf-8")

    try:
        render_to_svg_pages(bad_path)
        assert False, "expected a ValueError for an unloadable file"
    except ValueError:
        pass
