"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2025 Olivier Friard

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

import importlib
import logging
import numpy as np
import pandas as pd
from pathlib import Path

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMessageBox

from . import config as cfg
from . import project_functions
from . import dialog
from . import view_df


def add_plugins_to_menu(self):
    """
    add plugins to the plugins menu
    """
    for plugin_name in self.config_param.get(cfg.ANALYSIS_PLUGINS, {}):
        logging.debug(f"adding plugin '{plugin_name}' to menu")
        # Create an action for each submenu option
        action = QAction(self, triggered=lambda checked=False, name=plugin_name: run_plugin(self, name))
        action.setText(plugin_name)

        self.menu_plugins.addAction(action)


def get_plugin_name(plugin_path: str) -> str | None:
    """
    get name of a Python plugin
    """
    # search plugin name
    plugin_name: str | None = None
    with open(plugin_path, "r") as f_in:
        for line in f_in:
            if line.startswith("__plugin_name__"):
                plugin_name = line.split("=")[1].strip().replace('"', "")
                break
    return plugin_name


def get_r_plugin_name(plugin_path: str) -> str | None:
    """
    get name of a R plugin
    """
    # search plugin name
    plugin_name: str | None = None
    with open(plugin_path, "r") as f_in:
        for line in f_in:
            if line.startswith("plugin_name"):
                if "=" in line:
                    plugin_name = line.split("=")[1].strip().replace('"', "").replace("'", "")
                    break
                elif "<-" in line:
                    plugin_name = line.split("<-")[1].strip().replace('"', "").replace("'", "")
                    break
                else:
                    plugin_name = None
                    break
    return plugin_name


def get_r_plugin_description(plugin_path: str) -> str | None:
    """
    get description of a R plugin
    """
    # search plugin name
    plugin_description: str | None = None
    with open(plugin_path, "r") as f_in:
        for line in f_in:
            if line.startswith("description"):
                if "=" in line:
                    plugin_description = line.split("=")[1].strip().replace('"', "").replace("'", "")
                    break
                elif "<-" in line:
                    plugin_description = line.split("<-")[1].strip().replace('"', "").replace("'", "")
                    break
                else:
                    plugin_description = None
                    break
    return plugin_description


def load_plugins(self):
    """
    load selected plugins in analysis menu
    """

    def msg():
        QMessageBox.warning(
            self,
            cfg.programName,
            f"A plugin with the same name is already loaded ({self.config_param[cfg.ANALYSIS_PLUGINS][plugin_name]}).\n\nThe plugin from {file_} is not loaded.",
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )

    self.menu_plugins.clear()
    self.config_param[cfg.ANALYSIS_PLUGINS] = {}

    # load BORIS plugins
    for file_ in sorted((Path(__file__).parent / "analysis_plugins").glob("*.py")):
        if file_.name.startswith("_"):
            continue
        plugin_name = get_plugin_name(file_)
        if plugin_name is not None and plugin_name not in self.config_param.get(cfg.EXCLUDED_PLUGINS, set()):
            # check if plugin with same name already loaded
            if plugin_name in self.config_param[cfg.ANALYSIS_PLUGINS]:
                msg()
                continue

            self.config_param[cfg.ANALYSIS_PLUGINS][plugin_name] = str(file_)

    # load personal plugins
    if self.config_param.get(cfg.PERSONAL_PLUGINS_DIR, ""):
        for file_ in sorted(Path(self.config_param.get(cfg.PERSONAL_PLUGINS_DIR, "")).glob("*.py")):
            if file_.name.startswith("_"):
                continue
            plugin_name = get_plugin_name(file_)
            if plugin_name is not None and plugin_name not in self.config_param.get(cfg.EXCLUDED_PLUGINS, set()):
                # check if plugin with same name already loaded
                if plugin_name in self.config_param[cfg.ANALYSIS_PLUGINS]:
                    msg()
                    continue

                self.config_param[cfg.ANALYSIS_PLUGINS][plugin_name] = str(file_)

    # load personal R plugins
    if self.config_param.get(cfg.PERSONAL_PLUGINS_DIR, ""):
        for file_ in sorted(Path(self.config_param.get(cfg.PERSONAL_PLUGINS_DIR, "")).glob("*.R")):
            if file_.name.startswith("_"):
                continue
            plugin_name = get_r_plugin_name(file_)
            if plugin_name is not None and plugin_name not in self.config_param.get(cfg.EXCLUDED_PLUGINS, set()):
                # check if plugin with same name already loaded
                if plugin_name in self.config_param[cfg.ANALYSIS_PLUGINS]:
                    msg()
                    continue

                self.config_param[cfg.ANALYSIS_PLUGINS][plugin_name] = str(file_)

    logging.debug(f"{self.config_param.get(cfg.ANALYSIS_PLUGINS, {})=}")


