"""
module for testing observation GUI
"""
import sys
import os
from PyQt5.QtCore import *

sys.path.append("../src")

import observation
import config


def test_no_media_loaded(qtbot):

    w = observation.Observation("/tmp")
    w.show()
    qtbot.addWidget(w)

    qtbot.mouseClick(w.pbSave, Qt.LeftButton)

    assert w.state == "refused"
    #assert w.exec_() == QDialog.Accepted
    # qtbot.keyPress(w, Qt.Key_Enter)


def test_no_obs_id(qtbot):

    w = observation.Observation("/tmp")
    w.show()
    qtbot.addWidget(w)
    w.ffmpeg_bin = "ffmpeg"

    media_file = "files/geese1.mp4"
    w.check_media("1", media_file, True)
    w.add_media_to_listview("1", media_file)

    qtbot.mouseClick(w.pbSave, Qt.LeftButton)

    assert w.state == "refused"


def test_file_not_media(qtbot):

    w = observation.Observation("/tmp")
    w.show()
    qtbot.addWidget(w)
    w.mode = "new"
    w.pj = config.EMPTY_PROJECT
    w.ffmpeg_bin = "ffmpeg"

    w.leObservationId.setText("test")
    media_file = "files/test.boris"
    assert w.check_media("1", media_file, True) == False


def test_ok(qtbot):

    w = observation.Observation("/tmp")
    w.show()
    qtbot.addWidget(w)
    w.mode = "new"
    w.pj = config.EMPTY_PROJECT
    w.ffmpeg_bin = "ffmpeg"

    media_file = "files/geese1.mp4"
    w.leObservationId.setText("test")
    w.check_media("1", media_file, True)
    w.add_media_to_listview("1", media_file)

    qtbot.mouseClick(w.pbSave, Qt.LeftButton)

    assert w.state == "accepted"

    assert w.pj == {'time_format': 'hh:mm:ss', 'project_date': '', 'project_name': '', 'project_description': '',
                    'project_format_version': config.project_format_version,
                    'subjects_conf': {}, 'behaviors_conf': {}, 'observations': {},
                    'behavioral_categories': [],
                    'independent_variables': {}, 'coding_map': {}, 'behaviors_coding_map': [], 'converters': {}}


def test_cancel(qtbot):

    w = observation.Observation("/tmp")
    w.show()
    qtbot.addWidget(w)
    w.mode = "new"
    w.pj = config.EMPTY_PROJECT
    w.ffmpeg_bin = "ffmpeg"

    media_file = "files/geese1.mp4"
    w.leObservationId.setText("test")
    w.check_media("1", media_file, True)
    w.add_media_to_listview("1", media_file)

    qtbot.mouseClick(w.pbCancel, Qt.LeftButton)

    assert w.pj == config.EMPTY_PROJECT



def test_extract_wav(qtbot):

    try:
        os.remove("/tmp/geese1.mp4.wav")
    except Exception:
        pass

    w = observation.Observation("/tmp")
    w.show()
    qtbot.addWidget(w)
    w.mode = "new"
    w.pj = config.EMPTY_PROJECT
    w.ffmpeg_bin = "ffmpeg"
    w.ffmpeg_cache_dir = "/tmp"

    media_file = "files/geese1.mp4"
    w.leObservationId.setText("test")
    w.check_media("1", media_file, True)
    w.add_media_to_listview("1", media_file)

    w.cbVisualizeSpectrogram.setChecked(True)
    w.extract_wav()

    assert os.path.isfile("/tmp/geese1.mp4.wav")

