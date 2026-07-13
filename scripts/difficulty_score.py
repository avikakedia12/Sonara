#!/usr/bin/env python3
"""Estimate how hard a piece is to play, with the exact numbers behind the rating.

MusicXML/MIDI/etc. (or a raw audio file) -> a per-part difficulty score (0-10)
plus a plain-English breakdown of *why* -- fastest note value, pitch range,
average melodic leap, chord density, key signature, and notes-per-second at
the marked tempo. Each factor is a deterministic, rule-based measurement (no
ML model, nothing trained on a difficulty-graded corpus) -- a proxy built from
the same kind of hand-curated music-theory heuristics as transpose_score.py's
instrument ranges, not a substitute for a teacher's judgment. Treat the
numbers as "harder than X, easier than Y" signal, not a certified grade level.

Input may be a symbolic score (MusicXML/MIDI/etc.) OR a raw audio file
(wav/mp3/etc., by extension -- see audio_input.AUDIO_EXTENSIONS). Audio is run
through transcribe_audio.transcribe first to get a score; this reuses that
pipeline rather than duplicating it, so the same accuracy caveats apply --
rating a symbolic score directly is still the guaranteed-accurate path, since
a mis-transcribed note can throw off range/leap/rhythm measurements.
"""
import argparse
import json
from pathlib import Path

from music21 import converter, key as m21key, meter, stream, tempo as m21tempo

from audio_input import resolve_score_path

DEFAULT_BPM = 120.0

# (minimum overall score, label) bands, checked highest-first.
LEVEL_BANDS = [
    (8.0, "Virtuosic"),
    (6.0, "Advanced"),
    (4.0, "Intermediate"),
    (2.0, "Easy"),
    (0.0, "Beginner"),
]

# How much each factor contributes to a part's overall score. Rhythm and
# leaps dominate because they're the two heaviest drivers of "hard to sight
# read" in practice; key/meter are real but secondary, so they're weighted
# low rather than left out entirely.
WEIGHTS = {
    "rhythm": 0.25,
    "interval_leaps": 0.20,
    "chord_density": 0.20,
    "tempo_density": 0.15,
    "pitch_range": 0.10,
    "key_complexity": 0.05,
    "time_signature": 0.05,
}

# Named note values for the shortest-duration-present readout, longest first
# so the first quarterLength <= threshold match wins.
_NOTE_VALUE_NAMES = [
    (4.0, "whole note"),
    (2.0, "half note"),
    (1.0, "quarter note"),
    (0.5, "eighth note"),
    (0.25, "16th note"),
    (0.125, "32nd note"),
    (0.0625, "64th note"),
]


def level_for_score(score: float) -> str:
    for minimum, label in LEVEL_BANDS:
        if score >= minimum:
            return label
    return LEVEL_BANDS[-1][1]


def _note_value_name(quarter_length: float) -> str:
    for threshold, name in _NOTE_VALUE_NAMES:
        if quarter_length >= threshold - 1e-9:
            return name
    return "shorter than a 64th note"


def _parts_of(score: stream.Score) -> list[stream.Part]:
    return list(score.parts) if score.parts else [score]


def _note_events(part: stream.Part) -> list:
    """Notes and chords (not rests) in the part, in score order."""
    return [el for el in part.recurse().notes]


def get_rhythm_score(part: stream.Part) -> tuple[float, str]:
    events = _note_events(part)
    if not events:
        return 0.0, "no notes found"

    shortest_ql = min(e.quarterLength for e in events)
    tuplet_count = sum(1 for e in events if e.duration.tuplets)
    # A note's offset within its beat: 0.0 means it lands squarely on a beat.
    # Only meaningful for simple (denominator-4) meters, since "beat" here is
    # approximated as one quarter note -- a documented simplification, not a
    # true beat-strength analysis.
    off_beat = sum(1 for e in events if min(e.offset % 1.0, 1.0 - (e.offset % 1.0)) > 0.05)
    syncopation_ratio = off_beat / len(events)

    base = min(10.0, 10.0 - (shortest_ql - 0.0625) / (1.0 - 0.0625) * 9.0) if shortest_ql < 1.0 else 1.0
    base = max(1.0, min(10.0, base))
    score = base
    if tuplet_count:
        score += 1.0
    if syncopation_ratio > 0.1:
        score += 1.0
    score = min(10.0, score)

    detail = (
        f"fastest note value is a {_note_value_name(shortest_ql)}"
        + (f", {tuplet_count} tuplet note(s)" if tuplet_count else "")
        + f", {syncopation_ratio:.0%} of note onsets fall off the beat"
    )
    return round(score, 1), detail