def plugin_df_filter(df: pd.DataFrame, observations_list: list = [], parameters: dict = {}) -> pd.DataFrame:
    """
    filter the dataframe following parameters

    filter by selected observations.
    filter by selected subjects.
    filter by selected behaviors.
    filter by time interval.
    """

    # filter selected observations
    df = df[df["Observation id"].isin(observations_list)]

    if parameters:
        # filter selected subjects
        df = df[df["Subject"].isin(parameters["selected subjects"])]

        # filter selected behaviors
        df = df[df["Behavior"].isin(parameters["selected behaviors"])]

        if parameters["time"] == cfg.TIME_OBS_INTERVAL:
            # filter each observation with observation interval start/stop

            # keep events between observation interval start time and observation interval stop/end
            df_interval = df[
                (
                    ((df["Start (s)"] >= df["Observation interval start"]) & (df["Start (s)"] <= df["Observation interval stop"]))
                    | ((df["Stop (s)"] >= df["Observation interval start"]) & (df["Stop (s)"] <= df["Observation interval stop"]))
                )
                | ((df["Start (s)"] < df["Observation interval start"]) & (df["Stop (s)"] > df["Observation interval stop"]))
            ]

            df_interval.loc[df["Start (s)"] < df["Observation interval start"], "Start (s)"] = df["Observation interval start"]
            df_interval.loc[df["Stop (s)"] > df["Observation interval stop"], "Stop (s)"] = df["Observation interval stop"]

            df_interval.loc[:, "Duration (s)"] = (df_interval["Stop (s)"] - df_interval["Start (s)"]).replace(0, np.nan)

            df = df_interval

        else:
            # filter selected time interval
            if parameters["start time"] is not None and parameters["end time"] is not None:
                MIN_TIME = parameters["start time"]
                MAX_TIME = parameters["end time"]

                # keep events between start time and end_time
                df_interval = df[
                    (
                        ((df["Start (s)"] >= MIN_TIME) & (df["Start (s)"] <= MAX_TIME))
                        | ((df["Stop (s)"] >= MIN_TIME) & (df["Stop (s)"] <= MAX_TIME))
                    )
                    | ((df["Start (s)"] < MIN_TIME) & (df["Stop (s)"] > MAX_TIME))
                ]

                # cut state events to interval
                df_interval.loc[df["Start (s)"] < MIN_TIME, "Start (s)"] = MIN_TIME
                df_interval.loc[df["Stop (s)"] > MAX_TIME, "Stop (s)"] = MAX_TIME

                df_interval.loc[:, "Duration (s)"] = (df_interval["Stop (s)"] - df_interval["Start (s)"]).replace(0, np.nan)

                df = df_interval

    print("filtered")
    print("=" * 50)

    # print(f"{df=}")

    return df


