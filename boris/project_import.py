import sys
import logging
from boris import dialog
from boris import project_functions
from boris.config import *
import boris.utilities as utilities
from boris import param_panel

from PyQt5.QtWidgets import (QFileDialog, QTableWidgetItem,
                             QApplication, QMessageBox,
                             QListWidgetItem)
from PyQt5.QtCore import (Qt)
from PyQt5.QtGui import (QColor, QFont)


def check_text_file_type(rows):
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


def import_from_text_file(self):

    if self.twBehaviors.rowCount():
        response = dialog.MessageDialog(programName,
                                        "There are behaviors already configured. Do you want to append behaviors or replace them?",
                                        ['Append', 'Replace', CANCEL])
        if response == CANCEL:
            return

    fn = QFileDialog().getOpenFileName(self, "Import behaviors from text file", "",
                                            "Text files (*.txt *.tsv *.csv);;All files (*)")
    fileName = fn[0] if type(fn) is tuple else fn

    if fileName:

        if self.twBehaviors.rowCount() and response == "Replace":
            self.twBehaviors.setRowCount(0)
        try:
            with open(fileName, mode="rb") as f:
                rows_b = f.read().splitlines()

            rows = []
            idx = 1
            for row in rows_b:
                try:
                    rows.append(row.decode("utf-8"))
                except Exception:
                    QMessageBox.critical(None, programName,
                                            (f"Error while reading file\nThe line # {idx}\n"
                                            f"{row}\ncontains characters that are not readable."),
                                            QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                    return
                idx += 1

            fieldSeparator, fieldsNumber = check_text_file_type(rows)

            logging.debug(f"fields separator: {fieldSeparator}  fields number: {fieldsNumber}")

            if fieldSeparator is None:
                QMessageBox.critical(self, programName,
                                        "Separator character not found! Use plain text file and TAB or comma as value separator")
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

                    behavior = {"key": key, "code": code, "description": description, "modifiers": "",
                                "excluded": "", "coding map": "", "category": ""}

                    self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)

                    for field_type in behavioursFields:
                        if field_type == TYPE:
                            item = QTableWidgetItem(DEFAULT_BEHAVIOR_TYPE)
                            # add type combobox
                            if POINT in type_.upper():
                                item = QTableWidgetItem(POINT_EVENT)
                            if STATE in type_.upper():
                                item = QTableWidgetItem(STATE_EVENT)
                        else:
                            item = QTableWidgetItem(behavior[field_type])

                        if field_type not in ETHOGRAM_EDITABLE_FIELDS:
                            item.setFlags(Qt.ItemIsEnabled)
                            item.setBackground(QColor(230, 230, 230))

                        self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, behavioursFields[field_type], item)
        except Exception:
            error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
            logging.critical(f"Error in function '{sys._getframe().f_code.co_name}': {error_type} {error_file_name} {error_lineno}")
            dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


def import_behaviors_from_clipboard(self):
    """
    import ethogram from clipboard
    """

    try:
        cb = QApplication.clipboard()
        cb_text = cb.text()
        if not cb_text:
            QMessageBox.warning(None, programName,
                                    "The clipboard is empty",
                                    QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        if self.twBehaviors.rowCount():
            response = dialog.MessageDialog(programName,
                                            "Some behaviors are already configured. Do you want to append behaviors or replace them?",
                                            ["Append", "Replace", CANCEL])
            if response == CANCEL:
                return

            if response == "Replace":
                self.twBehaviors.setRowCount(0)

        cb_text_splitted = cb_text.split("\n")
        while "" in cb_text_splitted:
            cb_text_splitted.remove("")

        if len(set([len(x.split("\t")) for x in cb_text_splitted])) != 1:
            QMessageBox.warning(None, programName,
                                ("The clipboard content does not have a constant number of fields.<br>"
                                    "From your spreadsheet: CTRL + A (select all cells), CTRL + C (copy to clipboard)"),
                                    QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        for row in cb_text_splitted:
            if set(row.split("\t")) != set([""]):
                behavior = {"type": DEFAULT_BEHAVIOR_TYPE}
                for idx, field in enumerate(row.split("\t")):
                    if idx == 0:
                        behavior["type"] = STATE_EVENT if STATE in field.upper() else (POINT_EVENT if POINT in field.upper() else "")
                    if idx == 1:
                        behavior["key"] = field.strip() if len(field.strip()) == 1 else ""
                    if idx == 2:
                        behavior["code"] = field.strip()
                    if idx == 3:
                        behavior["description"] = field.strip()
                    if idx == 4:
                        behavior["category"] = field.strip()

                self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)

                for field_type in behavioursFields:
                    if field_type == TYPE:
                        item = QTableWidgetItem(behavior.get("type", DEFAULT_BEHAVIOR_TYPE))
                    else:
                        item = QTableWidgetItem(behavior.get(field_type, ""))

                    if field_type not in ETHOGRAM_EDITABLE_FIELDS:  # [TYPE, "excluded", "coding map", "modifiers", "category"]:
                        item.setFlags(Qt.ItemIsEnabled)
                        item.setBackground(QColor(230, 230, 230))

                    self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, behavioursFields[field_type], item)
    except Exception:
        error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
        logging.critical(f"Error in function '{sys._getframe().f_code.co_name}': {error_type} {error_file_name} {error_lineno}")
        dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)



