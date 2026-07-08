"""Shared helpers for building clean, Braille-safe music21 notation."""
from music21 import duration, note, pitch as m21pitch, stream, tie

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
