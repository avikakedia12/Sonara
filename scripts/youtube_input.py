"""Download the audio track from a YouTube URL so it can be fed into the
same pipeline as any other audio file (transcribe/braille/transpose/describe).

On a machine with ffmpeg available (production), yt-dlp's FFmpegExtractAudio
postprocessor normalizes whatever stream we get -- audio-only or a
progressive video+audio stream, m4a/webm/mp4/whatever -- into a clean
audio-only .m4a. This also sidesteps YouTube exposing wildly different
formats per video: some videos only have progressive (video+audio combined)
streams via the client that actually works for them (confirmed for a
VEVO/label video -- see PLAYER_CLIENTS below), and post-processing handles
that uniformly instead of chasing per-video format availability.

Local dev (this machine) has no ffmpeg installed, so postprocessing is
skipped there -- relies on YouTube already serving an m4a-compatible
audio-only stream as-is and macOS's native Core Audio decoder (audioread's
"macca" backend, which librosa falls back to) reading it directly.

Three things confirmed in production, all required together for downloads
to work from Railway at all:

- YT_PROXY_URL: routes yt-dlp's requests through a residential proxy (e.g.
  "http://user:pass@p.webshare.io:80"). Railway's datacenter IP range is
  blocked by YouTube's bot check regardless of player client or PO token --
  this is what actually clears that block. Optional: unset, yt-dlp just
  connects directly (fine for local dev on a residential IP).
- POT_PROVIDER_URL: the bgutil-ytdlp-pot-provider sidecar (see the
  neighboring Railway service "bgutil-pot-provider") mints the PO token the
  web client needs.
- PLAYER_CLIENTS: yt-dlp's default (unforced) client selection sometimes
  queries only a single client (e.g. android_vr) and, if that one reports
  the video UNPLAYABLE, gives up without trying any other -- confirmed for
  a real, public, playable video where android_vr alone falsely reports it
  unavailable but android/tv/web/mweb extract it fine. Passing an explicit
  list makes yt-dlp try all of them rather than stopping at the first
  definitive-looking failure.
"""
import os
import shutil
from pathlib import Path

import yt_dlp

POT_PROVIDER_URL = os.environ.get(
    "POT_PROVIDER_URL", "http://bgutil-pot-provider.railway.internal:4416"
)
YT_PROXY_URL = os.environ.get("YT_PROXY_URL")
PLAYER_CLIENTS = ["android", "tv", "web", "mweb"]
HAS_FFMPEG = shutil.which("ffmpeg") is not None


def download_youtube_audio(url: str, out_dir: Path) -> Path:
    """Downloads the best available audio-only stream (preferring m4a, which
    this project's pipeline can already read natively) and returns its path.
    Raises RuntimeError with a client-facing message on failure (invalid
    URL, private/unavailable video, no audio stream, etc.)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    outtmpl = str(out_dir / "%(id)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "extractor_args": {
            "youtube": {"player_client": PLAYER_CLIENTS},
            "youtubepot-bgutilhttp": {"base_url": [POT_PROVIDER_URL]},
        },
    }
    if YT_PROXY_URL:
        ydl_opts["proxy"] = YT_PROXY_URL
    if HAS_FFMPEG:
        ydl_opts["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "m4a"}
        ]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = Path(ydl.prepare_filename(info))
            if HAS_FFMPEG:
                path = path.with_suffix(".m4a")
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
