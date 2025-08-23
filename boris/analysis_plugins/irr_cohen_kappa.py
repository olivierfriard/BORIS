"""
BORIS plugin

Inter Rater Reliability (IRR) Cohen Kappa not weighted
"""

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from PySide6.QtWidgets import QInputDialog

__version__ = "0.0.1"
__version_date__ = "2025-08-22"
__plugin_name__ = "Inter Rater Reliability - Cohen Kappa"
__author__ = "Olivier Friard - University of Torino - Italy"


def run(df: pd.DataFrame):
    """
    Calculate the Inter Rater Reliability - Cohen Kappa
    """

    '''integer, ok = QInputDialog.getInt(
                None, "test", "value", value=1, minValue=100, maxValue=1000, step=10
            )
    '''

    # Get unique values as a numpy array
    unique_obs = df["Observation id"].unique()
    print(f"{unique_obs=}")

    # Convert to a list
    unique_obs_list = unique_obs.tolist()
    print(f"{unique_obs_list=}")
    
    '''
    if len(unique_obs_list) != 2:
        return f"You must select 2 observations ({len(unique_obs_list)} {'was' if len(unique_obs_list) < 2 else 'were'} selected)"
    '''

    print()
    # Convert to tuples grouped by observation
    grouped = {
    obs: [(row[0], row[1], row[2] + '|' + row[3]) for row in group[["Start (s)", "Stop (s)", "Subject", "Behavior"]].itertuples(index=False, name=None)]
    for obs, group in df.groupby("Observation id")
    }
    print(f"{grouped=}")


    # attribute a code for each interval
    def get_code(t_start, obs):
        for seg in obs:
            if t_start >= seg[0] and t_start < seg[1]:
                return seg[2]
        return ''


    ck_results: dict =  {}
    for idx1, obs_id1 in enumerate(unique_obs_list):
        obs1 = grouped[obs_id1]

        for obs_id2 in unique_obs_list[idx1 +1:]:

            obs2 = grouped[obs_id2]

            # get all the break points
            time_points = sorted(set([t for seg in obs1 for t in seg[:2]] + [t for seg in obs2 for t in seg[:2]]))

            # elementary intervals
            elementary_intervals = [(time_points[i], time_points[i+1]) for i in range(len(time_points)-1)]

            print(f"{elementary_intervals=}")


            obs1_codes = [get_code(t[0], obs1) for t in elementary_intervals]

            print(f"{obs1_codes=}")

            obs2_codes = [get_code(t[0], obs2) for t in elementary_intervals]

            print(f"{obs2_codes=}")

            # Cohen's Kappa
            kappa = cohen_kappa_score(obs1_codes, obs2_codes)
            print(f"Cohen's Kappa : {kappa:.3f}")

            ck_results[(obs_id1, obs_id2)] = kappa

    print()
    print(ck_results)

    return str(ck_results)

    return f"Observations:\n\n{unique_obs_list[0]}\n{unique_obs_list[1]}\n\nCohen's Kappa : {kappa:.3f}"

