"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2025 Olivier Friard

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


MACOS_CODE = "darwin"
MPV_SOCKET = "/tmp/mpvsocket"


ETHOGRAM_REPOSITORY_URL = "https://www.boris.unito.it/static/ethograms"

project_format_version: str = "7.0"

SECONDS_PER_DAY: int = 86_400

# cutoff value for displaying HH:MM:SS.zzz or YYYY-mm-DD HH:MM:SS:ZZZ
HOUR_CUTOFF: int = 7 * 24
DATE_CUTOFF: int = HOUR_CUTOFF * 60 * 60  # 1 week

SMART_TIME_CUTOFF_DEFAULT: int = 300

# minimal project version for handling observations from images
IMAGES_OBS_PROJECT_MIN_VERSION: tuple = (8, 6)

IMAGE_EXTENSIONS: tuple = ("*.jpg", "*.png", "*.jpeg", "*.tiff", "*.tif", "*.webp", "*.bmp")

CHECK_NEW_VERSION_DELAY: int = 15 * 24 * 60 * 60

N_PLAYER: int = 8

MAX_UNDO_QUEUE: int = 25

NA: str = "NA"

REALTIME_PLOT_CURSOR_COLOR: str = "red"

DARKER_DIFFERENCE = 5

CTRL_KEY: str = "Ctrl"
ALT_KEY: str = "Alt"

SPECTRO_TIMER: int = 500

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
PROJECT_VERSION = "project_format_version"

TIME_FORMAT = "time_format"

OBSERVATIONS = "observations"
EVENTS = "events"
TIME_OFFSET = "time offset"

CODING_MAP = "coding_map"
CODING_MAP_sp = "coding map"  # space between words (no underscore)
BEHAVIORS_CODING_MAP = "behaviors_coding_map"
SUBJECTS = "subjects_conf"
ETHOGRAM = "behaviors_conf"
BEHAVIORAL_CATEGORIES = "behavioral_categories"
BEHAVIORAL_CATEGORIES_CONF = "behavioral_categories_config"
CONVERTERS = "converters"

OFFSET = "offset"

OBSERVATION_TIME_INTERVAL = "observation time interval"

SUBJECT_NAME = "name"

TIME_BUDGET_FORMAT = "time_budget_format"
"""
COMPACT_TIME_BUDGET_FORMAT = "compact"
LONG_TIME_BUDGET_FORMAT = "long"
DEFAULT_TIME_BUDGET_FORMAT = LONG_TIME_BUDGET_FORMAT
"""

DESCRIPTION = "description"

TIME_BIN_SIZE = "time bin size"

CODING_MAP_RESIZE_W = 640
CODING_MAP_RESIZE_H = 640

# playerType
LIVE = "LIVE"
MEDIA = "MEDIA"
IMAGES = "IMAGES"

VIEWER_MEDIA = "VIEWER_MEDIA"
VIEWER_LIVE = "VIEWER_LIVE"
VIEWER_IMAGES = "VIEWER_IMAGES"

VIEWERS = (VIEWER_MEDIA, VIEWER_LIVE, VIEWER_IMAGES)

POINT_EVENT_PLOT_DURATION = 0.010
POINT_EVENT_PLOT_COLOR = "black"

CHAR_FORBIDDEN_IN_MODIFIERS = "(|),`~"

ADAPT_FAST_JUMP = "adapt_fast_jump"
ADAPT_FAST_JUMP_DEFAULT = False

TIME = "time"
BEHAVIOR_CODE = "code"
SUBJECT = "subject"
MODIFIER = "modifier"
COMMENT = "comment"
BEHAVIOR_KEY = "key"
SUBJECT_KEY = "key"
BEHAVIOR_CATEGORY = "category"


subjectsFields = [SUBJECT_KEY, SUBJECT_NAME, DESCRIPTION]

UNPAIRED = "UNPAIRED"
DISPLAY_SUBTITLES = "display_subtitles"
CHECK_PROJECT_INTEGRITY = "check_project_integrity"


YES = "Yes"
NO = "No"
CANCEL = "Cancel"
IGNORE = "Ignore"
APPEND = "Append"
CLOSE = "Close"
REPLACE = "Replace"
REMOVE = "Remove"
SAVE = "Save"
DISCARD = "Discard"
OK = "OK"
OVERWRITE = "Overwrite"
OVERWRITE_ALL = "Overwrite all"
SKIP = "Skip"
SKIP_ALL = "Skip all"

NO_FOCAL_SUBJECT = "No focal subject"

