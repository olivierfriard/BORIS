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
  along with this program; if not see <http://www.gnu.org/licPbehav_enses/>.

"""

import logging
import json

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QDialog, QWidget, QFileDialog, QMessageBox

from . import dialog
from .add_modifier_ui import Ui_Dialog
from . import config as cfg
from .utilities import sorted_keys


class addModifierDialog(QDialog, Ui_Dialog):
    tabMem = -1
    itemPositionMem = -1

    def __init__(self, modifiers_str: str, subjects: list = [], ask_at_stop_enabled: bool = False, parent=None):
        super().__init__()
        self.setupUi(self)

        self.subjects = subjects
        if not self.subjects:
            self.pb_add_subjects.setEnabled(False)

        self.ask_at_stop_enabled = ask_at_stop_enabled

        self.pbAddModifier.clicked.connect(self.addModifier)
        self.pbAddModifier.setIcon(QIcon(":/frame_forward"))
        self.pbAddSet.clicked.connect(self.add_set_of_modifiers)
        self.pbRemoveSet.clicked.connect(self.remove_set_of_modifiers)
        self.pbModifyModifier.clicked.connect(self.modifyModifier)
        self.pbModifyModifier.setIcon(QIcon(":/frame_backward"))

        self.pbMoveUp.clicked.connect(self.moveModifierUp)
        self.pbMoveDown.clicked.connect(self.moveModifierDown)
        self.pbMoveSetLeft.clicked.connect(self.moveSetLeft)
        self.pbMoveSetRight.clicked.connect(self.moveSetRight)
        self.pbRemoveModifier.clicked.connect(self.removeModifier)
        self.pb_sort_modifiers.clicked.connect(self.sort_modifiers)
        self.pb_add_subjects.clicked.connect(self.add_subjects)
        self.pb_load_file.clicked.connect(self.add_modifiers_from_file)

        self.pbOK.clicked.connect(lambda: self.pb_pushed(cfg.OK))
        self.pbCancel.clicked.connect(lambda: self.pb_pushed(cfg.CANCEL))

        self.le_name.textChanged.connect(self.set_name_changed)
        self.le_description.textChanged.connect(self.set_description_changed)

        self.cbType.currentIndexChanged.connect(self.type_changed)

        # self.cb_ask_at_stop.clicked.connect(self.ask_at_stop_changed)

        dummy_dict: dict = json.loads(modifiers_str) if modifiers_str else {}
        modif_values: list = []
        for idx in sorted_keys(dummy_dict):
            modif_values.append(dummy_dict[idx])

        self.modifiers_sets_dict: dict = {}
        for modif in modif_values:
            self.modifiers_sets_dict[str(len(self.modifiers_sets_dict))] = dict(modif)
            if self.ask_at_stop_enabled:
                if dict(modif).get("ask at stop", False):
                    self.cb_ask_at_stop.setChecked(True)

        self.tabWidgetModifiersSets.currentChanged.connect(self.tabWidgetModifiersSets_changed)

        # create tab
        for idx in sorted_keys(self.modifiers_sets_dict):
            self.tabWidgetModifiersSets.addTab(QWidget(), f"Set #{int(idx) + 1}")

        if self.tabWidgetModifiersSets.currentIndex() == -1:
            for w in (
                self.lb_name,
                self.le_name,
                self.lbType,
                self.lbValues,
                self.lb_description,
                self.le_description,
                self.cbType,
                self.lwModifiers,
                self.pbMoveUp,
                self.pbMoveDown,
                self.pbRemoveModifier,
                self.pbRemoveSet,
                self.pbMoveSetLeft,
                self.pbMoveSetRight,
                self.pb_add_subjects,
                self.pb_load_file,
                self.pb_sort_modifiers,
                self.cb_ask_at_stop,
            ):
                w.setVisible(False)
            for w in (self.leModifier, self.leCode, self.pbAddModifier, self.pbModifyModifier):
                w.setEnabled(False)

        # set first tab as active
        self.tabMem = 0

    def pb_pushed(self, button):
        if self.leModifier.text():
            if (
                dialog.MessageDialog(
                    cfg.programName,
                    (
                        "You are working on a behavior.<br>"
                        "If you close the window it will be lost.<br>"
                        "Do you want to change modifiers set"
                    ),
                    [cfg.CLOSE, cfg.CANCEL],
                )
                == cfg.CANCEL
            ):
                return
        if button == cfg.OK:
            self.accept()
        if button == cfg.CANCEL:
            self.reject()

    def add_subjects(self):
        """
        add subjects as modifiers
        """

        for subject, key in self.subjects:
            if self.itemPositionMem != -1:
                self.lwModifiers.insertItem(self.itemPositionMem, f"{subject} ({key})" if key else subject)
            else:
                self.lwModifiers.addItem(f"{subject} ({key})" if key else subject)

        self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex())]["values"] = [
            self.lwModifiers.item(x).text() for x in range(self.lwModifiers.count())
        ]

    def add_modifiers_from_file(self):
        """
        add modifiers from file
        """

        file_name, _ = QFileDialog.getOpenFileName(self, "Load modifiers from file", "", "All files (*)")
        if not file_name:
            return
        try:
            with open(file_name) as f_in:
                for line in f_in:
                    if line.strip():
                        for c in cfg.CHAR_FORBIDDEN_IN_MODIFIERS:
                            if c in line.strip():
                                QMessageBox.critical(
                                    self,
                                    cfg.programName,
                                    (
                                        f"The character <b>{c}</b> is not allowed.<br>"
                                        "The following characters are not allowed in modifiers:<br>"
                                        f"<b>{cfg.CHAR_FORBIDDEN_IN_MODIFIERS}</b>"
                                    ),
                                )
                                break
                        else:
                            if line.strip() not in [self.lwModifiers.item(x).text() for x in range(self.lwModifiers.count())]:
                                if self.itemPositionMem != -1:
                                    self.lwModifiers.insertItem(self.itemPositionMem, line.strip())
                                else:
                                    self.lwModifiers.addItem(line.strip())

            self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex())]["values"] = [
                self.lwModifiers.item(x).text() for x in range(self.lwModifiers.count())
            ]
        except Exception:
            QMessageBox.warning(self, cfg.programName, f"Error reading modifiers from file:<br>{file_name}")
            logging.warning(f"Error reading modifiers from file<br>{file_name}")

    def sort_modifiers(self):
        """
        sort modifiers
        """

        modifiers = sorted([self.lwModifiers.item(x).text() for x in range(self.lwModifiers.count())])
        self.lwModifiers.clear()
        for modifier in modifiers:
            if self.itemPositionMem != -1:
                self.lwModifiers.insertItem(self.itemPositionMem, modifier)
            else:
                self.lwModifiers.addItem(modifier)

        self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex())]["values"] = [
            self.lwModifiers.item(x).text() for x in range(self.lwModifiers.count())
        ]

    def set_name_changed(self):
        """
        set name changed
        """
        if not self.modifiers_sets_dict:
            self.modifiers_sets_dict["0"] = {"name": "", "description": "", "type": cfg.SINGLE_SELECTION, "values": []}
        self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex())]["name"] = self.le_name.text().strip()

    def set_description_changed(self):
        """
        set description changed
        """
        if not self.modifiers_sets_dict:
            self.modifiers_sets_dict["0"] = {"name": "", "description": "", "type": cfg.SINGLE_SELECTION, "values": []}
        self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex())]["description"] = self.le_description.text().strip()

    def type_changed(self):
        """
        type changed
        """
        if not self.modifiers_sets_dict:
            self.modifiers_sets_dict["0"] = {"name": "", "description": "", "type": cfg.SINGLE_SELECTION, "values": []}
        self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex())]["type"] = self.cbType.currentIndex()
        # disable if modifier numeric or value from external data file
        for obj in (
            self.lbValues,
            self.lwModifiers,
            self.leModifier,
            self.leCode,
            self.lbModifier,
            self.lbCode,
            self.lbCodeHelp,
            self.pbMoveUp,
            self.pbMoveDown,
            self.pbRemoveModifier,
            self.pb_add_subjects,
            self.pbAddModifier,
            self.pbModifyModifier,
            self.pb_load_file,
            self.pb_sort_modifiers,
        ):
            obj.setEnabled(self.cbType.currentIndex() not in [cfg.NUMERIC_MODIFIER, cfg.EXTERNAL_DATA_MODIFIER])
        if self.cbType.currentIndex() == cfg.EXTERNAL_DATA_MODIFIER:
            self.lb_name.setText("Variable name")
        else:
            self.lb_name.setText("Set name")

    # def ask_at_stop_changed(self):
    #    """
    #    value changed
    #    """
    #    self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex())]["ask at stop"] = self.cb_ask_at_stop.isChecked()

    def moveSetLeft(self):
        """
        move selected modifiers set left
        """
        if self.tabWidgetModifiersSets.currentIndex():
            (
                self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex() - 1)],
                self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex())],
            ) = (
                dict(self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex())]),
                dict(self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex() - 1)]),
            )
            self.tabWidgetModifiersSets.setCurrentIndex(self.tabWidgetModifiersSets.currentIndex() - 1)
            self.tabMem = self.tabWidgetModifiersSets.currentIndex()

    def moveSetRight(self):
        """
        move selected modifiers set right
        """
        if self.tabWidgetModifiersSets.currentIndex() < self.tabWidgetModifiersSets.count() - 1:
            (
                self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex() + 1)],
                self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex())],
            ) = (
                dict(self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex())]),
                dict(self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex() + 1)]),
            )

            self.tabWidgetModifiersSets.setCurrentIndex(self.tabWidgetModifiersSets.currentIndex() + 1)
            self.tabMem = self.tabWidgetModifiersSets.currentIndex()

    def moveModifierUp(self):
        """
        move up the selected modifier
        """
        if self.lwModifiers.currentRow() >= 0:
            currentRow = self.lwModifiers.currentRow()
            currentItem = self.lwModifiers.takeItem(currentRow)
            self.lwModifiers.insertItem(currentRow - 1, currentItem)
            self.lwModifiers.setCurrentItem(currentItem)
            self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex())]["values"] = [
                self.lwModifiers.item(x).text() for x in range(self.lwModifiers.count())
            ]

    def moveModifierDown(self):
        """
        move down the selected modifier
        """
        if self.lwModifiers.currentRow() >= 0:
            currentRow = self.lwModifiers.currentRow()
            currentItem = self.lwModifiers.takeItem(currentRow)
            self.lwModifiers.insertItem(currentRow + 1, currentItem)
            self.lwModifiers.setCurrentItem(currentItem)
            self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex())]["values"] = [
                self.lwModifiers.item(x).text() for x in range(self.lwModifiers.count())
            ]

    def add_set_of_modifiers(self):
        """
        Add a set of modifiers
        """

        # no modifiers set
        if self.tabWidgetModifiersSets.currentIndex() == -1:
            self.modifiers_sets_dict[str(len(self.modifiers_sets_dict))] = {
                "name": "",
                "description": "",
                "type": cfg.SINGLE_SELECTION,
                "ask at stop": False,
                "values": [],
            }
            self.tabWidgetModifiersSets.addTab(QWidget(), f"Set #{len(self.modifiers_sets_dict)}")
            self.tabWidgetModifiersSets.setCurrentIndex(self.tabWidgetModifiersSets.count() - 1)
            self.tabMem = self.tabWidgetModifiersSets.currentIndex()

            # set visible and available buttons and others elements
            for w in (
                self.lb_name,
                self.lbType,
                self.lbValues,
                self.le_name,
                self.lb_description,
                self.le_description,
                self.cbType,
                self.lwModifiers,
                self.pbMoveUp,
                self.pbMoveDown,
                self.pbRemoveModifier,
                self.pbRemoveSet,
                self.pbMoveSetLeft,
                self.pbMoveSetRight,
                self.pb_add_subjects,
                self.pb_load_file,
                self.pb_sort_modifiers,
            ):
                w.setVisible(True)
            self.cb_ask_at_stop.setVisible(self.ask_at_stop_enabled)

            for w in (self.leModifier, self.leCode, self.pbAddModifier, self.pbModifyModifier):
                w.setEnabled(True)
            return

        if len(self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex())]):
            self.modifiers_sets_dict[str(len(self.modifiers_sets_dict))] = {
                "name": "",
                "description": "",
                "type": cfg.SINGLE_SELECTION,
                "ask at stop": False,
                "values": [],
            }
            self.tabWidgetModifiersSets.addTab(QWidget(), f"Set #{len(self.modifiers_sets_dict)}")
            self.tabWidgetModifiersSets.setCurrentIndex(self.tabWidgetModifiersSets.count() - 1)
            self.tabMem = self.tabWidgetModifiersSets.currentIndex()

        else:
            QMessageBox.information(
                self,
                cfg.programName,
                "It is not possible to add a modifiers' set while the current modifiers' set is empty.",
            )

    def remove_set_of_modifiers(self):
        """
        remove set of modifiers
        """

        if self.tabWidgetModifiersSets.currentIndex() != -1:
            if dialog.MessageDialog(cfg.programName, "Confirm deletion of this set of modifiers?", [cfg.YES, cfg.NO]) == cfg.YES:
                index_to_delete = self.tabWidgetModifiersSets.currentIndex()

                for k in range(index_to_delete, len(self.modifiers_sets_dict) - 1):
                    self.modifiers_sets_dict[str(k)] = self.modifiers_sets_dict[str(k + 1)]
                # del last key
                del self.modifiers_sets_dict[str(len(self.modifiers_sets_dict) - 1)]

                # remove all tabs
                while self.tabWidgetModifiersSets.count():
                    self.tabWidgetModifiersSets.removeTab(0)

                # recreate tabs
                for idx in sorted_keys(self.modifiers_sets_dict):
                    self.tabWidgetModifiersSets.addTab(QWidget(), f"Set #{int(idx) + 1}")

                # set not visible and not available buttons and others elements
                if self.tabWidgetModifiersSets.currentIndex() == -1:
                    for w in (
                        self.lb_name,
                        self.le_name,
                        self.lbType,
                        self.lbValues,
                        self.lb_description,
                        self.le_description,
                        self.cbType,
                        self.lwModifiers,
                        self.pbMoveUp,
                        self.pbMoveDown,
                        self.pbRemoveModifier,
                        self.pbRemoveSet,
                        self.pbMoveSetLeft,
                        self.pbMoveSetRight,
                        self.cb_ask_at_stop,
                    ):
                        w.setVisible(False)
                    for w in (self.leModifier, self.leCode, self.pbAddModifier, self.pbModifyModifier):
                        w.setEnabled(False)

                if not len(self.modifiers_sets_dict):
                    # set invisible and unavailable buttons and others elements
                    for w in (
                        self.lb_name,
                        self.le_name,
                        self.lbType,
                        self.lbValues,
                        self.lb_description,
                        self.le_description,
                        self.cbType,
                        self.lwModifiers,
                        self.pbMoveUp,
                        self.pbMoveDown,
                        self.pbRemoveModifier,
                        self.pbRemoveSet,
                        self.pbMoveSetLeft,
                        self.pbMoveSetRight,
                        self.pb_add_subjects,
                        self.pb_load_file,
                        self.pb_sort_modifiers,
                    ):
                        w.setVisible(False)
                    for w in [self.leModifier, self.leCode, self.pbAddModifier, self.pbModifyModifier]:
                        w.setEnabled(False)
                    return

        else:
            QMessageBox.information(self, cfg.programName, "It is not possible to remove the last modifiers' set.")

    def modifyModifier(self):
        """
        modify modifier <- arrow
        """

        if self.lwModifiers.currentRow() >= 0:
            txt = self.lwModifiers.currentItem().text()
            code = ""
            if "(" in txt and ")" in txt:
                code = txt.split("(")[1].split(")")[0]

            self.leModifier.setText(txt.split("(")[0].strip())
            self.leCode.setText(code)

            self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex())]["values"].remove(
                self.lwModifiers.currentItem().text()
            )

            self.itemPositionMem = self.lwModifiers.currentRow()
            self.lwModifiers.takeItem(self.lwModifiers.currentRow())
        else:
            QMessageBox.information(self, cfg.programName, "Select a modifier to modify from the modifiers set")

    def removeModifier(self):
        """
        remove modifier from set
        """
        if self.lwModifiers.currentIndex().row() >= 0:
            self.lwModifiers.takeItem(self.lwModifiers.currentIndex().row())
            self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex())]["values"] = [
                self.lwModifiers.item(x).text() for x in range(self.lwModifiers.count())
            ]

    def addModifier(self):
        """
        add a modifier to set
        """

        txt = self.leModifier.text().strip()
        for c in cfg.CHAR_FORBIDDEN_IN_MODIFIERS:
            if c in txt:
                QMessageBox.critical(
                    self,
                    cfg.programName,
                    (
                        f"The character <b>{c}</b> is not allowed.<br>"
                        "The following characters are not allowed in modifiers:<br>"
                        f"<b>{cfg.CHAR_FORBIDDEN_IN_MODIFIERS}</b>"
                    ),
                )
                self.leModifier.setFocus()
                return

        if txt:
            if txt in [self.lwModifiers.item(x).text() for x in range(self.lwModifiers.count())]:
                QMessageBox.critical(self, cfg.programName, f"The modifier <b>{txt}</b> is already in the list")
                return

            if not self.modifiers_sets_dict:
                self.modifiers_sets_dict["0"] = {
                    "name": "",
                    "description": "",
                    "type": cfg.SINGLE_SELECTION,
                    "ask at stop": False,
                    "values": [],
                }

            if len(self.leCode.text().strip()) > 1:
                if self.leCode.text().strip().upper() not in cfg.function_keys.values():
                    QMessageBox.critical(
                        self,
                        cfg.programName,
                        "The modifier key code can not exceed one key\nSelect one key or a function key (F1, F2 ... F12)",
                    )
                    self.leCode.setFocus()
                    return

            if self.leCode.text().strip():
                for c in cfg.CHAR_FORBIDDEN_IN_MODIFIERS:
                    if c in self.leCode.text().strip():
                        QMessageBox.critical(
                            self,
                            cfg.programName,
                            f"The modifier key code is not allowed {cfg.CHAR_FORBIDDEN_IN_MODIFIERS}!",
                        )
                        self.leCode.setFocus()
                        return

                # check if code already exists
                if not self.modifiers_sets_dict:
                    self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex())] = {
                        "name": "",
                        "description": "",
                        "type": cfg.SINGLE_SELECTION,
                        "ask at stop": False,
                        "values": [],
                    }

                if "(" + self.leCode.text().strip() + ")" in " ".join(
                    self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex())]["values"]
                ):
                    QMessageBox.critical(self, cfg.programName, f"The shortcut code <b>{self.leCode.text().strip()}</b> already exists!")
                    self.leCode.setFocus()
                    return
                txt += f" ({self.leCode.text().strip()})"

            if self.itemPositionMem != -1:
                self.lwModifiers.insertItem(self.itemPositionMem, txt)
            else:
                self.lwModifiers.addItem(txt)

            self.modifiers_sets_dict[str(self.tabWidgetModifiersSets.currentIndex())]["values"] = [
                self.lwModifiers.item(x).text() for x in range(self.lwModifiers.count())
            ]
            self.leModifier.setText("")
            self.leCode.setText("")

        else:
            QMessageBox.critical(self, cfg.programName, "No modifier to add!")
            self.leModifier.setFocus()

    def tabWidgetModifiersSets_changed(self, tabIndex):
        """
        user changed the tab widget
        """

        # check if modifier field empty
        if self.leModifier.text() and tabIndex != self.tabMem:
            if (
                dialog.MessageDialog(
                    cfg.programName,
                    (
                        "You are working on a behavior.<br>"
                        "If you change the modifier's set it will be lost.<br>"
                        "Do you want to change modifiers set"
                    ),
                    [cfg.YES, cfg.NO],
                )
                == cfg.NO
            ):
                self.tabWidgetModifiersSets.setCurrentIndex(self.tabMem)
                return

        if tabIndex != self.tabMem:
            self.lwModifiers.clear()
            self.leCode.clear()
            self.leModifier.clear()
            # if self.ask_at_stop_enabled:
            #    self.cb_ask_at_stop.setChecked(False)

            self.tabMem = tabIndex

            if tabIndex != -1:
                self.le_name.setText(self.modifiers_sets_dict[str(tabIndex)]["name"])
                self.le_description.setText(self.modifiers_sets_dict[str(tabIndex)].get("description", ""))
                self.cbType.setCurrentIndex(self.modifiers_sets_dict[str(tabIndex)]["type"])
                # if self.ask_at_stop_enabled:
                #    self.cb_ask_at_stop.setChecked(self.modifiers_sets_dict[str(tabIndex)].get("ask at stop", False))

                self.lwModifiers.addItems(self.modifiers_sets_dict[str(tabIndex)]["values"])

    def get_modifiers(self) -> str:
        """
        returns modifiers as string
        """
        keys_to_delete: list = []
        for idx in self.modifiers_sets_dict:
            # add ask_at_stop value (boolean) to each set of modifiers
            if self.ask_at_stop_enabled:
                self.modifiers_sets_dict[idx]["ask at stop"] = self.cb_ask_at_stop.isChecked()
            # delete modifiers without values for selection
            if (
                self.modifiers_sets_dict[idx]["type"] in (cfg.SINGLE_SELECTION, cfg.MULTI_SELECTION)
                and not self.modifiers_sets_dict[idx]["values"]
            ):
                keys_to_delete.append(idx)

        for idx in keys_to_delete:
            del self.modifiers_sets_dict[idx]

        return json.dumps(self.modifiers_sets_dict) if self.modifiers_sets_dict else ""
