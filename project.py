#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2017 Olivier Friard

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


try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

import logging
import json
from utilities import sorted_keys

from config import *
import add_modifier
import dialog
import tablib
import copy


if QT_VERSION_STR[0] == "4":
    from project_ui import Ui_dlgProject
else:
    from project_ui5 import Ui_dlgProject


class ExclusionMatrix(QDialog):

    def __init__(self):
        super(ExclusionMatrix, self).__init__()

        hbox = QVBoxLayout(self)
        
        self.label = QLabel()
        self.label.setText("Check behaviors excluded by")
        hbox.addWidget(self.label)

        self.twExclusions = QTableWidget()
        hbox.addWidget(self.twExclusions)

        hbox2 = QHBoxLayout(self)
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        hbox2.addItem(spacerItem)

        self.pb_select_all = QPushButton("Select all")
        self.pb_select_all.clicked.connect(lambda: self.pb_cb_selection("select"))
        hbox2.addWidget(self.pb_select_all)

        self.pb_unselect_all = QPushButton("Unselect all")
        self.pb_unselect_all.clicked.connect(lambda: self.pb_cb_selection("unselect"))
        hbox2.addWidget(self.pb_unselect_all)

        self.pb_revert_selection = QPushButton("Revert selection")
        self.pb_revert_selection.clicked.connect(lambda: self.pb_cb_selection("revert"))
        hbox2.addWidget(self.pb_revert_selection)


        self.pbCancel = QPushButton("Cancel")
        self.pbCancel.clicked.connect(self.pbCancel_clicked)
        hbox2.addWidget(self.pbCancel)

        self.pbOK = QPushButton("OK")
        self.pbOK.clicked.connect(self.pbOK_clicked)
        hbox2.addWidget(self.pbOK)

        hbox.addLayout(hbox2)
        self.setLayout(hbox)

        self.setWindowTitle("Behaviors exclusion matrix")
        self.setGeometry(100, 100, 600, 400)

    def pbOK_clicked(self):
        self.accept()

    def pbCancel_clicked(self):
        self.reject()

    def pb_cb_selection(self, mode):
        """
        button for checkbox selection/deselection and revert selection
        """
        for r in range(self.twExclusions.rowCount()):
            for c in range(self.twExclusions.columnCount()):
                if mode == "select":
                    state = True
                if mode == "unselect":
                    state = False
                try:
                    if mode == "revert":
                        state = not self.twExclusions.cellWidget(r, c).isChecked()
                    self.twExclusions.cellWidget(r, c).setChecked(state)
                except:
                    pass
    
class BehavioralCategories(QDialog):

    def __init__(self, behavioralCategories):
        super(BehavioralCategories, self).__init__()

        self.setWindowTitle("Behavioral categories")

        self.vbox = QVBoxLayout(self)

        self.label = QLabel()
        self.label.setText("Behavioral categories")
        self.vbox.addWidget(self.label)

        self.lw = QListWidget()

        for category in behavioralCategories:
            item = QListWidgetItem(category)
            self.lw.addItem(item)

        self.vbox.addWidget(self.lw)

        self.hbox0 = QHBoxLayout(self)
        self.pbAddCategory = QPushButton("Add category")
        self.pbAddCategory.clicked.connect(self.pbAddCategory_clicked)
        self.pbRemoveCategory = QPushButton("Remove category")
        self.pbRemoveCategory.clicked.connect(self.pbRemoveCategory_clicked)
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.hbox0.addItem(spacerItem)
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
        category, ok = QInputDialog.getText(self, "New behavioral category", "Category name:")
        if ok:
            self.lw.addItem(QListWidgetItem(category))

    def pbRemoveCategory_clicked(self):
        for SelectedItem in self.lw.selectedItems():
            self.lw.takeItem(self.lw.row(SelectedItem))



