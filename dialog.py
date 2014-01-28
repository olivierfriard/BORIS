#!/usr/bin/env python

import PySide
from PySide.QtGui import *

def MessageDialog(title, text, buttons):
    response = ''
    message = QMessageBox()
    message.setWindowTitle(title)
    message.setText(text)
    message.setIcon(QMessageBox.Question)
    for button in buttons:
        message.addButton(button, QMessageBox.YesRole)
    
    message.exec_()
    return message.clickedButton().text()
    
