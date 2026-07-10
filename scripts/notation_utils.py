"""Shared helpers for building clean, Braille-safe music21 notation."""
import bisect
import contextlib
import io
from pathlib import Path

from music21 import duration, note, pitch as m21pitch, stream, tie


@contextlib.contextmanager
def quiet_basic_pitch():
    """basic-pitch's CoreML prediction path (basic_pitch.inference.Model.predict)
    unconditionally prints isfinite/shape/dtype debug lines on every inference
    window -- hundreds of lines of noise for a real recording, since it fires
    once per sliding window, not once per call. That's in the installed
    third-party package, not our code, so it can't be edited directly (and
    wouldn't survive a basic-pitch upgrade if it were monkeypatched); silencing
    stdout for the duration of the call is the least invasive fix available."""
    with contextlib.redirect_stdout(io.StringIO()):
        yield


def average_polyphony(notes: list[dict]) -> float:
    """Average number of simultaneously-sounding notes at each note's onset --
    a cheap proxy for how dense/polyphonic a passage is.

    For each note, the count of others sounding at its onset (other.start <=
    n.start < other.end) is (# starts <= n.start) - (# ends <= n.start), both
    obtained by binary search over pre-sorted start/end lists -- O(n log n)
    instead of comparing every note to every other note (O(n^2)), which matters
    once a piece produces several thousand notes (long/dense audio, or
    basic-pitch's characteristic over-segmentation)."""
    if not notes:
        return 0.0
    starts = sorted(n["start"] for n in notes)
    ends = sorted(n["end"] for n in notes)
    total = sum(
        bisect.bisect_right(starts, n["start"]) - bisect.bisect_right(ends, n["start"])
        for n in notes
    )
    return total / len(notes)


def predict_notes_adaptive(
    audio_path: Path, dense_polyphony_threshold: float = 3.4, minimum_note_length: float = 40.0
) -> tuple[list[dict], float, float, dict]:
    """Probe with basic-pitch's stock thresholds, estimate polyphony density from
    the result, and only re-run with higher (stricter) thresholds if the material
    looks dense/multi-voiced -- tuned thresholds measurably help on dense chamber
    music but measurably hurt on solo/sparse material (verified against MusicNet
    ground truth: quintet F 0.220->0.291 with stricter thresholds, solo piano F
    0.478->0.441, i.e. worse -- so one fixed default is wrong for both).

    dense_polyphony_threshold=3.4 is interpolated from exactly two calibration
    points (quintet ~4.15, solo piano ~2.63) -- a real cutoff, not arbitrary,
    but only validated to bracket those two cases. Untested on other ensemble
    sizes/genres; may need re-tuning as more material is evaluated.

    minimum_note_length (ms) is basic-pitch's own note-length floor -- notes
    shorter than this are dropped outright, regardless of detection confidence.
    basic-pitch's stock default (127.70ms) silently guts fast passage-work.
    40.0ms is used here instead of that stock default, based on a 7-track
    MusicNet grid search (with leave-one-out validation, not just picking the
    best value on the full set -- same discipline as dense_polyphony_threshold
    above) across values from 20-127.7ms: 40ms raised average onset+pitch
    F-measure from 0.395 to 0.413 (+6.4 points on a piano trio, +5.5 on a wind
    quintet, at the cost of -1.6 on solo piano and -0.4 on a string quartet --
    a net win, not uniform). Fixed threshold pairs applied uniformly across all
    7 tracks scored *worse* on average than keeping the existing adaptive
    per-track threshold selection, which is why this stays a flat default
    rather than something threaded into the polyphony-based branching above.

    The probe and (if triggered) dense pass both need basic-pitch's neural net
    output, just decoded at different thresholds -- so the net only runs once
    here (`run_inference`), and `model_output_to_notes` (the threshold-dependent
    decode step) is called again on the cached output rather than re-running
    the whole `predict()` (audio load + model inference + decode) a second
    time. Same results as calling predict() twice, just without redoing the
    identical inference pass."""
    from basic_pitch import ICASSP_2022_MODEL_PATH
    from basic_pitch.inference import AUDIO_SAMPLE_RATE, FFT_HOP, Model, run_inference
    from basic_pitch.note_creation import model_output_to_notes

    # Matches predict()'s minimum_note_length handling, converted the same way,
    # so both decodes below behave identically to two predict() calls.
    min_note_len = round(minimum_note_length / 1000 * (AUDIO_SAMPLE_RATE / FFT_HOP))

    model = Model(ICASSP_2022_MODEL_PATH)
    print(f"Transcribing {audio_path.name}...")
    with quiet_basic_pitch():
        model_output = run_inference(str(audio_path), model)

    def decode(onset_threshold: float, frame_threshold: float) -> list[dict]:
        midi_data, _ = model_output_to_notes(
            model_output, onset_thresh=onset_threshold, frame_thresh=frame_threshold, min_note_len=min_note_len,
        )
        return [
            {"start": n.start, "end": n.end, "pitch": n.pitch}
            for instrument in midi_data.instruments
            for n in instrument.notes
        ], midi_data

    stock = dict(onset_threshold=0.5, frame_threshold=0.3)
    probe_notes, midi_data = decode(**stock)
    polyphony = average_polyphony(probe_notes)

    if polyphony <= dense_polyphony_threshold:
        return probe_notes, polyphony, midi_data, stock

    dense = dict(onset_threshold=0.65, frame_threshold=0.25)
    dense_notes, midi_data = decode(**dense)
    return dense_notes, polyphony, midi_data, dense

