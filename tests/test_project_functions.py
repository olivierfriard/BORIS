"""
module for testing project_functions.py
"""

import project_functions
from config import *
from decimal import Decimal

_, _, pj, _ = project_functions.open_project_json("test.boris")




def test_remove_media_files_path():
    global pj
    pj_out = project_functions.remove_media_files_path(pj)


    true = True
    false = False

    REF = {'time_format': 'hh:mm:ss', 'project_name': 'test', 'project_date': '2016-11-27T01:55:22', 'subjects_conf': {'0': {'key': '1', 'name': 'subject1', 'description': 'Description subject #1'}, '1': {'key': '2', 'name': 'subject2', 'description': 'Description subject #2'}}, 'behavioral_categories': [], 'coding_map': {}, 'observations': {'offset positif': {'date': '2016-12-10T15:44:57', 'file': {'1': ['50FPS.mp4'], '2': ['50FPS.mp4']}, 'type': 'MEDIA', 'time offset second player': 20.0, 'visualize_spectrogram': False, 'time offset': Decimal('0.0'), 'independent_variables': {'b': '', 'a': '', 'c': '111'}, 'close_behaviors_between_videos': False, 'events': [[Decimal('22.425'), '', 'p', '', ''], [Decimal('199.96'), '', 'p', '', '']], 'description': '', 'media_info': {'length': {'50FPS.mp4': 180.05}, 'hasAudio': {'video1.avi': True, 'video2.avi': True, '50FPS.mp4': True}, 'hasVideo': {'video1.avi': True, 'video2.avi': True, '50FPS.mp4': True}, 'fps': {'50FPS.mp4': 50.0}}}, 'offset neg': {'close_behaviors_between_videos': False, 'time offset': Decimal('0.0'), 'file': {'1': ['50FPS.mp4'], '2': ['50FPS.mp4']}, 'events': [[Decimal('0.01'), '', 'p', '', ''], [Decimal('2.2'), '', 'p', '', ''], [Decimal('3.5'), '', 'p', '', ''], [Decimal('8.18'), '', 'p', '', '']], 'time offset second player': -20.0, 'visualize_spectrogram': False, 'date': '2016-12-11T00:58:15', 'description': '', 'type': 'MEDIA', 'independent_variables': {'b': '', 'a': '', 'c': '111'}, 'media_info': {'length': {'50FPS.mp4': 180.05}, 'hasAudio': {'50FPS.mp4': True}, 'hasVideo': {'50FPS.mp4': True}, 'fps': {'50FPS.mp4': 50.0}}}, 'observation #1': {'date': '2016-11-27T01:57:26', 'file': {'1': ['video1.avi'], '2': []}, 'type': 'MEDIA', 'time offset second player': 0.0, 'visualize_spectrogram': False, 'time offset': Decimal('0.0'), 'independent_variables': {'a': '12', 'b': 'text value for b', 'c': '111'}, 'close_behaviors_between_videos': False, 'events': [[Decimal('3.3'), 'subject1', 's', '', ''], [Decimal('7.75'), 'subject1', 's', '', ''], [Decimal('9.9'), 'subject1', 's', '', ''], [Decimal('16.2'), 'subject1', 's', '', ''], [Decimal('18.35'), 'subject1', 's', '', ''], [Decimal('24.475'), 'subject1', 's', '', ''], [Decimal('38.425'), 'subject2', 's', '', ''], [Decimal('46.1'), 'subject2', 's', '', '']], 'description': '', 'media_info': {'length': {'video1.avi': 225.64}, 'fps': {'video1.avi': 25.0}, 'hasVideo': {'video1.avi': True, '50FPS.mp4': True}, 'hasAudio': {'video1.avi': True, '50FPS.mp4': True}}}, 'observation #2': {'date': '2016-12-01T23:01:31', 'file': {'1': ['video1.avi', 'video2.avi'], '2': []}, 'type': 'MEDIA', 'time offset second player': 0.0, 'visualize_spectrogram': False, 'time offset': Decimal('0.0'), 'independent_variables': {'a': '123', 'b': 'some text', 'c': '333'}, 'close_behaviors_between_videos': False, 'events': [[Decimal('1.8'), '', 's', '', ''], [Decimal('8.125'), '', 's', '', ''], [Decimal('10.25'), '', 's', '', ''], [Decimal('23.35'), '', 's', '', ''], [Decimal('26.775'), '', 's', '', ''], [Decimal('31.475'), '', 's', '', ''], [Decimal('32.825'), '', 'p', '', ''], [Decimal('34.15'), '', 'p', '', ''], [Decimal('34.925'), '', 'p', '', ''], [Decimal('227.765'), '', 's', '', ''], [Decimal('253.49'), '', 's', '', ''], [Decimal('255.34'), '', 's', '', ''], [Decimal('261.14'), '', 's', '', ''], [Decimal('266.165'), 'subject1', 's', '', ''], [Decimal('276.69'), 'subject1', 's', '', ''], [Decimal('280.965'), 'subject1', 's', '', ''], [Decimal('286.215'), 'subject2', 's', '', ''], [Decimal('292.065'), 'subject2', 's', '', ''], [Decimal('294.215'), 'subject1', 's', '', ''], [Decimal('299.715'), '', 'p', '', ''], [Decimal('301.34'), '', 'p', '', ''], [Decimal('303.24'), '', 'p', '', ''], [Decimal('303.79'), '', 's', '', ''], [Decimal('307.765'), '', 's', '', ''], [Decimal('314.49'), 'subject2', 'p', '', ''], [Decimal('316.065'), 'subject2', 'p', '', ''], [Decimal('317.39'), 'subject2', 's', '', ''], [Decimal('320.365'), 'subject2', 's', '', '']], 'description': 'Description of observation #2', 'media_info': {'length': {'video1.avi': 225.64, 'video2.avi': 300.0}, 'fps': {'video1.avi': 25.0, 'video2.avi': 25.0}, 'hasVideo': {'video1.avi': True, 'video2.avi': True}, 'hasAudio': {'video1.avi': True, 'video2.avi': True}}}, 'live not paired': {'file': [], 'type': 'LIVE', 'date': '2018-02-20T15:34:38', 'description': '', 'time offset': Decimal('0.0'), 'events': [[Decimal('2.048'), '', 'p', '', ''], [Decimal('2.718'), '', 's', '', ''], [Decimal('5.439'), '', 'p', '', ''], [Decimal('9.071'), '', 'p', '', ''], [Decimal('10.478'), '', 's', '', ''], [Decimal('12.223'), '', 'p', '', ''], [Decimal('12.926'), '', 's', '', ''], [Decimal('15.136'), '', 'p', '', ''], [Decimal('17.47'), '', 's', '', ''], [Decimal('19.502'), '', 's', '', ''], [Decimal('24.318'), '', 's', '', ''], [Decimal('26.862'), '', 's', '', '']], 'independent_variables': {'a': '', 'b': '', 'c': '111'}, 'time offset second player': 0.0, 'visualize_spectrogram': False, 'close_behaviors_between_videos': False, 'scan_sampling_time': 0}, 'live': {'file': [], 'type': 'LIVE', 'date': '2018-02-27T15:39:40', 'description': '', 'time offset': Decimal('0.0'), 'events': [[Decimal('1.75'), '', 'p', '', ''], [Decimal('3.75'), '', 'p', '', ''], [Decimal('5.43'), '', 'p', '', ''], [Decimal('5.622'), '', 'p', '', ''], [Decimal('5.814'), '', 'p', '', ''], [Decimal('8.886'), '', 's', '', ''], [Decimal('12.509'), 'subject2', 's', '', ''], [Decimal('14.038'), '', 'p', '', ''], [Decimal('16.678'), '', 's', '', ''], [Decimal('18.438'), '', 's', '', ''], [Decimal('20.685'), 'subject2', 's', '', ''], [Decimal('26.63'), '', 's', '', '']], 'independent_variables': {'a': '', 'b': '', 'c': '111'}, 'time offset second player': 0.0, 'visualize_spectrogram': False, 'close_behaviors_between_videos': False, 'scan_sampling_time': 0}, 'modifiers': {'file': {'1': ['video1.avi'], '2': []}, 'type': 'MEDIA', 'date': '2018-02-28T15:25:10', 'description': '', 'time offset': Decimal('0.0'), 'events': [[Decimal('8.475'), '', 'q', 'm1', ''], [Decimal('12.35'), '', 'q', 'm2', ''], [Decimal('15.65'), '', 'q', 'm3', ''], [Decimal('19.175'), '', 'r', 'm1', ''], [Decimal('27.95'), '', 'r', 'm1', ''], [Decimal('30.425'), '', 'r', 'None', ''], [Decimal('40.825'), '', 'r', 'None', '']], 'independent_variables': {'a': '', 'b': '', 'c': '111'}, 'time offset second player': 0.0, 'visualize_spectrogram': False, 'close_behaviors_between_videos': False, 'media_info': {'length': {'video1.avi': 225.64}, 'fps': {'video1.avi': 25.0}, 'hasVideo': {'video1.avi': True}, 'hasAudio': {'video1.avi': True}}}}, 'independent_variables': {'0': {'label': 'a', 'description': 'aaaaa', 'type': 'numeric', 'default value': '', 'possible values': ''}, '1': {'label': 'b', 'description': 'bbbbb', 'type': 'text', 'default value': '', 'possible values': ''}, '2': {'label': 'c', 'description': 'cccccc', 'type': 'value from set', 'default value': '', 'possible values': '111,222,333'}}, 'behaviors_conf': {'0': {'type': 'Point event', 'key': 'P', 'code': 'p', 'description': 'Test point event', 'category': '', 'modifiers': {}, 'excluded': '', 'coding map': ''}, '1': {'type': 'State event', 'key': 'S', 'code': 's', 'description': 'Test state event', 'category': '', 'modifiers': {}, 'excluded': '', 'coding map': ''}, '2': {'type': 'Point event', 'key': 'Q', 'code': 'q', 'description': 'point event with 1 set of modifiers', 'category': '', 'modifiers': {'0': {'name': 'modif #1', 'type': 0, 'values': ['m1', 'm2', 'm3']}}, 'excluded': '', 'coding map': ''}, '3': {'type': 'State event', 'key': 'R', 'code': 'r', 'description': 'state event with 1 set of modifiers', 'category': '', 'modifiers': {'0': {'name': 'modif #1', 'type': 0, 'values': ['m1', 'm2', 'm3']}}, 'excluded': '', 'coding map': ''}}, 'project_format_version': '4.0', 'project_description': '', 'converters': {}}
    
    assert pj_out ==  REF
    return pj_out


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
