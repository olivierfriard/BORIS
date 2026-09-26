"""Tests for the observation dialog using the application's Qt binding."""

import copy
from pathlib import Path

import pytest
from PySide6.QtWidgets import QDialog, QMessageBox

from boris import config as cfg
from boris import observation


@pytest.fixture
def window(tmp_path, qapp):
    widget = observation.Observation(str(tmp_path), str(tmp_path / "project.boris"))
    widget.pj = copy.deepcopy(cfg.EMPTY_PROJECT)
    widget.ffmpeg_bin = "ffmpeg"
    widget.mode = "new"
    widget.rb_media_files.setChecked(True)
    widget.leObservationId.setText("test")
    yield widget
    widget.close()
    widget.deleteLater()


@pytest.fixture
def errors(monkeypatch):
    messages = []

    def critical(parent, title, message, *args):
        messages.append(message)
        return QMessageBox.StandardButton.Ok

    monkeypatch.setattr(QMessageBox, "critical", critical)
    return messages


def add_media(window, name="geese1.mp4"):
    error, message = window.check_media(str(Path("files", name).absolute()), "media abs path")
    assert error is False, message


def test_no_media_loaded(window, errors):
    window.pbSave.click()
    assert window.state == "refused"
    assert errors == ["A media file must be loaded in player #1"]


def test_no_obs_id(window, errors):
    add_media(window)
    window.leObservationId.clear()
    window.pbSave.click()
    assert window.state == "refused"
    assert errors == ["The <b>observation id</b> is mandatory and must be unique."]


def test_file_not_media(window):
    error, message = window.check_media("files/test.boris", "media abs path")
    assert error is True
    assert message
    assert window.twVideo1.rowCount() == 0


def test_players_in_crescent_order(window, errors):
    add_media(window)
    add_media(window)
    window.twVideo1.cellWidget(1, cfg.PLAYER_NUMBER_IDX).setCurrentText("3")
    window.pbSave.click()
    assert window.state == "refused"
    assert errors == ["Some player are not used. Please reorganize your media files"]


def test_ok(window, errors):
    add_media(window)
    window.pbSave.click()
    assert errors == []
    assert window.state == "accepted"
    assert window.result() == QDialog.DialogCode.Accepted
    assert window.pj == cfg.EMPTY_PROJECT


def test_cancel(window):
    add_media(window)
    window.pbCancel.click()
    assert window.result() == QDialog.DialogCode.Rejected
    assert window.pj == cfg.EMPTY_PROJECT


@pytest.mark.parametrize("media_file", ["geese1.mp4", "test.wav"])
def test_extract_wav(window, tmp_path, errors, media_file):
    add_media(window, media_file)
    window.cbVisualizeSpectrogram.setChecked(True)
    window.extract_wav()
    assert errors == []
    assert (tmp_path / f"{media_file}.wav").stat().st_size > 0