# North American Braille ASCII (NABCC) table: index i is the ASCII character
# for the braille cell whose dot pattern equals the 6-bit mask i (bit0=dot1,
# bit1=dot2, ... bit5=dot6) -- i.e. the same order as Unicode's Braille
# Patterns block (U+2800 = mask 0, U+2801 = mask 1, ...). This is what BRF
# (the format real embossers/braille displays expect) actually contains,
# as opposed to the Unicode Braille Patterns music21 prints to the screen.
_NABCC_TABLE = (
    " A1B'K2L@CIF/MSP\"E3H9O6R^DJG>NTQ,*5<-U8V.%[$+X!&;:4\\0Z7(_?W]#Y)="
)


def unicode_braille_to_brf(text: str) -> str:
    """Convert Unicode Braille Patterns (U+2800-U+283F) to BRF ASCII braille.
    Characters outside that block (e.g. plain newlines) pass through as-is."""
    out = []
    for ch in text:
        code = ord(ch)
        if 0x2800 <= code <= 0x283F:
            out.append(_NABCC_TABLE[code - 0x2800])
        else:
            out.append(ch)
    return "".join(out)


def insert_with_ties(target: stream.Part, offset: float, quarter_length: float, p: m21pitch.Pitch | None) -> None:
    """Insert a note/rest at offset, splitting non-standard durations (e.g. 1.25)
    into consecutive tied/simple components -- Braille cells only encode simple
    (plain or dotted) durations, not arbitrary fractional lengths."""
    d = duration.Duration(quarter_length)
    components = d.components if d.isComplex else (d,)
    running_offset = offset
    for i, comp in enumerate(components):
        if p is None:
            el = note.Rest()
        else:
            el = note.Note(p)
            if len(components) > 1:
                position = "start" if i == 0 else "stop" if i == len(components) - 1 else "continue"
                el.tie = tie.Tie(position)
        el.duration = duration.Duration(comp.quarterLength)
        target.insert(running_offset, el)
        running_offset += comp.quarterLength


def skyline_melody(part: stream.Part) -> stream.Part:
    """Collapse simultaneous notes down to the highest-sounding pitch at each offset."""
    chordified = part.chordify()
    melody = stream.Part()
    for el in chordified.recurse().getElementsByClass(("Chord", "Note", "Rest")):
        offset = el.getOffsetInHierarchy(chordified)
        if el.isRest:
            insert_with_ties(melody, offset, el.quarterLength, None)
        else:
            pitches = el.pitches if el.isChord else [el.pitch]
            top = max(pitches)
            insert_with_ties(melody, offset, el.quarterLength, top)
    melody.makeNotation(inPlace=True)
    return melody
