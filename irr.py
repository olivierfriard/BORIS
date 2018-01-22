from decimal import Decimal
import logging
import utilities
import numpy as np
from config import *


def cohen_kappa(obsid1, obsid2,
                events1, events2,
                interval, last_event,
                state_behaviors_codes,
                all_subjects, subjects_to_analyze, selected_subjects):
    """
    
    Args:
        events1 (list): events of obs #1 
        events2 (list): events of obs #2 
        last_event (Decimal): last event of 2 observations
        state_behaviors_codes (list): list of behavior codes defined as state event
        all_subjects (list):
        selected_subjects (list):
    
    Return:
         str: result of analysis
    """
    
    total_states = []

    currentTime = Decimal("0")
    while currentTime <= last_event:

        for idx in all_subjects:
            if all_subjects[idx]["name"] not in selected_subjects:
                continue

            logging.debug("subject: {}".format(all_subjects[idx]["name"]))

            current_states1 = utilities.get_current_states_by_subject(state_behaviors_codes,
                                                                      events1,
                                                                      subjects_to_analyze,
                                                                      currentTime)

            logging.debug("current_state1: {}".format(current_states1))

            if idx in current_states1:

                s1 = all_subjects[idx]["name"] + ":" + ("+".join(sorted(current_states1[idx])))

                if s1 not in total_states:
                    total_states.append(s1)

            current_states2 = utilities.get_current_states_by_subject(state_behaviors_codes,
                                                                      events2,
                                                                      subjects_to_analyze,
                                                                      currentTime)

            if idx in current_states2:

                s2 = all_subjects[idx]["name"] + ":" + ("+".join(sorted(current_states2[idx])))

                if s2 not in total_states:
                    total_states.append(s2)

        currentTime += interval

    total_states = sorted(total_states)
    
    logging.debug("total_states: {}".format(total_states))

    contingency_table = np.zeros((len(total_states), len(total_states)))

    tot1 = []
    tot2 = []
    currentTime = Decimal("0")
    while currentTime < last_event:

        for idx in all_subjects:
            if all_subjects[idx]["name"] not in selected_subjects:
                continue

            current_states1 = utilities.get_current_states_by_subject(state_behaviors_codes,
                                                                 events1,
                                                                 subjects_to_analyze,
                                                                 currentTime)

            if idx in current_states1:

                s1 = all_subjects[idx]["name"] + ":" + ("+".join(sorted(current_states1[idx])))

            current_states2 = utilities.get_current_states_by_subject(state_behaviors_codes,
                                                                 events2,
                                                                 subjects_to_analyze,
                                                                 currentTime)

            if idx in current_states2:

                s2 = all_subjects[idx]["name"] + ":" + ("+".join(sorted(current_states2[idx])))

            if idx in current_states1 and idx in current_states2:
                contingency_table[total_states.index(s1), total_states.index(s2)] += 1
                
            tot1.append(s1)
            tot2.append(s2)

        currentTime += interval

    print(tot1)
    print(tot2)

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

    print("overall_total", overall_total)
    agreements = sum(contingency_table.diagonal())
    print("agreements", agreements)

    sum_ef = 0
    for idx in range(len(total_states)):
        sum_ef += rows_sums[idx] * cols_sums[idx] / overall_total

    logging.debug("sum_ef {}".format(sum_ef))

    K = (agreements - sum_ef) / (overall_total - sum_ef)

    out += "K: <b>{:.3f}</b><br>".format(K)
    
    return out
