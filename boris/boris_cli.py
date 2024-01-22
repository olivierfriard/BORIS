"""
BORIS CLI

Behavioral Observation Research Interactive Software Command Line Interface

Copyright 2012-2024 Olivier Friard

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
import pathlib
import utilities
import project_functions
from config import *
import db_functions
import export_observation
import irr
import plot_events
import version

__version__ = version.__version__
__version_date__ = version.__version_date__


def cleanhtml(raw_html):
    raw_html = raw_html.replace("<br>", "\n")
    cleanr = re.compile("<.*?>")
    cleantext = re.sub(cleanr, "", raw_html)
    return cleantext


def all_observations(pj):
    return [idx for idx in sorted(pj[OBSERVATIONS])]


commands_list = ["check_state_events", "export_events", "irr", "subtitles", "check_project_integrity", "plot_events"]
commands_usage = {
    "check_state_events": (
        "usage:\nboris_cli -p PROJECT_FILE -o OBSERVATION_ID --command check_state_events\n"
        "where\n"
        "PROJECT_FILE is the path of the BORIS project\n"
        "OBSERVATION_ID is the id of observation(s) (if ommitted all observations are checked)"
    ),
    "export_events": (
        "usage:\nboris_cli -p PROJECT_FILE -o OBSERVATION_ID --command export_events [OUTPUT_FORMAT]\n"
        "where:\n"
        "PROJECT_FILE is the path of the BORIS project\n"
        "OBSERVATION_ID is the id of observation(s) (if ommitted all observations are exported)\n"
        "OUTPUT_FORMAT can be tsv (default), csv, xls, xlsx, ods, html"
    ),
    "irr": (
        'usage:\nboris_cli -p PROJECT_FILE -o "OBSERVATION_ID1" "OBSERVATION_ID2" --command irr [INTERVAL] [INCLUDE_MODIFIERS]\n'
        "where:\n"
        "PROJECT_FILE is the path of the BORIS project\n"
        "INTERVAL in seconds (default is 1)\n"
        "INCLUDE_MODIFIERS must be true or false (default is true)"
    ),
    "subtitles": (
        'usage:\nboris_cli -p PROJECT_FILE -o "OBSERVATION_ID" --command subtitles [OUTPUT_DIRECTORY]\n'
        "where:\n"
        "OUTPUT_DIRECTORY is the directory where subtitles files will be saved"
    ),
    "check_project_integrity": "usage:\nboris_cli -p PROJECT_FILE --command check_project_integrity",
    "plot_events": (
        "usage:\nboris_cli - p PROJECT_FILE -o OBSERVATION_ID --command plot_events "
        "[OUTPUT_DIRECTORY] [INCLUDE_MODIFIERS] [EXCLUDE_BEHAVIORS] [PLOT_FORMAT]\n"
        "where\n"
        "OUTPUT_DIRECTORY is the directory where the plots will be saved\n"
        "INCLUDE_MODIFIERS must be true or false (default is true)\n"
        "EXCLUDE_BEHAVIORS: True: behaviors without events are not plotted (default is true)\n"
        "PLOT_FORMAT can be png, svg, pdf, ps"
    ),
}

parser = argparse.ArgumentParser(description="BORIS CLI")
parser.add_argument("-v", "--version", action="store_true", dest="version", help="BORIS version")
parser.add_argument("-p", "--project", action="store", dest="project_file", help="Project file path")
parser.add_argument("-o", "--observation", nargs="*", action="store", default=[], dest="observation_id", help="Observation id")
parser.add_argument("-i", "--info", action="store_true", dest="project_info", help="Project information")
parser.add_argument("-c", "--command", nargs="*", action="store", dest="command", help="Command to execute")

args = parser.parse_args()

pj, observations_id_list = {}, {}

if args.version:
    print("version {}".format(__version__))
    sys.exit()

if args.command:
    if args.command[0].upper() == "LIST":
        for command in commands_list:
            print(command)
            print("=" * len(command))
            if command in commands_usage:
                print(commands_usage[command])
            print()
        print()
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
    """
    if not args.command:
        print("\nObservations:")
        for observation_id in observations_id_list:
            if observation_id in pj[OBSERVATIONS]:
                print("Id: {}".format(observation_id))
            else:
                print("{}: NOT FOUND in project".format(observation_id))
        print()
    """

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
                    print(
                        "Code: {}\tDescription: {}\tType: {}".format(
                            pj[ETHOGRAM][idx][BEHAVIOR_CODE], pj[ETHOGRAM][idx]["description"], pj[ETHOGRAM][idx][TYPE]
                        )
                    )
                """print("Behaviors: {}".format(",".join([pj[ETHOGRAM][k]["code"] for k in utilities.sorted_keys(pj[ETHOGRAM])])))"""
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

    if "check_state_events" in args.command:
        if not observations_id_list:
            print("No observation selected. Command applied on all observations found in project\n")
            observations_id_list = all_observations(pj)

        for observation_id in observations_id_list:
            ret, msg = project_functions.check_state_events_obs(observation_id, pj[ETHOGRAM], pj[OBSERVATIONS][observation_id], HHMMSS)
            print("{}: {}".format(observation_id, cleanhtml(msg)))
        sys.exit()

    if "export_events" in args.command:
        if not observations_id_list:
            print("No observation selected. Command applied on all observations found in project\n")
            observations_id_list = [idx for idx in pj[OBSERVATIONS]]

        behaviors = [pj[ETHOGRAM][k]["code"] for k in utilities.sorted_keys(pj[ETHOGRAM])]
        subjects = [pj[SUBJECTS][k]["name"] for k in utilities.sorted_keys(pj[SUBJECTS])] + [NO_FOCAL_SUBJECT]

        output_format = "tsv"
        if len(args.command) > 1:
            output_format = args.command[1]

        for observation_id in observations_id_list:
            ok, msg = export_observation.export_events(
                {"selected subjects": subjects, "selected behaviors": behaviors},
                observation_id,
                pj[OBSERVATIONS][observation_id],
                pj[ETHOGRAM],
                utilities.safeFileName(observation_id + "." + output_format),
                output_format,
            )
            if not ok:
                print(msg)

        sys.exit()

    if "irr" in args.command:
        if len(observations_id_list) != 2:
            print("select 2 observations")
            sys.exit()

        behaviors = [pj[ETHOGRAM][k]["code"] for k in utilities.sorted_keys(pj[ETHOGRAM])]
        subjects = [pj[SUBJECTS][k]["name"] for k in utilities.sorted_keys(pj[SUBJECTS])] + [NO_FOCAL_SUBJECT]

        ok, msg, db_connector = db_functions.load_aggregated_events_in_db(pj, subjects, observations_id_list, behaviors)

        if not ok:
            print(cleanhtml(msg))
            sys.exit()

        cursor = db_connector.cursor()

        interval = 1
        if len(args.command) > 1:
            interval = utilities.float2decimal(args.command[1])

        include_modifiers = True
        if len(args.command) > 2:
            include_modifiers = "TRUE" in args.command[2].upper()

        K, out = irr.cohen_kappa(cursor, observations_id_list[0], observations_id_list[1], interval, subjects, include_modifiers)

        print(("Cohen's Kappa - Index of Inter-Rater Reliability\n\n" "Interval time: {interval:.3f} s\n").format(interval=interval))

        print(out)
        sys.exit()

    if "subtitles" in args.command:
        if not observations_id_list:
            print("No observation selected. Command applied on all observations found in project\n")
            observations_id_list = all_observations(pj)

        behaviors = [pj[ETHOGRAM][k]["code"] for k in utilities.sorted_keys(pj[ETHOGRAM])]
        subjects = [pj[SUBJECTS][k]["name"] for k in utilities.sorted_keys(pj[SUBJECTS])] + [NO_FOCAL_SUBJECT]

        export_dir = "."
        if len(args.command) > 1:
            export_dir = args.command[1]
            if not pathlib.Path(export_dir).is_dir():
                print("{} is not a valid directory".format(export_dir))
                sys.exit()

        ok, msg = project_functions.create_subtitles(
            pj,
            observations_id_list,
            {"selected subjects": subjects, "selected behaviors": behaviors, "include modifiers": True},
            export_dir,
        )
        if not ok:
            print(cleanhtml(msg))
        sys.exit()

    if "check_project_integrity" in args.command[0]:
        msg = project_functions.check_project_integrity(pj, HHMMSS, args.project_file)
        if msg:
            print(cleanhtml(msg))
        else:
            print("No issuses found in project")
        sys.exit()

    if "plot_events" in args.command[0]:
        if not observations_id_list:
            print("No observation selected. Command applied on all observations found in project\n")
            observations_id_list = all_observations(pj)

        behaviors = [pj[ETHOGRAM][k]["code"] for k in utilities.sorted_keys(pj[ETHOGRAM])]
        subjects = [pj[SUBJECTS][k]["name"] for k in utilities.sorted_keys(pj[SUBJECTS])] + [NO_FOCAL_SUBJECT]

        export_dir = "."
        if len(args.command) > 1:
            export_dir = args.command[1]
            if not pathlib.Path(export_dir).is_dir():
                print("{} is not a valid directory".format(export_dir))
                sys.exit()

        include_modifiers = True
        if len(args.command) > 2:
            include_modifiers = "TRUE" in args.command[2].upper()

        exclude_behaviors = True
        if len(args.command) > 3:
            exclude_behaviors = False if "FALSE" in args.command[3].upper() else True

        plot_format = "png"
        if len(args.command) > 4:
            plot_format = args.command[4].lower()

        plot_events.create_events_plot(
            pj,
            observations_id_list,
            {
                "selected subjects": subjects,
                "selected behaviors": behaviors,
                "include modifiers": include_modifiers,
                "exclude behaviors": exclude_behaviors,
                "time": TIME_FULL_OBS,
                "start time": 0,
                "end time": 0,
            },
            plot_colors=BEHAVIORS_PLOT_COLORS,
            plot_directory=export_dir,
            file_format=plot_format,
        )
        sys.exit()

    print("Command {} not found!".format(args.command[0]))

print()
