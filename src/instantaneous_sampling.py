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
                           parameters_obs: dict,
                           time_interval: float):

    print(parameters_obs)
    results_df = {}

    state_behavior_codes = [x for x in utilities.state_behavior_codes(pj[ETHOGRAM]) if x in parameters_obs[SELECTED_BEHAVIORS]]

    n_rows = int((parameters_obs[END_TIME] - parameters_obs[START_TIME]) / time_interval) + 1


    for obs_id in selected_observations:
        '''
        out += f"Observation: {obs_id}\n\n"
        '''
        if obs_id not in results_df:
          results_df[obs_id] = {}

        for subject in parameters_obs[SELECTED_SUBJECTS]:

            '''
            out += subject + ":\n\n"
            '''
            results_df[obs_id][subject] = pd.DataFrame(index=range(n_rows), columns=["time"] + parameters_obs[SELECTED_BEHAVIORS])
            row_idx = 0
            t = parameters_obs[START_TIME]
            while t < parameters_obs[END_TIME]:

                current_states = utilities.get_current_states_modifiers_by_subject(state_behavior_codes,
                                                                             pj[OBSERVATIONS][obs_id][EVENTS],
                                                                             dict([(idx, pj[SUBJECTS][idx]) for idx in pj[SUBJECTS]
                                                                                                            if pj[SUBJECTS][idx]["name"] == subject]),
                                                                             t,
                                                                             include_modifiers=parameters_obs[INCLUDE_MODIFIERS])

                results_df[obs_id][subject].loc[row_idx, "time"] = float(t)
                for behav in parameters_obs[SELECTED_BEHAVIORS]:
                    print(list(current_states.values()))
                    results_df[obs_id][subject].loc[row_idx, behav] = int(behav in list(current_states.values())[0])

                t += time_interval
                row_idx += 1

            print(results_df[obs_id][subject].to_string(index=False))

            '''
            out += df.to_csv(index=False, sep="\t") + "\n\n"
            '''

    return results_df
