"""
BORIS plugin

Inter Rater Reliability (IRR) Weighted Cohen's Kappa with modifiers
- Supports behaviors with duration (start < stop) AND instantaneous events (start == stop)
- Modifiers are included in the category label (subject|behavior|mod1,mod2,...)
- Aggregated warning when kappa is NaN to avoid multiple popups
- event_weight configurable via QInputDialog.getDouble
"""

import math
from typing import Optional

import pandas as pd
from PySide6.QtWidgets import QInputDialog, QMessageBox

__version__ = "0.0.5"
__version_date__ = "2026-01-30"
__plugin_name__ = "Inter Rater Reliability - Weighted Cohen's Kappa with modifiers NEW"
__author__ = "Olivier Friard - University of Torino - Italy"
__description__ = """
This plugin calculates a time-weighted Cohen's Kappa to measure inter-rater reliability
between two observers who code categorical behaviors over time.

Weighted approach:
- Duration segments are weighted by their duration (seconds).
- Instantaneous behaviors (start == stop) are treated as point-events and each event contributes
  a fixed weight chosen by the user (so events are not lost).

Modifiers are included in the label used for comparison:
subject|behavior|mod1,mod2,...

If Cohen's Kappa is undefined (NaN), a single aggregated warning is shown at the end.
"""


def run(df: pd.DataFrame):
    """
    Calculate the Inter Rater Reliability - Weighted Cohen's Kappa with modifiers
    """

    # ------------------------------------------------------------------
    # Core weighted kappa computation (segments duration + events fixed weight)
    # ------------------------------------------------------------------

    def cohen_kappa_weighted_by_time(
        obs1: list[tuple[float, float, str]],
        obs2: list[tuple[float, float, str]],
        event_weight: float,
    ) -> tuple[
        float,  # kappa
        float,  # observed agreement (Po)
        float,  # expected agreement (Pe)
        dict[tuple[Optional[str], Optional[str]], float],  # contingency table
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

        def get_code_segments(t: float, segments: list[tuple[float, float, str]]) -> Optional[str]:
            active = [seg[2] for seg in segments if seg[0] <= t < seg[1]]
            return "+".join(sorted(active)) if active else None

        def get_code_at_time(
            t: float,
            segments: list[tuple[float, float, str]],
            events: list[tuple[float, str]],
        ) -> Optional[str]:
            active = [seg[2] for seg in segments if seg[0] <= t < seg[1]]
            instant = [ev[1] for ev in events if ev[0] == t]
            codes = active + instant
            return "+".join(sorted(codes)) if codes else None

        # 1) elementary intervals from SEGMENT boundaries ONLY (coherent with unweighted+modifiers)
        time_points = sorted(set([t for seg in seg1 for t in seg[:2]] + [t for seg in seg2 for t in seg[:2]]))
        elementary_intervals = []
        if len(time_points) >= 2:
            elementary_intervals = [(time_points[i], time_points[i + 1]) for i in range(len(time_points) - 1)]

        # 2) instantaneous event times (union)
        instant_times = sorted(set([t for t, _ in ev1] + [t for t, _ in ev2]))

        # 3) weighted contingency
        contingency: dict[tuple[Optional[str], Optional[str]], float] = {}
        total_weight = 0.0

        # (A) segments: weight = duration
        for start, end in elementary_intervals:
            duration = end - start
            if duration <= 0:
                continue
            c1 = get_code_segments(start, seg1)
            c2 = get_code_segments(start, seg2)
            total_weight += duration
            contingency[(c1, c2)] = contingency.get((c1, c2), 0.0) + duration

        # (B) events: weight = event_weight
        for t in instant_times:
            c1 = get_code_at_time(t, seg1, ev1)
            c2 = get_code_at_time(t, seg2, ev2)
            total_weight += event_weight
            contingency[(c1, c2)] = contingency.get((c1, c2), 0.0) + event_weight

        if total_weight == 0:
            return math.nan, math.nan, math.nan, contingency, total_weight

        # observed agreement (Po)
        po = sum(w for (c1, c2), w in contingency.items() if c1 == c2) / total_weight

        # marginals
        codes1: dict[Optional[str], float] = {}
        codes2: dict[Optional[str], float] = {}
        for (c1, c2), w in contingency.items():
            codes1[c1] = codes1.get(c1, 0.0) + w
            codes2[c2] = codes2.get(c2, 0.0) + w

        # expected agreement (Pe)
        all_codes = set(codes1) | set(codes2)
        pe = sum((codes1.get(c, 0.0) / total_weight) * (codes2.get(c, 0.0) / total_weight) for c in all_codes)

        # kappa
        if (1 - pe) == 0:
            kappa = math.nan
        else:
            kappa = (po - pe) / (1 - pe)

        return kappa, po, pe, contingency, total_weight

    # ------------------------------------------------------------------
    # Dialogs: rounding + event_weight
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
    # Rounding
    # ------------------------------------------------------------------

    df["Start (s)"] = df["Start (s)"].round(round_decimals)
    df["Stop (s)"] = df["Stop (s)"].round(round_decimals)

    # ------------------------------------------------------------------
    # Build grouped observations including modifiers (BORIS tuple columns)
    # ------------------------------------------------------------------

    unique_obs_list = df["Observation id"].unique().tolist()

    modifiers: list = [col for col in df.columns if isinstance(col, tuple)]

    grouped: dict[str, list[tuple[float, float, str]]] = {}
    for obs, group in df.groupby("Observation id"):
        o: list[tuple[float, float, str]] = []
        cols = ["Start (s)", "Stop (s)", "Subject", "Behavior"] + modifiers

        for row in group[cols].itertuples(index=False, name=None):
            # row layout: (start, stop, subject, behavior, mod1, mod2, ...)
            start, stop, subject, behavior = row[0], row[1], row[2], row[3]

            # collect modifiers that belong to this behavior
            modif_list = [row[i] for idx, i in enumerate(range(4, 4 + len(modifiers))) if modifiers[idx][0] == behavior]

            code = subject + "|" + behavior + "|" + ",".join(modif_list)
            o.append((start, stop, code))

        grouped[obs] = o

    # ------------------------------------------------------------------
    # Pairwise kappa
    # ------------------------------------------------------------------

    ck_results: dict = {}
    str_results: str = ""
    nan_pairs: list[tuple[str, str]] = []

    for idx1, obs_id1 in enumerate(unique_obs_list):
        obs1 = grouped[obs_id1]

        for obs_id2 in unique_obs_list[idx1:]:
            obs2 = grouped[obs_id2]

            kappa, po, pe, table, total_w = cohen_kappa_weighted_by_time(obs1, obs2, event_weight=event_weight)

            if math.isnan(kappa):
                nan_pairs.append((obs_id1, obs_id2))
                ck_results[(obs_id1, obs_id2)] = "NaN"
                ck_results[(obs_id2, obs_id1)] = "NaN"
                str_results += f"{obs_id1} - {obs_id2}: Kappa=NaN  Po={po}  Pe={pe}  Total weight={total_w}  Event weight={event_weight}\n"
            else:
                ck_results[(obs_id1, obs_id2)] = f"{kappa:.3f}"
                ck_results[(obs_id2, obs_id1)] = f"{kappa:.3f}"
                str_results += (
                    f"{obs_id1} - {obs_id2}: "
                    f"Kappa={kappa:.3f}  Po={po:.3f}  Pe={pe:.3f}  Total weight={total_w:.3f}  "
                    f"Event weight={event_weight}\n"
                )

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
