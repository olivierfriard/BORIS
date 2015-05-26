# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'edit_event.ui'
#
# Created: Thu Mar 26 12:23:54 2015
#      by: PyQt4 UI code generator 4.11.3
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

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName(_fromUtf8("Form"))
        Form.resize(342, 408)
        self.verticalLayout_2 = QtGui.QVBoxLayout(Form)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.label = QtGui.QLabel(Form)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout_3.addWidget(self.label)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.teTime = QtGui.QTimeEdit(Form)
        self.teTime.setObjectName(_fromUtf8("teTime"))
        self.horizontalLayout_2.addWidget(self.teTime)
        self.dsbTime = QtGui.QDoubleSpinBox(Form)
        self.dsbTime.setDecimals(3)
        self.dsbTime.setMaximum(9999999.0)
        self.dsbTime.setObjectName(_fromUtf8("dsbTime"))
        self.horizontalLayout_2.addWidget(self.dsbTime)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.horizontalLayout_3.addLayout(self.horizontalLayout_2)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.horizontalLayout_4 = QtGui.QHBoxLayout()
        self.horizontalLayout_4.setObjectName(_fromUtf8("horizontalLayout_4"))
        self.lbSubject = QtGui.QLabel(Form)
        self.lbSubject.setObjectName(_fromUtf8("lbSubject"))
        self.horizontalLayout_4.addWidget(self.lbSubject)
        self.cobSubject = QtGui.QComboBox(Form)
        self.cobSubject.setObjectName(_fromUtf8("cobSubject"))
        self.horizontalLayout_4.addWidget(self.cobSubject)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_4.addItem(spacerItem1)
        self.verticalLayout.addLayout(self.horizontalLayout_4)
        self.horizontalLayout_5 = QtGui.QHBoxLayout()
        self.horizontalLayout_5.setObjectName(_fromUtf8("horizontalLayout_5"))
        self.label_2 = QtGui.QLabel(Form)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.horizontalLayout_5.addWidget(self.label_2)
        self.cobCode = QtGui.QComboBox(Form)
        self.cobCode.setObjectName(_fromUtf8("cobCode"))
        self.horizontalLayout_5.addWidget(self.cobCode)
        spacerItem2 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_5.addItem(spacerItem2)
        self.verticalLayout.addLayout(self.horizontalLayout_5)
        self.groupBox = QtGui.QGroupBox(Form)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.verticalLayout.addWidget(self.groupBox)
        self.label_4 = QtGui.QLabel(Form)
        self.label_4.setObjectName(_fromUtf8("label_4"))
        self.verticalLayout.addWidget(self.label_4)
        self.leComment = QtGui.QPlainTextEdit(Form)
        self.leComment.setObjectName(_fromUtf8("leComment"))
        self.verticalLayout.addWidget(self.leComment)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.pbCancel = QtGui.QPushButton(Form)
        self.pbCancel.setObjectName(_fromUtf8("pbCancel"))
        self.horizontalLayout.addWidget(self.pbCancel)
        self.pbOK = QtGui.QPushButton(Form)
        self.pbOK.setObjectName(_fromUtf8("pbOK"))
        self.horizontalLayout.addWidget(self.pbOK)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(_translate("Form", "Edit event", None))
        self.label.setText(_translate("Form", "Time", None))
        self.teTime.setDisplayFormat(_translate("Form", "hh:mm:ss.zzz", None))
        self.lbSubject.setText(_translate("Form", "Subject", None))
        self.label_2.setText(_translate("Form", "Code", None))
        self.groupBox.setTitle(_translate("Form", "Modifiers", None))
        self.label_4.setText(_translate("Form", "Comment", None))
        self.pbCancel.setText(_translate("Form", "Cancel", None))
        self.pbOK.setText(_translate("Form", "OK", None))

