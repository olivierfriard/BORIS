#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2020 Olivier Friard

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

programName: str = "BORIS"

project_format_version = "7.0"

VLC_MIN_VERSION = "2"

CHECK_NEW_VERSION_DELAY = 15 * 24 * 60 * 60

N_PLAYER = 8

NA = "NA"

VLC_TIMER_OUT = 200
SPECTRO_TIMER = 200


function_keys = {
    16777264: "F1",
    16777265: "F2",
    16777266: "F3",
    16777267: "F4",
    16777268: "F5",
    16777269: "F6",
    16777270: "F7",
    16777271: "F8",
    16777272: "F9",
    16777273: "F10",
    16777274: "F11",
    16777275: "F12",
}

PROJECT_NAME = "project_name"
PROJECT_DATE = "project_date"
PROJECT_DESCRIPTION = "project_description"

TIME_FORMAT = "time_format"

OBSERVATIONS = "observations"
EVENTS = "events"
TIME_OFFSET = "time offset"

CODING_MAP = "coding_map"
BEHAVIORS_CODING_MAP = "behaviors_coding_map"
SUBJECTS = "subjects_conf"
ETHOGRAM = "behaviors_conf"
BEHAVIORAL_CATEGORIES = "behavioral_categories"
CONVERTERS = "converters"

OBSERVATION_TIME_INTERVAL = "observation time interval"

SUBJECT_NAME = "name"

TIME_BUDGET_FORMAT = "time_budget_format"
COMPACT_TIME_BUDGET_FORMAT = "compact"
LONG_TIME_BUDGET_FORMAT = "long"
DEFAULT_TIME_BUDGET_FORMAT = LONG_TIME_BUDGET_FORMAT


CODING_MAP_RESIZE_W = 640
CODING_MAP_RESIZE_H = 640

POINT_EVENT_PLOT_DURATION = 0.010
POINT_EVENT_PLOT_COLOR = "black"

CHAR_FORBIDDEN_IN_MODIFIERS = "(|),`~"

ADAPT_FAST_JUMP = "adapt_fast_jump"
ADAPT_FAST_JUMP_DEFAULT = False

subjects_config = ["key", "id"]

subjectsFields = ["key", SUBJECT_NAME, "description"]

UNPAIRED = "UNPAIRED"
DISPLAY_SUBTITLES = "display_subtitles"

YES = "Yes"
NO = "No"
CANCEL = "Cancel"
REMOVE = "Remove"
SAVE = "Save"
DISCARD = "Discard"
OK = "OK"
OVERWRITE = "Overwrite"
OVERWRITE_ALL = "Overwrite all"

NO_FOCAL_SUBJECT = "No focal subject"

TYPE = "type"
FILE = "file"
DESCRIPTION = "description"

PLOT_DATA = "plot_data"

PLOT_DATA_FILEPATH_IDX = 0
PLOT_DATA_COLUMNS_IDX = 1
PLOT_DATA_PLOTTITLE_IDX = 2
PLOT_DATA_VARIABLENAME_IDX = 3
PLOT_DATA_CONVERTERS_IDX = 4
PLOT_DATA_TIMEINTERVAL_IDX = 5
PLOT_DATA_TIMEOFFSET_IDX = 6
PLOT_DATA_SUBSTRACT1STVALUE_IDX = 7
PLOT_DATA_PLOTCOLOR_IDX = 8

DATA_PLOT_FIELDS = {
    PLOT_DATA_FILEPATH_IDX: "file_path",
    PLOT_DATA_COLUMNS_IDX: "columns",
    PLOT_DATA_PLOTTITLE_IDX: "title",
    PLOT_DATA_VARIABLENAME_IDX: "variable_name",
    PLOT_DATA_CONVERTERS_IDX: "converters",
    PLOT_DATA_TIMEINTERVAL_IDX: "time_interval",
    PLOT_DATA_TIMEOFFSET_IDX: "time_offset",
    PLOT_DATA_SUBSTRACT1STVALUE_IDX: "substract_first_value",
    PLOT_DATA_PLOTCOLOR_IDX: "color",
}
DATA_PLOT_STYLES = ["b-", "r-", "g-", "bo", "ro", "go"]

