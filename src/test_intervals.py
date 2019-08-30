import project_functions
from config import *

file_name = '/home/olivier/gdrive/src/python/pyobserver/boris_projects/testing/test2_v7.boris'

project_path, project_changed, pj, msg = project_functions.open_project_json(file_name)


print(pj[OBSERVATIONS].keys())

selected_observations = ['0588', '1000', '0160', '0259', '0447', '0860', '1342']

for obs_id in selected_observations:
