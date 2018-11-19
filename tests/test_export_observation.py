"""
module for testing export_observation.py
"""

import sys
import json
import os
sys.path.append("..")

import export_observation
from config import *

os.system("rm -rf output")
os.system("mkdir output")

class Test_export_events(object):
    def test_export_tabular_tsv(self):
    
        pj = json.loads(open("files/test.boris").read())
        obs_id = "observation #1"
        parameters = {"selected subjects": ["subject1", "subject2"],
                      "selected behaviors": ["p", "s"]}
        file_name = "test_export_events_tabular.tsv"
        output_format  = "tsv"

        r, msg = export_observation.export_events(parameters, obs_id, pj[OBSERVATIONS][obs_id], pj[ETHOGRAM], "output/" + file_name, output_format)
        assert open("files/test_export_events_tabular.tsv").read() == open("output/test_export_events_tabular.tsv").read()


    def test_export_tabular_csv(self):
    
        pj = json.loads(open("files/test.boris").read())
        obs_id = "observation #1"
        parameters = {"selected subjects": ["subject1", "subject2"],
                      "selected behaviors": ["p", "s"]}
        file_name = "test_export_events_tabular.csv"
        output_format  = "csv"

        r, msg = export_observation.export_events(parameters, obs_id, pj[OBSERVATIONS][obs_id], pj[ETHOGRAM], "output/" + file_name, output_format)
        assert open("files/test_export_events_tabular.csv").read() == open("output/test_export_events_tabular.csv").read()


    def test_export_tabular_html(self):
    
        pj = json.loads(open("files/test.boris").read())
        obs_id = "observation #1"
        parameters = {"selected subjects": ["subject1", "subject2"],
                      "selected behaviors": ["p", "s"]}
        file_name = "test_export_events_tabular.html"
        output_format  = "html"

        r, msg = export_observation.export_events(parameters, obs_id, pj[OBSERVATIONS][obs_id], pj[ETHOGRAM], "output/" + file_name, output_format)
        assert open("files/test_export_events_tabular.html").read() == open("output/test_export_events_tabular.html").read()



'''

# test #3
test_name, file_name, output_format  = "test #1 XLSX", "test1_export.xlsx", "xlsx"
r, msg = export_observation.export_events(parameters, obsId, pj[OBSERVATIONS][obsId], pj[ETHOGRAM], "tests/new/" + file_name, output_format)
if not r:
    print(msg)
    print("test {} failed".format(test_name))
    sys.exit(1)
#test_eval(test_name, file_name, r, msg)

# test #4
test_name, file_name,output_format  = "test #1 XLS", "test1_export.xls", "xls"
r, msg = export_observation.export_events(parameters, obsId, pj[OBSERVATIONS][obsId], pj[ETHOGRAM], "tests/new/" + file_name, output_format)
if not r:
    print(msg)
    print("test {} failed".format(test_name))
    sys.exit(1)
#test_eval(test_name, file_name, r, msg)


# test #5
test_name, file_name,output_format  = "test #1 ODS", "test1_export.ods", "ods"
r, msg = export_observation.export_events(parameters, obsId, pj[OBSERVATIONS][obsId], pj[ETHOGRAM], "tests/new/" + file_name, output_format)
if not r:
    print(msg)
    print("test {} failed".format(test_name))
    sys.exit(1)
#test_eval(test_name, file_name, r, msg)


'''
