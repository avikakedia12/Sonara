#!/usr/bin/env python3
"""Convert a music21-readable score (MusicXML/MIDI/etc.) into Braille music code.

Uses music21's built-in Braille transcriber (music21.braille), which implements
the Music Braille Code spec. Braille music is transcribed one line/voice at a
time (the way a blind musician reads one hand or one instrument's part), so
this operates on a single Part.

Raw polyphonic transcriptions (e.g. from an ML audio model) are often too
dense/noisy -- overlapping, unquantized notes -- for the Braille engine to
place in cells. Use --melody-only to collapse each simultaneity down to its
top note (a "skyline" reduction) when the source isn't clean enough for direct
transcription, or --quantize to snap durations to a rhythmic grid.

music21's braille formatter also breaks on long real pieces. This isn't really
a data problem: a several-minute part reliably fails where a ~25-measure chunk
of the same music succeeds, because the formatter groups an unbroken run of
notes (e.g. a tremolo passage with no rests) into one atomic "note grouping"
that must fit on a single braille line (standard width: 40 cells) -- and it has
no fallback to wrap that atomic group across lines, so it throws instead. So
whole parts are transcribed in fixed-size beat windows (which also mirrors how
braille music is actually read: page by page), and any window that still fails
at standard width is retried at progressively wider line lengths.
"""
import argparse
from pathlib import Path

from music21 import converter, duration, note, pitch as m21pitch, stream, tie
import music21.braille.translate as braille_translate


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


def chunk_part(part: stream.Part, chunk_beats: float) -> list[stream.Part]:
    total_beats = part.highestTime
    chunks = []
    start = 0.0
    while start < total_beats:
        end = start + chunk_beats
        excerpt = part.getElementsByOffset(
            start, end, includeEndBoundary=False, mustBeginInSpan=False
        ).stream()
        excerpt = excerpt.makeMeasures(inPlace=False)
        chunks.append((start, end, excerpt))
        start = end
    return chunks


def transcribe_with_retry(excerpt: stream.Part, line_lengths=(40, 80, 160, 320)):
    """Try standard braille line width first; widen only if a dense/unbroken
    passage doesn't fit, rather than failing outright."""
    last_exc = None
    for line_length in line_lengths:
        try:
            return braille_translate.partToBraille(excerpt, maxLineLength=line_length), line_length
        except Exception as exc:  # noqa: BLE001 - try the next width
            last_exc = exc
    raise last_exc


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Path to a MusicXML/MIDI/etc. score")
    parser.add_argument("--part-index", type=int, default=0, help="Which part to transcribe")
    parser.add_argument(
        "--melody-only",
        action="store_true",
        help="Reduce to a single top-note line before transcribing (for noisy/dense input)",
    )
    parser.add_argument(
        "--quantize",
        default=None,
        help="Quantize divisors as comma-separated ints, e.g. '4,3' (snap to 16th/triplet grid)",
    )
    parser.add_argument(
        "--chunk-beats",
        type=float,
        default=40.0,
        help="Transcribe in windows of this many beats (music21's braille formatter is unreliable on long parts)",
    )
    parser.add_argument("--out", type=Path, default=None, help="Output .brl path")
    args = parser.parse_args()

    score = converter.parse(str(args.input))
    parts = score.parts if score.parts else [score]
    if args.part_index >= len(parts):
        raise SystemExit(f"Score only has {len(parts)} part(s); --part-index {args.part_index} out of range")
    part = parts[args.part_index]

    if args.melody_only:
        part = skyline_melody(part)

    if args.quantize:
        divisors = tuple(int(x) for x in args.quantize.split(","))
        part = part.quantize(divisors, processOffsets=True, processDurations=True)

    sections = []
    failed = []
    for start, end, excerpt in chunk_part(part, args.chunk_beats):
        if not excerpt.flatten().notesAndRests:
            continue
        try:
            braille_text, line_length = transcribe_with_retry(excerpt)
        except Exception as exc:  # noqa: BLE001 - report and keep going across chunks
            failed.append((start, end, str(exc)))
            continue
        widened = f" (widened to {line_length} cells)" if line_length != 40 else ""
        sections.append(f"% beats {start:g}-{end:g}{widened}\n{braille_text}")

    out_path = args.out or args.input.with_suffix(".brl")
    out_path.write_text("\n\n".join(sections), encoding="utf-8")
    print(f"Wrote {out_path} ({len(sections)} of {len(sections) + len(failed)} chunks transcribed)")
    if failed:
        print(f"Failed chunks (beats): {[(round(s), round(e)) for s, e, _ in failed]}")
    print("\n\n".join(sections))


if __name__ == "__main__":
    main()
