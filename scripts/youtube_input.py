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

Two things have to be in place for this to work from Railway (confirmed in
production, both required together -- neither alone is enough):

- YT_PROXY_URL: routes yt-dlp's requests through a residential proxy (e.g.
  "http://user:pass@p.webshare.io:80"). Railway's datacenter IP range is
  blocked by YouTube's bot check regardless of player client or PO token --
  this is what actually clears that block. Optional: unset, yt-dlp just
  connects directly (fine for local dev on a residential IP).
- POT_PROVIDER_URL: the bgutil-ytdlp-pot-provider sidecar (see the
  neighboring Railway service "bgutil-pot-provider") mints the PO token the
  web client needs. Without a valid token, forcing a specific player client
  (android/tv_embedded) to dodge the token requirement instead loses
  real audio-only formats entirely -- those clients only expose progressive
  (video+audio combined) streams, and the "web" client's own audio-only
  formats get filtered out under YouTube's SABR streaming restriction
  (https://github.com/yt-dlp/yt-dlp/issues/12482). With a valid token,
  yt-dlp's default client selection produces genuine audio-only m4a/webm
  formats normally -- no player_client override needed.
"""
import os
from pathlib import Path

import yt_dlp

POT_PROVIDER_URL = os.environ.get(
    "POT_PROVIDER_URL", "http://bgutil-pot-provider.railway.internal:4416"
)
YT_PROXY_URL = os.environ.get("YT_PROXY_URL")


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
            "youtubepot-bgutilhttp": {"base_url": [POT_PROVIDER_URL]},
        },
    }
    if YT_PROXY_URL:
        ydl_opts["proxy"] = YT_PROXY_URL

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