TYPE = "type"
FILE = "file"
COLOR = "color"
DIRECTORIES_LIST = "directories_list"

SAVE_DATASET = 32

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


FILE_PATH = "file_path"

IMAGE_INDEX = "image index"
IMAGE_PATH = "image path"
FRAME_INDEX = "frame index"

ZOOM_LEVEL = "zoom level"
PAN_X = "pan-x"
PAN_Y = "pan-y"
ROTATION_ANGLE = "rotation angle"
DISPLAY_MEDIA_SUBTITLES = "display subtitles"
OVERLAY = "video overlay"


USE_EXIF_DATE = "use_exif_date"
TIME_LAPSE = "time_lapse_delay"


# fields for event configuration

ETHOGRAM_TABLE_COLUMNS: dict = {
    0: "key",
    1: "code",
    2: "type",
    3: "description",
    4: "color",
    5: "category",
    6: "modifiers",
    7: "excluded",
}

# fields in ethogram table from project window
behavioursFields: dict = {
    "type": 0,
    "key": 1,
    "code": 2,
    "description": 3,
    "color": 4,
    "category": 5,
    "modifiers": 6,
    "excluded": 7,
    "coding map": 8,
}
ETHOGRAM_EDITABLE_FIELDS: tuple = ("key", "code", "description")

PROJECT_BEHAVIORS_KEY_FIELD_IDX = 1
PROJECT_BEHAVIORS_CODE_FIELD_IDX = 2

MEDIA_FILE_PATH_IDX = 2
HAS_AUDIO_IDX = 6

STATE_EVENT = "State event"
STATE_EVENT_WITH_CODING_MAP = "State event with coding map"

STATE_EVENT_TYPES = [STATE_EVENT, STATE_EVENT_WITH_CODING_MAP]

POINT_EVENT = "Point event"
POINT_EVENT_WITH_CODING_MAP = "Point event with coding map"

POINT_EVENT_TYPES = [POINT_EVENT, POINT_EVENT_WITH_CODING_MAP]

BEHAVIOR_TYPES = [
    POINT_EVENT,
    STATE_EVENT,
    POINT_EVENT_WITH_CODING_MAP,
    STATE_EVENT_WITH_CODING_MAP,
]

DEFAULT_BEHAVIOR_TYPE = "Point event"

MEDIA_TW_EVENTS_FIELDS_DEFAULT = ("time", FRAME_INDEX, "subject", "code", "type", "modifier", "comment")


# fields for events tablewidget
MEDIA_TW_EVENTS_FIELDS = ("time", FRAME_INDEX, "subject", "code", "type", "modifier", "comment")
# MEDIA_TW_EVENTS_FIELDS = ("time", "subject", "code", "type", "modifier", "comment")
LIVE_TW_EVENTS_FIELDS = ("time", "subject", "code", "type", "modifier", "comment")
IMAGES_TW_EVENTS_FIELDS = ("time", "subject", "code", "type", "modifier", "comment", IMAGE_INDEX, IMAGE_PATH)

TW_EVENTS_FIELDS = {
    MEDIA: MEDIA_TW_EVENTS_FIELDS,
    LIVE: LIVE_TW_EVENTS_FIELDS,
    VIEWER_MEDIA: MEDIA_TW_EVENTS_FIELDS,
    VIEWER_LIVE: LIVE_TW_EVENTS_FIELDS,
    IMAGES: IMAGES_TW_EVENTS_FIELDS,
    VIEWER_IMAGES: IMAGES_TW_EVENTS_FIELDS,
}

# create dictionary index
TW_OBS_FIELD = {}
for observation_type in TW_EVENTS_FIELDS:
    TW_OBS_FIELD[observation_type] = {}
    for idx, field in enumerate(TW_EVENTS_FIELDS[observation_type]):
        TW_OBS_FIELD[observation_type][field] = idx


# fields for project events list
MEDIA_PJ_EVENTS_FIELDS = (TIME, "subject", "code", "modifier", "comment", FRAME_INDEX)
LIVE_PJ_EVENTS_FIELDS = (TIME, "subject", "code", "modifier", "comment")
IMAGES_PJ_EVENTS_FIELDS = (TIME, "subject", "code", "modifier", "comment", IMAGE_INDEX, IMAGE_PATH)

PJ_EVENTS_FIELDS = {
    MEDIA: MEDIA_PJ_EVENTS_FIELDS,
    VIEWER_MEDIA: MEDIA_PJ_EVENTS_FIELDS,
    LIVE: LIVE_PJ_EVENTS_FIELDS,
    VIEWER_LIVE: LIVE_PJ_EVENTS_FIELDS,
    IMAGES: IMAGES_PJ_EVENTS_FIELDS,
    VIEWER_IMAGES: IMAGES_PJ_EVENTS_FIELDS,
}


