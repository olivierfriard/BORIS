# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'add_modifier.ui'
#
# Created: Thu Mar 26 12:33:53 2015
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

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName(_fromUtf8("Dialog"))
        Dialog.resize(522, 344)
        self.verticalLayout_7 = QtGui.QVBoxLayout(Dialog)
        self.verticalLayout_7.setObjectName(_fromUtf8("verticalLayout_7"))
        self.verticalLayout_6 = QtGui.QVBoxLayout()
        self.verticalLayout_6.setObjectName(_fromUtf8("verticalLayout_6"))
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.verticalLayout_2 = QtGui.QVBoxLayout()
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.lbModifier = QtGui.QLabel(Dialog)
        self.lbModifier.setObjectName(_fromUtf8("lbModifier"))
        self.verticalLayout_2.addWidget(self.lbModifier)
        self.leModifier = QtGui.QLineEdit(Dialog)
        self.leModifier.setObjectName(_fromUtf8("leModifier"))
        self.verticalLayout_2.addWidget(self.leModifier)
        self.lbCode = QtGui.QLabel(Dialog)
        self.lbCode.setObjectName(_fromUtf8("lbCode"))
        self.verticalLayout_2.addWidget(self.lbCode)
        self.leCode = QtGui.QLineEdit(Dialog)
        self.leCode.setObjectName(_fromUtf8("leCode"))
        self.verticalLayout_2.addWidget(self.leCode)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem)
        self.horizontalLayout.addLayout(self.verticalLayout_2)
        self.verticalLayout_3 = QtGui.QVBoxLayout()
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        self.pbAddModifier = QtGui.QPushButton(Dialog)
        self.pbAddModifier.setObjectName(_fromUtf8("pbAddModifier"))
        self.verticalLayout_3.addWidget(self.pbAddModifier)
        self.pbModifyModifier = QtGui.QPushButton(Dialog)
        self.pbModifyModifier.setObjectName(_fromUtf8("pbModifyModifier"))
        self.verticalLayout_3.addWidget(self.pbModifyModifier)
        spacerItem1 = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_3.addItem(spacerItem1)
        self.horizontalLayout.addLayout(self.verticalLayout_3)
        self.verticalLayout_5 = QtGui.QVBoxLayout()
        self.verticalLayout_5.setObjectName(_fromUtf8("verticalLayout_5"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.tabWidgetModifiersSets = QtGui.QTabWidget(Dialog)
        self.tabWidgetModifiersSets.setTabPosition(QtGui.QTabWidget.North)
        self.tabWidgetModifiersSets.setElideMode(QtCore.Qt.ElideNone)
        self.tabWidgetModifiersSets.setObjectName(_fromUtf8("tabWidgetModifiersSets"))
        self.set1 = QtGui.QWidget()
        self.set1.setObjectName(_fromUtf8("set1"))
        self.tabWidgetModifiersSets.addTab(self.set1, _fromUtf8(""))
        self.verticalLayout.addWidget(self.tabWidgetModifiersSets)
        self.lwModifiers = QtGui.QListWidget(Dialog)
        self.lwModifiers.setObjectName(_fromUtf8("lwModifiers"))
        self.verticalLayout.addWidget(self.lwModifiers)
        self.verticalLayout_5.addLayout(self.verticalLayout)
        self.verticalLayout_4 = QtGui.QVBoxLayout()
        self.verticalLayout_4.setObjectName(_fromUtf8("verticalLayout_4"))
        self.pbRemoveModifier = QtGui.QPushButton(Dialog)
        self.pbRemoveModifier.setObjectName(_fromUtf8("pbRemoveModifier"))
        self.verticalLayout_4.addWidget(self.pbRemoveModifier)
        self.pbAddSet = QtGui.QPushButton(Dialog)
        self.pbAddSet.setObjectName(_fromUtf8("pbAddSet"))
        self.verticalLayout_4.addWidget(self.pbAddSet)
        self.pbRemoveSet = QtGui.QPushButton(Dialog)
        self.pbRemoveSet.setObjectName(_fromUtf8("pbRemoveSet"))
        self.verticalLayout_4.addWidget(self.pbRemoveSet)
        self.verticalLayout_5.addLayout(self.verticalLayout_4)
        self.horizontalLayout.addLayout(self.verticalLayout_5)
        self.verticalLayout_6.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        spacerItem2 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem2)
        self.pbCancel = QtGui.QPushButton(Dialog)
        self.pbCancel.setObjectName(_fromUtf8("pbCancel"))
        self.horizontalLayout_2.addWidget(self.pbCancel)
        self.pbOK = QtGui.QPushButton(Dialog)
        self.pbOK.setObjectName(_fromUtf8("pbOK"))
        self.horizontalLayout_2.addWidget(self.pbOK)
        self.verticalLayout_6.addLayout(self.horizontalLayout_2)
        self.verticalLayout_7.addLayout(self.verticalLayout_6)

        self.retranslateUi(Dialog)
        self.tabWidgetModifiersSets.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(_translate("Dialog", "Set modifiers", None))
        self.lbModifier.setText(_translate("Dialog", "Modifier", None))
        self.lbCode.setText(_translate("Dialog", "Key code", None))
        self.pbAddModifier.setText(_translate("Dialog", "-->", None))
        self.pbModifyModifier.setText(_translate("Dialog", "<--", None))
        self.tabWidgetModifiersSets.setTabText(self.tabWidgetModifiersSets.indexOf(self.set1), _translate("Dialog", "Set #1", None))
        self.pbRemoveModifier.setText(_translate("Dialog", "Remove modifier", None))
        self.pbAddSet.setText(_translate("Dialog", "Add set of modifiers", None))
        self.pbRemoveSet.setText(_translate("Dialog", "Remove set of modifiers", None))
        self.pbCancel.setText(_translate("Dialog", "Cancel", None))
        self.pbOK.setText(_translate("Dialog", "OK", None))