def import_from_JWatcher(self):
    """
    import behaviors configuration from JWatcher (GDF file)
    """
    try:
        if self.twBehaviors.rowCount():
            response = dialog.MessageDialog(programName,
                                            "There are behaviors already configured. Do you want to append behaviors or replace them?",
                                            ["Append", "Replace", CANCEL])
            if response == CANCEL:
                return

        fn = QFileDialog().getOpenFileName(self, "Import behaviors from JWatcher", "", "Global Definition File (*.gdf);;All files (*)")
        fileName = fn[0] if type(fn) is tuple else fn

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
                    if idx < len(rows) and "Behavior.description." in rows[idx + 1]:
                        description = rows[idx + 1].split("=")[-1]

                    behavior = {"key": key, "code": code, "description": description,
                                "modifiers": "", "excluded": "", "coding map": "", "category": ""}

                    self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)

                    for field_type in behavioursFields:
                        if field_type == TYPE:
                            item = QTableWidgetItem(DEFAULT_BEHAVIOR_TYPE)
                        else:
                            item = QTableWidgetItem(behavior[field_type])

                        if field_type in [TYPE, "excluded", "category", "coding map", "modifiers"]:
                            item.setFlags(Qt.ItemIsEnabled)
                            item.setBackground(QColor(230, 230, 230))

                        self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, behavioursFields[field_type], item)
    except Exception:
        error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
        logging.critical(f"Error in function '{sys._getframe().f_code.co_name}'': {error_type} {error_file_name} {error_lineno}")
        dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


