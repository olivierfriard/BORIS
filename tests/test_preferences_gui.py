"""
module for testing observation GUI


pytest -s -vv test_observation_gui.py
"""


import sys
import os
from PyQt5.QtCore import *

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from boris import preferences
from boris import config


def test_ok(qtbot):

    w = preferences.Preferences()

    qtbot.addWidget(w)
    
    def handle_dialog():
        qtbot.mouseClick(w.pbOK, Qt.LeftButton)

    QTimer.singleShot(1000, handle_dialog)

    r = w.exec_()
    assert r == 1


def test_cancel(qtbot):

    w = preferences.Preferences()

    qtbot.addWidget(w)
    
    def handle_dialog():
        qtbot.mouseClick(w.pbCancel, Qt.LeftButton)

    QTimer.singleShot(1000, handle_dialog)
    
    r = w.exec_()
    assert r == 0


def test_preferences_functions(qtbot):

    w = preferences.Preferences()
    w.rb_frames_mem_disk()
    w.reset_colors()

    qtbot.addWidget(w)
    
    def handle_dialog():
        qtbot.mouseClick(w.pbOK, Qt.LeftButton)

    QTimer.singleShot(1000, handle_dialog)

    r = w.exec_()
    assert r == 1

'''
def test_refresh_preferences(qtbot):

    w = preferences.Preferences()

    qtbot.addWidget(w)
    
    def handle_dialog():
        qtbot.keyClick(w.qm, Qt.Key_Enter)

    QTimer.singleShot(1000, handle_dialog)
    w.refresh_preferences()

    r = w.exec_()
    assert w.flag_refresh == True
'''

