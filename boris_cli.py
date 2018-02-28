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
import re
import utilities
import project_functions
from config import *
import db_functions
import export_observation
import irr



__version__ = "6.1"
__version_date__ = "2018-02-23"

def cleanhtml(raw_html):
    raw_html = raw_html.replace("<br>", "\n")
    cleanr = re.compile("<.*?>")
    cleantext = re.sub(cleanr, "", raw_html)
    return cleantext

commands_list = ["check_state_events", "export_events", "irr", "subtitles"]

parser = argparse.ArgumentParser(description="BORIS CLI")
parser.add_argument("-v", "--version", action="store_true", dest='version', help='BORIS version')

parser.add_argument("-p", "--project", action="store", dest='project_file', help='Project file path')

parser.add_argument("-o", "--observation", nargs = '*', action="store", default=[], dest='observation_id', help='Observation id')

parser.add_argument("-i", "--info", action="store_true", dest='project_info', help='Project information')

parser.add_argument("--command", nargs = '*', action="store", dest='command', help='Command to execute')

args = parser.parse_args()

pj = {}
observations_id_list = []

if args.version:
    print("version {}".format(__version__))
    sys.exit()

if args.project_file:

    if not args.command:
        print("Project path: {}".format(args.project_file))

    project_path, project_changed, pj, msg = project_functions.open_project_json(args.project_file)
    if "error" in pj:
        print(pj["error"])
        sys.exit()
    if msg:
        print(msg)

if args.observation_id:
    observations_id_list = args.observation_id

    if not args.command:
        print("\nObservations:")
        for observation_id in observations_id_list:
            if observation_id in pj[OBSERVATIONS]:
                print("Id: {}".format(observation_id))
            else:
                print("{}: NOT FOUND in project".format(observation_id))
        print()

if args.project_info:
    if not args.command:
        if pj:
            print("Project name: {}".format(pj[PROJECT_NAME]))
            print("Project date: {}".format(pj[PROJECT_DATE]))
            print("Project description: {}".format(pj[PROJECT_DESCRIPTION]))
            print()
    
            if not observations_id_list:
                print("Ethogram\n========")
                print("Number of behaviors in ethogram: {}".format(len(pj[ETHOGRAM])))
                for idx in utilities.sorted_keys(pj[ETHOGRAM]):
                    print("Code: {}\tDescription: {}\tType: {}".format(pj[ETHOGRAM][idx][BEHAVIOR_CODE],
                                                                       pj[ETHOGRAM][idx]["description"],
                                                                       pj[ETHOGRAM][idx][TYPE]
                                                                       ))
                '''print("Behaviors: {}".format(",".join([pj[ETHOGRAM][k]["code"] for k in utilities.sorted_keys(pj[ETHOGRAM])])))'''
                print()
                
                print("Subjects\n========")
                print("Number of subjects: {}".format(len(pj[SUBJECTS])))
                for idx in utilities.sorted_keys(pj[SUBJECTS]):
                    print("Name: {}\tDescription: {}".format(pj[SUBJECTS][idx]["name"], pj[SUBJECTS][idx]["description"]))
                print()

                print("Observations\n============")
                print("Number of observations: {}".format(len(pj[OBSERVATIONS])))
                print("List of observations:")
                for observation_id in sorted(pj[OBSERVATIONS].keys()):
                    print("Id: {}\tDate: {}".format(observation_id, pj[OBSERVATIONS][observation_id]["date"]))
                #print("Observations' id: {}".format(",".join(sorted(pj[OBSERVATIONS].keys()))))
            else:
                for observation_id in observations_id_list:
                    print("Observation id: {}".format(observation_id))
                    if pj[OBSERVATIONS][observation_id][EVENTS]:
                        
                        for event in pj[OBSERVATIONS][observation_id][EVENTS]:
                            print("\t".join([str(x) for x in event]))
                    else:
                        print("No events recorded")
                    print()
        else:
            print("No project")
        sys.exit()



if args.command:

    print("Command: {}\n".format(" ".join(args.command)))
    
    if not pj:
        print("No project")
        sys.exit()

    if not observations_id_list:
        print("No observation")
        sys.exit()
    
    if "check_state_events" in args.command:
        for observation_id in observations_id_list:
            ret, msg = project_functions.check_state_events_obs(observation_id, pj[ETHOGRAM], pj[OBSERVATIONS][observation_id], HHMMSS)
            print("{}: {}".format(observation_id, cleanhtml(msg)))
        sys.exit()

    if "export_events" in args.command:
        behaviors = [pj[ETHOGRAM][k]["code"] for k in utilities.sorted_keys(pj[ETHOGRAM])]
        subjects = [pj[SUBJECTS][k]["name"] for k in utilities.sorted_keys(pj[SUBJECTS])] + [NO_FOCAL_SUBJECT]

        output_format = "tsv"
        if len(args.command) > 1:
            output_format = args.command[1]
        
        for observation_id in observations_id_list:
            ok, msg = export_observation.export_events({"selected subjects": subjects,
                                              "selected behaviors": behaviors},
                                              observation_id,
                                              pj[OBSERVATIONS][observation_id],
                                              pj[ETHOGRAM],
                                              utilities.safeFileName(observation_id + "." + output_format),
                                              output_format)
            if not ok:
                print(msg)
            
        sys.exit()


    if "irr" in args.command:
        if len(observations_id_list) != 2:
            print("select 2 observations")
            sys.exit()

        behaviors = [pj[ETHOGRAM][k]["code"] for k in utilities.sorted_keys(pj[ETHOGRAM])]
        subjects = [pj[SUBJECTS][k]["name"] for k in utilities.sorted_keys(pj[SUBJECTS])] + [NO_FOCAL_SUBJECT]
        
        ok, msg, db_connector = db_functions.load_aggregated_events_in_db(pj,
                                                           subjects,
                                                           observations_id_list,
                                                           behaviors)

        if not ok:
            print(cleanhtml(msg))
            sys.exit()

        cursor = db_connector.cursor()

        interval = 1
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

        print(("Cohen's Kappa - Index of Inter-Rater Reliability\n\n"
              "Interval time: {interval:.3f} s\n").format(interval=interval))

        print(out)
        sys.exit()

    if "subtitles" in args.command:
        behaviors = [pj[ETHOGRAM][k]["code"] for k in utilities.sorted_keys(pj[ETHOGRAM])]
        subjects = [pj[SUBJECTS][k]["name"] for k in utilities.sorted_keys(pj[SUBJECTS])] + [NO_FOCAL_SUBJECT]

        export_dir = "."
        if len(args.command) > 1:
            export_dir = args.command[1]

        ok, msg = project_functions.create_subtitles(pj,
                                           observations_id_list,
                                           {"selected subjects": subjects,
                                           "selected behaviors": behaviors,
                                           "include modifiers": True},
                                           export_dir)
        if not ok:
            print(cleanhtml(msg))
        sys.exit()

    if "list" in args.command:
        print("Available commands:\n{}".format("\n".join(commands_list)))
        sys.exit()

    print("Command not found")
    
    
    
