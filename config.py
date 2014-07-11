#!/usr/bin/env python

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2014 Olivier Friard

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


#DEBUG = True

programName = 'BORIS'

project_format_version = '1.6'

OBSERVATIONS = 'observations'
TIME_OFFSET='time offset'

CODING_MAP = 'coding_map'
SUBJECTS = 'subjects_conf'

subjects_config = ['key', 'id']

subjectsFields = ['key', 'name', 'description']


### fields for event configuration
#fields = {'type': 0, 'key': 1, 'code': 2, 'description': 3, 'modifiers': 4, 'excluded': 5}
fields = {'type': 0, 'key': 1, 'code': 2, 'description': 3, 'modifiers': 4, 'excluded': 5, 'coding map': 6}
behavioursFields = {'type': 0, 'key': 1, 'code': 2, 'description': 3, 'modifiers': 4, 'excluded': 5, 'coding map': 6}

observation_types = ['Point event', 'State event', 'Point event with coding map', 'State event with coding map']

### fields from observation (list for order)
tw_events_fields = ['time', 'subject', 'code', 'type', 'modifier', 'comment']
pj_events_fields = ['time', 'subject', 'code', 'modifier', 'comment']

tw_indVarFields = ['label','description', 'type', 'default value']

### create dictionaries
tw_obs_fields, pj_obs_fields = {}, {}

for idx, field in enumerate(tw_events_fields):
    tw_obs_fields[ field ] = idx


for idx, field in enumerate(pj_events_fields):
    pj_obs_fields[ field ] = idx

LIVE = 'LIVE'
MEDIA = 'MEDIA'

HHMMSS = 'hh:mm:ss'
S = 's'

NEW='new'
LIST = 'list'
EDIT = 'edit'
OPEN = 'open'
SELECT = 'select'
SINGLE = 'single'
MULTIPLE = 'multiple'

NUMERIC = 'numeric'
TEXT = 'text'
INDEPENDENT_VARIABLES = 'independent_variables'
OBSERVATIONS = 'observations'

OPENCV = 'opencv'
VLC = 'vlc'
