#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2016 Olivier Friard

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


OBSERVATIONS = 'observations'
EVENTS = 'events'
TIME_OFFSET='time offset'
TIME_OFFSET_SECOND_PLAYER='time offset second player'

CODING_MAP = 'coding_map'
SUBJECTS = 'subjects_conf'
ETHOGRAM = 'behaviors_conf'
BEHAVIORAL_CATEGORIES = "behavioral_categories"

subjects_config = ['key', 'id']

subjectsFields = ['key', 'name', 'description']

UNPAIRED = 'UNPAIRED'

YES = "Yes"
NO = "No"
CANCEL = "Cancel"
REMOVE = "Remove"
SAVE = "Save"
DISCARD = "Discard"

NO_FOCAL_SUBJECT = 'No focal subject'

TYPE = "type"
FILE = "file"

BEHAVIOR_CODE = "code"

# fields for event configuration
fields = {'type': 0, 'key': 1, 'code': 2, 'description': 3, 'modifiers': 4, 'excluded': 5, 'coding map': 6}

# fields in ethogram table from project window
# behavioursFields = {'type': 0, 'key': 1, 'code': 2, 'description': 3, 'modifiers': 4, 'excluded': 5, 'coding map': 6}
behavioursFields = {'type': 0, 'key': 1, 'code': 2, 'description': 3, 'category': 4, 'modifiers': 5, 'excluded': 6, 'coding map': 7}

#observation_types = ['Point event', 'State event', 'Point event with coding map', 'State event with coding map']  # to be removed

BEHAVIOR_TYPES = ["Point event", "State event", "Point event with coding map", "State event with coding map"]

# fields for events table
tw_events_fields = ['time', 'subject', 'code', 'type', 'modifier', 'comment']

# fields for project events list
pj_events_fields = ["time", "subject", "code", "modifier", "comment"]

tw_indVarFields = ["label", "description", "type", "default value", "possible values"]

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

EVENT_COMMENT_FIELD_IDX = 4

LIVE = 'LIVE'
MEDIA = 'MEDIA'
VIEWER = 'VIEWER'

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

FILTERED_BEHAVIORS = "filtered behaviors"

NUMERIC = "numeric"
NUMERIC_idx = 0
TEXT = "text"
TEXT_idx = 1
SET_OF_VALUES = "value from set"
SET_OF_VALUES_idx = 2

INDEPENDENT_VARIABLES = 'independent_variables'
OBSERVATIONS = 'observations'

CLOSE_BEHAVIORS_BETWEEN_VIDEOS = "close_behaviors_between_videos"

OPENCV = 'opencv'
VLC = 'vlc'
FFMPEG = 'ffmpeg'

MEDIA_FILE_INFO = 'media_file_info'

STATE = 'STATE'
POINT = 'POINT'

START = "START"
STOP = "STOP"

PLAYER1 = '1'
PLAYER2 = '2'

VIDEO_TAB = 0
FRAME_TAB = 1

slider_maximum = 1000



#colors
subtitlesColors = ['cyan','red','blue','yellow','fuchsia','orange', 'lime', 'green']
CATEGORY_COLORS_LIST = ["#FF96CC", "#96FF9C","#CCFFFE", "#EEFF70", "#FF4F64", "#F8BF15", "#3DC7AD"]

# see matplotlib.colors.cnames.keys()
BEHAVIORS_PLOT_COLORS = ["blue", "green", "red", "cyan", "magenta","yellow", "lime",
                         "darksalmon", "purple", "orange", "maroon", "silver",
                         "slateblue", "hotpink", "steelblue", "darkgoldenrod",
'aliceblue',
'antiquewhite',
'aqua',
'aquamarine',
'azure',
'beige',
'bisque',
'black',
'blanchedalmond',
'blueviolet',
'brown',
'burlywood',
'cadetblue',
'chartreuse',
'chocolate',
'coral',
'cornflowerblue',
'cornsilk',
'crimson',
'darkblue',
'darkcyan',
'darkgray',
'darkgreen',
'darkgrey',
'darkkhaki',
'darkmagenta',
'darkolivegreen',
'darkorange',
'darkorchid',
'darkred',
'darksage',
'darkseagreen',
'darkslateblue',
'darkslategray',
'darkslategrey',
'darkturquoise',
'darkviolet',
'deeppink',
'deepskyblue',
'dimgray',
'dimgrey',
'dodgerblue',
'firebrick',
'floralwhite',
'forestgreen',
'fuchsia',
'gainsboro',
'ghostwhite',
'gold',
'goldenrod',
'gray',
'greenyellow',
'grey',
'honeydew',
'indianred',
'indigo',
'ivory',
'khaki',
'lavender',
'lavenderblush',
'lawngreen',
'lemonchiffon',
'lightblue',
'lightcoral',
'lightcyan',
'lightgoldenrodyellow',
'lightgray',
'lightgreen',
'lightgrey',
'lightpink',
'lightsage',
'lightsalmon',
'lightseagreen',
'lightskyblue',
'lightslategray',
'lightslategrey',
'lightsteelblue',
'lightyellow',
'limegreen',
'linen',
'mediumaquamarine',
'mediumblue',
'mediumorchid',
'mediumpurple',
'mediumseagreen',
'mediumslateblue',
'mediumspringgreen',
'mediumturquoise',
'mediumvioletred',
'midnightblue',
'mintcream',
'mistyrose',
'moccasin',
'navajowhite',
'navy',
'oldlace',
'olive',
'olivedrab',
'orangered',
'orchid',
'palegoldenrod',
'palegreen',
'paleturquoise',
'palevioletred',
'papayawhip',
'peachpuff',
'peru',
'pink',
'plum',
'powderblue',
'rosybrown',
'royalblue',
'saddlebrown',
'sage',
'salmon',
'sandybrown',
'seagreen',
'seashell',
'sienna',
'skyblue',
'slategray',
'slategrey',
'snow',
'springgreen',
'tan',
'teal',
'thistle',
'tomato',
'turquoise',
'violet',
'wheat',
'white',
'whitesmoke',
'yellowgreen']
