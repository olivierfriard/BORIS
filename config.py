#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2015 Olivier Friard

This file is part of BORIS.

  BORIS is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 3 of the License, or
  any later version.

  BORIS is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not see <http://www.gnu.org/licenses/>.

"""


programName = 'BORIS'

project_format_version = '1.6'

VLC_MIN_VERSION = '2'

CHECK_NEW_VERSION_DELAY = 15*24*60*60

#FFMPEG_BIN = 'ffmpeg'

function_keys = {16777264: 'F1',16777265: 'F2',16777266: 'F3',16777267: 'F4',16777268: 'F5', 16777269: 'F6', 16777270: 'F7', 16777271: 'F8', 16777272: 'F9', 16777273: 'F10',16777274: 'F11', 16777275: 'F12'}


subtitlesColors = ['cyan','red','blue','yellow','fuchsia','orange', 'lime']

OBSERVATIONS = 'observations'
EVENTS = 'events'
TIME_OFFSET='time offset'
TIME_OFFSET_SECOND_PLAYER='time offset second player'

CODING_MAP = 'coding_map'
SUBJECTS = 'subjects_conf'
ETHOGRAM = 'behaviors_conf'

subjects_config = ['key', 'id']

subjectsFields = ['key', 'name', 'description']

UNPAIRED = 'UNPAIRED'

YES = 'Yes'
NO = 'No'
CANCEL = 'Cancel'

NO_FOCAL_SUBJECT = 'No focal subject'

TYPE = "type"
FILE = "file"

# fields for event configuration
#fields = {'type': 0, 'key': 1, 'code': 2, 'description': 3, 'modifiers': 4, 'excluded': 5}
fields = {'type': 0, 'key': 1, 'code': 2, 'description': 3, 'modifiers': 4, 'excluded': 5, 'coding map': 6}
# fields in behaviours table from project window
behavioursFields = {'type': 0, 'key': 1, 'code': 2, 'description': 3, 'modifiers': 4, 'excluded': 5, 'coding map': 6}

observation_types = ['Point event', 'State event', 'Point event with coding map', 'State event with coding map']

# fields from observation (list for order)
tw_events_fields = ['time', 'subject', 'code', 'type', 'modifier', 'comment']
pj_events_fields = ['time', 'subject', 'code', 'modifier', 'comment']

tw_indVarFields = ['label','description', 'type', 'default value']

# create dictionaries
tw_obs_fields, pj_obs_fields = {}, {}

for idx, field in enumerate(tw_events_fields):
    tw_obs_fields[ field ] = idx


for idx, field in enumerate(pj_events_fields):
    pj_obs_fields[ field ] = idx


EVENT_TIME_FIELD_IDX = 0

SUBJECT_EVENT_FIELD = 1       # to be removed after check
EVENT_SUBJECT_FIELD_IDX = 1

BEHAVIOR_EVENT_FIELD = 2
EVENT_BEHAVIOR_FIELD_IDX = 2

EVENT_MODIFIER_FIELD_IDX = 3

COMMENT_EVENT_FIELD = 4

LIVE = 'LIVE'
MEDIA = 'MEDIA'

HHMMSS = 'hh:mm:ss'
HHMMSSZZZ = "hh:mm:ss.zzz"
S = 's'

NEW = 'new'
LIST = 'list'
EDIT = 'edit'
OPEN = 'open'
SELECT = 'select'
SINGLE = 'single'
MULTIPLE = 'multiple'

SELECT1 = 'select1'

NUMERIC = 'numeric'
TEXT = 'text'
INDEPENDENT_VARIABLES = 'independent_variables'
OBSERVATIONS = 'observations'

CLOSE_BEHAVIORS_BETWEEN_VIDEOS = "close_behaviors_between_videos"

OPENCV = 'opencv'
VLC = 'vlc'
FFMPEG = 'ffmpeg'

MEDIA_FILE_INFO = 'media_file_info'

STATE = 'STATE'
POINT = 'POINT'

PLAYER1 = '1'
PLAYER2 = '2'

VIDEO_TAB = 0
FRAME_TAB = 1

slider_maximum = 1000


