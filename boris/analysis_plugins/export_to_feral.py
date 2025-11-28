"""
BORIS plugin

Export to FERAL (getferal.ai)
"""

import pandas as pd
import json

__version__ = "0.1.0"
__version_date__ = "2025-11-27"
__plugin_name__ = "Export observations to FERAL"
__author__ = "Olivier Friard - University of Torino - Italy"


def run(df: pd.DataFrame, pj: dict):
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

    # class names
    class_names = {x: pj["behaviors_conf"][x]["code"] for x in pj["behaviors_conf"]}
    out["class_names"] = class_names
    reversed_class_names = {pj["behaviors_conf"][x]["code"]: int(x) for x in pj["behaviors_conf"]}
    print(f"{class_names=}")
    print(f"{reversed_class_names=}")

    observations: list = sorted([x for x in pj["observations"]])
    labels: dict = {}
    for observation_id in observations:
        # skip if no events
        if not pj["observations"][observation_id]["events"]:
            print(f"No events for observation {observation_id}")
            continue
        # check number of media file in player #1
        if len(pj["observations"][observation_id]["file"]["1"]) != 1:
            print(f"The observation {observation_id} contains more than one video")
            continue
        # check number of coded subjects
        print(set([x[1] for x in pj["observations"][observation_id]["events"]]))
        if len(set([x[1] for x in pj["observations"][observation_id]["events"]])) != 1:
            print(f"The observation {observation_id} contains more than one subject")
            continue

        media_file_path: str = pj["observations"][observation_id]["file"]["1"][0]
        # extract FPS
        FPS = pj["observations"][observation_id]["media_info"]["fps"][media_file_path]
        print(FPS)
        # extract media duration
        duration = pj["observations"][observation_id]["media_info"]["length"][media_file_path]
        print(duration)

        number_of_frames = int(duration / (1 / FPS))
        print(f"{number_of_frames=}")
        labels[observation_id] = [0] * number_of_frames

        for idx in range(number_of_frames):
            t = idx * (1 / FPS)
            behaviors = df[(df["Start (s)"] <= t) & (df["Stop (s)"] >= t)]["Behavior"].unique().tolist()
            if len(behaviors) > 1:
                print(f"The observation {observation_id} contains more than one behavior for frame {idx}")
                del labels[observation_id]
                break
            print(t, behaviors)
            if behaviors:
                behaviors_idx = reversed_class_names[behaviors[0]]
                print(behaviors_idx)
                labels[observation_id][idx] = behaviors_idx

    out["labels"] = labels
    return json.dumps(out, separators=(",", ": "))  # , indent=2, separators=(",", ": "))
