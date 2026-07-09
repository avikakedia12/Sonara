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

from music21 import converter, stream
import music21.braille.translate as braille_translate

from notation_utils import skyline_melody, unicode_braille_to_brf


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


def transcribe_to_braille(
    input_path: Path,
    part_index: int = 0,
    melody_only: bool = False,
    quantize: str | None = None,
    chunk_beats: float = 40.0,
) -> dict:
    """Core braille-transcription logic, usable as a library call (e.g. from
    the API layer) as well as from the CLI below. Returns a dict with the
    annotated .brl text, raw BRF text, and any per-chunk failures -- callers
    decide whether to write files or return the content directly."""
    score = converter.parse(str(input_path))
    parts = score.parts if score.parts else [score]
    if part_index >= len(parts):
        raise ValueError(f"Score only has {len(parts)} part(s); part_index {part_index} out of range")
    part = parts[part_index]

    if melody_only:
        part = skyline_melody(part)

    if quantize:
        divisors = tuple(int(x) for x in quantize.split(","))
        part = part.quantize(divisors, processOffsets=True, processDurations=True)

    annotated_sections = []
    raw_chunks = []
    failed = []
    for start, end, excerpt in chunk_part(part, chunk_beats):
        if not excerpt.flatten().notesAndRests:
            continue
        try:
            braille_text, line_length = transcribe_with_retry(excerpt)
        except Exception as exc:  # noqa: BLE001 - report and keep going across chunks
            failed.append((start, end, str(exc)))
            continue
        widened = f" (widened to {line_length} cells)" if line_length != 40 else ""
        annotated_sections.append(f"% beats {start:g}-{end:g}{widened}\n{braille_text}")
        raw_chunks.append(braille_text)

    brl_text = "\n\n".join(annotated_sections)
    # BRF is the ASCII format real embossers/braille displays expect. Unlike the
    # .brl above, it must contain *only* braille cells -- no "% beats" comments,
    # which would emboss as meaningless dot patterns on real hardware.
    brf_text = unicode_braille_to_brf("\n\n".join(raw_chunks))

    return {
        "brl_text": brl_text,
        "brf_text": brf_text,
        "chunks_transcribed": len(annotated_sections),
        "chunks_total": len(annotated_sections) + len(failed),
        "failed_chunks": [(round(s), round(e), msg) for s, e, msg in failed],
    }


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

    try:
        result = transcribe_to_braille(
            args.input, args.part_index, args.melody_only, args.quantize, args.chunk_beats
        )
    except ValueError as exc:
        raise SystemExit(str(exc))

    out_path = args.out or args.input.with_suffix(".brl")
    out_path.write_text(result["brl_text"], encoding="utf-8")

    brf_path = out_path.with_suffix(".brf")
    brf_path.write_text(result["brf_text"], encoding="utf-8")

    print(f"Wrote {out_path} and {brf_path} ({result['chunks_transcribed']} of {result['chunks_total']} chunks transcribed)")
    if result["failed_chunks"]:
        print(f"Failed chunks (beats): {[(s, e) for s, e, _ in result['failed_chunks']]}")
    print(result["brl_text"])


if __name__ == "__main__":
    main()
