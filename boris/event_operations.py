"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2023 Olivier Friard


  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
  MA 02110-1301, USA.

"""

import logging
from decimal import Decimal as dec
from decimal import InvalidOperation
from decimal import ROUND_DOWN
from typing import Union, Optional, List, Tuple, Dict

from . import config as cfg
from . import utilities as util
from . import dialog
from . import select_subj_behav
from . import select_modifiers
from .edit_event import DlgEditEvent, EditSelectedEvents

from PyQt5.QtWidgets import QMessageBox, QInputDialog, QLineEdit, QAbstractItemView, QApplication
from PyQt5.QtCore import QTime, Qt


def add_event(self):
    """
    manually add event to observation
    """

    if not self.observationId:
        self.no_observation()
        return

    if self.pause_before_addevent:
        # pause media
        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
            if self.playerType == cfg.MEDIA:
                memState = self.is_playing()
                if memState:
                    self.pause_video()

    if not self.pj[cfg.ETHOGRAM]:
        QMessageBox.warning(self, cfg.programName, "The ethogram is not set!")
        return

    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
        current_time = self.image_idx + 1
    else:
        current_time = self.getLaps()

    editWindow = DlgEditEvent(
        observation_type=self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE],
        time_value=0,
        image_idx=0,
        current_time=current_time,
        time_format=self.timeFormat,
        show_set_current_time=True,
    )
    editWindow.setWindowTitle("Add a new event")

    sortedSubjects = [""] + sorted([self.pj[cfg.SUBJECTS][x][cfg.SUBJECT_NAME] for x in self.pj[cfg.SUBJECTS]])

    editWindow.cobSubject.addItems(sortedSubjects)
    editWindow.cobSubject.setCurrentIndex(editWindow.cobSubject.findText(self.currentSubject, Qt.MatchFixedString))

    sortedCodes = sorted([self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] for x in self.pj[cfg.ETHOGRAM]])

    editWindow.cobCode.addItems(sortedCodes)

    if editWindow.exec_():  # button OK

        # MEDIA / LIVE
        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.MEDIA, cfg.LIVE):
            newTime = editWindow.time_widget.get_time()

            for idx in self.pj[cfg.ETHOGRAM]:
                if self.pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE] == editWindow.cobCode.currentText():

                    event = self.full_event(idx)

                    event[cfg.SUBJECT] = editWindow.cobSubject.currentText()
                    if editWindow.leComment.toPlainText():
                        event[cfg.COMMENT] = editWindow.leComment.toPlainText()

                    self.write_event(event, newTime)
                    break

            self.update_realtime_plot(force_plot=True)
            """
            if hasattr(self, "plot_events"):
                if not self.plot_events.visibleRegion().isEmpty():
                    self.plot_events.events_list = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]
                    self.plot_events.plot_events(float(self.getLaps()))
            """

            """
            # update subjects table
            self.currentStates = util.get_current_states_modifiers_by_subject(
                util.state_behavior_codes(self.pj[cfg.ETHOGRAM]),
                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS],
                dict(self.pj[cfg.SUBJECTS], **{"": {"name": ""}}),  # add no focal subject
                newTime,
                include_modifiers=True,
            )
            subject_idx = self.subject_name_index[self.currentSubject] if self.currentSubject else ""
            self.lbCurrentStates.setText(", ".join(self.currentStates[subject_idx]))
            self.show_current_states_in_subjects_table()
            """

        # IMAGES
        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
            new_index = editWindow.sb_image_idx.value()

            for idx in self.pj[cfg.ETHOGRAM]:
                if self.pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE] == editWindow.cobCode.currentText():

                    event = self.full_event(idx)

                    event[cfg.SUBJECT] = editWindow.cobSubject.currentText()
                    if editWindow.leComment.toPlainText():
                        event[cfg.COMMENT] = editWindow.leComment.toPlainText()

                    if self.playerType != cfg.VIEWER_IMAGES:
                        event[cfg.IMAGE_PATH] = self.images_list[new_index]
                    else:
                        event[cfg.IMAGE_PATH] = ""

                    event[cfg.IMAGE_INDEX] = new_index

                    time_ = dec("NaN")
                    if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.USE_EXIF_DATE, False):
                        if self.playerType != cfg.VIEWER_IMAGES:
                            if self.extract_exif_DateTimeOriginal(self.images_list[new_index]) != -1:
                                time_ = (
                                    self.extract_exif_DateTimeOriginal(self.images_list[new_index])
                                    - self.image_time_ref
                                )

                    elif self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.TIME_LAPSE, 0):
                        time_ = new_index * self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.TIME_LAPSE, 0)

                    self.write_event(event, dec(time_).quantize(dec("0.001"), rounding=ROUND_DOWN))

                    break

    if self.pause_before_addevent:
        # restart media
        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA and self.playerType == cfg.MEDIA:
            if memState:
                self.play_video()


def find_events(self):
    """
    find in events
    """

    self.find_dialog = dialog.FindInEvents()
    # list of rows to find
    self.find_dialog.rowsToFind = set([item.row() for item in self.twEvents.selectedIndexes()])
    self.find_dialog.currentIdx = -1
    self.find_dialog.clickSignal.connect(self.click_signal_find_in_events)
    self.find_dialog.setWindowFlags(Qt.WindowStaysOnTopHint)
    self.find_dialog.show()


def filter_events(self):
    """
    filter coded events and subjects
    """

    parameters = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selected_observations=[],  # empty selection of observations for selecting all subjects and behaviors
        start_coding=dec("NaN"),
        end_coding=dec("NaN"),
        maxTime=None,
        flagShowIncludeModifiers=False,
        flagShowExcludeBehaviorsWoEvents=False,
        by_category=False,
    )
    if parameters == {}:
        return

    self.filtered_subjects = parameters[cfg.SELECTED_SUBJECTS][:]
    if cfg.NO_FOCAL_SUBJECT in self.filtered_subjects:
        self.filtered_subjects.append("")
    self.filtered_behaviors = parameters[cfg.SELECTED_BEHAVIORS][:]

    logging.debug(f"self.filtered_behaviors: {self.filtered_behaviors}")

    self.load_tw_events(self.observationId)
    self.dwEvents.setWindowTitle(f"Events for “{self.observationId}” observation (filtered)")


def show_all_events(self) -> None:
    """
    show all events (disable filter)
    """
    self.filtered_subjects = []
    self.filtered_behaviors = []
    self.load_tw_events(self.observationId)
    self.dwEvents.setWindowTitle(f"Events for “{self.observationId}” observation")


def fill_events_undo_list(self, operation_description: str) -> None:
    """
    fill the undo events list for Undo function (CTRL + Z)
    """
    self.undo_queue.append(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][:])
    self.undo_description.append(operation_description)

    self.actionUndo.setText(operation_description)
    self.actionUndo.setEnabled(True)

    logging.debug(f"{operation_description} added to undo events list")

    if len(self.undo_queue) > cfg.MAX_UNDO_QUEUE:
        self.undo_queue.popleft()
        self.undo_description.popleft()
        logging.debug(f"Max events undo ")


def undo_event_operation(self) -> None:
    """
    undo operation on event(s)
    """
    if len(self.undo_queue) == 0:
        self.statusbar.showMessage(f"The Undo buffer is empty", 5000)
        return
    events = self.undo_queue.pop()
    operation_description = self.undo_description.pop()
    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS] = events[:]
    self.project_changed()

    self.statusbar.showMessage(operation_description, 5000)

    logging.debug(operation_description)

    # reload all events in tw
    self.load_tw_events(self.observationId)

    self.update_realtime_plot(force_plot=True)

    if not len(self.undo_queue):
        self.actionUndo.setText("Undo")
        self.actionUndo.setEnabled(False)
    else:
        self.actionUndo.setText(self.undo_description[-1])


def delete_all_events(self):
    """
    delete all (filtered) events in current observation
    """

    if not self.observationId:
        self.no_observation()
        return

    if not self.twEvents.rowCount():
        QMessageBox.warning(self, cfg.programName, "No events to delete")
        return

    if (
        dialog.MessageDialog(
            cfg.programName,
            ("Confirm the deletion of all (filtered) events in the current observation?<br>" "Filters do not apply!"),
            [cfg.YES, cfg.NO],
        )
        == cfg.YES
    ):

        # fill the undo list
        fill_events_undo_list(self, "Undo 'Delete all events'")

        rows_to_delete: list = []
        for row in range(self.twEvents.rowCount()):
            rows_to_delete.append(
                self.twEvents.item(row, cfg.TW_OBS_FIELD[self.playerType][cfg.TIME]).data(Qt.UserRole)
            )

        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS] = [
            event
            for event_idx, event in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS])
            if event_idx not in rows_to_delete
        ]

        self.update_realtime_plot(force_plot=True)

        self.project_changed()
        self.load_tw_events(self.observationId)


def delete_selected_events(self):
    """
    delete selected events
    """

    if not self.observationId:
        self.no_observation()
        return

    logging.debug("begin function delete_selected_events")

    if not self.twEvents.selectedIndexes():
        QMessageBox.warning(self, cfg.programName, "No event selected!")
    else:
        # list of rows to delete (set for unique)
        # fill the undo list
        fill_events_undo_list(self, "Undo 'Delete selected events'")

        rows_to_delete: list = []
        for row in set([item.row() for item in self.twEvents.selectedIndexes()]):
            rows_to_delete.append(
                self.twEvents.item(row, cfg.TW_OBS_FIELD[self.playerType][cfg.TIME]).data(Qt.UserRole)
            )

        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS] = [
            event
            for event_idx, event in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS])
            if event_idx not in rows_to_delete
        ]

        self.update_realtime_plot(force_plot=True)

        self.project_changed()
        self.load_tw_events(self.observationId)


def select_events_between_activated(self):
    """
    select events between a time interval
    """

    def parseTime(txt):
        """
        parse time in string (should be 00:00:00.000 or in seconds)
        """
        if ":" in txt:
            qtime = QTime.fromString(txt, "hh:mm:ss.zzz")

            if qtime.toString():
                timeSeconds = util.time2seconds(qtime.toString("hh:mm:ss.zzz"))
            else:
                return None
        else:
            try:
                timeSeconds = dec(txt)
            except InvalidOperation:
                return None
        return timeSeconds

    if not self.twEvents.rowCount():
        QMessageBox.warning(self, cfg.programName, "There are no events to select")
        return

    text, ok = QInputDialog.getText(
        self,
        "Select events in time interval",
        "Interval: (example: 12.5-14.7 or 02:45.780-03:15.120)",
        QLineEdit.Normal,
        "",
    )

    if ok and text != "":

        if "-" not in text:
            QMessageBox.critical(self, cfg.programName, "Use minus sign (-) to separate initial value from final value")
            return

        while " " in text:
            text = text.replace(" ", "")

        from_, to_ = text.split("-")[0:2]
        from_sec = parseTime(from_)
        if not from_sec:
            QMessageBox.critical(self, cfg.programName, f"Time value not recognized: {from_}")
            return
        to_sec = parseTime(to_)
        if not to_sec:
            QMessageBox.critical(self, cfg.programName, f"Time value not recognized: {to_}")
            return
        if to_sec < from_sec:
            QMessageBox.critical(self, cfg.programName, "The initial time is greater than the final time")
            return
        self.twEvents.clearSelection()
        self.twEvents.setSelectionMode(QAbstractItemView.MultiSelection)
        for r in range(self.twEvents.rowCount()):
            if ":" in self.twEvents.item(r, cfg.TW_EVENTS_FIELDS[self.playerType][cfg.TIME]).text():
                time = util.time2seconds(self.twEvents.item(r, cfg.TW_EVENTS_FIELDS[self.playerType][cfg.TIME]).text())
            else:
                time = dec(self.twEvents.item(r, cfg.TW_EVENTS_FIELDS[self.playerType][cfg.TIME]).text())
            if from_sec <= time <= to_sec:
                self.twEvents.selectRow(r)


def edit_selected_events(self):
    """
    edit one or more selected events for subject, behavior and/or comment
    """
    # list of rows to edit
    twEvents_rows_to_edit = set([item.row() for item in self.twEvents.selectedIndexes()])

    if not len(twEvents_rows_to_edit):
        QMessageBox.warning(self, cfg.programName, "No event selected!")
    elif len(twEvents_rows_to_edit) == 1:  # 1 event selected
        edit_event(self)
    else:  # editing of more events
        dialogWindow = EditSelectedEvents()
        dialogWindow.all_behaviors = sorted(
            [self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] for x in self.pj[cfg.ETHOGRAM]]
        )

        dialogWindow.all_subjects = [
            self.pj[cfg.SUBJECTS][str(k)][cfg.SUBJECT_NAME]
            for k in sorted([int(x) for x in self.pj[cfg.SUBJECTS].keys()])
        ]

        if dialogWindow.exec_():

            # fill the undo list
            fill_events_undo_list(self, "Undo 'Edit selected event(s)'")

            tsb_to_edit: list = []
            for row in twEvents_rows_to_edit:
                tsb_to_edit.append(
                    self.twEvents.item(row, cfg.TW_OBS_FIELD[self.playerType][cfg.TIME]).data(Qt.UserRole)
                )
                """
                tsb_to_edit.append(
                    [
                        util.time2seconds(self.read_tw_event_field(row, self.playerType, cfg.TIME))
                        if self.timeFormat == cfg.HHMMSS
                        else dec(self.read_tw_event_field(row, self.playerType, cfg.TIME)),
                        self.read_tw_event_field(row, self.playerType, cfg.SUBJECT),
                        self.read_tw_event_field(row, self.playerType, cfg.BEHAVIOR_CODE),
                    ]
                )
                """

            behavior_codes = []
            modifiers_mem = []
            mem_event_idx = []
            for idx, event in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]):
                if idx in tsb_to_edit:

                    new_event = list(event)
                    if dialogWindow.rbSubject.isChecked():
                        new_event[cfg.EVENT_SUBJECT_FIELD_IDX] = dialogWindow.newText.selectedItems()[0].text()
                    if dialogWindow.rbBehavior.isChecked():
                        new_event[cfg.EVENT_BEHAVIOR_FIELD_IDX] = dialogWindow.newText.selectedItems()[0].text()
                    if dialogWindow.rbComment.isChecked():
                        new_event[cfg.EVENT_COMMENT_FIELD_IDX] = dialogWindow.commentText.text()

                    if new_event[cfg.EVENT_BEHAVIOR_FIELD_IDX] not in behavior_codes:
                        behavior_codes.append(new_event[cfg.EVENT_BEHAVIOR_FIELD_IDX])

                    if new_event[cfg.EVENT_MODIFIER_FIELD_IDX] not in modifiers_mem:
                        modifiers_mem.append(new_event[cfg.EVENT_MODIFIER_FIELD_IDX])

                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][idx] = list(new_event)
                    mem_event_idx.append(idx)
                    self.project_changed()

            # check if behavior is unique for editing modifiers
            if len(behavior_codes) == 1:

                # get behavior index
                for idx in self.pj[cfg.ETHOGRAM]:
                    if self.pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE] == behavior_codes[0]:
                        break
                else:
                    return

                event = self.full_event(idx)

                if len(modifiers_mem) == 1:
                    current_modifier = modifiers_mem[0]
                else:
                    current_modifier = ""

                if event["modifiers"]:
                    modifiers_selector = select_modifiers.ModifiersList(
                        behavior_codes[0], eval(str(event["modifiers"])), current_modifier
                    )

                    r = modifiers_selector.exec_()
                    if r:
                        selected_modifiers = modifiers_selector.get_modifiers()

                        modifier_str = ""
                        for idx1 in util.sorted_keys(selected_modifiers):
                            if modifier_str:
                                modifier_str += "|"
                            if selected_modifiers[idx1]["type"] in (cfg.SINGLE_SELECTION, cfg.MULTI_SELECTION):
                                modifier_str += ",".join(selected_modifiers[idx1].get("selected", ""))
                            if selected_modifiers[idx1]["type"] in (cfg.NUMERIC_MODIFIER, cfg.EXTERNAL_DATA_MODIFIER):
                                modifier_str += selected_modifiers[idx1].get("selected", "NA")

                else:  # delete current modifier(s)
                    modifier_str = ""

                # set new modifier
                for idx, event in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]):
                    if idx in mem_event_idx:
                        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][idx][
                            cfg.EVENT_MODIFIER_FIELD_IDX
                        ] = modifier_str

            self.load_tw_events(self.observationId)

            self.update_realtime_plot(force_plot=True)


def edit_event(self):
    """
    edit event corresponding to the selected row in twEvents
    """

    if not self.observationId:
        self.no_observation()
        return

    if not self.twEvents.selectedItems():
        QMessageBox.warning(self, cfg.programName, "Select an event to edit")
        return

    twEvents_row = self.twEvents.selectedItems()[0].row()

    pj_event_idx = self.twEvents.item(twEvents_row, cfg.TW_OBS_FIELD[self.playerType][cfg.TIME]).data(Qt.UserRole)

    time_value = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][pj_event_idx][
        cfg.PJ_OBS_FIELDS[self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE]][cfg.TIME]
    ]

    image_idx = None
    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.IMAGES):
        image_idx = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][pj_event_idx][
            cfg.PJ_OBS_FIELDS[self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE]][cfg.IMAGE_INDEX]
        ]

    """
    elif self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.LIVE, cfg.MEDIA):
        value = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][pj_event_idx][
            cfg.PJ_OBS_FIELDS[self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE]][cfg.TIME]
        ]
    else:
        QMessageBox.warning(
            self,
            cfg.programName,
            f"Observation type {self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE]} not recognized",
        )
        return
    """

    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
        current_value = self.image_idx + 1
    else:
        current_value = self.getLaps()

    editWindow = DlgEditEvent(
        observation_type=self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE],
        time_value=time_value,
        image_idx=image_idx,
        current_time=current_value,
        time_format=self.timeFormat,
        show_set_current_time=True,
    )
    editWindow.setWindowTitle("Edit event")

    sortedSubjects = [""] + sorted([self.pj[cfg.SUBJECTS][x][cfg.SUBJECT_NAME] for x in self.pj[cfg.SUBJECTS]])

    editWindow.cobSubject.addItems(sortedSubjects)

    if (
        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][pj_event_idx][cfg.EVENT_SUBJECT_FIELD_IDX]
        in sortedSubjects
    ):
        editWindow.cobSubject.setCurrentIndex(
            sortedSubjects.index(
                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][pj_event_idx][cfg.EVENT_SUBJECT_FIELD_IDX]
            )
        )
    else:
        QMessageBox.warning(
            self,
            cfg.programName,
            (
                f"The subject <b>{self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][pj_event_idx][cfg.EVENT_SUBJECT_FIELD_IDX]}</b> "
                "does not exist more in the subject's list"
            ),
        )
        editWindow.cobSubject.setCurrentIndex(0)

    sortedCodes = sorted([self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] for x in self.pj[cfg.ETHOGRAM]])
    editWindow.cobCode.addItems(sortedCodes)

    # check if selected code is in code's list (no modification of codes)
    if (
        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][pj_event_idx][cfg.EVENT_BEHAVIOR_FIELD_IDX]
        in sortedCodes
    ):
        editWindow.cobCode.setCurrentIndex(
            sortedCodes.index(
                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][pj_event_idx][cfg.EVENT_BEHAVIOR_FIELD_IDX]
            )
        )
    else:
        logging.warning(
            (
                f"The behaviour {self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][pj_event_idx][cfg.EVENT_BEHAVIOR_FIELD_IDX]} "
                "does not exist more in the ethogram"
            )
        )
        QMessageBox.warning(
            self,
            cfg.programName,
            (
                f"The behaviour <b>{self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][pj_event_idx][cfg.EVENT_BEHAVIOR_FIELD_IDX]}</b> "
                "does not exist more in the ethogram"
            ),
        )
        editWindow.cobCode.setCurrentIndex(0)

    logging.debug(
        f"original modifiers: {self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][pj_event_idx][cfg.EVENT_MODIFIER_FIELD_IDX]}"
    )

    # frame index
    frame_idx = read_event_field(
        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][pj_event_idx],
        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE],
        cfg.FRAME_INDEX,
    )
    editWindow.sb_frame_idx.setValue(0 if frame_idx in (cfg.NA, None) else frame_idx)
    if frame_idx in (cfg.NA, None):
        editWindow.cb_set_frame_idx_na.setChecked(True)

    # comment
    editWindow.leComment.setPlainText(
        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][pj_event_idx][cfg.EVENT_COMMENT_FIELD_IDX]
    )

    flag_ok = False  # for looping until event is OK or Cancel pressed
    while True:
        if editWindow.exec_():  # button OK

            self.project_changed()

            # MEDIA / LIVE
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.MEDIA, cfg.LIVE):

                new_time = editWindow.time_widget.get_time()
                for key in self.pj[cfg.ETHOGRAM]:
                    if self.pj[cfg.ETHOGRAM][key][cfg.BEHAVIOR_CODE] == editWindow.cobCode.currentText():
                        event = self.full_event(key)
                        event[cfg.SUBJECT] = editWindow.cobSubject.currentText()
                        event[cfg.COMMENT] = editWindow.leComment.toPlainText()

                        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
                            if editWindow.sb_frame_idx.value():
                                event[cfg.FRAME_INDEX] = editWindow.sb_frame_idx.value()
                            else:
                                event[cfg.FRAME_INDEX] = cfg.NA

                        event["row"] = pj_event_idx
                        event["original_modifiers"] = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][
                            pj_event_idx
                        ][cfg.PJ_OBS_FIELDS[self.playerType][cfg.MODIFIER]]

                        r = self.write_event(event, new_time)
                        if r == 1:  # same event already present
                            continue
                        if not r:
                            flag_ok = True
                        break

                self.update_realtime_plot(force_plot=True)

            # IMAGES
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
                new_index = editWindow.sb_image_idx.value()

                for key in self.pj[cfg.ETHOGRAM]:
                    if self.pj[cfg.ETHOGRAM][key][cfg.BEHAVIOR_CODE] == editWindow.cobCode.currentText():
                        event = self.full_event(key)
                        if editWindow.time_value != cfg.NA:
                            event[cfg.TIME] = editWindow.time_widget.get_time()
                        else:
                            event[cfg.TIME] = dec(cfg.NA)
                        event[cfg.SUBJECT] = editWindow.cobSubject.currentText()
                        event[cfg.COMMENT] = editWindow.leComment.toPlainText()
                        event["row"] = pj_event_idx
                        event["original_modifiers"] = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][
                            pj_event_idx
                        ][cfg.PJ_OBS_FIELDS[self.playerType][cfg.MODIFIER]]

                        # not editable yet. Read previous value
                        event[cfg.IMAGE_PATH] = read_event_field(
                            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][pj_event_idx],
                            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE],
                            cfg.IMAGE_PATH,
                        )

                        """
                        try:
                            event[cfg.IMAGE_PATH] = self.images_list[new_index]
                        except IndexError:
                            event[cfg.IMAGE_PATH] = ""
                        """
                        event[cfg.IMAGE_INDEX] = new_index

                        """
                        time_ = dec("NaN")
                        if (
                            self.playerType != cfg.VIEWER_IMAGES
                            and self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.USE_EXIF_DATE, False)
                            and self.extract_exif_DateTimeOriginal(self.images_list[new_index]) != -1
                        ):
                            time_ = (
                                self.extract_exif_DateTimeOriginal(self.images_list[new_index]) - self.image_time_ref
                            )

                        elif self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.TIME_LAPSE, 0):
                            time_ = new_index * self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.TIME_LAPSE, 0)
                        """

                        r = self.write_event(event, event[cfg.TIME].quantize(dec("0.001"), rounding=ROUND_DOWN))

                        if r == 1:  # same event already present
                            continue
                        if not r:
                            flag_ok = True

                        break

        else:  # Cancel button
            flag_ok = True

        if flag_ok:
            break


def edit_time_selected_events(self):
    """
    edit time of one or more selected events
    """
    # list of rows to edit
    twEvents_rows_to_shift = set([item.row() for item in self.twEvents.selectedIndexes()])

    if not len(twEvents_rows_to_shift):
        QMessageBox.warning(self, cfg.programName, "No event selected!")
        return

    d, ok = QInputDialog.getDouble(
        self, "Time value", "Value to add or substract (use negative value):", 0, -86400, 86400, 3
    )
    if ok and d:
        if (
            dialog.MessageDialog(
                cfg.programName,
                (
                    f"Confirm the {'addition' if d > 0 else 'subtraction'} of {abs(d)} seconds "
                    "to all selected events in the current observation?"
                ),
                [cfg.YES, cfg.NO],
            )
            == cfg.NO
        ):
            return

        # fill the undo list
        fill_events_undo_list(self, "Undo 'Edit time'")

        for tw_event_idx in twEvents_rows_to_shift:
            pj_event_idx = self.twEvents.item(tw_event_idx, cfg.TW_OBS_FIELD[self.playerType][cfg.TIME]).data(
                Qt.UserRole
            )
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][pj_event_idx][
                cfg.PJ_OBS_FIELDS[self.playerType][cfg.TIME]
            ] += dec(f"{d:.3f}")
            self.project_changed()

        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS] = sorted(
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]
        )
        self.load_tw_events(self.observationId)

        self.update_realtime_plot(force_plot=True)


'''
def copy_selected_events(self):
    """
    copy selected events to clipboard
    """
    twEvents_rows_to_copy = set([item.row() for item in self.twEvents.selectedIndexes()])
    if not len(twEvents_rows_to_copy):
        QMessageBox.warning(self, cfg.programName, "No event selected!")
        return

    tsb_to_copy: list = []
    for row in twEvents_rows_to_copy:
        tsb_to_copy.append(self.twEvents.item(row, cfg.TW_OBS_FIELD[self.playerType][cfg.TIME]).data(Qt.UserRole))

    copied_events: list = []
    for idx, event in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]):
        if idx in tsb_to_copy:
            copied_events.append("\t".join([str(x) for x in event]))

    cb = QApplication.clipboard()
    cb.clear(mode=cb.Clipboard)
    cb.setText("\n".join(copied_events), mode=cb.Clipboard)
'''


def copy_selected_events(self):
    """
    copy selected events from project to clipboard
    """

    logging.debug("Copy selected events to clipboard")

    twEvents_rows_to_copy = set([item.row() for item in self.twEvents.selectedIndexes()])
    if not len(twEvents_rows_to_copy):
        QMessageBox.warning(self, cfg.programName, "No event selected!")
        return

    pj_event_idx_to_copy: list = []
    for row in twEvents_rows_to_copy:
        pj_event_idx_to_copy.append(
            self.twEvents.item(row, cfg.TW_OBS_FIELD[self.playerType][cfg.TIME]).data(Qt.UserRole)
        )

    copied_events: list = []
    for idx, event in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]):
        if idx in pj_event_idx_to_copy:
            copied_events.append("\t".join([str(x) for x in event]))

    cb = QApplication.clipboard()
    cb.clear(mode=cb.Clipboard)
    cb.setText("\n".join(copied_events), mode=cb.Clipboard)

    logging.debug("Selected events copied in clipboard")


def paste_clipboard_to_events(self):
    """
    paste clipboard to events
    """

    cb = QApplication.clipboard()
    cb_text = cb.text()
    cb_text_splitted = cb_text.split("\n")
    length: list = []
    content: list = []
    for l in cb_text_splitted:
        length.append(len(l.split("\t")))
        content.append(l.split("\t"))

    if set(length) != set([len(cfg.PJ_EVENTS_FIELDS[self.playerType])]):
        QMessageBox.warning(
            self,
            cfg.programName,
            (
                "The clipboard does not contain events!\n"
                f"For an observation from <b>{self.playerType}</b> "
                f"the events must be organized in {len(cfg.PJ_EVENTS_FIELDS[self.playerType])} columns separated by TAB character"
            ),
        )
        return

    for event in content:
        event[cfg.EVENT_TIME_FIELD_IDX] = dec(event[cfg.EVENT_TIME_FIELD_IDX])
        # skip if event already present
        if event in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]:
            continue

        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].append(event)

        self.project_changed()

    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS] = sorted(
        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]
    )
    self.load_tw_events(self.observationId)

    self.update_realtime_plot(force_plot=True)


def read_event_field(event: list, player_type: str, field_type: str) -> Union[str, None, int, dec]:
    """
    return value of field for event or NA if not available
    """
    if field_type not in cfg.PJ_EVENTS_FIELDS[player_type]:
        return None
    if cfg.PJ_OBS_FIELDS[player_type][field_type] < len(event):
        return event[cfg.PJ_OBS_FIELDS[player_type][field_type]]
    else:
        return cfg.NA
