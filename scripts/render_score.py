"""Render a MusicXML score into actual visual sheet music (SVG, one page per
page of engraved notation) using verovio.

verovio is a lightweight, pip-installable music engraving library -- unlike
music21's own .write('musicxml.png'), it doesn't need a full desktop notation
app (MuseScore Studio/LilyPond) installed, so rendering works headlessly
wherever this package is installed (a server, a CI box, etc.).

SVG rather than PNG/PDF: verovio renders natively to SVG (vector, scales
cleanly, opens directly in a browser or most OS image viewers) without an
extra image-conversion dependency (e.g. cairosvg) to go from SVG to a raster
format.
"""
import os
from pathlib import Path

import verovio

# verovio ships its font/glyph data (Bravura, Leipzig, etc.) inside its own
# package directory. setDefaultResourcePath() alone isn't reliable here: the
# API serves each request in a worker thread (FastAPI runs sync endpoints via
# a thread pool), and the toolkit only picks up the *default* resource path
# set in whichever thread happened to construct it first -- other threads'
# Toolkit() instances can end up without it and fail to load fonts. Setting
# it explicitly on each instance via setResourcePath() (below) avoids that.
_RESOURCE_PATH = os.path.join(os.path.dirname(verovio.__file__), "data")


def render_to_svg_pages(musicxml_path: Path) -> list[str]:
    """Returns one SVG string per page of engraved notation.

    Note: a raw, unquantized ML transcription (e.g. transcribe_audio.py
    without --quantize) can carry extremely fine-grained, irregular note
    durations -- verovio renders it anyway, but the result is visually dense
    and hard to read (lots of tiny tuplets/ties), and may log "Unknown dur"
    warnings for durations outside its recognized set. --quantize (or Braille's
    --quantize) snaps notes to a clean rhythmic grid first, which is what
    actually produces readable sheet music, not this rendering step itself."""
    tk = verovio.toolkit()
    tk.setResourcePath(_RESOURCE_PATH)
    if not tk.loadFile(str(musicxml_path)):
        raise ValueError(f"verovio could not load {musicxml_path} as MusicXML")
    return [tk.renderToSVG(page) for page in range(1, tk.getPageCount() + 1)]