def get_pitch_range_score(part: stream.Part) -> tuple[float, str]:
    pitches = [p for e in _note_events(part) for p in (e.pitches if e.isChord else (e.pitch,))]
    if not pitches:
        return 0.0, "no pitched notes found"
    low, high = min(pitches), max(pitches)
    span = high.ps - low.ps
    score = min(10.0, span / 3.6)
    detail = f"range {low.nameWithOctave} to {high.nameWithOctave} ({round(span)} semitones)"
    return round(score, 1), detail


def get_interval_leap_score(part: stream.Part) -> tuple[float, str]:
    events = _note_events(part)
    # Melodic line: top note of any chord, since that's what most instruments'
    # written line tracks -- an approximation for keyboard/harp writing, where
    # "leaps" span more than just the top voice, but a reasonable default.
    line = [max(e.pitches) if e.isChord else e.pitch for e in events]
    if len(line) < 2:
        return 0.0, "not enough notes to measure melodic movement"
    intervals = [abs(b.ps - a.ps) for a, b in zip(line, line[1:])]
    avg_interval = sum(intervals) / len(intervals)
    big_leaps = sum(1 for iv in intervals if iv > 12)
    score = min(10.0, avg_interval * 1.5)
    detail = f"average melodic leap {avg_interval:.1f} semitones, {big_leaps} leap(s) larger than an octave"
    return round(score, 1), detail


def get_chord_density_score(part: stream.Part) -> tuple[float, str]:
    events = _note_events(part)
    if not events:
        return 0.0, "no notes found"
    chords = [e for e in events if e.isChord]
    if not chords:
        return 0.0, "monophonic (no simultaneous notes within the part)"
    chord_ratio = len(chords) / len(events)
    avg_size = sum(len(c.pitches) for c in chords) / len(chords)
    score = min(10.0, chord_ratio * 6.0 + (avg_size - 1) * 1.5)
    detail = f"{chord_ratio:.0%} of note-events are chords, averaging {avg_size:.1f} notes per chord"
    return round(score, 1), detail


def get_tempo_density_score(part: stream.Part, bpm: float) -> tuple[float, str]:
    events = _note_events(part)
    duration_quarters = part.highestTime
    if not events or duration_quarters <= 0:
        return 0.0, "no notes found"
    duration_seconds = duration_quarters / bpm * 60.0
    notes_per_second = len(events) / duration_seconds if duration_seconds > 0 else 0.0
    score = min(10.0, notes_per_second * 1.1)
    detail = f"{round(bpm)} BPM, approximately {notes_per_second:.1f} notes/second"
    return round(score, 1), detail


def get_key_complexity_score(score: stream.Score) -> tuple[float, str]:
    explicit = score.recurse().getElementsByClass(m21key.KeySignature).first()
    key_obj = explicit if explicit is not None else score.analyze("key")
    sharps = abs(key_obj.sharps)
    result_score = min(10.0, sharps / 7.0 * 10.0)
    if isinstance(key_obj, m21key.Key):
        label = f"{key_obj.tonicPitchNameWithCase} {key_obj.mode}"
    else:
        label = "no sharps or flats" if sharps == 0 else f"{sharps} sharp/flat(s)"
    detail = f"key: {label} ({sharps} accidental(s) in the key signature)"
    return round(result_score, 1), detail


_SIMPLE_METERS = {"2/4", "3/4", "4/4", "2/2", "3/8", "6/8", "9/8", "12/8"}


def get_time_signature_score(score: stream.Score) -> tuple[float, str]:
    sigs = list(score.recurse().getElementsByClass(meter.TimeSignature))
    if not sigs:
        return 0.0, "no time signature found"
    ratio_strings = [ts.ratioString for ts in sigs]
    unique = list(dict.fromkeys(ratio_strings))
    irregular = any(r not in _SIMPLE_METERS for r in unique)
    result_score = (6.0 if irregular else 1.0) + min(4.0, (len(unique) - 1) * 2.0)
    result_score = min(10.0, result_score)
    detail = f"{'/'.join(unique)}" + (f" ({len(unique)} meter changes)" if len(unique) > 1 else "")
    return round(result_score, 1), detail


def _sentence(text: str) -> str:
    """Upper-case just the first character -- str.capitalize() also
    lower-cases the rest, which mangles note names like "E major" -> "e major"."""
    return text[:1].upper() + text[1:] if text else text


def _combine(factor_scores: dict[str, float]) -> float:
    total = sum(factor_scores[name] * weight for name, weight in WEIGHTS.items())
    return round(total, 1)