PJ_OBS_FIELDS = {}
for observation_type in PJ_EVENTS_FIELDS:
    PJ_OBS_FIELDS[observation_type] = {}
    for idx, field in enumerate(PJ_EVENTS_FIELDS[observation_type]):
        PJ_OBS_FIELDS[observation_type][field] = idx


# fields for independent variable definition
tw_indVarFields = ["label", "description", "type", "default value", "possible values"]


EVENT_TIME_FIELD_IDX = 0
EVENT_SUBJECT_FIELD_IDX = 1
EVENT_BEHAVIOR_FIELD_IDX = 2
EVENT_MODIFIER_FIELD_IDX = 3
EVENT_COMMENT_FIELD_IDX = 4
EVENT_STATUS_FIELD_IDX = -1
# EVENT_IMAGEIDX_FIELD_IDX = 6
# EVENT_IMAGEPATH_FIELD_IDX = 7


BEHAV_CODING_MAP_FIELDS = ["name", "Behavior codes"]

# characters not allowed in Excel sheet name
EXCEL_FORBIDDEN_CHARACTERS: str = r"\/*[]:?"


# indexes of project window
MEDIA_TAB_IDX = 0
LIVE_TAB_IDX = 1


HHMMSS = "hh:mm:ss"
HHMMSSZZZ = "hh:mm:ss.zzz"
S = "s"

START_FROM_CURRENT_TIME = "start_from_current_time"
START_FROM_CURRENT_EPOCH_TIME = "start_from_current_epoch_time"

SCAN_SAMPLING_TIME = "scan_sampling_time"

POINT_OBJECT = "Point"
SEGMENT_OBJECT = "Segment"
ANGLE_OBJECT = "Angle"
ORIENTED_ANGLE_OBJECT = "Oriented angle"
POLYGON_OBJECT = "Polygon"
POLYLINE_OBJECT = "Polyline"


NEW = "new"
LIST = "list"
EDIT = "edit"
OPEN = "open"
VIEW = "view"
OBS_START = "start"
SELECT = "select"
SINGLE = "single"
MULTIPLE = "multiple"


SELECT1 = "select1"

FILTERED_BEHAVIORS = "filtered behaviors"

SELECTED_BEHAVIORS = "selected behaviors"
SELECTED_SUBJECTS = "selected subjects"
INCLUDE_MODIFIERS = "include modifiers"
EXCLUDE_BEHAVIORS = "exclude behaviors"
EXCLUDE_NON_CODED_MODIFIERS = "exclude_non_coded_modifiers"
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
TIME_OBS_INTERVAL = "interval of observation"
TIME_ARBITRARY_INTERVAL = "time interval"

AVAILABLE_INDEP_VAR_TYPES = [NUMERIC, TEXT, SET_OF_VALUES, TIMESTAMP]

INDEPENDENT_VARIABLES = "independent_variables"
OBSERVATIONS = "observations"

CLOSE_BEHAVIORS_BETWEEN_VIDEOS = "close_behaviors_between_videos"

# MPV hardware decode
MPV_HWDEC = "mpv_hwdec"
MPV_HWDEC_NO = "no"
MPV_HWDEC_AUTO = "auto"
MPV_HWDEC_AUTOSAFE = "auto-safe"
MPV_HWDEC_OPTIONS = (MPV_HWDEC_AUTO, MPV_HWDEC_AUTOSAFE, MPV_HWDEC_NO)
MPV_HWDEC_DEFAULT_VALUE = MPV_HWDEC_AUTO

ANALYSIS_PLUGINS = "analysis_plugins"
EXCLUDED_PLUGINS = "excluded_plugins"
PERSONAL_PLUGINS_DIR = "personal_plugins_dir"

PROJECT_FILE_INDENTATION = "project file indentation"
PROJECT_FILE_INDENTATION_COMBO_OPTIONS = ("None", "Newline", "Tab", "2 spaces", "4 spaces")
PROJECT_FILE_INDENTATION_OPTIONS = (None, 0, "\t", 2, 4)
PROJECT_FILE_INDENTATION_DEFAULT_VALUE = None

TOOLBAR_ICON_SIZE = "toolbar icon size"
DEFAULT_TOOLBAR_ICON_SIZE_VALUE = 24


VIDEO_VIEWER = 0
PICTURE_VIEWER = 1

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
MEDIA_CREATION_TIME = "media_creation_time"

