import pytest
from fastapi.testclient import TestClient
from music21 import meter, note, stream

import api

client = TestClient(api.app)


def _fake_transcribe_factory():
    """Builds a fake transcribe() with the same signature/return shape as the
    real transcribe_audio.transcribe, so audio-input endpoint branches can be
    tested without running actual basic-pitch inference."""
    def fake_transcribe(
        audio_path, out_dir, title=None, quantize=None, onset_threshold=None, frame_threshold=None,
        minimum_note_length=None,
    ):
        out_dir.mkdir(parents=True, exist_ok=True)
        part = stream.Part()
        part.insert(0, meter.TimeSignature("4/4"))
        for pitch in ("C4", "D4", "E4", "F4"):
            part.append(note.Note(pitch, quarterLength=1.0))
        score = stream.Score()
        score.insert(0, part)
        out_path = out_dir / f"{audio_path.stem}.musicxml"
        score.write("musicxml", fp=str(out_path))
        return {
            "path": out_path,
            "polyphony": 1.0,
            "thresholds_used": {"onset_threshold": 0.5, "frame_threshold": 0.3},
            "tempo_bpm": 120.0,
            "sheet_music_svg": ["<svg>fake</svg>"],
            "sheet_music_svg_paths": [],
        }
    return fake_transcribe


@pytest.fixture
def fake_transcribe(monkeypatch):
    fn = _fake_transcribe_factory()
    monkeypatch.setattr(api, "transcribe", fn)
    return fn


def test_root_lists_all_endpoints():
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data["endpoints"]) == {"/transcribe", "/braille", "/transpose", "/describe"}


def test_transpose_endpoint_success(simple_musicxml_bytes):
    resp = client.post(
        "/transpose",
        files={"score": ("test.musicxml", simple_musicxml_bytes, "application/xml")},
        data={"target_instrument": "clarinet"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["target_instrument"] == "clarinet"
    assert "musicxml" in data and data["musicxml"]
    assert data["playable_range"] == {"low": "E3", "high": "C7"}
    assert "accuracy_note" not in data  # symbolic input, no transcription happened


def test_transpose_endpoint_unknown_instrument(simple_musicxml_bytes):
    resp = client.post(
        "/transpose",
        files={"score": ("test.musicxml", simple_musicxml_bytes, "application/xml")},
        data={"target_instrument": "kazoo"},
    )
    assert resp.status_code == 422


def test_transpose_endpoint_part_index_out_of_range(simple_musicxml_bytes):
    resp = client.post(
        "/transpose",
        files={"score": ("test.musicxml", simple_musicxml_bytes, "application/xml")},
        data={"target_instrument": "clarinet", "part_index": "5"},
    )
    assert resp.status_code == 422


def test_transpose_endpoint_audio_input_sets_accuracy_note(fake_transcribe):
    resp = client.post(
        "/transpose",
        files={"score": ("test.wav", b"not really audio, transcribe() is faked", "audio/wav")},
        data={"target_instrument": "clarinet"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "accuracy_note" in data
    assert "audio" in data["accuracy_note"].lower()


def test_braille_endpoint_success(simple_musicxml_bytes):
    resp = client.post(
        "/braille",
        files={"score": ("test.musicxml", simple_musicxml_bytes, "application/xml")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["brl"].strip() != ""
    assert data["brf"].strip() != ""
    assert data["failed_chunks"] == []
    assert "accuracy_note" not in data


def test_braille_endpoint_bad_part_index(simple_musicxml_bytes):
    resp = client.post(
        "/braille",
        files={"score": ("test.musicxml", simple_musicxml_bytes, "application/xml")},
        data={"part_index": "5"},
    )
    assert resp.status_code == 422


def test_braille_endpoint_audio_input_sets_accuracy_note(fake_transcribe):
    resp = client.post(
        "/braille",
        files={"score": ("test.wav", b"fake audio bytes", "audio/wav")},
    )
    assert resp.status_code == 200
    assert "accuracy_note" in resp.json()


def test_describe_endpoint_brief(simple_musicxml_bytes):
    resp = client.post(
        "/describe",
        files={"score": ("test.musicxml", simple_musicxml_bytes, "application/xml")},
        data={"level": "brief"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["level"] == "brief"
    assert data["description"].strip() != ""
    assert "accuracy_note" not in data
    assert "audio_base64" not in data


def test_describe_endpoint_bad_level(simple_musicxml_bytes):
    resp = client.post(
        "/describe",
        files={"score": ("test.musicxml", simple_musicxml_bytes, "application/xml")},
        data={"level": "essay"},
    )
    assert resp.status_code == 422


def test_describe_endpoint_audio_input_sets_accuracy_note(fake_transcribe):
    resp = client.post(
        "/describe",
        files={"score": ("test.wav", b"fake audio bytes", "audio/wav")},
    )
    assert resp.status_code == 200
    assert "accuracy_note" in resp.json()


def test_describe_endpoint_speak_returns_base64_audio(simple_musicxml_bytes, monkeypatch):
    def fake_speak(text, out_path):
        from pathlib import Path
        Path(out_path).write_bytes(b"FAKE_AUDIO_BYTES")
        return out_path

    monkeypatch.setattr(api, "speak_description", fake_speak)

    resp = client.post(
        "/describe",
        files={"score": ("test.musicxml", simple_musicxml_bytes, "application/xml")},
        data={"level": "brief", "speak": "true"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["audio_format"] == "aiff"
    import base64
    assert base64.b64decode(data["audio_base64"]) == b"FAKE_AUDIO_BYTES"


def test_describe_endpoint_speak_missing_pyttsx3_returns_422(simple_musicxml_bytes, monkeypatch):
    def fake_speak(text, out_path):
        raise RuntimeError("Speech rendering requires pyttsx3: run `pip install pyttsx3`")

    monkeypatch.setattr(api, "speak_description", fake_speak)

    resp = client.post(
        "/describe",
        files={"score": ("test.musicxml", simple_musicxml_bytes, "application/xml")},
        data={"level": "brief", "speak": "true"},
    )
    assert resp.status_code == 422


def test_transcribe_endpoint(fake_transcribe):
    resp = client.post(
        "/transcribe",
        files={"audio": ("test.wav", b"fake audio bytes", "audio/wav")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["polyphony"] == 1.0
    assert data["tempo_bpm"] == 120.0
    assert "accuracy_note" in data


def test_transcribe_endpoint_failure_surfaces_as_422(monkeypatch):
    def failing_transcribe(*args, **kwargs):
        raise RuntimeError("model blew up")

    monkeypatch.setattr(api, "transcribe", failing_transcribe)

    resp = client.post(
        "/transcribe",
        files={"audio": ("test.wav", b"fake audio bytes", "audio/wav")},
    )
    assert resp.status_code == 422
    assert "model blew up" in resp.json()["detail"]
