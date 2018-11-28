"""
module for testing export_observation.py
"""
import pytest
import sys
import json
import os
from openpyxl import load_workbook

sys.path.append("..")

import export_observation
from config import *

#os.system("rm -rf output")
#os.system("mkdir output")

@pytest.fixture()
def before():
    print('\nbefore each test')
    os.system("rm -rf output")
    os.system("mkdir output")


class Test_export_events(object):

    @pytest.mark.usefixtures("before")
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


    @pytest.mark.usefixtures("before")
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

    @pytest.mark.usefixtures("before")
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

    @pytest.mark.usefixtures("before")
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

        assert ref_all_cells == test_all_cells



class Test_export_events_jwatcher(object):

    @pytest.mark.usefixtures("before")
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



class Test_events_to_behavioral_sequences(object):

    def test_1(self):

        pj = json.loads(open("files/test.boris").read())

        obs_id = "observation #1"
        subject = "subject1"
        parameters = {"selected subjects": ["subject1"],
                      "selected behaviors": ["p", "s"],
                      INCLUDE_MODIFIERS: False,
                      EXCLUDE_BEHAVIORS: False,
                      "start time": 0,
                      "end time": 100.0}

        behav_seq_separator = "|"

        out = export_observation.events_to_behavioral_sequences(pj,
                                                                obs_id,
                                                                subject,
                                                                parameters,
                                                                behav_seq_separator)

        assert open("files/Test_events_to_behavioral_sequences_test_1").read() == out



    def test_2_separator_changed(self):

        pj = json.loads(open("files/test.boris").read())

        obs_id = "observation #1"
        subject = "subject1"
        parameters = {"selected subjects": ["subject1"],
                      "selected behaviors": ["p", "s"],
                      INCLUDE_MODIFIERS: False,
                      EXCLUDE_BEHAVIORS: False,
                      "start time": 0,
                      "end time": 100.0}

        behav_seq_separator = "£"

        out = export_observation.events_to_behavioral_sequences(pj,
                                                                obs_id,
                                                                subject,
                                                                parameters,
                                                                behav_seq_separator)

        assert open("files/Test_events_to_behavioral_sequences_test_2_separator").read() == out


    def test_3_no_behavior_found_for_selected_subject(self):

        pj = json.loads(open("files/test.boris").read())

        obs_id = "observation #1"
        subject = "subject1"
        parameters = {"selected subjects": ["subject2"],
                      "selected behaviors": ["p"],
                      INCLUDE_MODIFIERS: False,
                      EXCLUDE_BEHAVIORS: False,
                      "start time": 0,
                      "end time": 100.0}

        behav_seq_separator = "|"

        out = export_observation.events_to_behavioral_sequences(pj,
                                                                obs_id,
                                                                subject,
                                                                parameters,
                                                                behav_seq_separator)

        # open("1", "w").write(out)
        assert out == ""


    def test_4_behaviors_with_modifiers(self):

        pj = json.loads(open("files/test.boris").read())

        obs_id = "modifiers"
        subject = ""
        parameters = {"selected subjects": [""],
                      "selected behaviors": ["q", "r"],
                      INCLUDE_MODIFIERS: True,
                      EXCLUDE_BEHAVIORS: False,
                      "start time": 0,
                      "end time": 100.0}

        behav_seq_separator = "|"

        out = export_observation.events_to_behavioral_sequences(pj,
                                                                obs_id,
                                                                subject,
                                                                parameters,
                                                                behav_seq_separator)

        assert open("files/Test_events_to_behavioral_sequences_test_4_behaviors_with_modifiers").read() == out




    def test_5_observation_not_paired(self):

        pj = json.loads(open("files/test.boris").read())

        obs_id = "live not paired"
        subject = ""
        parameters = {"selected subjects": [""],
                      "selected behaviors": ["p", "s"],
                      INCLUDE_MODIFIERS: False,
                      EXCLUDE_BEHAVIORS: False,
                      "start time": 0,
                      "end time": 100.0}

        behav_seq_separator = "|"

        out = export_observation.events_to_behavioral_sequences(pj,
                                                                obs_id,
                                                                subject,
                                                                parameters,
                                                                behav_seq_separator)

        # open("1", "w").write(out)
        assert open("files/Test_events_to_behavioral_sequences_test_5_observation_not_paired").read() == out




'''

open("1", "w").write(out)

a= Test_export_events()
a.test_export_tabular_xlsx()
'''

