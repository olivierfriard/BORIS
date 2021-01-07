"""
module for testing observation GUI


pytest -s -vv test_observation_gui.py
"""


import sys
import os
from PyQt5.QtCore import *

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from boris import observation
from boris import config

def test_no_media_loaded(qtbot):

    w = observation.Observation("/tmp")
    #w.show()

    qtbot.addWidget(w)

    def handle_dialog():
        qtbot.keyClick(w.qm, Qt.Key_Enter)

    QTimer.singleShot(1000, handle_dialog)

    qtbot.mouseClick(w.pbSave, Qt.LeftButton)

    assert w.state == "refused"


def test_no_obs_id(qtbot):

    w = observation.Observation("/tmp")
    #w.show()
    qtbot.addWidget(w)
    w.ffmpeg_bin = "ffmpeg"

    media_file = "files/geese1.mp4"
    w.check_media("1", media_file, True)
    w.add_media_to_listview("1", media_file)

    def handle_dialog():
        qtbot.keyClick(w.qm, Qt.Key_Enter)
        #qtbot.mouseClick(w.qm.Ok, Qt.LeftButton)

    QTimer.singleShot(1000, handle_dialog)

    qtbot.mouseClick(w.pbSave, Qt.LeftButton)

    assert w.state == "refused"


def test_file_not_media(qtbot):
    """
    test if the loaded file is a media file or not
    """

    w = observation.Observation("/tmp")
    w.show()
    qtbot.addWidget(w)
    w.mode = "new"
    w.pj = config.EMPTY_PROJECT
    w.ffmpeg_bin = "ffmpeg"

    w.leObservationId.setText("test")
    media_file = "files/test.boris"
    r, msg = w.check_media("1", media_file, True)
    assert r == False


def test_players_in_crescent_order(qtbot):
    """
    test if players are used in crescent order
    """

    w = observation.Observation("/tmp")
    #w.show()
    qtbot.addWidget(w)
    #w.mode = "new"
    w.pj = config.EMPTY_PROJECT
    w.ffmpeg_bin = "ffmpeg"

    #w.leObservationId.setText("test")
    media_file1 = "files/geese1.mp4"
    w.check_media("1", media_file1, True)
    #w.add_media_to_listview("1", media_file1)

    media_file2 = "files/geese1.mp4"
    w.check_media("1", media_file2, True)
    w.twVideo1.cellWidget(1, 0).setCurrentIndex(2)

    def handle_dialog():
        qtbot.keyClick(w.qm, Qt.Key_Enter)
        #qtbot.mouseClick(w.qm.Ok, Qt.LeftButton)

    QTimer.singleShot(1000, handle_dialog)

    qtbot.mouseClick(w.pbSave, Qt.LeftButton)

    assert w.state == "refused"


def test_ok(qtbot):

    w = observation.Observation("/tmp")
    #w.show()
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
    #w.show()
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



def test_extract_wav_from_video(qtbot):

    try:
        os.remove("/tmp/geese1.mp4.wav")
    except Exception:
        pass

    w = observation.Observation("/tmp")
    #w.show()
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


def test_extract_wav_from_wav(qtbot):

    w = observation.Observation("/tmp")

    #w.show()
    qtbot.addWidget(w)
    w.mode = "new"
    w.pj = config.EMPTY_PROJECT
    w.ffmpeg_bin = "ffmpeg"
    w.ffmpeg_cache_dir = "/tmp"

    media_file = "files/test.wav"
    w.leObservationId.setText("test")
    w.check_media("1", media_file, True)
    w.add_media_to_listview("1", media_file)

    w.cbVisualizeSpectrogram.setChecked(True)
    w.extract_wav()

    assert os.path.isfile("/tmp/test.wav.wav")

