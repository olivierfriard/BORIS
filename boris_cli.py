"""
BORIS CLI

Behavioral Observation Research Interactive Software Command Line Interface

Copyright 2012-2018 Olivier Friard

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

import argparse
import sys
import utilities
import project_functions
from config import *
import db_functions
import irr

__version__ = "6.0.6"

parser = argparse.ArgumentParser(description="BORIS CLI")
parser.add_argument("-v", "--version", action="store_true", dest='version', help='BORIS version')

parser.add_argument("-p", "--project", action="store", dest='project_file', help='Project file path')

parser.add_argument("-o", "--observation", nargs = '*', action="store", default=[], dest='observation_id', help='Observation id')

parser.add_argument("--info", action="store_true", dest='project_info', help='Project information')

parser.add_argument("--command", nargs = '*', action="store", dest='command', help='Command to execute')

args = parser.parse_args()

pj = {}
observations_id_list = []

if args.version:
    print("version {}".format(__version__))
    sys.exit()

if args.project_file:

    print("Project path: {}".format(args.project_file))

    project_path, project_changed, pj, msg = project_functions.open_project_json(args.project_file)
    if "error" in pj:
        print(pj["error"])
        sys.exit()
    if msg:
        print(msg)

if args.observation_id:
    print("\nObservations id:")
    observations_id_list = args.observation_id
    for observation_id in observations_id_list:
        if observation_id in pj[OBSERVATIONS]:
            print("{}".format(observation_id))
        else:
            print("{}: NOT FOUND in project".format(observation_id))
    print()

if args.project_info:
    if pj:
        print("Project name: {}".format(pj[PROJECT_NAME]))
        print("Project date: {}".format(pj[PROJECT_DATE]))
        print("Project description: {}".format(pj[PROJECT_DESCRIPTION]))
        print()

        if not observations_id_list:
            print("Ethogram\n========")
            print("Number of behaviors in ethogram: {}".format(len(pj[ETHOGRAM])))
            print("Behaviors: {}".format(",".join([pj[ETHOGRAM][k]["code"] for k in utilities.sorted_keys(pj[ETHOGRAM])])))
            print()
            print("Number of subjects: {}".format(len(pj[SUBJECTS])))
            for idx in utilities.sorted_keys(pj[SUBJECTS]):
                print("Name: {}\tDescription: {}".format(pj[SUBJECTS][idx]["name"], pj[SUBJECTS][idx]["description"]))
            #print("Subjects: {}".format(",".join([pj[SUBJECTS][k]["name"] for k in utilities.sorted_keys(pj[SUBJECTS])])))
            print()
            print("Number of observations: {}".format(len(pj[OBSERVATIONS])))
            print("List of observations:")
            for observation_id in sorted(pj[OBSERVATIONS].keys()):
                print(observation_id)
            #print("Observations' id: {}".format(",".join(sorted(pj[OBSERVATIONS].keys()))))
        else:
            for observation_id in observations_id_list:
                print("Observation id: {}".format(observation_id))
                if pj[OBSERVATIONS][observation_id][EVENTS]:
                    print("\n".join([str(x) for x in pj[OBSERVATIONS][observation_id][EVENTS]]))
                else:
                    print("No events recorded")
    else:
        print("No project")
    sys.exit()




if args.command:
    
    print("Command: {}\n".format(args.command))
    
    if not pj:
        print("No project")
        sys.exit()
    if not observations_id_list:
        print("No observation")
        sys.exit()
    
    if "check_state_events" in args.command:
        print("Check state events:")
        for observation_id in observations_id_list:
            ret, msg = project_functions.check_state_events_obs(pj, observation_id)
            print("{}: {}".format(observation_id, msg))
        sys.exit()


    if "irr" in args.command:
        if len(observations_id_list) != 2:
            print("select 2 observations")
            sys.exit()

        behaviors = [pj[ETHOGRAM][k]["code"] for k in utilities.sorted_keys(pj[ETHOGRAM])]
        subjects = [pj[SUBJECTS][k]["name"] for k in utilities.sorted_keys(pj[SUBJECTS])] + [NO_FOCAL_SUBJECT]
        
        cursor = db_functions.load_aggregated_events_in_db(pj,
                                                           subjects,
                                                           observations_id_list,
                                                           behaviors).cursor()
        if len(args.command) > 1:
            interval = utilities.float2decimal(args.command[1])

        include_modifiers = True
        if len(args.command) > 2:
            include_modifiers =  "TRUE" in args.command[2].upper()

        K, out = irr.cohen_kappa(cursor,
                                  observations_id_list[0], observations_id_list[1],
                                  interval,
                                  subjects,
                                  include_modifiers)
        print(out)
        sys.exit()
