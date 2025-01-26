"""
BORIS plugin

Time budget
"""

import pandas as pd
import numpy as np

__version__ = "0.2.0"
__version_date__ = "2025-01-25"
__plugin_name__ = "Time budget"
__author__ = "Olivier Friard - University of Torino - Italy"


def run(df: pd.DataFrame):
    """
    Calculate the following values:

    - Total number of occurences of behavior
    - Total duration of behavior (in seconds)
    - Duration mean of behavior (in seconds)
    - Standard deviation of behavior duration (in seconds)
    - Inter-event intervals mean (in seconds)
    - Inter-event intervals standard deviation (in seconds)
    - % of total subject observation duration
    """

    string_results: str = "test\ntest1"

    group_by = ["Subject", "Behavior"]

    dfs = [
        df.groupby(group_by)["Behavior"].count().reset_index(name="number of occurences"),
        df.groupby(group_by)["Duration (s)"].sum().reset_index(name="total duration"),
        df.groupby(group_by)["Duration (s)"].mean().astype(float).round(3).reset_index(name="duration mean"),
        df.groupby(group_by)["Duration (s)"].std().astype(float).round(3).reset_index(name="duration std dev"),
    ]

    # inter events
    df2 = df.sort_values(by=["Observation id", "Subject", "Behavior", "Start (s)"])
    df2["diff"] = df2.groupby(["Observation id", "Subject", "Behavior"])["Start (s)"].shift(periods=-1) - df2["Stop (s)"]

    dfs.append(df2.groupby(group_by)["diff"].mean().astype(float).round(3).reset_index(name="inter-event intervals mean"))

    dfs.append(df2.groupby(group_by)["diff"].std().astype(float).round(3).reset_index(name="inter-event intervals std dev"))

    # % of total subject observation time

    interval = (df.groupby(["Subject"])["Stop (s)"].max() - df.groupby(["Subject"])["Start (s)"].min()).replace(0, np.nan)

    dfs.append(
        (100 * df.groupby(group_by)["Duration (s)"].sum() / interval)
        .astype(float)
        .round(3)
        .reset_index(name="% of total subject observation duration")
    )

    merged_df = dfs[0]
    for df in dfs[1:]:
        merged_df = pd.merge(merged_df, df, on=group_by)

    return merged_df, string_results


def main(df: pd.DataFrame, observations_list: list = [], parameters: dict = {}) -> pd.DataFrame:
    """
    filter by selected observations.
    filter by selected subjects.
    filter by selected behaviors.
    filter by time interval.
    """

    # filter selected observations
    if observations_list:
        df = df[df["Observation id"].isin(observations_list)]

    if parameters:
        # filter selected subjects
        df = df[df["Subject"].isin(parameters["selected subjects"])]

        # filter selected behaviors
        df = df[df["Behavior"].isin(parameters["selected behaviors"])]

        # filter selected time interval
        if parameters["start time"] is not None and parameters["end time"] is not None:
            MIN_TIME = parameters["start time"]
            MAX_TIME = parameters["end time"]

            df_interval = df[
                (
                    ((df["Start (s)"] >= MIN_TIME) & (df["Start (s)"] <= MAX_TIME))
                    | ((df["Stop (s)"] >= MIN_TIME) & (df["Stop (s)"] <= MAX_TIME))
                )
                | ((df["Start (s)"] < MIN_TIME) & (df["Stop (s)"] > MAX_TIME))
            ]

            df_interval.loc[df["Start (s)"] < MIN_TIME, "Start (s)"] = MIN_TIME
            df_interval.loc[df["Stop (s)"] > MAX_TIME, "Stop (s)"] = MAX_TIME

            df_interval.loc[:, "Duration (s)"] = df_interval["Stop (s)"] - df_interval["Start (s)"]

            df = df_interval

    return run(df)
