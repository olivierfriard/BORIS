#!/usr/bin/env python


from PySide.QtCore import *
from PySide.QtGui import *

from preferences_ui import Ui_prefDialog

class Preferences(QDialog, Ui_prefDialog):

    def __init__(self, parent=None):
        
        super(Preferences, self).__init__(parent)
        self.setupUi(self)


        ### make invisible "Save complete media path in project"
        self.cbSaveMediaFilePath.setVisible(False)

        self.pbOK.clicked.connect(self.pbOK_clicked)
        self.pbCancel.clicked.connect(self.pbCancel_clicked)

    def pbOK_clicked(self):
        self.accept()

    def pbCancel_clicked(self):
        self.reject()

