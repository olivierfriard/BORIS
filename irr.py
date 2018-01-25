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


def cohen_kappa(obsid1, obsid2,
                events1, events2,
                interval,
                state_behaviors_codes,
                point_behaviors_codes,
                selected_subjects,
                include_modifiers):
    """
    
    Args:
        obsid1 (str): id of observation #1
        obsid2 (str): id of observation #2
        events1 (list): events of obs #1 
        events2 (list): events of obs #2 
        state_behaviors_codes (list): list of behavior codes defined as state event
        point_behaviors_codes (list): list of behavior codes defined as point event
        selected_subjects (list): subjects selected for analysis
        include_modifiers (bool): True: include modifiers False: do not
    
    Return:
         str: result of analysis
    """
    
    last_event = max(events1[-1][0], events2[-1][0])
    
    logging.debug("last_event: {}".format(last_event))
    
    total_states = []

    currentTime = Decimal("0")
    while currentTime <= last_event:

        for events in [events1, events2]:

            for subject in selected_subjects:

                if subject == NO_FOCAL_SUBJECT:
                    subject = ""
                #logging.debug("subject: {}".format(subject))

                current_states = utilities.get_current_states_by_subject(state_behaviors_codes,
                                                                          events,
                                                                          {subject: {"name": subject}},
                                                                          currentTime)

                #print(currentTime, "subject", subject, "current_states", current_states)

                s = []
                if include_modifiers:
                    cm = {}
                    for behavior in current_states[subject]:
                        for ev in events:
                            if ev[EVENT_TIME_FIELD_IDX] > currentTime:
                                break
                            if ev[EVENT_SUBJECT_FIELD_IDX] == subject:
                                if ev[EVENT_BEHAVIOR_FIELD_IDX] == behavior:
                                    cm[behavior] = ev[EVENT_MODIFIER_FIELD_IDX]

                    logging.debug("subject: {}  currentTime: {}  cm: {}".format(subject, currentTime, cm))

                    if cm:
                        for behavior in cm:
                            s.append([subject, [[behavior, cm[behavior]]]])
                    else:
                        s.append([subject])
                else:
                    s.append([subject, current_states[subject]]) 

                print(currentTime, "state", s)

                # point events
                current_points = utilities.get_current_points_by_subject(point_behaviors_codes,
                                                                          events,
                                                                          {subject: {"name": subject}},
                                                                          currentTime,
                                                                          Decimal(str(round(interval/2, 3))))


                #print(currentTime, current_points)
                
                if current_points[subject]:
                    if include_modifiers:
                        if s == [['']]:
                            s = [[subject, current_points[subject]]]
                        else:
                            s.append([subject, current_points[subject]]) 
                    else:
                        s.append([subject, current_points[subject]])
    
                print(currentTime, "point", s)

    
                if s not in total_states:
                    total_states.append(s)

        currentTime += interval

    total_states = sorted(total_states)
    
    logging.debug("total_states: {}".format(total_states))
    
    print(total_states)

    contingency_table = np.zeros((len(total_states), len(total_states)))

    '''tot1, tot2 = [], []'''

    currentTime = Decimal("0")
    while currentTime < last_event:

        for subject in selected_subjects:

            if subject == NO_FOCAL_SUBJECT:
                subject = ""


            current_states1 = utilities.get_current_states_by_subject(state_behaviors_codes,
                                                                 events1,
                                                                 {subject: {"name": subject}},
                                                                 currentTime)

            s1 = []
            if include_modifiers:
                cm = {}
                for behavior in current_states1[subject]:
                    for ev in events1:
                        if ev[EVENT_TIME_FIELD_IDX] > currentTime:
                            break
                        if ev[EVENT_SUBJECT_FIELD_IDX] == subject:
                            if ev[EVENT_BEHAVIOR_FIELD_IDX] == behavior:
                                cm[behavior] = ev[EVENT_MODIFIER_FIELD_IDX]
                                
                logging.debug("cm: {}".format(cm))
                if cm:
                    for behavior in cm:
                        s1.append([subject, behavior, cm[behavior]])
                else:
                    s1.append([subject])
            else:
                s1.append([subject, current_states1[subject]]) 

            current_states2 = utilities.get_current_states_by_subject(state_behaviors_codes,
                                                                 events2,
                                                                 {subject: {"name": subject}},
                                                                 currentTime)

            s2 = []
            if include_modifiers:

                cm = {}
                for behavior in current_states2[subject]:
                    for ev in events2:
                        if ev[EVENT_TIME_FIELD_IDX] > currentTime:
                            break
                        if ev[EVENT_SUBJECT_FIELD_IDX] == subject:
                            if ev[EVENT_BEHAVIOR_FIELD_IDX] == behavior:
                                cm[behavior] = ev[EVENT_MODIFIER_FIELD_IDX]
    
                logging.debug("cm: {}".format(cm))
                if cm:
                    for behavior in cm:
                        s2.append([subject, behavior, cm[behavior]])
                else:
                    s2.append([subject])
            else:
                s2.append([subject, current_states2[subject]]) 

            '''if idx in current_states1 and idx in current_states2:'''
            try:
                contingency_table[total_states.index(s1), total_states.index(s2)] += 1
            except:
                return "Error with contingency table"
            '''
            tot1.append(s1)
            tot2.append(s2)
            '''

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
    out += "number of events: <b>{:.0f}</b><br>".format(
            len([event for event in events1
                 if (event[EVENT_SUBJECT_FIELD_IDX] in selected_subjects) or
                    (event[EVENT_SUBJECT_FIELD_IDX] == "" and NO_FOCAL_SUBJECT in selected_subjects)]) / 2)

    #out += "Observation length: <b>{:.3f} s</b><br>".format(self.observationTotalMediaLength(obsid1))
    #out += "Number of intervals: <b>{:.0f}</b><br><br>".format(self.observationTotalMediaLength(obsid1) / interval)

    out += "Observation #2: <b>{}</b><br>".format(obsid2)
    out += "number of events: <b>{:.0f}</b><br>".format(
            len([event for event in events2
                 if (event[EVENT_SUBJECT_FIELD_IDX] in selected_subjects) or
                    (event[EVENT_SUBJECT_FIELD_IDX] == "" and NO_FOCAL_SUBJECT in selected_subjects)]) / 2)

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
    
    
    obsid1, obsid2 = "obs #1", "obs #2"
    
    interval = 1
    
    #state_behaviors_codes = ['s']
    
    selected_subjects = ["No focal subject"]
    
    include_modifiers = True
    
    
 
    
    events1 = [[     Decimal(2.1),     "",     "p",     "",     ""    ],
        [     Decimal(3.743),     "",     "s",     "",     ""    ],
    
            [     Decimal(5.5),     "",     "p",     "",     ""    ],
            [     Decimal(5.6),     "",     "p",     "",     ""    ],
    
        [     Decimal(9.719),     "",     "s",     "",     ""    ],
        
    [     Decimal(10),     "",     "ss",     "x",     ""    ],        
    [     Decimal(11.135),     "",     "s",     "bbb|None",     ""    ],
        [     Decimal(15),     "",     "ss",     "x",     ""    ],        
    [     Decimal(22.87),     "",     "s",     "bbb|None",     ""    ],
    [     Decimal(22.871),     "",     "s",     "None|None",     ""    ],
    [     Decimal(35.759),     "",     "s",     "None|None",     ""    ]
   ]
    
    events2 = [    [    Decimal( 3.743),     "",     "s",     "",     ""    ],
        [     Decimal(9.719),     "",     "s",     "",     ""    ],
    [     Decimal(11.135),     "",     "s",     "aaa|None",     ""    ],
    [     Decimal(22.87),     "",     "s",     "aaa|None",     ""    ],
    [     Decimal(22.871),     "",     "s",     "None|None",     ""    ],
    [     Decimal(35.759),     "",     "s",     "None|None",     ""    ]
   ]
    
    state_behaviors_codes = ['s','ss']
    point_behaviors_codes = ['p']
    
    print(cohen_kappa(obsid1, obsid2,
                events1, events2,
                interval,
                state_behaviors_codes,
                point_behaviors_codes,
                selected_subjects,
                True #include_modifiers
                ))

    
    


