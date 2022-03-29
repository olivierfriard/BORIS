import logging
import socket
from .utilities import get_ip_address
from PyQt5.QtCore import QThread, pyqtSignal


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

        s.bind((get_ip_address(), 0))
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
