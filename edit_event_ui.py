# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'edit_event.ui'
#
# Created: Tue Apr  1 13:11:18 2014
#      by: pyside-uic 0.2.13 running on PySide 1.1.1
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(342, 408)
        self.verticalLayout = QtGui.QVBoxLayout(Form)
        self.verticalLayout.setObjectName("verticalLayout")
        self.gridLayout = QtGui.QGridLayout()
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtGui.QLabel(Form)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.teTime = QtGui.QTimeEdit(Form)
        self.teTime.setObjectName("teTime")
        self.horizontalLayout_2.addWidget(self.teTime)
        self.dsbTime = QtGui.QDoubleSpinBox(Form)
        self.dsbTime.setDecimals(3)
        self.dsbTime.setMaximum(9999999.0)
        self.dsbTime.setObjectName("dsbTime")
        self.horizontalLayout_2.addWidget(self.dsbTime)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem)
        self.gridLayout.addLayout(self.horizontalLayout_2, 0, 1, 1, 2)
        self.lbSubject = QtGui.QLabel(Form)
        self.lbSubject.setObjectName("lbSubject")
        self.gridLayout.addWidget(self.lbSubject, 1, 0, 1, 2)
        self.cobSubject = QtGui.QComboBox(Form)
        self.cobSubject.setObjectName("cobSubject")
        self.gridLayout.addWidget(self.cobSubject, 1, 2, 1, 1)
        self.label_2 = QtGui.QLabel(Form)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 2, 0, 1, 1)
        self.cobCode = QtGui.QComboBox(Form)
        self.cobCode.setObjectName("cobCode")
        self.gridLayout.addWidget(self.cobCode, 2, 2, 1, 1)
        self.label_3 = QtGui.QLabel(Form)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 3, 0, 1, 2)
        self.cobModifier = QtGui.QComboBox(Form)
        self.cobModifier.setObjectName("cobModifier")
        self.gridLayout.addWidget(self.cobModifier, 3, 2, 1, 1)
        self.label_4 = QtGui.QLabel(Form)
        self.label_4.setObjectName("label_4")
        self.gridLayout.addWidget(self.label_4, 4, 0, 1, 2)
        self.leComment = QtGui.QPlainTextEdit(Form)
        self.leComment.setObjectName("leComment")
        self.gridLayout.addWidget(self.leComment, 5, 0, 1, 3)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.pbCancel = QtGui.QPushButton(Form)
        self.pbCancel.setObjectName("pbCancel")
        self.horizontalLayout.addWidget(self.pbCancel)
        self.pbOK = QtGui.QPushButton(Form)
        self.pbOK.setObjectName("pbOK")
        self.horizontalLayout.addWidget(self.pbOK)
        self.gridLayout.addLayout(self.horizontalLayout, 6, 0, 1, 3)
        self.verticalLayout.addLayout(self.gridLayout)

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        Form.setWindowTitle(QtGui.QApplication.translate("Form", "Edit event", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Form", "Time", None, QtGui.QApplication.UnicodeUTF8))
        self.teTime.setDisplayFormat(QtGui.QApplication.translate("Form", "hh:mm:ss.zzz", None, QtGui.QApplication.UnicodeUTF8))
        self.lbSubject.setText(QtGui.QApplication.translate("Form", "Subject", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Form", "Code", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("Form", "Modifier", None, QtGui.QApplication.UnicodeUTF8))
        self.label_4.setText(QtGui.QApplication.translate("Form", "Comment", None, QtGui.QApplication.UnicodeUTF8))
        self.pbCancel.setText(QtGui.QApplication.translate("Form", "Cancel", None, QtGui.QApplication.UnicodeUTF8))
        self.pbOK.setText(QtGui.QApplication.translate("Form", "OK", None, QtGui.QApplication.UnicodeUTF8))

