#!/usr/bin/env python3
"""REST API for the Sonara pipeline.

Thin wrappers around the reusable functions already in transcribe_audio.py,
to_braille.py, and transpose_score.py -- no pipeline logic is duplicated
here, only request/response handling.

Run with: uvicorn api:app --reload --port 8000
Interactive docs at http://127.0.0.1:8000/docs once running.

IMPORTANT accuracy caveat for /transcribe: audio-to-notation transcription is
inherently imperfect (measured F-measure ~0.3-0.65 depending on material --
see README's Accuracy work section). This endpoint is a best-effort draft,
not a guaranteed-accurate source. For guaranteed-accurate output, start from
a symbolic score (MusicXML/MIDI from notation software) and call /braille or
/transpose directly, skipping /transcribe.
"""
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from music21 import converter, stream

from audio_input import AUDIO_EXTENSIONS
from to_braille import transcribe_to_braille
from transcribe_audio import transcribe
from transpose_score import INSTRUMENT_REGISTRY, transpose_for_instrument

app = FastAPI(
    title="Sonara",
    description="Audio-to-Braille music accessibility pipeline",
    version="0.1.0",
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
) -> tuple[Path, Optional[str]]:
    """If upload_path is audio, transcribe it to MusicXML first and return
    (musicxml_path, accuracy_note); otherwise return (upload_path, None)
    unchanged. Shared by /braille and /transpose so both accept audio or a
    symbolic score interchangeably."""
    if upload_path.suffix.lower() not in AUDIO_EXTENSIONS:
        return upload_path, None
    try:
        result = transcribe(upload_path, upload_path.parent / "out", None, transcribe_quantize, onset_threshold, frame_threshold)
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
async def transcribe_endpoint(
    audio: UploadFile = File(..., description="Audio file (wav/mp3/etc.)"),
    quantize: Optional[int] = Form(None, description="Beat-grid subdivisions, e.g. 4 = 16th notes; omit for raw timing"),
    title: Optional[str] = Form(None),
    onset_threshold: Optional[float] = Form(None, description="Fix a threshold instead of adaptive selection"),
    frame_threshold: Optional[float] = Form(None),
):
    """Audio -> MusicXML. Best-effort draft, not guaranteed accurate (see module docstring)."""
    audio_path = _save_upload(audio, ".wav")
    out_dir = audio_path.parent / "out"
    try:
        result = transcribe(audio_path, out_dir, title, quantize, onset_threshold, frame_threshold)
    except Exception as exc:  # noqa: BLE001 - surface as a client-facing error
        raise HTTPException(status_code=422, detail=f"Transcription failed: {exc}")

    return {
        "musicxml": result["path"].read_text(encoding="utf-8"),
        "polyphony": result["polyphony"],
        "thresholds_used": result["thresholds_used"],
        "tempo_bpm": result["tempo_bpm"],
        "accuracy_note": (
            "Best-effort audio transcription, not guaranteed accurate. "
            "For guaranteed-accurate output, provide a symbolic score to /braille or /transpose instead."
        ),
    }


@app.post("/braille")
async def braille_endpoint(
    score: UploadFile = File(..., description="MusicXML/MIDI/etc. score, OR a raw audio file (wav/mp3/etc.) to transcribe first"),
    part_index: int = Form(0),
    melody_only: bool = Form(False, description="Collapse to a single top-note line (for dense/noisy input)"),
    quantize: Optional[str] = Form(None, description="Braille rhythm quantization: comma-separated divisors, e.g. '4,3' (not related to transcribe_quantize below)"),
    chunk_beats: float = Form(40.0),
    transcribe_quantize: Optional[int] = Form(None, description="If input is audio: beat-grid subdivisions, e.g. 4 (ignored for symbolic input)"),
    onset_threshold: Optional[float] = Form(None, description="If input is audio: fix a threshold instead of adaptive selection"),
    frame_threshold: Optional[float] = Form(None),
):
    """Score or audio -> Braille Music Code (.brl annotated text + .brf embosser-ready ASCII)."""
    upload_path = _save_upload(score, ".musicxml")
    score_path, accuracy_note = _maybe_transcribe(upload_path, transcribe_quantize, onset_threshold, frame_threshold)
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
async def transpose_endpoint(
    score: UploadFile = File(..., description="MusicXML/MIDI/etc. score, OR a raw audio file (wav/mp3/etc.) to transcribe first"),
    target_instrument: str = Form(..., description=f"One of: {sorted(INSTRUMENT_REGISTRY)}"),
    part_index: int = Form(0),
    quantize: Optional[int] = Form(None, description="If input is audio: beat-grid subdivisions, e.g. 4 (ignored for symbolic input)"),
    onset_threshold: Optional[float] = Form(None, description="If input is audio: fix a threshold instead of adaptive selection"),
    frame_threshold: Optional[float] = Form(None),
):
    """Score or audio + target instrument -> transposed MusicXML + range-violation report."""
    if target_instrument not in INSTRUMENT_REGISTRY:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown instrument '{target_instrument}'. Choices: {sorted(INSTRUMENT_REGISTRY)}",
        )
    upload_path = _save_upload(score, ".musicxml")
    score_path, accuracy_note = _maybe_transcribe(upload_path, quantize, onset_threshold, frame_threshold)

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
    }
    if accuracy_note:
        response["accuracy_note"] = accuracy_note
    return response


@app.post("/describe")
async def describe_endpoint(score: UploadFile = File(...)):
    """Not implemented yet -- see README status."""
    raise HTTPException(status_code=501, detail="The /describe endpoint is not implemented yet.")


@app.get("/")
async def root():
    return {
        "name": "Sonara",
        "endpoints": ["/transcribe", "/braille", "/transpose", "/describe (not implemented)"],
        "docs": "/docs",
    }
