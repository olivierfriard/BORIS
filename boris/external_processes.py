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

"""


import os
import tempfile
import pathlib as pl
import logging

from PyQt5.QtWidgets import QFileDialog, QMessageBox, QInputDialog
from PyQt5.QtCore import (
    Qt,
    QProcess,
)

from . import config as cfg
from . import dialog
from . import utilities as util


def ffmpeg_process(self, action: str):
    """
    launch ffmpeg process with QProcess

    Args:
        action (str): "reencode_resize, rotate, merge
    """
    if action not in ("reencode_resize", "rotate", "merge"):
        return

    def readStdOutput(idx):
        """
        read stdout and stderr form qprocess and display them
        """
        self.processes_widget.label.setText(
            (
                "This operation can be long. Be patient...\n"
                "In the meanwhile you can continue to use BORIS\n\n"
                f"Done: {self.processes_widget.number_of_files - len(self.processes)} of {self.processes_widget.number_of_files}"
            )
        )

        # self.processes_widget.lwi.clear()
        std_out = self.processes[idx - 1][0].readAllStandardOutput().data().decode("utf-8")
        if std_out:
            self.processes_widget.lwi.addItems((f"{pl.Path(self.processes[idx - 1][1][2]).name}:   {std_out}",))

        """
        std_err = self.processes[idx - 1][0].readAllStandardError().data().decode("utf-8")
        if std_err:
            self.processes_widget.lwi.addItems((f"{pl.Path(self.processes[idx - 1][1][2]).name}: ERROR: {std_err}",))
            self.flag_ffmpeg_error = True
        """

        self.processes_widget.lwi.scrollToBottom()

    def qprocess_finished(idx):
        """
        function triggered when process finished
        """
        if self.processes:
            del self.processes[idx - 1]
        if self.processes:
            # start new process
            self.processes[-1][0].start(self.processes[-1][1][0], self.processes[-1][1][1])
        else:
            self.processes_widget.label.setText(
                (f"Done: {self.processes_widget.number_of_files - len(self.processes)} of {self.processes_widget.number_of_files}")
            )
            """
            self.processes_widget.hide()
            del self.processes_widget
            """

    if self.processes:
        QMessageBox.warning(self, cfg.programName, "BORIS is already running some job.")
        return

    if action == "merge":
        msg = "Select two or more media files to merge"
        file_type = "Media files (*)"
    else:
        msg = f"Select one or more video files to {action.replace('_', ' and ')}"
        file_type = "Video files (*)"
    fn = QFileDialog().getOpenFileNames(self, msg, "", file_type)
    file_names = fn[0] if type(fn) is tuple else fn

    if not file_names:
        return

    if action == "reencode_resize":
        current_bitrate = 10_000_000  # default 10 Mb/s
        current_resolution = 1024

        r = util.accurate_media_analysis(self.ffmpeg_bin, file_names[0])
        if "error" in r:
            QMessageBox.warning(self, cfg.programName, f"{file_names[0]}. {r['error']}")
        elif r["has_video"]:
            current_bitrate = r.get("bitrate", None)
            if current_bitrate is None:
                current_bitrate = -1
            else:
                current_bitrate = round(current_bitrate / 1024 / 1024)  # Convert to Mb/s
            current_resolution = int(r["resolution"].split("x")[0]) if r["resolution"] is not None else None

        ib = dialog.Input_dialog(
            "Set the parameters for re-encoding / resizing",
            [
                ("sb", "Horizontal resolution (in pixel)", 352, 3840, 100, current_resolution),
                ("sb", "Video quality (bitrate Mb/s)", 1, 1000, 1, current_bitrate),
            ],
        )
        if not ib.exec_():
            return

        if len(file_names) > 1:
            if (
                dialog.MessageDialog(
                    cfg.programName,
                    "All the selected video files will be re-encoded / resized with these parameters",
                    [cfg.OK, cfg.CANCEL],
                )
                == cfg.CANCEL
            ):
                return

        horiz_resol = ib.elements["Horizontal resolution (in pixel)"].value()
        video_quality = ib.elements["Video quality (bitrate Mb/s)"].value()

    if action == "merge":
        if len(file_names) == 1:
            QMessageBox.critical(self, cfg.programName, "Select more than one file")
            return

        file_extensions = []  # check extension of 1st media file
        file_list_lst = []
        for file_name in file_names:
            file_list_lst.append(f"file '{file_name}'")
            file_extensions.append(pl.Path(file_name).suffix)
        if len(set(file_extensions)) > 1:
            QMessageBox.critical(self, cfg.programName, "All media files must have the same format")
            return

        while True:
            output_file_name, _ = QFileDialog().getSaveFileName(self, "Output file name", "", "*")
            if output_file_name == "":
                return
            if pl.Path(output_file_name).suffix != file_extensions[0]:
                QMessageBox.warning(
                    self,
                    cfg.programName,
                    (
                        "The extension of output file must be the same than the extension of input files "
                        f"(<b>{file_extensions[0]}</b>).<br>You selected a {pl.Path(output_file_name).suffix} file."
                    ),
                )
            else:
                break

        # temp file for list of media file to merge
        with tempfile.NamedTemporaryFile() as tmp:
            file_list = tmp.name
        with open(file_list, "w") as f_out:
            f_out.write("\n".join(file_list_lst))

    if action == "rotate":
        rotation_items = ("Rotate 90 clockwise", "Rotate 90 counter clockwise", "rotate 180")

        rotation, ok = QInputDialog.getItem(self, "Rotate media file(s)", "Type of rotation", rotation_items, 0, False)

        if not ok:
            return
        rotation_idx = rotation_items.index(rotation) + 1

    # check if processed files already exist
    if action in ("reencode_resize", "rotate"):
        files_list = []
        for file_name in file_names:
            if action == "reencode_resize":
                fn = f"{file_name}.re-encoded.{horiz_resol}px.{video_quality}Mb.avi"

            if action == "rotate":
                fn = f"{file_name}.rotated{['', '90', '-90', '180'][rotation_idx]}.avi"

            if os.path.isfile(fn):
                files_list.append(fn)

        if files_list:
            response = dialog.MessageDialog(
                cfg.programName,
                "Some file(s) already exist.\n\n" + "\n".join(files_list),
                [cfg.OVERWRITE_ALL, cfg.CANCEL],
            )
            if response == cfg.CANCEL:
                return

    self.processes_widget = dialog.Info_widget()
    self.processes_widget.resize(700, 300)

    self.processes_widget.setWindowFlags(Qt.WindowStaysOnTopHint)
    if action == "reencode_resize":
        self.processes_widget.setWindowTitle("Re-encoding and resizing with FFmpeg")
    if action == "rotate":
        self.processes_widget.setWindowTitle("Rotating the video with FFmpeg")
    if action == "merge":
        self.processes_widget.setWindowTitle("Merging media files")

    self.processes_widget.label.setText("This operation can be long. Be patient...\nIn the meanwhile you can continue to use BORIS\n\n")
    self.processes_widget.number_of_files = len(file_names)
    self.processes_widget.show()

    if action == "merge":
        # ffmpeg -f concat -safe 0 -i join_video.txt -c copy output_demuxer.mp4
        args = ["-hide_banner", "-y", "-f", "concat", "-safe", "0", "-i", file_list, "-c", "copy", output_file_name]
        self.processes.append([QProcess(self), [self.ffmpeg_bin, args, output_file_name]])
        self.processes[-1][0].setProcessChannelMode(QProcess.MergedChannels)
        self.processes[-1][0].readyReadStandardOutput.connect(lambda: readStdOutput(len(self.processes)))
        self.processes[-1][0].readyReadStandardError.connect(lambda: readStdOutput(len(self.processes)))
        self.processes[-1][0].finished.connect(lambda: qprocess_finished(len(self.processes)))

        self.processes[-1][0].start(self.processes[-1][1][0], self.processes[-1][1][1])

    if action in ("reencode_resize", "rotate"):
        for file_name in sorted(file_names, reverse=True):
            if action == "reencode_resize":
                args = [
                    "-hide_banner",
                    "-y",
                    "-i",
                    f"{file_name}",
                    "-vf",
                    f"scale={horiz_resol}:-1",
                    "-b:v",
                    f"{video_quality * 1024 * 1024}",
                    f"{file_name}.re-encoded.{horiz_resol}px.{video_quality}Mb.avi",
                ]

            if action == "rotate":
                # check bitrate
                r = util.accurate_media_analysis(self.ffmpeg_bin, file_name)
                if "error" not in r and r["bitrate"] is not None:
                    current_bitrate = r["bitrate"]
                else:
                    current_bitrate = 10_000_000

                if rotation_idx in (1, 2):
                    args = [
                        "-hide_banner",
                        "-y",
                        "-i",
                        f"{file_name}",
                        "-vf",
                        f"transpose={rotation_idx}",
                        "-codec:a",
                        "copy",
                        "-b:v",
                        f"{current_bitrate}",
                        f"{file_name}.rotated{['', '90', '-90'][rotation_idx]}.avi",
                    ]

                if rotation_idx == 3:  # 180
                    args = [
                        "-hide_banner",
                        "-y",
                        "-i",
                        f"{file_name}",
                        "-vf",
                        "transpose=2,transpose=2",
                        "-codec:a",
                        "copy",
                        "-b:v",
                        f"{current_bitrate}",
                        f"{file_name}.rotated180.avi",
                    ]

            logging.debug("Launch process")
            logging.debug(f"{self.ffmpeg_bin} {' '.join(args)}")

            self.processes.append([QProcess(self), [self.ffmpeg_bin, args, file_name]])

            # self.processes[-1][0].setProcessChannelMode(QProcess.SeparateChannels)

            ## FFmpeg output the work in progress on stderr
            self.processes[-1][0].setProcessChannelMode(QProcess.MergedChannels)
            self.processes[-1][0].readyReadStandardOutput.connect(lambda: readStdOutput(len(self.processes)))
            # self.processes[-1][0].readyReadStandardError.connect(lambda: readStdOutput(len(self.processes)))

            self.processes[-1][0].finished.connect(lambda: qprocess_finished(len(self.processes)))

        self.processes[-1][0].start(self.processes[-1][1][0], self.processes[-1][1][1])
