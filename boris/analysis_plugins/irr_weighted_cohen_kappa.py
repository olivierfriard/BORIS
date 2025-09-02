"""
BORIS plugin

Inter Rater Reliability (IRR) Weighted Cohen's Kappa
"""

import pandas as pd
from typing import List, Tuple, Dict, Optional

from PySide6.QtWidgets import QInputDialog

__version__ = "0.0.3"
__version_date__ = "2025-09-02"
__plugin_name__ = "Inter Rater Reliability - Weighted Cohen's Kappa"
__author__ = "Olivier Friard - University of Torino - Italy"
__description__ = """
This plugin calculates Cohen's Kappa to measure inter-rater reliability between two observers who code categorical behaviors over time intervals.
Unlike the unweighted version, this approach takes into account the duration of each coded interval, giving more weight to longer intervals in the agreement calculation.
This plugin does not take into account the modifiers.

How it works:

Time segmentation
The program collects all the time boundaries from both observers and merges them into a unified set of time points.
These define a set of non-overlapping elementary intervals covering the entire observed period.

Assigning codes
For each elementary interval, the program identifies the behavior category assigned by each observer.

Weighted contingency table
Instead of treating each interval equally, the program assigns a weight equal to the duration of the interval.
These durations are accumulated in a contingency table that records how much time was spent in each combination of categories across the two observers.

Agreement calculation

Observed agreement (po): The proportion of total time where both observers assigned the same category.

Expected agreement (pe): The proportion of agreement expected by chance, based on the time-weighted marginal distributions of each observer's coding.

Cohen's Kappa (κ): Computed from the weighted observed and expected agreements.
"""


def run(df: pd.DataFrame):
    """
    Calculate the Inter Rater Reliability - Weighted Cohen's Kappa
    """

    def cohen_kappa_weighted_by_time(
        obs1: List[Tuple[float, float, str]], obs2: List[Tuple[float, float, str]]
    ) -> Tuple[float, float, float, Dict[Tuple[Optional[str], Optional[str]], float]]:
        """
        Compute Cohen's Kappa weighted by time duration.

        Args:
            obs1: List of (start_time, end_time, code) for observer 1
            obs2: List of (start_time, end_time, code) for observer 2

        Returns:
            kappa (float): Cohen's Kappa weighted by duration
            po (float): Observed agreement proportion (weighted)
            pe (float): Expected agreement proportion by chance (weighted)
            contingency (dict): Contingency table {(code1, code2): total_duration}
        """

        # 1. Collect all time boundaries from both observers
        time_points = sorted(set([t for seg in obs1 for t in seg[:2]] + [t for seg in obs2 for t in seg[:2]]))

        # 2. Build elementary intervals (non-overlapping time bins)
        elementary_intervals = [(time_points[i], time_points[i + 1]) for i in range(len(time_points) - 1)]

        # 3. # Attribute all active codes for each interval
        def get_code(t: float, obs: List[Tuple[float, float, str]]) -> Optional[str]:
            active_codes = [seg[2] for seg in obs if seg[0] <= t < seg[1]]
            if not active_codes:
                return None
            return "+".join(sorted(active_codes))

        # 4. Build weighted contingency table (durations instead of counts)
        contingency: Dict[Tuple[Optional[str], Optional[str]], float] = {}
        total_time = 0.0

        for start, end in elementary_intervals:
            c1 = get_code(start, obs1)
            c2 = get_code(start, obs2)
            duration = end - start
            total_time += duration
            contingency[(c1, c2)] = contingency.get((c1, c2), 0.0) + duration

        # 5. Observed agreement (po)
        po = sum(duration for (c1, c2), duration in contingency.items() if c1 == c2) / total_time

        # Marginal distributions for each observer
        codes1: Dict[Optional[str], float] = {}
        codes2: Dict[Optional[str], float] = {}
        for (c1, c2), duration in contingency.items():
            codes1[c1] = codes1.get(c1, 0.0) + duration
            codes2[c2] = codes2.get(c2, 0.0) + duration

        # 6. Expected agreement (pe), using marginal proportions
        all_codes = set(codes1) | set(codes2)
        pe = sum((codes1.get(c, 0.0) / total_time) * (codes2.get(c, 0.0) / total_time) for c in all_codes)

        # 7. Kappa calculation
        kappa = (po - pe) / (1 - pe) if (1 - pe) != 0 else 0.0

        return kappa, po, pe, contingency

    # ask user for the number of decimal places for rounding (can be negative)
    round_decimals, ok = QInputDialog.getInt(
        None, "Rounding", "Enter the number of decimal places for rounding (can be negative)", value=3, minValue=-5, maxValue=3, step=1
    )

    # round times
    df["Start (s)"] = df["Start (s)"].round(round_decimals)
    df["Stop (s)"] = df["Stop (s)"].round(round_decimals)

    # Get unique values as a numpy array
    unique_obs = df["Observation id"].unique()

    # Convert to a list
    unique_obs_list = unique_obs.tolist()

    # Convert to tuples grouped by observation
    grouped = {
        obs: [
            (row[0], row[1], row[2] + "|" + row[3])  # concatenate subject and behavior with |
            for row in group[["Start (s)", "Stop (s)", "Subject", "Behavior"]].itertuples(index=False, name=None)
        ]
        for obs, group in df.groupby("Observation id")
    }

    ck_results: dict = {}
    str_results: str = ""
    for idx1, obs_id1 in enumerate(unique_obs_list):
        obs1 = grouped[obs_id1]

        ck_results[(obs_id1, obs_id1)] = "1.000"

        for obs_id2 in unique_obs_list[idx1 + 1 :]:
            obs2 = grouped[obs_id2]

            # Cohen's Kappa
            kappa, po, pe, table = cohen_kappa_weighted_by_time(obs1, obs2)

            print(f"{obs_id1} -  {obs_id2}:  Cohen's Kappa: {kappa:.3f}   Expected agreement: {pe:.3f}  Observed agreement: {po:.3f}")
            str_results += (
                f"{obs_id1} -  {obs_id2}:  Cohen's Kappa: {kappa:.3f}   Expected agreement: {pe:.3f}  Observed agreement: {po:.3f}\n"
            )

            ck_results[(obs_id1, obs_id2)] = f"{kappa:.3f}"
            ck_results[(obs_id2, obs_id1)] = f"{kappa:.3f}"

    # DataFrame conversion
    df_results = pd.Series(ck_results).unstack()

    return df_results, str_results
