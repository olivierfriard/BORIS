# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'param_panel.ui'
#
# Created: Fri Jul 10 15:47:52 2015
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
        Dialog.resize(670, 626)
        self.verticalLayout_2 = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.lbSubjects = QtGui.QLabel(Dialog)
        self.lbSubjects.setObjectName(_fromUtf8("lbSubjects"))
        self.verticalLayout.addWidget(self.lbSubjects)
        self.lwSubjects = QtGui.QListWidget(Dialog)
        self.lwSubjects.setObjectName(_fromUtf8("lwSubjects"))
        self.verticalLayout.addWidget(self.lwSubjects)
        self.lbBehaviors = QtGui.QLabel(Dialog)
        self.lbBehaviors.setObjectName(_fromUtf8("lbBehaviors"))
        self.verticalLayout.addWidget(self.lbBehaviors)
        self.lwBehaviors = QtGui.QListWidget(Dialog)
        self.lwBehaviors.setObjectName(_fromUtf8("lwBehaviors"))
        self.verticalLayout.addWidget(self.lwBehaviors)
        self.cbIncludeModifiers = QtGui.QCheckBox(Dialog)
        self.cbIncludeModifiers.setObjectName(_fromUtf8("cbIncludeModifiers"))
        self.verticalLayout.addWidget(self.cbIncludeModifiers)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.lbMaxTime = QtGui.QLabel(Dialog)
        self.lbMaxTime.setObjectName(_fromUtf8("lbMaxTime"))
        self.horizontalLayout.addWidget(self.lbMaxTime)
        self.sbMaxTime = QtGui.QSpinBox(Dialog)
        self.sbMaxTime.setObjectName(_fromUtf8("sbMaxTime"))
        self.horizontalLayout.addWidget(self.sbMaxTime)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem1)
        self.pbCancel = QtGui.QPushButton(Dialog)
        self.pbCancel.setObjectName(_fromUtf8("pbCancel"))
        self.horizontalLayout_2.addWidget(self.pbCancel)
        self.pbOK = QtGui.QPushButton(Dialog)
        self.pbOK.setObjectName(_fromUtf8("pbOK"))
        self.horizontalLayout_2.addWidget(self.pbOK)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(_translate("Dialog", "Parameters", None))
        self.lbSubjects.setText(_translate("Dialog", "Subjects", None))
        self.lbBehaviors.setText(_translate("Dialog", "Behaviors", None))
        self.cbIncludeModifiers.setText(_translate("Dialog", "Include modifiers", None))
        self.lbMaxTime.setText(_translate("Dialog", "Max time (s)", None))
        self.pbCancel.setText(_translate("Dialog", "Cancel", None))
        self.pbOK.setText(_translate("Dialog", "OK", None))

