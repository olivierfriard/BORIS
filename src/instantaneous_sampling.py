"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2019 Olivier Friard

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

from config import *
import utilities
import pandas as pd


def instantaneous_sampling(pj: dict,
                           selected_observations: list,
                           parameters_obs: dict):

    interval = 1

    print(parameters_obs)

    state_behavior_codes = [x for x in utilities.state_behavior_codes(pj[ETHOGRAM]) if x in parameters_obs[SELECTED_BEHAVIORS]]

    n_rows = int((parameters_obs[END_TIME] - parameters_obs[START_TIME]) / interval) + 1



    for obs_id in selected_observations:
        for subject in parameters_obs[SELECTED_SUBJECTS]:

            print(subject)
            df = pd.DataFrame(index=range(n_rows), columns=["time"] + parameters_obs[SELECTED_BEHAVIORS])
            row_idx = 0
            t = parameters_obs[START_TIME]
            while t < parameters_obs[END_TIME]:

                current_states = utilities.get_current_states_modifiers_by_subject(state_behavior_codes,
                                                                             pj[OBSERVATIONS][obs_id][EVENTS],
                                                                             dict([(idx, pj[SUBJECTS][idx]) for idx in pj[SUBJECTS]
                                                                                                            if pj[SUBJECTS][idx]["name"] == subject]),
                                                                             t,
                                                                             include_modifiers=parameters_obs[INCLUDE_MODIFIERS])

                df.loc[row_idx, "time"] = float(t)
                for behav in parameters_obs[SELECTED_BEHAVIORS]:
                    df.loc[row_idx, behav] = int(behav in list(current_states.values())[0])

                t += 1
                row_idx += 1

            print(df.to_string(index=False))