def analyze_part(part: stream.Part, part_name: str, piece_factors: dict[str, dict]) -> dict:
    tempos = list(part.recurse().getElementsByClass(m21tempo.MetronomeMark))
    bpm = tempos[0].number if tempos and tempos[0].number else DEFAULT_BPM

    rhythm_score, rhythm_detail = get_rhythm_score(part)
    range_score, range_detail = get_pitch_range_score(part)
    leap_score, leap_detail = get_interval_leap_score(part)
    chord_score, chord_detail = get_chord_density_score(part)
    tempo_score, tempo_detail = get_tempo_density_score(part, bpm)

    factors = {
        "rhythm": {"score": rhythm_score, "detail": rhythm_detail},
        "interval_leaps": {"score": leap_score, "detail": leap_detail},
        "chord_density": {"score": chord_score, "detail": chord_detail},
        "tempo_density": {"score": tempo_score, "detail": tempo_detail},
        "pitch_range": {"score": range_score, "detail": range_detail},
        **piece_factors,
    }
    overall = _combine({name: f["score"] for name, f in factors.items()})

    return {
        "name": part_name,
        "score": overall,
        "level": level_for_score(overall),
        "factors": factors,
    }


def build_difficulty_report(score: stream.Score) -> dict:
    parts = _parts_of(score)
    instrumentation = []
    for i, part in enumerate(parts):
        instr = part.getInstrument(returnDefault=False)
        instrumentation.append(instr.instrumentName if instr is not None and instr.instrumentName else f"Part {i + 1}")

    key_score, key_detail = get_key_complexity_score(score)
    ts_score, ts_detail = get_time_signature_score(score)
    piece_factors = {
        "key_complexity": {"score": key_score, "detail": key_detail},
        "time_signature": {"score": ts_score, "detail": ts_detail},
    }

    per_part = [analyze_part(part, name, piece_factors) for name, part in zip(instrumentation, parts)]
    hardest = max(per_part, key=lambda p: p["score"])
    overall_score = hardest["score"]

    summary = (
        f"Estimated difficulty: {level_for_score(overall_score)} ({overall_score:.1f}/10)"
        + (f", driven by {hardest['name']}" if len(per_part) > 1 else "")
        + f". {_sentence(hardest['factors']['rhythm']['detail'])}. "
        f"{_sentence(hardest['factors']['pitch_range']['detail'])}. "
        f"{_sentence(hardest['factors']['interval_leaps']['detail'])}. "
        f"{_sentence(hardest['factors']['chord_density']['detail'])}. "
        f"{_sentence(piece_factors['key_complexity']['detail'])}. "
        f"{_sentence(hardest['factors']['tempo_density']['detail'])}."
    )

    return {
        "overall_score": overall_score,
        "overall_level": level_for_score(overall_score),
        "hardest_part": hardest["name"] if len(per_part) > 1 else None,
        "summary": summary,
        "per_part": per_part,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input", type=Path,
        help="Path to a MusicXML/MIDI/etc. score, or an audio file (wav/mp3/etc.) to transcribe first",
    )
    parser.add_argument(
        "--transcribe-quantize", type=int, default=None, metavar="SUBDIVISIONS",
        help="If input is audio: snap notes to a detected beat grid, e.g. 4 (ignored for symbolic input)",
    )
    parser.add_argument(
        "--onset-threshold", type=float, default=None,
        help="If input is audio: fix a basic-pitch onset threshold instead of auto-selecting",
    )
    parser.add_argument(
        "--frame-threshold", type=float, default=None,
        help="If input is audio: fix a basic-pitch frame threshold instead of auto-selecting",
    )
    parser.add_argument(
        "--min-note-length", type=float, default=None, metavar="MILLISECONDS",
        help="If input is audio: basic-pitch's note-length floor in ms (default 40.0, tuned lower than "
             "basic-pitch's stock 127.70); lower still for fast passage-work",
    )
    parser.add_argument("--out", type=Path, default=None, help="Write the full report as JSON to this path")
    args = parser.parse_args()

    score_path = resolve_score_path(
        args.input, quantize=args.transcribe_quantize,
        onset_threshold=args.onset_threshold, frame_threshold=args.frame_threshold,
        minimum_note_length=args.min_note_length,
    )
    if score_path != args.input:
        print(f"Transcribed {args.input} -> {score_path}")

    parsed = converter.parse(str(score_path))
    if not isinstance(parsed, stream.Score):
        wrapped = stream.Score()
        wrapped.insert(0, parsed)
        parsed = wrapped

    report = build_difficulty_report(parsed)
    print(report["summary"])
    print()
    for part_report in report["per_part"]:
        print(f"{part_report['name']}: {part_report['level']} ({part_report['score']:.1f}/10)")
        for factor_name, factor in part_report["factors"].items():
            print(f"  {factor_name}: {factor['score']:.1f} -- {factor['detail']}")

    if args.out:
        args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
