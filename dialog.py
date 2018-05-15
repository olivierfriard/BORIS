#!/usr/bin/env python

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2018 Olivier Friard

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


try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

import config


def MessageDialog(title, text, buttons):
    response = ""
    message = QMessageBox()
    message.setWindowTitle(title)
    message.setText(text)
    message.setIcon(QMessageBox.Question)
    for button in buttons:
        message.addButton(button, QMessageBox.YesRole)

    message.setWindowFlags(Qt.WindowStaysOnTopHint)
    message.exec_()
    return message.clickedButton().text()


class Info_widget(QWidget):

    def __init__(self, parent = None):
        super(Info_widget, self).__init__(parent)

        self.setWindowTitle("BORIS")
        layout = QVBoxLayout()
        self.label = QLabel()
        layout.addWidget(self.label)
        self.lwi = QListWidget()
        layout.addWidget(self.lwi)
        self.setLayout(layout)


class DuplicateBehaviorCode(QDialog):
    """
    let user show between behaviors that are coded by same key
    """

    def __init__(self, text, codes_list):

        super(DuplicateBehaviorCode, self).__init__()

        self.setWindowTitle(config.programName)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        Vlayout = QVBoxLayout()
        widget = QWidget(self)
        widget.setLayout(Vlayout)

        label = QLabel()
        label.setText(text)
        Vlayout.addWidget(label)

        self.lw = QListWidget(widget)
        self.lw.setObjectName("lw_modifiers")
        #TODO: to be enabled
        #lw.installEventFilter(self)

        '''
        if QT_VERSION_STR[0] == "4":
            lw.setItemSelected(item, True)
        else:
            item.setSelected(True)
        '''

        for code in codes_list:
            item = QListWidgetItem(code)
            self.lw.addItem(item)

        Vlayout.addWidget(self.lw)

        pbCancel = QPushButton("Cancel")
        pbCancel.clicked.connect(self.reject)
        Vlayout.addWidget(pbCancel)
        pbOK = QPushButton("OK")
        pbOK.setDefault(True)
        pbOK.clicked.connect(self.pbOK_clicked)
        Vlayout.addWidget(pbOK)

        self.setLayout(Vlayout)

        #self.installEventFilter(self)

        self.setMaximumSize(1024 , 960)

    def getCode(self):
        """
        get selected behavior code
        """
        if self.lw.selectedItems():
            return self.lw.selectedItems()[0].text()

    def pbOK_clicked(self):
        self.accept()


class ChooseObservationsToImport(QDialog):
    """
    dialog for selectiong items
    """

    def __init__(self, text, observations_list):

        super(ChooseObservationsToImport, self).__init__()

        self.setWindowTitle(config.programName)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        Vlayout = QVBoxLayout()
        widget = QWidget(self)
        widget.setLayout(Vlayout)

        label = QLabel()
        label.setText(text)
        Vlayout.addWidget(label)

        self.lw = QListWidget(widget)
        self.lw.setObjectName("lw_observations")
        self.lw.setSelectionMode(QAbstractItemView.ExtendedSelection)
        #TODO: to be enabled
        #lw.installEventFilter(self)

        '''
        if QT_VERSION_STR[0] == "4":
            lw.setItemSelected(item, True)
        else:
            item.setSelected(True)
        '''

        for code in observations_list:
            item = QListWidgetItem(code)
            self.lw.addItem(item)

        Vlayout.addWidget(self.lw)

        pbCancel = QPushButton("Cancel")
        pbCancel.clicked.connect(self.reject)
        Vlayout.addWidget(pbCancel)
        pbOK = QPushButton("OK")
        pbOK.setDefault(True)
        pbOK.clicked.connect(self.pbOK_clicked)
        Vlayout.addWidget(pbOK)

        self.setLayout(Vlayout)

        #self.installEventFilter(self)

        self.setMaximumSize(1024 , 960)

    def get_selected_observations(self):
        """
        get selected_observations
        """
        return [item.text() for item in self.lw.selectedItems()]

    def pbOK_clicked(self):
        self.accept()


class JumpTo(QDialog):
    """
    "jump to" dialog box
    """

    def __init__(self, timeFormat):
        super(JumpTo, self).__init__()
        hbox = QVBoxLayout(self)
        self.label = QLabel()
        self.label.setText("Go to time")
        hbox.addWidget(self.label)
        if timeFormat == "hh:mm:ss":
            self.te = QTimeEdit()
            self.te.setDisplayFormat("hh:mm:ss.zzz")
        else:
            self.te = QDoubleSpinBox()
            self.te.setMinimum(0)
            self.te.setMaximum(86400)
            self.te.setDecimals(3)
        hbox.addWidget(self.te)
        self.pbOK = QPushButton('OK')
        self.pbOK.clicked.connect(self.pbOK_clicked)
        self.pbCancel = QPushButton('Cancel')
        self.pbCancel.clicked.connect(self.pbCancel_clicked)
        hbox2 = QHBoxLayout(self)
        hbox2.addWidget(self.pbCancel)
        hbox2.addWidget(self.pbOK)
        hbox.addLayout(hbox2)
        self.setLayout(hbox)
        self.setWindowTitle('Jump to specific time')

    def pbOK_clicked(self):
        self.accept()

    def pbCancel_clicked(self):
        self.reject()


