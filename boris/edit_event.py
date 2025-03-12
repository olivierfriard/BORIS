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

from decimal import Decimal as dec
import math

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)

from . import config as cfg
from . import dialog
from .edit_event_ui import Ui_Form


class DlgEditEvent(QDialog, Ui_Form):
    def __init__(
        self,
        observation_type: str,
        time_value: dec = dec(0),
        image_idx=None,
        current_time=0,
        time_format: str = cfg.S,
        show_set_current_time: bool = False,
        parent=None,
    ):
        super().__init__(parent)
        self.setupUi(self)
        self.time_value = time_value
        self.image_idx = image_idx
        self.observation_type = observation_type

        self.pb_set_to_current_time.setVisible(show_set_current_time)
        self.current_time = current_time

        # hide image index
        if observation_type in (cfg.LIVE, cfg.MEDIA):
            for w in (self.lb_image_idx, self.sb_image_idx, self.cb_set_time_na, self.pb_set_to_current_image_index):
                w.setVisible(False)
            # hide frame index because frame index is automatically extracted
            for w in (self.lb_frame_idx, self.sb_frame_idx, self.cb_set_frame_idx_na):
                w.setVisible(False)

        if (observation_type in (cfg.LIVE, cfg.MEDIA)) or (observation_type == cfg.IMAGES and not math.isnan(self.time_value)):
            self.time_widget = dialog.get_time_widget(self.time_value)

            if time_format == cfg.S:
                self.time_widget.rb_seconds.setChecked(True)
            if time_format == cfg.HHMMSS:
                self.time_widget.rb_time.setChecked(True)
            if self.time_value > cfg.DATE_CUTOFF:
                self.time_widget.rb_datetime.setChecked(True)

            self.horizontalLayout_2.insertWidget(0, self.time_widget)

        if observation_type == cfg.IMAGES:
            self.time_widget = dialog.get_time_widget(self.time_value)
            # hide frame index widgets
            for w in (self.lb_frame_idx, self.sb_frame_idx, self.cb_set_frame_idx_na, self.pb_set_to_current_time):
                w.setVisible(False)
            self.sb_image_idx.setValue(self.image_idx)

            # self.pb_set_to_current_time.setText("Set to current image index")

        self.pb_set_to_current_time.clicked.connect(self.set_to_current_time)
        self.pb_set_to_current_image_index.clicked.connect(self.set_to_current_image_index)

        self.cb_set_time_na.stateChanged.connect(self.time_na)

        self.cb_set_frame_idx_na.stateChanged.connect(self.frame_idx_na)
        self.pbOK.clicked.connect(self.close_widget)
        self.pbCancel.clicked.connect(self.reject)

    def close_widget(self):
        """
        close the widget
        """
        if self.observation_type in (cfg.IMAGES):
            if self.sb_image_idx.value() == 0:
                QMessageBox.warning(self, cfg.programName, "The image index cannot be null")
                return
        self.accept()

    def set_to_current_image_index(self):
        """
        set image index to current image index
        """
        if self.observation_type in (cfg.IMAGES):
            self.sb_image_idx.setValue(int(self.current_time))

    def set_to_current_time(self):
        """
        set time to current media time
        """
        if self.observation_type in (cfg.LIVE, cfg.MEDIA):
            self.time_widget.set_time(dec(float(self.current_time)))

    def frame_idx_na(self):
        """
        set/unset frame index NA
        """
        self.lb_frame_idx.setEnabled(not self.cb_set_frame_idx_na.isChecked())
        self.sb_frame_idx.setEnabled(not self.cb_set_frame_idx_na.isChecked())

    def time_na(self):
        """
        set/unset time to NA
        """

        self.time_widget.setEnabled(not self.cb_set_time_na.isChecked())
        self.pb_set_to_current_time.setEnabled(not self.cb_set_time_na.isChecked())


class EditSelectedEvents(QDialog):
    """
    "edit selected events" dialog box
    """

    def __init__(self):
        super(EditSelectedEvents, self).__init__()

        self.setWindowTitle("Edit selected events")

        hbox = QVBoxLayout(self)

        self.rbSubject = QRadioButton("Subject")
        self.rbSubject.setChecked(False)
        self.rbSubject.toggled.connect(self.rb_changed)
        hbox.addWidget(self.rbSubject)

        self.rbBehavior = QRadioButton("Behavior")
        self.rbBehavior.setChecked(False)
        self.rbBehavior.toggled.connect(self.rb_changed)
        hbox.addWidget(self.rbBehavior)

        self.lb = QLabel("New value")
        hbox.addWidget(self.lb)
        self.newText = QListWidget(self)
        hbox.addWidget(self.newText)

        self.rbComment = QRadioButton("Comment")
        self.rbComment.setChecked(False)
        self.rbComment.toggled.connect(self.rb_changed)
        hbox.addWidget(self.rbComment)

        self.lbComment = QLabel("New comment")
        hbox.addWidget(self.lbComment)

        self.commentText = QLineEdit()
        hbox.addWidget(self.commentText)

        hbox2 = QHBoxLayout(self)
        self.pbOK = QPushButton("OK")
        self.pbOK.clicked.connect(self.pbOK_clicked)
        self.pbCancel = QPushButton("Cancel")
        self.pbCancel.clicked.connect(self.pbCancel_clicked)
        hbox2.addWidget(self.pbCancel)
        hbox2.addWidget(self.pbOK)
        hbox.addLayout(hbox2)

        self.setLayout(hbox)

    def rb_changed(self):
        self.newText.setEnabled(not self.rbComment.isChecked())
        self.commentText.setEnabled(self.rbComment.isChecked())

        if self.rbSubject.isChecked():
            self.newText.clear()
            self.newText.addItems(self.all_subjects)

        if self.rbBehavior.isChecked():
            self.newText.clear()
            self.newText.addItems(self.all_behaviors)

        if self.rbComment.isChecked():
            self.newText.clear()

    def pbOK_clicked(self):
        """
        if not self.rbSubject.isChecked() and not self.rbBehavior.isChecked() and not self.rbComment.isChecked():
            QMessageBox.warning(
                None,
                cfg.programName,
                "You must select a field to be edited",
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            return
        """

        if (self.rbSubject.isChecked() or self.rbBehavior.isChecked()) and self.newText.selectedItems() == []:
            QMessageBox.warning(
                None,
                cfg.programName,
                "You must select a new value from the list",
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            return

        self.accept()

    def pbCancel_clicked(self):
        """
        Cancel editing
        """
        self.reject()
