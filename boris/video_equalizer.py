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
from .video_equalizer_ui import Ui_Equalizer


class Video_equalizer(QDialog, Ui_Equalizer):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUi(self)

        self.pb_close.clicked.connect(self.close)


'''
def show():
    widget = Video_equalizer()
    print(widget)
    widget.show()
    print("show")
'''

if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    w = Video_equalizer()
    w.show()
    sys.exit(app.exec_())
