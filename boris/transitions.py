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
import os
import subprocess
import tempfile

from PyQt5.QtWidgets import QFileDialog, QMessageBox

from . import config as cfg
from . import dialog, export_observation, select_subj_behav
from . import select_observations


def behavioral_strings_analysis(strings, behav_seq_separator):
    """
    Analyze behavioral strings
    """

    rows = strings[:]
    sequences = []
    for row in rows:
        if behav_seq_separator:
            r = row.strip().split(behav_seq_separator)
        else:
            r = list(row.strip())

        sequences.append(r)

    # extract unique behaviors
    unique_behaviors = []
    for seq in sequences:
        for c in seq:
            if c not in unique_behaviors:
                unique_behaviors.append(c)

    unique_behaviors.sort()

    return sequences, unique_behaviors


def observed_transitions_matrix(sequences, behaviours, mode="frequency") -> str:
    """
    create the normalized matrix of observed transitions
    mode:
    * frequency:
    * number
    * frequencies_after_behaviors
    """

    logging.debug("function: observed_transitions_matrix")
    logging.debug(f"behaviours: {behaviours}")

    if "" in behaviours:
        behaviours.remove("")

    transitions = {}
    for behaviour in behaviours:
        if not behaviour:
            continue
        transitions[behaviour] = {}
        for behaviour2 in behaviours:
            transitions[behaviour][behaviour2] = 0

    for seq in sequences:
        for i in range(len(seq) - 1):
            if not seq[i]:
                continue
            if seq[i] in behaviours and seq[i + 1] in behaviours:
                transitions[seq[i]][seq[i + 1]] += 1

    transitions_total_number = sum([sum(transitions[x].values()) for x in transitions])

    if not transitions_total_number:
        return False

    out = "\t" + "\t".join(list(behaviours)) + "\n"
    for behaviour in behaviours:
        out += "{}\t".format(behaviour)
        for behaviour2 in behaviours:
            if mode == "frequency":
                out += "{}\t".format(transitions[behaviour][behaviour2] / transitions_total_number)
            elif mode == "number":
                out += "{}\t".format(transitions[behaviour][behaviour2])
            elif mode == "frequencies_after_behaviors":
                if sum(transitions[behaviour].values()):
                    out += "{}\t".format(transitions[behaviour][behaviour2] / sum(transitions[behaviour].values()))
                else:
                    out += "{}\t".format(transitions[behaviour][behaviour2])
        out = out[:-1] + "\n"

    return out


def create_transitions_gv_from_matrix(matrix, cutoff_all=0, cutoff_behavior=0, edge_label="percent_node") -> tuple:
    """
    create code for GraphViz
    matrix: matrix of frequency
    edge_label: (percent_node, fraction_node)
    return string containing graphviz code
    """

    behaviours = matrix.split("\n")[0].strip().split("\t")
    transitions = {}

    for row in matrix.split("\n")[1:]:
        if not row:
            continue

        transitions[row.split("\t")[0]] = {}
        for idx, r in enumerate(row.split("\t")[1:]):
            if "." in r:
                transitions[row.split("\t")[0]][behaviours[idx]] = float(r)
            else:
                transitions[row.split("\t")[0]][behaviours[idx]] = int(r)

    """transitions_total_number = sum([sum(transitions[x].values()) for x in transitions])"""

    out = "digraph G { \n"

    for behaviour1 in behaviours:
        for behaviour2 in behaviours:
            if behaviour1 not in transitions or behaviour2 not in transitions:
                return True, "Error: the file does not seem a transition matrix"
            if transitions[behaviour1][behaviour2]:
                if edge_label == "percent_node":
                    if transitions[behaviour1][behaviour2] > cutoff_all:
                        out += '"{behaviour1}" -> "{behaviour2}" [label="{label:0.3f}"];\n'.format(
                            behaviour1=behaviour1, behaviour2=behaviour2, label=transitions[behaviour1][behaviour2]
                        )

                if edge_label == "fraction_node":
                    transition_sum = sum(transitions[behaviour1].values())
                    if transitions[behaviour1][behaviour2] / transition_sum > cutoff_behavior:
                        out += """"{behaviour1}" -> "{behaviour2}" [label="{label}%"];\n""".format(
                            behaviour1=behaviour1,
                            behaviour2=behaviour2,
                            label=round(transitions[behaviour1][behaviour2] / transition_sum * 100, 1),
                        )

    out += "\n}"
    return False, out


