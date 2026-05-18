"""
BORIS plugin

Export events to Praat TextGrid using one tier per subject/behavior.
"""

from pathlib import Path

import pandas as pd
from PySide6.QtWidgets import QFileDialog

from boris import config as cfg

__version__ = "0.1.0"
__version_date__ = "2026-05-14"
__plugin_name__ = "Export events as Praat TextGrid (subject-behavior tiers)"
__author__ = "Olivier Friard - University of Torino - Italy"
__description__ = """
Export selected BORIS events to Praat TextGrid files.

Each subject/behavior pair is exported as a separate tier. This allows
overlapping behaviors for the same subject to be represented in one TextGrid
file, because overlapping behaviors no longer share the same IntervalTier.
"""


REQUIRED_COLUMNS = {
    "Observation id",
    "Subject",
    "Behavior",
    "Behavior type",
    "Start (s)",
    "Stop (s)",
}


def run(df: pd.DataFrame, project: dict = None, parameters: dict = None) -> str:
    """
    Export the selected events to Praat TextGrid.
    """

    missing_columns = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing_columns:
        return "Missing column(s): " + ", ".join(missing_columns)

    observation_ids = selected_observation_ids(df, project)
    if not observation_ids:
        return "No observations found; nothing to export."

    if len(observation_ids) == 1:
        obs_id = observation_ids[0]
        default_file_name = f"{safe_file_name(obs_id)}.TextGrid"
        file_name, _ = QFileDialog.getSaveFileName(
            None,
            "Export events as Praat TextGrid",
            default_file_name,
            "Praat TextGrid files (*.TextGrid);;All files (*)",
        )
        if not file_name:
            return "No output file selected; nothing written."

        path = Path(file_name)
        if path.suffix == "":
            path = path.with_suffix(".TextGrid")

        xmin, xmax = observation_bounds(df, obs_id, project, parameters)
        path.write_text(build_textgrid(df, obs_id, xmin=xmin, xmax=xmax), encoding="utf-8")
        return f"Saved: {path}"

    export_dir = QFileDialog.getExistingDirectory(None, "Export events as Praat TextGrid")
    if not export_dir:
        return "No output directory selected; nothing written."

    return export_textgrids(df, export_dir, project=project, parameters=parameters)


def export_textgrids(df: pd.DataFrame, export_dir: str | Path, project: dict = None, parameters: dict = None) -> str:
    """
    Write one TextGrid file per observation and return a short export report.
    """

    export_path = Path(export_dir)
    export_path.mkdir(parents=True, exist_ok=True)

    messages: list[str] = []
    used_paths: set[Path] = set()

    for obs_id in selected_observation_ids(df, project):
        xmin, xmax = observation_bounds(df, obs_id, project, parameters)
        out_path = unique_textgrid_path(export_path, obs_id, used_paths)
        out_path.write_text(build_textgrid(df, obs_id, xmin=xmin, xmax=xmax), encoding="utf-8")
        messages.append(f"Saved: {out_path}")

    if not messages:
        return "No observations found; nothing written."

    return "\n".join(messages)


def build_textgrid(df: pd.DataFrame, observation_id: str, xmin: float = 0.0, xmax: float | None = None) -> str:
    """
    Build the Praat TextGrid text for one observation.
    """

    missing_columns = sorted(REQUIRED_COLUMNS - set(df.columns))
    if missing_columns:
        raise ValueError("Missing column(s): " + ", ".join(missing_columns))

    obs_df = df[df["Observation id"] == observation_id].copy()
    obs_df = obs_df.dropna(subset=["Behavior", "Behavior type", "Start (s)", "Stop (s)"])
    obs_df["Subject"] = obs_df["Subject"].fillna(cfg.NO_FOCAL_SUBJECT)

    if xmax is None:
        xmax = dataframe_observation_xmax(obs_df)

    xmin = float(xmin)
    xmax = max(float(xmax), xmin)

    tiers = build_tiers(obs_df, xmin, xmax)

    lines = [
        'File type = "ooTextFile"',
        'Object class = "TextGrid"',
        "",
        f"xmin = {format_time(xmin)}",
        f"xmax = {format_time(xmax)}",
        "tiers? <exists>",
        f"size = {len(tiers)}",
        "item []:",
    ]

    for tier_index, tier in enumerate(tiers, start=1):
        if tier["class"] == "IntervalTier":
            lines.extend(interval_tier_lines(tier_index, tier["name"], tier["intervals"], xmin, xmax))
        else:
            lines.extend(point_tier_lines(tier_index, tier["name"], tier["points"], xmin, xmax))

    return "\n".join(lines) + "\n"


