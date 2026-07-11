#!/usr/bin/env python3
"""REST API for the Sonara pipeline.

Thin wrappers around the reusable functions already in transcribe_audio.py,
to_braille.py, transpose_score.py, and describe_score.py -- no pipeline
logic is duplicated here, only request/response handling.

Run with: uvicorn api:app --reload --port 8000
Interactive docs at http://127.0.0.1:8000/docs once running.

IMPORTANT accuracy caveat for /transcribe: audio-to-notation transcription is
inherently imperfect (measured F-measure ~0.3-0.65 depending on material --
see README's Accuracy work section). This endpoint is a best-effort draft,
not a guaranteed-accurate source. For guaranteed-accurate output, start from
a symbolic score (MusicXML/MIDI from notation software) and call /braille or
/transpose directly, skipping /transcribe.
"""
import base64
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from music21 import converter, stream

from audio_input import AUDIO_EXTENSIONS
from describe_score import build_description, speak_description
from render_score import render_to_svg_pages
from to_braille import transcribe_to_braille
from transcribe_audio import transcribe
from transpose_score import INSTRUMENT_REGISTRY, transpose_for_instrument

app = FastAPI(
    title="Sonara",
    description="Audio-to-Braille music accessibility pipeline",
    version="0.1.0",
)

# Local-dev-only: lets the Vite frontend (localhost:5173 by default) call this
# API (localhost:8000) despite being a different origin. Both sides only ever
# run on localhost in this project, so a permissive localhost/127.0.0.1
# allowlist is fine here -- this isn't a public deployment.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


def _save_upload(upload: UploadFile, default_suffix: str) -> Path:
    suffix = Path(upload.filename or "").suffix or default_suffix
    tmp_dir = Path(tempfile.mkdtemp(prefix="sonara_api_"))
    dest = tmp_dir / f"input{suffix}"
    with dest.open("wb") as f:
        shutil.copyfileobj(upload.file, f)
    return dest


def _maybe_transcribe(
    upload_path: Path,
    transcribe_quantize: Optional[int] = None,
    onset_threshold: Optional[float] = None,
    frame_threshold: Optional[float] = None,
    minimum_note_length: Optional[float] = None,
) -> tuple[Path, Optional[str]]:
    """If upload_path is audio, transcribe it to MusicXML first and return
    (musicxml_path, accuracy_note); otherwise return (upload_path, None)
    unchanged. Shared by /braille and /transpose so both accept audio or a
    symbolic score interchangeably."""
    if upload_path.suffix.lower() not in AUDIO_EXTENSIONS:
        return upload_path, None
    try:
        result = transcribe(
            upload_path, upload_path.parent / "out", None, transcribe_quantize,
            onset_threshold, frame_threshold, minimum_note_length,
        )
    except Exception as exc:  # noqa: BLE001 - surface as a client-facing error
        raise HTTPException(status_code=422, detail=f"Transcription failed: {exc}")
    accuracy_note = (
        "Input was audio, transcribed with best-effort accuracy first. "
        "For guaranteed-accurate output, provide a symbolic score instead."
    )
    return result["path"], accuracy_note


def _load_part(score_path: Path, part_index: int) -> stream.Part:
    parsed = converter.parse(str(score_path))
    parts = parsed.parts if parsed.parts else [parsed]
    if part_index >= len(parts):
        raise HTTPException(
            status_code=422,
            detail=f"Score only has {len(parts)} part(s); part_index {part_index} out of range",
        )
    return parts[part_index]


@app.post("/transcribe")
def transcribe_endpoint(
    audio: UploadFile = File(..., description="Audio file (wav/mp3/etc.)"),
    quantize: Optional[int] = Form(None, description="Beat-grid subdivisions, e.g. 4 = 16th notes; omit for raw timing"),
    title: Optional[str] = Form(None),
    onset_threshold: Optional[float] = Form(None, description="Fix a threshold instead of adaptive selection"),
    frame_threshold: Optional[float] = Form(None),
    minimum_note_length: Optional[float] = Form(
        None, description="basic-pitch's note-length floor in ms (default 40.0, tuned lower than basic-pitch's stock 127.70); lower still for fast passage-work"
    ),
):
    """Audio -> MusicXML. Best-effort draft, not guaranteed accurate (see module docstring)."""
    audio_path = _save_upload(audio, ".wav")
    out_dir = audio_path.parent / "out"
    try:
        result = transcribe(audio_path, out_dir, title, quantize, onset_threshold, frame_threshold, minimum_note_length)
    except Exception as exc:  # noqa: BLE001 - surface as a client-facing error
        raise HTTPException(status_code=422, detail=f"Transcription failed: {exc}")

    return {
        "musicxml": result["path"].read_text(encoding="utf-8"),
        "polyphony": result["polyphony"],
        "thresholds_used": result["thresholds_used"],
        "tempo_bpm": result["tempo_bpm"],
        "sheet_music_svg": result["sheet_music_svg"],
        "accuracy_note": (
            "Best-effort audio transcription, not guaranteed accurate. "
            "For guaranteed-accurate output, provide a symbolic score to /braille or /transpose instead."
        ),
    }


