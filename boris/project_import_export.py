"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2024 Olivier Friard

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

import logging
import urllib
import json
import pathlib as pl
import pandas as pd
import tablib
import pickle

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QApplication, QFileDialog, QListWidgetItem, QMessageBox, QTableWidgetItem


from . import config as cfg
from . import dialog, param_panel, project_functions, export_observation
from . import utilities as util


def export_project_as_pickle_object(pj: dict) -> None:
    """
    export the project dictionary as a pickle file
    """
    file_name, _ = QFileDialog().getSaveFileName(None, "Export project as pickle file", "", "All files (*)")
    if not file_name:
        return
    try:
        with open(file_name, "wb") as f_out:
            pickle.dump(pj, f_out)
    except Exception:
        QMessageBox.critical(
            None,
            cfg.programName,
            "Error during file saving.",
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )


def export_ethogram(self) -> None:
    """
    export ethogram in various format
    """
    extended_file_formats: list = [
        "BORIS project file (*.boris)",
        "Tab Separated Values (*.tsv)",
        "Comma Separated Values (*.csv)",
        "Open Document Spreadsheet ODS (*.ods)",
        "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
        "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
        "HTML (*.html)",
    ]
    file_formats: list = ["boris", cfg.TSV_EXT, cfg.CSV_EXT, cfg.ODS_EXT, cfg.XLSX_EXT, cfg.XLS_EXT, cfg.HTML_EXT]

    filediag_func = QFileDialog().getSaveFileName

    file_name, filter_ = filediag_func(self, "Export ethogram", "", ";;".join(extended_file_formats))
    if not file_name:
        return

    output_format: str = file_formats[extended_file_formats.index(filter_)]
    if pl.Path(file_name).suffix != "." + output_format:
        file_name = str(pl.Path(file_name)) + "." + output_format

    if output_format == "boris":
        r = self.check_ethogram()
        if cfg.CANCEL in r:
            return
        pj = dict(cfg.EMPTY_PROJECT)
        pj[cfg.ETHOGRAM] = dict(r)
        # behavioral categories

        pj[cfg.BEHAVIORAL_CATEGORIES] = list(self.pj[cfg.BEHAVIORAL_CATEGORIES])

        # project file indentation
        file_indentation = self.config_param.get(cfg.PROJECT_FILE_INDENTATION, cfg.PROJECT_FILE_INDENTATION_DEFAULT_VALUE)
        try:
            with open(file_name, "w") as f_out:
                f_out.write(json.dumps(pj, indent=file_indentation))
        except Exception:
            QMessageBox.critical(
                None,
                cfg.programName,
                "Error during file saving.",
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )

    else:
        ethogram_data = tablib.Dataset()
        ethogram_data.title = "Ethogram"
        if self.leProjectName.text():
            ethogram_data.title = f"Ethogram of {self.leProjectName.text()} project"

        ethogram_data.headers = [
            "Behavior code",
            "Behavior type",
            "Description",
            "Key",
            "Color",
            "Behavioral category",
            "Excluded behaviors",
            "Modifiers",
            "Modifiers (JSON)",
        ]

        for r in range(self.twBehaviors.rowCount()):
            row: list = []
            for field in ("code", cfg.TYPE, "description", "key", cfg.COLOR, "category", "excluded"):
                row.append(self.twBehaviors.item(r, cfg.behavioursFields[field]).text())

            # modifiers
            if self.twBehaviors.item(r, cfg.behavioursFields[cfg.MODIFIERS]).text():
                # modifiers a string
                modifiers_dict = eval(self.twBehaviors.item(r, cfg.behavioursFields[cfg.MODIFIERS]).text())
                modifiers_list = []
                for key in modifiers_dict:
                    values = ",".join(modifiers_dict[key]["values"])
                    modifiers_list.append(f"{modifiers_dict[key]['name']}:{values}")
                row.append(";".join(modifiers_list))
                # modifiers as JSON
                row.append(self.twBehaviors.item(r, cfg.behavioursFields[cfg.MODIFIERS]).text())
            else:
                # modifiers a string
                row.append("")
                # modifiers as JSON
                row.append("")

            ethogram_data.append(row)

        ok, msg = export_observation.dataset_write(ethogram_data, file_name, output_format)
        if not ok:
            QMessageBox.critical(None, cfg.programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


def export_subjects(self) -> None:
    """
    export the subjetcs list in various format
    """
    extended_file_formats: list = [
        cfg.TSV,
        cfg.CSV,
        cfg.ODS,
        cfg.XLSX,
        cfg.XLS,
        cfg.HTML,
    ]
    file_formats: list = [cfg.TSV_EXT, cfg.CSV_EXT, cfg.ODS_EXT, cfg.XLSX_EXT, cfg.XLS_EXT, cfg.HTML_EXT]

    filediag_func = QFileDialog().getSaveFileName

    file_name, filter_ = filediag_func(self, "Export the subjects list", "", ";;".join(extended_file_formats))
    if not file_name:
        return

    outputFormat = file_formats[extended_file_formats.index(filter_)]
    if pl.Path(file_name).suffix != "." + outputFormat:
        file_name = str(pl.Path(file_name)) + "." + outputFormat

    subjects_data = tablib.Dataset()
    subjects_data.title = "Subjects"
    if self.leProjectName.text():
        subjects_data.title = f"Subjects defined in the {self.leProjectName.text()} project"

    subjects_data.headers: list = [
        "Key",
        "Subject name",
        "Description",
    ]

    for r in range(self.twSubjects.rowCount()):
        row: list = []
        for idx, _ in enumerate(("Key", "Subject name", "Description")):
            row.append(self.twSubjects.item(r, idx).text())

        subjects_data.append(row)

    ok, msg = export_observation.dataset_write(subjects_data, file_name, outputFormat)
    if not ok:
        QMessageBox.critical(None, cfg.programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


def select_behaviors(
    title: str = "Record value from external data file",
    text: str = "Behaviors",
    behavioral_categories: list = [],
    ethogram: dict = {},
    behavior_type=[cfg.STATE_EVENT, cfg.POINT_EVENT],
) -> list:
    """
    allow user to select behaviors to import

    Args:
        title (str): title of dialog box
        text (str): text of dialog box
        behavioral_categories (list): behavioral categories
        ethogram (dict): ethogram

    """

    paramPanelWindow = param_panel.Param_panel()
    paramPanelWindow.resize(800, 600)
    paramPanelWindow.setWindowTitle(title)
    paramPanelWindow.lbBehaviors.setText(text)
    for w in [
        paramPanelWindow.lwSubjects,
        paramPanelWindow.pbSelectAllSubjects,
        paramPanelWindow.pbUnselectAllSubjects,
        paramPanelWindow.pbReverseSubjectsSelection,
        paramPanelWindow.lbSubjects,
        paramPanelWindow.cbIncludeModifiers,
        paramPanelWindow.cbExcludeBehaviors,
        paramPanelWindow.frm_time,
        paramPanelWindow.frm_time_bin_size,
    ]:
        w.setVisible(False)

    if behavioral_categories:
        categories = behavioral_categories
        # check if behavior not included in a category
        if "" in [ethogram[idx][cfg.BEHAVIOR_CATEGORY] for idx in ethogram if cfg.BEHAVIOR_CATEGORY in ethogram[idx]]:
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
        for behavior in [ethogram[x][cfg.BEHAVIOR_CODE] for x in util.sorted_keys(ethogram)]:
            if (categories == ["###no category###"]) or (
                behavior
                in [
                    ethogram[x][cfg.BEHAVIOR_CODE]
                    for x in ethogram
                    if cfg.BEHAVIOR_CATEGORY in ethogram[x] and ethogram[x][cfg.BEHAVIOR_CATEGORY] == category
                ]
            ):
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


def check_text_file_type(rows: list):
    """
    check text file
    returns separator and number of fields (if unique)
    """
    for separator in "\t,;":
        cs: list = []
        for row in rows:
            cs.append(row.count(separator))
        if len(set(cs)) == 1:
            return separator, cs[0] + 1
    return None, None


def import_ethogram_from_dict(self, project: dict):
    """
    Import behaviors from a BORIS project dictionary
    """
    # import behavioral_categories
    self.pj[cfg.BEHAVIORAL_CATEGORIES] = list(project.get(cfg.BEHAVIORAL_CATEGORIES, []))

    # configuration of behaviours
    if not (cfg.ETHOGRAM in project and project[cfg.ETHOGRAM]):
        QMessageBox.warning(self, cfg.programName, "No behaviors configuration found in project")
        return

    if self.twBehaviors.rowCount():
        response = dialog.MessageDialog(
            cfg.programName,
            ("Some behaviors are already configured. " "Do you want to append behaviors or replace them?"),
            [cfg.APPEND, cfg.REPLACE, cfg.CANCEL],
        )
        if response == cfg.REPLACE:
            self.twBehaviors.setRowCount(0)
            self.twBehaviors_cellChanged(0, 0)
        if response == cfg.CANCEL:
            return

    behaviors_to_import = select_behaviors(
        title="Select the behaviors to import",
        text="Behaviors",
        behavioral_categories=list(project.get(cfg.BEHAVIORAL_CATEGORIES, [])),
        ethogram=dict(project[cfg.ETHOGRAM]),
        behavior_type=[cfg.STATE_EVENT, cfg.POINT_EVENT],
    )

    for i in util.sorted_keys(project[cfg.ETHOGRAM]):
        if project[cfg.ETHOGRAM][i][cfg.BEHAVIOR_CODE] not in behaviors_to_import:
            continue

        self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)

        for field in project[cfg.ETHOGRAM][i]:
            item = QTableWidgetItem()

            if field == cfg.TYPE:
                item.setText(project[cfg.ETHOGRAM][i][field])
                item.setFlags(Qt.ItemIsEnabled)
                item.setBackground(QColor(230, 230, 230))

            else:
                if field == cfg.MODIFIERS and isinstance(project[cfg.ETHOGRAM][i][field], str):
                    modif_set_dict = {}
                    if project[cfg.ETHOGRAM][i][field]:
                        modif_set_list = project[cfg.ETHOGRAM][i][field].split("|")
                        for modif_set in modif_set_list:
                            modif_set_dict[str(len(modif_set_dict))] = {
                                "name": "",
                                "type": cfg.SINGLE_SELECTION,
                                "values": modif_set.split(","),
                            }
                    project[cfg.ETHOGRAM][i][field] = dict(modif_set_dict)

                item.setText(str(project[cfg.ETHOGRAM][i][field]))

                if field not in cfg.ETHOGRAM_EDITABLE_FIELDS:
                    item.setFlags(Qt.ItemIsEnabled)
                    item.setBackground(QColor(230, 230, 230))

            self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, cfg.behavioursFields[field], item)

    self.twBehaviors.resizeColumnsToContents()


