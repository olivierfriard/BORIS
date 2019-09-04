"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2019 Olivier Friard

module for testing instantaneous_sampling.py

pytest -vv instantaneous_sampling.py
"""

import os
import sys
import json


sys.path.append("../src")
import config
import instantaneous_sampling


class Test_1(object):

    def test_1(self):

        pj = json.loads(open("files/test.boris").read())

        parameters = {config.SELECTED_SUBJECTS: ["subject1", "subject2"],
                      config.SELECTED_BEHAVIORS: ["s"],
                      config.INCLUDE_MODIFIERS: False,
                      config.EXCLUDE_BEHAVIORS: False,
                      "start time": 0,
                      "end time": 100.0}

        results = instantaneous_sampling.instantaneous_sampling(pj,
                                                      ["live"],
                                                      parameters,
                                                      time_interval=1)


        print(results["live"]["subject1"].export("tsv"), file=open("output/instant_sampling_test_1", "w"))

        assert open("output/instant_sampling_test_1").read() == open("files/instant_sampling_test_1").read()


    def test_2(self):

        pj = json.loads(open("files/test.boris").read())

        parameters = {config.SELECTED_SUBJECTS: ["subject1", "subject2"],
                      config.SELECTED_BEHAVIORS: ["s"],
                      config.INCLUDE_MODIFIERS: False,
                      config.EXCLUDE_BEHAVIORS: False,
                      "start time": 0,
                      "end time": 100.0}

        results = instantaneous_sampling.instantaneous_sampling(pj,
                                                      ["live"],
                                                      parameters,
                                                      time_interval=1)


        print(results["live"]["subject2"].export("tsv"), file=open("output/instant_sampling_test_2", "w"))

        assert open("output/instant_sampling_test_2").read() == open("files/instant_sampling_test_2").read()



