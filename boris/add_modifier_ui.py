# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'add_modifier.ui'
##
## Created by: Qt User Interface Compiler version 6.8.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog,
    QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QSizePolicy, QSpacerItem,
    QTabWidget, QVBoxLayout, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(1088, 654)
        self.verticalLayout_5 = QVBoxLayout(Dialog)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.cb_ask_at_stop = QCheckBox(Dialog)
        self.cb_ask_at_stop.setObjectName(u"cb_ask_at_stop")

        self.verticalLayout_5.addWidget(self.cb_ask_at_stop)

        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.lbModifier = QLabel(Dialog)
        self.lbModifier.setObjectName(u"lbModifier")

        self.verticalLayout_2.addWidget(self.lbModifier)

        self.leModifier = QLineEdit(Dialog)
        self.leModifier.setObjectName(u"leModifier")

        self.verticalLayout_2.addWidget(self.leModifier)

        self.lbCode = QLabel(Dialog)
        self.lbCode.setObjectName(u"lbCode")

        self.verticalLayout_2.addWidget(self.lbCode)

        self.leCode = QLineEdit(Dialog)
        self.leCode.setObjectName(u"leCode")

        self.verticalLayout_2.addWidget(self.leCode)

        self.lbCodeHelp = QLabel(Dialog)
        self.lbCodeHelp.setObjectName(u"lbCodeHelp")
        self.lbCodeHelp.setWordWrap(True)

        self.verticalLayout_2.addWidget(self.lbCodeHelp)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer)


        self.horizontalLayout_5.addLayout(self.verticalLayout_2)

        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.pbAddModifier = QPushButton(Dialog)
        self.pbAddModifier.setObjectName(u"pbAddModifier")

        self.verticalLayout_3.addWidget(self.pbAddModifier)

        self.pbModifyModifier = QPushButton(Dialog)
        self.pbModifyModifier.setObjectName(u"pbModifyModifier")

        self.verticalLayout_3.addWidget(self.pbModifyModifier)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer_2)


        self.horizontalLayout_5.addLayout(self.verticalLayout_3)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tabWidgetModifiersSets = QTabWidget(Dialog)
        self.tabWidgetModifiersSets.setObjectName(u"tabWidgetModifiersSets")
        self.tabWidgetModifiersSets.setMaximumSize(QSize(16777215, 30))
        self.tabWidgetModifiersSets.setTabPosition(QTabWidget.TabPosition.North)
        self.tabWidgetModifiersSets.setTabShape(QTabWidget.TabShape.Rounded)
        self.tabWidgetModifiersSets.setElideMode(Qt.TextElideMode.ElideNone)
        self.tabWidgetModifiersSets.setDocumentMode(True)

        self.verticalLayout.addWidget(self.tabWidgetModifiersSets)

        self.lb_name = QLabel(Dialog)
        self.lb_name.setObjectName(u"lb_name")

        self.verticalLayout.addWidget(self.lb_name)

        self.le_name = QLineEdit(Dialog)
        self.le_name.setObjectName(u"le_name")

        self.verticalLayout.addWidget(self.le_name)

        self.lb_description = QLabel(Dialog)
        self.lb_description.setObjectName(u"lb_description")

        self.verticalLayout.addWidget(self.lb_description)

        self.le_description = QLineEdit(Dialog)
        self.le_description.setObjectName(u"le_description")

        self.verticalLayout.addWidget(self.le_description)

        self.lbType = QLabel(Dialog)
        self.lbType.setObjectName(u"lbType")

        self.verticalLayout.addWidget(self.lbType)

        self.cbType = QComboBox(Dialog)
        self.cbType.addItem("")
        self.cbType.addItem("")
        self.cbType.addItem("")
        self.cbType.addItem("")
        self.cbType.setObjectName(u"cbType")

        self.verticalLayout.addWidget(self.cbType)

        self.lbValues = QLabel(Dialog)
        self.lbValues.setObjectName(u"lbValues")

        self.verticalLayout.addWidget(self.lbValues)

        self.lwModifiers = QListWidget(Dialog)
        self.lwModifiers.setObjectName(u"lwModifiers")

        self.verticalLayout.addWidget(self.lwModifiers)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.pbMoveUp = QPushButton(Dialog)
        self.pbMoveUp.setObjectName(u"pbMoveUp")

        self.horizontalLayout.addWidget(self.pbMoveUp)

        self.pbMoveDown = QPushButton(Dialog)
        self.pbMoveDown.setObjectName(u"pbMoveDown")

        self.horizontalLayout.addWidget(self.pbMoveDown)

        self.pb_sort_modifiers = QPushButton(Dialog)
        self.pb_sort_modifiers.setObjectName(u"pb_sort_modifiers")

        self.horizontalLayout.addWidget(self.pb_sort_modifiers)

        self.pbRemoveModifier = QPushButton(Dialog)
        self.pbRemoveModifier.setObjectName(u"pbRemoveModifier")

        self.horizontalLayout.addWidget(self.pbRemoveModifier)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.pbAddSet = QPushButton(Dialog)
        self.pbAddSet.setObjectName(u"pbAddSet")

        self.horizontalLayout_3.addWidget(self.pbAddSet)

        self.pbMoveSetLeft = QPushButton(Dialog)
        self.pbMoveSetLeft.setObjectName(u"pbMoveSetLeft")

        self.horizontalLayout_3.addWidget(self.pbMoveSetLeft)

        self.pbMoveSetRight = QPushButton(Dialog)
        self.pbMoveSetRight.setObjectName(u"pbMoveSetRight")

        self.horizontalLayout_3.addWidget(self.pbMoveSetRight)

        self.pbRemoveSet = QPushButton(Dialog)
        self.pbRemoveSet.setObjectName(u"pbRemoveSet")

        self.horizontalLayout_3.addWidget(self.pbRemoveSet)


        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")

        self.verticalLayout.addLayout(self.horizontalLayout_4)

        self.pb_add_subjects = QPushButton(Dialog)
        self.pb_add_subjects.setObjectName(u"pb_add_subjects")

        self.verticalLayout.addWidget(self.pb_add_subjects)

        self.pb_load_file = QPushButton(Dialog)
        self.pb_load_file.setObjectName(u"pb_load_file")

        self.verticalLayout.addWidget(self.pb_load_file)

        self.verticalSpacer_3 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_3)


        self.horizontalLayout_5.addLayout(self.verticalLayout)


        self.verticalLayout_4.addLayout(self.horizontalLayout_5)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.pbCancel = QPushButton(Dialog)
        self.pbCancel.setObjectName(u"pbCancel")

        self.horizontalLayout_2.addWidget(self.pbCancel)

        self.pbOK = QPushButton(Dialog)
        self.pbOK.setObjectName(u"pbOK")

        self.horizontalLayout_2.addWidget(self.pbOK)


        self.verticalLayout_4.addLayout(self.horizontalLayout_2)


        self.verticalLayout_5.addLayout(self.verticalLayout_4)


        self.retranslateUi(Dialog)

        self.tabWidgetModifiersSets.setCurrentIndex(-1)


        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Set modifiers", None))
        self.cb_ask_at_stop.setText(QCoreApplication.translate("Dialog", u"Ask for modifier(s) when behavior stops", None))
        self.lbModifier.setText(QCoreApplication.translate("Dialog", u"Modifier", None))
        self.lbCode.setText(QCoreApplication.translate("Dialog", u"Key code", None))
        self.lbCodeHelp.setText(QCoreApplication.translate("Dialog", u"Key code is case sensitive. Type one character or a function key (F1, F2... F12)", None))
        self.pbAddModifier.setText(QCoreApplication.translate("Dialog", u"->", None))
        self.pbModifyModifier.setText(QCoreApplication.translate("Dialog", u"<-", None))
        self.lb_name.setText(QCoreApplication.translate("Dialog", u"Set name", None))
        self.lb_description.setText(QCoreApplication.translate("Dialog", u"Description", None))
        self.lbType.setText(QCoreApplication.translate("Dialog", u"Modifier type", None))
        self.cbType.setItemText(0, QCoreApplication.translate("Dialog", u"Single selection", None))
        self.cbType.setItemText(1, QCoreApplication.translate("Dialog", u"Multiple selection", None))
        self.cbType.setItemText(2, QCoreApplication.translate("Dialog", u"Numeric", None))
        self.cbType.setItemText(3, QCoreApplication.translate("Dialog", u"Value from external data file", None))

        self.lbValues.setText(QCoreApplication.translate("Dialog", u"Values", None))
        self.pbMoveUp.setText(QCoreApplication.translate("Dialog", u"Move modifier up", None))
        self.pbMoveDown.setText(QCoreApplication.translate("Dialog", u"Move modifier down", None))
        self.pb_sort_modifiers.setText(QCoreApplication.translate("Dialog", u"Sort modifiers", None))
        self.pbRemoveModifier.setText(QCoreApplication.translate("Dialog", u"Remove modifier", None))
        self.pbAddSet.setText(QCoreApplication.translate("Dialog", u"Add set of modifiers", None))
        self.pbMoveSetLeft.setText(QCoreApplication.translate("Dialog", u"Move set left", None))
        self.pbMoveSetRight.setText(QCoreApplication.translate("Dialog", u"Move set right", None))
        self.pbRemoveSet.setText(QCoreApplication.translate("Dialog", u"Remove set of modifiers", None))
        self.pb_add_subjects.setText(QCoreApplication.translate("Dialog", u"Add subjects as modifiers", None))
        self.pb_load_file.setText(QCoreApplication.translate("Dialog", u"Load modifiers from file", None))
        self.pbCancel.setText(QCoreApplication.translate("Dialog", u"Cancel", None))
        self.pbOK.setText(QCoreApplication.translate("Dialog", u"OK", None))
    # retranslateUi

