"""
BORIS plugin

Export to FERAL (getferal.ai)
"""

import pandas as pd
import json
from pathlib import Path

from PySide6.QtWidgets import QFileDialog

__version__ = "0.1.0"
__version_date__ = "2025-11-27"
__plugin_name__ = "Export observations to FERAL"
__author__ = "Olivier Friard - University of Torino - Italy"


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
    log.append(f"{observations=}")

    labels: dict = {}
    for observation_id in observations:
        # skip if no events
        if not project["observations"][observation_id]["events"]:
            print(f"No events for observation {observation_id}")
            continue

        # check number of media file in player #1
        if len(project["observations"][observation_id]["file"]["1"]) != 1:
            log.append(f"The observation {observation_id} contains more than one video")
            continue

        # check number of coded subjects
        if len(set([x[1] for x in project["observations"][observation_id]["events"]])) != 1:
            log.append(f"The observation {observation_id} contains more than one subject")
            continue

        media_file_path: str = project["observations"][observation_id]["file"]["1"][0]
        media_file_name = str(Path(media_file_path).name)
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
            # print(t, behaviors)
            if behaviors:
                behaviors_idx = reversed_class_names[behaviors[0]]
                labels[media_file_name][idx] = behaviors_idx

    out["labels"] = labels

    filename, _ = QFileDialog.getSaveFileName(
        None,
        "Choose a file to save",
        "",  # start directory
        "JSON files (*.json);;All files (*.*)",
    )
    if filename:
        with open(filename, "w") as f_out:
            f_out.write(json.dumps(out, separators=(",", ": ")))

    return "\n".join(log)
