"""
module for testing project_functions.py


pytest -s -vv test_project_functions.py
"""

import pytest
import os
import sys
import json
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from boris import project_functions
from boris import config

@pytest.fixture()
def before():
    os.system("rm -rf output")
    os.system("mkdir output")


class Test_behavior_category(object):

    def test_1(self):
        pj = json.loads(open("files/test.boris").read())
        assert project_functions.behavior_category(pj[config.ETHOGRAM]) == {'p': '', 's': '', 'q': '', 'r': '', 'm': ''}


class Test_check_coded_behaviors(object):

    def test_1(self):
        pj = json.loads(open("files/test.boris").read())
        assert project_functions.check_coded_behaviors(pj) == set()


class Test_check_if_media_available(object):

    def test_media_not_available(self):
        pj = json.loads(open("files/test.boris").read())

        assert project_functions.check_if_media_available(pj[config.OBSERVATIONS]["offset positif"],
                                                          'files/test.boris') == (False, 'Media file <b>video_test_25fps_360s.mp4</b> not found')

    def test_live_observation(self):
        pj = json.loads(open("files/test.boris").read())

        assert project_functions.check_if_media_available(pj[config.OBSERVATIONS]["live"],
                                                          'files/test.boris') == (True, "")

    '''
    def test_media_available(self):
        pj = json.loads(open("files/test_without_media_files_paths.boris").read())

        assert project_functions.check_if_media_available(pj[OBSERVATIONS]["geese1"],
                                                          'files/test.boris') == (True, "")
    '''



class Test_check_project_integrity(object):

    def test_observation_not_paired(self):
        """
        one observation not paired
        """
        pj = json.loads(open("files/test.boris").read())

        results = project_functions.check_project_integrity(pj,
                                                            config.HHMMSS,
                                                           'files/test.boris',
                                                            media_file_available=False)

        assert results == '''Observation: <b>live not paired</b><br>The behavior <b>s</b>  is not PAIRED for subject "<b>No focal subject</b>" at <b>00:00:26.862</b><br>'''


    def test_modifiers_with_trailing_spaces(self):
        """
        Project containing some modifiers with trailing spaces
        """

        pj = json.loads(open("files/test_with_leading_trailing_spaces_in_modifiers.boris").read())

        results = project_functions.check_project_integrity(pj,
                                                            config.HHMMSS,
                                                           "files/test_with_leading_trailing_spaces_in_modifiers.boris",
                                                            media_file_available=False)

        #print(results)
        #assert results == '''The following modifier defined in ethogram has leading/trailing spaces: <b>a&#9608;&#9608;&#9608;</b><br><br>The following modifier defined in ethogram has leading/trailing spaces: <b>c&#9608;&#9608;</b><br><br>The following modifier defined in ethogram has leading/trailing spaces: <b>c&#9608;</b><br><br>The following modifier defined in ethogram has leading/trailing spaces: <b>d&#9608;&#9608;</b>'''
        assert results == '''The following <b>modifier</b> defined in ethogram has leading/trailing spaces or special chars: <b>a&#9608;&#9608;&#9608;</b><br><br>The following <b>modifier</b> defined in ethogram has leading/trailing spaces or special chars: <b>c&#9608;&#9608;</b><br><br>The following <b>modifier</b> defined in ethogram has leading/trailing spaces or special chars: <b>c&#9608;</b><br><br>The following <b>modifier</b> defined in ethogram has leading/trailing spaces or special chars: <b>d&#9608;&#9608;</b>'''

class Test_check_state_events_obs(object):

    def test_observation_ok(self):
        pj = json.loads(open("files/test.boris").read())

        results = project_functions.check_state_events_obs("offset positif",
                                                            pj[config.ETHOGRAM],
                                                            pj[config.OBSERVATIONS]["offset positif"],
                                                            config.HHMMSS)
        # print(results)

        assert results == (True, 'No problem detected')


    def test_observation_not_paired(self):
        pj = json.loads(open("files/test.boris").read())

        results = project_functions.check_state_events_obs("live not paired",
                                                            pj[config.ETHOGRAM],
                                                            pj[config.OBSERVATIONS]["live not paired"],
                                                            config.HHMMSS)
        # print(results)

        assert results == (False, 'The behavior <b>s</b>  is not PAIRED for subject "<b>No focal subject</b>" at <b>00:00:26.862</b><br>')


class Test_export_observations_list(object):

    @pytest.mark.usefixtures("before")
    def test1(self):
        pj = json.loads(open("files/test2.boris").read())
        selected_observations = [x for x in pj[config.OBSERVATIONS]]

        result = project_functions.export_observations_list(pj=pj,
                                                            file_name="output/export_observations_list_test1.tsv",
                                                            selected_observations = selected_observations,
                                                            output_format="tsv"
                                                            )
        assert result == True
        assert open("files/export_observations_list_test1.tsv").read() == open("output/export_observations_list_test1.tsv").read()


class Test_media_full_path(object):

    def test_file_and_dir(self):
        assert project_functions.media_full_path("geese1.mp4", os.getcwd() + "/files/test.boris") == os.getcwd() + "/files/geese1.mp4"

    def test_file_not_found(self):
        assert project_functions.media_full_path("geese1.xxx", os.getcwd() + "/files/test.boris") == ""


    def test_project_file_not_found(self):
        assert project_functions.media_full_path("geese1.xxx", os.getcwd() + "/files/test.xxx.boris") == ""



class Test_remove_media_files_path(object):

    def test_1(self):
        """
        test the deletion of the media files path in project
        """

        pj = json.loads(open("files/test2.boris").read())
        pj_wo_media_files_paths = project_functions.remove_media_files_path(pj)

        assert pj_wo_media_files_paths == json.loads(open("files/test_without_media_files_paths.boris").read())







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
