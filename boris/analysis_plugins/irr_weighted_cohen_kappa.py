"""
BORIS plugin

Inter Rater Reliability (IRR) Weighted Cohen's Kappa
- Supports behaviors with duration (start < stop) AND instantaneous events (start == stop)
- Aggregated warning when kappa is NaN to avoid multiple popups
- event_weight configurable via QInputDialog.getDouble
"""

import math
from typing import Optional

import pandas as pd
from PySide6.QtWidgets import QInputDialog, QMessageBox

__version__ = "0.0.5"
__version_date__ = "2026-01-30"
__plugin_name__ = "Inter Rater Reliability - Weighted Cohen's Kappa NEW"
__author__ = "Olivier Friard - University of Torino - Italy"
__description__ = """
This plugin calculates Cohen's Kappa to measure inter-rater reliability between two observers
who code categorical behaviors over time intervals.

Weighted approach:
- Duration segments are weighted by their duration (seconds).
- Instantaneous behaviors (start == stop) are treated as point-events and each event contributes
  a fixed weight chosen by the user.

If Cohen's Kappa is undefined (NaN), a single aggregated warning is shown at the end.
"""


def run(df: pd.DataFrame):
    """
    Calculate the Inter Rater Reliability - Weighted Cohen's Kappa
    """

    # ------------------------------------------------------------------
    # Core weighted kappa computation
    # ------------------------------------------------------------------

    def cohen_kappa_weighted_by_time(
        obs1: list[tuple[float, float, str]],
        obs2: list[tuple[float, float, str]],
        event_weight: float,
    ) -> tuple[
        float,  # kappa
        float,  # observed agreement
        float,  # expected agreement
        dict[tuple[Optional[str], Optional[str]], float],  # contingency
        float,  # total weight
    ]:
        def split_segments_events(obs):
            segments = []
            events = []
            for start, stop, code in obs:
                if start < stop:
                    segments.append((start, stop, code))
                else:  # start == stop
                    events.append((start, code))
            return segments, events

        seg1, ev1 = split_segments_events(obs1)
        seg2, ev2 = split_segments_events(obs2)

        def get_code_segments(t, segments):
            active = [seg[2] for seg in segments if seg[0] <= t < seg[1]]
            return "+".join(sorted(active)) if active else None

        def get_code_at_time(t, segments, events):
            active = [seg[2] for seg in segments if seg[0] <= t < seg[1]]
            instant = [ev[1] for ev in events if ev[0] == t]
            codes = active + instant
            return "+".join(sorted(codes)) if codes else None

        # --- intervals from SEGMENTS ONLY
        time_points = sorted(set([t for seg in seg1 for t in seg[:2]] + [t for seg in seg2 for t in seg[:2]]))
        elementary_intervals = []
        if len(time_points) >= 2:
            elementary_intervals = [(time_points[i], time_points[i + 1]) for i in range(len(time_points) - 1)]

        # --- instantaneous events
        instant_times = sorted(set([t for t, _ in ev1] + [t for t, _ in ev2]))

        contingency = {}
        total_weight = 0.0

        # (A) duration-weighted segments
        for start, end in elementary_intervals:
            duration = end - start
            if duration <= 0:
                continue
            c1 = get_code_segments(start, seg1)
            c2 = get_code_segments(start, seg2)
            total_weight += duration
            contingency[(c1, c2)] = contingency.get((c1, c2), 0.0) + duration

        # (B) instantaneous events (fixed weight)
        for t in instant_times:
            c1 = get_code_at_time(t, seg1, ev1)
            c2 = get_code_at_time(t, seg2, ev2)
            total_weight += event_weight
            contingency[(c1, c2)] = contingency.get((c1, c2), 0.0) + event_weight

        if total_weight == 0:
            return math.nan, math.nan, math.nan, contingency, total_weight

        # observed agreement
        po = sum(w for (c1, c2), w in contingency.items() if c1 == c2) / total_weight

        # marginals
        codes1, codes2 = {}, {}
        for (c1, c2), w in contingency.items():
            codes1[c1] = codes1.get(c1, 0.0) + w
            codes2[c2] = codes2.get(c2, 0.0) + w

        # expected agreement
        pe = sum((codes1.get(c, 0.0) / total_weight) * (codes2.get(c, 0.0) / total_weight) for c in set(codes1) | set(codes2))

        if (1 - pe) == 0:
            kappa = math.nan
        else:
            kappa = (po - pe) / (1 - pe)

        return kappa, po, pe, contingency, total_weight

    # ------------------------------------------------------------------
    # Dialogs
    # ------------------------------------------------------------------

    round_decimals, ok = QInputDialog.getInt(
        None,
        "Rounding",
        "Enter the number of decimal places for rounding (can be negative)",
        value=3,
        minValue=-5,
        maxValue=3,
        step=1,
    )

    event_weight, ok_w = QInputDialog.getDouble(
        None,
        "Instantaneous event weight",
        "Weight assigned to each instantaneous event (start == stop):",
        value=1.0,
        minValue=0.0,
        maxValue=10.0,
        decimals=3,
    )

    if not ok_w:
        event_weight = 1.0

    # ------------------------------------------------------------------
    # Data preparation
    # ------------------------------------------------------------------

    df["Start (s)"] = df["Start (s)"].round(round_decimals)
    df["Stop (s)"] = df["Stop (s)"].round(round_decimals)

    unique_obs_list = df["Observation id"].unique().tolist()

    grouped = {
        obs: [
            (row[0], row[1], row[2] + "|" + row[3])
            for row in group[["Start (s)", "Stop (s)", "Subject", "Behavior"]].itertuples(index=False, name=None)
        ]
        for obs, group in df.groupby("Observation id")
    }

    # ------------------------------------------------------------------
    # Pairwise kappa
    # ------------------------------------------------------------------

    ck_results: dict = {}
    str_results: str = ""
    nan_pairs: list = []

    for idx1, obs_id1 in enumerate(unique_obs_list):
        obs1 = grouped[obs_id1]

        for obs_id2 in unique_obs_list[idx1:]:
            obs2 = grouped[obs_id2]

            kappa, po, pe, table, total_w = cohen_kappa_weighted_by_time(obs1, obs2, event_weight)

            if math.isnan(kappa):
                nan_pairs.append((obs_id1, obs_id2))
                ck_results[(obs_id1, obs_id2)] = "NaN"
                ck_results[(obs_id2, obs_id1)] = "NaN"
            else:
                ck_results[(obs_id1, obs_id2)] = f"{kappa:.3f}"
                ck_results[(obs_id2, obs_id1)] = f"{kappa:.3f}"

            str_results += f"{obs_id1} - {obs_id2}: Kappa={kappa}  Po={po}  Pe={pe}  Total weight={total_w}  Event weight={event_weight}\n"

    # ------------------------------------------------------------------
    # Aggregated warning
    # ------------------------------------------------------------------

    if nan_pairs:
        pairs_txt = "\n".join(f"- {a} vs {b}" for a, b in nan_pairs)
        QMessageBox.warning(
            None,
            "Cohen's Kappa not defined (NaN)",
            (
                "Weighted Cohen's Kappa was not defined for the following observer pairs:\n\n"
                f"{pairs_txt}\n\n"
                "Typical reasons:\n"
                "- perfect agreement without variability\n"
                "- expected agreement = 1\n"
                "- total weight = 0\n"
            ),
        )

    df_results = pd.Series(ck_results).unstack()
    return df_results, str_results
