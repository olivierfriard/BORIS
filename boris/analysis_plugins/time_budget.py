"""
BORIS plugin
"""

import pandas as pd

__version__ = "0.1.0"
__version_date__ = "2024-11-14"
__plugin_name__ = "Time budget"
__author__ = "Olivier Friard - University of Torino - Italy"


def time_budget(df: pd.DataFrame, observations_list: list = [], parameters: dict = {}) -> pd.DataFrame:
    """
    Calculate the following values for the selected observations:

    - Total number of occurences of behavior
    - Total duration of behavior (in seconds)
    - Duration mean of behavior (in seconds)
    - Standard deviation of behavior duration (in seconds)
    - Inter-event intervals mean (in seconds)
    - Inter-event intervals standard deviation (in seconds)
    - % of total duration
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

    dfs = [
        df.groupby(["Subject", "Behavior"])["Behavior"].count().reset_index(name="number of occurences"),
        df.groupby(["Subject", "Behavior"])["Duration (s)"].sum().reset_index(name="total duration"),
        df.groupby(["Subject", "Behavior"])["Duration (s)"].mean().astype(float).round(3).reset_index(name="duration mean"),
        df.groupby(["Subject", "Behavior"])["Duration (s)"].std().astype(float).round(3).reset_index(name="duration std dev"),
    ]

    # inter events
    df2 = df.sort_values(by=["Observation id", "Subject", "Behavior", "Start (s)"])
    df2["diff"] = df2.groupby(["Observation id", "Subject", "Behavior"])["Start (s)"].shift(periods=-1) - df2["Stop (s)"]

    dfs.append(df2.groupby(["Subject", "Behavior"])["diff"].mean().astype(float).round(3).reset_index(name="inter-event intervals mean"))

    dfs.append(df2.groupby(["Subject", "Behavior"])["diff"].std().astype(float).round(3).reset_index(name="inter-event intervals std dev"))

    # % of time
    dfs.append(
        (100 * df.groupby(["Subject", "Behavior"])["Duration (s)"].sum() / df.groupby(["Subject"])["Duration (s)"].sum())
        .astype(float)
        .round(3)
        .reset_index(name="% of total duration")
    )

    merged_df = dfs[0]
    for df in dfs[1:]:
        merged_df = pd.merge(merged_df, df, on=["Subject", "Behavior"])

    return merged_df
