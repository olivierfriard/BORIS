"""
BORIS plugin

number of occurences of behaviors
"""

import pandas as pd

__version__ = "0.0.1"
__version_date__ = "2025-04-10"
__plugin_name__ = "Behavior latency"
__author__ = "Olivier Friard - University of Torino - Italy"


import itertools


def run(df: pd.DataFrame):
    """
    Latency of a behavior after another.
    """

    df["start_time"] = pd.to_datetime(df["Start (s)"])
    df["end_time"] = pd.to_datetime(df["Stop (s)"])

    latency_by_subject: dict = {}

    for subject, group in df.groupby("subject"):
        behaviors = group["behavior"].tolist()
        # combinations = []
        # Utiliser itertools pour créer des combinaisons 2 à 2 des comportements
        for comb in itertools.combinations(behaviors, 2):
            # combinations.append(comb)

            last_A_end_time = None

            # Liste pour stocker les latences de chaque sujet
            subject_latency = []

            for index, row in group.iterrows():
                if row["behavior"] == comb[0]:
                    # Si on rencontre un comportement A, on réinitialise le temps de fin du comportement A
                    last_A_end_time = row["end_time"]
                    subject_latency.append(None)  # Pas de latence pour A
                elif row["behavior"] == comb[1] and last_A_end_time is not None:
                    # Si on rencontre un comportement B et qu'on a déjà vu un A avant
                    latency_time = row["start_time"] - last_A_end_time
                    subject_latency.append(latency_time)
                else:
                    # Si on rencontre un B mais sans A avant
                    subject_latency.append(None)

            # Ajout des latences calculées au DataFrame
            df.loc[group.index, f"latency {comb[1]} after {comb[0]}"] = subject_latency

            # Calcul de la latence totale ou moyenne par sujet
            latency_by_subject[(subject, comb)] = df.groupby("subject")["latency"].agg(["sum", "mean"])

    return str(latency_by_subject)
