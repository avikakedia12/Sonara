from unittest.mock import MagicMock, patch

import pytest
import yt_dlp

from youtube_input import download_youtube_audio


def test_download_youtube_audio_success(tmp_path, monkeypatch):
    downloaded_path = tmp_path / "abc123.m4a"
    downloaded_path.write_bytes(b"fake audio bytes")

    fake_ydl = MagicMock()
    fake_ydl.__enter__.return_value = fake_ydl
    fake_ydl.__exit__.return_value = False
    fake_ydl.extract_info.return_value = {"id": "abc123", "ext": "m4a"}
    fake_ydl.prepare_filename.return_value = str(downloaded_path)

    with patch("yt_dlp.YoutubeDL", return_value=fake_ydl) as mock_cls:
        result = download_youtube_audio("https://youtube.com/watch?v=abc123", tmp_path)

    assert result == downloaded_path
    fake_ydl.extract_info.assert_called_once_with("https://youtube.com/watch?v=abc123", download=True)
    # bestaudio, no postprocessors -- must not depend on ffmpeg being installed
    opts = mock_cls.call_args[0][0]
    assert "postprocessors" not in opts
    assert "m4a" in opts["format"]


def test_download_youtube_audio_raises_clear_error_on_failure(tmp_path):
    fake_ydl = MagicMock()
    fake_ydl.__enter__.return_value = fake_ydl
    fake_ydl.__exit__.return_value = False
    fake_ydl.extract_info.side_effect = yt_dlp.utils.DownloadError("Video unavailable")

    with patch("yt_dlp.YoutubeDL", return_value=fake_ydl):
        with pytest.raises(RuntimeError, match="Could not download audio"):
            download_youtube_audio("https://youtube.com/watch?v=deadbeef", tmp_path)


def test_download_youtube_audio_raises_if_file_missing(tmp_path):
    fake_ydl = MagicMock()
    fake_ydl.__enter__.return_value = fake_ydl
    fake_ydl.__exit__.return_value = False
    fake_ydl.extract_info.return_value = {"id": "xyz", "ext": "m4a"}
    fake_ydl.prepare_filename.return_value = str(tmp_path / "xyz.m4a")  # never written

    with patch("yt_dlp.YoutubeDL", return_value=fake_ydl):
        with pytest.raises(RuntimeError, match="no file was found"):
            download_youtube_audio("https://youtube.com/watch?v=xyz", tmp_path)
