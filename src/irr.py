"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2019 Olivier Friard


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

from decimal import Decimal
import logging
import utilities
import numpy as np
from config import *


def cohen_kappa(cursor,
                obsid1, obsid2,
                interval,
                selected_subjects,
                include_modifiers):
    """
    Inter-rater reliability Cohen's kappa coefficient (time-unit)
    see Sequential Analysis and Observational Methods for the Behavioral Sciences p. 77


    Args:
        cursor (sqlite3.cursor): cursor to aggregated events db
        obsid1 (str): id of observation #1
        obsid2 (str): id of observation #2
        selected_subjects (list): subjects selected for analysis
        include_modifiers (bool): True: include modifiers False: do not

    Return:
        float: K
        str: result of analysis
    """

    def subj_behav_modif(cursor, obsid, subject, time, include_modifiers):
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
        rows = cursor.execute("""SELECT behavior, modifiers FROM aggregated_events
                  WHERE
                   observation = ?
                   AND subject = ?
                   AND type = 'STATE'
                   AND (? BETWEEN start AND STOP)
                   """ ,
                (obsid, subject, float(currentTime),)).fetchall()

        for row in rows:
            if include_modifiers:
                s.append([subject, row[0], row[1]])
            else:
                s.append([subject, row[0]])

        # point behaviors
        rows = cursor.execute("""SELECT behavior, modifiers FROM aggregated_events
                  WHERE
                   observation = ?
                   AND subject = ?
                   AND type = 'POINT'
                   AND abs(start - ?) <= ?
                   """ ,
                (obsid, subject, float(currentTime), float(interval / 2),)).fetchall()

        for row in rows:
            if include_modifiers:
                s.append([subject, row[0], row[1]])
            else:
                s.append([subject, row[0]])

        return s

    first_event = cursor.execute(("SELECT min(start) FROM aggregated_events "
                                  "WHERE observation in (?, ?) AND subject in ('{}') ").format("','".join(selected_subjects)),
                                                                                               (obsid1, obsid2)).fetchone()[0]

    if first_event is None:
        logging.debug("An observation has no recorded events: {} or {}".format(obsid1, obsid2))
        return -100, "An observation has no recorded events: {} {}".format(obsid1, obsid2)

    logging.debug("first_event: {}".format(first_event))
    last_event = cursor.execute(("SELECT max(stop) FROM aggregated_events "
                                 "WHERE observation in (?, ?) AND subject in ('{}') ").format("','".join(selected_subjects)),
                                                                                             (obsid1, obsid2)).fetchone()[0]

    logging.debug("last_event: {}".format(last_event))

    nb_events1 = cursor.execute(("SELECT COUNT(*) FROM aggregated_events "
                                 "WHERE observation = ? AND subject in ('{}') ").format("','".join(selected_subjects)),
                                                                                        (obsid1,)).fetchone()[0]
    nb_events2 = cursor.execute(("SELECT COUNT(*) FROM aggregated_events "
                                 "WHERE observation = ? AND subject in ('{}') ").format("','".join(selected_subjects)),
                                                                                       (obsid2,)).fetchone()[0]

    total_states = []

    currentTime = Decimal(str(first_event))
    while currentTime <= last_event:

        for obsid in [obsid1, obsid2]:
            for subject in selected_subjects:

                s = subj_behav_modif(cursor, obsid, subject, currentTime, include_modifiers)

                if s not in total_states:
                    total_states.append(s)

                logging.debug("{} {} {} {}".format(obsid, subject, currentTime, s))

        currentTime += interval


    total_states = sorted(total_states)

    logging.debug("total_states: {} len:{}".format(total_states, len(total_states)))

    contingency_table = np.zeros((len(total_states), len(total_states)))

    currentTime = Decimal(str(first_event))
    while currentTime < last_event:

        for subject in selected_subjects:

            s1 = subj_behav_modif(cursor, obsid1, subject, currentTime, include_modifiers)
            s2 = subj_behav_modif(cursor, obsid2, subject, currentTime, include_modifiers)

            logging.debug("currentTime: {} s1:{} s2:{}".format(currentTime, s1, s2))

            try:
                contingency_table[total_states.index(s1), total_states.index(s2)] += 1
            except:
                return -100, "Error with contingency table"

        currentTime += interval

    logging.debug("contingency_table:\n {}".format(contingency_table))

    template = ("Observation: {obsid1}\n"
                "number of events: {nb_events1}\n\n"
                "Observation: {obsid2}\n"
                "number of events: {nb_events2:.0f}\n\n"
                "K = {K:.3f}")

    #out += "Observation length: <b>{:.3f} s</b><br>".format(self.observationTotalMediaLength(obsid1))
    #out += "Number of intervals: <b>{:.0f}</b><br><br>".format(self.observationTotalMediaLength(obsid1) / interval)

    #out += "Observation length: <b>{:.3f} s</b><br>".format(self.observationTotalMediaLength(obsid2))
    #out += "Number of intervals: <b>{:.0f}</b><br><br>".format(self.observationTotalMediaLength(obsid2) / interval)

    cols_sums = contingency_table.sum(axis=0)
    rows_sums = contingency_table.sum(axis=1)
    overall_total = contingency_table.sum()

    logging.debug("overall_total: {}".format(overall_total))

    agreements = sum(contingency_table.diagonal())

    logging.debug("agreements: {}".format(agreements))

    sum_ef = 0
    for idx in range(len(total_states)):
        sum_ef += rows_sums[idx] * cols_sums[idx] / overall_total

    logging.debug("sum_ef {}".format(sum_ef))

    if not (overall_total - sum_ef):
        K = 1
    else:
        try:
            K = round((agreements - sum_ef) / (overall_total - sum_ef), 3)
        except:
            K = nan

    out = template.format(obsid1=obsid1, obsid2=obsid2,
                          nb_events1=nb_events1, nb_events2=nb_events2,
                          K=K
                          )

    return K, out


