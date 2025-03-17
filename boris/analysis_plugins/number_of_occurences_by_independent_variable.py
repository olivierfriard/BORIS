"""
BORIS plugin

number of occurences of behaviors by independent_variable
"""

import pandas as pd

__version__ = "0.3.0"
__version_date__ = "2025-03-17"
__plugin_name__ = "Number of occurences of behaviors by subject by independent_variable"
__author__ = "Olivier Friard - University of Torino - Italy"


def run(df: pd.DataFrame):
    """
    Calculate the number of occurrences of behaviors by subject and by independent_variable.

    This plugin returns a Pandas dataframe
    """

    df_results: df.DataFrame = (
        df.groupby(
            [
                "independent variable 'Weather'",
                "Subject",
                "Behavior",
            ]
        )["Behavior"]
        .count()
        .reset_index(name="number of occurences")
    )

    return df_results
