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
import time

'''
def instantaneous_sampling_new(pj: dict,
                           selected_observations: list,
                           parameters_obs: dict,
                           time_interval: float):

    t1 = time.time()

    results_df = {}

    state_behavior_codes = [x for x in utilities.state_behavior_codes(pj[ETHOGRAM]) if x in parameters_obs[SELECTED_BEHAVIORS]]

    n_rows = int((parameters_obs[END_TIME] - parameters_obs[START_TIME]) / time_interval) + 1

    for obs_id in selected_observations:
        if obs_id not in results_df:
          results_df[obs_id] = {}

        for subject in parameters_obs[SELECTED_SUBJECTS]:

            if parameters_obs[INCLUDE_MODIFIERS]:
                behav_modif_list = [(idx[2], idx[3]) for idx in pj[OBSERVATIONS][obs_id][EVENTS] if idx[1] == subject]
                # add selected behavior if not found in (behavior, modifier)
                for behav in parameters_obs[SELECTED_BEHAVIORS]:
                    if behav not in [x[0] for x in behav_modif_list]:
                        behav_modif_list.append((behav, ""))
                behav_modif_set = set(sorted(behav_modif_list))

                print(behav_modif_set)

                results_df[obs_id][subject] = pd.DataFrame(index=range(n_rows), columns=["time"] + [f"{x[0]} ({x[1]})" for x in behav_modif_set])
            else:
                results_df[obs_id][subject] = pd.DataFrame(index=range(n_rows), columns=["time"] + parameters_obs[SELECTED_BEHAVIORS])


        sel_subject_dict = dict([(idx, pj[SUBJECTS][idx]) for idx in pj[SUBJECTS]
                                                              if pj[SUBJECTS][idx]["name"] in parameters_obs[SELECTED_SUBJECTS]])



        row_idx = 0
        t = parameters_obs[START_TIME]
        while t < parameters_obs[END_TIME]:

            current_states = utilities.get_current_states_modifiers_by_subject(state_behavior_codes,
                                                                         pj[OBSERVATIONS][obs_id][EVENTS],
                                                                         sel_subject_dict,
                                                                         t,
                                                                         include_modifiers=parameters_obs[INCLUDE_MODIFIERS])

            print(current_states)

            for subject_idx in current_states:
                l = [float(t)]
                for behav in parameters_obs[SELECTED_BEHAVIORS]:
                    l.append(int(behav in current_states[subject_idx]))
                results_df[obs_id][pj[SUBJECTS][subject_idx]["name"]].loc[row_idx] = l

            t += time_interval
            row_idx += 1

    print(time.time() - t1)
    return results_df
'''


def instantaneous_sampling(pj: dict,
                           selected_observations: list,
                           parameters_obs: dict,
                           time_interval: float):

    print(parameters_obs[SELECTED_SUBJECTS])

    t1 = time.time()

    results_df = {}

    state_behavior_codes = [x for x in utilities.state_behavior_codes(pj[ETHOGRAM]) if x in parameters_obs[SELECTED_BEHAVIORS]]

    n_rows = int((parameters_obs[END_TIME] - parameters_obs[START_TIME]) / time_interval) + 1

    for obs_id in selected_observations:

        if obs_id not in results_df:
            results_df[obs_id] = {}

        for subject in parameters_obs[SELECTED_SUBJECTS]:

            # extract tuple (behavior, modifier)
            behav_modif_list = [(idx[2], idx[3])
                                for idx in pj[OBSERVATIONS][obs_id][EVENTS] if idx[1] == (subject if subject != NO_FOCAL_SUBJECT else "")]

            # add selected behavior if not found in (behavior, modifier)
            if not parameters_obs[EXCLUDE_BEHAVIORS]:
                for behav in parameters_obs[SELECTED_BEHAVIORS]:
                    if behav not in [x[0] for x in behav_modif_list]:
                        behav_modif_list.append((behav, ""))

            behav_modif_set = set(behav_modif_list)

            if parameters_obs[INCLUDE_MODIFIERS]:
                results_df[obs_id][subject] = pd.DataFrame(index=range(n_rows),
                                                           columns=["time"] + [f"{x[0]}" + f" ({x[1]})" * (x[1] != "")
                                                                               for x in sorted(behav_modif_set)])
            else:
                results_df[obs_id][subject] = pd.DataFrame(index=range(n_rows),
                                                           columns=["time"] + [x[0] for x in sorted(behav_modif_set)])

            #  print(results_df[obs_id][subject].columns)

            if subject == NO_FOCAL_SUBJECT:
                sel_subject_dict = {"": {SUBJECT_NAME: ""}}
            else:
                sel_subject_dict = dict([(idx, pj[SUBJECTS][idx]) for idx in pj[SUBJECTS] if pj[SUBJECTS][idx][SUBJECT_NAME] == subject])

            row_idx = 0
            t = parameters_obs[START_TIME]
            while t < parameters_obs[END_TIME]:

                current_states = utilities.get_current_states_modifiers_by_subject(state_behavior_codes,
                                                                                   pj[OBSERVATIONS][obs_id][EVENTS],
                                                                                   sel_subject_dict,
                                                                                   t,
                                                                                   include_modifiers=parameters_obs[INCLUDE_MODIFIERS])

                cols = [float(t)]  # time

                #  print(current_states)

                for behav in list(results_df[obs_id][subject].columns)[1:]:  # skip time
                    cols.append(int(behav in current_states[list(current_states.keys())[0]]))

                results_df[obs_id][subject].loc[row_idx] = cols

                t += time_interval
                row_idx += 1

    print(time.time() - t1)
    return results_df
