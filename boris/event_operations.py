"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2022 Olivier Friard


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
from decimal import Decimal
from . import config as cfg
from . import utilities as util
from . import dialog
from .edit_event import DlgEditEvent, EditSelectedEvents

from PyQt5.QtWidgets import QMessageBox, QInputDialog, QLineEdit, QAbstractItemView
from PyQt5.QtCore import QTime


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

    if (dialog.MessageDialog(
            cfg.programName,
        ("Confirm the deletion of all (filtered) events in the current observation?<br>"
         "Filters do not apply!"),
        [cfg.YES, cfg.NO],
    ) == cfg.YES):
        rows_to_delete = []
        for row in range(self.twEvents.rowCount()):
            rows_to_delete.append([
                util.time2seconds(self.twEvents.item(row, cfg.EVENT_TIME_FIELD_IDX).text())
                if self.timeFormat == cfg.HHMMSS else Decimal(self.twEvents.item(row, cfg.EVENT_TIME_FIELD_IDX).text()),
                self.twEvents.item(row, cfg.EVENT_SUBJECT_FIELD_IDX).text(),
                self.twEvents.item(row, cfg.EVENT_BEHAVIOR_FIELD_IDX).text(),
            ])

        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS] = [
            event for idx, event in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]) if [
                event[cfg.EVENT_TIME_FIELD_IDX], event[cfg.EVENT_SUBJECT_FIELD_IDX], event[cfg.EVENT_BEHAVIOR_FIELD_IDX]
            ] not in rows_to_delete
        ]

        self.projectChanged = True
        self.loadEventsInTW(self.observationId)


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
        try:
            rows_to_delete = []
            for row in set([item.row() for item in self.twEvents.selectedIndexes()]):
                rows_to_delete.append([
                    util.time2seconds(self.twEvents.item(row, cfg.EVENT_TIME_FIELD_IDX).text()) if self.timeFormat
                    == cfg.HHMMSS else Decimal(self.twEvents.item(row, cfg.EVENT_TIME_FIELD_IDX).text()),
                    self.twEvents.item(row, cfg.EVENT_SUBJECT_FIELD_IDX).text(),
                    self.twEvents.item(row, cfg.EVENT_BEHAVIOR_FIELD_IDX).text(),
                ])

            # logging.debug(f"rows to delete: {rows_to_delete}")

            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS] = [
                event for idx, event in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]) if [
                    event[cfg.EVENT_TIME_FIELD_IDX], event[cfg.EVENT_SUBJECT_FIELD_IDX], event[
                        cfg.EVENT_BEHAVIOR_FIELD_IDX]
                ] not in rows_to_delete
            ]

            self.projectChanged = True
            self.loadEventsInTW(self.observationId)

        except Exception:
            logging.critical("Critical error during event deletion")
            QMessageBox.critical(self, cfg.programName, "Problem during event deletion")


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
                timeSeconds = Decimal(txt)
            except InvalidOperation:
                return None
        return timeSeconds

    if self.twEvents.rowCount():
        text, ok = QInputDialog.getText(
            self,
            "Select events in time interval",
            "Interval: (example: 12.5-14.7 or 02:45.780-03:15.120)",
            QLineEdit.Normal,
            "",
        )

        if ok and text != "":

            if "-" not in text:
                QMessageBox.critical(self, cfg.programName,
                                     "Use minus sign (-) to separate initial value from final value")
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
            for r in range(0, self.twEvents.rowCount()):
                if ":" in self.twEvents.item(r, 0).text():
                    time = util.time2seconds(self.twEvents.item(r, 0).text())
                else:
                    time = Decimal(self.twEvents.item(r, 0).text())
                if from_sec <= time <= to_sec:
                    self.twEvents.selectRow(r)

    else:
        QMessageBox.warning(self, cfg.programName, "There are no events to select")


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
            [self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] for x in self.pj[cfg.ETHOGRAM]])

        dialogWindow.all_subjects = [
            self.pj[cfg.SUBJECTS][str(k)][cfg.SUBJECT_NAME]
            for k in sorted([int(x) for x in self.pj[cfg.SUBJECTS].keys()])
        ]

        if dialogWindow.exec_():

            tsb_to_edit = []
            for row in twEvents_rows_to_edit:
                tsb_to_edit.append([
                    util.time2seconds(self.twEvents.item(row, cfg.EVENT_TIME_FIELD_IDX).text()) if self.timeFormat
                    == cfg.HHMMSS else Decimal(self.twEvents.item(row, cfg.EVENT_TIME_FIELD_IDX).text()),
                    self.twEvents.item(row, cfg.EVENT_SUBJECT_FIELD_IDX).text(),
                    self.twEvents.item(row, cfg.EVENT_BEHAVIOR_FIELD_IDX).text(),
                ])

            for idx, event in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]):
                if [
                        event[cfg.EVENT_TIME_FIELD_IDX],
                        event[cfg.EVENT_SUBJECT_FIELD_IDX],
                        event[cfg.EVENT_BEHAVIOR_FIELD_IDX],
                ] in tsb_to_edit:
                    if dialogWindow.rbSubject.isChecked():
                        event[cfg.EVENT_SUBJECT_FIELD_IDX] = dialogWindow.newText.selectedItems()[0].text()
                    if dialogWindow.rbBehavior.isChecked():
                        event[cfg.EVENT_BEHAVIOR_FIELD_IDX] = dialogWindow.newText.selectedItems()[0].text()
                    if dialogWindow.rbComment.isChecked():
                        event[cfg.EVENT_COMMENT_FIELD_IDX] = dialogWindow.commentText.text()

                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][idx] = event
                    self.projectChanged = True
            self.loadEventsInTW(self.observationId)






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

    try:
        twEvents_row = self.twEvents.selectedItems()[0].row()

        tsb_to_edit = [
            util.time2seconds(self.twEvents.item(twEvents_row, cfg.EVENT_TIME_FIELD_IDX).text()) if self.timeFormat == cfg.HHMMSS
            else Decimal(self.twEvents.item(twEvents_row, cfg.EVENT_TIME_FIELD_IDX).text()),
            self.twEvents.item(twEvents_row, cfg.EVENT_SUBJECT_FIELD_IDX).text(),
            self.twEvents.item(twEvents_row, cfg.EVENT_BEHAVIOR_FIELD_IDX).text(),
        ]

        row = [
            idx for idx, event in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS])
            if [event[cfg.EVENT_TIME_FIELD_IDX], event[cfg.EVENT_SUBJECT_FIELD_IDX], event[cfg.EVENT_BEHAVIOR_FIELD_IDX]] ==
            tsb_to_edit
        ][0]

        editWindow = DlgEditEvent(
            logging.getLogger().getEffectiveLevel(),
            time_value=self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][row][0],
            current_time=self.getLaps(),
            time_format=self.timeFormat,
            show_set_current_time=True,
        )
        editWindow.setWindowTitle("Edit event")

        sortedSubjects = [""] + sorted([self.pj[cfg.SUBJECTS][x][cfg.SUBJECT_NAME] for x in self.pj[cfg.SUBJECTS]])

        editWindow.cobSubject.addItems(sortedSubjects)

        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][row][cfg.EVENT_SUBJECT_FIELD_IDX] in sortedSubjects:
            editWindow.cobSubject.setCurrentIndex(
                sortedSubjects.index(
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][row][cfg.EVENT_SUBJECT_FIELD_IDX]))
        else:
            QMessageBox.warning(
                self,
                cfg.programName,
                (f"The subject <b>{self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][row][cfg.EVENT_SUBJECT_FIELD_IDX]}</b> "
                    "does not exist more in the subject's list"),
            )
            editWindow.cobSubject.setCurrentIndex(0)

        sortedCodes = sorted([self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] for x in self.pj[cfg.ETHOGRAM]])
        editWindow.cobCode.addItems(sortedCodes)

        # check if selected code is in code's list (no modification of codes)
        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][row][cfg.EVENT_BEHAVIOR_FIELD_IDX] in sortedCodes:
            editWindow.cobCode.setCurrentIndex(
                sortedCodes.index(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][row][cfg.EVENT_BEHAVIOR_FIELD_IDX]))
        else:
            logging.warning((
                f"The behaviour {self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][row][cfg.EVENT_BEHAVIOR_FIELD_IDX]} "
                "does not exist more in the ethogram"))
            QMessageBox.warning(
                self,
                cfg.programName,
                (f"The behaviour <b>{self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][row][cfg.EVENT_BEHAVIOR_FIELD_IDX]}</b> "
                    "does not exist more in the ethogram"),
            )
            editWindow.cobCode.setCurrentIndex(0)

        logging.debug(
            f"original modifiers: {self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][row][cfg.EVENT_MODIFIER_FIELD_IDX]}"
        )

        # comment
        editWindow.leComment.setPlainText(
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][row][cfg.EVENT_COMMENT_FIELD_IDX])

        if editWindow.exec_():  # button OK

            self.projectChanged = True

            newTime = editWindow.time_widget.get_time()

            for key in self.pj[cfg.ETHOGRAM]:
                if self.pj[cfg.ETHOGRAM][key][cfg.BEHAVIOR_CODE] == editWindow.cobCode.currentText():
                    event = self.full_event(key)
                    event["subject"] = editWindow.cobSubject.currentText()
                    event["comment"] = editWindow.leComment.toPlainText()
                    event["row"] = row
                    event["original_modifiers"] = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][row][
                        cfg.pj_obs_fields["modifier"]]

                    self.writeEvent(event, newTime)
                    break

    except Exception:
        dialog.error_message2()
