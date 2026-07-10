from pathlib import Path

import pytest
from music21 import meter, note, stream

REPO_ROOT = Path(__file__).resolve().parent.parent
SAMPLE_DIR = REPO_ROOT / "data" / "sample"


@pytest.fixture
def sample_score_path() -> Path:
    """A real, hand-checkable symbolic score (5-part chamber piece)."""
    path = SAMPLE_DIR / "1727_true.musicxml"
    if not path.exists():
        pytest.skip(f"sample score not found at {path} (data/sample/ is gitignored, regenerate from archive/)")
    return path

@pytest.fixture
def sample_audio_path() -> Path:
    path = SAMPLE_DIR / "1727_clip30.wav"
    if not path.exists():
        pytest.skip(f"sample audio not found at {path} (data/sample/ is gitignored, regenerate from archive/)")
    return path


@pytest.fixture
def simple_musicxml_bytes(tmp_path) -> bytes:
    """A small but real, valid MusicXML file (one part, 8 quarter notes) --
    enough for transpose/braille/describe to operate on meaningfully."""
    part = stream.Part()
    part.insert(0, meter.TimeSignature("4/4"))
    for pitch in ("C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"):
        part.append(note.Note(pitch, quarterLength=1.0))
    score = stream.Score()
    score.insert(0, part)

    xml_path = tmp_path / "simple.musicxml"
    score.write("musicxml", fp=str(xml_path))
    return xml_path.read_bytes()
