"""
BORIS plugin

Time budget
"""

import pandas as pd
import numpy as np

__version__ = "0.3.0"
__version_date__ = "2025-03-17"
__plugin_name__ = "Time budget"
__author__ = "Olivier Friard - University of Torino - Italy"


def run(df: pd.DataFrame):
    """
    Calculate the following values:

    - Total number of occurences of behavior
    - Total duration of behavior (in seconds)  (pandas.DataFrame.sum() ignore NaN values when computing the sum. Use min_count=1)
    - Duration mean of behavior (in seconds)
    - Standard deviation of behavior duration (in seconds)
    - Inter-event intervals mean (in seconds)
    - Inter-event intervals standard deviation (in seconds)
    - % of total subject observation duration
    """

    print("running time budget plugin")

    print(df)

    group_by = ["Subject", "Behavior"]

    dfs = [
        df.groupby(group_by)["Behavior"].count().reset_index(name="number of occurences"),
        df.groupby(group_by)["Duration (s)"].sum(min_count=1).reset_index(name="total duration"),
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
        (100 * df.groupby(group_by)["Duration (s)"].sum(min_count=1) / interval)
        .astype(float)
        .round(3)
        .reset_index(name="% of total subject observation duration")
    )

    merged_df = dfs[0]
    for df in dfs[1:]:
        merged_df = pd.merge(merged_df, df, on=group_by)

    return merged_df
