"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2022 Olivier Friard

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

from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSignal, QEvent
from .video_equalizer_ui import Ui_Equalizer


class Video_equalizer(QDialog, Ui_Equalizer):
    """
    management of video equalizer: brightness, saturation, contrast, gamma and hue
    """

    sendEventSignal = pyqtSignal(int, str, int)

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

        self.initialize(0)

    def initialize(self, n_player):
        if n_player not in self.equalizer:
            return

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
        self.equalizer[self.cb_player.currentIndex()][self.sender().objectName()] = self.sender().value()
        self.sendEventSignal.emit(self.cb_player.currentIndex(), self.sender().objectName(), self.sender().value())

        self.initialize(self.cb_player.currentIndex())


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    w = Video_equalizer()
    w.show()
    sys.exit(app.exec_())
