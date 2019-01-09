"""
module for testing project_functions.py


pytest -s -vv test_project_functions.py
"""

import os
import sys
import json
from decimal import Decimal

sys.path.append("../src")

import project_functions
from config import *


class Test_remove_media_files_path(object):

    def test_1(self):
        """
        test the deletion of the media files path in project
        """

        pj = json.loads(open("files/test.boris").read())
        pj_wo_media_files_paths = project_functions.remove_media_files_path(pj)

        assert pj_wo_media_files_paths == json.loads(open("files/test_without_media_files_paths.boris").read())


class Test_media_full_path(object):

    def test_file_and_dir(self):
        assert project_functions.media_full_path("geese1.mp4", os.getcwd() + "/files/test.boris") == os.getcwd() + "/files/geese1.mp4"

    def test_file_not_found(self):
        assert project_functions.media_full_path("geese1.xxx", os.getcwd() + "/files/test.boris") == ""


    def test_project_file_not_found(self):
        assert project_functions.media_full_path("geese1.xxx", os.getcwd() + "/files/test.xxx.boris") == ""
'''

def test_observation_total_length1():
    out = project_functions.observation_total_length(pj[OBSERVATIONS]["live"])
    assert out == Decimal("26.63")
    return out

def test_observation_total_length2():
    out = project_functions.observation_total_length(pj[OBSERVATIONS]["observation #1"])
    assert out == Decimal("225.6399999999999863575794734")
    return out


for f in [test_remove_media_files_path,
          test_media_full_path1,
          test_observation_total_length1,
          test_observation_total_length2,
          ]:
    print(f)
    print(f())
    print("=====================================")

'''