class EditSelectedEvents(QDialog):
    """
    "edit selected events" dialog box
    """

    def __init__(self):
        super(EditSelectedEvents, self).__init__()

        self.setWindowTitle("Edit selected events")

        hbox = QVBoxLayout(self)

        self.rbSubject = QRadioButton("Subject")
        self.rbSubject.setChecked(False)
        self.rbSubject.toggled.connect(self.rb_changed)
        hbox.addWidget(self.rbSubject)

        self.rbBehavior = QRadioButton("Behavior")
        self.rbBehavior.setChecked(False)
        self.rbBehavior.toggled.connect(self.rb_changed)
        hbox.addWidget(self.rbBehavior)

        self.lb = QLabel("New value")
        hbox.addWidget(self.lb)
        self.newText = QListWidget(self)
        hbox.addWidget(self.newText)

        self.rbComment = QRadioButton("Comment")
        self.rbComment.setChecked(False)
        self.rbComment.toggled.connect(self.rb_changed)
        hbox.addWidget(self.rbComment)

        self.lbComment = QLabel("New comment")
        hbox.addWidget(self.lbComment)

        self.commentText = QLineEdit()
        hbox.addWidget(self.commentText)

        hbox2 = QHBoxLayout(self)
        self.pbOK = QPushButton("OK")
        self.pbOK.clicked.connect(self.pbOK_clicked)
        self.pbCancel = QPushButton("Cancel")
        self.pbCancel.clicked.connect(self.pbCancel_clicked)
        hbox2.addWidget(self.pbCancel)
        hbox2.addWidget(self.pbOK)
        hbox.addLayout(hbox2)

        self.setLayout(hbox)

    def rb_changed(self):

        self.newText.setEnabled(not self.rbComment.isChecked())
        self.commentText.setEnabled(self.rbComment.isChecked())

        if self.rbSubject.isChecked():
            self.newText.clear()
            self.newText.addItems(self.all_subjects)

        if self.rbBehavior.isChecked():
            self.newText.clear()
            self.newText.addItems(self.all_behaviors)

        if self.rbComment.isChecked():
            self.newText.clear()


    def pbOK_clicked(self):
        if not self.rbSubject.isChecked() and not self.rbBehavior.isChecked() and not self.rbComment.isChecked():
            QMessageBox.warning(None, config.programName, "You must select a field to be edited",
            QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        if (self.rbSubject.isChecked() or self.rbBehavior.isChecked()) and self.newText.selectedItems() == []:
            QMessageBox.warning(None, config.programName, "You must select a new value from the list",
            QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        self.accept()

    def pbCancel_clicked(self):
        self.reject()


class FindInEvents(QWidget):
    """
    "find in events" dialog box
    """

    clickSignal = pyqtSignal(str)
    sendEventSignal = pyqtSignal(QEvent)

    currentIdx = -1

    def __init__(self):
        super(FindInEvents, self).__init__()

        self.setWindowTitle("Find in events")

        hbox = QVBoxLayout()

        self.cbSubject = QCheckBox("Subject")
        self.cbSubject.setChecked(True)
        hbox.addWidget(self.cbSubject)

        self.cbBehavior = QCheckBox("Behavior")
        self.cbBehavior.setChecked(True)
        hbox.addWidget(self.cbBehavior)

        self.cbModifier = QCheckBox("Modifiers")
        self.cbModifier.setChecked(True)
        hbox.addWidget(self.cbModifier)

        self.cbComment = QCheckBox("Comment")
        self.cbComment.setChecked(True)
        hbox.addWidget(self.cbComment)

        self.lbFind = QLabel("Find")
        hbox.addWidget(self.lbFind)

        self.findText = QLineEdit()
        hbox.addWidget(self.findText)

        self.cbFindInSelectedEvents = QCheckBox("Find in selected events")
        self.cbFindInSelectedEvents.setChecked(False)
        hbox.addWidget(self.cbFindInSelectedEvents)

        self.lb_message = QLabel()
        hbox.addWidget(self.lb_message)

        hbox2 = QHBoxLayout()
        self.pbOK = QPushButton("Find")
        self.pbOK.clicked.connect(lambda: self.click("FIND"))
        self.pbCancel = QPushButton("Close")
        self.pbCancel.clicked.connect(lambda: self.click("CLOSE"))
        hbox2.addWidget(self.pbCancel)
        hbox2.addWidget(self.pbOK)
        hbox.addLayout(hbox2)

        self.setLayout(hbox)

    def click(self, msg):
        self.clickSignal.emit(msg)


class FindReplaceEvents(QWidget):
    """
    "find replace events" dialog box
    """

    clickSignal = pyqtSignal(str)
    sendEventSignal = pyqtSignal(QEvent)

    def __init__(self):
        super(FindReplaceEvents, self).__init__()

        self.setWindowTitle("Find/Replace events")

        hbox = QVBoxLayout()

        self.cbSubject = QCheckBox("Subject")
        self.cbSubject.setChecked(False)
        hbox.addWidget(self.cbSubject)


        self.cbBehavior = QCheckBox("Behavior")
        self.cbBehavior.setChecked(False)
        hbox.addWidget(self.cbBehavior)

        self.cbModifier = QCheckBox("Modifiers")
        self.cbModifier.setChecked(False)
        hbox.addWidget(self.cbModifier)

        self.cbComment = QCheckBox("Comment")
        self.cbComment.setChecked(False)
        hbox.addWidget(self.cbComment)

        self.lbFind = QLabel("Find")
        hbox.addWidget(self.lbFind)

        self.findText = QLineEdit()
        hbox.addWidget(self.findText)

        self.lbReplace = QLabel("Replace")
        hbox.addWidget(self.lbReplace)

        self.replaceText = QLineEdit()
        hbox.addWidget(self.replaceText)

        self.cbFindInSelectedEvents = QCheckBox("Find/Replace in selected events")
        self.cbFindInSelectedEvents.setChecked(False)
        hbox.addWidget(self.cbFindInSelectedEvents)

        hbox2 = QHBoxLayout()

        self.pbCancel = QPushButton("Cancel")
        self.pbCancel.clicked.connect(lambda: self.click("CANCEL"))
        hbox2.addWidget(self.pbCancel)

        self.pbOK = QPushButton("Find and replace")
        self.pbOK.clicked.connect(lambda: self.click("FIND_REPLACE"))
        hbox2.addWidget(self.pbOK)

        self.pbFindReplaceAll = QPushButton("Find and replace all")
        self.pbFindReplaceAll.clicked.connect(lambda: self.click("FIND_REPLACE_ALL"))
        hbox2.addWidget(self.pbFindReplaceAll)

        hbox.addLayout(hbox2)
        self.setLayout(hbox)

    def click(self, msg):
        self.clickSignal.emit(msg)


class Results_dialog(QDialog):
    """
    widget for visualizing text output
    """
    def __init__(self):
        super().__init__()

        self.setWindowTitle("")

        hbox = QVBoxLayout()

        self.lb = QLabel("")
        hbox.addWidget(self.lb)

        self.ptText = QPlainTextEdit()
        hbox.addWidget(self.ptText)

        hbox2 = QHBoxLayout()
        self.pbSave = QPushButton("Save text")
        self.pbSave.clicked.connect(self.save_results)
        hbox2.addWidget(self.pbSave)

        self.pbCancel = QPushButton("Cancel")
        self.pbCancel.clicked.connect(self.reject)
        hbox2.addWidget(self.pbCancel)
        self.pbCancel.setVisible(False)

        self.pbOK = QPushButton("OK")
        self.pbOK.clicked.connect(self.accept)
        hbox2.addWidget(self.pbOK)

        hbox.addLayout(hbox2)

        self.setLayout(hbox)

        self.resize(540, 640)


    def save_results(self):
        """
        save content of self.ptText
        """
        
        fn = QFileDialog(self).getSaveFileName(self, "Save results", "", "Text files (*.txt *.tsv);;All files (*)")
        file_name = fn[0] if type(fn) is tuple else fn
        
        if file_name:
            try:
                with open(file_name, "w") as f:
                    f.write(self.ptText.toPlainText())
            except:
                QMessageBox.critical(self, programName, "The file {} can not be saved".format(file_name))



class ResultsWidget(QWidget):
    """
    widget for visualizing text output
    """
    def __init__(self):
        super().__init__()

        self.setWindowTitle("")

        hbox = QVBoxLayout()

        self.lb = QLabel("")
        hbox.addWidget(self.lb)

        self.ptText = QPlainTextEdit()
        hbox.addWidget(self.ptText)

        hbox2 = QHBoxLayout()
        self.pbSave = QPushButton("Save results")
        self.pbSave.clicked.connect(self.save_results)
        hbox2.addWidget(self.pbSave)

        self.pbOK = QPushButton("OK")
        self.pbOK.clicked.connect(self.close)
        hbox2.addWidget(self.pbOK)

        hbox.addLayout(hbox2)

        self.setLayout(hbox)

        self.resize(540, 640)


    def save_results(self):
        """
        save content of self.ptText
        """
        
        fn = QFileDialog(self).getSaveFileName(self, "Save results", "", "Text files (*.txt *.tsv);;All files (*)")
        file_name = fn[0] if type(fn) is tuple else fn
        
        if file_name:
            try:
                with open(file_name, "w") as f:
                    f.write(self.ptText.toPlainText())
            except:
                QMessageBox.critical(self, programName, "The file {} can not be saved".format(file_name))



class FrameViewer(QWidget):
    """
    widget for visualizing frame
    """
    def __init__(self):
        super(FrameViewer, self).__init__()

        self.setWindowTitle("")

        hbox = QVBoxLayout()

        self.lbFrame = QLabel("")
        hbox.addWidget(self.lbFrame)

        self.setLayout(hbox)

    def pbOK_clicked(self):
        self.close()
