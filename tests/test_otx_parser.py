"""
module for testing otx_parser.py

https://realpython.com/python-continuous-integration/

pytest -s -vv test_otx_parser.py
"""

import os
import pytest
import sys
import json
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from boris import otx_parser
from boris import config


class Test_otx_to_boris(object):
    def assert_project_is_imported(self, project, expected):
        assert project[config.PROJECT_NAME] == expected[config.PROJECT_NAME]
        assert project[config.PROJECT_DATE] == expected[config.PROJECT_DATE]
        assert project[config.BEHAVIORAL_CATEGORIES] == expected[config.BEHAVIORAL_CATEGORIES]
        assert project[config.SUBJECTS] == expected[config.SUBJECTS]
        assert set(project[config.ETHOGRAM]) == set(expected[config.ETHOGRAM])
        assert [behavior[config.BEHAVIOR_CODE] for behavior in project[config.ETHOGRAM].values()] == [
            behavior[config.BEHAVIOR_CODE] for behavior in expected[config.ETHOGRAM].values()
        ]
        assert set(project[config.INDEPENDENT_VARIABLES]) == set(expected[config.INDEPENDENT_VARIABLES])
        assert set(project[config.OBSERVATIONS]) == set(expected[config.OBSERVATIONS])

    def test_otx(self):
        boris_project, errors = otx_parser.otx_to_boris("files/otx_parser_test.otx")
        assert errors == []
        pj = json.loads(Path("files/otx_import_test.boris").read_text())
        self.assert_project_is_imported(boris_project, pj)

        # with open("1", "w") as f:
        #    f.write(json.dumps(boris_project))

    def test_otb(self):
        boris_project, errors = otx_parser.otx_to_boris("files/otx_parser_test.otb")
        assert errors == []
        pj = json.loads(Path("files/otx_import_test.boris").read_text())
        self.assert_project_is_imported(boris_project, pj)
        """
        with open("1", "w") as f:
            f.write(json.dumps(boris_project))

        """
