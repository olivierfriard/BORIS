"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2022 Olivier Friard


  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
  MA 02110-1301, USA.

"""

import logging
from decimal import Decimal

from . import config as cfg
from . import utilities as util


def get_latency(self):
    """
    get latency (time after marker/stimulus)
    """
    print("latency")

    _, selected_observations = self.selectObservations(cfg.MULTIPLE)
    if not selected_observations:
        return

    cancel_pressed, marker_behaviors = self.filter_behaviors(
        title="Select the marker behaviors",
        text="",
        table="",
    )
    if cancel_pressed:
        return

    cancel_pressed, behaviors = self.filter_behaviors(
        title="Select the behaviors for latency",
        text="",
        table="",
    )
    if cancel_pressed:
        return

    for obs_id in selected_observations:
        print(obs_id)
        print(self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS])
        grouped_events = util.group_events(self.pj, obs_id)
        print(grouped_events)

        for marker_behavior in marker_behaviors:
            for sbm in grouped_events:
                if sbm[1] == marker_behavior:
                    for idx1, event1 in enumerate(grouped_events[sbm]):
                        if idx1 < len(grouped_events[sbm]) - 1:
                            limit = grouped_events[sbm][idx1 + 1][0]
                        else:
                            limit = self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS][-1][cfg.EVENT_TIME_FIELD_IDX] + 1
                        for sbm2 in grouped_events:
                            if sbm2[1] in behaviors:
                                for event in grouped_events[sbm2]:
                                    if event[0] >= event1[0] and event[0] < limit:
                                        print(sbm2, " after ", sbm, ":", event[0] - event1[0])