def load_dataframe_into_behaviors_tablewidget(self, df: pd.DataFrame) -> int:
    """
    Load pandas dataframe into the twBehaviors table widget

    Returns:
        int: 0 if no error else error code
    """

    expected_labels: list = [
        "Behavior code",
        "Behavior type",
        "Description",
        "Key",
        "Behavioral category",
        "Excluded behaviors",
    ]

    ethogram_header: dict = {
        "code": "Behavior code",
        "description": "Description",
        "key": "Key",
        "color": "Color",
        "category": "Behavioral category",
        "excluded": "Excluded behaviors",
        "modifiers": "modifiers (JSON)",
    }

    # change all column names to uppercase
    df.columns = df.columns.str.upper()

    for column in expected_labels:
        if column.upper() not in list(df.columns):
            QMessageBox.warning(
                None,
                cfg.programName,
                (
                    f"The {column} column was not found in the file header.<br>"
                    "For information the current file header contains the following labels:<br>"
                    f"{'<br>'.join(['<b>' + util.replace_leading_trailing_chars(x, ' ', '&#9608;') + '</b>' for x in df.columns])}<br>"
                    "<br>"
                    "The first row of the spreadsheet must contain the following labels:<br>"
                    f"{'<br>'.join(['<b>' + x + '</b>' for x in expected_labels])}<br>"
                    "<br>The order is not mandatory."
                ),
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            return 1

    for _, row in df.iterrows():
        behavior = {"coding map": ""}
        for x in ethogram_header:
            behavior[x] = row[ethogram_header[x].upper()] if str(row[ethogram_header[x].upper()]) != "nan" else ""

        self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)

        for field_type in cfg.behavioursFields:
            if field_type == cfg.TYPE:
                item = QTableWidgetItem(cfg.DEFAULT_BEHAVIOR_TYPE)
                # add type combobox
                if cfg.POINT in row["Behavior type".upper()].upper():
                    item = QTableWidgetItem(cfg.POINT_EVENT)
                elif cfg.STATE in row["Behavior type".upper()].upper():
                    item = QTableWidgetItem(cfg.STATE_EVENT)
                else:
                    QMessageBox.critical(
                        None,
                        cfg.programName,
                        f"{row['Behavior code']} has no behavior type (POINT or STATE)",
                        QMessageBox.Ok | QMessageBox.Default,
                        QMessageBox.NoButton,
                    )
                    return 2

            else:
                item = QTableWidgetItem(str(behavior[field_type]))

            if field_type not in cfg.ETHOGRAM_EDITABLE_FIELDS:
                item.setFlags(Qt.ItemIsEnabled)
                item.setBackground(QColor(230, 230, 230))

            self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, cfg.behavioursFields[field_type], item)

    return 0


