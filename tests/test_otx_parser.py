"""
module for testing otx_parser.py

https://realpython.com/python-continuous-integration/

pytest -s -vv test_otx_parser.py
"""

import os
import pytest
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from boris import otx_parser

@pytest.fixture()
def before():
    os.system("rm -rf output")
    os.system("mkdir output")

class Test_otx_to_boris(object):

    def test_otx(self):
        boris_project = otx_parser.otx_to_boris("files/otx_parser_test.otx")
        pj = json.loads(open("files/otx_import_test.boris").read())
        assert boris_project == pj

        #with open("1", "w") as f:
        #    f.write(json.dumps(boris_project))


    def test_otb(self):
        boris_project = otx_parser.otx_to_boris("files/otx_parser_test.otb")
        pj = json.loads(open("files/otx_import_test.boris").read())
        assert boris_project == pj
        '''
        with open("1", "w") as f:
            f.write(json.dumps(boris_project))

        '''