def run_plugin(self, plugin_name):
    """
    run plugin
    """

    if not self.project:
        QMessageBox.warning(
            self,
            cfg.programName,
            "No observations found. Open a project first",
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    logging.debug(f"{self.config_param.get(cfg.ANALYSIS_PLUGINS, {})=}")

    if plugin_name not in self.config_param.get(cfg.ANALYSIS_PLUGINS, {}):
        QMessageBox.critical(self, cfg.programName, f"Plugin '{plugin_name}' not found")
        return

    plugin_path: str = self.config_param.get(cfg.ANALYSIS_PLUGINS, {}).get(plugin_name, "")

    logging.debug(f"{plugin_path=}")

    if not Path(plugin_path).is_file():
        QMessageBox.critical(self, cfg.programName, f"The plugin {plugin_path} was not found.")
        return

    logging.debug(f"run plugin from {plugin_path}")

    # select observations to analyze
    selected_observations, parameters = self.obs_param()
    if not selected_observations:
        return

    logging.info("preparing dataframe for plugin")

    df = project_functions.project2dataframe(self.pj, selected_observations)

    logging.info("done")

    """
    logging.debug("dataframe info")
    logging.debug(f"{df.info()}")
    logging.debug(f"{df.head()}")
    """

    # filter the dataframe with parameters
    logging.info("filtering dataframe for plugin")
    filtered_df = plugin_df_filter(df, observations_list=selected_observations, parameters=parameters)
    logging.info("done")

    if Path(plugin_path).suffix == ".py":
        # load plugin as module
        module_name = Path(plugin_path).stem

        spec = importlib.util.spec_from_file_location(module_name, plugin_path)
        plugin_module = importlib.util.module_from_spec(spec)

        logging.debug(f"{plugin_module=}")

        spec.loader.exec_module(plugin_module)

        plugin_version = plugin_module.__version__
        plugin_version_date = plugin_module.__version_date__

        logging.info(
            f"{plugin_module.__plugin_name__} loaded v.{getattr(plugin_module, '__version__')} v. {getattr(plugin_module, '__version_date__')}"
        )

        # run plugin
        plugin_results = plugin_module.run(filtered_df)

    if Path(plugin_path).suffix in (".R", ".r"):
        try:
            from rpy2 import robjects
            from rpy2.robjects import pandas2ri
            from rpy2.robjects.packages import SignatureTranslatedAnonymousPackage
            from rpy2.robjects.conversion import localconverter
        except Exception:
            QMessageBox.critical(self, cfg.programName, "The rpy2 Python module is not installed. R plugins cannot be used")
            return

        # Read code from file
        try:
            with open(plugin_path, "r") as f:
                r_code = f.read()
        except Exception:
            QMessageBox.critical(self, cfg.programName, f"Error reading the plugin {plugin_path}.")
            return

        # read version
        plugin_version = next(
            (
                x.split("<-")[1].replace('"', "").replace("'", "").strip()
                for x in r_code.splitlines()
                if x.replace(" ", "").startswith("version<-")
            ),
            None,
        )
        # read version date
        plugin_version_date = next(
            (
                x.split("<-")[1].replace('"', "").replace("'", "").strip()
                for x in r_code.split("\n")
                if x.replace(" ", "").startswith("version_date<")
            ),
            None,
        )

        r_plugin = SignatureTranslatedAnonymousPackage(r_code, "r_plugin")

        with localconverter(robjects.default_converter + pandas2ri.converter):
            r_df = robjects.conversion.py2rpy(filtered_df)

        try:
            r_result = r_plugin.run(r_df)
        except Exception as e:
            QMessageBox.critical(self, cfg.programName, f"Error in the plugin {plugin_path}: {e}.")
            return

        with localconverter(robjects.default_converter + pandas2ri.converter):
            plugin_results = robjects.conversion.rpy2py(r_result)

    # test if plugin_results is a tuple: if not transform it to tuple
    if not isinstance(plugin_results, tuple):
        plugin_results = tuple([plugin_results])

    self.plugin_visu: list = []
    for result in plugin_results:
        if isinstance(result, str):
            self.plugin_visu.append(dialog.Results_dialog())
            self.plugin_visu[-1].setWindowTitle(plugin_name)
            self.plugin_visu[-1].ptText.clear()
            self.plugin_visu[-1].ptText.appendPlainText(result)
            self.plugin_visu[-1].show()
        elif isinstance(result, pd.DataFrame):
            self.plugin_visu.append(view_df.View_df(plugin_name, f"{plugin_version} ({plugin_version_date})", result))
            self.plugin_visu[-1].show()
        else:
            # result is not str nor dataframe
            QMessageBox.critical(
                None,
                cfg.programName,
                (
                    f"Plugin returns an unknown object type: {type(result)}\n\n"
                    "Plugins must return str and/or Pandas Dataframes.\n"
                    "Check the plugin code."
                ),
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
