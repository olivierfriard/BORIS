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

import re

from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QListWidgetItem,
    QSizePolicy,
    QSpacerItem,
    QAbstractItemView,
    QMessageBox,
)

from . import config as cfg
from . import utilities as util


class ModifiersList(QDialog):
    """
    class for selection the modifier(s)
    """

    def __init__(self, code: str, modifiers_dict: dict, currentModifier: str):
        super().__init__()
        self.setWindowTitle(cfg.programName)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        self.modifiers_dict = dict(modifiers_dict)
        currentModifierList = currentModifier.split("|")

        V1layout = QVBoxLayout()
        label = QLabel()
        label.setText(f"Choose the modifier{'s' * (len(self.modifiers_dict) > 1)} for <b>{code}</b> behavior")
        V1layout.addWidget(label)

        Hlayout = QHBoxLayout()
        self.modifiersSetNumber = 0

        for idx in util.sorted_keys(modifiers_dict):
            if self.modifiers_dict[idx]["type"] not in (
                cfg.SINGLE_SELECTION,
                cfg.MULTI_SELECTION,
                cfg.NUMERIC_MODIFIER,
            ):
                continue

            V2layout = QVBoxLayout()

            self.modifiersSetNumber += 1

            if self.modifiers_dict[idx].get("name", ""):
                lb1 = QLabel(f"Modifier <b>{self.modifiers_dict[idx].get('name', '')}</b>")
                V2layout.addWidget(lb1)

            if self.modifiers_dict[idx].get("description", ""):
                lb2 = QLabel(f"<small>{self.modifiers_dict[idx].get('description', '')[:50]}</small>")
                V2layout.addWidget(lb2)

            if self.modifiers_dict[idx]["type"] in (
                cfg.SINGLE_SELECTION,
                cfg.MULTI_SELECTION,
            ):
                lw = QListWidget()
                self.modifiers_dict[idx]["widget"] = lw
                lw.setObjectName(f"lw_modifiers_({self.modifiers_dict[idx]['type']})")
                lw.installEventFilter(self)

                if self.modifiers_dict[idx]["type"] == cfg.SINGLE_SELECTION:
                    item = QListWidgetItem("None")
                    lw.addItem(item)
                    item.setSelected(True)

                for modifier in self.modifiers_dict[idx]["values"]:
                    item = QListWidgetItem(modifier)
                    if self.modifiers_dict[idx]["type"] == cfg.MULTI_SELECTION:
                        item.setCheckState(Qt.Unchecked)

                        # previously selected
                        try:
                            if currentModifierList != [""] and re.sub(r" \(.\)", "", modifier) in currentModifierList[int(idx)].split(","):
                                item.setCheckState(Qt.Checked)
                        except Exception:  # for old projects due to a fixed bug
                            pass

                    lw.addItem(item)

                    if self.modifiers_dict[idx]["type"] == cfg.SINGLE_SELECTION:
                        try:
                            if currentModifierList != [""] and re.sub(r" \(.\)", "", modifier) == currentModifierList[int(idx)]:
                                item.setSelected(True)
                        except Exception:  # for old projects due to a fixed bug
                            pass
                V2layout.addWidget(lw)

            if self.modifiers_dict[idx]["type"] in [cfg.NUMERIC_MODIFIER]:
                le = QLineEdit()
                self.modifiers_dict[idx]["widget"] = le
                le.setObjectName(f"le_modifiers_({self.modifiers_dict[idx]['type']})")

                if currentModifierList != [""] and currentModifierList[int(idx)] != "None":
                    le.setText(currentModifierList[int(idx)])

                V2layout.addWidget(le)

                # vertical spacer
                spacerItem = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
                V2layout.addItem(spacerItem)

            Hlayout.addLayout(V2layout)

        V1layout.addLayout(Hlayout)

        H2layout = QHBoxLayout()
        H2layout.addStretch(1)

        pbCancel = QPushButton(cfg.CANCEL)
        pbCancel.clicked.connect(self.reject)
        H2layout.addWidget(pbCancel)

        pbOK = QPushButton(cfg.OK)
        pbOK.setDefault(True)
        pbOK.clicked.connect(self.pbOK_clicked)
        H2layout.addWidget(pbOK)

        V1layout.addLayout(H2layout)
        self.setLayout(V1layout)

        self.installEventFilter(self)
        self.setMaximumSize(1024, 960)

    def eventFilter(self, receiver, event):
        """
        send event (if keypress) to main window
        """
        if event.type() == QEvent.KeyPress:
            ek, ek_text = event.key(), event.text()

            # reject and close dialog if escape pressed
            if ek == Qt.Key_Escape:  # close
                self.reject()
                return False

            # accept and close dialog if enter pressed
            if ek == Qt.Key_Enter or ek == Qt.Key_Return:  # enter or enter from numeric pad
                if not self.pbOK_clicked():
                    return False
                return True

            modifiersSetIndex = 0
            for widget in self.children():
                if "_modifiers" in widget.objectName():
                    modifiersSetIndex = modifiersSetIndex + 1
                if "lw_modifiers" in widget.objectName():
                    if self.modifiersSetNumber == 1:
                        # check if modifiers have code
                        for index in range(widget.count()):
                            if "(" in widget.item(index).text():
                                break
                        else:
                            # modifiers have no associated code: the modifier starting with hit key will be selected
                            if ek not in (Qt.Key_Down, Qt.Key_Up):
                                if ek == Qt.Key_Space and f"({cfg.MULTI_SELECTION})" in widget.objectName():  # checking using SPACE bar
                                    if widget.item(widget.currentRow()).checkState() == Qt.Checked:
                                        widget.item(widget.currentRow()).setCheckState(Qt.Unchecked)
                                    else:
                                        widget.item(widget.currentRow()).setCheckState(Qt.Checked)

                                else:
                                    for index in range(widget.count()):
                                        if widget.item(index).text().upper().startswith(ek_text.upper()):
                                            widget.setCurrentRow(index)
                                            widget.scrollToItem(
                                                widget.item(index),
                                                QAbstractItemView.EnsureVisible,
                                            )
                                            return True
                            else:  # up / down keys
                                try:
                                    if ek == Qt.Key_Down and widget.currentRow() < widget.count() - 1:
                                        widget.setCurrentRow(widget.currentRow() + 1)
                                    if ek == Qt.Key_Up and widget.currentRow() > 0:
                                        widget.setCurrentRow(widget.currentRow() - 1)
                                except Exception:
                                    return

                    for index in range(widget.count()):
                        # check function kesy (F1, F2...)
                        if ek in cfg.function_keys:
                            if f"({cfg.function_keys[ek]})" in widget.item(index).text().upper():
                                if f"({cfg.SINGLE_SELECTION})" in widget.objectName():
                                    widget.item(index).setSelected(True)
                                    # close dialog if one set of modifiers
                                    if self.modifiersSetNumber == 1:
                                        self.accept()
                                        return True
                                    # else move to next set of mofifiers
                                    elif modifiersSetIndex != self.modifiersSetNumber:
                                        widget.parent().focusNextChild()
                                        return True

                                if f"({cfg.MULTI_SELECTION})" in widget.objectName():
                                    if widget.item(index).checkState() == Qt.Checked:
                                        widget.item(index).setCheckState(Qt.Unchecked)
                                    else:
                                        widget.item(index).setCheckState(Qt.Checked)

                        if ek < 1114112 and f"({ek_text})" in widget.item(index).text():
                            if f"({cfg.SINGLE_SELECTION})" in widget.objectName():
                                widget.item(index).setSelected(True)
                                # close dialog if one set of modifiers
                                if self.modifiersSetNumber == 1:
                                    self.accept()
                                    return True
                                # else move to next set of mofifiers
                                elif modifiersSetIndex != self.modifiersSetNumber:
                                    widget.parent().focusNextChild()
                                    return True

                            if f"({cfg.MULTI_SELECTION})" in widget.objectName():
                                if widget.item(index).checkState() == Qt.Checked:
                                    widget.item(index).setCheckState(Qt.Unchecked)
                                else:
                                    widget.item(index).setCheckState(Qt.Checked)

            return True
        else:
            return False

    def get_modifiers(self):
        """
        get modifiers
        returns list of selected modifiers
        """

        for idx in util.sorted_keys(self.modifiers_dict):
            if self.modifiers_dict[idx]["type"] in [
                cfg.SINGLE_SELECTION,
                cfg.MULTI_SELECTION,
                cfg.NUMERIC_MODIFIER,
            ]:
                self.modifiers_dict[idx]["selected"] = []

            if self.modifiers_dict[idx]["type"] == cfg.MULTI_SELECTION:
                for j in range(self.modifiers_dict[idx]["widget"].count()):
                    if self.modifiers_dict[idx]["widget"].item(j).checkState() == Qt.Checked:
                        self.modifiers_dict[idx]["selected"].append(
                            re.sub(
                                r" \(.*\)",
                                "",
                                self.modifiers_dict[idx]["widget"].item(j).text(),
                            )
                        )

                if not self.modifiers_dict[idx]["selected"]:
                    self.modifiers_dict[idx]["selected"].append("None")

            if self.modifiers_dict[idx]["type"] == cfg.SINGLE_SELECTION:
                for item in self.modifiers_dict[idx]["widget"].selectedItems():
                    self.modifiers_dict[idx]["selected"].append(re.sub(r" \(.*\)", "", item.text()))

            if self.modifiers_dict[idx]["type"] == cfg.NUMERIC_MODIFIER:
                self.modifiers_dict[idx]["selected"] = (
                    self.modifiers_dict[idx]["widget"].text() if self.modifiers_dict[idx]["widget"].text() else "None"
                )

        return self.modifiers_dict

    def pbOK_clicked(self):
        """
        OK button is clicked
        """
        for idx in util.sorted_keys(self.modifiers_dict):
            if self.modifiers_dict[idx]["type"] == cfg.NUMERIC_MODIFIER:
                if self.modifiers_dict[idx]["widget"].text():
                    try:
                        _ = float(self.modifiers_dict[idx]["widget"].text())
                    except Exception:
                        QMessageBox.warning(
                            self,
                            cfg.programName,
                            f"<b>{self.modifiers_dict[idx]['widget'].text()}</b> is not a numeric value",
                        )
                        return False

        self.accept()