@app.post("/braille")
def braille_endpoint(
    score: UploadFile = File(..., description="MusicXML/MIDI/etc. score, OR a raw audio file (wav/mp3/etc.) to transcribe first"),
    part_index: int = Form(0),
    melody_only: bool = Form(False, description="Collapse to a single top-note line (for dense/noisy input)"),
    quantize: Optional[str] = Form(None, description="Braille rhythm quantization: comma-separated divisors, e.g. '4,3' (not related to transcribe_quantize below)"),
    chunk_beats: float = Form(40.0),
    transcribe_quantize: Optional[int] = Form(None, description="If input is audio: beat-grid subdivisions, e.g. 4 (ignored for symbolic input)"),
    onset_threshold: Optional[float] = Form(None, description="If input is audio: fix a threshold instead of adaptive selection"),
    frame_threshold: Optional[float] = Form(None),
    minimum_note_length: Optional[float] = Form(
        None, description="If input is audio: basic-pitch's note-length floor in ms (default 40.0, tuned lower than basic-pitch's stock 127.70); lower still for fast passage-work"
    ),
):
    """Score or audio -> Braille Music Code (.brl annotated text + .brf embosser-ready ASCII)."""
    upload_path = _save_upload(score, ".musicxml")
    score_path, accuracy_note = _maybe_transcribe(
        upload_path, transcribe_quantize, onset_threshold, frame_threshold, minimum_note_length
    )
    try:
        result = transcribe_to_braille(score_path, part_index, melody_only, quantize, chunk_beats)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    response = {
        "brl": result["brl_text"],
        "brf": result["brf_text"],
        "chunks_transcribed": result["chunks_transcribed"],
        "chunks_total": result["chunks_total"],
        "failed_chunks": result["failed_chunks"],
    }
    if accuracy_note:
        response["accuracy_note"] = accuracy_note
    return response


@app.post("/transpose")
def transpose_endpoint(
    score: UploadFile = File(..., description="MusicXML/MIDI/etc. score, OR a raw audio file (wav/mp3/etc.) to transcribe first"),
    target_instrument: str = Form(..., description=f"One of: {sorted(INSTRUMENT_REGISTRY)}"),
    part_index: int = Form(0),
    quantize: Optional[int] = Form(None, description="If input is audio: beat-grid subdivisions, e.g. 4 (ignored for symbolic input)"),
    onset_threshold: Optional[float] = Form(None, description="If input is audio: fix a threshold instead of adaptive selection"),
    frame_threshold: Optional[float] = Form(None),
    minimum_note_length: Optional[float] = Form(
        None, description="If input is audio: basic-pitch's note-length floor in ms (default 40.0, tuned lower than basic-pitch's stock 127.70); lower still for fast passage-work"
    ),
):
    """Score or audio + target instrument -> transposed MusicXML + range-violation report."""
    target_instrument = target_instrument.lower()
    if target_instrument not in INSTRUMENT_REGISTRY:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown instrument '{target_instrument}'. Choices: {sorted(INSTRUMENT_REGISTRY)}",
        )
    upload_path = _save_upload(score, ".musicxml")
    score_path, accuracy_note = _maybe_transcribe(upload_path, quantize, onset_threshold, frame_threshold, minimum_note_length)

    part = _load_part(score_path, part_index)

    written, out_of_range = transpose_for_instrument(part, target_instrument)

    out_score = stream.Score()
    out_score.insert(0, written)
    out_path = score_path.parent / "transposed.musicxml"
    out_score.write("musicxml", fp=str(out_path))

    _, low, high = INSTRUMENT_REGISTRY[target_instrument]
    response = {
        "musicxml": out_path.read_text(encoding="utf-8"),
        "target_instrument": target_instrument,
        "playable_range": {"low": low, "high": high},
        "out_of_range_notes": out_of_range,
        "sheet_music_svg": render_to_svg_pages(out_path),
    }
    if accuracy_note:
        response["accuracy_note"] = accuracy_note
    return response


