#!/usr/bin/env python3
"""Transpose a score for a target instrument and range-check the result.

Input is assumed to carry its true sounding pitch already (via music21's
toSoundingPitch, which is a no-op if the part has no transposing instrument
declared, or correctly un-transposes it if it does). The part is then
retargeted to the requested instrument and converted to that instrument's
written pitch using music21's interval-based transposition -- no dataset or
training involved, this is a fixed, deterministic music-theory operation.

Notes that fall outside the target instrument's playable range are flagged
in the report but NOT altered (no silent octave-shifting or dropping) --
range violations are a judgment call for a human, not something to guess at
automatically.

Input may be a symbolic score (MusicXML/MIDI/etc.) OR a raw audio file
(wav/mp3/etc., by extension -- see AUDIO_EXTENSIONS). Audio is run through
transcribe_audio.transcribe first to get a score; this reuses that pipeline
rather than duplicating it, so the same accuracy caveats apply (see that
module's docstring) -- transposing straight from a symbolic score is still
the guaranteed-accurate path.
"""
import argparse
from pathlib import Path

from music21 import converter, instrument as m21instrument, pitch as m21pitch, stream

from audio_input import AUDIO_EXTENSIONS, resolve_score_path

# Written-pitch playable ranges, hand-curated from standard orchestration
# references (practical ranges, not extreme professional limits). music21's
# own Instrument classes reliably provide a lowestNote but almost never a
# highestNote, so this fills that gap rather than silently skipping half the
# range check. Transposition intervals themselves ARE built into music21 and
# are used as-is (not reproduced here).
INSTRUMENT_REGISTRY = {
    "flute": (m21instrument.Flute, "C4", "D7"),
    "oboe": (m21instrument.Oboe, "B-3", "A6"),
    "clarinet": (m21instrument.Clarinet, "E3", "C7"),
    "bassoon": (m21instrument.Bassoon, "B-1", "E-5"),
    "alto_sax": (m21instrument.AltoSaxophone, "B-3", "F#6"),
    "tenor_sax": (m21instrument.TenorSaxophone, "B-3", "F#6"),
    "trumpet": (m21instrument.Trumpet, "F#3", "D6"),
    "horn": (m21instrument.Horn, "F#2", "C6"),
    "violin": (m21instrument.Violin, "G3", "C7"),
    "viola": (m21instrument.Viola, "C3", "E6"),
    "cello": (m21instrument.Violoncello, "C2", "C6"),
    "contrabass": (m21instrument.Contrabass, "E2", "G5"),
    "piano": (m21instrument.Piano, "A0", "C8"),
    "english_horn": (m21instrument.EnglishHorn, "B3", "C7"),
}


def transpose_for_instrument(part: stream.Part, target_name: str) -> tuple[stream.Part, list[dict]]:
    cls, low_str, high_str = INSTRUMENT_REGISTRY[target_name]
    low, high = m21pitch.Pitch(low_str), m21pitch.Pitch(high_str)

    sounding = part.toSoundingPitch()
    for el in list(sounding.recurse().getElementsByClass(m21instrument.Instrument)):
        sounding.remove(el, recurse=True)
    sounding.insert(0, cls())
    sounding.atSoundingPitch = True
    written = sounding.toWrittenPitch()

    out_of_range = []
    for n in written.recurse().notes:
        pitches = n.pitches if n.isChord else (n.pitch,)
        for p in pitches:
            if p.ps < low.ps or p.ps > high.ps:
                out_of_range.append({
                    "offset": n.getOffsetInHierarchy(written),
                    "pitch": p.nameWithOctave,
                    "direction": "below" if p.ps < low.ps else "above",
                })
    return written, out_of_range


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input", type=Path,
        help="Path to a MusicXML/MIDI/etc. score, or an audio file (wav/mp3/etc.) to transcribe first",
    )
    parser.add_argument(
        "--target-instrument", required=True, choices=sorted(INSTRUMENT_REGISTRY.keys()),
        help="Instrument to transpose for",
    )
    parser.add_argument("--part-index", type=int, default=0, help="Which part to transpose")
    parser.add_argument("--out", type=Path, default=None, help="Output MusicXML path")
    parser.add_argument(
        "--quantize", type=int, default=None, metavar="SUBDIVISIONS",
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
    args = parser.parse_args()

    score_path = resolve_score_path(
        args.input, quantize=args.quantize,
        onset_threshold=args.onset_threshold, frame_threshold=args.frame_threshold,
        minimum_note_length=args.min_note_length,
    )
    if score_path != args.input:
        print(f"Transcribed {args.input} -> {score_path}")

    score = converter.parse(str(score_path))
    parts = score.parts if score.parts else [score]
    if args.part_index >= len(parts):
        raise SystemExit(f"Score only has {len(parts)} part(s); --part-index {args.part_index} out of range")
    part = parts[args.part_index]

    written, out_of_range = transpose_for_instrument(part, args.target_instrument)

    out_score = stream.Score()
    out_score.insert(0, written)
    out_path = args.out or args.input.with_stem(f"{args.input.stem}_{args.target_instrument}").with_suffix(".musicxml")
    out_score.write("musicxml", fp=str(out_path))

    _, low_str, high_str = INSTRUMENT_REGISTRY[args.target_instrument]
    print(f"Wrote {out_path}")
    if out_of_range:
        print(
            f"\n{len(out_of_range)} note(s) outside {args.target_instrument}'s playable "
            f"written range ({low_str}-{high_str}), NOT altered -- flagged for review:"
        )
        for v in out_of_range[:20]:
            print(f"  beat {v['offset']:.2f}: {v['pitch']} ({v['direction']} range)")
        if len(out_of_range) > 20:
            print(f"  ... and {len(out_of_range) - 20} more")
    else:
        print(f"All notes within {args.target_instrument}'s playable range ({low_str}-{high_str}).")


if __name__ == "__main__":
    main()
