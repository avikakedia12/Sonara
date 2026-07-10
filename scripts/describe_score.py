#!/usr/bin/env python3
"""Describe a score's structure in plain text, and optionally speak it aloud.

MusicXML/MIDI/etc. (or a raw audio file) -> a structural description a blind
musician can use to get oriented before reading the piece note-by-note in
Braille -- title/instrumentation/key/tempo up front, with progressively more
detail (per-part range, dynamics, and a full change log of every tempo/time
signature/key/dynamic marking) available via --level.

Input may be a symbolic score (MusicXML/MIDI/etc.) OR a raw audio file
(wav/mp3/etc., by extension -- see audio_input.AUDIO_EXTENSIONS). Audio is run
through transcribe_audio.transcribe first to get a score; this reuses that
pipeline rather than duplicating it, so the same accuracy caveats apply (see
that module's docstring) -- describing a symbolic score directly is still the
guaranteed-accurate path.

Key is read from an explicit KeySignature/Key object if the score has one;
otherwise it's *estimated* via music21's Krumhansl-Schmuckler key-finding
algorithm (`Stream.analyze('key')`) and labeled "estimated" in the output --
this is a best-guess, not ground truth, and can be wrong on ambiguous or
modulating material.

Duration is likewise an estimate: total score length in quarter notes divided
by the first tempo marking (or 120bpm if none is present), which ignores any
mid-piece tempo changes. Good enough to say "about three minutes", not
precise enough to cue a stopwatch.

Speech (--speak) uses pyttsx3, an offline/local TTS wrapper (no dataset,
training, or network calls) -- optional dependency, only imported if --speak
is passed. Install with `pip install pyttsx3`.
"""
import argparse
from pathlib import Path

from music21 import converter, dynamics as m21dynamics, instrument as m21instrument, key as m21key, meter, stream, tempo as m21tempo

from audio_input import resolve_score_path

DEFAULT_BPM = 120.0


def _parts_of(score: stream.Score) -> list[stream.Part]:
    return list(score.parts) if score.parts else [score]


def _measure_number(el) -> int | None:
    measure = el.getContextByClass(stream.Measure)
    return measure.number if measure is not None else None


def get_title_composer(score: stream.Score) -> tuple[str | None, str | None]:
    md = score.metadata
    if md is None:
        return None, None
    return md.title, md.composer


def get_instrumentation(score: stream.Score) -> list[str]:
    names = []
    for i, part in enumerate(_parts_of(score)):
        instr = part.getInstrument(returnDefault=False)
        names.append(instr.instrumentName if instr is not None and instr.instrumentName else f"Part {i + 1}")
    return names


def get_key(score: stream.Score) -> tuple[str, bool]:
    explicit = score.recurse().getElementsByClass(m21key.KeySignature).first()
    if explicit is not None:
        if isinstance(explicit, m21key.Key):
            return explicit.tonicPitchNameWithCase + " " + explicit.mode, False
        sharps = explicit.sharps
        if sharps == 0:
            label = "no sharps or flats"
        else:
            kind = "sharp" if sharps > 0 else "flat"
            label = f"{abs(sharps)} {kind}{'s' if abs(sharps) != 1 else ''}"
        return label, False
    estimated = score.analyze("key")
    return f"{estimated.tonicPitchNameWithCase} {estimated.mode}", True


def get_time_signatures(score: stream.Score) -> list[tuple[int | None, str]]:
    seen = []
    last_ratio = None
    for ts in score.recurse().getElementsByClass(meter.TimeSignature):
        if ts.ratioString == last_ratio:
            continue
        seen.append((_measure_number(ts), ts.ratioString))
        last_ratio = ts.ratioString
    return seen


def get_tempos(score: stream.Score) -> list[tuple[int | None, float]]:
    seen = []
    last_bpm = None
    for mm in score.recurse().getElementsByClass(m21tempo.MetronomeMark):
        if mm.number is None or mm.number == last_bpm:
            continue
        seen.append((_measure_number(mm), mm.number))
        last_bpm = mm.number
    return seen


def get_measure_count(score: stream.Score) -> int | None:
    counts = [len(p.getElementsByClass(stream.Measure)) for p in _parts_of(score)]
    counts = [c for c in counts if c > 0]
    return max(counts) if counts else None


def estimate_duration_seconds(score: stream.Score, tempos: list[tuple[int | None, float]]) -> float:
    bpm = tempos[0][1] if tempos else DEFAULT_BPM
    total_quarters = max((p.highestTime for p in _parts_of(score)), default=0.0)
    return total_quarters / bpm * 60.0


def format_duration(seconds: float) -> str:
    minutes, secs = divmod(round(seconds), 60)
    return f"{minutes}:{secs:02d}"


def get_ambitus(part: stream.Part) -> tuple[str, str] | None:
    pitches = [p for n in part.recurse().notes for p in (n.pitches if n.isChord else (n.pitch,))]
    if not pitches:
        return None
    return min(pitches).nameWithOctave, max(pitches).nameWithOctave


