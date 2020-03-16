"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2020 Olivier Friard


  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
  MA 02110-1301, USA.

"""

import logging
from decimal import Decimal

import numpy as np

from boris import utilities
from boris.config import *


def subj_behav_modif(cursor,
                     obsid,
                     subject,
                     time,
                     interval,
                     include_modifiers: bool):
    """
    current behaviors for observation obsId at time

    Args:
        cursor (sqlite3.cursor): cursor to aggregated events db
        obsid (str): id of observation
        subject (str): name of subject
        time (Decimal): time
        include_modifiers (bool): True: include modifiers False: do not

    Returns:
        list: list of lists [subject, behavior, modifiers]
    """

    s = []
    # state behaviors
    rows = cursor.execute(("SELECT behavior, modifiers FROM aggregated_events "
                           "WHERE "
                           "observation = ? "
                           "AND subject = ? "
                           "AND type = 'STATE' "
                           "AND (? BETWEEN start AND STOP) "),
                          (obsid, subject, float(time),)).fetchall()

    for row in rows:
        if include_modifiers:
            s.append([subject, row[0], row[1]])
        else:
            s.append([subject, row[0]])

    # point behaviors
    rows = cursor.execute(("SELECT behavior, modifiers FROM aggregated_events "
                           "WHERE "
                           "observation = ? "
                           "AND subject = ? "
                           "AND type = 'POINT' "
                           "AND abs(start - ?) <= ? "),
                          (obsid, subject, float(time), float(interval / 2),)).fetchall()

    for row in rows:
        if include_modifiers:
            s.append([subject, row[0], row[1]])
        else:
            s.append([subject, row[0]])

    return s


def cohen_kappa(cursor,
                obsid1: str,
                obsid2: str,
                interval: Decimal,
                selected_subjects: list,
                include_modifiers: bool):
    """
    Inter-rater reliability Cohen's kappa coefficient (time-unit)
    see Sequential Analysis and Observational Methods for the Behavioral Sciences p. 77

    Args:
        cursor (sqlite3.cursor): cursor to aggregated events db
        obsid1 (str): id of observation #1
        obsid2 (str): id of observation #2
        interval (decimal.Decimal): time unit (s)
        selected_subjects (list): subjects selected for analysis
        include_modifiers (bool): True: include modifiers False: do not

    Return:
        float: K
        str: result of analysis
    """

    # check if obs have events
    for obs_id in [obsid1, obsid2]:
        if not cursor.execute("SELECT * FROM aggregated_events WHERE observation = ? ",
                              (obs_id, )).fetchall():
            return -100, f"The observation {obs_id} has no recorded events"


    first_event = cursor.execute(("SELECT min(start) FROM aggregated_events "
                                  f"WHERE observation in (?, ?) AND subject in ({','.join('?'*len(selected_subjects))}) "),
                                 (obsid1, obsid2) + tuple(selected_subjects)).fetchone()[0]

    logging.debug(f"first_event: {first_event}")

    last_event = cursor.execute(("SELECT max(stop) FROM aggregated_events "
                                 f"WHERE observation in (?, ?) AND subject in ({','.join('?'*len(selected_subjects))}) "),
                                (obsid1, obsid2) + tuple(selected_subjects)).fetchone()[0]


    logging.debug(f"last_event: {last_event}")

    nb_events1 = cursor.execute(("SELECT COUNT(*) FROM aggregated_events "
                                 f"WHERE observation = ? AND subject in ({','.join('?'*len(selected_subjects))}) "),
                                (obsid1,) + tuple(selected_subjects)).fetchone()[0]
    nb_events2 = cursor.execute(("SELECT COUNT(*) FROM aggregated_events "
                                 f"WHERE observation = ? AND subject in ({','.join('?'*len(selected_subjects))}) "),
                                (obsid2,) + tuple(selected_subjects)).fetchone()[0]

    total_states = []

    currentTime = Decimal(str(first_event))
    while currentTime <= last_event:

        for obsid in [obsid1, obsid2]:
            for subject in selected_subjects:

                s = subj_behav_modif(cursor, obsid, subject, currentTime, interval, include_modifiers)

                if s not in total_states:
                    total_states.append(s)

                logging.debug(f"{obsid} {subject} {currentTime} {s}")

        currentTime += interval

    total_states = sorted(total_states)

    logging.debug(f"total_states: {total_states} len:{len(total_states)}")

    contingency_table = np.zeros((len(total_states), len(total_states)))

    seq1 = {}
    seq2 = {}
    currentTime = Decimal(str(first_event))
    while currentTime <= last_event:

        seq1[currentTime] = []
        seq2[currentTime] = []
        for subject in selected_subjects:

            s1 = subj_behav_modif(cursor, obsid1, subject, currentTime, interval, include_modifiers)
            s2 = subj_behav_modif(cursor, obsid2, subject, currentTime, interval, include_modifiers)

            seq1[currentTime].append(s1)
            seq2[currentTime].append(s2)

            logging.debug(f"currentTime: {currentTime} s1:{s1} s2:{s2}")

            try:
                contingency_table[total_states.index(s1), total_states.index(s2)] += 1
            except Exception:
                return -100, "Error with contingency table"

        currentTime += interval

    logging.debug(f"seq1:\n {list(seq1.values())}")
    logging.debug(f"seq2:\n {list(seq2.values())}")

    logging.debug(f"contingency_table:\n {contingency_table}")

    template = ("Observation: {obsid1}\n"
                "number of events: {nb_events1}\n\n"
                "Observation: {obsid2}\n"
                "number of events: {nb_events2:.0f}\n\n"
                "K = {K:.3f}")

    # out += "Observation length: <b>{:.3f} s</b><br>".format(self.observationTotalMediaLength(obsid1))
    # out += "Number of intervals: <b>{:.0f}</b><br><br>".format(self.observationTotalMediaLength(obsid1) / interval)

    # out += "Observation length: <b>{:.3f} s</b><br>".format(self.observationTotalMediaLength(obsid2))
    # out += "Number of intervals: <b>{:.0f}</b><br><br>".format(self.observationTotalMediaLength(obsid2) / interval)

    cols_sums = contingency_table.sum(axis=0)
    rows_sums = contingency_table.sum(axis=1)
    overall_total = contingency_table.sum()

    logging.debug(f"overall_total: {overall_total}")

    agreements = sum(contingency_table.diagonal())

    logging.debug(f"agreements: {agreements}")

    sum_ef = 0
    for idx in range(len(total_states)):
        sum_ef += rows_sums[idx] * cols_sums[idx] / overall_total

    logging.debug(f"sum_ef {sum_ef}")

    if not (overall_total - sum_ef):
        K = 1
    else:
        try:
            K = round((agreements - sum_ef) / (overall_total - sum_ef), 3)
        except Exception:
            K = nan

    out = template.format(obsid1=obsid1, obsid2=obsid2,
                          nb_events1=nb_events1, nb_events2=nb_events2,
                          K=K
                          )

    logging.debug(f"K: {K}")
    return K, out


def needleman_wunsch_identity(cursor,
                              obsid1: str,
                              obsid2: str,
                              interval,
                              selected_subjects: list,
                              include_modifiers: bool):
    """
    Needleman - Wunsch identity between 2 observations

    see http://anhaidgroup.github.io/py_stringmatching/v0.4.1/NeedlemanWunsch.html#

    Args:
        cursor (sqlite3.cursor): cursor to aggregated events db
        obsid1 (str): id of observation #1
        obsid2 (str): id of observation #2
        interval
        selected_subjects (list): subjects selected for analysis
        include_modifiers (bool): True: include modifiers False: do not

    Return:
        float: identity
        str: result of analysis
    """

    def zeros(shape):
        retval = []
        for x in range(shape[0]):
            retval.append([])
            for y in range(shape[1]):
                retval[-1].append(0)
        return retval

    match_award = 1
    mismatch_penalty = -1
    gap_penalty = -1


    def match_score(alpha, beta):
        if alpha == beta:
            return match_award
        elif alpha == '-' or beta == '-':
            return gap_penalty
        else:
            return mismatch_penalty

    def finalize(align1, align2):
        align1 = align1[::-1]
        align2 = align2[::-1]

        i, j = 0, 0

        symbol = []
        found = 0
        score = 0
        identity = 0
        for i in range(0, len(align1)):
            if align1[i] == align2[i]:
                symbol.append(align1[i])
                identity = identity + 1
                score += match_score(align1[i], align2[i])

            elif align1[i] != align2[i] and align1[i] != '-' and align2[i] != '-':
                score += match_score(align1[i], align2[i])
                symbol.append(" ")
                found = 0

            # if one of them is a gap, output a space
            elif align1[i] == '-' or align2[i] == '-':
                symbol.append(" ")
                score += gap_penalty

        identity = float(identity) / len(align1) * 100

        return {'identity': identity,
                'score': score,
                "align1": align1,
                "align2": align2,
                "symbol": symbol}


    def needle(seq1, seq2):
        m, n = len(seq1), len(seq2)

        score = zeros((m + 1, n + 1))

        for i in range(0, m + 1):
            score[i][0] = gap_penalty * i
        for j in range(0, n + 1):
            score[0][j] = gap_penalty * j
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                match = score[i - 1][j - 1] + match_score(seq1[i - 1], seq2[j - 1])
                delete = score[i - 1][j] + gap_penalty
                insert = score[i][j - 1] + gap_penalty
                score[i][j] = max(match, delete, insert)

        align1, align2 = [], []
        i, j = m, n 
        while i > 0 and j > 0:
            score_current = score[i][j]
            score_diagonal = score[i - 1][j - 1]
            score_up = score[i][j - 1]
            score_left = score[i - 1][j]

            if score_current == score_diagonal + match_score(seq1[i - 1], seq2[j - 1]):
                align1.append(seq1[i - 1])
                align2.append(seq2[j - 1])
                i -= 1
                j -= 1
            elif score_current == score_left + gap_penalty:
                align1.append(seq1[i - 1])
                align2.append("-")
                i -= 1
            elif score_current == score_up + gap_penalty:
                align1.append("-")
                align2.append(seq2[j - 1])
                j -= 1

        # Finish tracing up to the top left cell
        while i > 0:
            align1.append(seq1[i - 1])
            align2.append("-")
            i -= 1
        while j > 0:
            align1.append("-")
            align2.append(seq2[j - 1])
            j -= 1

        return finalize(align1, align2)


    first_event = cursor.execute(("SELECT min(start) FROM aggregated_events "
                                  f"WHERE observation in (?, ?) AND subject in ({','.join('?'*len(selected_subjects))}) "),
                                 (obsid1, obsid2) + tuple(selected_subjects)).fetchone()[0]

    if first_event is None:
        logging.debug(f"An observation has no recorded events: {obsid1} or {obsid2}")
        return -100, f"An observation has no recorded events: {obsid1} {obsid2}"

    logging.debug(f"first_event: {first_event}")

    last_event = cursor.execute(("SELECT max(start) FROM aggregated_events "
                                 f"WHERE observation in (?, ?) AND subject in ({','.join('?'*len(selected_subjects))}) "),
                                (obsid1, obsid2) + tuple(selected_subjects)).fetchone()[0]

    logging.debug(f"last_event: {last_event}")

    nb_events1 = cursor.execute(("SELECT COUNT(*) FROM aggregated_events "
                                 f"WHERE observation = ? AND subject in ({','.join('?'*len(selected_subjects))}) "),
                                (obsid1,) + tuple(selected_subjects)).fetchone()[0]


    nb_events2 = cursor.execute(("SELECT COUNT(*) FROM aggregated_events "
                                 f"WHERE observation = ? AND subject in ({','.join('?'*len(selected_subjects))}) "),
                                (obsid2,) + tuple(selected_subjects)).fetchone()[0]

    seq1, seq2 = {}, {}

    currentTime = Decimal(str(first_event))
    while currentTime <= last_event:

        seq1[currentTime], seq2[currentTime] = [], []

        for subject in selected_subjects:

            s1 = subj_behav_modif(cursor, obsid1, subject, currentTime, interval, include_modifiers)
            s2 = subj_behav_modif(cursor, obsid2, subject, currentTime, interval, include_modifiers)

            seq1[currentTime].append(s1)
            seq2[currentTime].append(s2)

            logging.debug(f"currentTime: {currentTime} s1:{s1} s2:{s2}")

        currentTime += interval

    logging.debug(f"seq1:\n {list(seq1.values())}")
    logging.debug(f"seq2:\n {list(seq2.values())}")

    r = needle(list(seq1.values()), list(seq2.values()))

    out = (f"Observation: {obsid1}\n"
           f"number of events: {nb_events1}\n\n"
           f"Observation: {obsid2}\n"
           f"number of events: {nb_events2:.0f}\n\n"
           f"identity = {r['identity']:.3f} %")

    logging.debug(f"identity: {r['identity']}")

    return r['identity'], out
