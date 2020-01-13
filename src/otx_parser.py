"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2020 Olivier Friard

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


Parse an OTX or OTB (compressed OTX) file and convert the ethogram, modifiers, subjects
and independent variables to BORIS format
"""

import re
import zipfile
from xml.dom import minidom


def otx_to_boris(file_path: str) -> dict:
    """
    convert otx/otb file in a BORIS project

    Args:
        file_path (str): path to otx/otb file

    Returns:
        dict: BORIS project
    """

    # check file if compressed (otb)
    if ".otb" in file_path:
        with zipfile.ZipFile(file_path) as file_zip:
            files_list = file_zip.namelist()
            if files_list:
                try:
                    file_zip.extract(files_list[0])
                except:
                    return {"error": "error when extracting file"}
            else:
                return {"error": "error when extracting file"}

            try:
                xmldoc = minidom.parse(files_list[0])
            except:
                return {"error": "parsing error"}

    elif ".otx" in file_path:
        try:
            xmldoc = minidom.parse(file_path)
        except:
            return {"error": "parsing error"}

    else:
        return {"error": "file must be .otb or .otx"}

    flag_long_key = False

    # metadata
    itemlist = xmldoc.getElementsByTagName('MET_METADATA')
    for item in itemlist:
        metadata = minidom.parseString(item.toxml())
        try:
            project_name = re.sub('<[^>]*>', '', metadata.getElementsByTagName('MET_PROJECT_NAME')[0].toxml())
        except Exception:
            project_name = ""
        try:
            project_description = re.sub('<[^>]*>', '', metadata.getElementsByTagName('MET_PROJECT_DESCRIPTION')[0].toxml())
        except Exception:
            project_description = ""

        try:
            project_creation_date = re.sub('<[^>]*>', '', metadata.getElementsByTagName('MET_CREATION_DATETIME')[0].toxml())
        except Exception:
            project_creation_date = ""

    modifiers = {}
    modifiers_set = {}

    itemlist = xmldoc.getElementsByTagName('CDS_MODIFIER')

    for item in itemlist:
        modif = minidom.parseString(item.toxml())

        modif_code = re.sub('<[^>]*>', '', modif.getElementsByTagName('CDS_ELE_NAME')[0].toxml())

        modif_id = re.sub('<[^>]*>', '', modif.getElementsByTagName('CDS_ELE_ID')[0].toxml())

        try:
            modif_parent_id = re.sub('<[^>]*>', '', modif.getElementsByTagName('CDS_ELE_PARENT_ID')[0].toxml())

        except:
            modif_parent_id = ""

        try:
            description = re.sub('<[^>]*>', '', modif.getElementsByTagName('CDS_ELE_DESCRIPTION')[0].toxml())
        except:
            description = ""
        try:
            key = re.sub('<[^>]*>', '',modif.getElementsByTagName('CDS_ELE_START_KEYCODE')[0].toxml())
        except:
            key = ""

        if modif_parent_id:
            modifiers[modif_parent_id]["values"].append(modif_code)
        else:
            if len(key) > 1:
                key = ""
                flag_long_key = True
            modifiers[modif_id] = { "set_name": modif_code, "key": key, "description": description, "values": []}


    connections = {}
    itemlist = xmldoc.getElementsByTagName('CDS_CONNECTION')

    for item in itemlist:
        connections[ item.attributes['CDS_ELEMENT_ID'].value ] =  item.attributes['CDS_MODIFIER_ID'].value

    # behaviors
    behaviors = {}
    behaviors_list = []
    behav_category = []
    mutually_exclusive_list = []

    itemlist = xmldoc.getElementsByTagName('CDS_BEHAVIOR')

    for item in itemlist:
        behav = minidom.parseString(item.toxml())

        behav_code = re.sub('<[^>]*>', '', behav.getElementsByTagName('CDS_ELE_NAME')[0].toxml())

        behav_id = re.sub('<[^>]*>', '', behav.getElementsByTagName('CDS_ELE_ID')[0].toxml())

        try:
            description = re.sub('<[^>]*>', '', behav.getElementsByTagName('CDS_ELE_DESCRIPTION')[0].toxml())
        except:
            description = ""
        try:
            key = re.sub('<[^>]*>', '',behav.getElementsByTagName('CDS_ELE_START_KEYCODE')[0].toxml())
        except:
            key = ""

        try:
            parent_name = re.sub('<[^>]*>', '',behav.getElementsByTagName('CDS_ELE_PARENT_NAME')[0].toxml())
        except:
            parent_name = ""

        try:
            mutually_exclusive = re.sub('<[^>]*>', '',behav.getElementsByTagName('CDS_ELE_MUT_EXCLUSIVE')[0].toxml())
        except:
            mutually_exclusive = ""

        if mutually_exclusive == "Y" and parent_name:
            mutually_exclusive_list.append(behav_code)

        if behav_id in connections:
            modifiers_ = modifiers[ connections[ behav_id ] ]["set_name"]
        else:
            modifiers_ = ""

        if parent_name:

            if len(key) > 1:
                key = ""
                flag_long_key = True

            behaviors[str(len(behaviors))] = {"id": int(behav_id),"code": behav_code,
                      "key": key, "description": description, "modifiers": modifiers_,
                      "category": parent_name}
            behaviors_list.append(behav_code)
        else:
            behav_category.append(behav_code)

    behaviors_boris = {}
    for k in behaviors:
        behaviors_boris[k] = {"code": behaviors[k]["code"],
                              "type": "State event",
                              "key": behaviors[k]["key"],
                              "description": behaviors[k]["key"],
                              "category": behaviors[k]["category"],
                              "excluded":"",
                              "coding map":""
                             }

        if behaviors[k]["code"] in mutually_exclusive_list:
            behaviors_boris[k]["excluded"] = ",".join([x for x in behaviors_list if x != behaviors[k]["code"]])

        if behaviors[k]["modifiers"]:
            for modif_key in modifiers:
                if modifiers[modif_key]["set_name"] == behaviors[k]["modifiers"]:
                    behaviors_boris[k]["modifiers"] = {"0": {"name": behaviors[k]["modifiers"],
                                                             "type": 0,
                                                             "values": modifiers[modif_key]["values"]
                                                            }
                                                      }
        else:
            behaviors_boris[k]["modifiers"] = {}


    # subjects
    subjects = {}
    itemlist = xmldoc.getElementsByTagName("CDS_SUBJECT")
    for item in itemlist:
        subject = minidom.parseString(item.toxml())
        subject_name = re.sub('<[^>]*>', '', subject.getElementsByTagName("CDS_ELE_NAME")[0].toxml())
        try:
            key = re.sub('<[^>]*>', '', subject.getElementsByTagName("CDS_ELE_START_KEYCODE")[0].toxml())
        except:
            key = ""
        try:
            parent_name = re.sub("<[^>]*>", "",subject.getElementsByTagName("CDS_ELE_PARENT_NAME")[0].toxml())
        except:
            parent_name = ""

        if parent_name:
            if len(key) > 1:
                key = ""
                flag_long_key = True
            subjects[str(len(subjects))] = {"key": key,
                                            "name": subject_name,
                                            "description": ""
                                            }


    # independent variables
    variables = {}
    itemlist = xmldoc.getElementsByTagName("VL_VARIABLE")

    for item in itemlist:

        variable = minidom.parseString(item.toxml())

        variable_label = re.sub('<[^>]*>', '', variable.getElementsByTagName('VL_LABEL')[0].toxml())

        variable_id = re.sub('<[^>]*>', '', variable.getElementsByTagName('VL_ID')[0].toxml())

        variable_type = re.sub('<[^>]*>', '', variable.getElementsByTagName('VL_TYPE')[0].toxml())
        if variable_type == "Double":
            variable_type = "numeric"

        try:
            variable_description = re.sub('<[^>]*>', '', modif.getElementsByTagName('VL_DESCRIPTION')[0].toxml())
        except:
            variable_description = ""

        try:
            values =  variable.getElementsByTagName('VL_VALUE')
            values_list = []
            for value in values:
                values_list.append(re.sub('<[^>]*>', '',value.toxml()))
            values_str = ",".join( values_list )

        except:
            values_str= ""

        variables[variable_id] = { "label": variable_label,  "type": variable_type.lower(), "description": variable_description}
        if values_str:
            variables[variable_id]["predefined_values"] = values_str
            variables[variable_id]["type"] = "value from set"

    variables_boris = {}
    for k in variables:
        variables_boris[k] = {"label": variables[k]["label"],
                              "description": variables[k]["description"],
                              "type": variables[k]["type"],
                              "default value": "",
                              "possible values": variables[k]["predefined_values"] if "predefined_values" in variables[k] else "",
                              }

    project =  {"time_format": "hh:mm:ss",
                "project_name": project_name,
                "project_date": project_creation_date.replace(" ", "T"),
                "behaviors_conf": behaviors_boris,
                "project_format_version": "7.0",
                "project_description": project_description,
                "behavioral_categories": behav_category,
                "subjects_conf": subjects,
                "coding_map": {},
                "behaviors_coding_map": {},
                "observations": {},
                "independent_variables": variables_boris,
                "converters": {}
                }

    if flag_long_key:
        project["msg"] = "The keys longer than one char were deleted"

    return project

