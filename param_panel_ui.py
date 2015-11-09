# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'param_panel.ui'
#
# Created: Mon Nov  9 16:09:27 2015
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
        self.horizontalLayout_3 = QtGui.QHBoxLayout()
        self.horizontalLayout_3.setObjectName(_fromUtf8("horizontalLayout_3"))
        self.pbSelectAllSubjects = QtGui.QPushButton(Dialog)
        self.pbSelectAllSubjects.setObjectName(_fromUtf8("pbSelectAllSubjects"))
        self.horizontalLayout_3.addWidget(self.pbSelectAllSubjects)
        self.pbUnselectAllSubjects = QtGui.QPushButton(Dialog)
        self.pbUnselectAllSubjects.setObjectName(_fromUtf8("pbUnselectAllSubjects"))
        self.horizontalLayout_3.addWidget(self.pbUnselectAllSubjects)
        self.pbReverseSubjectsSelection = QtGui.QPushButton(Dialog)
        self.pbReverseSubjectsSelection.setObjectName(_fromUtf8("pbReverseSubjectsSelection"))
        self.horizontalLayout_3.addWidget(self.pbReverseSubjectsSelection)
        self.verticalLayout.addLayout(self.horizontalLayout_3)
        self.lwSubjects = QtGui.QListWidget(Dialog)
        self.lwSubjects.setObjectName(_fromUtf8("lwSubjects"))
        self.verticalLayout.addWidget(self.lwSubjects)
        self.lbBehaviors = QtGui.QLabel(Dialog)
        self.lbBehaviors.setObjectName(_fromUtf8("lbBehaviors"))
        self.verticalLayout.addWidget(self.lbBehaviors)
        self.horizontalLayout_4 = QtGui.QHBoxLayout()
        self.horizontalLayout_4.setObjectName(_fromUtf8("horizontalLayout_4"))
        self.pbSelectAllBehaviors = QtGui.QPushButton(Dialog)
        self.pbSelectAllBehaviors.setObjectName(_fromUtf8("pbSelectAllBehaviors"))
        self.horizontalLayout_4.addWidget(self.pbSelectAllBehaviors)
        self.pbUnselectAllBehaviors = QtGui.QPushButton(Dialog)
        self.pbUnselectAllBehaviors.setObjectName(_fromUtf8("pbUnselectAllBehaviors"))
        self.horizontalLayout_4.addWidget(self.pbUnselectAllBehaviors)
        self.pbReverseBehaviorsSelection = QtGui.QPushButton(Dialog)
        self.pbReverseBehaviorsSelection.setObjectName(_fromUtf8("pbReverseBehaviorsSelection"))
        self.horizontalLayout_4.addWidget(self.pbReverseBehaviorsSelection)
        self.verticalLayout.addLayout(self.horizontalLayout_4)
        self.lwBehaviors = QtGui.QListWidget(Dialog)
        self.lwBehaviors.setObjectName(_fromUtf8("lwBehaviors"))
        self.verticalLayout.addWidget(self.lwBehaviors)
        self.cbIncludeModifiers = QtGui.QCheckBox(Dialog)
        self.cbIncludeModifiers.setObjectName(_fromUtf8("cbIncludeModifiers"))
        self.verticalLayout.addWidget(self.cbIncludeModifiers)
        self.cbExcludeBehaviors = QtGui.QCheckBox(Dialog)
        self.cbExcludeBehaviors.setObjectName(_fromUtf8("cbExcludeBehaviors"))
        self.verticalLayout.addWidget(self.cbExcludeBehaviors)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.lbMaxTime = QtGui.QLabel(Dialog)
        self.lbMaxTime.setObjectName(_fromUtf8("lbMaxTime"))
        self.horizontalLayout.addWidget(self.lbMaxTime)
        self.sbMaxTime = QtGui.QDoubleSpinBox(Dialog)
        self.sbMaxTime.setMaximum(10000.0)
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
        self.pbSelectAllSubjects.setText(_translate("Dialog", "Select all", None))
        self.pbUnselectAllSubjects.setText(_translate("Dialog", "Unselect all", None))
        self.pbReverseSubjectsSelection.setText(_translate("Dialog", "Reverse selection", None))
        self.lbBehaviors.setText(_translate("Dialog", "Behaviors", None))
        self.pbSelectAllBehaviors.setText(_translate("Dialog", "Select all", None))
        self.pbUnselectAllBehaviors.setText(_translate("Dialog", "Unselect all", None))
        self.pbReverseBehaviorsSelection.setText(_translate("Dialog", "Reverse selection", None))
        self.cbIncludeModifiers.setText(_translate("Dialog", "Include modifiers", None))
        self.cbExcludeBehaviors.setText(_translate("Dialog", "Exclude behaviors without events", None))
        self.lbMaxTime.setText(_translate("Dialog", "Max time (decimal minutes)", None))
        self.pbCancel.setText(_translate("Dialog", "Cancel", None))
        self.pbOK.setText(_translate("Dialog", "OK", None))

