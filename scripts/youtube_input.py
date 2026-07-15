"""Download the audio track from a YouTube URL so it can be fed into the
same pipeline as any other audio file (transcribe/braille/transpose/describe).

Deliberately avoids yt-dlp's FFmpegExtractAudio postprocessor (and any
format that would need merging separate audio/video streams): this machine
has no ffmpeg installed, and none of that is actually necessary here --
YouTube already serves audio-only streams (no video track to strip), and
macOS's native Core Audio decoder (audioread's "macca" backend, which
librosa falls back to) reads m4a/AAC directly. Downloading the m4a
audio-only stream as-is and handing that straight to the existing pipeline
is both simpler and requires one fewer dependency than the usual
yt-dlp-plus-ffmpeg setup.
"""
import os
from pathlib import Path

import yt_dlp

# bgutil-ytdlp-pot-provider sidecar (see the neighboring Railway service
# "bgutil-pot-provider") mints the PO token YouTube's web client now
# requires. Without it, every player client eventually hits the "Sign in to
# confirm you're not a bot" wall from Railway's datacenter IPs regardless of
# client spoofing -- confirmed in production.
#
# The web client alone isn't enough even with a valid token: YouTube forces
# SABR streaming for web, which omits direct format URLs entirely (yt-dlp
# only gets image formats back -- see
# https://github.com/yt-dlp/yt-dlp/issues/12482). android/tv_embedded still
# expose real progressive audio URLs and aren't gated behind a token, so
# they're kept in the mix for their formats while web (protected by the
# token) is what actually clears the bot check -- confirmed together they
# extract a usable format where either alone fails.
POT_PROVIDER_URL = os.environ.get(
    "POT_PROVIDER_URL", "http://bgutil-pot-provider.railway.internal:4416"
)
PLAYER_CLIENTS = ["android", "tv_embedded", "web"]


def download_youtube_audio(url: str, out_dir: Path) -> Path:
    """Downloads the best available audio-only stream (preferring m4a, which
    this project's pipeline can already read natively) and returns its path.
    Raises RuntimeError with a client-facing message on failure (invalid
    URL, private/unavailable video, no audio stream, etc.)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(out_dir / "%(id)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio/best",
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        # No postprocessors -- keep whatever container the audio-only stream
        # already comes in rather than re-encoding via ffmpeg.
        "extractor_args": {
            "youtube": {"player_client": PLAYER_CLIENTS},
            "youtubepot-bgutilhttp": {"base_url": [POT_PROVIDER_URL]},
        },
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = Path(ydl.prepare_filename(info))
    except yt_dlp.utils.DownloadError as exc:
        if "Sign in to confirm" in str(exc):
            raise RuntimeError(
                "YouTube is blocking downloads from this server (not specific to this video or "
                "your account). Download the audio yourself (e.g. with a browser extension or "
                "yt-dlp locally) and upload the file directly instead -- that always works."
            ) from exc
        raise RuntimeError(f"Could not download audio from that YouTube URL: {exc}") from exc

    if not path.exists():
        raise RuntimeError(f"yt-dlp reported success but no file was found at {path}")
    return path
