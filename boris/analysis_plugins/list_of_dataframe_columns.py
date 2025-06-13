"""
BORIS plugin

number of occurences of behaviors
"""

import pandas as pd

__version__ = "0.0.1"
__version_date__ = "2025-06-13"
__plugin_name__ = "List of dataframe columns"
__author__ = "Olivier Friard - University of Torino - Italy"


def run(df: pd.DataFrame) -> pd.DataFrame:
    """
    List the columns present in the dataframe
    """

    df_results = pd.DataFrame(df.columns, columns=["column name"])

    return df_results
