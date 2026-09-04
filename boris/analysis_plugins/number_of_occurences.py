"""
BORIS plugin

number of occurrences of behaviors
"""

import pandas as pd

__version__ = "0.3.0"
__version_date__ = "2025-03-17"
__plugin_name__ = "Number of occurrences of behaviors"
__author__ = "Olivier Friard - University of Torino - Italy"


def run(df: pd.DataFrame):
    """
    Calculate the number of occurrences of behaviors by subject.
    """

    df_results: pd.DataFrame = df.groupby(["Subject", "Behavior"])["Behavior"].count().reset_index(name="number of occurrences")

    return df_results