@app.post("/describe")
async def describe_endpoint(
    score: UploadFile = File(..., description="MusicXML/MIDI/etc. score, OR a raw audio file (wav/mp3/etc.) to transcribe first"),
    level: str = Form("standard", description="brief | standard | detailed"),
    speak: bool = Form(False, description="Also render the description to speech audio (base64 AIFF in the response)"),
    transcribe_quantize: Optional[int] = Form(None, description="If input is audio: beat-grid subdivisions, e.g. 4 (ignored for symbolic input)"),
    onset_threshold: Optional[float] = Form(None, description="If input is audio: fix a threshold instead of adaptive selection"),
    frame_threshold: Optional[float] = Form(None),
    minimum_note_length: Optional[float] = Form(
        None, description="If input is audio: basic-pitch's note-length floor in ms (default 40.0, tuned lower than basic-pitch's stock 127.70); lower still for fast passage-work"
    ),
):
    """Score or audio -> structural text description, optionally spoken aloud.

    Unlike the other three endpoints, this one is async def (runs on the main
    thread) rather than plain def (runs in Starlette's worker thread pool):
    speak_description()'s pyttsx3 backend uses macOS's NSSpeechSynthesizer,
    which silently produces a corrupt, zero-duration audio file -- no
    exception, no error, just broken output -- when driven from any thread
    other than the process's true main thread. describe's non-speech work is
    lightweight text generation, so blocking the event loop briefly here is a
    much better tradeoff than every speak=true request returning broken audio.
    """
    if level not in ("brief", "standard", "detailed"):
        raise HTTPException(status_code=422, detail="level must be one of: brief, standard, detailed")

    upload_path = _save_upload(score, ".musicxml")
    score_path, accuracy_note = _maybe_transcribe(
        upload_path, transcribe_quantize, onset_threshold, frame_threshold, minimum_note_length
    )

    parsed = converter.parse(str(score_path))
    if not isinstance(parsed, stream.Score):
        wrapped = stream.Score()
        wrapped.insert(0, parsed)
        parsed = wrapped

    description = build_description(parsed, level)

    response = {"description": description, "level": level}
    if accuracy_note:
        response["accuracy_note"] = accuracy_note

    if speak:
        tts_path = score_path.parent / "description.aiff"
        try:
            speak_description(description, tts_path)
        except RuntimeError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        response["audio_base64"] = base64.b64encode(tts_path.read_bytes()).decode("ascii")
        response["audio_format"] = "aiff"

    return response


@app.get("/")
async def root():
    return {
        "name": "Sonara",
        "endpoints": ["/transcribe", "/braille", "/transpose", "/describe"],
        "docs": "/docs",
        "view": "/view",
    }


@app.get("/view", response_class=HTMLResponse)
async def view():
    """A minimal upload form that calls /transcribe and renders the returned
    sheet_music_svg directly in the page -- unlike /docs (Swagger UI), which
    can only show a JSON response as text, this actually displays the
    notation, since the browser is given real HTML/SVG to render, not a JSON
    string to read. No framework/build step -- one static page, inline JS."""
    return """<!DOCTYPE html>
<html>
<head>
<title>Sonara</title>
<style>
body { font-family: sans-serif; max-width: 900px; margin: 2em auto; padding: 0 1em; }
#status { margin: 1em 0; color: #555; }
#sheetMusic svg { max-width: 100%; height: auto; display: block; margin-bottom: 1em; }
</style>
</head>
<body>
<h1>Sonara: Transcribe &amp; View</h1>
<p>Upload an audio file to transcribe it and see the actual rendered sheet music below.</p>
<input type="file" id="audioFile" accept="audio/*">
<button id="submitBtn">Transcribe</button>
<div id="status"></div>
<div id="sheetMusic"></div>
<script>
document.getElementById('submitBtn').onclick = async () => {
    const fileInput = document.getElementById('audioFile');
    const status = document.getElementById('status');
    const sheetDiv = document.getElementById('sheetMusic');
    sheetDiv.innerHTML = '';
    if (!fileInput.files.length) {
        status.textContent = 'Choose an audio file first.';
        return;
    }
    status.textContent = 'Transcribing... this can take up to a minute or more for longer files.';
    const formData = new FormData();
    formData.append('audio', fileInput.files[0]);
    try {
        const resp = await fetch('/transcribe', { method: 'POST', body: formData });
        const data = await resp.json();
        if (!resp.ok) {
            status.textContent = 'Error: ' + (data.detail || resp.status);
            return;
        }
        status.textContent = `Done. Polyphony ${data.polyphony?.toFixed(2)}, ` +
            `tempo ${data.tempo_bpm?.toFixed(1)} BPM, ${data.sheet_music_svg.length} page(s). ` +
            data.accuracy_note;
        for (const svg of data.sheet_music_svg) {
            const page = document.createElement('div');
            page.innerHTML = svg;
            sheetDiv.appendChild(page);
        }
    } catch (e) {
        status.textContent = 'Request failed: ' + e;
    }
};
</script>
</body>
</html>"""