def transitions_matrix(self, mode):
    """
    create transitions frequencies matrix with selected observations, subjects and behaviors
    mode:
    * frequency
    * number
    * frequencies_after_behaviors
    """
    # ask user observations to analyze
    _, selected_observations = select_observations.select_observations2(
        self, cfg.MULTIPLE, windows_title="Select observations for transitions matrix"
    )

    if not selected_observations:
        return

    parameters = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selected_observations,
        flagShowIncludeModifiers=True,
        flagShowExcludeBehaviorsWoEvents=False,
        n_observations=len(selected_observations),
    )

    if parameters == {}:
        return

    if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
        return

    flagMulti = False
    if len(parameters[cfg.SELECTED_SUBJECTS]) == 1:
        fn = QFileDialog().getSaveFileName(
            None,
            "Create matrix of transitions " + mode,
            "",
            "Transitions matrix files (*.txt *.tsv);;All files (*)",
        )
        fileName = fn[0] if type(fn) is tuple else fn  # PyQt4/5

    else:
        exportDir = QFileDialog(self).getExistingDirectory(
            self,
            "Choose a directory to save the transitions matrices",
            os.path.expanduser("~"),
            options=QFileDialog(self).ShowDirsOnly,
        )
        if not exportDir:
            return
        flagMulti = True

    flag_overwrite_all = False
    for subject in parameters[cfg.SELECTED_SUBJECTS]:
        logging.debug(f"subjects: {subject}")

        strings_list = []
        for obs_id in selected_observations:
            strings_list.append(
                export_observation.events_to_behavioral_sequences(self.pj, obs_id, subject, parameters, self.behav_seq_separator)
            )

        sequences, observed_behaviors = behavioral_strings_analysis(strings_list, self.behav_seq_separator)

        observed_matrix = observed_transitions_matrix(
            sequences, sorted(list(set(observed_behaviors + parameters[cfg.SELECTED_BEHAVIORS]))), mode=mode
        )

        if not observed_matrix:
            QMessageBox.warning(self, cfg.programName, f"No transitions found for <b>{subject}</b>")
            continue

        logging.debug(f"observed_matrix {mode}:\n{observed_matrix}")

        if flagMulti:
            try:
                nf = f"{exportDir}{os.sep}{subject}_transitions_{mode}_matrix.tsv"

                if os.path.isfile(nf) and not flag_overwrite_all:
                    answer = dialog.MessageDialog(
                        cfg.programName,
                        f"A file with same name already exists.<br><b>{nf}</b>",
                        ["Overwrite", "Overwrite all", cfg.CANCEL],
                    )
                    if answer == cfg.CANCEL:
                        continue
                    if answer == "Overwrite all":
                        flag_overwrite_all = True

                with open(nf, "w") as outfile:
                    outfile.write(observed_matrix)
            except Exception:
                QMessageBox.critical(self, cfg.programName, f"The file {nf} can not be saved")
        else:
            try:
                with open(fileName, "w") as outfile:
                    outfile.write(observed_matrix)

            except Exception:
                QMessageBox.critical(self, cfg.programName, f"The file {fileName} can not be saved")


def transitions_dot_script():
    """
    create dot script (graphviz language) from transitions frequencies matrix
    """

    fn = QFileDialog().getOpenFileNames(
        None,
        "Select one or more transitions matrix files",
        "",
        "Transitions matrix files (*.txt *.tsv);;All files (*)",
    )
    fileNames = fn[0] if type(fn) is tuple else fn

    out = ""

    for fileName in fileNames:
        with open(fileName, "r") as infile:
            result, gv = create_transitions_gv_from_matrix(infile.read(), cutoff_all=0, cutoff_behavior=0, edge_label="percent_node")
            if result:
                QMessageBox.critical(
                    None,
                    cfg.programName,
                    gv,
                )
                return

            with open(fileName + ".gv", "w") as f:
                f.write(gv)

            out += f"<b>{fileName}.gv</b> created<br>"

    if out:
        QMessageBox.information(
            None,
            cfg.programName,
            (f"{out}<br><br>The DOT scripts can be used with Graphviz or WebGraphviz " "to generate diagram"),
        )


def transitions_flow_diagram():
    """
    create flow diagram with graphviz (if installed) from transitions matrix
    """

    # check if dot present in path
    result = subprocess.getoutput("dot -V")
    if "graphviz" not in result:
        QMessageBox.critical(
            None,
            cfg.programName,
            (
                "The GraphViz package is not installed.<br>"
                "The <b>dot</b> program was not found in the path.<br><br>"
                'Go to <a href="http://www.graphviz.org">'
                "http://www.graphviz.org</a> for information"
            ),
        )
        return

    fn = QFileDialog().getOpenFileNames(
        None,
        "Select one or more transitions matrix files",
        "",
        "Transitions matrix files (*.txt *.tsv);;All files (*)",
    )
    fileNames = fn[0] if type(fn) is tuple else fn

    out = ""
    for fileName in fileNames:
        with open(fileName, "r") as infile:
            result, gv = create_transitions_gv_from_matrix(infile.read(), cutoff_all=0, cutoff_behavior=0, edge_label="percent_node")
            if result:
                QMessageBox.critical(
                    None,
                    cfg.programName,
                    gv,
                )
                return

            with open(tempfile.gettempdir() + os.sep + os.path.basename(fileName) + ".tmp.gv", "w") as f:
                f.write(gv)
            result = subprocess.getoutput(
                (f'dot -Tpng -o "{fileName}.png" ' f'"{tempfile.gettempdir() + os.sep + os.path.basename(fileName)}.tmp.gv"')
            )
            if not result:
                out += f"<b>{fileName}.png</b> created<br>"
            else:
                out += f"Problem with <b>{fileName}</b><br>"

    if out:
        QMessageBox.information(None, cfg.programName, out)
