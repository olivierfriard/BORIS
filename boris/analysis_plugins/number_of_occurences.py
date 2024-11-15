"""
BORIS plugin

number of occurences of behaviors
"""

import pandas as pd

__version__ = "0.1.0"
__version_date__ = "2024-11-14"
__plugin_name__ = "Number of occurences of behaviors"


def number_of_occurences(df: pd.DataFrame, observations_list: list = [], parameters: dict = {}) -> pd.DataFrame:
    """
    Calculate the number of occurrences of behaviors per subject for a given list of observations.
    If the observations list is empty, the function will include all available observations.

    parameters
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

    return df.groupby(["Subject", "Behavior"])["Behavior"].count().reset_index(name="number of occurences")
