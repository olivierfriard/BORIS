"""
module for testing export_observation.py
"""

import sys
import json
import os
from openpyxl import load_workbook

sys.path.append("..")

import export_observation
from config import *

os.system("rm -rf output")
os.system("mkdir output")


class Test_export_events(object):

    '''
    def test_export_tabular_tsv(self):

        pj = json.loads(open("files/test.boris").read())
        obs_id = "observation #1"
        parameters = {"selected subjects": ["subject1", "subject2"],
                      "selected behaviors": ["p", "s"]}
        file_name = "test_export_events_tabular.tsv"
        output_format  = "tsv"

        r, msg = export_observation.export_events(parameters,
                                                  obs_id,
                                                  pj[OBSERVATIONS][obs_id],
                                                  pj[ETHOGRAM],
                                                  "output/" + file_name,
                                                  output_format)

        assert open("files/test_export_events_tabular.tsv").read() == open("output/test_export_events_tabular.tsv").read()


    def test_export_tabular_csv(self):

        pj = json.loads(open("files/test.boris").read())
        obs_id = "observation #1"
        parameters = {"selected subjects": ["subject1", "subject2"],
                      "selected behaviors": ["p", "s"]}
        file_name = "test_export_events_tabular.csv"
        output_format  = "csv"

        r, msg = export_observation.export_events(parameters,
                                                  obs_id,
                                                  pj[OBSERVATIONS][obs_id],
                                                  pj[ETHOGRAM],
                                                  "output/" + file_name, output_format)

        assert open("files/test_export_events_tabular.csv").read() == open("output/test_export_events_tabular.csv").read()


    def test_export_tabular_html(self):

        pj = json.loads(open("files/test.boris").read())
        obs_id = "observation #1"
        parameters = {"selected subjects": ["subject1", "subject2"],
                      "selected behaviors": ["p", "s"]}
        file_name = "test_export_events_tabular.html"
        output_format  = "html"

        r, msg = export_observation.export_events(parameters,
                                                  obs_id,
                                                  pj[OBSERVATIONS][obs_id],
                                                  pj[ETHOGRAM],
                                                  "output/" + file_name,
                                                  output_format)

        assert open("files/test_export_events_tabular.html").read() == open("output/test_export_events_tabular.html").read()
    '''

    def test_export_tabular_xlsx(self):

        pj = json.loads(open("files/test.boris").read())

        obs_id = "observation #1"
        parameters = {"selected subjects": ["subject1", "subject2"],
                      "selected behaviors": ["p", "s"]}
        file_name = "test_export_events_tabular.xlsx"
        output_format  = "xlsx"

        r, msg = export_observation.export_events(parameters,
                                                  obs_id,
                                                  pj[OBSERVATIONS][obs_id],
                                                  pj[ETHOGRAM],
                                                  "output/" + file_name,
                                                  output_format)

        ref_all_cells = []
        wb = load_workbook(filename=f'files/{file_name}', read_only=True)
        for ws_name in wb.sheetnames:
            ref_all_cells.extend([cell.value for row in wb[ws_name].rows for cell in row])

        test_all_cells = []
        wb = load_workbook(filename=f'output/{file_name}', read_only=True)
        for ws_name in wb.sheetnames:
            test_all_cells.extend([cell.value for row in wb[ws_name].rows for cell in row])

        #print(ref_all_cells == test_all_cells)

        assert ref_all_cells == test_all_cells



class Test_export_events_jwatcher(object):

    def test_1(self):

        pj = json.loads(open("files/test.boris").read())

        obs_id = "observation #1"
        parameters = {"selected subjects": ["subject1"],
                      "selected behaviors": ["p", "s"]}
        file_name = "test_jwatcher"
        output_format  = ""

        r, msg = export_observation.export_events_jwatcher(parameters,
                                                           obs_id,
                                                           pj["observations"][obs_id],
                                                           pj[ETHOGRAM],
                                                           "output/" + file_name,
                                                           output_format)

        ref = [x for x in open("files/test_jwatcher_subject1.dat").readlines() if not x.startswith("#")]
        out = [x for x in open("output/test_jwatcher_subject1.dat").readlines() if not x.startswith("#")]
        assert ref == out

        ref = [x for x in open("files/test_jwatcher_subject1.faf").readlines() if not x.startswith("#")]
        out = [x for x in open("output/test_jwatcher_subject1.faf").readlines() if not x.startswith("#")]
        assert ref == out

        ref = [x for x in open("files/test_jwatcher_subject1.fmf").readlines() if not x.startswith("#")]
        out = [x for x in open("output/test_jwatcher_subject1.fmf").readlines() if not x.startswith("#")]
        assert ref == out


'''
a= Test_export_events()
a.test_export_tabular_xlsx()
'''

