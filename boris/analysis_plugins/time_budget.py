"""
BORIS plugin
"""

import pandas as pd

__version__ = "0.1.0"
__version_date__ = "2024-11-14"


def time_budget(dataframe: pd.DataFrame, observations_list: list = [], parameters: dict = {}) -> pd.DataFrame:
    """
    Calculate the following values for a given list of observations:

    - total number of occurences
    - total duration
    - duration mean
    - duration std dev
    - inter-event intervals mean
    - inter-event intervals std dev
    - % of total duration

    If the observations list is empty, the function will include all available observations.
    """

    # filter selected observations
    if observations_list:
        dataframe = dataframe[dataframe["Observation id"].isin(observations_list)]

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
            df_interval.loc[df["Stop (s)"] > MAX_TIME, "Start (s)"] = MAX_TIME

            df_interval.loc[:, "Duration (s)"] = df_interval["Stop (s)"] - df_interval["Start (s)"]

            df = df_interval

    dfs = [
        dataframe.groupby(["Subject", "Behavior"])["Behavior"].count().reset_index(name="number of occurences"),
        dataframe.groupby(["Subject", "Behavior"])["Duration (s)"].sum().reset_index(name="total duration"),
        dataframe.groupby(["Subject", "Behavior"])["Duration (s)"].mean().reset_index(name="duration mean"),
        dataframe.groupby(["Subject", "Behavior"])["Duration (s)"].std().reset_index(name="duration std dev"),
    ]

    # inter events
    df2 = dataframe.sort_values(by=["Observation id", "Subject", "Behavior", "Start (s)"])
    df2["diff"] = df2.groupby(["Observation id", "Subject", "Behavior"])["Start (s)"].shift(periods=-1) - df2["Stop (s)"]

    dfs.append(df2.groupby(["Subject", "Behavior"])["diff"].mean().reset_index(name="inter-event intervals mean"))

    dfs.append(df2.groupby(["Subject", "Behavior"])["diff"].std().reset_index(name="inter-event intervals std dev"))

    dfs.append(
        (
            100 * dataframe.groupby(["Subject", "Behavior"])["Duration (s)"].sum() / dataframe.groupby(["Subject"])["Duration (s)"].sum()
        ).reset_index(name="% of total duration")
    )

    merged_df = dfs[0]
    for df in dfs[1:]:
        merged_df = pd.merge(merged_df, df, on=["Subject", "Behavior"])

    return merged_df
