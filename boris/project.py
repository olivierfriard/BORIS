#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2020 Olivier Friard

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

import json
import logging
import pathlib
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

import tablib
from PyQt5.QtCore import Qt
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from boris import add_modifier
from boris import dialog
from boris import export_observation
from boris import param_panel
from boris import exclusion_matrix
from boris import project_import
from boris.config import *

from boris.project_ui import Ui_dlgProject
import boris.utilities as utilities
import boris.dialog as dialog
import boris.project_functions as project_functions


class BehavioralCategories(QDialog):

    def __init__(self, pj):
        super().__init__()

        self.pj = pj
        self.setWindowTitle("Behavioral categories")

        self.renamed = None
        self.removed = None

        self.vbox = QVBoxLayout(self)

        self.label = QLabel()
        self.label.setText("Behavioral categories")
        self.vbox.addWidget(self.label)

        self.lw = QListWidget()

        if BEHAVIORAL_CATEGORIES in pj:
            for category in pj[BEHAVIORAL_CATEGORIES]:
                self.lw.addItem(QListWidgetItem(category))

        self.vbox.addWidget(self.lw)

        self.hbox0 = QHBoxLayout(self)
        self.pbAddCategory = QPushButton("Add category")
        self.pbAddCategory.clicked.connect(self.pbAddCategory_clicked)
        self.pbRemoveCategory = QPushButton("Remove category")
        self.pbRemoveCategory.clicked.connect(self.pbRemoveCategory_clicked)
        self.pb_rename_category = QPushButton("Rename category")
        self.pb_rename_category.clicked.connect(self.pb_rename_category_clicked)

        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.hbox0.addItem(spacerItem)
        self.hbox0.addWidget(self.pb_rename_category)
        self.hbox0.addWidget(self.pbRemoveCategory)
        self.hbox0.addWidget(self.pbAddCategory)
        self.vbox.addLayout(self.hbox0)

        hbox1 = QHBoxLayout(self)
        self.pbOK = QPushButton("OK")
        self.pbOK.clicked.connect(self.accept)
        self.pbCancel = QPushButton("Cancel")
        self.pbCancel.clicked.connect(self.reject)
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        hbox1.addItem(spacerItem)
        hbox1.addWidget(self.pbCancel)
        hbox1.addWidget(self.pbOK)
        self.vbox.addLayout(hbox1)

        self.setLayout(self.vbox)


    def pbAddCategory_clicked(self):
        """
        add a behavioral category
        """
        category, ok = QInputDialog.getText(self, "New behavioral category", "Category name:")
        if ok:
            self.lw.addItem(QListWidgetItem(category))


    def pbRemoveCategory_clicked(self):
        """
        remove the selected behavioral category
        """

        for SelectedItem in self.lw.selectedItems():
            # check if behavioral category is in use
            category_to_remove = self.lw.item(self.lw.row(SelectedItem)).text().strip()
            behaviors_in_category = []
            for idx in self.pj[ETHOGRAM]:
                if BEHAVIOR_CATEGORY in self.pj[ETHOGRAM][idx] and self.pj[ETHOGRAM][idx][BEHAVIOR_CATEGORY] == category_to_remove:
                    behaviors_in_category.append(self.pj[ETHOGRAM][idx][BEHAVIOR_CODE])
            flag_remove = False
            if behaviors_in_category:

                flag_remove = dialog.MessageDialog(
                    programName, ("Some behavior belong to the <b>{1}</b> to remove:<br>"
                                  "{0}<br>"
                                  "<br>Some features may not be available anymore.<br>").format(
                                      "<br>".join(behaviors_in_category), category_to_remove),
                    ["Remove category", CANCEL]) == "Remove category"

            else:
                flag_remove = True

            if flag_remove:
                self.lw.takeItem(self.lw.row(SelectedItem))
                self.removed = category_to_remove
                self.accept()



    def pb_rename_category_clicked(self):
        """
        rename the selected behavioral category
        """
        for SelectedItem in self.lw.selectedItems():
            # check if behavioral category is in use
            category_to_rename = self.lw.item(self.lw.row(SelectedItem)).text().strip()
            behaviors_in_category = []
            for idx in self.pj[ETHOGRAM]:
                if BEHAVIOR_CATEGORY in self.pj[ETHOGRAM][idx] and self.pj[ETHOGRAM][idx][BEHAVIOR_CATEGORY] == category_to_rename:
                    behaviors_in_category.append(self.pj[ETHOGRAM][idx][BEHAVIOR_CODE])

            flag_rename = False
            if behaviors_in_category:
                flag_rename = dialog.MessageDialog(
                    programName,
                    ("Some behavior belong to the <b>{1}</b> to rename:<br>"
                     "{0}<br>").format("<br>".join(behaviors_in_category), category_to_rename),
                    ["Rename category", CANCEL]) == "Rename category"
            else:
                flag_rename = True

            if flag_rename:
                new_category_name, ok = QInputDialog.getText(self, "Rename behavioral category", "New category name:",
                                                             QLineEdit.Normal, category_to_rename)
                if ok:
                    self.lw.item(self.lw.indexFromItem(SelectedItem).row()).setText(new_category_name)
                    # check behaviors belonging to the renamed category
                    self.renamed = [category_to_rename, new_category_name]
                    self.accept()


