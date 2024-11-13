"""
BORIS plugin

"""

import pandas as pd


def number_of_occurences(df: pd.DataFrame, observations_list: list = []):
    """
    Calculate the number of occurrences per subject for a given list of observations.
    If the observations list is empty, the function will include all available observations.
    """
    if not observations_list:
        return df.groupby(["Subject", "Behavior"])["Behavior"].count().reset_index(name="number of occurences")
    else:
        return (
            df[df["Observation id"].isin(observations_list)]
            .groupby(["Subject", "Behavior"])["Behavior"]
            .count()
            .reset_index(name="number of occurences")
        )


print("number_of_occurences loaded")
