import sys
import os
import pytest
import subprocess
from unittest.mock import patch, MagicMock
import logging

# Assuming the function is imported from a module named `media_analysis`
# from media_analysis import accurate_media_analysis

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from boris import utilities
from boris import config


# Mocking the ffprobe_media_analysis function
def mock_ffprobe_media_analysis(ffmpeg_bin, file_name):
    return {
        "duration": 120,
        "duration_ms": 120000,
        "bitrate": 5000,
        "frames_number": 3000,
        "fps": 25,
        "has_video": True,
        "has_audio": True,
    }


# Mocking the time2seconds function
def mock_time2seconds(time_str):
    return 120


# Mocking the dec function
def mock_dec(value):
    return float(value)


@patch("utilities.ffprobe_media_analysis", side_effect=mock_ffprobe_media_analysis)
@patch("utilities.time2seconds", side_effect=mock_time2seconds)
@patch("utilities.dec", side_effect=mock_dec)
def test_accurate_media_analysis_success(mock_dec, mock_time2seconds, mock_ffprobe_media_analysis):
    ffmpeg_bin = "/path/to/ffmpeg"
    file_name = "test_video.mp4"

    result = utilities.accurate_media_analysis(ffmpeg_bin, file_name)

    assert result["duration"] == 120
    assert result["duration_ms"] == 120000
    assert result["bitrate"] == 5000
    assert result["frames_number"] == 3000
    assert result["fps"] == 25
    assert result["has_video"] is True
    assert result["has_audio"] is True


"""

@patch("utilities.ffprobe_media_analysis", return_value={"error": "ffprobe failed"})
@patch("utilities.time2seconds", side_effect=mock_time2seconds)
@patch("utilities.dec", side_effect=mock_dec)
@patch("subprocess.Popen")
def test_accurate_media_analysis_fallback(mock_popen, mock_dec, mock_time2seconds, mock_ffprobe_media_analysis):
    ffmpeg_bin = "/path/to/ffmpeg"
    file_name = "test_video.mp4"

    # Mocking the subprocess.Popen behavior
    mock_process = MagicMock()
    mock_process.communicate.return_value = (
        b"",
        b"Duration: 00:02:00.00, bitrate: 5000 kb/s\nStream #0:0: Video: h264, 1920x1080, 25 fps\nStream #0:1: Audio: aac",
    )
    mock_popen.return_value = mock_process

    result = utilities.accurate_media_analysis(ffmpeg_bin, file_name)

    assert result["duration"] == 120
    assert result["duration_ms"] == 120000
    assert result["bitrate"] == 5000000
    assert result["frames_number"] == 3000
    assert result["fps"] == 25
    assert result["has_video"] is True
    assert result["has_audio"] is True


@patch("utilities.ffprobe_media_analysis", return_value={"error": "ffprobe failed"})
@patch("utilities.time2seconds", side_effect=mock_time2seconds)
@patch("utilities.dec", side_effect=mock_dec)
@patch("subprocess.Popen")
def test_accurate_media_analysis_file_not_found(mock_popen, mock_dec, mock_time2seconds, mock_ffprobe_media_analysis):
    ffmpeg_bin = "/path/to/ffmpeg"
    file_name = "nonexistent_video.mp4"

    # Mocking the subprocess.Popen behavior
    mock_process = MagicMock()
    mock_process.communicate.return_value = (b"", b"No such file or directory")
    mock_popen.return_value = mock_process

    result = utilities.accurate_media_analysis(ffmpeg_bin, file_name)

    assert result["error"] == "No such file or directory"


@patch("utilities.ffprobe_media_analysis", return_value={"error": "ffprobe failed"})
@patch("utilities.time2seconds", side_effect=mock_time2seconds)
@patch("utilities.dec", side_effect=mock_dec)
@patch("subprocess.Popen")
def test_accurate_media_analysis_invalid_media(mock_popen, mock_dec, mock_time2seconds, mock_ffprobe_media_analysis):
    ffmpeg_bin = "/path/to/ffmpeg"
    file_name = "invalid_media.mp4"

    # Mocking the subprocess.Popen behavior
    mock_process = MagicMock()
    mock_process.communicate.return_value = (b"", b"Invalid data found when processing input")
    mock_popen.return_value = mock_process

    result = utilities.accurate_media_analysis(ffmpeg_bin, file_name)

    assert result["error"] == "This file does not seem to be a media file"


"""