STATE = "STATE"
POINT = "POINT"

START = "START"
STOP = "STOP"

PLAYER1 = "1"
PLAYER2 = "2"
ALL_PLAYERS = [str(x + 1) for x in range(N_PLAYER)]

VISUALIZE_SPECTROGRAM = "visualize_spectrogram"
VISUALIZE_WAVEFORM = "visualize_waveform"
MEDIA_CREATION_DATE_AS_OFFSET = "media_creation_date_as_offset"

MEDIA_SCAN_SAMPLING_DURATION = "media_scan_sampling_duration"
IMAGE_DISPLAY_DURATION = "image_display_duration"

# plot type
WAVEFORM_PLOT = "waveform"
SPECTROGRAM_PLOT = "spectrogram"
EVENTS_PLOT = "plot_events"

PLAYING = "playing"
PAUSED = "paused"
STOPPED = "stopped"

POINT_EVENT_ST_DURATION = 0.5

VIDEO_TAB = 0
FRAME_TAB = 1

SLIDER_MAXIMUM = 1000

FRAME_DEFAULT_CACHE_SIZE = 1

EXCLUDED = "excluded"

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

CODING_PAD_CONFIG = "coding pad configuration"
CODING_PAD_GEOMETRY = "coding pad geometry"
NO_COLOR_CODING_PAD = "#777777"

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

# see matplotlib for color name
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
    TIME_FORMAT: HHMMSS,
    PROJECT_DATE: "",
    PROJECT_NAME: "",
    PROJECT_DESCRIPTION: "",
    PROJECT_VERSION: project_format_version,
    SUBJECTS: {},
    ETHOGRAM: {},
    OBSERVATIONS: {},
    BEHAVIORAL_CATEGORIES: [],
    BEHAVIORAL_CATEGORIES_CONF: {},
    INDEPENDENT_VARIABLES: {},
    CODING_MAP: {},
    BEHAVIORS_CODING_MAP: [],
    CONVERTERS: {},
}

INIT_PARAM = {
    DISPLAY_SUBTITLES: False,
    SAVE_FRAMES: DISK,
    MEMORY_FOR_FRAMES: DEFAULT_MEMORY_FOR_FRAMES,
    ADAPT_FAST_JUMP: ADAPT_FAST_JUMP_DEFAULT,
    # TIME_BUDGET_FORMAT: DEFAULT_TIME_BUDGET_FORMAT,
    MPV_HWDEC: MPV_HWDEC_DEFAULT_VALUE,
    PROJECT_FILE_INDENTATION: PROJECT_FILE_INDENTATION_DEFAULT_VALUE,
    f"{MEDIA} tw fields": MEDIA_TW_EVENTS_FIELDS_DEFAULT,
}

SDIS_EXT = "sds"
TBS_EXT = "tbs"
TSV_EXT = "tsv"
CSV_EXT = "csv"
RDS_EXT = "rds"
PANDAS_DF_EXT = "pkl"
HTML_EXT = "html"
SQL_EXT = "sql"
ODS_EXT = "ods"
XLS_EXT = "xls"
XLSX_EXT = "xlsx"

# Output format
TSV = "Tab Separated Values (*.tsv)"
CSV = "Comma Separated Values (*.csv)"
ODS = "OpenDocument Spreadsheet ODS (*.ods)"
ODS_WB = "OpenDocument Workbook (*.ods)"
XLSX = "Microsoft Excel Spreadsheet XLSX (*.xlsx)"
XLSX_WB = "Microsoft Excel Workbook (*.xlsx)"
XLS = "Legacy Microsoft Excel Spreadsheet XLS (*.xls)"
HTML = "HTML (*.html)"
PANDAS_DF = "Pandas DataFrame (*.pkl)"
RDS = "R dataframe (*.rds)"
SQL = "SQL dump file (*.sql)"
SDIS = "SDIS (*.sds)"
TBS = "Timed Behavioral Sequences (*.tbs)"
TEXT_FILE = "Text file"

FILE_NAME_SUFFIX = {
    TSV: TSV_EXT,
    CSV: CSV_EXT,
    ODS: ODS_EXT,
    ODS_WB: ODS_EXT,
    XLSX: XLSX_EXT,
    XLSX_WB: XLSX_EXT,
    XLS: XLS_EXT,
    HTML: HTML_EXT,
    PANDAS_DF: PANDAS_DF_EXT,
    RDS: RDS_EXT,
    SQL: SQL_EXT,
    SDIS: SDIS_EXT,
    TBS: TBS_EXT,
    TEXT_FILE: "cli",
}
