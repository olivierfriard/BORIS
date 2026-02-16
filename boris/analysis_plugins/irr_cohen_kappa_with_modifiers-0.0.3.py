"""
BORIS plugin

Inter Rater Reliability (IRR) Unweighted Cohen's Kappa with modifiers
"""

import pandas as pd
from PySide6.QtWidgets import QInputDialog
from sklearn.metrics import cohen_kappa_score

__version__ = "0.0.3"
__version_date__ = "2025-09-02"
__plugin_name__ = "Inter Rater Reliability - Unweighted Cohen's Kappa with modifiers"
__author__ = "Olivier Friard - University of Torino - Italy"
__description__ = """
This plugin calculates Cohen's Kappa to measure inter-rater reliability between two observers who code categorical behaviors over time intervals.
Unlike the weighted version, this approach does not take into account the duration of the intervals.
Each segment of time is treated equally, regardless of how long it lasts.
This plugin takes into account the modifiers.


How it works:

Time segmentation
The program identifies all the time boundaries (start and end points) used by both observers.
These boundaries are merged into a common timeline, which is then divided into a set of non-overlapping elementary intervals.

Assigning codes
For each elementary interval, the program determines which behavior was coded by each observer.

Comparison of codes
The program builds two parallel lists of behavior codes, one for each observer.
Each elementary interval is counted as one unit of observation, no matter how long the interval actually lasts.

Cohen's Kappa calculation
Using these two lists, the program computes Cohen's Kappa using the cohen_kappa_score function of the sklearn package.
(see https://scikit-learn.org/stable/modules/generated/sklearn.metrics.cohen_kappa_score.html for details)
This coefficient measures how much the observers agree on their coding, adjusted for the amount of agreement that would be expected by chance.

"""


def run(df: pd.DataFrame):
    """
    Calculate the Inter Rater Reliability - Unweighted Cohen's Kappa with modifiers
    """

    # Attribute all active codes for each interval
    def get_code(t_start, obs):
        active_codes = [seg[2] for seg in obs if seg[0] <= t_start < seg[1]]
        if not active_codes:
            return ""
        # Sort to ensure deterministic representation (e.g., "A+B" instead of "B+A")
        return "+".join(sorted(active_codes))

    # ask user for the number of decimal places for rounding (can be negative)
    round_decimals, ok = QInputDialog.getInt(
        None, "Rounding", "Enter the number of decimal places for rounding (can be negative)", value=3, minValue=-5, maxValue=3, step=1
    )

    # round times
    df["Start (s)"] = df["Start (s)"].round(round_decimals)
    df["Stop (s)"] = df["Stop (s)"].round(round_decimals)

    # Get unique values
    unique_obs_list = df["Observation id"].unique().tolist()

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