def build_tiers(df: pd.DataFrame, xmin: float, xmax: float) -> list[dict]:
    """
    Build tier payloads grouped by subject, behavior, and behavior type.
    """

    tiers: list[dict] = []
    if df.empty:
        return tiers

    df_sorted = df.sort_values(by=["Subject", "Behavior", "Behavior type", "Start (s)", "Stop (s)"], kind="stable")

    for (subject, behavior, behavior_type), group in df_sorted.groupby(
        ["Subject", "Behavior", "Behavior type"],
        dropna=False,
        sort=False,
    ):
        tier_name = make_tier_name(subject, behavior)
        if behavior_type in cfg.POINT_EVENT_TYPES:
            points = [
                {"time": float(row["Start (s)"]), "mark": str(behavior)}
                for row in group.to_dict("records")
                if xmin <= float(row["Start (s)"]) <= xmax
            ]
            if points:
                tiers.append({"class": "TextTier", "name": tier_name, "points": points})
            continue

        intervals = []
        for row in group.to_dict("records"):
            start = max(xmin, float(row["Start (s)"]))
            stop = min(xmax, float(row["Stop (s)"]))
            if stop <= start:
                continue
            intervals.append({"start": start, "stop": stop, "text": str(behavior)})

        for lane_index, lane in enumerate(split_overlapping_intervals(intervals)):
            lane_name = tier_name if lane_index == 0 else f"{tier_name}_{lane_index + 1}"
            tiers.append({"class": "IntervalTier", "name": lane_name, "intervals": lane})

    return tiers


def split_overlapping_intervals(intervals: list[dict]) -> list[list[dict]]:
    """
    Split same-tier overlapping intervals into additional tiers.
    """

    lanes: list[list[dict]] = []
    lane_stops: list[float] = []

    for interval in sorted(intervals, key=lambda item: (item["start"], item["stop"], item["text"])):
        for lane_index, last_stop in enumerate(lane_stops):
            if interval["start"] >= last_stop:
                lanes[lane_index].append(interval)
                lane_stops[lane_index] = interval["stop"]
                break
        else:
            lanes.append([interval])
            lane_stops.append(interval["stop"])

    return lanes


def interval_tier_lines(tier_index: int, name: str, intervals: list[dict], xmin: float, xmax: float) -> list[str]:
    intervals_with_nulls = add_null_intervals(intervals, xmin, xmax)
    lines = [
        f"    item [{tier_index}]:",
        '        class = "IntervalTier"',
        f'        name = "{praat_escape(name)}"',
        f"        xmin = {format_time(xmin)}",
        f"        xmax = {format_time(xmax)}",
        f"        intervals: size = {len(intervals_with_nulls)}",
    ]

    for idx, interval in enumerate(intervals_with_nulls, start=1):
        lines.extend(
            [
                f"        intervals [{idx}]:",
                f"            xmin = {format_time(interval['start'])}",
                f"            xmax = {format_time(interval['stop'])}",
                f'            text = "{praat_escape(interval["text"])}"',
            ]
        )

    return lines


def point_tier_lines(tier_index: int, name: str, points: list[dict], xmin: float, xmax: float) -> list[str]:
    points = sorted(points, key=lambda item: (item["time"], item["mark"]))
    lines = [
        f"    item [{tier_index}]:",
        '        class = "TextTier"',
        f'        name = "{praat_escape(name)}"',
        f"        xmin = {format_time(xmin)}",
        f"        xmax = {format_time(xmax)}",
        f"        points: size = {len(points)}",
    ]

    for idx, point in enumerate(points, start=1):
        lines.extend(
            [
                f"        points [{idx}]:",
                f"            number = {format_time(point['time'])}",
                f'            mark = "{praat_escape(point["mark"])}"',
            ]
        )

    return lines


def add_null_intervals(intervals: list[dict], xmin: float, xmax: float) -> list[dict]:
    """
    Fill IntervalTier gaps with Praat-compatible empty intervals.
    """

    filled: list[dict] = []
    cursor = xmin

    for interval in sorted(intervals, key=lambda item: (item["start"], item["stop"])):
        start = max(xmin, interval["start"])
        stop = min(xmax, interval["stop"])
        if stop <= start:
            continue
        if start > cursor:
            filled.append({"start": cursor, "stop": start, "text": "null"})
        elif start < cursor:
            start = cursor
        if stop > start:
            filled.append({"start": start, "stop": stop, "text": interval["text"]})
            cursor = stop

    if cursor < xmax:
        filled.append({"start": cursor, "stop": xmax, "text": "null"})

    return filled


