"""
BORIS
Behavioral Observation Research Interactive Software
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

import sys
import subprocess
import platform
import numpy as np
import pandas as pd
import matplotlib

from . import version
from . import config as cfg
from . import utilities as util


from PyQt5.QtCore import QT_VERSION_STR, PYQT_VERSION_STR
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QMessageBox


def actionAbout_activated(self):
    """
    About dialog
    """

    programs_versions: list = ["MPV media player"]

    mpv_lib_version, mpv_lib_file_path = util.mpv_lib_version()
    programs_versions.append(
        f"Library version: {mpv_lib_version} file: {mpv_lib_file_path} python-mpv version: {util.python_mpv_script_version()}"
    )

    # ffmpeg
    if self.ffmpeg_bin == "ffmpeg" and sys.platform.startswith("linux"):
        ffmpeg_true_path = subprocess.getoutput("which ffmpeg")
    else:
        ffmpeg_true_path = self.ffmpeg_bin
    programs_versions.extend(
        [
            "\nFFmpeg",
            subprocess.getoutput(f'"{self.ffmpeg_bin}" -version').split("\n")[0],
            f"Path: {ffmpeg_true_path}",
            "https://www.ffmpeg.org",
        ]
    )

    # numpy
    programs_versions.extend(["\nNumpy", f"version {np.__version__}", "https://numpy.org"])

    # matplotlib
    programs_versions.extend(["\nMatplotlib", f"version {matplotlib.__version__}", "https://matplotlib.org"])

    # pandas
    programs_versions.extend(["\nPandas", f"version {pd.__version__}", "https://pandas.pydata.org"])

    # graphviz
    gv_result = subprocess.getoutput("dot -V")

    programs_versions.extend(["\nGraphViz", gv_result if "graphviz" in gv_result else "not installed", "https://www.graphviz.org/"])

    about_dialog = QMessageBox()
    about_dialog.setIconPixmap(QPixmap(":/boris_unito"))

    about_dialog.setWindowTitle(f"About {cfg.programName}")
    about_dialog.setStandardButtons(QMessageBox.Ok)
    about_dialog.setDefaultButton(QMessageBox.Ok)
    about_dialog.setEscapeButton(QMessageBox.Ok)

    about_dialog.setInformativeText(
        (
            f"<b>{cfg.programName}</b> v. {version.__version__} - {version.__version_date__}"
            "<p>Copyright &copy; 2012-2024 Olivier Friard - Marco Gamba<br>"
            "Department of Life Sciences and Systems Biology<br>"
            "University of Torino - Italy<br>"
            "<br>"
            'BORIS is released under the <a href="https://www.gnu.org/copyleft/gpl.html">GNU General Public License</a><br>'
            'See <a href="https://www.boris.unito.it">www.boris.unito.it</a> for more details.<br>'
            "<br>"
            "The authors would like to acknowledge Valentina Matteucci for her precious help."
            "<hr>"
            "How to cite BORIS:<br>"
            "Friard, O. and Gamba, M. (2016), BORIS: a free, versatile open-source event-logging software for video/audio "
            "coding and live observations. Methods Ecol Evol, 7: 1325–1330.<br>"
            '<a href="https://besjournals.onlinelibrary.wiley.com/doi/full/10.1111/2041-210X.12584">DOI:10.1111/2041-210X.12584</a>'
        )
    )
    n = "\n"
    current_system = platform.uname()
    details = (
        f"Operating system: {current_system.system} {current_system.release} {current_system.version} \n"
        f"CPU: {current_system.machine} {current_system.processor}\n\n"
        f"Python {platform.python_version()} ({'64-bit' if sys.maxsize > 2**32 else '32-bit'})"
        f" - Qt {QT_VERSION_STR} - PyQt {PYQT_VERSION_STR}\n\n"
    )

    r, memory = util.mem_info()
    if not r:
        details += (
            f"Memory (RAM)  Total: {memory.get('total_memory', 'Not available'):.2f} Mb  "
            f"Free: {memory.get('free_memory', 'Not available'):.2f} Mb\n\n"
        )

    details += n.join(programs_versions)
    """
    memory_in_use = f"{utilities.rss_memory_used(self.pid)} Mb" if utilities.rss_memory_used(self.pid) != -1 else "Not available"
    percent_memory_in_use = (f"({utilities.rss_memory_percent_used(self.pid):.1f} % of total memory)"
                                if utilities.rss_memory_percent_used(self.pid) != -1
                                else "")
    """
    """
    f"Total memory: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.1f} Gb "
    f"({100 - psutil.virtual_memory().percent :.1f} % available){n}"
    f"Memory in use by BORIS: {memory_in_use} {percent_memory_in_use}{n}{n}"
    """

    about_dialog.setDetailedText(details)

    _ = about_dialog.exec_()
