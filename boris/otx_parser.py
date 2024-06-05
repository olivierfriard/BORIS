"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2024 Olivier Friard

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


Parse an OTX/ODX or OTB (compressed OTX) file and convert the ethogram, modifiers, subjects
and independent variables to BORIS format

"""

import datetime as dt
from decimal import Decimal as dec
import re
import zipfile
import pathlib as pl
from xml.dom import minidom
import logging
from typing import Tuple

try:
    from . import config as cfg
except Exception:
    import config as cfg


def otx_to_boris(file_path: str) -> Tuple[dict, list]:
    """
    convert otx/otb/odx file in a BORIS project

    For ODX files ask to import observations

    Args:
        file_path (str): path to otx/otb/odx file

    Returns:
        dict: BORIS project
        list: list of errors during importation
    """

    if pl.Path(file_path).suffix == ".otb":
        with zipfile.ZipFile(file_path) as file_zip:
            files_list = file_zip.namelist()
            if files_list:
                try:
                    file_zip.extract(files_list[0])
                except Exception:
                    return {"fatal": True}, ["Error when extracting file from OTB"]
            else:
                return {"fatal": True}, ["Error when extracting file"]

            try:
                xmldoc = minidom.parse(files_list[0])
            except Exception:
                return {"fatal": True}, ["XML parsing error"]

    elif pl.Path(file_path).suffix in (".odx", ".otx"):
        try:
            xmldoc = minidom.parse(file_path)
        except Exception:
            return {"fatal": True}, ["XML parsing error"]

    else:
        return {"fatal": True}, ["The file must be in OTB, OTX or ODX format"]

    flag_long_key: bool = False
    error_list: list = []

    # metadata
    for item in xmldoc.getElementsByTagName("MET_METADATA"):
        metadata = minidom.parseString(item.toxml())
        try:
            project_name = re.sub("<[^>]*>", "", metadata.getElementsByTagName("MET_PROJECT_NAME")[0].toxml())
        except Exception:
            project_name = ""
        try:
            project_description = re.sub("<[^>]*>", "", metadata.getElementsByTagName("MET_PROJECT_DESCRIPTION")[0].toxml())
        except Exception:
            project_description = ""

        try:
            project_creation_date = re.sub("<[^>]*>", "", metadata.getElementsByTagName("MET_CREATION_DATETIME")[0].toxml())
        except Exception:
            project_creation_date = ""

    # modifiers
    modifiers: dict = {}
    # modifiers_set = {}
    itemlist = xmldoc.getElementsByTagName("CDS_MODIFIER")
    for item in itemlist:
        modif = minidom.parseString(item.toxml())

        modif_code = re.sub("<[^>]*>", "", modif.getElementsByTagName("CDS_ELE_NAME")[0].toxml())

        modif_id = re.sub("<[^>]*>", "", modif.getElementsByTagName("CDS_ELE_ID")[0].toxml())

        try:
            modif_parent_id = re.sub("<[^>]*>", "", modif.getElementsByTagName("CDS_ELE_PARENT_ID")[0].toxml())
        except Exception:
            modif_parent_id = ""

        try:
            description = re.sub("<[^>]*>", "", modif.getElementsByTagName("CDS_ELE_DESCRIPTION")[0].toxml())
        except Exception:
            description = ""
        try:
            key = re.sub("<[^>]*>", "", modif.getElementsByTagName("CDS_ELE_START_KEYCODE")[0].toxml())
        except Exception:
            key = ""

        if modif_parent_id:
            modifiers[modif_parent_id]["values"].append(modif_code)
        else:
            if len(key) > 1:
                key = ""
                flag_long_key = True
            modifiers[modif_id] = {"set_name": modif_code, "key": key, "description": description, "values": []}

    logging.debug(modifiers)

    # connect modifiers to behaviors
    connections: dict = {}
    itemlist = xmldoc.getElementsByTagName("CDS_CONNECTION")
    for item in itemlist:
        if item.attributes["CDS_ELEMENT_ID"].value not in connections:
            connections[item.attributes["CDS_ELEMENT_ID"].value] = []
        connections[item.attributes["CDS_ELEMENT_ID"].value].append(item.attributes["CDS_MODIFIER_ID"].value)

    logging.debug(connections)

    # behaviors
    behaviors: dict = {}
    behaviors_list: list = []
    behav_category: list = []
    mutually_exclusive_list: list = []
    itemlist = xmldoc.getElementsByTagName("CDS_BEHAVIOR")
    for item in itemlist:
        behav = minidom.parseString(item.toxml())

        behav_code = re.sub("<[^>]*>", "", behav.getElementsByTagName("CDS_ELE_NAME")[0].toxml())

        behav_id = re.sub("<[^>]*>", "", behav.getElementsByTagName("CDS_ELE_ID")[0].toxml())

        try:
            description = re.sub("<[^>]*>", "", behav.getElementsByTagName("CDS_ELE_DESCRIPTION")[0].toxml())
        except Exception:
            description = ""
        try:
            key = re.sub("<[^>]*>", "", behav.getElementsByTagName("CDS_ELE_START_KEYCODE")[0].toxml())
        except Exception:
            key = ""

        try:
            stop_key = re.sub("<[^>]*>", "", behav.getElementsByTagName("CDS_ELE_STOP_KEYCODE")[0].toxml())
        except Exception:
            stop_key = ""

        try:
            parent_name = re.sub("<[^>]*>", "", behav.getElementsByTagName("CDS_ELE_PARENT_NAME")[0].toxml())
        except Exception:
            parent_name = ""

        try:
            mutually_exclusive = re.sub("<[^>]*>", "", behav.getElementsByTagName("CDS_ELE_MUT_EXCLUSIVE")[0].toxml())
        except Exception:
            mutually_exclusive = ""

        if mutually_exclusive == "Y" and parent_name:
            mutually_exclusive_list.append(behav_code)

        if behav_id in connections:
            modifier_sets = [modifiers[modifier_set]["set_name"] for modifier_set in connections[behav_id]]
        else:
            modifier_sets = []

        if parent_name:  # behavior
            if (not key or len(key) > 1) and stop_key:
                key = stop_key

            if len(key) > 1:
                key = ""
                flag_long_key = True

            behaviors[str(len(behaviors))] = {
                "id": int(behav_id),
                "code": behav_code,
                "key": key,
                "description": description,
                "modifiers": modifier_sets,
                "category": parent_name,
            }
            behaviors_list.append(behav_code)

        else:  #  behavioral category
            behav_category.append(behav_code)

    behaviors_boris: dict = {}
    for k in behaviors:
        behaviors_boris[k] = {
            "code": behaviors[k]["code"],
            "type": cfg.POINT_EVENT,
            "key": behaviors[k]["key"],
            "description": behaviors[k]["description"],
            "category": behaviors[k]["category"],
            "excluded": "",
            "coding map": "",
        }

        if behaviors[k]["code"] in mutually_exclusive_list:
            behaviors_boris[k]["excluded"] = ",".join([x for x in behaviors_list if x != behaviors[k]["code"]])

        behaviors_boris[k]["modifiers"] = {}
        if behaviors[k]["modifiers"]:
            for modif_key in modifiers:
                if modifiers[modif_key]["set_name"] in behaviors[k]["modifiers"]:
                    new_index = str(len(behaviors_boris[k]["modifiers"]))
                    behaviors_boris[k]["modifiers"][new_index] = {
                        "name": modifiers[modif_key]["set_name"],
                        "type": cfg.SINGLE_SELECTION,
                        "values": modifiers[modif_key]["values"],
                        "description": modifiers[modif_key]["description"],
                    }

    logging.debug(behaviors_boris)

    # subjects
    subjects = {}
    itemlist = xmldoc.getElementsByTagName("CDS_SUBJECT")
    for item in itemlist:
        subject = minidom.parseString(item.toxml())
        subject_name = re.sub("<[^>]*>", "", subject.getElementsByTagName("CDS_ELE_NAME")[0].toxml())
        try:
            key = re.sub("<[^>]*>", "", subject.getElementsByTagName("CDS_ELE_START_KEYCODE")[0].toxml())
        except Exception:
            key = ""
        try:
            parent_name = re.sub("<[^>]*>", "", subject.getElementsByTagName("CDS_ELE_PARENT_NAME")[0].toxml())
        except Exception:
            parent_name = ""

        if parent_name:
            if len(key) > 1:
                key = ""
                flag_long_key = True
            subjects[str(len(subjects))] = {"key": key, "name": subject_name, "description": ""}

    # independent variables
    variables = {}
    itemlist = xmldoc.getElementsByTagName("VL_VARIABLE")
    for item in itemlist:
        variable = minidom.parseString(item.toxml())

        variable_label = re.sub("<[^>]*>", "", variable.getElementsByTagName("VL_LABEL")[0].toxml())

        variable_id = re.sub("<[^>]*>", "", variable.getElementsByTagName("VL_ID")[0].toxml())

        variable_type = re.sub("<[^>]*>", "", variable.getElementsByTagName("VL_TYPE")[0].toxml())
        if variable_type.upper() == "TEXT":
            variable_type = cfg.TEXT
        if variable_type.upper() == "DOUBLE":
            variable_type = cfg.NUMERIC
        if variable_type.upper() == "FILEREFERENCE":
            variable_type = cfg.TEXT
        if variable_type.upper() == "DURATION":
            variable_type = cfg.TEXT
        if variable_type.upper() == "TIMESTAMP":
            variable_type = cfg.TIMESTAMP
        if variable_type.upper() == "BOOLEAN":
            variable_type = cfg.TEXT

        try:
            variable_description = re.sub("<[^>]*>", "", modif.getElementsByTagName("VL_DESCRIPTION")[0].toxml())
        except Exception:
            variable_description = ""

        try:
            values = variable.getElementsByTagName("VL_VALUE")
            values_list = []
            for value in values:
                values_list.append(re.sub("<[^>]*>", "", value.toxml()))
            values_str = ",".join(values_list)

        except Exception:
            values_str = ""

        variables[variable_id] = {
            "label": variable_label,
            "type": variable_type.lower(),
            "description": variable_description,
        }
        if values_str:
            variables[variable_id]["predefined_values"] = values_str
            variables[variable_id]["type"] = "value from set"

    variables_boris = {}
    for k in variables:
        variables_boris[k] = {
            "label": variables[k]["label"],
            "description": variables[k]["description"],
            "type": variables[k]["type"],
            "default value": "",
            "possible values": variables[k]["predefined_values"] if "predefined_values" in variables[k] else "",
        }

    # create empty project from template
    project = dict(cfg.EMPTY_PROJECT)
    project[cfg.OBSERVATIONS] = {}

    observations = xmldoc.getElementsByTagName("OBS_OBSERVATION")

    for OBS_OBSERVATION in observations:
        # OBS_OBSERVATION = minidom.parseString(OBS_OBSERVATION.toxml())

        obs_id = OBS_OBSERVATION.getAttribute("NAME")

        project[cfg.OBSERVATIONS][obs_id] = dict(
            {
                "file": {},
                "type": "LIVE",
                "description": "",
                "time offset": 0,
                cfg.EVENTS: [],
                "observation time interval": [0, 0],
                "independent_variables": {},
                "visualize_spectrogram": False,
                "visualize_waveform": False,
                "close_behaviors_between_videos": False,
                "scan_sampling_time": 0,
                "start_from_current_time": False,
                "start_from_current_epoch_time": False,
            }
        )

        OBS_EVENT_LOGS = OBS_OBSERVATION.getElementsByTagName("OBS_EVENT_LOGS")[0]

        for OBS_EVENT_LOG in OBS_EVENT_LOGS.getElementsByTagName("OBS_EVENT_LOG"):
            CREATION_DATETIME = OBS_EVENT_LOG.getAttribute("CREATION_DATETIME")

            CREATION_DATETIME = CREATION_DATETIME.replace(" ", "T")  # .split(".")[0]

            logging.debug(f"{CREATION_DATETIME=}")  # ex: 2022-05-18 10:04:09.474512"""

            project[cfg.OBSERVATIONS][obs_id]["date"] = CREATION_DATETIME

            for event in OBS_EVENT_LOG.getElementsByTagName("OBS_EVENT"):
                OBS_EVENT_TIMESTAMP = event.getElementsByTagName("OBS_EVENT_TIMESTAMP")[0].childNodes[0].data

                full_timestamp = dt.datetime.strptime(OBS_EVENT_TIMESTAMP, "%Y-%m-%d %H:%M:%S.%f").timestamp()
                logging.debug(f"{full_timestamp=}")

                # day_timestamp = dt.datetime.strptime(OBS_EVENT_TIMESTAMP.split(" ")[0], "%Y-%m-%d").timestamp()
                # timestamp = dec(str(round(full_timestamp - day_timestamp, 3)))
                timestamp = dec(full_timestamp).quantize(dec(".001"))

                try:
                    OBS_EVENT_SUBJECT = event.getElementsByTagName("OBS_EVENT_SUBJECT")[0].getAttribute("NAME")
                except Exception:
                    OBS_EVENT_SUBJECT = ""

                OBS_EVENT_BEHAVIOR = event.getElementsByTagName("OBS_EVENT_BEHAVIOR")[0].getAttribute("NAME")
                logging.debug(f"{OBS_EVENT_BEHAVIOR=}")
                if not OBS_EVENT_BEHAVIOR:
                    logging.warning(f"Behavior missing in observation {obs_id} at {timestamp}")
                    error_list.append(f"Behavior missing in observation {obs_id} at {timestamp}")
                    continue

                # modifier
                try:
                    OBS_EVENT_BEHAVIOR_MODIFIER = (
                        event.getElementsByTagName("OBS_EVENT_BEHAVIOR")[0]
                        .getElementsByTagName("OBS_EVENT_BEHAVIOR_MODIFIER")[0]
                        .childNodes[0]
                        .data
                    )
                except Exception:
                    OBS_EVENT_BEHAVIOR_MODIFIER: str = ""

                # comment
                try:
                    OBS_EVENT_COMMENT: str = event.getElementsByTagName("OBS_EVENT_COMMENT")[0].childNodes[0].data
                except Exception:
                    OBS_EVENT_COMMENT: str = ""

                logging.debug(f"{timestamp=}")
                logging.debug(f"{OBS_EVENT_SUBJECT=}")
                logging.debug(f"{OBS_EVENT_BEHAVIOR=}")
                logging.debug(f"{OBS_EVENT_BEHAVIOR_MODIFIER=}")
                logging.debug(f"{OBS_EVENT_COMMENT=}")

                project[cfg.OBSERVATIONS][obs_id][cfg.EVENTS].append(
                    [
                        timestamp,
                        OBS_EVENT_SUBJECT,
                        OBS_EVENT_BEHAVIOR,
                        OBS_EVENT_BEHAVIOR_MODIFIER,
                        OBS_EVENT_COMMENT,
                    ]
                )

    project[cfg.PROJECT_NAME] = project_name
    project[cfg.PROJECT_DATE] = project_creation_date.replace(" ", "T")
    project[cfg.ETHOGRAM] = behaviors_boris
    project[cfg.PROJECT_DESCRIPTION] = project_description
    project[cfg.BEHAVIORAL_CATEGORIES] = behav_category
    project[cfg.SUBJECTS] = subjects
    project[cfg.INDEPENDENT_VARIABLES] = variables_boris

    if flag_long_key:
        error_list.append("The keys longer than one char were deleted.")
        logging.debug("The keys longer than one char were deleted.")

    return project, error_list


if __name__ == "__main__":
    import sys
    import pprint

    logging.basicConfig(
        format="%(asctime)s,%(msecs)d  %(module)s l.%(lineno)d %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        level=logging.DEBUG,
    )
    project, errors = otx_to_boris(sys.argv[1])

    pprint.pprint(project)
    pprint.pprint(errors)