def import_subjects_from_clipboard(self):
    """
    import subjects from clipboard
    """
    try:
        cb = QApplication.clipboard()
        cb_text = cb.text()
        if not cb_text:
            QMessageBox.warning(None, programName,
                                    "The clipboard is empty",
                                    QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        if self.twSubjects.rowCount():
            response = dialog.MessageDialog(programName,
                                            "Some subjects are already configured. Do you want to append subjects or replace them?",
                                            ["Append", "Replace", CANCEL])
            if response == CANCEL:
                return

            if response == "Replace":
                self.twSubjects.setRowCount(0)

        cb_text_splitted = cb_text.split("\n")

        if len(set([len(x.split("\t")) for x in cb_text_splitted])) != 1:
            QMessageBox.warning(None, programName,
                                ("The clipboard content does not have a constant number of fields.<br>"
                                    "From your spreadsheet: CTRL + A (select all cells), CTRL + C (copy to clipboard)"),
                                QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        for row in cb_text_splitted:
            if set(row.split("\t")) != set([""]):
                subject = {}
                for idx, field in enumerate(row.split("\t")):
                    if idx == 0:
                        subject["key"] = field.strip() if len(field.strip()) == 1 else ""
                    if idx == 1:
                        subject[SUBJECT_NAME] = field.strip()
                    if idx == 2:
                        subject["description"] = field.strip()

                self.twSubjects.setRowCount(self.twSubjects.rowCount() + 1)

                for idx, field_name in enumerate(subjectsFields):
                    item = QTableWidgetItem(subject.get(field_name, ""))
                    self.twSubjects.setItem(self.twSubjects.rowCount() - 1, idx, item)
    except Exception:
        error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
        logging.critical(f"Error in function '{sys._getframe().f_code.co_name}': {error_type} {error_file_name} {error_lineno}")
        dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


def select_behaviors(title="Record value from external data file",
                     text="Behaviors",
                     behavioral_categories=[],
                     ethogram={},
                     behavior_type=[STATE_EVENT, POINT_EVENT]):
    """
    allow user to select behaviors to import

    Args:
        title (str): title of dialog box
        text (str): text of dialog box
        behavioral_categories (list): behavioral categories
        ethogram (dict): ethogram

    """

    try:
        paramPanelWindow = param_panel.Param_panel()
        paramPanelWindow.resize(800, 600)
        paramPanelWindow.setWindowTitle(title)
        paramPanelWindow.lbBehaviors.setText(text)
        for w in [paramPanelWindow.lwSubjects, paramPanelWindow.pbSelectAllSubjects, paramPanelWindow.pbUnselectAllSubjects,
                paramPanelWindow.pbReverseSubjectsSelection, paramPanelWindow.lbSubjects, paramPanelWindow.cbIncludeModifiers,
                paramPanelWindow.cbExcludeBehaviors, paramPanelWindow.frm_time]:
            w.setVisible(False)

        if behavioral_categories:
            categories = behavioral_categories
            # check if behavior not included in a category
            if "" in [ethogram[idx][BEHAVIOR_CATEGORY] for idx in ethogram
                    if BEHAVIOR_CATEGORY in ethogram[idx]]:
                categories += [""]
        else:
            categories = ["###no category###"]

        for category in categories:

            if category != "###no category###":

                if category == "":
                    paramPanelWindow.item = QListWidgetItem("No category")
                    paramPanelWindow.item.setData(34, "No category")
                else:
                    paramPanelWindow.item = QListWidgetItem(category)
                    paramPanelWindow.item.setData(34, category)

                font = QFont()
                font.setBold(True)
                paramPanelWindow.item.setFont(font)
                paramPanelWindow.item.setData(33, "category")
                paramPanelWindow.item.setData(35, False)

                paramPanelWindow.lwBehaviors.addItem(paramPanelWindow.item)

            # check if behavior type must be shown
            for behavior in [ethogram[x][BEHAVIOR_CODE] for x in utilities.sorted_keys(ethogram)]:

                if ((categories == ["###no category###"]) or
                (behavior in [ethogram[x][BEHAVIOR_CODE] for x in ethogram
                                if BEHAVIOR_CATEGORY in ethogram[x] and
                                    ethogram[x][BEHAVIOR_CATEGORY] == category])):

                    paramPanelWindow.item = QListWidgetItem(behavior)
                    paramPanelWindow.item.setCheckState(Qt.Unchecked)

                    if category != "###no category###":
                        paramPanelWindow.item.setData(33, "behavior")
                        if category == "":
                            paramPanelWindow.item.setData(34, "No category")
                        else:
                            paramPanelWindow.item.setData(34, category)

                    paramPanelWindow.lwBehaviors.addItem(paramPanelWindow.item)

        if paramPanelWindow.exec_():
            return paramPanelWindow.selectedBehaviors

        return []
    except Exception:
        error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
        logging.critical(f"Error in function '{sys._getframe().f_code.co_name}'': {error_type} {error_file_name} {error_lineno}")
        dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)


def import_behaviors_from_project(self):
    try:

        fn = QFileDialog().getOpenFileName(self, "Import behaviors from project file", "",
                                            ("Project files (*.boris *.boris.gz);;"
                                            "All files (*)")
                                            )
        file_name = fn[0] if type(fn) is tuple else fn

        if file_name:
            _, _, project, _ = project_functions.open_project_json(file_name)

            # import behavioral_categories
            if BEHAVIORAL_CATEGORIES in project:
                self.pj[BEHAVIORAL_CATEGORIES] = list(project[BEHAVIORAL_CATEGORIES])

            # configuration of behaviours
            if ETHOGRAM in project and project[ETHOGRAM]:
                if self.twBehaviors.rowCount():
                    response = dialog.MessageDialog(programName,
                                                    ("Some behaviors are already configured. "
                                                        "Do you want to append behaviors or replace them?"),
                                                    ["Append", "Replace", CANCEL])
                    if response == "Replace":
                        self.twBehaviors.setRowCount(0)
                    if response == CANCEL:
                        return

                behaviors_to_import = select_behaviors(title="Select the behaviors to import",
                                                       text="Behaviors",
                                                       behavioral_categories=list(project[BEHAVIORAL_CATEGORIES]),
                                                       ethogram=dict(project[ETHOGRAM]),
                                                       behavior_type=[STATE_EVENT, POINT_EVENT])

                for i in utilities.sorted_keys(project[ETHOGRAM]):

                    if project[ETHOGRAM][i][BEHAVIOR_CODE] not in behaviors_to_import:
                        continue

                    self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)

                    for field in project[ETHOGRAM][i]:

                        item = QTableWidgetItem()

                        if field == TYPE:
                            item.setText(project[ETHOGRAM][i][field])
                            item.setFlags(Qt.ItemIsEnabled)
                            item.setBackground(QColor(230, 230, 230))

                        else:
                            if field == "modifiers" and isinstance(project[ETHOGRAM][i][field], str):
                                modif_set_dict = {}
                                if project[ETHOGRAM][i][field]:
                                    modif_set_list = project[ETHOGRAM][i][field].split("|")
                                    for modif_set in modif_set_list:
                                        modif_set_dict[str(len(modif_set_dict))] = {"name": "", "type": SINGLE_SELECTION,
                                                                                    "values": modif_set.split(",")}
                                project[ETHOGRAM][i][field] = dict(modif_set_dict)

                            item.setText(str(project[ETHOGRAM][i][field]))

                            if field not in ETHOGRAM_EDITABLE_FIELDS:
                                item.setFlags(Qt.ItemIsEnabled)
                                item.setBackground(QColor(230, 230, 230))

                        self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, behavioursFields[field], item)

                self.twBehaviors.resizeColumnsToContents()

            else:
                QMessageBox.warning(self, programName, "No behaviors configuration found in project")

    except Exception:
        error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
        logging.critical(f"Error in function '{sys._getframe().f_code.co_name}': {error_type} {error_file_name} {error_lineno}")
        dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)



