"""
module for testing export_observation.py
"""

import export_observation

import os
import sys
import project_functions
from config import *


def test_export_events_1():



    assert out ==  REF


def test_eval(test_name, file_name):
    result = subprocess.getoutput("diff tests/new/{0} tests/ref/{0}".format(file_name))
    if result:
        print(result)
        print("{} failed".format(test_name))
        sys.exit(1)
    print("{} passed".format(test_name))
    
os.system("rm tests/new/*")

import subprocess
_, _, pj, _ = project_functions.open_project_json("test.boris")


parameters = {"selected subjects": ["subject1", "subject2"],
              "selected behaviors": ["p", "s"]}
obsId = "observation #1"

# test #1
test_name, file_name,output_format  = "test #1 TSV", "test1_export.tsv", "tsv"
r, msg = export_observation.export_events(parameters, obsId, pj[OBSERVATIONS][obsId], pj[ETHOGRAM], "tests/new/" + file_name, output_format)
if not r:
    print(msg)
    print("test {} failed".format(test_name))
    sys.exit(1)

test_eval(test_name, file_name)

# test #2
test_name, file_name,output_format  = "test #1 CSV", "test1_export.csv", "csv"
r, msg = export_observation.export_events(parameters, obsId, pj[OBSERVATIONS][obsId], pj[ETHOGRAM], "tests/new/" + file_name, output_format)
if not r:
    print(msg)
    print("test {} failed".format(test_name))
    sys.exit(1)
test_eval(test_name, file_name)

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

# test #6
test_name, file_name,output_format  = "test #1 HTML", "test1_export.html", "html"
r, msg = export_observation.export_events(parameters, obsId, pj[OBSERVATIONS][obsId], pj[ETHOGRAM], "tests/new/" + file_name, output_format)
if not r:
    print(msg)
    print("test {} failed".format(test_name))
    sys.exit(1)
test_eval(test_name, file_name)