BEHAVIOR_CODE = "code"
BEHAVIOR_KEY = "key"
BEHAVIOR_CATEGORY = "category"


# fields for event configuration
fields = {
    "type": 0,
    "key": 1,
    "code": 2,
    "description": 3,
    "modifiers": 4,
    "excluded": 5,
    "coding map": 6,
}

behav_fields_in_mainwindow = {
    0: "key",
    1: "code",
    2: "type",
    3: "description",
    4: "category",
    5: "modifiers",
    6: "excluded",
}

# fields in ethogram table from project window
# behavioursFields = {'type': 0, 'key': 1, 'code': 2, 'description': 3, 'modifiers': 4, 'excluded': 5, 'coding map': 6}
behavioursFields = {
    "type": 0,
    "key": 1,
    "code": 2,
    "description": 3,
    "category": 4,
    "modifiers": 5,
    "excluded": 6,
    "coding map": 7,
}

ETHOGRAM_FIELDS = [
    "type",
    "key",
    "code",
    "description",
    "category",
    "modifiers",
    "excluded",
    "coding map",
]
ETHOGRAM_EDITABLE_FIELDS = ["key", "code", "description"]

PROJECT_BEHAVIORS_KEY_FIELD_IDX = 1
PROJECT_BEHAVIORS_CODE_FIELD_IDX = 2

MEDIA_FILE_PATH_IDX = 2
HAS_AUDIO_IDX = 6

STATE_EVENT = "State event"
POINT_EVENT = "Point event"

BEHAVIOR_TYPES = [
    "Point event",
    "State event",
    "Point event with coding map",
    "State event with coding map",
]

DEFAULT_BEHAVIOR_TYPE = "Point event"

# fields for events table
tw_events_fields = ["time", "subject", "code", "type", "modifier", "comment"]

# fields for project events list
pj_events_fields = ["time", "subject", "code", "modifier", "comment"]

tw_indVarFields = ["label", "description", "type", "default value", "possible values"]

BEHAV_CODING_MAP_FIELDS = ["name", "Behavior codes"]

EXCEL_FORBIDDEN_CHARACTERS = r"\/*[]:?"

# create dictionaries
tw_obs_fields, pj_obs_fields = {}, {}

for idx, field in enumerate(tw_events_fields):
    tw_obs_fields[field] = idx


for idx, field in enumerate(pj_events_fields):
    pj_obs_fields[field] = idx


EVENT_TIME_FIELD_IDX = 0

SUBJECT_EVENT_FIELD = 1  # to be removed after check
EVENT_SUBJECT_FIELD_IDX = 1

BEHAVIOR_EVENT_FIELD = 2  # to be removed after check
EVENT_BEHAVIOR_FIELD_IDX = 2

EVENT_MODIFIER_FIELD_IDX = 3

EVENT_COMMENT_FIELD_IDX = 4

SUBJECT_NAME_FIELD_IDX = 1

LIVE = "LIVE"
MEDIA = "MEDIA"
VIEWER = "VIEWER"

HHMMSS = "hh:mm:ss"
HHMMSSZZZ = "hh:mm:ss.zzz"
S = "s"

START_FROM_CURRENT_TIME = "start_from_current_time"
START_FROM_CURRENT_EPOCH_TIME = "start_from_current_epoch_time"

SCAN_SAMPLING_TIME = "scan_sampling_time"

NEW = "new"
LIST = "list"
EDIT = "edit"
OPEN = "open"
VIEW = "view"
SELECT = "select"
SINGLE = "single"
MULTIPLE = "multiple"

SELECT1 = "select1"

FILTERED_BEHAVIORS = "filtered behaviors"

