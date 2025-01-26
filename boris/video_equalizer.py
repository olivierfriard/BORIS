"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2025 Olivier Friard

This file is part of BORIS.

  BORIS is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 3 of the License, or
  any later version.

  BORIS is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not see <http://www.gnu.org/licenses/>.

"""

from PySide6.QtWidgets import QDialog
from PySide6.QtCore import Signal, QEvent
from .video_equalizer_ui import Ui_Equalizer


class Video_equalizer(QDialog, Ui_Equalizer):
    """
    management of video equalizer: brightness, saturation, contrast, gamma and hue
    """

    sendEventSignal = Signal(int, str, int)
    sendKeyPressSignal = Signal(QEvent)

    def __init__(self, equalizer, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.equalizer = equalizer
        self.pb_close.clicked.connect(self.close)
        self.pb_reset.clicked.connect(self.reset)
        self.pb_reset_all.clicked.connect(self.reset_all)
        self.cb_player.currentIndexChanged.connect(self.player_changed)

        self.hs_brightness.valueChanged.connect(self.parameter_changed)
        self.hs_contrast.valueChanged.connect(self.parameter_changed)
        self.hs_saturation.valueChanged.connect(self.parameter_changed)
        self.hs_gamma.valueChanged.connect(self.parameter_changed)
        self.hs_hue.valueChanged.connect(self.parameter_changed)

        for n_player in self.equalizer:
            self.cb_player.addItem(f"Player {n_player + 1}")

        self.installEventFilter(self)

        self.initialize(0)

    def initialize(self, n_player: int) -> None:
        if n_player not in self.equalizer:
            return

        print(self.equalizer)

        self.hs_brightness.setValue(self.equalizer[n_player]["hs_brightness"])
        self.lb_brightness.setText(str(self.equalizer[n_player]["hs_brightness"]))

        self.hs_contrast.setValue(self.equalizer[n_player]["hs_contrast"])
        self.lb_contrast.setText(str(self.equalizer[n_player]["hs_contrast"]))

        self.hs_saturation.setValue(self.equalizer[n_player]["hs_saturation"])
        self.lb_saturation.setText(str(self.equalizer[n_player]["hs_saturation"]))

        self.hs_gamma.setValue(self.equalizer[n_player]["hs_gamma"])
        self.lb_gamma.setText(str(self.equalizer[n_player]["hs_gamma"]))

        self.hs_hue.setValue(self.equalizer[n_player]["hs_hue"])
        self.lb_hue.setText(str(self.equalizer[n_player]["hs_hue"]))

    def player_changed(self, index):
        self.initialize(index)

    def reset(self):
        """
        Reset value for all parameters to 0 for current player
        """
        for w in (self.hs_brightness, self.hs_contrast, self.hs_saturation, self.hs_gamma, self.hs_hue):
            w.setValue(0)

    def reset_all(self):
        """
        Reset value for all parameters to 0 for all players
        """

        for n_player in self.equalizer:
            for parameter in self.equalizer[n_player]:
                self.equalizer[n_player][parameter] = 0
                self.sendEventSignal.emit(n_player, parameter, 0)

    def parameter_changed(self):
        """
        Send signal when horizontal slider value changed
        """
        if self.cb_player.currentIndex() not in self.equalizer:
            return

        print(type(self.sender().value()))

        self.equalizer[self.cb_player.currentIndex()][self.sender().objectName()] = round(self.sender().value())
        self.sendEventSignal.emit(self.cb_player.currentIndex(), self.sender().objectName(), round(self.sender().value()))

        self.initialize(self.cb_player.currentIndex())

    def eventFilter(self, receiver, event):
        """
        send event (if keypress) to main window
        """
        if event.type() == QEvent.KeyPress:
            self.sendKeyPressSignal.emit(event)
            return True
        else:
            return False


def video_equalizer_show(self):
    """
    Video equalizer
    """

    def update_parameter(n_player, parameter, value):
        """
        update player parameter with value received by signal
        """
        if parameter == "hs_brightness":
            self.dw_player[n_player].player.brightness = value
        if parameter == "hs_contrast":
            self.dw_player[n_player].player.contrast = value
        if parameter == "hs_saturation":
            self.dw_player[n_player].player.saturation = value
        if parameter == "hs_gamma":
            self.dw_player[n_player].player.gamma = value
        if parameter == "hs_hue":
            self.dw_player[n_player].player.hue = value

    # send current parameters
    equalizer = {}
    for n_player, _ in enumerate(self.dw_player):
        equalizer[n_player] = {
            "hs_brightness": round(self.dw_player[n_player].player.brightness),
            "hs_contrast": round(self.dw_player[n_player].player.contrast),
            "hs_saturation": round(self.dw_player[n_player].player.saturation),
            "hs_gamma": round(self.dw_player[n_player].player.gamma),
            "hs_hue": round(self.dw_player[n_player].player.hue),
        }

    self.video_equalizer_wgt = Video_equalizer(equalizer)
    self.video_equalizer_wgt.sendEventSignal.connect(update_parameter)
    # send key press events received by widget to main window
    self.video_equalizer_wgt.sendKeyPressSignal.connect(self.signal_from_widget)

    self.video_equalizer_wgt.show()
