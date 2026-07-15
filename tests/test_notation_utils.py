import numpy as np
import pretty_midi
import pytest
import soundfile as sf
from music21 import chord as m21chord, note as m21note, stream

import notation_utils
from notation_utils import (
    SAFE_CHUNK_SECONDS,
    _merge_chunk_results,
    average_polyphony,
    insert_with_ties,
    predict_notes_adaptive_chunked,
    skyline_melody,
    unicode_braille_to_brf,
)


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


def _write_silence(path, duration_s, sr=8000):
    """A real (but silent, tiny-sample-rate) audio file -- enough for librosa's
    real duration/load/slice logic to operate on for real in these tests,
    while the actually-expensive part (basic-pitch inference) is faked."""
    sf.write(str(path), np.zeros(int(duration_s * sr), dtype=np.float32), sr)


def test_predict_notes_adaptive_chunked_delegates_when_short(tmp_path, monkeypatch):
    audio_path = tmp_path / "short.wav"
    _write_silence(audio_path, SAFE_CHUNK_SECONDS - 10)

    calls = []

    def fake_predict(path, dense_polyphony_threshold=3.4, minimum_note_length=40.0):
        calls.append(path)
        return [], 0.0, pretty_midi.PrettyMIDI(), {"onset_threshold": 0.5, "frame_threshold": 0.3}

    monkeypatch.setattr(notation_utils, "predict_notes_adaptive", fake_predict)

    predict_notes_adaptive_chunked(audio_path)

    # Delegates straight to predict_notes_adaptive on the *original* path --
    # no chunking overhead (temp files, multiple calls) for the common case.
    assert calls == [audio_path]


def test_predict_notes_adaptive_chunked_triggers_chunking_when_long(tmp_path, monkeypatch):
    """Confirms the branch decision only -- predict_notes_adaptive_chunked runs
    each chunk in a freshly *spawned* process (see its docstring for why:
    confirmed against production that a plain in-process loop over safe-sized
    chunks still crashes, cumulatively), so a monkeypatch in this test process
    can't observe what happens inside those child processes. The actual
    shifting/merging math is tested directly against _merge_chunk_results
    below, without any multiprocessing involved."""
    audio_path = tmp_path / "long.wav"
    _write_silence(audio_path, SAFE_CHUNK_SECONDS + 10)

    calls = []
    monkeypatch.setattr(notation_utils, "predict_notes_adaptive", lambda *a, **k: calls.append(a))

    predict_notes_adaptive_chunked(audio_path)

    # Never called directly in *this* process for the long-audio path --
    # confirms chunking (not delegation) was taken, without asserting
    # anything about the spawned children themselves.
    assert calls == []


def test_merge_chunk_results_shifts_notes_by_chunk_offset():
    chunk_results = [
        ([{"start": 0.0, "end": 1.0, "pitch": 61, "velocity": 100}], 1.0, {"onset_threshold": 0.5, "frame_threshold": 0.3}, 0, False),
        ([{"start": 0.0, "end": 1.0, "pitch": 62, "velocity": 100}], 2.0, {"onset_threshold": 0.65, "frame_threshold": 0.25}, 0, False),
        ([{"start": 0.0, "end": 1.0, "pitch": 63, "velocity": 100}], 3.0, {"onset_threshold": 0.5, "frame_threshold": 0.3}, 0, False),
    ]
    chunk_offsets = [0.0, SAFE_CHUNK_SECONDS, SAFE_CHUNK_SECONDS * 2]
    chunk_durations = [SAFE_CHUNK_SECONDS, SAFE_CHUNK_SECONDS, 10.0]

    notes, polyphony, midi_data, thresholds_used = _merge_chunk_results(chunk_results, chunk_offsets, chunk_durations)

    # Each chunk's note (originally at t=0 in its own chunk-local timeline)
    # should land at its chunk's offset in the merged result, not pile up at 0.
    starts = sorted(n["start"] for n in notes)
    assert starts == [0.0, SAFE_CHUNK_SECONDS, SAFE_CHUNK_SECONDS * 2]

    midi_starts = sorted(n.start for n in midi_data.instruments[0].notes)
    assert midi_starts == pytest.approx(starts)
    assert sorted(n["pitch"] for n in notes) == [61, 62, 63]

    # Duration-weighted average of the three chunks' polyphonies (1, 2, 3).
    total_duration = sum(chunk_durations)
    expected_polyphony = (1 * SAFE_CHUNK_SECONDS + 2 * SAFE_CHUNK_SECONDS + 3 * 10) / total_duration
    assert polyphony == pytest.approx(expected_polyphony, rel=1e-3)

    # Reports the last chunk's threshold choice.
    assert thresholds_used == {"onset_threshold": 0.5, "frame_threshold": 0.3}


def test_merge_chunk_results_empty_chunks_produce_empty_midi():
    chunk_results = [([], 0.0, {"onset_threshold": 0.5, "frame_threshold": 0.3}, 0, False)]
    notes, polyphony, midi_data, thresholds_used = _merge_chunk_results(chunk_results, [0.0], [SAFE_CHUNK_SECONDS])

    assert notes == []
    assert polyphony == 0.0
    assert midi_data.instruments[0].notes == []
