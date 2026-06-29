"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2026 Olivier Friard

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

"""

import copy
import importlib
import inspect
import json
import logging
import re
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import get_args, get_origin

import numpy as np
import pandas as pd
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMessageBox

from . import config as cfg
from . import dialog, project_functions, version, view_df


def add_plugins_to_menu(self):
    """
    add plugins to the plugins menu
    """

    def add_plugin_action(plugin_name):
        logging.debug(f"adding plugin '{plugin_name}' to menu")
        # Create an action for each submenu option
        action = QAction(self, triggered=lambda checked=False, name=plugin_name: run_plugin(self, name))
        action.setText(plugin_name)

        self.menu_plugins.addAction(action)

    def is_relative_to(path: Path, parent: Path) -> bool:
        try:
            path.resolve().relative_to(parent.resolve())
        except ValueError:
            return False
        return True

    personal_plugins_dir = self.config_param.get(cfg.PERSONAL_PLUGINS_DIR, "")
    personal_plugins_path = Path(personal_plugins_dir).expanduser() if personal_plugins_dir else None

    official_plugin_names: list[str] = []
    personal_plugin_names: list[str] = []
    for plugin_name, plugin_path in self.config_param.get(cfg.ANALYSIS_PLUGINS, {}).items():
        plugin_path = Path(plugin_path).expanduser()
        if personal_plugins_path is not None and is_relative_to(plugin_path, personal_plugins_path):
            personal_plugin_names.append(plugin_name)
        else:
            official_plugin_names.append(plugin_name)

    for plugin_name in official_plugin_names:
        add_plugin_action(plugin_name)

    if official_plugin_names and personal_plugin_names:
        self.menu_plugins.addSeparator()

    for plugin_name in personal_plugin_names:
        add_plugin_action(plugin_name)


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


def get_plugin_version(plugin_path: str) -> str | None:
    """
    get version of a Python plugin
    """
    plugin_version: str | None = None
    with open(plugin_path, "r") as f_in:
        for line in f_in:
            if line.startswith("__version__"):
                if "=" in line:
                    plugin_version = line.split("=", 1)[1].strip().replace('"', "").replace("'", "")
                else:
                    plugin_version = None
                break
    return plugin_version


def version_parts(version_str: str) -> tuple[int, ...]:
    """
    Return the numeric parts of a version string.
    """

    parts: list[int] = []
    for part in str(version_str).strip().lstrip("vV").split("."):
        match = re.match(r"^(\d+)", part)
        if match is None:
            break
        parts.append(int(match.group(1)))
    return tuple(parts)


def compare_versions(version_a: str, version_b: str) -> int:
    """
    Compare two version strings by their numeric parts.
    """

    parts_a = version_parts(version_a)
    parts_b = version_parts(version_b)
    size = max(len(parts_a), len(parts_b))
    parts_a = parts_a + (0,) * (size - len(parts_a))
    parts_b = parts_b + (0,) * (size - len(parts_b))
    return (parts_a > parts_b) - (parts_a < parts_b)


def boris_version_satisfies_requirement(current_version: str, requirement: str | None) -> bool:
    """
    Return True if current_version satisfies a plugin BORIS version requirement.
    """

    if not requirement:
        return True

    requirement = str(requirement).strip()
    operators = (">=", "<=", "==", "!=", ">", "<", "=")
    operator = ">="
    required_version = requirement

    for candidate in operators:
        if requirement.startswith(candidate):
            operator = candidate
            required_version = requirement[len(candidate) :].strip()
            break

    if not version_parts(current_version) or not version_parts(required_version):
        return False

    comparison = compare_versions(current_version, required_version)

    if operator == ">=":
        return comparison >= 0
    if operator == ">":
        return comparison > 0
    if operator == "<=":
        return comparison <= 0
    if operator == "<":
        return comparison < 0
    if operator in ("==", "="):
        return comparison == 0
    if operator == "!=":
        return comparison != 0

    return False


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


def get_r_plugin_version(plugin_path: str) -> str | None:
    """
    get version of a R plugin
    """
    plugin_version: str | None = None
    with open(plugin_path, "r") as f_in:
        for line in f_in:
            line_without_spaces = line.replace(" ", "")
            if line_without_spaces.startswith("version=") or line_without_spaces.startswith("version<-"):
                if "=" in line:
                    plugin_version = line.split("=", 1)[1].strip().replace('"', "").replace("'", "")
                    break
                elif "<-" in line:
                    plugin_version = line.split("<-", 1)[1].strip().replace('"', "").replace("'", "")
                    break
                else:
                    plugin_version = None
                    break
    return plugin_version


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


def get_python_plugin_files(plugin_dir: str | Path) -> list[Path]:
    """
    Return Python plugin files found directly in plugin_dir.
    """
    plugin_dir = Path(plugin_dir).expanduser()
    if not plugin_dir.is_dir():
        return []
    return sorted(file_ for file_ in plugin_dir.glob("*.py") if not file_.name.startswith("_"))


def get_default_external_plugins_dir() -> Path:
    """
    Return the default directory for the official external plugins repository.
    """
    return Path.home() / cfg.OFFICIAL_PLUGINS_REPO_NAME


def _plugin_source_dir_candidates(root_dir: str | Path) -> list[Path]:
    """
    Return possible plugin directories for a cloned/downloaded plugins repository.
    """
    root_dir = Path(root_dir).expanduser()
    candidates = [
        root_dir,
        root_dir / "plugins",
        root_dir / "analysis_plugins",
        root_dir / "boris" / "analysis_plugins",
    ]

    seen: set[Path] = set()
    unique_candidates: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve() if candidate.exists() else candidate
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_candidates.append(candidate)
    return unique_candidates


def _contains_python_plugins(plugin_dir: str | Path) -> bool:
    """
    Check if plugin_dir contains at least one valid Python plugin.
    """
    for file_ in get_python_plugin_files(plugin_dir):
        try:
            if get_plugin_name(file_) is not None:
                return True
        except Exception as exc:
            logging.warning(f"Unable to read plugin name from {file_}: {exc}")
    return False


def get_plugin_dir_from_repository(root_dir: str | Path) -> Path | None:
    """
    Return the directory that contains plugins inside a cloned/downloaded plugins repository.
    """
    for candidate in _plugin_source_dir_candidates(root_dir):
        if _contains_python_plugins(candidate):
            return candidate
    return None


def _official_plugins_root_candidates(config_param: dict | None = None) -> list[Path]:
    """
    Return configured root directories for the official external plugins repository.
    """
    config_param = config_param or {}
    candidates: list[Path] = []

    configured_dir = config_param.get(cfg.OFFICIAL_PLUGINS_DIR, "")
    if configured_dir:
        candidates.append(Path(configured_dir).expanduser())

    seen: set[Path] = set()
    unique_candidates: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve() if candidate.exists() else candidate
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_candidates.append(candidate)
    return unique_candidates


def get_external_plugins_dir(config_param: dict | None = None) -> Path | None:
    """
    Return the official external plugins directory, if available.
    """
    for root_dir in _official_plugins_root_candidates(config_param):
        plugin_dir = get_plugin_dir_from_repository(root_dir)
        if plugin_dir is not None:
            return plugin_dir
    return None


def get_official_plugins_dir(config_param: dict | None = None) -> Path | None:
    """
    Return the official plugins directory from the external BORIS_plugins repository.
    """
    return get_external_plugins_dir(config_param)


def get_official_plugin_files(config_param: dict | None = None) -> list[Path]:
    """
    Return the Python plugins loaded as official BORIS plugins.
    """
    official_plugins_dir = get_official_plugins_dir(config_param)
    if official_plugins_dir is None:
        return []
    return get_python_plugin_files(official_plugins_dir)


def official_plugins_branch_source() -> dict[str, str]:
    """
    Return metadata for the official plugins main branch source.
    """
    return {
        "type": cfg.OFFICIAL_PLUGINS_SOURCE_BRANCH,
        "branch": cfg.OFFICIAL_PLUGINS_REPO_BRANCH,
        "archive_url": cfg.OFFICIAL_PLUGINS_ARCHIVE_URL,
        "text": f"{cfg.OFFICIAL_PLUGINS_REPO_BRANCH} branch",
    }


def official_plugins_source_from_release(release: dict) -> dict[str, str]:
    """
    Return metadata for an official plugins release source.
    """
    return {
        "type": cfg.OFFICIAL_PLUGINS_SOURCE_RELEASE,
        "tag_name": release["tag_name"],
        "archive_url": release["zipball_url"],
        "text": _official_plugins_release_text(release),
    }


def normalize_official_plugins_source(source: dict | None) -> dict[str, str]:
    """
    Return a complete official plugins source dict.
    """
    if not isinstance(source, dict):
        return official_plugins_branch_source()

    archive_url = source.get("archive_url") or ""
    if not archive_url:
        return official_plugins_branch_source()

    source_type = source.get("type")
    if not source_type:
        source_type = cfg.OFFICIAL_PLUGINS_SOURCE_RELEASE if source.get("tag_name") else cfg.OFFICIAL_PLUGINS_SOURCE_BRANCH

    text = source.get("text")
    if not text:
        if source_type == cfg.OFFICIAL_PLUGINS_SOURCE_RELEASE and source.get("tag_name"):
            text = source["tag_name"]
        elif source_type == cfg.OFFICIAL_PLUGINS_SOURCE_BRANCH:
            text = f"{source.get('branch', cfg.OFFICIAL_PLUGINS_REPO_BRANCH)} branch"
        else:
            text = archive_url

    normalized_source = {
        "type": source_type,
        "archive_url": archive_url,
        "text": text,
    }
    if source_type == cfg.OFFICIAL_PLUGINS_SOURCE_RELEASE and source.get("tag_name"):
        normalized_source["tag_name"] = source["tag_name"]
    if source_type == cfg.OFFICIAL_PLUGINS_SOURCE_BRANCH:
        normalized_source["branch"] = source.get("branch", cfg.OFFICIAL_PLUGINS_REPO_BRANCH)
    return normalized_source


def _official_plugins_release_text(release: dict) -> str:
    """
    Return the release label shown in Preferences.
    """
    tag_name = release["tag_name"]
    release_name = release.get("name") or tag_name
    text = tag_name if release_name == tag_name else f"{release_name} ({tag_name})"

    published_at = release.get("published_at", "")
    if published_at:
        text = f"{text} - {published_at[:10]}"

    if release.get("prerelease"):
        text = f"{text} [pre-release]"

    return text


def list_official_plugins_releases() -> list[dict[str, str]]:
    """
    Return published releases for the official plugins repository.
    """
    request = urllib.request.Request(
        f"{cfg.OFFICIAL_PLUGINS_RELEASES_API_URL}?per_page=100",
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{cfg.programName}/plugins",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        releases = json.load(response)

    if not isinstance(releases, list):
        raise RuntimeError("Unexpected response from GitHub releases API")

    official_releases: list[dict[str, str]] = []
    for release in releases:
        if not isinstance(release, dict) or release.get("draft"):
            continue

        tag_name = release.get("tag_name")
        archive_url = release.get("zipball_url")
        if not tag_name or not archive_url:
            continue

        official_releases.append(official_plugins_source_from_release(release))

    return official_releases


def _safe_extract_zip(zip_path: Path, destination: Path) -> None:
    """
    Extract a zip file without allowing paths outside destination.
    """
    destination = destination.resolve()
    with zipfile.ZipFile(zip_path) as zip_file:
        for member in zip_file.infolist():
            member_path = (destination / member.filename).resolve()
            if not member_path.is_relative_to(destination):
                raise RuntimeError(f"Unsafe path in plugin archive: {member.filename}")
        zip_file.extractall(destination)


def _copy_repository_contents(source_dir: Path, target_dir: Path) -> None:
    """
    Replace target_dir contents with source_dir contents, preserving .git if present.
    """
    target_dir.parent.mkdir(parents=True, exist_ok=True)
    target_dir.mkdir(exist_ok=True)

    with tempfile.TemporaryDirectory(dir=target_dir.parent) as backup_dir_str:
        backup_dir = Path(backup_dir_str)
        moved_children: list[tuple[Path, Path]] = []

        for child in target_dir.iterdir():
            if child.name == ".git":
                continue
            backup_child = backup_dir / child.name
            shutil.move(str(child), str(backup_child))
            moved_children.append((backup_child, child))

        try:
            for child in source_dir.iterdir():
                if child.name == ".git":
                    continue

                destination = target_dir / child.name
                if child.is_dir() and not child.is_symlink():
                    shutil.copytree(child, destination, symlinks=True)
                else:
                    shutil.copy2(child, destination, follow_symlinks=False)
        except Exception:
            for child in target_dir.iterdir():
                if child.name == ".git":
                    continue
                if child.is_dir() and not child.is_symlink():
                    shutil.rmtree(child)
                else:
                    child.unlink()

            for backup_child, original_child in moved_children:
                shutil.move(str(backup_child), str(original_child))
            raise


def download_official_plugins_repository(
    target_dir: str | Path,
    archive_url: str = cfg.OFFICIAL_PLUGINS_ARCHIVE_URL,
) -> Path:
    """
    Download or update the official plugins repository from a GitHub zip archive.
    """
    target_dir = Path(target_dir).expanduser()

    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        zip_path = temp_dir / f"{cfg.OFFICIAL_PLUGINS_REPO_NAME}.zip"
        extract_dir = temp_dir / "extracted"
        extract_dir.mkdir()

        request = urllib.request.Request(archive_url, headers={"User-Agent": f"{cfg.programName}/plugins"})
        with urllib.request.urlopen(request, timeout=60) as response, open(zip_path, "wb") as zip_file:
            shutil.copyfileobj(response, zip_file)

        _safe_extract_zip(zip_path, extract_dir)

        extracted_children = [child for child in extract_dir.iterdir()]
        source_dir = extracted_children[0] if len(extracted_children) == 1 and extracted_children[0].is_dir() else extract_dir

        if get_plugin_dir_from_repository(source_dir) is None:
            raise RuntimeError(f"No official plugin found in archive downloaded from {archive_url}")

        _copy_repository_contents(source_dir, target_dir)

    plugin_dir = get_plugin_dir_from_repository(target_dir)
    if plugin_dir is None:
        raise RuntimeError(f"No official plugin found in {target_dir}")

    return plugin_dir


def load_plugins(self):
    """
    load selected plugins in config_param
    """

    logging.debug("Loading plugins")

    def msg(plugin_name, file_):
        message = (
            f"A plugin with the same name is already loaded ({self.config_param[cfg.ANALYSIS_PLUGINS][plugin_name]}).\n\n"
            f"The plugin from {file_} is not loaded."
        )
        QMessageBox.warning(
            self,
            cfg.programName,
            message,
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Default,
            QMessageBox.StandardButton.NoButton,
        )

    def load_python_plugins(plugin_files: list[Path], source: str):
        for file_ in plugin_files:
            logging.debug(f"Loading {source} plugin: {Path(file_).stem}")

            # test module
            module_name = Path(file_).stem
            spec = importlib.util.spec_from_file_location(module_name, file_)
            plugin_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin_module)
            attributes_list = dir(plugin_module)

            if "__plugin_name__" in attributes_list:
                plugin_name = plugin_module.__plugin_name__
            else:
                continue

            if "run" not in attributes_list:
                continue

            # plugin_name = get_plugin_name(file_)
            if plugin_name is not None and plugin_name not in self.config_param.get(cfg.EXCLUDED_PLUGINS, set()):
                # check if plugin with same name already loaded
                if plugin_name in self.config_param[cfg.ANALYSIS_PLUGINS]:
                    msg(plugin_name, file_)
                    continue

                self.config_param[cfg.ANALYSIS_PLUGINS][plugin_name] = str(file_)

    self.menu_plugins.clear()
    self.config_param[cfg.ANALYSIS_PLUGINS] = {}

    # load official BORIS plugins from the external repository
    official_plugins_dir = get_official_plugins_dir(self.config_param)
    logging.debug(f"Loading official BORIS plugins from {official_plugins_dir}")
    load_python_plugins(get_official_plugin_files(self.config_param), "official BORIS")

    # load personal plugins
    if self.config_param.get(cfg.PERSONAL_PLUGINS_DIR, ""):
        load_python_plugins(get_python_plugin_files(self.config_param.get(cfg.PERSONAL_PLUGINS_DIR, "")), "personal")

    # load personal R plugins
    if self.config_param.get(cfg.PERSONAL_PLUGINS_DIR, ""):
        for file_ in sorted(Path(self.config_param.get(cfg.PERSONAL_PLUGINS_DIR, "")).glob("*.R")):
            if file_.name.startswith("_"):
                continue
            plugin_name = get_r_plugin_name(file_)
            if plugin_name is not None and plugin_name not in self.config_param.get(cfg.EXCLUDED_PLUGINS, set()):
                # check if plugin with same name already loaded
                if plugin_name in self.config_param[cfg.ANALYSIS_PLUGINS]:
                    msg(plugin_name, file_)
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


def annotation_includes_type(annotation, expected_type: type) -> bool:
    """
    Return True if an annotation is expected_type or a union/generic containing it.
    """
    if annotation is expected_type:
        return True

    if isinstance(annotation, str):
        normalized = annotation.replace(" ", "")
        expected_name = expected_type.__name__
        qualified_expected_name = f"{expected_type.__module__}.{expected_name}"
        annotation_parts = [
            part.removesuffix("]").split("[", 1)[0]
            for part in normalized.replace("Optional[", "").replace("Union[", "").replace(",", "|").split("|")
        ]
        return (
            normalized == expected_name
            or normalized == qualified_expected_name
            or normalized.startswith(f"{expected_name}[")
            or normalized.startswith(f"{qualified_expected_name}[")
            or any(
                part == expected_name or part == qualified_expected_name or part.endswith(f".{expected_name}") for part in annotation_parts
            )
        )

    origin = get_origin(annotation)
    if origin is expected_type:
        return True

    return any(annotation_includes_type(arg, expected_type) for arg in get_args(annotation) if arg is not type(None))


def run_plugin(self, plugin_name):
    """
    run plugin
    """

    if not self.project:
        QMessageBox.warning(
            self,
            cfg.programName,
            "No observations found. Open a project first",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Default,
            QMessageBox.StandardButton.NoButton,
        )
        return

    logging.debug(f"{self.config_param.get(cfg.ANALYSIS_PLUGINS, {})=}")

    if plugin_name not in self.config_param.get(cfg.ANALYSIS_PLUGINS, {}):
        QMessageBox.critical(self, cfg.programName, f"Plugin '{plugin_name}' not found")
        return

    plugin_path: str = self.config_param.get(cfg.ANALYSIS_PLUGINS, {}).get(plugin_name, "")

    logging.debug(f"{plugin_path=}")

    # check if plugin file exists
    if not Path(plugin_path).is_file():
        QMessageBox.critical(self, cfg.programName, f"The plugin {plugin_path} was not found.")
        return

    logging.debug(f"run plugin from {plugin_path}")

    plugin_module = None

    # Python plugin
    if Path(plugin_path).suffix == ".py":
        # load plugin as module
        module_name = Path(plugin_path).stem

        spec = importlib.util.spec_from_file_location(module_name, plugin_path)
        plugin_module = importlib.util.module_from_spec(spec)

        logging.debug(f"{plugin_module=}")

        spec.loader.exec_module(plugin_module)

        required_boris_version = getattr(plugin_module, "__require_boris_version__", None)
        if required_boris_version and not boris_version_satisfies_requirement(version.__version__, required_boris_version):
            plugin_display_name = getattr(plugin_module, "__plugin_name__", plugin_name)
            QMessageBox.critical(
                self,
                cfg.programName,
                (
                    f"The plugin '{plugin_display_name}' requires BORIS {required_boris_version}.\n\n"
                    f"Current BORIS version: {version.__version__}."
                ),
            )
            return

    # select observations to analyze
    selected_observations, parameters = self.obs_param()
    if not selected_observations:
        return

    # Python plugin
    if Path(plugin_path).suffix == ".py":
        plugin_version = plugin_module.__version__
        plugin_version_date = plugin_module.__version_date__

        logging.info(
            f"{plugin_module.__plugin_name__} loaded v.{getattr(plugin_module, '__version__')} v. {getattr(plugin_module, '__version_date__')}"
        )

        # check arguments required by the run function of the plugin
        dataframe_required: bool = False
        project_required: bool = False
        parameters_required: bool = False
        # for param in inspect.signature(plugin_module.run).parameters.values():
        for name, annotation in inspect.getfullargspec(plugin_module.run).annotations.items():
            if name == "df" and annotation_includes_type(annotation, pd.DataFrame):
                dataframe_required = True
            if name == "project" and annotation_includes_type(annotation, dict):
                project_required = True
            if name == "parameters" and annotation_includes_type(annotation, dict):
                parameters_required = True

        # create arguments for the plugin run function
        plugin_kwargs: dict = {}

        if dataframe_required:
            logging.info("preparing dataframe for plugin")
            message, df = project_functions.project2dataframe(self.pj, selected_observations)
            if message:
                logging.critical(message)
                QMessageBox.critical(self, cfg.programName, message)
                return
            logging.info("done")

            # filter the dataframe with parameters
            logging.info("filtering dataframe for plugin")
            filtered_df = plugin_df_filter(df, observations_list=selected_observations, parameters=parameters)
            logging.info("done")

            plugin_kwargs["df"] = filtered_df

        if project_required:
            pj_copy = copy.deepcopy(self.pj)

            # remove unselected observations from project
            for obs_id in self.pj[cfg.OBSERVATIONS]:
                if obs_id not in selected_observations:
                    del pj_copy[cfg.OBSERVATIONS][obs_id]

            plugin_kwargs["project"] = pj_copy

        if parameters_required:
            plugin_kwargs["parameters"] = parameters

        plugin_results = plugin_module.run(**plugin_kwargs)

    # R plugin
    if Path(plugin_path).suffix in (".R", ".r"):
        try:
            from rpy2 import robjects
            from rpy2.robjects import pandas2ri
            from rpy2.robjects.conversion import localconverter
            from rpy2.robjects.packages import SignatureTranslatedAnonymousPackage
        except Exception:
            QMessageBox.critical(self, cfg.programName, "The rpy2 Python module is not installed. R plugins cannot be used")
            return

        logging.info("preparing dataframe for plugin")

        message, df = project_functions.project2dataframe(self.pj, selected_observations)
        if message:
            logging.critical(message)
            QMessageBox.critical(self, cfg.programName, message)
            return

        logging.info("done")

        # filter the dataframe with parameters
        logging.info("filtering dataframe for plugin")
        filtered_df = plugin_df_filter(df, observations_list=selected_observations, parameters=parameters)
        logging.info("done")

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
        result_title = plugin_name
        result_payload = result

        if isinstance(result, tuple) and len(result) == 2 and isinstance(result[0], str) and isinstance(result[1], (str, pd.DataFrame)):
            result_title, result_payload = result

        if isinstance(result_payload, str):
            self.remove_closed_results_objects()
            self.results_objects.append(dialog.Results_widget())
            self.results_objects[-1].setWindowTitle(result_title)
            self.results_objects[-1].ptText.clear()
            self.results_objects[-1].ptText.appendPlainText(result_payload)
            self.results_objects[-1].show()
        elif isinstance(result_payload, pd.DataFrame):
            self.remove_closed_results_objects()
            self.results_objects.append(view_df.View_df(result_title, f"{plugin_version} ({plugin_version_date})", result_payload))
            self.results_objects[-1].show()
        else:
            # result is not str nor dataframe
            QMessageBox.critical(
                None,
                cfg.programName,
                (
                    f"Plugin returns an unknown object type: {type(result_payload)}\n\n"
                    "Plugins must return str, Pandas Dataframes,\n"
                    "or tuples formatted as (title, str/DataFrame).\n"
                    "Check the plugin code."
                ),
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Default,
                QMessageBox.StandardButton.NoButton,
            )
