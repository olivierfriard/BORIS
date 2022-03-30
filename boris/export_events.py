import logging
import os
import re
import pathlib as pl
from . import utilities as util
from . import config as cfg
from . import select_observations
from . import export_observation
from . import select_subj_behav
from . import project_functions
from . import dialog

from PyQt5.QtWidgets import QFileDialog, QMessageBox, QInputDialog


def export_events_as_behavioral_sequences(self, separated_subjects=False, timed=False):
    """
    export events from selected observations by subject as behavioral sequences (plain text file)
    behaviors are separated by character specified in self.behaviouralStringsSeparator (usually pipe |)
    for use with Behatrix (see http://www.boris.unito.it/pages/behatrix)

    Args:
        separated_subjects (bool):
        timed (bool):
    """

    # ask user for observations to analyze
    result, selected_observations = select_observations.select_observations(
        self.pj, cfg.MULTIPLE, "Select observations to export as behavioral sequences"
    )

    if not selected_observations:
        return

    parameters = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selected_observations,
        maxTime=0,
        flagShowIncludeModifiers=True,
        flagShowExcludeBehaviorsWoEvents=False,
    )

    if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
        return

    fn = QFileDialog().getSaveFileName(
        self, "Export events as behavioral sequences", "", "Text files (*.txt);;All files (*)"
    )
    file_name = fn[0] if type(fn) is tuple else fn

    if file_name:
        r, msg = export_observation.observation_to_behavioral_sequences(
            pj=self.pj,
            selected_observations=selected_observations,
            parameters=parameters,
            behaviors_separator=self.behaviouralStringsSeparator,
            separated_subjects=separated_subjects,
            timed=timed,
            file_name=file_name,
        )
        if not r:
            logging.critical(f"Error while exporting events as behavioral sequences: {msg}")
            QMessageBox.critical(
                None,
                cfg.programName,
                f"Error while exporting events as behavioral sequences:<br>{msg}",
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )


def export_tabular_events(self, mode: str = "tabular"):
    """
    export events from selected observations in various formats: TSV, CSV, ODS, XLSX, XLS, HTML

    Args:
        mode (str): export mode: must be ["tabular", "jwatcher"]
    """

    # ask user observations to analyze
    result, selectedObservations = self.selectObservations(cfg.MULTIPLE)
    if not selectedObservations:
        return

    out = ""
    # check if coded behaviors are defined in ethogram
    ethogram_behavior_codes = {self.pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE] for idx in self.pj[cfg.ETHOGRAM]}
    behaviors_not_defined = []
    out = ""  # will contain the output
    for obs_id in selectedObservations:
        for event in self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]:
            if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] not in ethogram_behavior_codes:
                behaviors_not_defined.append(event[cfg.EVENT_BEHAVIOR_FIELD_IDX])
    if set(sorted(behaviors_not_defined)):
        out += (
            "The following behaviors are not defined in the ethogram: "
            f"<b>{', '.join(set(sorted(behaviors_not_defined)))}</b><br><br>"
        )

    # check if state events are paired
    not_paired_obs_list = []
    for obsId in selectedObservations:
        r, msg = project_functions.check_state_events_obs(
            obsId, self.pj[cfg.ETHOGRAM], self.pj[cfg.OBSERVATIONS][obsId], self.timeFormat
        )

        if not r:
            out += f"Observation: <strong>{obsId}</strong><br>{msg}<br>"
            not_paired_obs_list.append(obsId)

    if out:
        out = f"Some observations have UNPAIRED state events<br><br>{out}"
        self.results = dialog.Results_dialog()
        self.results.setWindowTitle(f"{cfg.programName} - Check selected observations")
        self.results.ptText.setReadOnly(True)
        self.results.ptText.appendHtml(out)
        self.results.pbSave.setVisible(False)
        self.results.pbCancel.setVisible(True)

        if not self.results.exec_():
            return

    parameters = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selectedObservations,
        maxTime=0,
        flagShowIncludeModifiers=False,
        flagShowExcludeBehaviorsWoEvents=False,
    )

    if not parameters["selected subjects"] or not parameters["selected behaviors"]:
        return

    if mode == "tabular":
        if len(selectedObservations) > 1:  # choose directory for exporting observations

            items = (
                "Tab Separated Values (*.tsv)",
                "Comma separated values (*.csv)",
                "Open Document Spreadsheet (*.ods)",
                "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
                "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
                "HTML (*.html)",
            )
            item, ok = QInputDialog.getItem(self, "Export events format", "Available formats", items, 0, False)
            if not ok:
                return
            outputFormat = re.sub(".* \(\*\.", "", item)[:-1]

            exportDir = QFileDialog().getExistingDirectory(
                self,
                "Choose a directory to export events",
                os.path.expanduser("~"),
                options=QFileDialog.ShowDirsOnly,
            )
            if not exportDir:
                return

        if len(selectedObservations) == 1:
            extended_file_formats = [
                "Tab Separated Values (*.tsv)",
                "Comma Separated Values (*.csv)",
                "Open Document Spreadsheet ODS (*.ods)",
                "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
                "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
                "HTML (*.html)",
            ]
            file_formats = ["tsv", "csv", "ods", "xlsx", "xls", "html"]

            fileName, filter_ = QFileDialog().getSaveFileName(
                self, "Export events", "", ";;".join(extended_file_formats)
            )
            if not fileName:
                return

            outputFormat = file_formats[extended_file_formats.index(filter_)]
            if pl.Path(fileName).suffix != "." + outputFormat:
                fileName = str(pl.Path(fileName)) + "." + outputFormat
                # check if file with new extension already exists
                if pl.Path(fileName).is_file():
                    if (
                        dialog.MessageDialog(
                            cfg.programName, f"The file {fileName} already exists.", [cfg.CANCEL, cfg.OVERWRITE]
                        )
                        == cfg.CANCEL
                    ):
                        return

    if mode == "jwatcher":
        exportDir = QFileDialog().getExistingDirectory(
            self, "Choose a directory to export events", os.path.expanduser("~"), options=QFileDialog.ShowDirsOnly
        )
        if not exportDir:
            return

        outputFormat = "dat"

    mem_command = ""  # remember user choice when file already exists
    for obsId in selectedObservations:
        if len(selectedObservations) > 1 or mode == "jwatcher":
            """
            fileName = str(pathlib.Path(pathlib.Path(exportDir) / safeFileName(obsId)).with suffix("." + outputFormat))
            """
            fileName = f"{pl.Path(exportDir) / util.safeFileName(obsId)}.{outputFormat}"
            # check if file with new extension already exists
            if mem_command != "Overwrite all" and pl.Path(fileName).is_file():
                if mem_command == "Skip all":
                    continue
                mem_command = dialog.MessageDialog(
                    cfg.programName,
                    f"The file {fileName} already exists.",
                    [cfg.OVERWRITE, "Overwrite all", "Skip", "Skip all", cfg.CANCEL],
                )
                if mem_command == cfg.CANCEL:
                    return
                if mem_command in ["Skip", "Skip all"]:
                    continue

        if mode == "tabular":
            export_function = export_observation.export_events
        if mode == "jwatcher":
            export_function = export_observation.export_events_jwatcher

        r, msg = export_function(
            parameters, obsId, self.pj[cfg.OBSERVATIONS][obsId], self.pj[cfg.ETHOGRAM], fileName, outputFormat
        )

        if not r and msg:
            QMessageBox.critical(None, cfg.programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