def get_dynamics(part: stream.Part) -> list[tuple[int | None, str]]:
    return [(_measure_number(d), d.value) for d in part.recurse().getElementsByClass(m21dynamics.Dynamic)]


def build_description(score: stream.Score, level: str = "standard") -> str:
    parts = _parts_of(score)
    instrumentation = get_instrumentation(score)
    key_str, key_estimated = get_key(score)
    time_sigs = get_time_signatures(score)
    tempos = get_tempos(score)
    measure_count = get_measure_count(score)
    duration_s = estimate_duration_seconds(score, tempos)

    lines = []

    title, composer = get_title_composer(score)
    header = title or "Untitled piece"
    if composer:
        header += f" by {composer}"
    lines.append(header + ".")

    ensemble = "Solo " + instrumentation[0] if len(instrumentation) == 1 else ", ".join(instrumentation)
    lines.append(f"Scored for {ensemble}.")

    key_phrase = f"Key: {key_str}" + (" (estimated)" if key_estimated else "")
    ts_phrase = f"time signature {time_sigs[0][1]}" if time_sigs else "no time signature found"
    tempo_phrase = f"tempo marking {round(tempos[0][1])} BPM" if tempos else f"no tempo marking (assuming {round(DEFAULT_BPM)} BPM for duration estimate)"
    lines.append(f"{key_phrase}, {ts_phrase}, {tempo_phrase}.")

    length_phrase = f"{measure_count} measures" if measure_count else "measure count unavailable"
    lines.append(f"{length_phrase}, approximately {format_duration(duration_s)} at the opening tempo.")

    if level == "brief":
        return " ".join(lines)

    for name, part in zip(instrumentation, parts):
        ambitus = get_ambitus(part)
        range_phrase = f"range {ambitus[0]} to {ambitus[1]}" if ambitus else "no pitched notes found"
        dynamics = get_dynamics(part)
        dyn_values = sorted({v for _, v in dynamics}, key=lambda v: v)
        dyn_phrase = f"dynamics used: {', '.join(dyn_values)}" if dyn_values else "no dynamic markings"
        lines.append(f"{name}: {range_phrase}; {dyn_phrase}.")

    if len(time_sigs) > 1:
        lines.append(f"{len(time_sigs)} time signature changes.")
    if len(tempos) > 1:
        lines.append(f"{len(tempos)} tempo changes.")

    if level == "standard":
        return " ".join(lines)

    if len(time_sigs) > 1:
        change_list = ", ".join(f"measure {m or '?'}: {ts}" for m, ts in time_sigs)
        lines.append(f"Time signature changes -- {change_list}.")
    if len(tempos) > 1:
        change_list = ", ".join(f"measure {m or '?'}: {round(bpm)} BPM" for m, bpm in tempos)
        lines.append(f"Tempo changes -- {change_list}.")

    for name, part in zip(instrumentation, parts):
        dynamics = get_dynamics(part)
        if not dynamics:
            continue
        change_list = ", ".join(f"measure {m or '?'}: {v}" for m, v in dynamics)
        lines.append(f"{name} dynamic markings -- {change_list}.")

    return " ".join(lines)


def speak_description(text: str, out_path: Path) -> Path:
    try:
        import pyttsx3
    except ImportError as exc:
        raise RuntimeError("Speech rendering requires pyttsx3: run `pip install pyttsx3`") from exc

    engine = pyttsx3.init()
    engine.save_to_file(text, str(out_path))
    engine.runAndWait()
    return out_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input", type=Path,
        help="Path to a MusicXML/MIDI/etc. score, or an audio file (wav/mp3/etc.) to transcribe first",
    )
    parser.add_argument(
        "--level", choices=("brief", "standard", "detailed"), default="standard",
        help="brief: header/key/tempo/length only. standard: + per-part range and dynamics summary. "
             "detailed: + full measure-by-measure change log.",
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
    parser.add_argument("--out", type=Path, default=None, help="Output text path (defaults to stdout only)")
    parser.add_argument("--speak", action="store_true", help="Also render the description to speech audio")
    parser.add_argument(
        "--tts-out", type=Path, default=None,
        help="Speech audio output path (defaults to <input-stem>_description.aiff)",
    )
    args = parser.parse_args()

    score_path = resolve_score_path(
        args.input, quantize=args.transcribe_quantize,
        onset_threshold=args.onset_threshold, frame_threshold=args.frame_threshold,
        minimum_note_length=args.min_note_length,
    )
    if score_path != args.input:
        print(f"Transcribed {args.input} -> {score_path}")

    score = converter.parse(str(score_path))
    if not isinstance(score, stream.Score):
        wrapped = stream.Score()
        wrapped.insert(0, score)
        score = wrapped

    description = build_description(score, args.level)
    print(description)

    if args.out:
        args.out.write_text(description, encoding="utf-8")
        print(f"\nWrote {args.out}")

    if args.speak:
        tts_out = args.tts_out or score_path.with_name(f"{score_path.stem}_description.aiff")
        try:
            speak_description(description, tts_out)
        except RuntimeError as exc:
            raise SystemExit(str(exc))
        print(f"Wrote {tts_out}")


if __name__ == "__main__":
    main()
