"""
BORIS plugin

Export to FERAL (getferal.ai)
"""

import pandas as pd

__version__ = "0.1.0"
__version_date__ = "2025-11-27"
__plugin_name__ = "Export observations to FERAL"
__author__ = "Olivier Friard - University of Torino - Italy"

def run(df: pd.DataFrame, pj:dict):
    """
    Export observations to FERAL
    See https://www.getferal.ai/ > Label Preparation
    """

    # class names
    class_names = {x:pj['behaviors_conf'][x]['code'] for x in pj['behaviors_conf']}
    print(f"{class_names=}")

    observations = sorted([x for x in pj['observations']])
    labels = {}
    for observation_id in observations:
        # skip if no events
        if not pj['observations'][observation_id]['events']:
            continue
        # check number of media file in player #1
        if len(pj['observations'][observation_id]['file']['1']) != 1:
            continue
        labels[observation_id] = []
        media_file_path = pj['observations'][observation_id]['file']['1'][0]
        # extract FPS
        FPS = pj['observations'][observation_id]["media_info"]['fps'][media_file_path]
        print(FPS)
        # extract media duration
        duration = pj['observations'][observation_id]["media_info"]['length'][media_file_path]
        print(duration)

        number_of_frames = int(duration / (1 /FPS))
        print(f'{number_of_frames=}')

        for idx in range(number_of_frames):
            t = idx * (1/FPS)
            print(t, df[(df["Start (s)"] <= t) & (df["Stop (s)"] >= t)]["Behavior"].unique().tolist())

    

    #unique_ids = df["Observation id"].dropna().unique().tolist()
    #print(unique_ids)

    return str(pj)
