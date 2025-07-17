"""
BORIS plugin

number of occurences of behaviors by independent_variable
"""

import pandas as pd

__version__ = "0.4.0"
__version_date__ = "2025-07-17"
__plugin_name__ = "Number of occurences of behaviors by subject by independent_variable"
__author__ = "Olivier Friard - University of Torino - Italy"


def run(df: pd.DataFrame):
    """
    Calculate the number of occurrences of behaviors by subject and by independent_variable.

    This plugin returns a Pandas dataframe
    """

    df_results_list: list = []

    flag_variable_found = False

    for column in df.columns:
        if isinstance(column, tuple) or (isinstance(column, str) and not column.startswith("independent variable '")):
            continue

        flag_variable_found = True
        grouped_df: df.DataFrame = (
            df.groupby(
                [
                    column,
                    "Subject",
                    "Behavior",
                ]
            )["Behavior"]
            .count()
            .reset_index(name="number of occurences")
        )

        grouped_df.rename(columns={column: "Value"}, inplace=True)

        grouped_df.insert(0, "independent variable name", column)

        df_results_list.append(grouped_df)

    df_results = pd.concat(df_results_list, ignore_index=True) if df_results_list else pd.DataFrame([])

    if not flag_variable_found:
        return "No independent variable found"
    else:
        return df_results