def import_behaviors_from_project(self):
    fn = QFileDialog().getOpenFileName(
        self, "Import behaviors from project file", "", ("Project files (*.boris *.boris.gz);;" "All files (*)")
    )
    file_name = fn[0] if type(fn) is tuple else fn

    if not file_name:
        return
    _, _, project, _ = project_functions.open_project_json(file_name)

    import_ethogram_from_dict(self, project)


def import_behaviors_from_text_file(self):
    """
    Import behaviors from text file (CSV or TSV)
    """

    if self.twBehaviors.rowCount():
        response = dialog.MessageDialog(
            cfg.programName,
            "There are behaviors already configured. Do you want to append behaviors or replace them?",
            [cfg.APPEND, cfg.REPLACE, cfg.CANCEL],
        )
        if response == cfg.CANCEL:
            return

    fn = QFileDialog().getOpenFileName(
        self, "Import behaviors from text file (CSV, TSV)", "", "Text files (*.txt *.tsv *.csv);;All files (*)"
    )
    file_name = fn[0] if type(fn) is tuple else fn

    if not file_name:
        return

    if pl.Path(file_name).suffix.upper() == ".CSV":
        delimiter = ","
    elif pl.Path(file_name).suffix.upper() == ".TSV":
        delimiter = "\t"
    else:
        QMessageBox.warning(
            None,
            cfg.programName,
            ("The type of file was not recognized. Must be Comma Separated Values (,) or Tab Separated Values"),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    try:
        df = pd.read_csv(file_name, delimiter=delimiter)
    except Exception:
        QMessageBox.warning(
            None,
            cfg.programName,
            ("The type of file was not recognized. Must be Comma Separated Values (,) or Tab Separated Values"),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    if self.twBehaviors.rowCount() and response == cfg.REPLACE:
        self.twBehaviors.setRowCount(0)

    load_dataframe_into_behaviors_tablewidget(self, df)


def import_behaviors_from_spreadsheet(self):
    """
    Import behaviors from a spreadsheet file (XLSX)
    """

    if self.twBehaviors.rowCount():
        response = dialog.MessageDialog(
            cfg.programName,
            "There are behaviors already configured. Do you want to append behaviors or replace them?",
            [cfg.APPEND, cfg.REPLACE, cfg.CANCEL],
        )
        if response == cfg.CANCEL:
            return

    fn = QFileDialog().getOpenFileName(
        self, "Import behaviors from a spreadsheet file", "", "Spreadsheet files (*.xlsx *.ods);;All files (*)"
    )
    file_name = fn[0] if type(fn) is tuple else fn

    if not file_name:
        return

    if pl.Path(file_name).suffix.upper() == ".XLSX":
        engine = "openpyxl"
    elif pl.Path(file_name).suffix.upper() == ".ODS":
        engine = "odf"
    else:
        QMessageBox.warning(
            None,
            cfg.programName,
            ("The type of file was not recognized. Must be Microsoft-Excel XLSX format or OpenDocument ODS"),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    try:
        df = pd.read_excel(file_name, sheet_name=0, engine=engine)
    except Exception:
        QMessageBox.warning(
            None,
            cfg.programName,
            ("The type of file was not recognized. Must be Microsoft-Excel XLSX format or OpenDocument ODS"),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    if self.twBehaviors.rowCount() and response == cfg.REPLACE:
        self.twBehaviors.setRowCount(0)

    load_dataframe_into_behaviors_tablewidget(self, df)


def import_behaviors_from_clipboard(self):
    """
    import ethogram from clipboard
    """

    cb = QApplication.clipboard()
    cb_text = cb.text()
    if not cb_text:
        QMessageBox.warning(
            None,
            cfg.programName,
            "The clipboard is empty",
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    if self.twBehaviors.rowCount():
        response = dialog.MessageDialog(
            cfg.programName,
            "Some behaviors are already configured. Do you want to append behaviors or replace them?",
            [cfg.APPEND, cfg.REPLACE, cfg.CANCEL],
        )
        if response == cfg.CANCEL:
            return

        if response == cfg.REPLACE:
            self.twBehaviors.setRowCount(0)

    cb_text_splitted = cb_text.split("\n")
    while "" in cb_text_splitted:
        cb_text_splitted.remove("")

    if len(set([len(x.split("\t")) for x in cb_text_splitted])) != 1:
        QMessageBox.warning(
            None,
            cfg.programName,
            (
                "The clipboard content does not have a constant number of fields.<br>"
                "From your spreadsheet: CTRL + A (select all cells), CTRL + C (copy to clipboard)"
            ),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    for row in cb_text_splitted:
        if set(row.split("\t")) != set([""]):
            behavior = {"type": cfg.DEFAULT_BEHAVIOR_TYPE}
            for idx, field in enumerate(row.split("\t")):
                if idx == 0:
                    behavior["type"] = (
                        cfg.STATE_EVENT if cfg.STATE in field.upper() else (cfg.POINT_EVENT if cfg.POINT in field.upper() else "")
                    )
                if idx == 1:
                    behavior["key"] = field.strip() if len(field.strip()) == 1 else ""
                if idx == 2:
                    behavior["code"] = field.strip()
                if idx == 3:
                    behavior["description"] = field.strip()
                if idx == 4:
                    behavior["category"] = field.strip()

            self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)

            for field_type in cfg.behavioursFields:
                if field_type == cfg.TYPE:
                    item = QTableWidgetItem(behavior.get("type", cfg.DEFAULT_BEHAVIOR_TYPE))
                else:
                    item = QTableWidgetItem(behavior.get(field_type, ""))

                if field_type not in cfg.ETHOGRAM_EDITABLE_FIELDS:  # [TYPE, "excluded", "coding map", "modifiers", "category"]:
                    item.setFlags(Qt.ItemIsEnabled)
                    item.setBackground(QColor(230, 230, 230))

                self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, cfg.behavioursFields[field_type], item)


def import_behaviors_from_JWatcher(self):
    """
    import behaviors configuration from JWatcher (GDF file)
    """

    if self.twBehaviors.rowCount():
        response = dialog.MessageDialog(
            cfg.programName,
            "There are behaviors already configured. Do you want to append behaviors or replace them?",
            [cfg.APPEND, cfg.REPLACE, cfg.CANCEL],
        )
        if response == cfg.CANCEL:
            return

    fn = QFileDialog().getOpenFileName(self, "Import behaviors from JWatcher", "", "Global Definition File (*.gdf);;All files (*)")
    fileName = fn[0] if type(fn) is tuple else fn

    if fileName:
        if self.twBehaviors.rowCount() and response == cfg.REPLACE:
            self.twBehaviors.setRowCount(0)

        with open(fileName, "r") as f:
            rows = f.readlines()

        for idx, row in enumerate(rows):
            if row and row[0] == "#":
                continue

            if "Behavior.name." in row and "=" in row:
                key, code = row.split("=")
                key = key.replace("Behavior.name.", "")
                # read description
                if idx < len(rows) and "Behavior.description." in rows[idx + 1]:
                    description = rows[idx + 1].split("=")[-1]

                behavior = {
                    "key": key,
                    "code": code,
                    "description": description,
                    "modifiers": "",
                    "excluded": "",
                    "coding map": "",
                    "category": "",
                }

                self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)

                for field_type in cfg.behavioursFields:
                    if field_type == cfg.TYPE:
                        item = QTableWidgetItem(cfg.DEFAULT_BEHAVIOR_TYPE)
                    else:
                        item = QTableWidgetItem(behavior[field_type])

                    if field_type in [cfg.TYPE, "excluded", "category", "coding map", "modifiers"]:
                        item.setFlags(Qt.ItemIsEnabled)
                        item.setBackground(QColor(230, 230, 230))

                    self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, cfg.behavioursFields[field_type], item)


def import_behaviors_from_repository(self):
    """
    import behaviors from the BORIS ethogram repository
    """

    try:
        ethogram_list = urllib.request.urlopen(f"{cfg.ETHOGRAM_REPOSITORY_URL}/ethogram_list.json").read().strip().decode("utf-8")
    except Exception:
        QMessageBox.critical(self, cfg.programName, "An error occured during retrieving the ethogram list from BORIS repository")
        return

    try:
        ethogram_list_list = json.loads(ethogram_list)
    except Exception:
        QMessageBox.critical(self, cfg.programName, "An error occured during loading ethogram list from BORIS repository")
        return

    choice_dialog = dialog.ChooseObservationsToImport(
        "Choose the ethogram to import:", sorted([f"{x['species']} by {x['author']}" for x in ethogram_list_list])
    )
    while True:
        if not choice_dialog.exec_():
            return

        if len(choice_dialog.get_selected_observations()) == 0:
            QMessageBox.critical(self, cfg.programName, "Choose one ethogram")
            continue

        if len(choice_dialog.get_selected_observations()) > 1:
            QMessageBox.critical(self, cfg.programName, "Choose only one ethogram")
            continue

        break

    for x in ethogram_list_list:
        if f"{x['species']} by {x['author']}" == choice_dialog.get_selected_observations()[0]:
            file_name = x["file name"]
            break

    try:
        boris_project_str = urllib.request.urlopen(f"{cfg.ETHOGRAM_REPOSITORY_URL}/{file_name}").read().strip().decode("utf-8")
    except Exception:
        QMessageBox.critical(self, cfg.programName, f"An error occured during retrieving {file_name} from BORIS repository")
        return
    boris_project = json.loads(boris_project_str)

    import_ethogram_from_dict(self, boris_project)


def load_dataframe_into_subjects_tablewidget(self, df: pd.DataFrame) -> int:
    """
    Load pandas dataframe into the twSubjects table widget

    Returns:
        int: 0 if no error else error code

    """

    expected_labels: list = ["Key", "Subject name", "Description"]

    # change all column names to uppercase
    df.columns = df.columns.str.upper()

    for column in expected_labels:
        if column.upper() not in list(df.columns):
            QMessageBox.warning(
                None,
                cfg.programName,
                (
                    f"The column {column} was not found in the file header.<br>"
                    "The first row of spreadsheet must contain the following labels:<br>"
                    "Subject name, Description, Key<br>"
                    "The order is not mandatory."
                ),
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            return 1

    for _, row in df.iterrows():
        self.twSubjects.setRowCount(self.twSubjects.rowCount() + 1)

        for idx, field in enumerate(expected_labels):
            self.twSubjects.setItem(
                self.twSubjects.rowCount() - 1,
                idx,
                QTableWidgetItem(str(row[field.upper()]) if str(row[field.upper()]) != "nan" else ""),
            )

    return 0


def import_subjects_from_clipboard(self):
    """
    import subjects from clipboard
    """
    cb = QApplication.clipboard()
    cb_text = cb.text()
    if not cb_text:
        QMessageBox.warning(
            None,
            cfg.programName,
            "The clipboard is empty",
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    if self.twSubjects.rowCount():
        response = dialog.MessageDialog(
            cfg.programName,
            "Some subjects are already configured. Do you want to append subjects or replace them?",
            [cfg.APPEND, cfg.REPLACE, cfg.CANCEL],
        )
        if response == cfg.CANCEL:
            return

        if response == cfg.REPLACE:
            self.twSubjects.setRowCount(0)

    cb_text_splitted = cb_text.split("\n")

    if len(set([len(x.split("\t")) for x in cb_text_splitted])) != 1:
        QMessageBox.warning(
            None,
            cfg.programName,
            (
                "The clipboard content does not have a constant number of fields.<br>"
                "From your spreadsheet: CTRL + A (select all cells), CTRL + C (copy to clipboard)"
            ),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    for row in cb_text_splitted:
        if set(row.split("\t")) != set([""]):
            subject = {}
            for idx, field in enumerate(row.split("\t")):
                if idx == 0:
                    subject["key"] = field.strip() if len(field.strip()) == 1 else ""
                if idx == 1:
                    subject[cfg.SUBJECT_NAME] = field.strip()
                if idx == 2:
                    subject["description"] = field.strip()

            self.twSubjects.setRowCount(self.twSubjects.rowCount() + 1)

            for idx, field_name in enumerate(cfg.subjectsFields):
                item = QTableWidgetItem(subject.get(field_name, ""))
                self.twSubjects.setItem(self.twSubjects.rowCount() - 1, idx, item)


def import_subjects_from_project(self):
    """
    import subjects from a BORIS project
    """

    fn = QFileDialog().getOpenFileName(
        self, "Import subjects from project file", "", ("Project files (*.boris *.boris.gz);;" "All files (*)")
    )
    file_name = fn[0] if type(fn) is tuple else fn

    if not file_name:
        return

    _, _, project, _ = project_functions.open_project_json(file_name)

    if "error" in project:
        logging.debug(project["error"])
        QMessageBox.critical(self, cfg.programName, project["error"])
        return

    # configuration of subjects
    if not (cfg.SUBJECTS in project and project[cfg.SUBJECTS]):
        QMessageBox.warning(self, cfg.programName, "No subjects configuration found in project")
        return

    if self.twSubjects.rowCount():
        response = dialog.MessageDialog(
            cfg.programName,
            ("There are subjects already configured. " "Do you want to append subjects or replace them?"),
            [cfg.APPEND, cfg.REPLACE, cfg.CANCEL],
        )

        if response == cfg.REPLACE:
            self.twSubjects.setRowCount(0)

        if response == cfg.CANCEL:
            return

    for idx in util.sorted_keys(project[cfg.SUBJECTS]):
        self.twSubjects.setRowCount(self.twSubjects.rowCount() + 1)

        for idx2, sbjField in enumerate(cfg.subjectsFields):
            if sbjField in project[cfg.SUBJECTS][idx]:
                self.twSubjects.setItem(
                    self.twSubjects.rowCount() - 1,
                    idx2,
                    QTableWidgetItem(project[cfg.SUBJECTS][idx][sbjField]),
                )
            else:
                self.twSubjects.setItem(self.twSubjects.rowCount() - 1, idx2, QTableWidgetItem(""))

    self.twSubjects.resizeColumnsToContents()


def import_subjects_from_text_file(self):
    """
    import subjects from a text file (CSV or TSV)
    """

    if self.twSubjects.rowCount():
        response = dialog.MessageDialog(
            cfg.programName,
            ("There are subjects already configured. " "Do you want to append subjects or replace them?"),
            [cfg.APPEND, cfg.REPLACE, cfg.CANCEL],
        )

        if response == cfg.CANCEL:
            return

    fn = QFileDialog().getOpenFileName(
        self, "Import behaviors from text file (CSV, TSV)", "", "Text files (*.txt *.tsv *.csv);;All files (*)"
    )
    file_name = fn[0] if type(fn) is tuple else fn

    if not file_name:
        return

    if self.twSubjects.rowCount() and response == cfg.REPLACE:
        self.twSubjects.setRowCount(0)

    if pl.Path(file_name).suffix.upper() == ".CSV":
        delimiter = ","
    elif pl.Path(file_name).suffix.upper() == ".TSV":
        delimiter = "\t"
    else:
        QMessageBox.warning(
            None,
            cfg.programName,
            ("The type of file was not recognized. Must be Comma Separated Values (,) or Tab Separated Values"),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    try:
        df = pd.read_csv(file_name, delimiter=delimiter)
    except Exception:
        QMessageBox.warning(
            None,
            cfg.programName,
            ("The type of file was not recognized. Must be Comma Separated Values (,) or Tab Separated Values"),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    load_dataframe_into_subjects_tablewidget(self, df)


def import_subjects_from_spreadsheet(self):
    """
    import subjects from a spreadsheet file (XLSX or ODS)
    """

    if self.twSubjects.rowCount():
        response = dialog.MessageDialog(
            cfg.programName,
            ("There are subjects already configured. Do you want to append subjects or replace them?"),
            [cfg.APPEND, cfg.REPLACE, cfg.CANCEL],
        )

        if response == cfg.CANCEL:
            return

    fn = QFileDialog().getOpenFileName(
        self, "Import subjects from a spreadsheet file", "", "Spreadsheet files (*.xlsx *.ods);;All files (*)"
    )
    file_name = fn[0] if type(fn) is tuple else fn

    if not file_name:
        return

    if self.twSubjects.rowCount() and response == cfg.REPLACE:
        self.twSubjects.setRowCount(0)

    if pl.Path(file_name).suffix.upper() == ".XLSX":
        engine = "openpyxl"
    elif pl.Path(file_name).suffix.upper() == ".ODS":
        engine = "odf"
    else:
        QMessageBox.warning(
            None,
            cfg.programName,
            ("The type of file was not recognized. Must be Microsoft-Excel XLSX format or OpenDocument ODS"),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    try:
        df = pd.read_excel(file_name, sheet_name=0, engine=engine)
    except Exception:
        QMessageBox.warning(
            None,
            cfg.programName,
            ("The type of file was not recognized. Must be Microsoft-Excel XLSX format or OpenDocument ODS"),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    load_dataframe_into_subjects_tablewidget(self, df)


def import_indep_variables_from_project(self):
    """
    import independent variables from another project
    """

    fn = QFileDialog().getOpenFileName(
        self,
        "Import independent variables from project file",
        "",
        ("Project files (*.boris *.boris.gz);;" "All files (*)"),
    )

    file_name = fn[0] if type(fn) is tuple else fn

    if not file_name:
        return

    _, _, project, _ = project_functions.open_project_json(file_name)

    if "error" in project:
        logging.debug(project["error"])
        QMessageBox.critical(self, cfg.programName, project["error"])
        return

    # independent variables
    if not (cfg.INDEPENDENT_VARIABLES in project and project[cfg.INDEPENDENT_VARIABLES]):
        QMessageBox.warning(self, cfg.programName, "No independent variables found in project")
        return

    # check if variables are already present
    existing_var = []

    for r in range(self.twVariables.rowCount()):
        existing_var.append(self.twVariables.item(r, 0).text().strip().upper())

    for i in util.sorted_keys(project[cfg.INDEPENDENT_VARIABLES]):
        self.twVariables.setRowCount(self.twVariables.rowCount() + 1)
        flag_renamed = False
        for idx, field in enumerate(cfg.tw_indVarFields):
            item = QTableWidgetItem()
            if field in project[cfg.INDEPENDENT_VARIABLES][i]:
                if field == "label":
                    txt = project[cfg.INDEPENDENT_VARIABLES][i]["label"].strip()
                    while txt.upper() in existing_var:
                        txt += "_2"
                        flag_renamed = True
                else:
                    txt = project[cfg.INDEPENDENT_VARIABLES][i][field].strip()
                item.setText(txt)
            else:
                item.setText("")
            self.twVariables.setItem(self.twVariables.rowCount() - 1, idx, item)

    self.twVariables.resizeColumnsToContents()
    if flag_renamed:
        QMessageBox.information(self, cfg.programName, "Some variables already present were renamed")
