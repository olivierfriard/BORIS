"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2022 Olivier Friard


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

import datetime
import json
import logging
import socket

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication, QInputDialog, QLineEdit, QListWidgetItem

from . import config as cfg
from . import dialog
from . import utilities as util


class ProjectServerThread(QThread):
    """
    thread for serving project to BORIS mobile app
    """

    signal = pyqtSignal(dict)

    def __init__(self, message):
        QThread.__init__(self)
        self.message = message

    def __del__(self):
        self.wait()

    def run(self):

        BUFFER_SIZE = 1024

        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.settimeout(1800)

        s.bind((util.get_ip_address(), 0))
        self.signal.emit({"URL": f"{s.getsockname()[0]}:{s.getsockname()[1]}"})

        s.listen(5)
        while 1:
            try:
                c, addr = s.accept()

                logging.debug(f"Got connection from {addr}")

            except socket.timeout:
                s.close()

                logging.debug("Project server timeout")

                self.signal.emit({"MESSAGE": "Project server timeout"})
                return

            rq = c.recv(BUFFER_SIZE)

            logging.debug(f"request: {rq}")

            if rq == b"get":
                msg = self.message
                while msg:
                    c.send(msg[0:BUFFER_SIZE])
                    msg = msg[BUFFER_SIZE:]
                c.close()

                logging.debug("Project sent")

                self.signal.emit({"MESSAGE": f"Project sent to {addr[0]}"})

            if rq == b"stop":
                c.close()

                logging.debug("server stopped")

                self.signal.emit({"MESSAGE": "The server is now stopped"})
                return

            # receive an observation
            if rq == b"put":
                c.send(b"SEND")
                c.close()
                c2, addr = s.accept()
                rq2 = b""
                while 1:
                    d = c2.recv(BUFFER_SIZE)
                    if d:
                        rq2 += d
                        if rq2.endswith(b"#####"):
                            break
                    else:
                        break
                c2.close()
                self.signal.emit({"RECEIVED": f"{rq2.decode('utf-8')}", "SENDER": addr})


def send_project_via_socket(self):
    """
    send project to a device via socket
    """

    def receive_signal(msg_dict):

        if "RECEIVED" in msg_dict:
            try:
                sent_obs = json.loads(msg_dict["RECEIVED"][:-5])  # cut final
            except Exception:
                logging.debug("error receiving observation")
                del self.w
                self.actionSend_project.setText("Project server")
                return

            logging.debug(f"decoded {type(sent_obs)} length: {len(sent_obs)}")

            flag_msg = False
            mem_obsid = ""
            for obsId in sent_obs:

                self.w.lwi.addItem(
                    QListWidgetItem(f"{datetime.datetime.now().isoformat()}: Observation {obsId} received")
                )
                self.w.lwi.scrollToBottom()

                if obsId in self.pj[cfg.OBSERVATIONS]:
                    flag_msg = True
                    response = dialog.MessageDialog(
                        cfg.programName,
                        (
                            f"An observation with the same id<br><b>{obsId}</b><br>"
                            f"received from<br><b>{msg_dict['SENDER'][0]}</b><br>"
                            "already exists in the current project."
                        ),
                        [cfg.OVERWRITE, "Rename received observation", cfg.CANCEL],
                    )

                    if response == cfg.CANCEL:
                        return
                    self.project_changed()
                    if response == cfg.OVERWRITE:
                        self.pj[cfg.OBSERVATIONS][obsId] = dict(sent_obs[obsId])

                    if response == "Rename received observation":
                        new_id = obsId
                        while new_id in self.pj[cfg.OBSERVATIONS]:
                            new_id, ok = QInputDialog.getText(
                                self,
                                f"Rename observation received from {msg_dict['SENDER'][0]}",
                                "New observation id:",
                                QLineEdit.Normal,
                                new_id,
                            )

                        self.pj[cfg.OBSERVATIONS][new_id] = dict(sent_obs[obsId])

                else:
                    self.pj[cfg.OBSERVATIONS][obsId] = dict(sent_obs[obsId])
                    self.project_changed()
                    mem_obsid = obsId

        elif "URL" in msg_dict:
            self.tcp_port = int(msg_dict["URL"].split(":")[-1])
            self.w.label.setText(f"Project server URL:<br><b>{msg_dict['URL']}</b><br><br>Timeout: 30 minutes")

        else:
            if "stopped" in msg_dict["MESSAGE"] or "timeout" in msg_dict["MESSAGE"]:
                del self.w
                self.actionSend_project.setText("Project server")
            else:
                self.w.lwi.addItem(QListWidgetItem(f"{datetime.datetime.now().isoformat()}: {msg_dict['MESSAGE']}"))
                self.w.lwi.scrollToBottom()

    if "server" in self.actionSend_project.text():

        include_obs = cfg.NO
        if self.pj[cfg.OBSERVATIONS]:
            include_obs = dialog.MessageDialog(cfg.programName, "Include observations?", [cfg.YES, cfg.NO, cfg.CANCEL])
            if include_obs == cfg.CANCEL:
                return

        self.w = dialog.Info_widget()
        self.w.resize(450, 100)
        self.w.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.w.setWindowTitle("Project server")
        self.w.label.setText("")
        self.w.show()
        QApplication.processEvents()

        cp_project = dict(self.pj)
        if include_obs == cfg.NO:
            cp_project[cfg.OBSERVATIONS] = {}

        self.server_thread = ProjectServerThread(
            message=str.encode(
                str(json.dumps(cp_project, indent=None, separators=(",", ":"), default=util.decimal_default))
            )
        )
        self.server_thread.signal.connect(receive_signal)

        self.server_thread.start()

        self.actionSend_project.setText("Stop serving project")

    # send stop msg to project server
    elif "serving" in self.actionSend_project.text():

        s = socket.socket()
        s.connect((util.get_ip_address(), self.tcp_port))
        s.send(str.encode("stop"))
        received = ""
        while 1:
            data = s.recv(20)  # BUFFER_SIZE = 20
            if not data:
                break
            received += data
        s.close