SELECTED_BEHAVIORS = "selected behaviors"
SELECTED_SUBJECTS = "selected subjects"
INCLUDE_MODIFIERS = "include modifiers"
EXCLUDE_BEHAVIORS = "exclude behaviors"
EXCLUDED_BEHAVIORS = "excluded behaviors"
TIME_INTERVAL = "time"
START_TIME = "start time"
END_TIME = "end time"

# indep variables
NUMERIC = "numeric"
NUMERIC_idx = 0
TEXT = "text"
TEXT_idx = 1
SET_OF_VALUES = "value from set"
SET_OF_VALUES_idx = 2
TIMESTAMP = "timestamp"
TIMESTAMP_idx = 3


TIME_FULL_OBS = "full obs"
TIME_EVENTS = "limit to events"
TIME_ARBITRARY_INTERVAL = "time interval"

AVAILABLE_INDEP_VAR_TYPES = [NUMERIC, TEXT, SET_OF_VALUES, TIMESTAMP]


INDEPENDENT_VARIABLES = "independent_variables"
OBSERVATIONS = "observations"

CLOSE_BEHAVIORS_BETWEEN_VIDEOS = "close_behaviors_between_videos"

VLC = "vlc"
FFMPEG = "ffmpeg"

SAVE_FRAMES = "save_frames"
MEMORY_FOR_FRAMES = "memory_for_frames"
DEFAULT_MEMORY_FOR_FRAMES = 80  # % total memory
DISK = "disk"
MEMORY = "memory"
DEFAULT_FRAME_MODE = DISK

MEDIA_FILE_INFO = "media_file_info"
MEDIA_INFO = "media_info"
LENGTH = "length"
FPS = "fps"
HAS_AUDIO = "hasAudio"
HAS_VIDEO = "hasVideo"

STATE = "STATE"
POINT = "POINT"

START = "START"
STOP = "STOP"

PLAYER1, PLAYER2 = "1", "2"
ALL_PLAYERS = [str(x + 1) for x in range(N_PLAYER)]

VISUALIZE_SPECTROGRAM = "visualize_spectrogram"
VISUALIZE_WAVEFORM = "visualize_waveform"

POINT_EVENT_ST_DURATION = 0.5

VIDEO_TAB = 0
FRAME_TAB = 1

slider_maximum = 1000

FRAME_BITMAP_FORMAT_LIST = ["JPG", "PNG"]
FRAME_DEFAULT_BITMAP_FORMAT = "JPG"

FRAME_DEFAULT_CACHE_SIZE = 1

# modifiers
MODIFIERS = "modifiers"
SINGLE_SELECTION = 0
MULTI_SELECTION = 1
NUMERIC_MODIFIER = 2
EXTERNAL_DATA_MODIFIER = 3

MODIFIERS_STR = {
    SINGLE_SELECTION: "Single item selection",
    MULTI_SELECTION: "Multiple items selection",
    NUMERIC_MODIFIER: "Numeric",
    EXTERNAL_DATA_MODIFIER: "Value from external data file",
}

# colors
subtitlesColors = [
    "cyan",
    "red",
    "blue",
    "yellow",
    "fuchsia",
    "orange",
    "lime",
    "green",
]

CATEGORY_COLORS_LIST = [
    "#FF96CC",
    "#96FF9C",
    "#CCFFFE",
    "#EEFF70",
    "#FF4F64",
    "#F8BF15",
    "#3DC7AD",
]

SPECTROGRAM_COLOR_MAPS = ["viridis", "inferno", "plasma", "magma", "gray", "YlOrRd"]
SPECTROGRAM_DEFAULT_COLOR_MAP = "viridis"
SPECTROGRAM_DEFAULT_TIME_INTERVAL = 10


# see matplotlib.colors.cnames.keys()
# https://xkcd.com/color/rgb/

# sage colors are no more available
# darksage #598556
# lightsage #bcecac
# sage #87ae73
ACTIVE_MEASUREMENTS_COLOR = "lime"
PASSIVE_MEASUREMENTS_COLOR = "red"

