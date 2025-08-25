"""
BORIS plugin

Inter Rater Reliability (IRR) Weighted Cohen Kappa
"""

import pandas as pd
from typing import List, Tuple, Dict, Optional

__version__ = "0.0.1"
__version_date__ = "2025-08-25"
__plugin_name__ = "Inter Rater Reliability - Weighted Cohen Kappa"
__author__ = "Olivier Friard - University of Torino - Italy"


def run(df: pd.DataFrame):
    """
    Calculate the Inter Rater Reliability - Weighted Cohen Kappa
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

        # 3. Helper: get the active code for an observer at a given time
        def get_code(t: float, obs: List[Tuple[float, float, str]]) -> Optional[str]:
            for seg in obs:
                if seg[0] <= t < seg[1]:
                    return seg[2]
            return None  # in case no segment covers this time

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
