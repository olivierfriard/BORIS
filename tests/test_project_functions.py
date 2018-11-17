"""
module for testing project_functions.py
"""
import sys
import json
from decimal import Decimal

sys.path.append("..")

import project_functions
from config import *




'''_, _, pj, _ = project_functions.open_project_json("files/test.boris")
'''

class Test_remove_media_files_path(object):
    def test_1(self):
    
        pj = json.loads(open("files/test.boris").read())
        pj_wo_media_files_paths = project_functions.remove_media_files_path(pj)
    
        assert pj_wo_media_files_paths == json.loads(open("files/test_without_media_files_paths.boris").read())



"""

def test_media_full_path1():
    out = project_functions.media_full_path("video1.avi", "/home/olivier/projects/BORIS/test.boris")
    assert out == "/home/olivier/projects/BORIS/video1.avi"
    return out

'''
def test_media_full_path2():
    out = project_functions.media_full_path("video.xxx", "/home/olivier/projects/BORIS/test.boris")
    assert out == ""
    return out
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

"""
