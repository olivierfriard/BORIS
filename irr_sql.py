"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2018 Olivier Friard


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
                state_behaviors_codes,
                point_behaviors_codes,
                selected_subjects,
                include_modifiers):
    """
    
    Args:
        cursor (sqlite3.cursor): cursor to aggregated events db
        obsid1 (str): id of observation #1
        obsid2 (str): id of observation #2
        state_behaviors_codes (list): list of behavior codes defined as state event
        point_behaviors_codes (list): list of behavior codes defined as point event
        selected_subjects (list): subjects selected for analysis
        include_modifiers (bool): True: include modifiers False: do not
    
    Return:
         str: result of analysis
    """
    last_event = cursor.execute("""SELECT max(stop) FROM events WHERE observation in (?, ?) AND subject in ('{}') """.format("','".join(selected_subjects)),
                                               (obsid1, obsid2)).fetchone()[0]

    logging.debug("last_event: {}".format(last_event))
    
    print(obsid1)
    print(selected_subjects)
    nb_events1 = cursor.execute("""SELECT COUNT(*) FROM events WHERE observation = ? AND subject in ('{}') """.format("','".join(selected_subjects)),
                                               (obsid1,)).fetchone()[0]
    
    nb_events2 = cursor.execute("""SELECT COUNT(*) FROM events WHERE observation = ? AND subject in ('{}') """.format("','".join(selected_subjects)),
                                               (obsid2,)).fetchone()[0]

    total_states = []

    currentTime = Decimal("0")
    while currentTime <= last_event:

        for obsid in [obsid1, obsid2]:
            for subject in selected_subjects:
                
                print(subject, currentTime)
            
                rows = cursor.execute("""SELECT behavior, modifiers FROM events
                          WHERE
                           observation = ?
                           AND subject = ?
                           AND type = 'STATE'
                           AND ( ? BETWEEN start AND STOP)
                           """ ,
                        (obsid, subject, float(currentTime),)).fetchall()

                s = []
                for row in rows:
                    s.append([subject, row[0], row[1]])
                    
                if s not in total_states:
                    total_states.append(s)
        
        print("currentTime ", currentTime, )

        currentTime += interval


    total_states = sorted(total_states)
    
    logging.debug("total_states: {}".format(total_states))
    
    print(total_states)

    contingency_table = np.zeros((len(total_states), len(total_states)))

    '''tot1, tot2 = [], []'''

    currentTime = Decimal("0")
    while currentTime < last_event:

        for subject in selected_subjects:
            
            rows = cursor.execute("""SELECT behavior, modifiers FROM events
                      WHERE
                       observation = ?
                       AND subject = ?
                       AND type = 'STATE'
                       AND ( ? BETWEEN start AND STOP)
                       """ ,
                    (obsid1, subject, float(currentTime),)).fetchall()

            s1 = []
            for row in rows:
                s1.append([subject, row[0], row[1]])

            rows = cursor.execute("""SELECT behavior, modifiers FROM events
                      WHERE
                       observation = ?
                       AND subject = ?
                       AND type = 'STATE'
                       AND ( ? BETWEEN start AND STOP)
                       """ ,
                    (obsid2, subject, float(currentTime),)).fetchall()

            s2 = []
            for row in rows:
                s2.append([subject, row[0], row[1]])

            try:
                contingency_table[total_states.index(s1), total_states.index(s2)] += 1
            except:
                return "Error with contingency table"

        currentTime += interval

    '''
    print(tot1)
    print(tot2)
    '''

    '''
    taskdata=[[0,str(i),str(tot1[i])] for i in range(0,len(tot1))]+[[1,str(i),str(tot2[i])] for i in range(0,len(tot2))]
    ratingtask = agreement.AnnotationTask(data=taskdata) 
    print("kappa " +str(ratingtask.kappa()))
    '''

    logging.debug("contingency_table:\n {}".format(contingency_table))

    out = ""
    out += "<b>Cohen's Kappa - Index of Inter-rater Reliability</b><br><br>"

    out += "Interval time: <b>{:.3f} s</b><br><br>".format(interval)
    out += "Selected subjects: <b>{}</b><br><br>".format(", ".join(selected_subjects))

    out += "Observation #1: <b>{}</b><br>".format(obsid1)
    out += "number of events: <b>{:.0f}</b><br>".format(nb_events1)

    #out += "Observation length: <b>{:.3f} s</b><br>".format(self.observationTotalMediaLength(obsid1))
    #out += "Number of intervals: <b>{:.0f}</b><br><br>".format(self.observationTotalMediaLength(obsid1) / interval)

    out += "Observation #2: <b>{}</b><br>".format(obsid2)
    out += "number of events: <b>{:.0f}</b><br>".format(nb_events2)

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

    try:
        K = (agreements - sum_ef) / (overall_total - sum_ef)
    except:
        K = 1

    out += "K: <b>{:.3f}</b><br>".format(K)
    
    return out


if __name__ == '__main__':
    
    from decimal import Decimal
    
    from nltk import agreement
    
    
    logging.basicConfig(level=logging.INFO)
    
    
    obsid1, obsid2 = "live1", "live2"
    obsid1, obsid2 = "live #1 no subj no modif", "live #2 no subj no modif"
    
    interval = 1
    
    #state_behaviors_codes = ['s']
    
    selected_subjects = ["No focal subject"]
    
    include_modifiers = True
    
 
   
    state_behaviors_codes = ['s']
    point_behaviors_codes = ['p']
    
    
    import db_functions
    
    import test_sample_project
    
    print
    
    cursor = db_functions.load_aggregated_events_in_db(test_sample_project.p, [], [], [])
    #print(cursor)
    
    #import sys
    #sys.exit()
    
    print(cohen_kappa(cursor,
                obsid1, obsid2,
                interval,
                state_behaviors_codes,
                point_behaviors_codes,
                selected_subjects,
                True #include_modifiers
                ))

    
    


