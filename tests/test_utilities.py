"""
module for testing export_observation.py
"""


import os
import sys
import decimal

sys.path.append("..")
import utilities



'''
def test_angle():
    assert round(utilities.angle((0,0),(0,90),(90,0)),3) == 90.0
    assert round(utilities.angle((0,0),(90,0),(90,0)), 3) == 0.0
'''

class Test_angle(object):
    def test_1(self):
        round(utilities.angle((0,0),(0,90),(90,0)),3) == 90.0

    def test_2(self):
        assert round(utilities.angle((0,0),(90,0),(90,0)), 3) == 0.0
        
    def test_3(self):
        assert round(utilities.angle((0,0),(90,0),(0,90)), 3) == 90.0


class Test_polygon_area(object):
    def test_1(self):
        assert round(utilities.polygon_area([(0,0),(90,0),(0,90)])) == 4050
    def test_2(self):
        assert round(utilities.polygon_area([(0,0),(90,0),(0,90),(90,90)]) ) == 0

class Test_url2path(object):
    def test_1(self):
        assert utilities.url2path("file:///home/olivier/v%C3%A9lo/test") == "/home/olivier/vélo/test"
        
class Test_time2seconds(object):
    def test_1(self):
        assert utilities.time2seconds("11:22:33.44") == decimal.Decimal("40953.44")
    def test_2(self):
        assert utilities.time2seconds("-11:22:33.44") == decimal.Decimal("-40953.44")
    def test_3(self):
        assert utilities.time2seconds("00:00:00.000") == decimal.Decimal("0.000")
