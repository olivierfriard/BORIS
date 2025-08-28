"""
BORIS plugin

Inter Rater Reliability (IRR) Unweighted Cohen's Kappa with modifiers
"""

import pandas as pd
from sklearn.metrics import cohen_kappa_score

__version__ = "0.0.1"
__version_date__ = "2025-08-25"
__plugin_name__ = "Inter Rater Reliability - Unweighted Cohen's Kappa with modifiers"
__author__ = "Olivier Friard - University of Torino - Italy"


def run(df: pd.DataFrame):
    """
    Calculate the Inter Rater Reliability - Unweighted Cohen's Kappa with modifiers
    """

    # attribute a code for each interval
    def get_code(t_start, obs):
        for seg in obs:
            if t_start >= seg[0] and t_start < seg[1]:
                return seg[2]
        return ""

    # Get unique values as a numpy array
    unique_obs = df["Observation id"].unique()

    # Convert to a list
    unique_obs_list = unique_obs.tolist()

    # Convert to tuples grouped by observation
    grouped: dict = {}
    modifiers: list = []
    for col in df.columns:
        if isinstance(col, tuple):
            modifiers.append(col)

    for obs, group in df.groupby("Observation id"):
        o: list = []
        for row in group[["Start (s)", "Stop (s)", "Subject", "Behavior"] + modifiers].itertuples(index=False, name=None):
            modif_list = [row[i] for idx, i in enumerate(range(4, 4 + len(modifiers))) if modifiers[idx][0] == row[3]]
            o.append((row[0], row[1], row[2] + "|" + row[3] + "|" + ",".join(modif_list)))
        grouped[obs] = o

    ck_results: dict = {}
    for idx1, obs_id1 in enumerate(unique_obs_list):
        obs1 = grouped[obs_id1]

        ck_results[(obs_id1, obs_id1)] = "1.000"

        for obs_id2 in unique_obs_list[idx1 + 1 :]:
            obs2 = grouped[obs_id2]

            # get all the break points
            time_points = sorted(set([t for seg in obs1 for t in seg[:2]] + [t for seg in obs2 for t in seg[:2]]))

            # elementary intervals
            elementary_intervals = [(time_points[i], time_points[i + 1]) for i in range(len(time_points) - 1)]

            obs1_codes = [get_code(t[0], obs1) for t in elementary_intervals]

            obs2_codes = [get_code(t[0], obs2) for t in elementary_intervals]

            # Cohen's Kappa
            kappa = cohen_kappa_score(obs1_codes, obs2_codes)
            print(f"{obs_id1} -  {obs_id2}:  Cohen's Kappa : {kappa:.3f}")

            ck_results[(obs_id1, obs_id2)] = f"{kappa:.3f}"
            ck_results[(obs_id2, obs_id1)] = f"{kappa:.3f}"

    # DataFrame conversion
    df_results = pd.Series(ck_results).unstack()

    return df_results
