"""Unavailable media paths must not abort a project's integrity check."""

import errno
from pathlib import Path

import pytest

from boris import config as cfg
from boris import project_functions


@pytest.mark.parametrize("absolute", [False, True])
@pytest.mark.parametrize("error_number", [errno.EACCES, errno.EIO])
def test_inaccessible_media_is_reported(monkeypatch, tmp_path, absolute, error_number):
    project = tmp_path / "project.boris"
    media = str(tmp_path / "video.mp4") if absolute else "video.mp4"
    original_exists = Path.exists
    candidates = {Path(media), project.parent / media}

    def exists(path):
        if path in candidates:
            raise OSError(error_number, "synthetic filesystem error", str(path))
        return original_exists(path)

    # Python 3.13 can propagate these errors from exists(); 3.14 suppresses them.
    monkeypatch.setattr(Path, "exists", exists)
    observation = {cfg.TYPE: cfg.MEDIA, cfg.FILE: {cfg.ALL_PLAYERS[0]: [media]}}
    assert project_functions.check_if_media_available(observation, str(project)) == (
        False,
        f"Media file <b>{media}</b> was not found",
    )


def test_inaccessible_working_directory_candidate_allows_project_relative_file(monkeypatch, tmp_path):
    media = tmp_path / "video.mp4"
    media.write_bytes(b"synthetic media placeholder")
    original_exists = Path.exists

    def exists(path):
        if path == Path("video.mp4"):
            raise PermissionError(errno.EACCES, "synthetic access denial", str(path))
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", exists)
    assert project_functions.full_path("video.mp4", str(tmp_path / "project.boris")) == str(media)


def test_accessible_absolute_file_is_preserved(tmp_path):
    media = tmp_path / "video.mp4"
    media.touch()
    assert project_functions.full_path(str(media), str(tmp_path / "project.boris")) == str(media)


def test_inaccessible_project_relative_candidate(monkeypatch, tmp_path):
    candidate = tmp_path / "video.mp4"
    original_exists = Path.exists

    def exists(path):
        if path == candidate:
            raise PermissionError(errno.EACCES, "synthetic access denial", str(path))
        if path == Path("video.mp4"):
            return False
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", exists)
    assert project_functions.full_path("video.mp4", str(tmp_path / "project.boris")) == ""


def test_missing_file_is_reported(tmp_path):
    assert project_functions.full_path(str(tmp_path / "missing.mp4"), str(tmp_path / "project.boris")) == ""


def test_unexpected_error_is_not_suppressed(monkeypatch, tmp_path):
    original_exists = Path.exists

    def exists(path):
        if path == Path("video.mp4"):
            raise RuntimeError("unexpected implementation failure")
        return original_exists(path)

    monkeypatch.setattr(Path, "exists", exists)
    with pytest.raises(RuntimeError, match="unexpected implementation failure"):
        project_functions.full_path("video.mp4", str(tmp_path / "project.boris"))