def observation_bounds(df: pd.DataFrame, observation_id: str, project: dict = None, parameters: dict = None) -> tuple[float, float]:
    """
    Determine the TextGrid time domain for one observation.
    """

    obs_df = df[df["Observation id"] == observation_id] if "Observation id" in df.columns else pd.DataFrame()
    fallback_xmax = dataframe_observation_xmax(obs_df)

    if parameters:
        time_mode = parameters.get(cfg.TIME)
        if time_mode == cfg.TIME_ARBITRARY_INTERVAL:
            return float(parameters.get(cfg.START_TIME, 0.0)), float(parameters.get(cfg.END_TIME, fallback_xmax))

        if project and time_mode == cfg.TIME_OBS_INTERVAL:
            observation = project.get(cfg.OBSERVATIONS, {}).get(observation_id, {})
            interval = observation.get(cfg.OBSERVATION_TIME_INTERVAL, [0, 0])
            offset = float(observation.get(cfg.TIME_OFFSET, 0) or 0)
            xmin = float(interval[0] or 0) + offset
            if len(interval) > 1 and interval[1]:
                xmax = float(interval[1]) + offset
            else:
                xmax = observation_total_length(observation)
            return xmin, max(xmax, fallback_xmax, xmin)

        if project and time_mode == cfg.TIME_FULL_OBS:
            observation = project.get(cfg.OBSERVATIONS, {}).get(observation_id, {})
            return 0.0, max(observation_total_length(observation), fallback_xmax)

    return 0.0, fallback_xmax


def dataframe_observation_xmax(df: pd.DataFrame) -> float:
    if df.empty or "Stop (s)" not in df.columns:
        return 0.0
    values = pd.to_numeric(df["Stop (s)"], errors="coerce").dropna()
    if values.empty:
        return 0.0
    return max(0.0, float(values.max()))


def observation_total_length(observation: dict) -> float:
    """
    Return the best available observation length from the BORIS project dict.
    """

    obs_type = observation.get(cfg.TYPE)
    if obs_type == cfg.MEDIA:
        totals: list[float] = []
        lengths = observation.get(cfg.MEDIA_INFO, {}).get(cfg.LENGTH, {})
        for media_files in observation.get(cfg.FILE, {}).values():
            total = 0.0
            found_length = False
            for media_file in media_files:
                if media_file in lengths:
                    total += float(lengths[media_file])
                    found_length = True
            if found_length:
                totals.append(total)
        if totals:
            return max(totals)

    event_times = []
    for event in observation.get(cfg.EVENTS, []):
        try:
            event_times.append(float(event[cfg.EVENT_TIME_FIELD_IDX]))
        except Exception:
            continue

    return max(event_times, default=0.0)


def selected_observation_ids(df: pd.DataFrame, project: dict = None) -> list[str]:
    if project and project.get(cfg.OBSERVATIONS):
        return list(project[cfg.OBSERVATIONS].keys())
    if df.empty or "Observation id" not in df.columns:
        return []
    return sorted(str(obs_id) for obs_id in df["Observation id"].dropna().unique())


def unique_textgrid_path(export_dir: Path, observation_id: str, used_paths: set[Path]) -> Path:
    base_name = safe_file_name(observation_id) or "observation"
    path = export_dir / f"{base_name}.TextGrid"
    counter = 2
    while path in used_paths or path.exists():
        path = export_dir / f"{base_name}_{counter}.TextGrid"
        counter += 1
    used_paths.add(path)
    return path


def make_tier_name(subject: object, behavior: object) -> str:
    subject_text = str(subject).strip() or cfg.NO_FOCAL_SUBJECT
    behavior_text = str(behavior).strip()
    return f"{subject_text} {behavior_text}"


def praat_escape(value: object) -> str:
    return str(value).replace("\r", " ").replace("\n", " ").replace('"', '""')


def format_time(value: float) -> str:
    text = f"{float(value):.12f}".rstrip("0").rstrip(".")
    return text if text else "0"


def safe_file_name(value: object) -> str:
    file_name = str(value)
    for char in ["/", "\\", ":", "*", "?", '"', "<", ">", "|", "\n", "\r"]:
        file_name = file_name.replace(char, "_")
    return file_name
