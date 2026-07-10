from pathlib import Path

import audio_input


def test_symbolic_extensions_pass_through_unchanged(tmp_path, monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("transcribe() should not be called for a symbolic score")

    monkeypatch.setattr(audio_input, "transcribe", fail_if_called)

    for suffix in (".musicxml", ".mid", ".midi", ".xml", ".mxl"):
        p = tmp_path / f"foo{suffix}"
        p.touch()
        assert audio_input.resolve_score_path(p) == p


def test_audio_extensions_are_recognized():
    assert audio_input.AUDIO_EXTENSIONS == {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aiff", ".aif"}


def test_audio_extension_triggers_transcription(tmp_path, monkeypatch):
    calls = {}

    def fake_transcribe(
        audio_path, out_dir, title=None, quantize=None, onset_threshold=None, frame_threshold=None,
        minimum_note_length=None,
    ):
        calls["args"] = (audio_path, out_dir, title, quantize, onset_threshold, frame_threshold, minimum_note_length)
        out_dir.mkdir(parents=True, exist_ok=True)
        result_path = out_dir / "transcribed.musicxml"
        result_path.touch()
        return {"path": result_path}

    monkeypatch.setattr(audio_input, "transcribe", fake_transcribe)

    audio_path = tmp_path / "foo.wav"
    audio_path.touch()

    result = audio_input.resolve_score_path(audio_path, quantize=4, onset_threshold=0.6, frame_threshold=0.2)

    assert result == tmp_path / "transcribed.musicxml"
    assert calls["args"] == (audio_path, tmp_path, None, 4, 0.6, 0.2, None)


def test_out_dir_defaults_to_input_parent(tmp_path, monkeypatch):
    def fake_transcribe(audio_path, out_dir, **kwargs):
        assert out_dir == audio_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        return {"path": out_dir / "out.musicxml"}

    monkeypatch.setattr(audio_input, "transcribe", fake_transcribe)

    audio_path = tmp_path / "sub" / "foo.mp3"
    audio_path.parent.mkdir()
    audio_path.touch()

    audio_input.resolve_score_path(audio_path)


def test_extension_matching_is_case_insensitive(tmp_path, monkeypatch):
    called = []
    monkeypatch.setattr(
        audio_input, "transcribe",
        lambda audio_path, out_dir, **kwargs: called.append(True) or {"path": out_dir / "out.musicxml"},
    )
    p = tmp_path / "foo.WAV"
    p.touch()
    audio_input.resolve_score_path(p)
    assert called == [True]
