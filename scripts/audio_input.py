"""Shared "accept audio or a symbolic score" resolution for scripts that
otherwise only take a MusicXML/MIDI score (transpose, braille), so a raw
audio file can be dropped in directly instead of running transcribe_audio.py
as a separate step first.
"""
from pathlib import Path

from transcribe_audio import transcribe

AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aiff", ".aif"}


def resolve_score_path(
    input_path: Path,
    out_dir: Path | None = None,
    quantize: int | None = None,
    onset_threshold: float | None = None,
    frame_threshold: float | None = None,
    minimum_note_length: float | None = None,
) -> Path:
    """If input_path is audio, transcribe it to MusicXML first and return that
    path; otherwise return input_path unchanged. Keeps the audio->score step
    isolated so callers that already have a symbolic score pay no extra cost."""
    if input_path.suffix.lower() not in AUDIO_EXTENSIONS:
        return input_path
    result = transcribe(
        input_path,
        out_dir or input_path.parent,
        quantize=quantize,
        onset_threshold=onset_threshold,
        frame_threshold=frame_threshold,
        minimum_note_length=minimum_note_length,
    )
    return result["path"]
