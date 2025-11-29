"""
BORIS plugin

Export to FERAL (getferal.ai)
"""

import pandas as pd
import json
from pathlib import Path

from PySide6.QtWidgets import QFileDialog

# dependencies for CategoryDialog
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QDialog
from PySide6.QtCore import Qt


__version__ = "0.1.1"
__version_date__ = "2025-11-28"
__plugin_name__ = "Export observations to FERAL"
__author__ = "Olivier Friard - University of Torino - Italy"


class CategoryDialog(QDialog):
    def __init__(self, items, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Organize the videos in categories")

        self.setModal(True)

        # Main layout
        main_layout = QVBoxLayout(self)
        lists_layout = QHBoxLayout()

        # All videos
        self.list_unclassified = self._create_list_widget()
        self.label_unclassified = QLabel("All videos")
        col0_layout = QVBoxLayout()
        col0_layout.addWidget(self.label_unclassified)
        col0_layout.addWidget(self.list_unclassified)

        self.list_cat1 = self._create_list_widget()
        self.label_cat1 = QLabel("train")
        col1_layout = QVBoxLayout()
        col1_layout.addWidget(self.label_cat1)
        col1_layout.addWidget(self.list_cat1)

        self.list_cat2 = self._create_list_widget()
        self.label_cat2 = QLabel("val")
        col2_layout = QVBoxLayout()
        col2_layout.addWidget(self.label_cat2)
        col2_layout.addWidget(self.list_cat2)

        self.list_cat3 = self._create_list_widget()
        self.label_cat3 = QLabel("test")
        col3_layout = QVBoxLayout()
        col3_layout.addWidget(self.label_cat3)
        col3_layout.addWidget(self.list_cat3)

        self.list_cat4 = self._create_list_widget()
        self.label_cat4 = QLabel("inference")
        col4_layout = QVBoxLayout()
        col4_layout.addWidget(self.label_cat4)
        col4_layout.addWidget(self.list_cat4)

        # Add all columns to the horizontal layout
        lists_layout.addLayout(col0_layout)
        lists_layout.addLayout(col1_layout)
        lists_layout.addLayout(col2_layout)
        lists_layout.addLayout(col3_layout)
        lists_layout.addLayout(col4_layout)

        main_layout.addLayout(lists_layout)

        buttons_layout = QHBoxLayout()
        self.btn_ok = QPushButton("OK")
        self.btn_cancel = QPushButton("Cancel")

        self.btn_ok.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.btn_ok)
        buttons_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(buttons_layout)

        # Populate "Unclassified" with input items
        for text in items:
            QListWidgetItem(text, self.list_unclassified)

    def _create_list_widget(self):
        """
        Create a QListWidget ready for drag & drop.
        """
        lw = QListWidget()
        lw.setSelectionMode(QListWidget.ExtendedSelection)
        lw.setDragEnabled(True)
        lw.setAcceptDrops(True)
        lw.setDropIndicatorShown(True)
        lw.setDragDropMode(QListWidget.DragDrop)
        lw.setDefaultDropAction(Qt.MoveAction)
        return lw

    def get_categories(self):
        """
        Return the content of all categories as a dictionary of lists.
        """

        def collect(widget):
            return [widget.item(i).text().rstrip("*") for i in range(widget.count())]

        return {
            "unclassified": collect(self.list_unclassified),
            "train": collect(self.list_cat1),
            "val": collect(self.list_cat2),
            "test": collect(self.list_cat3),
            "inference": collect(self.list_cat4),
        }


def run(df: pd.DataFrame, project: dict):
    """
    Export observations to FERAL
    See https://www.getferal.ai/ > Label Preparation
    """

    out: dict = {
        "is_multilabel": False,
        "splits": {
            "train": [],
            "val": [],
            "test": [],
            "inference": [],
        },
    }

    log: list = []

    # class names
    class_names = {x: project["behaviors_conf"][x]["code"] for x in project["behaviors_conf"]}
    out["class_names"] = class_names
    reversed_class_names = {project["behaviors_conf"][x]["code"]: int(x) for x in project["behaviors_conf"]}
    log.append(f"{class_names=}")

    observations: list = sorted([x for x in project["observations"]])
    log.append(f"Selected observation: {observations}")

    labels: dict = {}
    video_list: list = []
    for observation_id in observations:
        log.append("---")
        log.append(observation_id)

        # check number of media file in player #1
        if len(project["observations"][observation_id]["file"]["1"]) != 1:
            log.append(f"The observation {observation_id} contains more than one video")
            continue

        # check number of coded subjects
        if len(set([x[1] for x in project["observations"][observation_id]["events"]])) > 1:
            log.append(f"The observation {observation_id} contains more than one subject")
            continue

        media_file_path: str = project["observations"][observation_id]["file"]["1"][0]
        media_file_name = str(Path(media_file_path).name)

        # skip if no events
        if not project["observations"][observation_id]["events"]:
            video_list.append(media_file_name)
            log.append(f"No events for observation {observation_id}")
            continue
        else:
            video_list.append(media_file_name + "*")

        # extract FPS
        FPS = project["observations"][observation_id]["media_info"]["fps"][media_file_path]
        log.append(f"{media_file_name} {FPS=}")
        # extract media duration
        duration = project["observations"][observation_id]["media_info"]["length"][media_file_path]
        log.append(f"{media_file_name} {duration=}")

        number_of_frames = int(duration / (1 / FPS))
        log.append(f"{number_of_frames=}")

        labels[media_file_name] = [0] * number_of_frames

        for idx in range(number_of_frames):
            t = idx * (1 / FPS)
            behaviors = (
                df[(df["Observation id"] == observation_id) & (df["Start (s)"] <= t) & (df["Stop (s)"] >= t)]["Behavior"].unique().tolist()
            )
            if len(behaviors) > 1:
                log.append(f"The observation {observation_id} contains more than one behavior for frame {idx}")
                del labels[media_file_name]
                break
            if behaviors:
                behaviors_idx = reversed_class_names[behaviors[0]]
                labels[media_file_name][idx] = behaviors_idx

    out["labels"] = labels

    # splits
    dlg = CategoryDialog(video_list)

    if dlg.exec():  # Dialog accepted
        result = dlg.get_categories()
        del result["unclassified"]
        out["splits"] = result

        filename, _ = QFileDialog.getSaveFileName(
            None,
            "Choose a file to save",
            "",  # start directory
            "JSON files (*.json);;All files (*.*)",
        )
        if filename:
            with open(filename, "w") as f_out:
                f_out.write(json.dumps(out, separators=(",", ": "), indent=1))

    else:
        log.append("splits section missing")

    return "\n".join(log)
