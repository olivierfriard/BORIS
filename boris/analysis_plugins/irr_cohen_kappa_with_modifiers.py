"""
BORIS plugin

Inter Rater Reliability (IRR) Unweighted Cohen's Kappa with modifiers
- Supports behaviors with duration (start < stop) AND instantaneous events (start == stop)
- Aggregated warning when kappa is NaN to avoid multiple popups
"""

import math

import pandas as pd
from PySide6.QtWidgets import QInputDialog, QMessageBox
from sklearn.metrics import cohen_kappa_score

__version__ = "0.0.4"
__version_date__ = "2026-01-30"
__plugin_name__ = "Inter Rater Reliability - Unweighted Cohen's Kappa with modifiers NEW"
__author__ = "Olivier Friard - University of Torino - Italy"
__description__ = """
This plugin calculates Cohen's Kappa to measure inter-rater reliability between two observers who code categorical behaviors over time.

- Unweighted: interval duration is NOT used.
- Modifiers are included in the category label.
- Behaviors with duration (start < stop) are evaluated on elementary intervals.
- Instantaneous behaviors (start == stop) are evaluated as point-events (each counts as 1 unit).
- If Cohen's Kappa is undefined (NaN) for some observer pairs, a single aggregated warning is shown at the end.
"""


def run(df: pd.DataFrame):
    """
    Calculate the Inter Rater Reliability - Unweighted Cohen's Kappa with modifiers
    (supports instantaneous events: start == stop)
    """

    # ---------- helpers -------------------------------------------------

    def split_segments_events(obs):
        """Separate duration segments from instantaneous events."""
        segments = []
        events = []
        for start, stop, code in obs:
            if start < stop:
                segments.append((start, stop, code))
            else:  # start == stop
                events.append((start, code))
        return segments, events

    def get_code_segments(t, segments):
        """Codes active from duration segments at time t (no instantaneous events)."""
        active = [seg[2] for seg in segments if seg[0] <= t < seg[1]]
        if not active:
            return ""
        return "+".join(sorted(active))

    def get_code_at_time(t, segments, events):
        """
        Codes at exact time t for an event-observation:
        includes both:
        - active duration segments at t
        - instantaneous events exactly at t
        """
        active = [seg[2] for seg in segments if seg[0] <= t < seg[1]]
        instant = [ev[1] for ev in events if ev[0] == t]
        codes = active + instant
        if not codes:
            return ""
        return "+".join(sorted(codes))

    # ---------- rounding ------------------------------------------------

    round_decimals, ok = QInputDialog.getInt(
        None,
        "Rounding",
        "Enter the number of decimal places for rounding (can be negative)",
        value=3,
        minValue=-5,
        maxValue=3,
        step=1,
    )

    df["Start (s)"] = df["Start (s)"].round(round_decimals)
    df["Stop (s)"] = df["Stop (s)"].round(round_decimals)

    # ---------- group data by observer ---------------------------------

    unique_obs_list = df["Observation id"].unique().tolist()

    # Detect modifier columns (BORIS style: tuple columns)
    modifiers: list = [col for col in df.columns if isinstance(col, tuple)]

    grouped: dict = {}
    for obs, group in df.groupby("Observation id"):
        o: list = []
        cols = ["Start (s)", "Stop (s)", "Subject", "Behavior"] + modifiers
        for row in group[cols].itertuples(index=False, name=None):
            # row layout: (start, stop, subject, behavior, mod1, mod2, ...)
            behavior = row[3]

            # collect modifiers that belong to this behavior
            modif_list = [row[i] for idx, i in enumerate(range(4, 4 + len(modifiers))) if modifiers[idx][0] == behavior]

            # encode subject|behavior|mod1,mod2,...
            code = row[2] + "|" + behavior + "|" + ",".join(modif_list)
            o.append((row[0], row[1], code))

        grouped[obs] = o

    # ---------- compute Cohen's Kappa ----------------------------------

    ck_results: dict = {}
    nan_pairs: list[tuple[str, str]] = []  # collect NaN pairs to show ONE popup at end

    for idx1, obs_id1 in enumerate(unique_obs_list):
        obs1 = grouped[obs_id1]
        seg1, ev1 = split_segments_events(obs1)

        for obs_id2 in unique_obs_list[idx1:]:
            obs2 = grouped[obs_id2]
            seg2, ev2 = split_segments_events(obs2)

            # 1) build elementary intervals from segment boundaries ONLY
            time_points = sorted(set([t for seg in seg1 for t in seg[:2]] + [t for seg in seg2 for t in seg[:2]]))

            elementary_intervals = []
            if len(time_points) >= 2:
                elementary_intervals = [(time_points[i], time_points[i + 1]) for i in range(len(time_points) - 1)]

            # 2) instant event times (union)
            instant_times = sorted(set([t for t, _ in ev1] + [t for t, _ in ev2]))

            print(f"{instant_times=}")

            # 3) build code lists:
            # - interval observations: segment codes only (avoid double-counting events)
            obs1_codes = [get_code_segments(t0, seg1) for (t0, t1) in elementary_intervals]
            obs2_codes = [get_code_segments(t0, seg2) for (t0, t1) in elementary_intervals]

            # - event observations: codes at exact time (segments + events)
            obs1_codes += [get_code_at_time(t, seg1, ev1) for t in instant_times]
            obs2_codes += [get_code_at_time(t, seg2, ev2) for t in instant_times]

            print(f"{obs1_codes=}")
            print(f"{obs2_codes=}")

            # If nothing to compare, mark NaN
            if len(obs1_codes) == 0:
                nan_pairs.append((obs_id1, obs_id2))
                ck_results[(obs_id1, obs_id2)] = "NaN"
                ck_results[(obs_id2, obs_id1)] = "NaN"
                continue

            # Cohen's Kappa
            kappa = cohen_kappa_score(obs1_codes, obs2_codes)

            if math.isnan(kappa):
                nan_pairs.append((obs_id1, obs_id2))
                ck_results[(obs_id1, obs_id2)] = "NaN"
                ck_results[(obs_id2, obs_id1)] = "NaN"
            else:
                print(f"{obs_id1} - {obs_id2}: Cohen's Kappa : {kappa:.3f}")
                ck_results[(obs_id1, obs_id2)] = f"{kappa:.3f}"
                ck_results[(obs_id2, obs_id1)] = f"{kappa:.3f}"

    # ---------- ONE aggregated warning at the end -----------------------

    if nan_pairs:
        pairs_txt = "\n".join([f"- {a} vs {b}" for a, b in nan_pairs])
        QMessageBox.warning(
            None,
            "Cohen's Kappa not defined (NaN)",
            (
                "Cohen's Kappa was not defined (NaN) for the following observer pairs:\n\n"
                f"{pairs_txt}\n\n"
                "Typical reasons:\n"
                "- perfect agreement without variability (only one category present)\n"
                "- no intervals/events available to compare\n\n"
                "Consider reporting percent agreement (and/or Gwet's AC1) for those pairs."
            ),
        )

    # ---------- output ---------------------------------------------------

    df_results = pd.Series(ck_results).unstack()
    return df_results
