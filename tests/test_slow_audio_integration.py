"""Real end-to-end tests against actual basic-pitch audio transcription (no
mocking) -- slower (several seconds each, loads a real model) and skipped by
default. Run explicitly with `pytest -m slow`.

Everything else in tests/ verifies logic with fakes/synthetic scores, which
is fast and deterministic but never actually calls basic-pitch. These tests
are the ones that would catch a real regression in the audio_input.py <->
transcribe_audio.py integration itself.
"""
import pytest

from audio_input import resolve_score_path
from describe_score import build_description
from to_braille import transcribe_to_braille
from transpose_score import transpose_for_instrument
from music21 import converter

pytestmark = pytest.mark.slow


def test_transpose_real_audio_input(sample_audio_path):
    score_path = resolve_score_path(sample_audio_path, quantize=4)
    assert score_path != sample_audio_path
    assert score_path.suffix == ".musicxml"

    score = converter.parse(str(score_path))
    part = score.parts[0] if score.parts else score
    written, out_of_range = transpose_for_instrument(part, "clarinet")

    assert len(list(written.recurse().notes)) > 0
    assert isinstance(out_of_range, list)


def test_braille_real_audio_input(sample_audio_path):
    result = transcribe_to_braille(
        resolve_score_path(sample_audio_path, quantize=4), melody_only=True, quantize="4"
    )
    assert result["chunks_transcribed"] > 0
    assert result["brl_text"].strip() != ""


def test_describe_real_audio_input(sample_audio_path):
    score_path = resolve_score_path(sample_audio_path, quantize=4)
    score = converter.parse(str(score_path))
    text = build_description(score, "detailed")
    assert "BPM" in text
    assert "measures" in text