BEHAVIORS_PLOT_COLORS = [
    "tab:blue",
    "tab:orange",
    "tab:green",
    "tab:red",
    "tab:purple",
    "tab:brown",
    "tab:pink",
    "tab:gray",
    "tab:olive",
    "tab:cyan",
    "blue",
    "green",
    "red",
    "cyan",
    "magenta",
    "yellow",
    "lime",
    "darksalmon",
    "purple",
    "orange",
    "maroon",
    "silver",
    "slateblue",
    "hotpink",
    "steelblue",
    "darkgoldenrod",
    "aqua",
    "aquamarine",
    "beige",
    "bisque",
    "black",
    "blanchedalmond",
    "blueviolet",
    "brown",
    "burlywood",
    "cadetblue",
    "chartreuse",
    "chocolate",
    "coral",
    "cornflowerblue",
    "cornsilk",
    "crimson",
    "darkblue",
    "darkcyan",
    "darkgreen",
    "darkgrey",
    "darkkhaki",
    "darkmagenta",
    "darkolivegreen",
    "darkorange",
    "darkorchid",
    "darkred",
    "#598556",
    "darkseagreen",
    "darkslateblue",
    "darkslategray",
    "darkslategrey",
    "darkturquoise",
    "darkviolet",
    "deeppink",
    "deepskyblue",
    "dimgray",
    "dimgrey",
    "dodgerblue",
    "firebrick",
    "floralwhite",
    "forestgreen",
    "fuchsia",
    "gainsboro",
    "gold",
    "goldenrod",
    "gray",
    "greenyellow",
    "grey",
    "honeydew",
    "indianred",
    "indigo",
    "khaki",
    "lawngreen",
    "lemonchiffon",
    "lightblue",
    "lightcoral",
    "lightgoldenrodyellow",
    "lightgray",
    "lightgreen",
    "lightgrey",
    "lightpink",
    "#bcecac",
    "lightsalmon",
    "lightseagreen",
    "lightskyblue",
    "lightslategray",
    "lightslategrey",
    "lightsteelblue",
    "lightyellow",
    "limegreen",
    "linen",
    "mediumaquamarine",
    "mediumblue",
    "mediumorchid",
    "mediumpurple",
    "mediumseagreen",
    "mediumslateblue",
    "mediumspringgreen",
    "mediumturquoise",
    "mediumvioletred",
    "midnightblue",
    "mintcream",
    "mistyrose",
    "moccasin",
    "navajowhite",
    "navy",
    "oldlace",
    "olive",
    "olivedrab",
    "orangered",
    "orchid",
    "palegoldenrod",
    "palegreen",
    "paleturquoise",
    "palevioletred",
    "papayawhip",
    "peachpuff",
    "peru",
    "pink",
    "plum",
    "powderblue",
    "rosybrown",
    "royalblue",
    "saddlebrown",
    "#87ae73",
    "salmon",
    "sandybrown",
    "seagreen",
    "seashell",
    "sienna",
    "skyblue",
    "slategray",
    "slategrey",
    "springgreen",
    "tan",
    "teal",
    "thistle",
    "tomato",
    "turquoise",
    "violet",
    "wheat",
    "yellowgreen",
    "darkgray",
]

EMPTY_PROJECT = {
    "time_format": HHMMSS,
    "project_date": "",
    "project_name": "",
    "project_description": "",
    "project_format_version": project_format_version,
    SUBJECTS: {},
    ETHOGRAM: {},
    OBSERVATIONS: {},
    BEHAVIORAL_CATEGORIES: [],
    INDEPENDENT_VARIABLES: {},
    CODING_MAP: {},
    BEHAVIORS_CODING_MAP: [],
    CONVERTERS: {},
}


INIT_PARAM = {DISPLAY_SUBTITLES: False,
              SAVE_FRAMES: DISK,
              MEMORY_FOR_FRAMES: DEFAULT_MEMORY_FOR_FRAMES,
              ADAPT_FAST_JUMP: ADAPT_FAST_JUMP_DEFAULT,
              TIME_BUDGET_FORMAT: DEFAULT_TIME_BUDGET_FORMAT,
              }
