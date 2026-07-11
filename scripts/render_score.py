"""Render a MusicXML score into actual visual sheet music -- SVG (vector) or
PNG (raster), one page per page of engraved notation -- using verovio.

verovio is a lightweight, pip-installable music engraving library -- unlike
music21's own .write('musicxml.png'), it doesn't need a full desktop notation
app (MuseScore Studio/LilyPond) installed, so rendering works headlessly
wherever this package is installed (a server, a CI box, etc.).

PNG rendering shells out to macOS's built-in `qlmanage` (Quick Look) to
rasterize verovio's SVG output, rather than adding a PNG-rendering dependency
(e.g. cairosvg) that itself needs a native library (libcairo) this machine
doesn't have installed. This makes render_to_png_pages() macOS-only; a
Linux/other-platform deployment would need cairosvg+libcairo (or an
equivalent SVG rasterizer) swapped in instead.
"""
import os
import shutil
import subprocess
import tempfile
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


def render_to_png_pages(musicxml_path: Path, size: int = 1600) -> list[bytes]:
    """Same as render_to_svg_pages, but rasterized to PNG bytes -- for
    clients that just want an image to look at (e.g. embedded directly in an
    API JSON response as base64), not vector markup to parse or re-render.
    macOS-only (see module docstring)."""
    svg_pages = render_to_svg_pages(musicxml_path)

    png_pages = []
    with tempfile.TemporaryDirectory(prefix="sonara_render_") as tmp_dir:
        tmp_dir_path = Path(tmp_dir)
        for i, svg in enumerate(svg_pages):
            svg_path = tmp_dir_path / f"page{i}.svg"
            svg_path.write_text(svg, encoding="utf-8")
            subprocess.run(
                ["qlmanage", "-t", "-s", str(size), "-o", str(tmp_dir_path), str(svg_path)],
                check=True, capture_output=True,
            )
            png_path = tmp_dir_path / f"page{i}.svg.png"
            png_pages.append(png_path.read_bytes())
    return png_pages