class projectDialog(QDialog, Ui_dlgProject):

    def __init__(self, log_level, parent=None):

        super(projectDialog, self).__init__(parent)
        logging.basicConfig(level=log_level)

        self.setupUi(self)

        self.lbObservationsState.setText("")
        self.lbSubjectsState.setText("")

        # ethogram tab
        self.pbAddBehavior.clicked.connect(self.pbAddBehavior_clicked)
        self.pbCloneBehavior.clicked.connect(self.pb_clone_behavior_clicked)

        self.pbRemoveBehavior.clicked.connect(self.pbRemoveBehavior_clicked)
        self.pbRemoveAllBehaviors.clicked.connect(self.pbRemoveAllBehaviors_clicked)

        self.pbBehaviorsCategories.clicked.connect(self.pbBehaviorsCategories_clicked)

        self.pbExclusionMatrix.clicked.connect(self.pbExclusionMatrix_clicked)

        self.pbImportBehaviorsFromProject.clicked.connect(self.pbImportBehaviorsFromProject_clicked)

        self.pbImportFromJWatcher.clicked.connect(self.pbImportFromJWatcher_clicked)
        self.pbImportFromTextFile.clicked.connect(self.pbImportFromTextFile_clicked)

        self.pbExportEthogram.clicked.connect(self.export_ethogram)

        self.twBehaviors.cellChanged[int, int].connect(self.twBehaviors_cellChanged)
        self.twBehaviors.cellDoubleClicked[int, int].connect(self.twBehaviors_cellDoubleClicked)

        # left align table header
        for i in range(self.twBehaviors.columnCount()):
            self.twBehaviors.horizontalHeaderItem(i).setTextAlignment(Qt.AlignLeft)

        # subjects
        self.pbAddSubject.clicked.connect(self.pbAddSubject_clicked)
        self.pbRemoveSubject.clicked.connect(self.pbRemoveSubject_clicked)
        self.twSubjects.cellChanged[int, int].connect(self.twSubjects_cellChanged)

        self.pbImportSubjectsFromProject.clicked.connect(self.pbImportSubjectsFromProject_clicked)

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
        '''self.cbType.highlighted.connect(self.cbtype_changed)'''

        self.pbImportVarFromProject.clicked.connect(self.pbImportVarFromProject_clicked)

        # observations
        self.pbRemoveObservation.clicked.connect(self.pbRemoveObservation_clicked)

        self.pbOK.clicked.connect(self.pbOK_clicked)
        self.pbCancel.clicked.connect(self.pbCancel_clicked)

        self.selected_twvariables_row = -1
        
        self.pbAddBehaviorsCodingMap.clicked.connect(self.add_behaviors_coding_map)
        self.pbRemoveBehaviorsCodingMap.clicked.connect(self.remove_behaviors_coding_map)

        # disable widget for indep var setting
        for widget in [self.leLabel, self.leDescription, self.cbType, self.lePredefined, self.dte_default_date, self.leSetValues]:
            widget.setEnabled(False)

    def add_behaviors_coding_map(self):
        """
        Add a behaviors coding map from file
        """
        
        fn = QFileDialog(self).getOpenFileName(self, "Open a behaviors coding map", "", "Behaviors coding map (*.behav_coding_map);;All files (*)")
        fileName = fn[0] if type(fn) is tuple else fn
        if fileName:
            try:
                bcm = json.loads(open(fileName, "r").read())
            except:
                QMessageBox.critical(self, programName, "The file {} seems not a behaviors coding map...".format(fileName))
                return              

            if "coding_map_type" not in bcm or bcm["coding_map_type"] != "BORIS behaviors coding map":
                QMessageBox.critical(self, programName, "The file {} seems not a BORIS behaviors coding map...".format(fileName))
            
            if BEHAVIORS_CODING_MAP not in self.pj:
                self.pj[BEHAVIORS_CODING_MAP] = []
                
            bcm_code_not_found = []
            existing_codes = [self.pj[ETHOGRAM][key]["code"] for key in self.pj[ETHOGRAM]]
            for code in [bcm["areas"][key]["code"] for key in bcm["areas"]]:
                if code not in existing_codes:
                    bcm_code_not_found.append(code)
                    
            if bcm_code_not_found:
                QMessageBox.warning(self, programName, ("The following behavior{} are not defined in the ethogram:<br>"
                                                        "{}").format("s" if len(bcm_code_not_found)>1 else "", ",".join(bcm_code_not_found)))

            self.pj[BEHAVIORS_CODING_MAP].append(copy.deepcopy(bcm))
            
            self.twBehavCodingMap.setRowCount(self.twBehavCodingMap.rowCount() + 1)

            self.twBehavCodingMap.setItem(self.twBehavCodingMap.rowCount() - 1, 0, QTableWidgetItem(bcm["name"]))
            codes = ", ".join([bcm["areas"][idx]["code"] for idx in bcm["areas"]])
            self.twBehavCodingMap.setItem(self.twBehavCodingMap.rowCount() - 1, 1, QTableWidgetItem(codes))


    def remove_behaviors_coding_map(self):
        """
        remove the first selected behaviors coding map
        """
        if not self.twBehavCodingMap.selectedIndexes():
            QMessageBox.warning(self, programName, "Select a behaviors coding map")
        else:
            if dialog.MessageDialog(programName, "Remove the selected behaviors coding map?", [YES, CANCEL]) == YES:
                del self.pj[BEHAVIORS_CODING_MAP][self.twBehavCodingMap.selectedIndexes()[0].row()]
                self.twBehavCodingMap.removeRow(self.twBehavCodingMap.selectedIndexes()[0].row())
                


    def export_ethogram(self):
        """
        export ethogram in various format
        """
        while True:
            
            fileFormats = ("Tab Separated Values (*.txt *.tsv);;"
                               "Comma Separated Values (*.txt *.csv);;"
                               "Microsoft Excel XLS (*.xls);;"
                               "Open Document Spreadsheet ODS (*.ods);;"
                               "HTML (*.html);;"
                               "All files (*)")
            
            if QT_VERSION_STR[0] == "4":
                f = QFileDialog(self).getSaveFileNameAndFilter
            else:
                f = QFileDialog(self).getSaveFileName

            fileName, filter_ = f(self, "Export ethogram", "", fileFormats)
            if not fileName:
                return

            outputFormat = ""
            availableFormats = ("tsv", "csv", "xls", "ods", "html")
            for fileExtension in availableFormats:
                if fileExtension in filter_:
                    outputFormat = fileExtension
                    if not fileName.upper().endswith("." + fileExtension.upper()):
                        fileName += "." + fileExtension

            if not outputFormat:
                QMessageBox.warning(self, programName, "Choose a file format", QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            else:
                break
                
        ethogram_data = tablib.Dataset()
        ethogram_data.title = "Ethogram"
        if self.leProjectName.text():
            ethogram_data.title = "Ethogram of {} project".format(self.leProjectName.text())
            
        ethogram_data.headers = ["Behavior code", "Behavior type", "Description", "Key", "Behavioral category", "Excluded behaviors"]
        
        for r in range(0, self.twBehaviors.rowCount()):
            
            row = []
            row.append(self.twBehaviors.item(r, behavioursFields["code"]).text())

            combobox = self.twBehaviors.cellWidget(r, behavioursFields["type"])
            row.append(BEHAVIOR_TYPES[combobox.currentIndex()])
            row.append(self.twBehaviors.item(r, behavioursFields["description"]).text())
            row.append(self.twBehaviors.item(r, behavioursFields["key"]).text())
            row.append(self.twBehaviors.item(r, behavioursFields["category"]).text())
            row.append(self.twBehaviors.item(r, behavioursFields["excluded"]).text())
            ethogram_data.append(row)

        try:
            if outputFormat == "tsv":
                with open(fileName, "wb") as f:
                    f.write(str.encode(ethogram_data.tsv))
            if outputFormat == "csv":
                with open(fileName, "wb") as f:
                    f.write(str.encode(ethogram_data.csv))
            if outputFormat == "ods":
                with open(fileName, "wb") as f:
                    f.write(ethogram_data.ods)
            if outputFormat == "xls":
                
                # check worksheet title
                for forbidden_char in r"\/*[]:?":
                    ethogram_data.title = ethogram_data.title.replace(forbidden_char, " ")
                if len(ethogram_data.title) > 31:
                    ethogram_data.title = ethogram_data.title[:31]

                with open(fileName, "wb") as f:
                    f.write(ethogram_data.xls)
            if outputFormat == "html":
                with open(fileName, "wb") as f:
                    f.write(str.encode(ethogram_data.html))

            '''
            if outputFormat == "xlsx":
                with open(fileName, "wb") as f:
                    f.write(data.xlsx)
            '''

        except:
            errorMsg = sys.exc_info()[1]

            logging.critical(errorMsg)
            QMessageBox.critical(None, programName, str(errorMsg), QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


    def leLabel_changed(self):
        if self.selected_twvariables_row != -1:
            self.twVariables.item(self.selected_twvariables_row, 0).setText(self.leLabel.text())

    def leDescription_changed(self):
        if self.selected_twvariables_row != -1:
            self.twVariables.item(self.selected_twvariables_row, 1).setText(self.leDescription.text())

    def lePredefined_changed(self):
        if self.selected_twvariables_row != -1:
            self.twVariables.item(self.selected_twvariables_row, 3).setText(self.lePredefined.text())
            if not self.lePredefined.hasFocus():
                r, msg = self.check_indep_var_config()
                if not r:
                    QMessageBox.warning(self, programName + " - Independent variables error", msg)

    def leSetValues_changed(self):
        if self.selected_twvariables_row != -1:
            self.twVariables.item(self.selected_twvariables_row, 4).setText(self.leSetValues.text())

    def dte_default_date_changed(self):
        if self.selected_twvariables_row != -1:
            self.twVariables.item(self.selected_twvariables_row, 3).setText(self.dte_default_date.dateTime().toString(Qt.ISODate))


    def pbBehaviorsCategories_clicked(self):
        """

        """

        if BEHAVIORAL_CATEGORIES in self.pj:
            bc = BehavioralCategories(self.pj[BEHAVIORAL_CATEGORIES])
        else:
            bc = BehavioralCategories([])

        if bc.exec_():
            self.pj[BEHAVIORAL_CATEGORIES] = []
            for index in range(bc.lw.count()):
                self.pj[BEHAVIORAL_CATEGORIES].append(bc.lw.item(index).text().strip())


    def twBehaviors_cellDoubleClicked(self, row, column):
        """
        manage double-click on ethogram table:
        * behavior category
        * modifiers
        * exclusion
        * modifiers coding map

        """

        # check if double click on excluded column
        if column == behavioursFields["excluded"]:
            QMessageBox.information(self, programName, "Use the 'Exclusion matrix' button to manage excluded behaviors")

        # check if double click on 'coding map' column
        if column == behavioursFields["coding map"]:

            combobox = self.twBehaviors.cellWidget(row, behavioursFields["type"])
            if "with coding map" in BEHAVIOR_TYPES[combobox.currentIndex()]:
                self.behaviorTypeChanged(row)
            else:
                QMessageBox.information(self, programName, "Change the behavior type on first column to select a coding map")
            

        # check if double click on category
        if column == behavioursFields["category"]:
            self.category_doubleclicked(row)

        if column == behavioursFields["modifiers"]:
            # check if behavior has coding map
            if self.twBehaviors.item(row, behavioursFields["coding map"]).text():
                QMessageBox.warning(self, programName, "Use the coding map to set/modify the areas")
            else:
                addModifierWindow = add_modifier.addModifierDialog(self.twBehaviors.item(row, column).text())
                addModifierWindow.setWindowTitle("""Set modifiers for "{}" behavior""".format(self.twBehaviors.item(row, 2).text()))
                if addModifierWindow.exec_():
                    self.twBehaviors.item(row, column).setText(addModifierWindow.getModifiers())


    def category_doubleclicked(self, row):
        """
        select category for behavior
        """
        if BEHAVIORAL_CATEGORIES in self.pj:
            categories = ["None"] +self.pj[BEHAVIORAL_CATEGORIES]
        else:
            categories = ["None"]

        if self.twBehaviors.item(row, behavioursFields["category"]).text() in categories:
            selected = categories.index(self.twBehaviors.item(row, behavioursFields["category"]).text())
        else:
            selected = 0

        category, ok = QInputDialog.getItem(self, "Select a behavioral category", "Behavioral categories", categories, selected, False)

        if ok and category:
            if category == "None":
                category = ""
            self.twBehaviors.item(row, behavioursFields["category"]).setText(category)


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
            except:
                return False

        return True


    def variableTypeChanged(self, row):
        """
        variable type combobox changed
        """

        if self.twVariables.cellWidget(row, tw_indVarFields.index("type")).currentText() == SET_OF_VALUES:
            if self.twVariables.item(row, tw_indVarFields.index("possible values")).text() == "NA":
                self.twVariables.item(row, tw_indVarFields.index("possible values")).setText("Double-click to add values")
                #self.twVariables.item(row, tw_indVarFields.index("possible values")).setBackground(Qt.red)
        else:
            # check if set of values defined
            if self.twVariables.item(row, tw_indVarFields.index("possible values")).text() not in ["NA","Double-click to add values"]:
                if dialog.MessageDialog(programName, "Erase the set of values?", [YES, CANCEL]) == CANCEL:
                    self.twVariables.cellWidget(row, tw_indVarFields.index("type")).setCurrentIndex(SET_OF_VALUES_idx)
                    return
                else:
                    self.twVariables.item(row, tw_indVarFields.index("possible values")).setText("NA")
            else:
                self.twVariables.item(row, tw_indVarFields.index("possible values")).setText("NA")

            if self.twVariables.cellWidget(row, tw_indVarFields.index("type")).currentText() == TIMESTAMP:
                self.twVariables.item(row, tw_indVarFields.index("default value")).setFlags(Qt.ItemIsEnabled)
            else:
                self.twVariables.item(row, tw_indVarFields.index("default value")).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)


            # check compatibility between variable type and default value
            if not self.check_variable_default_value(self.twVariables.item(row, tw_indVarFields.index("default value")).text(),
                                                   self.twVariables.cellWidget(row, tw_indVarFields.index("type")).currentIndex()):
                QMessageBox.warning(self, programName + " - Independent variables error", "The default value ({0}) of variable <b>{1}</b> is not compatible with variable type".format(
                                    self.twVariables.item(row, tw_indVarFields.index("default value")).text(),
                                    self.twVariables.item(row, tw_indVarFields.index("label")).text()))


    def check_indep_var_config_old(self):
        """
        check if default type is compatible with var type
        """

        self.lePredefined.setStyleSheet("color: rgb(0, 0, 0);")
        if self.cbType.currentText() != TIMESTAMP and not self.check_variable_default_value(self.lePredefined.text(), self.cbType.currentText()):
            self.lePredefined.setStyleSheet("color: rgb(255, 0, 0);")
            return False, "The default value is not compatible with the variable type"

        # check if default value in set of values
        if self.cbType.currentText() == SET_OF_VALUES and self.leSetValues.text() == "":
            return False, "No values were defined in set"

        if self.cbType.currentText() == SET_OF_VALUES and self.leSetValues.text() and self.lePredefined.text() not in self.leSetValues.text().split(","):
            self.lePredefined.setStyleSheet("color: rgb(255, 0, 0);")
            return False

        return True, "OK"


    def check_indep_var_config(self):
        """
        check if default type is compatible with var type
        """

        existing_var = []
        for r in range(self.twVariables.rowCount()):

            if self.twVariables.item(r, 0).text().strip().upper() in existing_var:
                return False, "Row: {} - The variable label <b>{}</b> is already in use." .format(r + 1, self.twVariables.item(r, 0).text())

            # check if same lables
            existing_var.append(self.twVariables.item(r, 0).text().strip().upper())

            # check default value
            if self.twVariables.item(r, 2).text() != TIMESTAMP and not self.check_variable_default_value(self.twVariables.item(r, 3).text(), self.twVariables.item(r, 2).text()):
                return False, "Row: {} - The default value ({}) is not compatible with the variable type ({})".format(r + 1, self.twVariables.item(r, 3).text(), self.twVariables.item(r, 2).text())

            # check if default value in set of values
            if self.twVariables.item(r, 2).text() == SET_OF_VALUES and self.twVariables.item(r, 4).text() == "":
                return False, "No values were defined in set"

            if (self.twVariables.item(r, 2).text() == SET_OF_VALUES
                and self.twVariables.item(r, 4).text()
                and self.twVariables.item(r, 3).text()
                and self.twVariables.item(r, 3).text() not in self.twVariables.item(r, 4).text().split(",")):
                return False, "The default value ({}) is not contained in set of values".format(self.twVariables.item(r, 3).text())


        return True, "OK"


    def cbtype_changed(self):

        print("changed")
        self.leSetValues.setVisible(self.cbType.currentText() == SET_OF_VALUES)
        self.label_5.setVisible(self.cbType.currentText() == SET_OF_VALUES)

        self.dte_default_date.setVisible(self.cbType.currentText() == TIMESTAMP)
        self.label_9.setVisible(self.cbType.currentText() == TIMESTAMP)
        self.lePredefined.setVisible(self.cbType.currentText() != TIMESTAMP)
        self.label_4.setVisible(self.cbType.currentText() != TIMESTAMP)


        '''
        if self.cbType.hasFocus():
            if self.cbType.currentText() == TIMESTAMP:
                self.twVariables.item(self.selected_twvariables_row, 3).setText(self.dte_default_date.dateTime().toString(Qt.ISODate))
                self.twVariables.item(self.selected_twvariables_row, 4).setText("")
            else:
                self.twVariables.item(self.selected_twvariables_row, 3).setText(self.lePredefined.text())
                self.twVariables.item(self.selected_twvariables_row, 4).setText("")

            # remove spaces after and before comma
            if self.cbType.currentText() == SET_OF_VALUES:
                self.twVariables.item(self.selected_twvariables_row, 4).setText( ",".join([x.strip() for x in  self.leSetValues.text().split(",")]))

            self.twVariables.item(self.selected_twvariables_row, 2).setText(self.cbType.currentText())

            r, msg = self.check_indep_var_config()

            if not r:
                QMessageBox.warning(self, programName + " - Independent variables error", msg)
        '''
        
    def cbtype_activated(self):
        
        print("activated")
        
        if self.cbType.currentText() == TIMESTAMP:
            self.twVariables.item(self.selected_twvariables_row, 3).setText(self.dte_default_date.dateTime().toString(Qt.ISODate))
            self.twVariables.item(self.selected_twvariables_row, 4).setText("")
        else:
            self.twVariables.item(self.selected_twvariables_row, 3).setText(self.lePredefined.text())
            self.twVariables.item(self.selected_twvariables_row, 4).setText("")

        # remove spaces after and before comma
        if self.cbType.currentText() == SET_OF_VALUES:
            self.twVariables.item(self.selected_twvariables_row, 4).setText( ",".join([x.strip() for x in  self.leSetValues.text().split(",")]))

        self.twVariables.item(self.selected_twvariables_row, 2).setText(self.cbType.currentText())

        r, msg = self.check_indep_var_config()

        if not r:
            QMessageBox.warning(self, programName + " - Independent variables error", msg)
        



    def pbAddVariable_clicked(self):
        """
        add an independent variable
        """
        logging.debug("add an independent variable")

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


    def pbRemoveVariable_clicked(self):
        """
        remove the selected independent variable
        """
        logging.debug("remove selected independent variable")

        if not self.twVariables.selectedIndexes():
            QMessageBox.warning(self, programName, "Select a variable to remove")
        else:
            if dialog.MessageDialog(programName, "Remove the selected variable?", [YES, CANCEL]) == YES:
                self.twVariables.removeRow(self.twVariables.selectedIndexes()[0].row())

        if self.twVariables.selectedIndexes():
            self.twVariables_cellClicked(self.twVariables.selectedIndexes()[0].row(), 0)
        else:
            self.twVariables_cellClicked(-1, 0)



    def pbImportVarFromProject_clicked(self):
        """
        import independent variables from another project
        """

        fn = QFileDialog(self).getOpenFileName(self, "Import independent variables from project file", "", "Project files (*.boris);;All files (*)")
        fileName = fn[0] if type(fn) is tuple else fn

        if fileName:
            with open(fileName, "r") as infile:
                s = infile.read()
            try:
                project = json.loads(s)
            except:
                QMessageBox.warning(None, programName, "Error while reading independent variables from selected file", QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                return

            # independent variables
            if project[INDEPENDENT_VARIABLES]:

                # check if variables are already present
                existing_var = []

                for r in range(self.twVariables.rowCount()):
                    existing_var.append(self.twVariables.item(r, 0).text().strip().upper())  # = [self.pj[INDEPENDENT_VARIABLES][k]["label"].upper().strip() for k in self.pj[INDEPENDENT_VARIABLES]]

                for i in sorted_keys(project[INDEPENDENT_VARIABLES]):

                    self.twVariables.setRowCount(self.twVariables.rowCount() + 1)
                    flag_renamed = False
                    for idx, field in enumerate(tw_indVarFields):
                        item = QTableWidgetItem()
                        if field in project[INDEPENDENT_VARIABLES][i]:
                            if field == "label":
                                txt = project[INDEPENDENT_VARIABLES][i]["label"].strip()
                                while txt.upper() in existing_var:
                                    txt += "_2"
                                    flag_renamed = True
                            else:
                                txt = project[INDEPENDENT_VARIABLES][i][field].strip()
                            item.setText(txt)
                        else:
                            item.setText("")
                        self.twVariables.setItem(self.twVariables.rowCount() - 1, idx, item)

                self.twVariables.resizeColumnsToContents()
                if flag_renamed:
                    QMessageBox.information(self, programName, "Some variables already present were renamed")

            else:
                QMessageBox.warning(self, programName, "No independent variables found in project")


    def pbImportSubjectsFromProject_clicked(self):
        """
        import subjects from another project
        """
        if QT_VERSION_STR[0] == "4":
            fileName = QFileDialog(self).getOpenFileName(self, "Import subjects from project file", "", "Project files (*.boris);;All files (*)")
        else:
            fileName, _ = QFileDialog(self).getOpenFileName(self, "Import subjects from project file", "", "Project files (*.boris);;All files (*)")

        if fileName:

            with open(fileName, "r") as infile:
                s = infile.read()

            try:
                project = json.loads(s)
            except:
                QMessageBox.warning(None, programName, "Error while reading subjects from selected file", QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                return

            # configuration of behaviours
            if project[SUBJECTS]:

                if self.twSubjects.rowCount():

                    response = dialog.MessageDialog(programName, 'There are subjects already configured. Do you want to append subjects or replace them?', ['Append', 'Replace', 'Cancel'])

                    if response == 'Replace':
                        self.twSubjects.setRowCount(0)

                    if response == CANCEL:
                        return

                for idx in sorted(project[SUBJECTS].keys()):

                    self.twSubjects.setRowCount(self.twSubjects.rowCount() + 1)

                    for idx2, sbjField in enumerate(subjectsFields):

                        if sbjField in project[SUBJECTS][idx]:
                            self.twSubjects.setItem(self.twSubjects.rowCount() - 1, idx2, QTableWidgetItem(project[SUBJECTS][idx][sbjField]))
                        else:
                            self.twSubjects.setItem(self.twSubjects.rowCount() - 1, idx2, QTableWidgetItem(""))

                self.twSubjects.resizeColumnsToContents()
            else:
                QMessageBox.warning(self, programName, "No subjects configuration found in project")


    def pbImportBehaviorsFromProject_clicked(self):
        """
        import behaviors from another project
        """

        fn =  QFileDialog(self).getOpenFileName(self, "Import behaviors from project file", "", "Project files (*.boris);;All files (*)")
        fileName = fn[0] if type(fn) is tuple else fn

        if fileName:
            with open(fileName, "r") as infile:
                s = infile.read()
            try:
                project = json.loads(s)
            except:
                QMessageBox.warning(None, programName, "Error while reading behaviors from selected file", QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                return

            # import behavioral_categories
            if BEHAVIORAL_CATEGORIES in project:
                self.pj[BEHAVIORAL_CATEGORIES] = project[BEHAVIORAL_CATEGORIES]

            # configuration of behaviours
            if project[ETHOGRAM]:

                if self.twBehaviors.rowCount():
                    response = dialog.MessageDialog(programName, "There are behaviors already configured. Do you want to append behaviors or replace them?",
                                                    ["Append", "Replace", CANCEL])
                    if response == "Replace":
                        self.twBehaviors.setRowCount(0)
                    if response == CANCEL:
                        return

                for i in sorted_keys(project[ETHOGRAM]):

                    self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)

                    for field in project[ETHOGRAM][i]:

                        item = QTableWidgetItem()

                        if field == "type":
                            comboBox = QComboBox()
                            comboBox.addItems(BEHAVIOR_TYPES)
                            comboBox.setCurrentIndex(BEHAVIOR_TYPES.index(project[ETHOGRAM][i][field]))
                            self.twBehaviors.setCellWidget(self.twBehaviors.rowCount() - 1, behavioursFields[field], comboBox)

                        else:
                            if field == "modifiers" and isinstance(project[ETHOGRAM][i][field], str):
                                modif_set_dict = {}
                                if project[ETHOGRAM][i][field]:
                                    modif_set_list = project[ETHOGRAM][i][field].split("|")
                                    for modif_set in modif_set_list:
                                        modif_set_dict[str(len(modif_set_dict))] = {"name": "", "type": SINGLE_SELECTION, "values": modif_set.split(",")}
                                project[ETHOGRAM][i][field] = dict(modif_set_dict)

                            item.setText(str(project[ETHOGRAM][i][field]))

                            if field in ["modifiers", "excluded", "category", "coding map"]:
                                item.setFlags(Qt.ItemIsEnabled)

                            self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, behavioursFields[field], item)

                self.twBehaviors.resizeColumnsToContents()

            else:
                QMessageBox.warning(self, programName, "No behaviors configuration found in project")


    def pbExclusionMatrix_clicked(self):
        """
        activate exclusion matrix window
        """

        if not self.twBehaviors.rowCount():
            QMessageBox.warning(None, programName, "The ethogram is empty!", QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        ex = ExclusionMatrix()

        stateBehaviors, allBehaviors, excl, new_excl  = [], [], {}, {}

        flag_point_event_present = False
        for r in range(0, self.twBehaviors.rowCount()):
            if self.twBehaviors.item(r, behavioursFields["code"]):
                if "Point" in BEHAVIOR_TYPES[self.twBehaviors.cellWidget(r, 0).currentIndex()]:
                    flag_point_event_present = True
                    break

        if flag_point_event_present:
            includePointEvents = dialog.MessageDialog(programName, "Do you want to include point events?", [YES, NO])
        else:
            includePointEvents = NO

        for r in range(0, self.twBehaviors.rowCount()):
            combobox = self.twBehaviors.cellWidget(r, 0)
            if self.twBehaviors.item(r, behavioursFields["code"]):

                if includePointEvents == YES or (includePointEvents == NO and "State" in BEHAVIOR_TYPES[combobox.currentIndex()]):
                    allBehaviors.append(self.twBehaviors.item(r, behavioursFields["code"]).text())

                excl[self.twBehaviors.item(r, behavioursFields["code"]).text()] = self.twBehaviors.item(r, behavioursFields["excluded"]).text().split(",")
                new_excl[self.twBehaviors.item(r, behavioursFields["code"]).text()] = []

                if "State" in BEHAVIOR_TYPES[combobox.currentIndex()]:
                    stateBehaviors.append(self.twBehaviors.item(r, behavioursFields["code"]).text())

        logging.debug("all behaviors: {}".format(allBehaviors))
        logging.debug("stateBehaviors: {}".format(stateBehaviors))

        if not stateBehaviors:
            QMessageBox.warning(None, programName, "State events not found in behaviors list!", QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        logging.debug('exclusion matrix {0}'.format(excl))

        # columns contain state events
        ex.twExclusions.setColumnCount(len(stateBehaviors))
        ex.twExclusions.setHorizontalHeaderLabels(stateBehaviors)

        # rows contains all events
        ex.twExclusions.setRowCount(len(allBehaviors))
        ex.twExclusions.setVerticalHeaderLabels(allBehaviors)

        for r in range(len(allBehaviors)):
            for c in range(len(stateBehaviors)):
                if stateBehaviors[c] != allBehaviors[r]:
                    checkBox = QCheckBox()
                    if stateBehaviors[c] in excl[allBehaviors[r]]:  # or headers[ r ] in excl[ headers[c] ]:
                        checkBox.setChecked(True)
                    ex.twExclusions.setCellWidget(r, c, checkBox)

        if ex.exec_():

            for r in range(len(allBehaviors)):
                for c in range(len(stateBehaviors)):
                    if stateBehaviors[c] != allBehaviors[r]:
                        checkBox = ex.twExclusions.cellWidget(r, c)
                        if checkBox.isChecked():

                            s1 = stateBehaviors[c]
                            s2 = allBehaviors[r]

                            if s1 not in new_excl[s2]:
                                new_excl[s2].append(s1)

            logging.debug('new exclusion matrix {0}'.format(new_excl))

            # update excluded field
            for r in range(0, self.twBehaviors.rowCount()):
                if includePointEvents == YES or (includePointEvents == NO and "State" in BEHAVIOR_TYPES[self.twBehaviors.cellWidget(r, 0).currentIndex()]):
                    for e in excl:
                        if e == self.twBehaviors.item(r, behavioursFields['code']).text():
                            item = QTableWidgetItem(','.join(new_excl[e]))
                            item.setFlags(Qt.ItemIsEnabled)
                            self.twBehaviors.setItem(r, behavioursFields['excluded'], item)


    def pbRemoveAllBehaviors_clicked(self):

        if self.twBehaviors.rowCount():

            response = dialog.MessageDialog(programName, "Remove all behaviors?", [YES, CANCEL])

            if response == YES:

                # extract all codes to delete
                codesToDelete = []
                row_mem = {}
                for r in range(self.twBehaviors.rowCount()-1, -1, -1):
                    if self.twBehaviors.item(r, 2).text():
                        codesToDelete.append(self.twBehaviors.item(r, 2).text())
                        row_mem[self.twBehaviors.item(r, 2).text()] = r

                # extract all codes used in observations
                codesInObs = []
                for obs in self.pj[OBSERVATIONS]:
                    events = self.pj[OBSERVATIONS][obs]['events']
                    for event in events:
                        codesInObs.append(event[2])

                for codeToDelete in codesToDelete:
                    # if code to delete used in obs ask confirmation
                    if codeToDelete in codesInObs:
                        response = dialog.MessageDialog(programName, "The code <b>{}</b> is used in observations!".format(codeToDelete), ['Remove', CANCEL])
                        if response == "Remove":
                            self.twBehaviors.removeRow(row_mem[codeToDelete])
                    else:   # remove without asking
                        self.twBehaviors.removeRow(row_mem[codeToDelete])


    def pbImportFromJWatcher_clicked(self):
        """
        import behaviors configuration from JWatcher (GDL file)
        """
        if self.twBehaviors.rowCount():
            response = dialog.MessageDialog(programName, "There are behaviors already configured. Do you want to append behaviors or replace them?", ['Append', 'Replace', CANCEL])
            if response == CANCEL:
                return

        if QT_VERSION_STR[0] == "4":
            fileName = QFileDialog(self).getOpenFileName(self, "Import behaviors from JWatcher", "", "Global Definition File (*.gdf);;All files (*)")
        else:
            fileName, _ = QFileDialog(self).getOpenFileName(self, "Import behaviors from JWatcher", "", "Global Definition File (*.gdf);;All files (*)")
        if fileName:

            if self.twBehaviors.rowCount() and response == "Replace":
                self.twBehaviors.setRowCount(0)

            with open(fileName, "r") as f:
                rows = f.readlines()

            for idx, row in enumerate(rows):
                if row and row[0] == "#":
                    continue

                if "Behavior.name." in row and "=" in row:
                    key, code = row.split('=')
                    key = key.replace("Behavior.name.", "")
                    # read description
                    if idx < len(rows) and "Behavior.description." in rows[idx+1]:
                        description = rows[idx+1].split('=')[-1]

                    behavior = {"key": key, "code": code, "description": description, "modifiers": "", "excluded": "", "coding map": "", "category": ""}

                    self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)

                    signalMapper = QSignalMapper(self)

                    for field_type in behavioursFields:
                        if field_type == TYPE:
                            # add type combobox
                            comboBox = QComboBox()
                            comboBox.addItems(BEHAVIOR_TYPES)
                            comboBox.setCurrentIndex(0)   # event type from jwatcher not known
                            signalMapper.setMapping(comboBox, self.twBehaviors.rowCount() - 1)
                            comboBox.currentIndexChanged["int"].connect(signalMapper.map)
                            self.twBehaviors.setCellWidget(self.twBehaviors.rowCount() - 1, behavioursFields[field_type], comboBox)
                        else:
                            item = QTableWidgetItem(behavior[field_type])
                            if field_type in ["excluded", "category", "coding map", "modifiers"]:
                                item.setFlags(Qt.ItemIsEnabled)
                            self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, behavioursFields[field_type], item)

                    signalMapper.mapped["int"].connect(self.behaviorTypeChanged)

    def check_text_file_type(self, rows):
        """
        check text file
        returns separator and number of fields (if unique)
        """
        separators = "\t,;"
        for separator in separators:
            cs = []
            for row in rows:

                cs.append(row.count(separator))
            if len(set(cs)) == 1:
                return separator, cs[0] + 1
        return None, None


    def pbImportFromTextFile_clicked(self):
        """
        import ethogram from text file
        ethogram must be organized like:
        typeOfBehavior separator key separator behaviorCode [separator description]

        """

        if self.twBehaviors.rowCount():
            response = dialog.MessageDialog(programName, "There are behaviors already configured. Do you want to append behaviors or replace them?", ['Append', 'Replace', CANCEL])
            if response == CANCEL:
                return

        fn = QFileDialog(self).getOpenFileName(self, "Import behaviors from text file", "", "Text files (*.txt *.tsv *.csv);;All files (*)")
        fileName = fn[0] if type(fn) is tuple else fn
        '''
        if QT_VERSION_STR[0] == "4":
            fileName = QFileDialog(self).getOpenFileName(self, "Import behaviors from text file", "", "Text files (*.txt *.tsv *.csv);;All files (*)")
        else:
            fileName, _ = QFileDialog(self).getOpenFileName(self, "Import behaviors from text file", "", "Text files (*.txt *.tsv *.csv);;All files (*)")
        '''

        if fileName:

            if self.twBehaviors.rowCount() and response == "Replace":
                self.twBehaviors.setRowCount(0)

            with open(fileName, mode="rb") as f:
                rows_b = f.read().splitlines()

            rows = []
            idx = 1
            for row in rows_b:
                try:
                    rows.append(row.decode("utf-8"))
                except:
                    QMessageBox.critical(None, programName, "Error while reading file\nThe line # {}\n{}\ncontains characters that are not readable.".format(idx,row), QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                    return
                idx += 1

            fieldSeparator, fieldsNumber = self.check_text_file_type(rows)

            logging.debug("fields separator: {}  fields number: {}".format(fieldSeparator, fieldsNumber))

            if fieldSeparator is None:
                QMessageBox.critical(self, programName, "Separator character not found! Use plain text file and TAB or comma as value separator")
            else:

                for row in rows:

                    type_, key, code, description = "", "", "", ""

                    if fieldsNumber == 3:  # fields: type, key, code
                        type_, key, code = row.split(fieldSeparator)
                        description = ""
                    if fieldsNumber == 4:  # fields:  type, key, code, description
                        type_, key, code, description = row.split(fieldSeparator)

                    if fieldsNumber > 4:
                        type_, key, code, description = row.split(fieldSeparator)[:4]

                    behavior = {"key": key, "code": code, "description": description, "modifiers": "", "excluded": "", "coding map": "", "category": ""}

                    self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)

                    signalMapper = QSignalMapper(self)

                    for field_type in behavioursFields:
                        if field_type == TYPE:
                            # add type combobox
                            comboBox = QComboBox()
                            comboBox.addItems(BEHAVIOR_TYPES)

                            if POINT in type_.upper():
                                comboBox.setCurrentIndex(0)
                            if STATE in type_.upper():
                                comboBox.setCurrentIndex(1)

                            signalMapper.setMapping(comboBox, self.twBehaviors.rowCount() - 1)
                            comboBox.currentIndexChanged["int"].connect(signalMapper.map)
                            self.twBehaviors.setCellWidget(self.twBehaviors.rowCount() - 1, behavioursFields[field_type], comboBox)
                        else:
                            item = QTableWidgetItem(behavior[field_type])
                            if field_type in ["excluded", "coding map", "modifiers", "category"]:
                                item.setFlags(Qt.ItemIsEnabled)
                            self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, behavioursFields[field_type], item)

                    signalMapper.mapped['int'].connect(self.behaviorTypeChanged)


    def twBehaviors_cellChanged(self, row, column):

        keys, codes = [], []
        self.lbObservationsState.setText("")

        for r in range(0, self.twBehaviors.rowCount()):

            # check key
            if self.twBehaviors.item(r, behavioursFields["key"]):
                # check key length
                if self.twBehaviors.item(r, behavioursFields["key"]).text().upper() not in ['F' + str(i) for i in range(1, 13)] \
                   and len(self.twBehaviors.item(r, behavioursFields["key"]).text()) > 1:
                    self.lbObservationsState.setText("""<font color="red">Key length &gt; 1</font>""")
                    return

                keys.append(self.twBehaviors.item(r, behavioursFields["key"]).text())

                # convert to upper text
                self.twBehaviors.item(r, behavioursFields["key"]).setText(self.twBehaviors.item(r, behavioursFields["key"]).text().upper())

            # check code
            if self.twBehaviors.item(r, behavioursFields["code"]):
                if self.twBehaviors.item(r, behavioursFields["code"]).text() in codes:
                    self.lbObservationsState.setText("""<font color="red">Code duplicated at line {} </font>""".format(r + 1))
                else:
                    if self.twBehaviors.item(r, behavioursFields["code"]).text():
                        codes.append(self.twBehaviors.item(r, behavioursFields["code"]).text())

        # check subjects for key duplication
        '''
        for r in range(0, self.twSubjects.rowCount()):
            if self.twSubjects.item(r, fields["key"]):
                if self.twSubjects.item(r, fields["key"]).text() in keys:
                    self.lbObservationsState.setText("""<font color="red">Key found in subjects list at line {} </font>""".format(r + 1))
        '''


    def pb_clone_behavior_clicked(self):
        """
        clone the selected configuration
        """
        if not self.twBehaviors.selectedIndexes():
            QMessageBox.about(self, programName, "First select a behavior")
        else:
            self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)

            row = self.twBehaviors.selectedIndexes()[0].row()
            for field in behavioursFields:

                if field == "type":
                    item = QTableWidgetItem()
                    combobox = self.twBehaviors.cellWidget(row, 0)
                    index = combobox.currentIndex()

                    newComboBox = QComboBox()
                    newComboBox.addItems(BEHAVIOR_TYPES)
                    newComboBox.setCurrentIndex(index)

                    self.twBehaviors.setCellWidget(self.twBehaviors.rowCount() - 1, 0, newComboBox)

                else:
                    item = QTableWidgetItem(self.twBehaviors.item(row, behavioursFields[field]))
                    self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, behavioursFields[field], item)

    def pbRemoveBehavior_clicked(self):
        """
        remove behavior
        """

        if not self.twBehaviors.selectedIndexes():
            QMessageBox.warning(self, programName, "First select a behaviour to remove")
        else:
            if dialog.MessageDialog(programName, "Remove the selected behavior?", [YES, CANCEL]) == YES:

                # check if behavior already used in observations

                codeToDelete = self.twBehaviors.item(self.twBehaviors.selectedIndexes()[0].row(), 2).text()

                codesInObs = []
                for obs in self.pj[OBSERVATIONS]:
                    events = self.pj[OBSERVATIONS][obs]['events']
                    for event in events:
                        codesInObs.append(event[2])

                if codeToDelete in codesInObs:
                    if dialog.MessageDialog(programName, 'The code to remove is used in observations!', [REMOVE, CANCEL]) == REMOVE:
                        self.twBehaviors.removeRow(self.twBehaviors.selectedIndexes()[0].row())

                else:
                    # code not used
                    self.twBehaviors.removeRow(self.twBehaviors.selectedIndexes()[0].row())

                self.twBehaviors_cellChanged(0, 0)


    def pbAddBehavior_clicked(self):
        """
        add new behavior to ethogram
        """

        response = "Point event"

        # Add behavior to table
        self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)

        signalMapper = QSignalMapper(self)

        for field_type in behavioursFields:
            item = QTableWidgetItem()
            if field_type == TYPE:
                # add type combobox
                comboBox = QComboBox()
                comboBox.addItems(BEHAVIOR_TYPES)
                comboBox.setCurrentIndex(BEHAVIOR_TYPES.index(response))

                signalMapper.setMapping(comboBox, self.twBehaviors.rowCount() - 1)
                comboBox.currentIndexChanged["int"].connect(signalMapper.map)
                self.twBehaviors.setCellWidget(self.twBehaviors.rowCount() - 1, behavioursFields[field_type], comboBox)
            else:

                if field_type in ["category", "excluded", "coding map", "modifiers"]:
                    item.setFlags(Qt.ItemIsEnabled)

                self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, behavioursFields[field_type], item)

        signalMapper.mapped["int"].connect(self.behaviorTypeChanged)


    def behaviorTypeChanged(self, row):
        """
        event type combobox changed
        """

        combobox = self.twBehaviors.cellWidget(row, behavioursFields["type"])
        if "with coding map" in BEHAVIOR_TYPES[combobox.currentIndex()]:
            # let user select a coding maop
            
            fn = QFileDialog(self).getOpenFileName(self, "Select a coding map for {} behavior".format(self.twBehaviors.item(row, behavioursFields['code']).text()),
                                                    "", "BORIS map files (*.boris_map);;All files (*)")
            fileName = fn[0] if type(fn) is tuple else fn

            if fileName:
                new_map = json.loads(open(fileName, "r").read())
                self.pj["coding_map"][new_map["name"]] = new_map

                # add modifiers from coding map areas
                modifstr = str({"0": {"name": new_map["name"], "type": MULTI_SELECTION, "values": list(sorted(new_map['areas'].keys()))}})
                
                self.twBehaviors.item(row, behavioursFields['modifiers']).setText(modifstr)
                self.twBehaviors.item(row, behavioursFields['coding map']).setText(new_map["name"])

            else:
                # if coding map already exists do not reset the behavior type if no filename selected
                if not self.twBehaviors.item(row, behavioursFields["coding map"]).text():
                    QMessageBox.critical(self, programName, """No coding map was selected.\nEvent type will be reset to "Point event" """)
                    self.twBehaviors.cellWidget(row, behavioursFields["type"]).setCurrentIndex(0)
        else:
            self.twBehaviors.item(row, behavioursFields["coding map"]).setText("")

    def pbAddSubject_clicked(self):
        """
        add a subject
        """

        self.twSubjects.setRowCount(self.twSubjects.rowCount() + 1)
        for col in range(0, len(subjectsFields)):
            item = QTableWidgetItem("")
            self.twSubjects.setItem(self.twSubjects.rowCount() - 1, col, item)

    def pbRemoveSubject_clicked(self):
        """
        remove selected subject from subjects list
        control before if subject used in observations
        """
        if not self.twSubjects.selectedIndexes():
            QMessageBox.warning(self, programName, "First select a subject to remove")
        else:

            if dialog.MessageDialog(programName, "Remove the selected subject?", [YES, CANCEL]) == YES:

                flagDel = False
                if self.twSubjects.item(self.twSubjects.selectedIndexes()[0].row(), 1):
                    subjectToDelete = self.twSubjects.item(self.twSubjects.selectedIndexes()[0].row(), 1).text()  # 1: subject name

                    subjectsInObs = []
                    for obs in self.pj[OBSERVATIONS]:
                        events = self.pj[OBSERVATIONS][obs]['events']
                        for event in events:
                            subjectsInObs.append(event[1])  # 1: subject name
                    if subjectToDelete in subjectsInObs:
                        if dialog.MessageDialog(programName, "The subject to remove is used in observations!", [REMOVE, CANCEL]) == REMOVE:
                            flagDel = True
                    else:
                        # code not used
                        flagDel = True

                else:
                    flagDel = True

                if flagDel:
                    self.twSubjects.removeRow(self.twSubjects.selectedIndexes()[0].row())

                self.twSubjects_cellChanged(0,0)


    def twSubjects_cellChanged(self, row, column):
        """
        check if subject not unique
        """

        subjects, keys = [], []
        self.lbSubjectsState.setText("")

        for r in range(self.twSubjects.rowCount()):

            # check key
            if self.twSubjects.item(r, 0):

                # check key length
                if self.twSubjects.item(r, 0).text().upper() not in ["F" + str(i) for i in range(1, 13)] \
                   and len(self.twSubjects.item(r, 0).text()) > 1:
                    self.lbSubjectsState.setText(("""<font color="red">Error on key {} for subject!</font>"""
                                                  "The key is too long (keys must be of one character"
                                                  " except for function keys _F1, F2..._)").format(self.twSubjects.item(r, 0).text()))
                    return

                if self.twSubjects.item(r, 0).text() in keys:
                    self.lbSubjectsState.setText("""<font color="red">Key duplicated at row # {}</font>""".format(r + 1))
                else:
                    if self.twSubjects.item(r, 0).text():
                        keys.append(self.twSubjects.item(r, 0).text())

                # convert to upper text
                self.twSubjects.item(r, 0).setText(self.twSubjects.item(r, 0).text().upper())

            # check subject
            if self.twSubjects.item(r, 1):
                if self.twSubjects.item(r, 1).text() in subjects:
                    self.lbSubjectsState.setText("""<font color="red">Subject duplicated at row # {}</font>""".format(r + 1))
                else:
                    if self.twSubjects.item(r, 1).text():
                        subjects.append(self.twSubjects.item(r, 1).text())

        # check behaviours keys
        '''
        for r in range(0, self.twBehaviors.rowCount()):
            # check key
            if self.twBehaviors.item(r, fields['key']):
                if self.twBehaviors.item(r, fields['key']).text() in keys:
                    self.lbSubjectsState.setText("""<font color="red">Key found in behaviours configuration ({}) at line # {} </font>""".format(self.twBehaviors.item(r, fields['key']).text(), r + 1))
        '''


    def twVariables_cellClicked(self, row, column):
        """
        check if variable default values are compatible with variable type
        """

        self.selected_twvariables_row = row
        logging.debug("selected row: {}".format(self.selected_twvariables_row))

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

    def pbCancel_clicked(self):
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

        self.pj["project_name"] = self.leProjectName.text()
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
        for row in range(0, self.twSubjects.rowCount()):
            if self.twSubjects.item(row, 1):
                if self.twSubjects.item(row, 1).text() != self.twSubjects.item(row, 1).text().strip():
                    subjects_name_with_leading_trailing_spaces += '"{}" '.format(self.twSubjects.item(row, 1).text())

        remove_leading_trailing_spaces = NO
        if subjects_name_with_leading_trailing_spaces:
            remove_leading_trailing_spaces = dialog.MessageDialog(programName,
                                            ("Attention! Some leading and/or trailing spaces are present in the following <b>subject name(s)</b>:<br>"
                                            "<b>{}</b><br><br>"
                                            "Do you want to remove the leading and trailing spaces?<br><br>"
                                            """<font color="red"><b>Be careful with this option if you have already done observations!</b></font>""").format(subjects_name_with_leading_trailing_spaces),
                                            [YES, NO])

        for row in range(0, self.twSubjects.rowCount()):
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
                    QMessageBox.warning(self, programName, "The subject name can not be empty (check row #{}).".format(row + 1))
                    return

                if "|" in subjectName:
                    QMessageBox.warning(self, programName, "The pipe (|) character is not allowed in subject name <b>{}</b>".format(subjectName))
                    return
            else:
                QMessageBox.warning(self, programName, "Missing subject name in subjects configuration at row {}".format(row + 1))
                return

            # description
            subjectDescription = ""
            if self.twSubjects.item(row, 2):
                subjectDescription = self.twSubjects.item(row, 2).text().strip()

            self.subjects_conf[str(len(self.subjects_conf))] = {"key": key, "name": subjectName, "description": subjectDescription}

        self.pj[SUBJECTS] =  dict(self.subjects_conf)

        # store behaviors
        missing_data = []

        self.obs = {}

        # coding maps in ethogram
        code_with_leading_trailing_spaces = ""
        for r in range(0, self.twBehaviors.rowCount()):
            if self.twBehaviors.item(r, behavioursFields["code"]).text() != self.twBehaviors.item(r, behavioursFields["code"]).text().strip():
                code_with_leading_trailing_spaces += '"{}" '.format(self.twBehaviors.item(r, behavioursFields["code"]).text())

        remove_leading_trailing_spaces = NO
        if code_with_leading_trailing_spaces:
            remove_leading_trailing_spaces = dialog.MessageDialog(programName,
                                            ("Attention! Some leading and/or trailing spaces are present in the following <b>behaviors code(s)</b>:<br>"
                                            "<b>{}</b><br><br>"
                                            "Do you want to remove the leading and trailing spaces?<br><br>"
                                            """<font color="red"><b>Be careful with this option if you have already done observations!</b></font>""").format(code_with_leading_trailing_spaces),
                                            [YES, NO])

        codingMapsList = []
        for r in range(0, self.twBehaviors.rowCount()):

            row = {}
            for field in behavioursFields:
                if field == "type":
                    combobox = self.twBehaviors.cellWidget(r, behavioursFields["type"])
                    row[field] = BEHAVIOR_TYPES[combobox.currentIndex()]
                else:
                    if self.twBehaviors.item(r, behavioursFields[field]):
                        # check for | char in code
                        if field == "code" and "|" in self.twBehaviors.item(r, behavioursFields[field]).text():
                            QMessageBox.warning(self, programName, "The pipe (|) character is not allowed in code <b>{}</b> !".format(self.twBehaviors.item(r, behavioursFields[field]).text()))
                            return

                        '''
                        if field == "code" and self.twBehaviors.item(r, behavioursFields[field]).text() != self.twBehaviors.item(r, behavioursFields[field]).text().strip():
                            code_with_trailing_spaces += self.twBehaviors.item(r, behavioursFields[field]).text().strip() + " "
                        '''

                        if remove_leading_trailing_spaces == YES:
                            row[field] = self.twBehaviors.item(r, behavioursFields[field]).text().strip()
                        else:
                            row[field] = self.twBehaviors.item(r, behavioursFields[field]).text()

                        if field == "modifiers" and row["modifiers"]:
                            row["modifiers"] = eval(row["modifiers"])

                    else:
                        row[field] = ""

            if (row["type"]) and (row["key"]) and (row["code"]):
                self.obs[str(len(self.obs))] = row
            else:
                missing_data.append(str(r + 1))

            if self.twBehaviors.item(r, behavioursFields["coding map"]).text():
                codingMapsList.append(self.twBehaviors.item(r, behavioursFields["coding map"]).text())


        # remove coding map from project if not in ethogram
        cmToDelete = []
        for cm in self.pj["coding_map"]:
            if cm not in codingMapsList:
                cmToDelete.append(cm)

        for cm in cmToDelete:
            del self.pj["coding_map"][cm]

        if missing_data:
            QMessageBox.warning(self, programName, "Missing data in ethogram at row{} !".format(",".join(missing_data)))
            return

        # delete coding maps loaded in pj and not cited in ethogram
        '''
        for loadedCodingMap in loadedCodingMaps:
            del self.pj['coding_map'][ loadedCodingMap ]
        '''

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
                    if field  == "label" and self.twVariables.item(r, idx).text() == "":
                        QMessageBox.warning(self, programName, "The label of an indipendent variable can not be empty (check row #{}).".format(r + 1))
                        return
                    row[field] = self.twVariables.item(r, idx).text().strip()
                else:
                    row[field] = ""

            self.indVar[str(len(self.indVar))] = row

        self.pj[INDEPENDENT_VARIABLES] = dict(self.indVar)

        self.accept()