class projectDialog(QDialog, Ui_dlgProject):

    def __init__(self, parent=None):

        super().__init__()

        self.setupUi(self)

        self.lbObservationsState.setText("")
        self.lbSubjectsState.setText("")

        # ethogram tab
        self.pbAddBehavior.clicked.connect(self.pbAddBehavior_clicked)
        self.pbCloneBehavior.clicked.connect(self.pb_clone_behavior_clicked)

        self.pbRemoveBehavior.clicked.connect(self.pbRemoveBehavior_clicked)
        self.pbRemoveAllBehaviors.clicked.connect(self.pbRemoveAllBehaviors_clicked)

        self.pbBehaviorsCategories.clicked.connect(self.pbBehaviorsCategories_clicked)

        self.pb_convert_behav_keys_to_lower.clicked.connect(self.convert_behaviors_keys_to_lower_case)

        self.pbExclusionMatrix.clicked.connect(self.pbExclusionMatrix_clicked)

        self.pbImportBehaviorsFromProject.clicked.connect(self.pbImportBehaviorsFromProject_clicked)

        self.pbImportFromJWatcher.clicked.connect(self.pbImportFromJWatcher_clicked)
        self.pbImportFromTextFile.clicked.connect(self.import_from_text_file)
        self.pb_import_behaviors_from_clipboard.clicked.connect(self.import_behaviors_from_clipboard)

        self.pbExportEthogram.clicked.connect(self.export_ethogram)

        self.twBehaviors.cellChanged[int, int].connect(self.twBehaviors_cellChanged)
        self.twBehaviors.cellDoubleClicked[int, int].connect(self.twBehaviors_cellDoubleClicked)

        # left align table header
        for i in range(self.twBehaviors.columnCount()):
            self.twBehaviors.horizontalHeaderItem(i).setTextAlignment(Qt.AlignLeft)

        # subjects
        self.pbAddSubject.clicked.connect(self.pbAddSubject_clicked)
        self.pbRemoveSubject.clicked.connect(self.pbRemoveSubject_clicked)
        self.pb_remove_all_subjects.clicked.connect(self.remove_all_subjects)

        self.twSubjects.cellChanged[int, int].connect(self.twSubjects_cellChanged)

        self.pb_convert_subjects_key_to_lower.clicked.connect(self.convert_subjects_keys_to_lower_case)

        self.pbImportSubjectsFromProject.clicked.connect(self.pbImportSubjectsFromProject_clicked)
        self.pb_import_subjects_from_clipboard.clicked.connect(self.import_subjects_from_clipboard)

        # independent variables tab
        self.pbAddVariable.clicked.connect(self.pbAddVariable_clicked)
        self.pbRemoveVariable.clicked.connect(self.pbRemoveVariable_clicked)

        self.leLabel.textChanged.connect(self.leLabel_changed)
        self.leDescription.textChanged.connect(self.leDescription_changed)
        self.lePredefined.textChanged.connect(self.lePredefined_changed)
        self.leSetValues.textChanged.connect(self.leSetValues_changed)
        self.dte_default_date.dateTimeChanged.connect(self.dte_default_date_changed)

        self.twVariables.cellClicked[int, int].connect(self.twVariables_cellClicked)

        self.cbType.currentIndexChanged.connect(self.cbtype_changed)
        self.cbType.activated.connect(self.cbtype_activated)

        self.pbImportVarFromProject.clicked.connect(self.pbImportVarFromProject_clicked)

        # observations tab
        self.pbRemoveObservation.clicked.connect(self.pbRemoveObservation_clicked)

        self.pbOK.clicked.connect(self.pbOK_clicked)
        self.pbCancel.clicked.connect(self.pbCancel_clicked)

        self.selected_twvariables_row = -1

        self.pbAddBehaviorsCodingMap.clicked.connect(self.add_behaviors_coding_map)
        self.pbRemoveBehaviorsCodingMap.clicked.connect(self.remove_behaviors_coding_map)

        # converters tab
        self.pb_add_converter.clicked.connect(self.add_converter)
        self.pb_modify_converter.clicked.connect(self.modify_converter)
        self.pb_save_converter.clicked.connect(self.save_converter)
        self.pb_cancel_converter.clicked.connect(self.cancel_converter)
        self.pb_delete_converter.clicked.connect(self.delete_converter)

        self.pb_load_from_file.clicked.connect(lambda: self.load_converters_from_file_repo("file"))
        self.pb_load_from_repo.clicked.connect(lambda: self.load_converters_from_file_repo("repo"))

        self.pb_code_help.clicked.connect(self.pb_code_help_clicked)

        self.row_in_modification = -1
        self.flag_modified = False

        for w in [self.le_converter_name, self.le_converter_description, self.pteCode, self.pb_save_converter, self.pb_cancel_converter]:
            w.setEnabled(False)

        # disable widget for indep var setting
        for widget in [self.leLabel, self.le_converter_description, self.cbType, self.lePredefined, self.dte_default_date,
                       self.leSetValues]:
            widget.setEnabled(False)

        self.twBehaviors.horizontalHeader().sortIndicatorChanged.connect(self.sort_twBehaviors)
        self.twSubjects.horizontalHeader().sortIndicatorChanged.connect(self.sort_twSubjects)
        self.twVariables.horizontalHeader().sortIndicatorChanged.connect(self.sort_twVariables)


    def sort_twBehaviors(self, index, order):
        """order ethogram table"""
        self.twBehaviors.sortItems(index, order)


    def sort_twSubjects(self, index, order):
        """order subjects table"""
        self.twSubjects.sortItems(index, order)


    def sort_twVariables(self, index, order):
        """order variables table"""
        self.twVariables.sortItems(index, order)


    def convert_behaviors_keys_to_lower_case(self):
        """
        convert behaviors key to lower case to help to migrate to v. 7
        """

        try:
            if not self.twBehaviors.rowCount():
                QMessageBox.critical(None, programName, "The ethogram is empty", QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                return

            # check if some keys will be duplicated after conversion
            try:
                all_keys = [self.twBehaviors.item(row, behavioursFields["key"]).text() for row in range(self.twBehaviors.rowCount())]
            except Exception:
                pass
            if all_keys == [x.lower() for x in all_keys]:
                QMessageBox.information(self, programName, "All keys are already lower case")
                return

            if dialog.MessageDialog(programName, "Confirm the conversion of key to lower case.", [YES, CANCEL]) == CANCEL:
                return

            if len([x.lower() for x in all_keys]) != len(set([x.lower() for x in all_keys])):
                if dialog.MessageDialog(programName,
                                        "Some keys will be duplicated after conversion. Proceed?", [YES, CANCEL]) == CANCEL:
                    return

            for row in range(self.twBehaviors.rowCount()):
                if self.twBehaviors.item(row, behavioursFields["key"]).text():
                    self.twBehaviors.item(row, behavioursFields["key"]).setText(self.twBehaviors.item(row,
                                                                                                    behavioursFields["key"]).text().lower())

                # convert modifier shortcuts
                if self.twBehaviors.item(row, behavioursFields["modifiers"]).text():

                    modifiers_dict = (
                        eval(
                            self.twBehaviors.item(
                                row, behavioursFields["modifiers"]
                            ).text()
                        )
                        if self.twBehaviors.item(
                            row, behavioursFields["modifiers"]
                        ).text()
                        else {}
                    )

                    for modifier_set in modifiers_dict:
                        try:
                            for idx2, value in enumerate(modifiers_dict[modifier_set]["values"]):
                                if re.findall(r'\((\w+)\)', value):
                                    modifiers_dict[modifier_set]["values"][idx2] = value.split("(")[
                                                                                                    0] + "(" + \
                                                                                                re.findall(r'\((\w+)\)',
                                                                                                            value)[
                                                                                                    0].lower() + ")" + \
                                                                                                value.split(")")[-1]
                        except Exception:
                            logging.warning("error during conversion of modifier short cut to lower case")

                    self.twBehaviors.item(row, behavioursFields["modifiers"]).setText(str(modifiers_dict))
        except Exception:
            dialog.error_message("convert behaviors keys to lower case", sys.exc_info())


    def convert_subjects_keys_to_lower_case(self):
        """
        convert subjects key to lower case to help to migrate to v. 7
        """
        try:
            # check if some keys will be duplicated after conversion
            try:
                all_keys = [self.twSubjects.item(row, subjectsFields.index("key")).text() for row in range(self.twSubjects.rowCount())]
            except Exception:
                pass
            if all_keys == [x.lower() for x in all_keys]:
                QMessageBox.information(self, programName, "All keys are already lower case")
                return

            if dialog.MessageDialog(programName, "Confirm the conversion of key to lower case.", [YES, CANCEL]) == CANCEL:
                return

            if len([x.lower() for x in all_keys]) != len(set([x.lower() for x in all_keys])):
                if dialog.MessageDialog(programName,
                                        "Some keys will be duplicated after conversion. Proceed?", [YES, CANCEL]) == CANCEL:
                    return

            for row in range(self.twSubjects.rowCount()):
                if self.twSubjects.item(row, subjectsFields.index("key")).text():
                    self.twSubjects.item(row, subjectsFields.index("key")).setText(
                        self.twSubjects.item(row, subjectsFields.index("key")).text().lower())
        except Exception:
            dialog.error_message("convert subjects keys to lower case", sys.exc_info())


    def add_behaviors_coding_map(self):
        """
        Add a behaviors coding map from file
        """

        try:
            fn = QFileDialog().getOpenFileName(self, "Open a behaviors coding map",
                                            "", "Behaviors coding map (*.behav_coding_map);;All files (*)")
            fileName = fn[0] if type(fn) is tuple else fn
            if fileName:
                try:
                    bcm = json.loads(open(fileName, "r").read())
                except Exception:
                    QMessageBox.critical(self, programName, f"The file {fileName} is not a behaviors coding map.")
                    return

                if "coding_map_type" not in bcm or bcm["coding_map_type"] != "BORIS behaviors coding map":
                    QMessageBox.critical(self, programName, f"The file {fileName} is not a BORIS behaviors coding map.")

                if BEHAVIORS_CODING_MAP not in self.pj:
                    self.pj[BEHAVIORS_CODING_MAP] = []

                bcm_code_not_found = []
                existing_codes = [self.pj[ETHOGRAM][key]["code"] for key in self.pj[ETHOGRAM]]
                for code in [bcm["areas"][key]["code"] for key in bcm["areas"]]:
                    if code not in existing_codes:
                        bcm_code_not_found.append(code)

                if bcm_code_not_found:
                    QMessageBox.warning(self, programName,
                                        ("The following behavior{} are not defined in the ethogram:<br>"
                                        "{}").format("s" if len(bcm_code_not_found) > 1 else "", ",".join(bcm_code_not_found)))

                self.pj[BEHAVIORS_CODING_MAP].append(dict(bcm))

                self.twBehavCodingMap.setRowCount(self.twBehavCodingMap.rowCount() + 1)

                self.twBehavCodingMap.setItem(self.twBehavCodingMap.rowCount() - 1, 0, QTableWidgetItem(bcm["name"]))
                codes = ", ".join([bcm["areas"][idx]["code"] for idx in bcm["areas"]])
                self.twBehavCodingMap.setItem(self.twBehavCodingMap.rowCount() - 1, 1, QTableWidgetItem(codes))
        except Exception:
            dialog.error_message("add behaviors coding map", sys.exc_info())


    def remove_behaviors_coding_map(self):
        """
        remove the first selected behaviors coding map
        """
        try:
            if not self.twBehavCodingMap.selectedIndexes():
                QMessageBox.warning(self, programName, "Select a behaviors coding map")
            else:
                if dialog.MessageDialog(programName, "Remove the selected behaviors coding map?", [YES, CANCEL]) == YES:
                    del self.pj[BEHAVIORS_CODING_MAP][self.twBehavCodingMap.selectedIndexes()[0].row()]
                    self.twBehavCodingMap.removeRow(self.twBehavCodingMap.selectedIndexes()[0].row())
        except Exception:
            error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
            logging.critical(f"Error in function '{sys._getframe().f_code.co_name}'': {error_type} {error_file_name} {error_lineno}")
            dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


    def export_ethogram(self):
        """
        export ethogram in various format
        """
        try:
            extended_file_formats = ["Tab Separated Values (*.tsv)",
                                    "Comma Separated Values (*.csv)",
                                    "Open Document Spreadsheet ODS (*.ods)",
                                    "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
                                    "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
                                    "HTML (*.html)"]
            file_formats = ["tsv", "csv", "ods", "xlsx", "xls", "html"]

            filediag_func = QFileDialog().getSaveFileName

            fileName, filter_ = filediag_func(self, "Export ethogram", "", ";;".join(extended_file_formats))
            if not fileName:
                return

            outputFormat = file_formats[extended_file_formats.index(filter_)]
            if pathlib.Path(fileName).suffix != "." + outputFormat:
                fileName = str(pathlib.Path(fileName)) + "." + outputFormat

            ethogram_data = tablib.Dataset()
            ethogram_data.title = "Ethogram"
            if self.leProjectName.text():
                ethogram_data.title = f"Ethogram of {self.leProjectName.text()} project"

            ethogram_data.headers = ["Behavior code", "Behavior type", "Description", "Key", "Behavioral category", "Excluded behaviors"]

            for r in range(self.twBehaviors.rowCount()):
                row = []
                for field in ["code", TYPE, "description", "key", "category", "excluded"]:
                    row.append(self.twBehaviors.item(r, behavioursFields[field]).text())
                ethogram_data.append(row)

            ok, msg = export_observation.dataset_write(ethogram_data, fileName, outputFormat)
            if not ok:
                QMessageBox.critical(None, programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
        except Exception:
            error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
            logging.critical(f"Error in function '{sys._getframe().f_code.co_name}'': {error_type} {error_file_name} {error_lineno}")
            dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


    def leLabel_changed(self):
        try:
            if self.selected_twvariables_row != -1:
                self.twVariables.item(self.selected_twvariables_row, 0).setText(self.leLabel.text())
        except Exception:
            error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
            logging.critical(f"Error in function '{sys._getframe().f_code.co_name}'': {error_type} {error_file_name} {error_lineno}")
            dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


    def leDescription_changed(self):
        try:
            if self.selected_twvariables_row != -1:
                self.twVariables.item(self.selected_twvariables_row, 1).setText(self.leDescription.text())
        except Exception:
            error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
            logging.critical(f"Error in function '{sys._getframe().f_code.co_name}'': {error_type} {error_file_name} {error_lineno}")
            dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


    def lePredefined_changed(self):
        try:
            if self.selected_twvariables_row != -1:
                self.twVariables.item(self.selected_twvariables_row, 3).setText(self.lePredefined.text())
                if not self.lePredefined.hasFocus():
                    r, msg = self.check_indep_var_config()
                    if not r:
                        QMessageBox.warning(self, f"{programName} - Independent variables error", msg)
        except Exception:
            error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
            logging.critical(f"Error in function '{sys._getframe().f_code.co_name}'': {error_type} {error_file_name} {error_lineno}")
            dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


    def leSetValues_changed(self):
        try:
            if self.selected_twvariables_row != -1:
                self.twVariables.item(self.selected_twvariables_row, 4).setText(self.leSetValues.text())
        except Exception:
            error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
            logging.critical(f"Error in function '{sys._getframe().f_code.co_name}'': {error_type} {error_file_name} {error_lineno}")
            dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


    def dte_default_date_changed(self):
        try:
            if self.selected_twvariables_row != -1:
                self.twVariables.item(self.selected_twvariables_row, 3).setText(self.dte_default_date.dateTime().toString(Qt.ISODate))
        except Exception:
            error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
            logging.critical(f"Error in function '{sys._getframe().f_code.co_name}'': {error_type} {error_file_name} {error_lineno}")
            dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


    def pbBehaviorsCategories_clicked(self):
        """
        behavioral categories manager
        """

        try:
            bc = BehavioralCategories(self.pj)

            if bc.exec_():
                self.pj[BEHAVIORAL_CATEGORIES] = []
                for index in range(bc.lw.count()):
                    self.pj[BEHAVIORAL_CATEGORIES].append(bc.lw.item(index).text().strip())

                # check if behavior belong to removed category
                if bc.removed:
                    for row in range(self.twBehaviors.rowCount()):
                        if self.twBehaviors.item(row, behavioursFields["category"]):
                            if self.twBehaviors.item(row, behavioursFields["category"]).text() == bc.removed:
                                if dialog.MessageDialog(
                                    programName,
                                    (f"The <b>{self.twBehaviors.item(row, behavioursFields['code']).text()}</b> behavior belongs "
                                    f"to a behavioral category <b>{self.twBehaviors.item(row, behavioursFields['category']).text()}</b> "
                                    "that is no more in the behavioral categories list.<br><br>"
                                    "Remove the behavior from category?"
                                    ),
                                        [YES, CANCEL]) == YES:
                                    self.twBehaviors.item(row, behavioursFields["category"]).setText("")
                if bc.renamed:
                    for row in range(self.twBehaviors.rowCount()):
                        if self.twBehaviors.item(row, behavioursFields["category"]):
                            if self.twBehaviors.item(row, behavioursFields["category"]).text() == bc.renamed[0]:
                                self.twBehaviors.item(row, behavioursFields["category"]).setText(bc.renamed[1])
        except Exception:
            error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
            logging.critical(f"Error in function '{sys._getframe().f_code.co_name}'': {error_type} {error_file_name} {error_lineno}")
            dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


    def twBehaviors_cellDoubleClicked(self, row, column):
        """
        manage double-click on ethogram table:
        * behavioral category
        * modifiers
        * exclusion
        * modifiers coding map

        Args:
            row (int): row double-clicked
            column (int): column double-clicked
        """

        try:
            # check if double click on excluded column
            if column == behavioursFields["excluded"]:
                self.pbExclusionMatrix_clicked()

            # check if double click on 'coding map' column
            if column == behavioursFields["coding map"]:
                if "with coding map" in self.twBehaviors.item(row, behavioursFields[TYPE]).text():
                    self.behaviorTypeChanged(row)
                else:
                    QMessageBox.information(self, programName, "Change the behavior type on first column to select a coding map")

            # check if double click on category
            if column == behavioursFields["type"]:
                self.behavior_type_doubleclicked(row)

            # behavioral category
            if column == behavioursFields["category"]:
                self.category_doubleclicked(row)

            if column == behavioursFields["modifiers"]:
                # check if behavior has coding map
                if (self.twBehaviors.item(row, behavioursFields["coding map"]) is not None 
                    and self.twBehaviors.item(row, behavioursFields["coding map"]).text()):
                        QMessageBox.warning(self, programName, "Use the coding map to set/modify the areas")
                else:
                    subjects_list = []
                    for subject_row in range(self.twSubjects.rowCount()):
                        key = self.twSubjects.item(subject_row, 0).text() if self.twSubjects.item(subject_row, 0) else ""
                        subjectName = self.twSubjects.item(subject_row, 1).text().strip() if self.twSubjects.item(subject_row, 1) else ""
                        subjects_list.append((subjectName, key))

                    addModifierWindow = add_modifier.addModifierDialog(self.twBehaviors.item(row, column).text(),
                                                                    subjects=subjects_list
                                                                    )
                    addModifierWindow.setWindowTitle(f'Set modifiers for "{self.twBehaviors.item(row, 2).text()}" behavior')
                    if addModifierWindow.exec_():
                        self.twBehaviors.item(row, column).setText(addModifierWindow.getModifiers())
        except Exception:
            error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
            logging.critical(f"Error in function '{sys._getframe().f_code.co_name}'': {error_type} {error_file_name} {error_lineno}")
            dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


    def behavior_type_doubleclicked(self, row):
        """
        select type for behavior
        """

        try:
            if self.twBehaviors.item(row, behavioursFields[TYPE]).text() in BEHAVIOR_TYPES:
                selected = BEHAVIOR_TYPES.index(self.twBehaviors.item(row, behavioursFields[TYPE]).text())
            else:
                selected = 0

            new_type, ok = QInputDialog.getItem(self, "Select a behavior type", "Types of behavior", BEHAVIOR_TYPES, selected, False)

            if ok and new_type:
                self.twBehaviors.item(row, behavioursFields["type"]).setText(new_type)

                self.behaviorTypeChanged(row)
        except Exception:
            error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
            logging.critical(f"Error in function '{sys._getframe().f_code.co_name}'': {error_type} {error_file_name} {error_lineno}")
            dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


    def category_doubleclicked(self, row):
        """
        select category for behavior
        """

        try:
            categories = ["None"] + self.pj[BEHAVIORAL_CATEGORIES] if BEHAVIORAL_CATEGORIES in self.pj else ["None"]

            if self.twBehaviors.item(row, behavioursFields["category"]).text() in categories:
                selected = categories.index(self.twBehaviors.item(row, behavioursFields["category"]).text())
            else:
                selected = 0

            category, ok = QInputDialog.getItem(self, "Select a behavioral category", "Behavioral categories", categories, selected, False)

            if ok and category:
                if category == "None":
                    category = ""
                self.twBehaviors.item(row, behavioursFields["category"]).setText(category)
        except Exception:
            error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
            logging.critical(f"Error in function '{sys._getframe().f_code.co_name}'': {error_type} {error_file_name} {error_lineno}")
            dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


    def check_variable_default_value(self, txt, varType):
        """
        check if variable default value is compatible with variable type
        """
        # check for numeric type
        if varType == NUMERIC:
            try:
                if txt:
                    float(txt)
                return True
            except Exception:
                return False

        return True


    def variableTypeChanged(self, row):
        """
        variable type combobox changed
        """

        try:
            if self.twVariables.cellWidget(row, tw_indVarFields.index("type")).currentText() == SET_OF_VALUES:
                if self.twVariables.item(row, tw_indVarFields.index("possible values")).text() == "NA":
                    self.twVariables.item(row, tw_indVarFields.index("possible values")).setText("Double-click to add values")
            else:
                # check if set of values defined
                if self.twVariables.item(row, tw_indVarFields.index("possible values")).text() not in ["NA", "Double-click to add values"]:
                    if dialog.MessageDialog(programName, "Erase the set of values?", [YES, CANCEL]) == CANCEL:
                        self.twVariables.cellWidget(row, tw_indVarFields.index("type")).setCurrentIndex(SET_OF_VALUES_idx)
                        return
                    else:
                        self.twVariables.item(row, tw_indVarFields.index("possible values")).setText("NA")
                else:
                    self.twVariables.item(row, tw_indVarFields.index("possible values")).setText("NA")

            # check compatibility between variable type and default value
            if not self.check_variable_default_value(self.twVariables.item(row, tw_indVarFields.index("default value")).text(),
                                                     self.twVariables.cellWidget(row, tw_indVarFields.index("type")).currentIndex()):
                QMessageBox.warning(self,
                                    programName + " - Independent variables error",
                    (f"The default value ({self.twVariables.item(row, tw_indVarFields.index('default value')).text()}) "
                        f"of variable <b>{self.twVariables.item(row, tw_indVarFields.index('label')).text()}</b> "
                        "is not compatible with variable type")
                                   )
        except Exception:
            error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
            logging.critical(f"Error in function '{sys._getframe().f_code.co_name}'': {error_type} {error_file_name} {error_lineno}")
            dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


    def check_indep_var_config(self):
        """
        check if default type is compatible with var type
        """

        try:
            existing_var = []
            for r in range(self.twVariables.rowCount()):

                if self.twVariables.item(r, 0).text().strip().upper() in existing_var:
                    return False, f"Row: {r + 1} - The variable label <b>{self.twVariables.item(r, 0).text()}</b> is already in use."

                # check if same lables
                existing_var.append(self.twVariables.item(r, 0).text().strip().upper())

                # check default value
                if (self.twVariables.item(r, 2).text() != TIMESTAMP
                        and not self.check_variable_default_value(self.twVariables.item(r, 3).text(), self.twVariables.item(r, 2).text())):
                    return False, (f"Row: {r + 1} - "
                                f"The default value ({self.twVariables.item(r, 3).text()}) is not compatible "
                                f"with the variable type ({self.twVariables.item(r, 2).text()})")

                # check if default value in set of values
                if self.twVariables.item(r, 2).text() == SET_OF_VALUES and self.twVariables.item(r, 4).text() == "":
                    return False, "No values were defined in set"

                if (self.twVariables.item(r, 2).text() == SET_OF_VALUES
                        and self.twVariables.item(r, 4).text()
                        and self.twVariables.item(r, 3).text()
                        and self.twVariables.item(r, 3).text() not in self.twVariables.item(r, 4).text().split(",")):
                    return False, f"The default value ({self.twVariables.item(r, 3).text()}) is not contained in set of values"

            return True, "OK"
        except Exception:
            error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
            logging.critical(f"Error in function '{sys._getframe().f_code.co_name}'': {error_type} {error_file_name} {error_lineno}")
            dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


    def cbtype_changed(self):

        try:
            self.leSetValues.setVisible(self.cbType.currentText() == SET_OF_VALUES)
            self.label_5.setVisible(self.cbType.currentText() == SET_OF_VALUES)

            self.dte_default_date.setVisible(self.cbType.currentText() == TIMESTAMP)
            self.label_9.setVisible(self.cbType.currentText() == TIMESTAMP)
            self.lePredefined.setVisible(self.cbType.currentText() != TIMESTAMP)
            self.label_4.setVisible(self.cbType.currentText() != TIMESTAMP)
        except Exception:
            error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
            logging.critical(f"Error in function '{sys._getframe().f_code.co_name}'': {error_type} {error_file_name} {error_lineno}")
            dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


    def cbtype_activated(self):

        try:
            if self.cbType.currentText() == TIMESTAMP:
                self.twVariables.item(self.selected_twvariables_row, 3).setText(self.dte_default_date.dateTime().toString(Qt.ISODate))
                self.twVariables.item(self.selected_twvariables_row, 4).setText("")
            else:
                self.twVariables.item(self.selected_twvariables_row, 3).setText(self.lePredefined.text())
                self.twVariables.item(self.selected_twvariables_row, 4).setText("")

            # remove spaces after and before comma
            if self.cbType.currentText() == SET_OF_VALUES:
                self.twVariables.item(self.selected_twvariables_row, 4).setText(
                    ",".join([x.strip() for x in self.leSetValues.text().split(",")]))

            self.twVariables.item(self.selected_twvariables_row, 2).setText(self.cbType.currentText())

            r, msg = self.check_indep_var_config()

            if not r:
                QMessageBox.warning(self, f"{programName} - Independent variables error", msg)
        except Exception:
            error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
            logging.critical(f"Error in function '{sys._getframe().f_code.co_name}'': {error_type} {error_file_name} {error_lineno}")
            dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


    def pbAddVariable_clicked(self):
        """
        add an independent variable
        """
        
        logging.debug("add an independent variable")
        try:
            self.twVariables.setRowCount(self.twVariables.rowCount() + 1)
            self.selected_twvariables_row = self.twVariables.rowCount() - 1

            for idx, field in enumerate(tw_indVarFields):
                if field == "type":
                    item = QTableWidgetItem("numeric")
                else:
                    item = QTableWidgetItem("")
                self.twVariables.setItem(self.twVariables.rowCount() - 1, idx, item)

            self.twVariables.setCurrentCell(self.twVariables.rowCount() - 1, 0)

            self.twVariables_cellClicked(self.twVariables.rowCount() - 1, 0)
        except Exception:
            error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
            logging.critical(f"Error in function '{sys._getframe().f_code.co_name}'': {error_type} {error_file_name} {error_lineno}")
            dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


    def pbRemoveVariable_clicked(self):
        """
        remove the selected independent variable
        """
        logging.debug("remove selected independent variable")

        try:
            if not self.twVariables.selectedIndexes():
                QMessageBox.warning(self, programName, "Select a variable to remove")
            else:
                if dialog.MessageDialog(programName, "Remove the selected variable?", [YES, CANCEL]) == YES:
                    self.twVariables.removeRow(self.twVariables.selectedIndexes()[0].row())

            if self.twVariables.selectedIndexes():
                self.twVariables_cellClicked(self.twVariables.selectedIndexes()[0].row(), 0)
            else:
                self.twVariables_cellClicked(-1, 0)
        except Exception:
            error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
            logging.critical(f"Error in function '{sys._getframe().f_code.co_name}'': {error_type} {error_file_name} {error_lineno}")
            dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


    def pbImportVarFromProject_clicked(self):
        """
        import independent variables from another project
        """

        project_import.import_indep_variables_from_project(self)


    def pbImportSubjectsFromProject_clicked(self):
        """
        import subjects from another project
        """

        project_import.import_subjects_from_project(self)




    def pbImportBehaviorsFromProject_clicked(self):
        """
        import behaviors from another BORIS project
        """

        project_import.import_behaviors_from_project(self)


    def pbExclusionMatrix_clicked(self):
        """
        activate exclusion matrix window
        """

        try:
            if not self.twBehaviors.rowCount():
                QMessageBox.critical(None, programName, "The ethogram is empty",
                QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                return

            for row in range(self.twBehaviors.rowCount()):
                if not self.twBehaviors.item(row, behavioursFields["code"]).text():
                    QMessageBox.critical(None, programName, f"A behavior code is empty at row {row + 1}",
                                        QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                    return

            ex = exclusion_matrix.ExclusionMatrix()

            state_behaviors, point_behaviors, allBehaviors, excl, new_excl = [], [], [], {}, {}

            # list of point events
            for r in range(self.twBehaviors.rowCount()):
                if self.twBehaviors.item(r, behavioursFields[BEHAVIOR_CODE]):
                    if "Point" in self.twBehaviors.item(r, behavioursFields[TYPE]).text():
                        point_behaviors.append(self.twBehaviors.item(r, behavioursFields[BEHAVIOR_CODE]).text())

            # check if point are present and if user want to include them in exclusion matrix
            include_point_events = NO
            if point_behaviors:
                include_point_events = dialog.MessageDialog(programName,
                                                    "Do you want to include the point events in the exclusion matrix?",
                                                            [YES, NO])


            for r in range(self.twBehaviors.rowCount()):

                if self.twBehaviors.item(r, behavioursFields[BEHAVIOR_CODE]):

                    if (include_point_events == YES
                            or (include_point_events == NO and "State" in self.twBehaviors.item(r, behavioursFields[TYPE]).text())):
                        allBehaviors.append(self.twBehaviors.item(r, behavioursFields[BEHAVIOR_CODE]).text())

                    excl[self.twBehaviors.item(r, behavioursFields[BEHAVIOR_CODE]).text()] = self.twBehaviors.item(
                        r, behavioursFields["excluded"]).text().split(",")
                    new_excl[self.twBehaviors.item(r, behavioursFields[BEHAVIOR_CODE]).text()] = []

                    if "State" in self.twBehaviors.item(r, behavioursFields[TYPE]).text():
                        state_behaviors.append(self.twBehaviors.item(r, behavioursFields[BEHAVIOR_CODE]).text())

            logging.debug(f"point behaviors: {point_behaviors}")
            logging.debug(f"state behaviors: {state_behaviors}")

            if not state_behaviors:
                QMessageBox.critical(None, programName, "No state events were defined in ethogram",
                                    QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                return

            logging.debug(f"exclusion matrix {excl}")

            # first row contain state events
            ex.twExclusions.setColumnCount(len(state_behaviors))
            ex.twExclusions.setHorizontalHeaderLabels(state_behaviors)
            ex.twExclusions.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)

            # first column contains all events: point + state
            ex.twExclusions.setRowCount(len(point_behaviors + state_behaviors))
            for idx, header in enumerate(point_behaviors + state_behaviors):
                item = QTableWidgetItem(header)
                if header in point_behaviors:
                    item.setBackground(QColor(0, 200, 200))
                ex.twExclusions.setVerticalHeaderItem(idx, item)
            ex.twExclusions.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

            ex.allBehaviors = allBehaviors
            ex.stateBehaviors = state_behaviors
            ex.point_behaviors = point_behaviors

            ex.checkboxes = {}

            for c, c_name in enumerate(state_behaviors):
                flag_left_bottom = False
                for r, r_name in enumerate(point_behaviors + state_behaviors):
                    if c_name == r_name:
                        flag_left_bottom = True

                    if c_name != r_name:
                        ex.checkboxes[f"{r_name}|{c_name}"] = QCheckBox()
                        ex.checkboxes[f"{r_name}|{c_name}"].setStyleSheet("text-align: center; margin-left:50%; margin-right:50%;")

                        if flag_left_bottom:
                            # hide if cell in left-bottom part of table
                            ex.checkboxes[f"{r_name}|{c_name}"].setEnabled(False)

                        # connect function when a CB is clicked
                        ex.checkboxes[f"{r_name}|{c_name}"].clicked.connect(ex.cb_clicked)
                        if c_name in excl[r_name]:
                            ex.checkboxes[f"{r_name}|{c_name}"].setChecked(True)
                        ex.twExclusions.setCellWidget(r, c, ex.checkboxes[f"{r_name}|{c_name}"])

            ex.twExclusions.resizeColumnsToContents()
            # check corresponding checkbox
            ex.cb_clicked()

            if ex.exec_():
                for c, c_name in enumerate(state_behaviors):
                    for r, r_name in enumerate(point_behaviors + state_behaviors):
                        if c_name != r_name:
                            if ex.twExclusions.cellWidget(r, c).isChecked():
                                if c_name not in new_excl[r_name]:
                                    new_excl[r_name].append(c_name)

                logging.debug(f"new exclusion matrix {new_excl}")

                # update excluded field
                for r in range(self.twBehaviors.rowCount()):
                    if (include_point_events == YES
                            or (include_point_events == NO and "State" in self.twBehaviors.item(r, 0).text())):
                        for e in excl:
                            if e == self.twBehaviors.item(r, behavioursFields[BEHAVIOR_CODE]).text():
                                item = QTableWidgetItem(",".join(new_excl[e]))
                                item.setFlags(Qt.ItemIsEnabled)
                                item.setBackground(QColor(230, 230, 230))
                                self.twBehaviors.setItem(r, behavioursFields["excluded"], item)
        except Exception:
            dialog.error_message("exclusion matrix", sys.exc_info())

    def pbRemoveAllBehaviors_clicked(self):

        if self.twBehaviors.rowCount():

            if dialog.MessageDialog(programName, "Remove all behaviors?", [YES, CANCEL]) == YES:

                try:
                    # delete ethogram rows without behavior code
                    for r in range(self.twBehaviors.rowCount() - 1, -1, -1):
                        if not self.twBehaviors.item(r, PROJECT_BEHAVIORS_CODE_FIELD_IDX).text():
                            self.twBehaviors.removeRow(r)

                    # extract all codes to delete
                    codesToDelete = []
                    row_mem = {}
                    for r in range(self.twBehaviors.rowCount() - 1, -1, -1):
                        if self.twBehaviors.item(r, PROJECT_BEHAVIORS_CODE_FIELD_IDX).text():
                            codesToDelete.append(self.twBehaviors.item(r, PROJECT_BEHAVIORS_CODE_FIELD_IDX).text())
                            row_mem[self.twBehaviors.item(r, PROJECT_BEHAVIORS_CODE_FIELD_IDX).text()] = r

                    # extract all codes used in observations
                    codesInObs = []
                    for obs in self.pj[OBSERVATIONS]:
                        events = self.pj[OBSERVATIONS][obs][EVENTS]
                        for event in events:
                            codesInObs.append(event[EVENT_BEHAVIOR_FIELD_IDX])

                    for codeToDelete in codesToDelete:
                        # if code to delete used in obs ask confirmation
                        if codeToDelete in codesInObs:
                            response = dialog.MessageDialog(programName,
                                                            f"The code <b>{codeToDelete}</b> is used in observations!",
                                                            ['Remove', CANCEL])
                            if response == "Remove":
                                self.twBehaviors.removeRow(row_mem[codeToDelete])
                        else:   # remove without asking
                            self.twBehaviors.removeRow(row_mem[codeToDelete])

                except Exception:
                    error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
                    logging.critical(f"Error in function '{sys._getframe().f_code.co_name}': {error_type} {error_file_name} {error_lineno}")
                    dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


    def pbImportFromJWatcher_clicked(self):
        """
        import behaviors configuration from JWatcher (GDF file)
        """

        project_import.import_from_JWatcher(self)


    def import_from_text_file(self):
        """
        import ethogram from text file
        ethogram must be organized like:
        typeOfBehavior separator key separator behaviorCode [separator description]
        """

        project_import.import_from_text_file(self)


    def import_behaviors_from_clipboard(self):
        """
        import ethogram from clipboard
        """

        project_import.import_behaviors_from_clipboard(self)


    def import_subjects_from_clipboard(self):
        """
        import subjects from clipboard
        """

        project_import.import_subjects_from_clipboard(self)


    def twBehaviors_cellChanged(self, row, column):
        """
        check ethogram
        """

        keys, codes = [], []
        self.lbObservationsState.setText("")

        for r in range(self.twBehaviors.rowCount()):

            # check key
            if self.twBehaviors.item(r, PROJECT_BEHAVIORS_KEY_FIELD_IDX):
                key = self.twBehaviors.item(r, PROJECT_BEHAVIORS_KEY_FIELD_IDX).text()
                # check key length
                if key.upper() not in list(function_keys.values()) and len(key) > 1:
                    self.lbObservationsState.setText('<font color="red">Key length &gt; 1</font>')
                    return

                keys.append(key)

            # check code
            if self.twBehaviors.item(r, PROJECT_BEHAVIORS_CODE_FIELD_IDX):
                if self.twBehaviors.item(r, PROJECT_BEHAVIORS_CODE_FIELD_IDX).text() in codes:
                    self.lbObservationsState.setText(f'<font color="red">Code duplicated at line {r + 1} </font>')
                else:
                    if self.twBehaviors.item(r, PROJECT_BEHAVIORS_CODE_FIELD_IDX).text():
                        codes.append(self.twBehaviors.item(r, PROJECT_BEHAVIORS_CODE_FIELD_IDX).text())


    def pb_clone_behavior_clicked(self):
        """
        clone the selected configuration
        """
        try:
            if not self.twBehaviors.selectedIndexes():
                QMessageBox.about(self, programName, "First select a behavior")
            else:
                self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)

                row = self.twBehaviors.selectedIndexes()[0].row()
                for field in behavioursFields:
                    item = QTableWidgetItem(self.twBehaviors.item(row, behavioursFields[field]))
                    self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, behavioursFields[field], item)
                    if field in [TYPE, "category", "excluded", "coding map", "modifiers"]:
                        item.setFlags(Qt.ItemIsEnabled)
                        item.setBackground(QColor(230, 230, 230))
            self.twBehaviors.scrollToBottom()
        except Exception:
            dialog.error_message("cloning a behavior", sys.exc_info())


    def pbRemoveBehavior_clicked(self):
        """
        remove behavior
        """

        if not self.twBehaviors.selectedIndexes():
            QMessageBox.warning(self, programName, "Select a behaviour to be removed")
        else:
            if dialog.MessageDialog(programName, "Remove the selected behavior?", [YES, CANCEL]) == YES:

                # check if behavior already used in observations
                flag_break = False
                codeToDelete = self.twBehaviors.item(self.twBehaviors.selectedIndexes()[0].row(), 2).text()
                for obs_id in self.pj[OBSERVATIONS]:
                    if codeToDelete in [event[EVENT_BEHAVIOR_FIELD_IDX] for event in self.pj[OBSERVATIONS][obs_id][EVENTS]]:
                        if dialog.MessageDialog(programName, "The code to remove is used in observations!", [REMOVE, CANCEL]) == CANCEL:
                            return
                        break

                self.twBehaviors.removeRow(self.twBehaviors.selectedIndexes()[0].row())
                self.twBehaviors_cellChanged(0, 0)


    def pbAddBehavior_clicked(self):
        """
        add new behavior to ethogram
        """

        try:
            # Add behavior to table
            self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)
            for field_type in behavioursFields:
                item = QTableWidgetItem()
                if field_type == TYPE:
                    item.setText("Point event")
                # no manual editing, gray back ground
                if field_type in [TYPE, "category", "modifiers", "excluded", "coding map"]:
                    item.setFlags(Qt.ItemIsEnabled)
                    item.setBackground(QColor(230, 230, 230))
                self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, behavioursFields[field_type], item)
        except Exception:
            dialog.error_message("adding a new behavior", sys.exc_info())
        self.twBehaviors.scrollToBottom()


    def behaviorTypeChanged(self, row):
        """
        event type combobox changed
        """

        if "with coding map" in self.twBehaviors.item(row, behavioursFields[TYPE]).text():
            # let user select a coding maop
            fn = QFileDialog().getOpenFileName(self,
                                               "Select a coding map for "
                                               f"{self.twBehaviors.item(row, behavioursFields['code']).text()} behavior",
                                               "", "BORIS map files (*.boris_map);;All files (*)")
            fileName = fn[0] if type(fn) is tuple else fn

            if fileName:
                try:
                    new_map = json.loads(open(fileName, "r").read())
                except Exception:
                    QMessageBox.critical(self, programName, "Error reding the file")
                    return
                self.pj[CODING_MAP][new_map["name"]] = new_map

                # add modifiers from coding map areas
                modifstr = str({"0": {"name": new_map["name"], "type": MULTI_SELECTION, "values": list(sorted(new_map['areas'].keys()))}})

                self.twBehaviors.item(row, behavioursFields["modifiers"]).setText(modifstr)
                self.twBehaviors.item(row, behavioursFields["coding map"]).setText(new_map["name"])

            else:
                # if coding map already exists do not reset the behavior type if no filename selected
                if not self.twBehaviors.item(row, behavioursFields["coding map"]).text():
                    QMessageBox.critical(self, programName, 'No coding map was selected.\nEvent type will be reset to "Point event" ')
                    self.twBehaviors.item(row, behavioursFields["type"]).setText("Point event")
        else:
            self.twBehaviors.item(row, behavioursFields["coding map"]).setText("")


    def pbAddSubject_clicked(self):
        """
        add a subject
        """

        try:
            self.twSubjects.setRowCount(self.twSubjects.rowCount() + 1)
            for col in range(len(subjectsFields)):
                item = QTableWidgetItem("")
                self.twSubjects.setItem(self.twSubjects.rowCount() - 1, col, item)
        except Exception:
            dialog.error_message("adding a new subject", sys.exc_info())
        self.twSubjects.scrollToBottom()


    def pbRemoveSubject_clicked(self):
        """
        remove selected subject from subjects list
        control before if subject used in observations
        """
        try:
            if not self.twSubjects.selectedIndexes():
                QMessageBox.warning(self, programName, "Select a subject to remove")
            else:
                if dialog.MessageDialog(programName, "Remove the selected subject?", [YES, CANCEL]) == YES:

                    flagDel = False
                    if self.twSubjects.item(self.twSubjects.selectedIndexes()[0].row(), 1):
                        subjectToDelete = self.twSubjects.item(self.twSubjects.selectedIndexes()[0].row(), 1).text()  # 1: subject name

                        subjectsInObs = []
                        for obs in self.pj[OBSERVATIONS]:
                            events = self.pj[OBSERVATIONS][obs][EVENTS]
                            for event in events:
                                subjectsInObs.append(event[EVENT_SUBJECT_FIELD_IDX])
                        if subjectToDelete in subjectsInObs:
                            if dialog.MessageDialog(programName, "The subject to remove is used in observations!",
                                                    [REMOVE, CANCEL]) == REMOVE:
                                flagDel = True
                        else:
                            # code not used
                            flagDel = True
                    else:
                        flagDel = True

                    if flagDel:
                        self.twSubjects.removeRow(self.twSubjects.selectedIndexes()[0].row())

                    self.twSubjects_cellChanged(0, 0)
        except Exception:
            dialog.error_message("removing subject", sys.exc_info())


    def remove_all_subjects(self):
        """
        remove all subjects.
        Verify if they are used in observations
        """
        try:
            if self.twSubjects.rowCount():

                if dialog.MessageDialog(programName, "Remove all subjects?", [YES, CANCEL]) == YES:

                    # delete ethogram rows without behavior code
                    for r in range(self.twSubjects.rowCount() - 1, -1, -1):
                        if not self.twSubjects.item(r, 1).text():  # no name
                            self.twSubjects.removeRow(r)

                    # extract all subjects names to delete
                    namesToDelete = []
                    row_mem = {}
                    for r in range(self.twSubjects.rowCount() - 1, -1, -1):
                        if self.twSubjects.item(r, 1).text():
                            namesToDelete.append(self.twSubjects.item(r, 1).text())
                            row_mem[self.twSubjects.item(r, 1).text()] = r

                    # extract all subjects name used in observations
                    namesInObs = []
                    for obs in self.pj[OBSERVATIONS]:
                        events = self.pj[OBSERVATIONS][obs][EVENTS]
                        for event in events:
                            namesInObs.append(event[EVENT_SUBJECT_FIELD_IDX])

                    flag_force = False
                    for nameToDelete in namesToDelete:
                        # if name to delete used in obs ask confirmation
                        if nameToDelete in namesInObs and not flag_force:
                            response = dialog.MessageDialog(programName,
                                                            f"The subject <b>{nameToDelete}</b> is used in observations!",
                                                            ["Force removing of all subjects", REMOVE, CANCEL])
                            if response == "Force removing of all subjects":
                                flag_force = True
                                self.twSubjects.removeRow(row_mem[nameToDelete])

                            if response == REMOVE:
                                self.twSubjects.removeRow(row_mem[nameToDelete])
                        else:   # remove without asking
                            self.twSubjects.removeRow(row_mem[nameToDelete])
        except Exception:
            dialog.error_message("removing all subjects", sys.exc_info())


    def twSubjects_cellChanged(self, row: int, column: int):
        """
        check if subject not unique
        """

        subjects, keys = [], []
        self.lbSubjectsState.setText("")

        for r in range(self.twSubjects.rowCount()):

            # check key
            if self.twSubjects.item(r, 0):

                # check key length
                if (self.twSubjects.item(r, 0).text().upper() not in list(function_keys.values())
                        and len(self.twSubjects.item(r, 0).text()) > 1):
                    self.lbSubjectsState.setText((f'<font color="red">Error on key {self.twSubjects.item(r, 0).text()} for subject!</font>'
                                                  "The key is too long (keys must be of one character"
                                                  " except for function keys _F1, F2..._)"))
                    return

                if self.twSubjects.item(r, 0).text() in keys:
                    self.lbSubjectsState.setText(f'<font color="red">Key duplicated at row # {r + 1}</font>')
                else:
                    if self.twSubjects.item(r, 0).text():
                        keys.append(self.twSubjects.item(r, 0).text())

            # check subject
            if self.twSubjects.item(r, 1):
                if self.twSubjects.item(r, 1).text() in subjects:
                    self.lbSubjectsState.setText(f'<font color="red">Subject duplicated at row # {r + 1}</font>')
                else:
                    if self.twSubjects.item(r, 1).text():
                        subjects.append(self.twSubjects.item(r, 1).text())


    def twVariables_cellClicked(self, row, column):
        """
        check if variable default values are compatible with variable type
        """

        self.selected_twvariables_row = row
        logging.debug(f"selected row: {self.selected_twvariables_row}")

        if self.selected_twvariables_row == -1:
            for widget in [self.leLabel, self.leDescription, self.cbType, self.lePredefined, self.dte_default_date, self.leSetValues]:
                widget.setEnabled(False)
                self.leLabel.setText("")
                self.leDescription.setText("")
                self.lePredefined.setText("")
                self.leSetValues.setText("")

                self.cbType.clear()
            return

        # enable widget for indep var setting
        for widget in [self.leLabel, self.leDescription, self.cbType, self.lePredefined, self.dte_default_date, self.leSetValues]:
            widget.setEnabled(True)

        self.leLabel.setText(self.twVariables.item(row, 0).text())
        self.leDescription.setText(self.twVariables.item(row, 1).text())
        self.lePredefined.setText(self.twVariables.item(row, 3).text())
        self.leSetValues.setText(self.twVariables.item(row, 4).text())

        self.cbType.clear()
        self.cbType.addItems(AVAILABLE_INDEP_VAR_TYPES)
        self.cbType.setCurrentIndex(NUMERIC_idx)

        self.cbType.setCurrentIndex(AVAILABLE_INDEP_VAR_TYPES.index(self.twVariables.item(row, 2).text()))


    def pbRemoveObservation_clicked(self):
        """
        remove all selected observations
        """

        try:
            if not self.twObservations.selectedIndexes():
                QMessageBox.warning(self, programName, "No selected observation")
            else:
                response = dialog.MessageDialog(programName, "Are you sure to remove all the selected observation?", [YES, CANCEL])
                if response == YES:
                    rows_to_delete = []
                    for index in self.twObservations.selectedIndexes():
                        rows_to_delete.append(index.row())
                        obs_id = self.twObservations.item(index.row(), 0).text()
                        if obs_id in self.pj[OBSERVATIONS]:
                            del self.pj[OBSERVATIONS][obs_id]

                    for row in sorted(set(rows_to_delete), reverse=True):
                        self.twObservations.removeRow(row)
        except Exception:
            dialog.error_message("removing observation", sys.exc_info())


    def pbCancel_clicked(self):
        if self.flag_modified:
            if dialog.MessageDialog("BORIS", "The converters were modified. Are you sure to cancel?",
                                    [CANCEL, OK]) == OK:
                self.reject()
        else:
            self.reject()


    def pbOK_clicked(self):
        """
        verify project configuration
        """

        if self.lbObservationsState.text():
            QMessageBox.warning(self, programName, self.lbObservationsState.text())
            return

        if self.lbSubjectsState.text():
            QMessageBox.warning(self, programName, self.lbSubjectsState.text())
            return

        self.pj["project_name"] = self.leProjectName.text().strip()
        self.pj["project_date"] = self.dteDate.dateTime().toString(Qt.ISODate)
        self.pj["project_description"] = self.teDescription.toPlainText()

        # time format
        if self.rbSeconds.isChecked():
            self.pj["time_format"] = S
        if self.rbHMS.isChecked():
            self.pj["time_format"] = HHMMSS

        # store subjects
        self.subjects_conf = {}

        # check for leading/trailing spaces in subjects names
        subjects_name_with_leading_trailing_spaces = ""
        for row in range(self.twSubjects.rowCount()):
            if self.twSubjects.item(row, 1):
                if self.twSubjects.item(row, 1).text() != self.twSubjects.item(row, 1).text().strip():
                    subjects_name_with_leading_trailing_spaces += f'"{self.twSubjects.item(row, 1).text()}" '

        remove_leading_trailing_spaces = NO
        if subjects_name_with_leading_trailing_spaces:

            remove_leading_trailing_spaces = dialog.MessageDialog(programName, (
                "Attention! Some leading and/or trailing spaces are present in the following <b>subject name(s)</b>:<br>"
                f"<b>{subjects_name_with_leading_trailing_spaces}</b><br><br>"
                "Do you want to remove the leading and trailing spaces?<br><br>"
                '<font color="red"><b>Be careful with this option'
                " if you have already done observations!</b></font>"
            ), [YES, NO])

        # check subjects
        for row in range(self.twSubjects.rowCount()):
            # check key
            if self.twSubjects.item(row, 0):
                key = self.twSubjects.item(row, 0).text()
            else:
                key = ""

            # check subject name
            if self.twSubjects.item(row, 1):
                if remove_leading_trailing_spaces == YES:
                    subjectName = self.twSubjects.item(row, 1).text().strip()
                else:
                    subjectName = self.twSubjects.item(row, 1).text()

                # check if subject name is empty
                if subjectName == "":
                    QMessageBox.warning(self, programName, f"The subject name can not be empty (check row #{row + 1}).")
                    return

                if "|" in subjectName:
                    QMessageBox.warning(self, programName,
                                        f"The pipe (|) character is not allowed in subject name <b>{subjectName}</b>")
                    return
            else:
                QMessageBox.warning(self, programName, f"Missing subject name in subjects configuration at row #{row + 1}")
                return

            # description
            subjectDescription = ""
            if self.twSubjects.item(row, 2):
                subjectDescription = self.twSubjects.item(row, 2).text().strip()

            self.subjects_conf[str(len(self.subjects_conf))] = {"key": key, "name": subjectName, "description": subjectDescription}

        self.pj[SUBJECTS] = dict(self.subjects_conf)

        # store behaviors
        missing_data = []
        self.obs = {}

        # Ethogram
        # coding maps in ethogram

        # check for leading/trailing space in behaviors and modifiers
        code_with_leading_trailing_spaces, modifiers_with_leading_trailing_spaces = [], []
        for r in range(self.twBehaviors.rowCount()):

            if self.twBehaviors.item(r, behavioursFields["code"]).text() != self.twBehaviors.item(
                    r, behavioursFields["code"]).text().strip():
                code_with_leading_trailing_spaces.append(self.twBehaviors.item(r, behavioursFields["code"]).text())

            if self.twBehaviors.item(r, behavioursFields["modifiers"]).text():
                try:
                    modifiers_dict = eval(self.twBehaviors.item(r, behavioursFields["modifiers"]).text())
                    for k in modifiers_dict:
                        for value in modifiers_dict[k]["values"]:
                            modif_code = value.split(" (")[0]
                            if modif_code.strip() != modif_code:
                                modifiers_with_leading_trailing_spaces.append(modif_code)
                except Exception:
                    logging.critical("error checking leading/trailing spaces in modifiers")

        remove_leading_trailing_spaces = NO
        if code_with_leading_trailing_spaces:
            remove_leading_trailing_spaces = dialog.MessageDialog(
                programName,
                (
                    "<b>Warning!</b> Some leading and/or trailing spaces are present"
                    " in the following behaviors code(s):<br>"
                    f"<b>{'<br>'.join([x.replace(' ', '&#9608;') for x in code_with_leading_trailing_spaces])}</b><br><br>"
                    "Do you want to remove the leading and trailing spaces from behaviors?<br><br>"
                    """<font color="red"><b>Be careful with this option"""
                    """ if you have already done observations!</b></font>"""
                ),
                [YES, NO, CANCEL],
            )
        if remove_leading_trailing_spaces == CANCEL:
            return

        remove_leading_trailing_spaces_in_modifiers = NO
        if modifiers_with_leading_trailing_spaces:
            remove_leading_trailing_spaces_in_modifiers = dialog.MessageDialog(
                programName,
                (
                    "<b>Warning!</b> Some leading and/or trailing spaces are present"
                    " in the following modifier(s):<br>"
                    f"<b>{'<br>'.join([x.replace(' ', '&#9608;') for x in set(modifiers_with_leading_trailing_spaces)])}</b><br><br>"
                    "Do you want to remove the leading and trailing spaces from modifiers?<br><br>"
                    """<font color="red"><b>Be careful with this option"""
                    """ if you have already done observations!</b></font>"""
                ),
                [YES, NO, CANCEL],
            )
        if remove_leading_trailing_spaces_in_modifiers == CANCEL:
            return

        codingMapsList = []
        for r in range(self.twBehaviors.rowCount()):
            row = {}
            for field in behavioursFields:
                if self.twBehaviors.item(r, behavioursFields[field]):

                    # check for | char in code
                    if field == "code" and "|" in self.twBehaviors.item(r, behavioursFields[field]).text():
                        QMessageBox.warning(self, programName,
                                            ("The pipe (|) character is not allowed in code "
                                             f"<b>{self.twBehaviors.item(r, behavioursFields[field]).text()}</b> !"))
                        return

                    if remove_leading_trailing_spaces == YES:
                        row[field] = self.twBehaviors.item(r, behavioursFields[field]).text().strip()
                    else:
                        row[field] = self.twBehaviors.item(r, behavioursFields[field]).text()

                    if field == "modifiers" and row["modifiers"]:

                        if remove_leading_trailing_spaces_in_modifiers == YES:
                            try:
                                modifiers_dict = eval(row["modifiers"])
                                for k in modifiers_dict:
                                    for idx, value in enumerate(modifiers_dict[k]["values"]):
                                        modif_code = value.split(" (")[0]

                                        modifiers_dict[k]["values"][idx] = modifiers_dict[k][
                                            "values"
                                        ][idx].replace(modif_code, modif_code.strip())

                                row["modifiers"] = dict(modifiers_dict)
                            except Exception:

                                logging.critical("Error removing leading/trailing spaces in modifiers")

                                QMessageBox.critical(self, programName, "Error removing leading/trailing spaces in modifiers")

                        else:
                            row["modifiers"] = eval(row["modifiers"])
                else:
                    row[field] = ""

            if (row["type"]) and (row["code"]):
                self.obs[str(len(self.obs))] = row
            else:
                missing_data.append(str(r + 1))

            if self.twBehaviors.item(r, behavioursFields["coding map"]).text():
                codingMapsList.append(self.twBehaviors.item(r, behavioursFields["coding map"]).text())


        # remove coding map from project if not in ethogram
        cmToDelete = []
        for cm in self.pj[CODING_MAP]:
            if cm not in codingMapsList:
                cmToDelete.append(cm)

        for cm in cmToDelete:
            del self.pj[CODING_MAP][cm]

        if missing_data:
            QMessageBox.warning(self, programName, f"Missing data in ethogram at row {','.join(missing_data)} !")
            return

        # check if behavior belong to category that is not in categories list
        behavior_category = []
        for idx in self.obs:
            if BEHAVIOR_CATEGORY in self.obs[idx]:
                if self.obs[idx][BEHAVIOR_CATEGORY]:
                    if self.obs[idx][BEHAVIOR_CATEGORY] not in self.pj[BEHAVIORAL_CATEGORIES]:
                        behavior_category.append((self.obs[idx][BEHAVIOR_CODE], self.obs[idx][BEHAVIOR_CATEGORY]))
        if behavior_category:

            response = dialog.MessageDialog(f"{programName} - Behavioral categories",
                                            ("The behavioral categorie(s) "
                                             f"{', '.join(set(['<b>' + x[1] + '</b>' + ' (used with <b>' + x[0] + '</b>)' for x in behavior_category]))} "
                                             "are no more defined in behavioral categories list"),
                                            ["Add behavioral category/ies", "Ignore", CANCEL])
            if response == "Add behavioral category/ies":
                [self.pj[BEHAVIORAL_CATEGORIES].append(x1) for x1 in set(x[1] for x in behavior_category)]
            if response == CANCEL:
                return

        # delete coding maps loaded in pj and not cited in ethogram
        self.pj[ETHOGRAM] = dict(self.obs)

        # independent variables
        r, msg = self.check_indep_var_config()
        if not r:
            QMessageBox.warning(self, programName + " - Independent variables error", msg)
            return

        self.indVar = {}
        for r in range(self.twVariables.rowCount()):
            row = {}
            for idx, field in enumerate(tw_indVarFields):
                if self.twVariables.item(r, idx):
                    # check if label is empty
                    if field == "label" and self.twVariables.item(r, idx).text() == "":
                        QMessageBox.warning(self, programName,
                                            f"The label of an indipendent variable can not be empty (check row #{r + 1}).")
                        return
                    row[field] = self.twVariables.item(r, idx).text().strip()
                else:
                    row[field] = ""

            self.indVar[str(len(self.indVar))] = row

        self.pj[INDEPENDENT_VARIABLES] = dict(self.indVar)

        # converters
        converters = {}
        for row in range(self.tw_converters.rowCount()):
            converters[self.tw_converters.item(row, 0).text()] = {"name": self.tw_converters.item(row, 0).text(),
                                                                  "description": self.tw_converters.item(row, 1).text(),
                                                                  "code": self.tw_converters.item(row, 2).text().replace("@", "\n")
                                                                  }
        self.pj[CONVERTERS] = dict(converters)

        self.accept()


    def pb_code_help_clicked(self):
        """
        help for writing converters
        """
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Help for writing converters")

        msg.setText(("A converter is a function that will convert a time value from external data into seconds.<br>"
                     "A time value like 00:23:59 must be converted into seconds before to be plotted synchronously with your media.<br>"
                     "For this you can use BORIS native converters or write your own converter.<br>"
                     "A converter must be written using the <a href=\"www.python.org\">Python3</a> language.<br>"
                     ))

        # msg.setInformativeText("This is additional information")

        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()


    def add_converter(self):
        """Add a new converter"""

        for w in [self.le_converter_name, self.le_converter_description, self.pteCode, self.pb_save_converter, self.pb_cancel_converter]:
            w.setEnabled(True)
        # disable buttons
        for w in [self.pb_add_converter, self.pb_modify_converter, self.pb_delete_converter,
                  self.pb_load_from_file, self.pb_load_from_repo, self.tw_converters]:
            w.setEnabled(False)


    def modify_converter(self):
        """Modifiy the selected converter"""

        try:
            if not self.tw_converters.selectedIndexes():
                QMessageBox.warning(self, programName, "Select a converter in the table")
                return

            for w in [self.le_converter_name, self.le_converter_description, self.pteCode, self.pb_save_converter, self.pb_cancel_converter]:
                w.setEnabled(True)

            # disable buttons
            for w in [self.pb_add_converter, self.pb_modify_converter, self.pb_delete_converter,
                    self.pb_load_from_file, self.pb_load_from_repo, self.tw_converters]:
                w.setEnabled(False)

            self.le_converter_name.setText(self.tw_converters.item(self.tw_converters.selectedIndexes()[0].row(), 0).text())
            self.le_converter_description.setText(self.tw_converters.item(self.tw_converters.selectedIndexes()[0].row(), 1).text())
            self.pteCode.setPlainText(self.tw_converters.item(self.tw_converters.selectedIndexes()[0].row(), 2).text().replace("@", "\n"))

            self.row_in_modification = self.tw_converters.selectedIndexes()[0].row()
        except Exception:
            dialog.error_message("modifying a converter", sys.exc_info())


    def code_2_func(self, name, code):
        """
        convert code to function

        Args:
            name (str): function name
            code (str): Python code

        Returns:
            str: string containing Python function
        """

        function = f"def {name}(INPUT):\n"
        function += """    INPUT = INPUT.decode("utf-8") if isinstance(INPUT, bytes) else INPUT\n"""
        function += "\n".join(["    " + row for row in code.split("\n")])
        function += "\n    return OUTPUT"

        return function


    def save_converter(self):
        """Save converter"""

        # check if name
        self.le_converter_name.setText(self.le_converter_name.text().strip())
        if not self.le_converter_name.text():
            QMessageBox.critical(self, "BORIS", "The converter must have a name")
            return

        if not self.le_converter_name.text().replace("_", "a").isalnum():
            QMessageBox.critical(self, "BORIS", "Forbidden characters are used in converter name.<br>Use a..z, A..Z, 0..9 _")
            return

        # test code with exec
        code = self.pteCode.toPlainText()
        if not code:
            QMessageBox.critical(self, "BORIS", "The converter must have Python code")
            return

        function = self.code_2_func(self.le_converter_name.text(), code)

        try:
            exec(function)
        except Exception:
            QMessageBox.critical(self, "BORIS", f"The code produces an error:<br><b>{sys.exc_info()[1]}</b>")
            return

        if self.row_in_modification == -1:
            self.tw_converters.setRowCount(self.tw_converters.rowCount() + 1)
            row = self.tw_converters.rowCount() - 1
        else:
            row = self.row_in_modification

        self.tw_converters.setItem(row, 0, QTableWidgetItem(self.le_converter_name.text()))
        self.tw_converters.setItem(row, 1, QTableWidgetItem(self.le_converter_description.text()))
        self.tw_converters.setItem(row, 2, QTableWidgetItem(self.pteCode.toPlainText().replace("\n", "@")))

        self.row_in_modification = -1

        for w in [self.le_converter_name, self.le_converter_description, self.pteCode]:
            w.setEnabled(False)
            w.clear()
        self.pb_save_converter.setEnabled(False)
        self.pb_cancel_converter.setEnabled(False)
        self.tw_converters.setEnabled(True)

        self.flag_modified = True

        # enable buttons
        for w in [self.pb_add_converter, self.pb_modify_converter, self.pb_delete_converter,
                  self.pb_load_from_file, self.pb_load_from_repo, self.tw_converters]:
            w.setEnabled(True)


    def cancel_converter(self):
        """Cancel converter"""

        for w in [self.le_converter_name, self.le_converter_description, self.pteCode]:
            w.setEnabled(False)
            w.clear()
        self.pb_save_converter.setEnabled(False)
        self.pb_cancel_converter.setEnabled(False)

        # enable buttons
        for w in [self.pb_add_converter, self.pb_modify_converter, self.pb_delete_converter,
                  self.pb_load_from_file, self.pb_load_from_repo, self.tw_converters]:
            w.setEnabled(True)


    def delete_converter(self):
        """Delete selected converter"""

        if self.tw_converters.selectedIndexes():
            if dialog.MessageDialog("BORIS", "Confirm converter deletion", [CANCEL, OK]) == OK:
                self.tw_converters.removeRow(self.tw_converters.selectedIndexes()[0].row())
        else:
            QMessageBox.warning(self, programName, "Select a converter in the table")


    def load_converters_in_table(self):
        """
        load converters in table
        """
        self.tw_converters.setRowCount(0)

        for converter in sorted(self.converters.keys()):
            self.tw_converters.setRowCount(self.tw_converters.rowCount() + 1)
            self.tw_converters.setItem(self.tw_converters.rowCount() - 1, 0,
                                       QTableWidgetItem(converter))  # id / name
            self.tw_converters.setItem(self.tw_converters.rowCount() - 1, 1,
                                       QTableWidgetItem(self.converters[converter]["description"]))
            self.tw_converters.setItem(self.tw_converters.rowCount() - 1, 2,
                                       QTableWidgetItem(self.converters[converter]["code"].replace("\n", "@")))

        [self.tw_converters.resizeColumnToContents(idx) for idx in [0, 1]]


    def load_converters_from_file_repo(self, mode):
        """
        Load converters from file (JSON) or BORIS remote repository

        Args:
            mode (str): string "repo" or "file"
        """

        converters_from_file = {}
        if mode == "file":
            fn = QFileDialog(self).getOpenFileName(self, "Load converters from file", "", "All files (*)")
            file_name = fn[0] if type(fn) is tuple else fn

            if file_name:
                with open(file_name, "r") as f_in:
                    try:
                        converters_from_file = json.loads(f_in.read())["BORIS converters"]
                    except Exception:
                        QMessageBox.critical(self, programName, "This file does not contain converters...")
                        return

        if mode == "repo":

            converters_repo_URL = "http://www.boris.unito.it/archive/converters.json"
            try:
                converters_from_repo = urllib.request.urlopen(converters_repo_URL).read().strip().decode("utf-8")
            except Exception:
                QMessageBox.critical(self, programName, "An error occured during retrieving converters from BORIS remote repository")
                return

            try:
                converters_from_file = eval(converters_from_repo)["BORIS converters"]
            except Exception:
                QMessageBox.critical(self, programName, "An error occured during retrieving converters from BORIS remote repository")
                return


        if converters_from_file:

            diag_choose_conv = dialog.ChooseObservationsToImport("Choose the converters to load:",
                                                                 sorted(list(converters_from_file.keys())))

            if diag_choose_conv.exec_():

                selected_converters = diag_choose_conv.get_selected_observations()
                if selected_converters:

                    # extract converter names from table
                    converter_names = []
                    for row in range(self.tw_converters.rowCount()):
                        converter_names.append(self.tw_converters.item(row, 0).text())

                    for converter in selected_converters:
                        converter_name = converter

                        if converter in converter_names:
                            while True:
                                text, ok = QInputDialog.getText(self, "Converter conflict",
                                                                      "The converter already exists<br>Rename it:",
                                                                      QLineEdit.Normal,
                                                                      converter)
                                if not ok:
                                    break
                                if text in converter_names:
                                    QMessageBox.critical(self, programName, "This name already exists in converters")

                                if not text.replace("_", "a").isalnum():
                                    QMessageBox.critical(self, programName,
                                                         "This name contains forbidden character(s).<br>Use a..z, A..Z, 0..9 _")

                                if text != converter and text not in converter_names and text.replace("_", "a").isalnum():
                                    break

                            if ok:
                                converter_name = text
                            else:
                                continue
                        # test if code does not produce error
                        function = self.code_2_func(converter_name, converters_from_file[converter]["code"])

                        try:
                            exec(function)
                        except Exception:
                            QMessageBox.critical(self, "BORIS",
                                                 (f"The code of {converter_name} converter produces an error: "
                                                  f"<br><b>{sys.exc_info()[1]}</b>"))

                        self.tw_converters.setRowCount(self.tw_converters.rowCount() + 1)
                        self.tw_converters.setItem(self.tw_converters.rowCount() - 1, 0,
                                                   QTableWidgetItem(converter_name))
                        self.tw_converters.setItem(self.tw_converters.rowCount() - 1, 1,
                                                   QTableWidgetItem(converters_from_file[converter]["description"]))
                        self.tw_converters.setItem(self.tw_converters.rowCount() - 1, 2,
                                                   QTableWidgetItem(converters_from_file[converter]["code"].replace("\n", "@")))

                        self.flag_modified = True

                [self.tw_converters.resizeColumnToContents(idx) for idx in [0, 1]]


