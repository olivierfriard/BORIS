

import intervals as I
import project_functions
from config import *
import db_functions
import pandas as pd

file_name = '/home/olivier/gdrive/src/python/pyobserver/boris_projects/testing/test2_v7.boris'

project_path, project_changed, pj, msg = project_functions.open_project_json(file_name)


# print(pj[OBSERVATIONS].keys())

selected_observations = ['0588', '1000', '0160', '0259', '0447', '0860', '1342']

selected_observations = list(pj[OBSERVATIONS].keys())

selected_subjects = [pj[SUBJECTS][x]["name"] for x in pj[SUBJECTS]]
print(selected_subjects)

selected_behaviors = [pj[ETHOGRAM][x]["code"] for x in pj[ETHOGRAM]]

print(selected_behaviors)

def sql():
    cursor = db_functions.load_aggregated_events_in_db(pj,
                                           selected_subjects,
                                           selected_observations,
                                           selected_behaviors)
    return cursor


def pand():
    df = pd.DataFrame( columns=["obs", "subject", "behav", "occurence"])

    for obs_id in selected_observations:  # pj[OBSERVATIONS]:
        for event in pj[OBSERVATIONS][obs_id][EVENTS]:
            # print([obs_id, event[1], event[2], event[0]])
            df.loc[len(df)] = [obs_id, event[1], event[2], event[0]]
    return df


_, _, db = sql()
cursor = db.cursor()
cursor.execute("SELECT COUNT(*) FROM aggregated_events ")
for row in cursor.fetchall():
    print(row[0])


# print(len(pand()))


'''
for obs_id in selected_observations:
    for subject in selected_subjects:
        for behav in selected_behaviors:
'''