def import_subjects_from_project(self):
    """
    import subjects from another project
    """

    try:
        fn = QFileDialog().getOpenFileName(self, "Import subjects from project file", "",
                                        ("Project files (*.boris *.boris.gz);;"
                                            "All files (*)")
                                        )
        file_name = fn[0] if type(fn) is tuple else fn

        if file_name:
            _, _, project, _ = project_functions.open_project_json(file_name)

            if "error" in project:
                logging.debug(project["error"])
                QMessageBox.critical(self, programName, project["error"])
                return

            # configuration of behaviours
            if SUBJECTS in project and project[SUBJECTS]:

                if self.twSubjects.rowCount():
                    response = dialog.MessageDialog(programName,
                                                    ("There are subjects already configured. "
                                                    "Do you want to append subjects or replace them?"),
                                                    ['Append', 'Replace', 'Cancel'])

                    if response == "Replace":
                        self.twSubjects.setRowCount(0)

                    if response == CANCEL:
                        return

                for idx in utilities.sorted_keys(project[SUBJECTS]):

                    self.twSubjects.setRowCount(self.twSubjects.rowCount() + 1)

                    for idx2, sbjField in enumerate(subjectsFields):

                        if sbjField in project[SUBJECTS][idx]:
                            self.twSubjects.setItem(self.twSubjects.rowCount() - 1, idx2,
                                                    QTableWidgetItem(project[SUBJECTS][idx][sbjField]))
                        else:
                            self.twSubjects.setItem(self.twSubjects.rowCount() - 1, idx2, QTableWidgetItem(""))

                self.twSubjects.resizeColumnsToContents()
            else:
                QMessageBox.warning(self, programName, "No subjects configuration found in project")
    except Exception:
        error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
        logging.critical(f"Error in function '{sys._getframe().f_code.co_name}': {error_type} {error_file_name} {error_lineno}")
        dialog.error_message_box(sys._getframe().f_code.co_name, error_type, error_file_name, error_lineno)



def import_indep_variables_from_project(self):
    """
    import independent variables from another project
    """

    try:
        fn = QFileDialog().getOpenFileName(self, "Import independent variables from project file", "",
                                        ("Project files (*.boris *.boris.gz);;"
                                            "All files (*)")
                                        )

        file_name = fn[0] if type(fn) is tuple else fn

        if file_name:

            _, _, project, _ = project_functions.open_project_json(file_name)

            if "error" in project:
                logging.debug(project["error"])
                QMessageBox.critical(self, programName, project["error"])
                return

            # independent variables
            if INDEPENDENT_VARIABLES in project and project[INDEPENDENT_VARIABLES]:

                # check if variables are already present
                existing_var = []

                for r in range(self.twVariables.rowCount()):
                    existing_var.append(self.twVariables.item(r, 0).text().strip().upper())

                for i in utilities.sorted_keys(project[INDEPENDENT_VARIABLES]):

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

    except Exception:
        error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
        logging.critical(f"Import independent variable from project: {error_type} {error_file_name} {error_lineno}")

        dialog.error_message_box("Import independent variable from project", error_type, error_file_name, error_lineno)
