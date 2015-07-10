# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'param_panel.ui'
#
# Created: Fri Jul 10 11:37:47 2015
#      by: PyQt4 UI code generator 4.11.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(629, 559)
        self.lwSubjects = QtGui.QListWidget(Dialog)
        self.lwSubjects.setGeometry(QtCore.QRect(50, 30, 256, 192))
        self.lwSubjects.setObjectName(_fromUtf8("lwSubjects"))
        self.pbOK = QtGui.QPushButton(Dialog)
        self.pbOK.setGeometry(QtCore.QRect(520, 520, 83, 25))
        self.pbOK.setObjectName(_fromUtf8("pbOK"))
        self.pbCancel = QtGui.QPushButton(Dialog)
        self.pbCancel.setGeometry(QtCore.QRect(420, 520, 83, 25))
        self.pbCancel.setObjectName(_fromUtf8("pbCancel"))
        self.lbSubjects = QtGui.QLabel(Dialog)
        self.lbSubjects.setGeometry(QtCore.QRect(50, 10, 57, 14))
        self.lbSubjects.setObjectName(_fromUtf8("lbSubjects"))

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(_translate("Dialog", "Dialog", None))
        self.pbOK.setText(_translate("Dialog", "OK", None))
        self.pbCancel.setText(_translate("Dialog", "Cancel", None))
        self.lbSubjects.setText(_translate("Dialog", "Subjects", None))

