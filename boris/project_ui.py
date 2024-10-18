# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'project.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QDateTimeEdit,
    QDialog, QFrame, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPlainTextEdit, QPushButton,
    QRadioButton, QSizePolicy, QSpacerItem, QTabWidget,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

class Ui_dlgProject(object):
    def setupUi(self, dlgProject):
        if not dlgProject.objectName():
            dlgProject.setObjectName(u"dlgProject")
        dlgProject.resize(1202, 697)
        self.verticalLayout_7 = QVBoxLayout(dlgProject)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_6 = QVBoxLayout()
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.tabProject = QTabWidget(dlgProject)
        self.tabProject.setObjectName(u"tabProject")
        self.tabInformation = QWidget()
        self.tabInformation.setObjectName(u"tabInformation")
        self.verticalLayout = QVBoxLayout(self.tabInformation)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_15 = QHBoxLayout()
        self.horizontalLayout_15.setObjectName(u"horizontalLayout_15")
        self.label = QLabel(self.tabInformation)
        self.label.setObjectName(u"label")

        self.horizontalLayout_15.addWidget(self.label)

        self.leProjectName = QLineEdit(self.tabInformation)
        self.leProjectName.setObjectName(u"leProjectName")

        self.horizontalLayout_15.addWidget(self.leProjectName)


        self.verticalLayout.addLayout(self.horizontalLayout_15)

        self.lbProjectFilePath = QLabel(self.tabInformation)
        self.lbProjectFilePath.setObjectName(u"lbProjectFilePath")

        self.verticalLayout.addWidget(self.lbProjectFilePath)

        self.horizontalLayout_18 = QHBoxLayout()
        self.horizontalLayout_18.setObjectName(u"horizontalLayout_18")
        self.label_7 = QLabel(self.tabInformation)
        self.label_7.setObjectName(u"label_7")

        self.horizontalLayout_18.addWidget(self.label_7)

        self.dteDate = QDateTimeEdit(self.tabInformation)
        self.dteDate.setObjectName(u"dteDate")
        self.dteDate.setCalendarPopup(True)

        self.horizontalLayout_18.addWidget(self.dteDate)

        self.horizontalSpacer_10 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_18.addItem(self.horizontalSpacer_10)


        self.verticalLayout.addLayout(self.horizontalLayout_18)

        self.label_6 = QLabel(self.tabInformation)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setAlignment(Qt.AlignLeading|Qt.AlignLeft|Qt.AlignTop)

        self.verticalLayout.addWidget(self.label_6)

        self.teDescription = QPlainTextEdit(self.tabInformation)
        self.teDescription.setObjectName(u"teDescription")

        self.verticalLayout.addWidget(self.teDescription)

        self.horizontalLayout_19 = QHBoxLayout()
        self.horizontalLayout_19.setObjectName(u"horizontalLayout_19")
        self.lbTimeFormat = QLabel(self.tabInformation)
        self.lbTimeFormat.setObjectName(u"lbTimeFormat")

        self.horizontalLayout_19.addWidget(self.lbTimeFormat)

        self.rbSeconds = QRadioButton(self.tabInformation)
        self.rbSeconds.setObjectName(u"rbSeconds")
        self.rbSeconds.setChecked(True)

        self.horizontalLayout_19.addWidget(self.rbSeconds)

        self.rbHMS = QRadioButton(self.tabInformation)
        self.rbHMS.setObjectName(u"rbHMS")

        self.horizontalLayout_19.addWidget(self.rbHMS)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_19.addItem(self.horizontalSpacer_2)


        self.verticalLayout.addLayout(self.horizontalLayout_19)

        self.lb_project_format_version = QLabel(self.tabInformation)
        self.lb_project_format_version.setObjectName(u"lb_project_format_version")

        self.verticalLayout.addWidget(self.lb_project_format_version)

        self.tabProject.addTab(self.tabInformation, "")
        self.tabEthogram = QWidget()
        self.tabEthogram.setObjectName(u"tabEthogram")
        self.verticalLayout_10 = QVBoxLayout(self.tabEthogram)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.verticalLayout_5 = QVBoxLayout()
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.horizontalLayout_11 = QHBoxLayout()
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.twBehaviors = QTableWidget(self.tabEthogram)
        if (self.twBehaviors.columnCount() < 9):
            self.twBehaviors.setColumnCount(9)
        __qtablewidgetitem = QTableWidgetItem()
        self.twBehaviors.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.twBehaviors.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.twBehaviors.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.twBehaviors.setHorizontalHeaderItem(3, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.twBehaviors.setHorizontalHeaderItem(4, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.twBehaviors.setHorizontalHeaderItem(5, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.twBehaviors.setHorizontalHeaderItem(6, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.twBehaviors.setHorizontalHeaderItem(7, __qtablewidgetitem7)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.twBehaviors.setHorizontalHeaderItem(8, __qtablewidgetitem8)
        self.twBehaviors.setObjectName(u"twBehaviors")
        self.twBehaviors.setAutoFillBackground(False)
        self.twBehaviors.setFrameShadow(QFrame.Sunken)
        self.twBehaviors.setMidLineWidth(0)
        self.twBehaviors.setAlternatingRowColors(True)
        self.twBehaviors.setSelectionMode(QAbstractItemView.SingleSelection)
        self.twBehaviors.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.twBehaviors.setSortingEnabled(False)
        self.twBehaviors.horizontalHeader().setProperty(u"showSortIndicator", False)
        self.twBehaviors.verticalHeader().setProperty(u"showSortIndicator", False)

        self.horizontalLayout_11.addWidget(self.twBehaviors)

        self.verticalLayout_11 = QVBoxLayout()
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.pb_behavior = QPushButton(self.tabEthogram)
        self.pb_behavior.setObjectName(u"pb_behavior")

        self.verticalLayout_11.addWidget(self.pb_behavior)

        self.pb_import = QPushButton(self.tabEthogram)
        self.pb_import.setObjectName(u"pb_import")

        self.verticalLayout_11.addWidget(self.pb_import)

        self.pbBehaviorsCategories = QPushButton(self.tabEthogram)
        self.pbBehaviorsCategories.setObjectName(u"pbBehaviorsCategories")

        self.verticalLayout_11.addWidget(self.pbBehaviorsCategories)

        self.verticalSpacer_3 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_11.addItem(self.verticalSpacer_3)

        self.pb_exclusion_matrix = QPushButton(self.tabEthogram)
        self.pb_exclusion_matrix.setObjectName(u"pb_exclusion_matrix")

        self.verticalLayout_11.addWidget(self.pb_exclusion_matrix)

        self.pbExportEthogram = QPushButton(self.tabEthogram)
        self.pbExportEthogram.setObjectName(u"pbExportEthogram")

        self.verticalLayout_11.addWidget(self.pbExportEthogram)


        self.horizontalLayout_11.addLayout(self.verticalLayout_11)


        self.verticalLayout_5.addLayout(self.horizontalLayout_11)

        self.lbObservationsState = QLabel(self.tabEthogram)
        self.lbObservationsState.setObjectName(u"lbObservationsState")

        self.verticalLayout_5.addWidget(self.lbObservationsState)


        self.verticalLayout_10.addLayout(self.verticalLayout_5)

        self.tabProject.addTab(self.tabEthogram, "")
        self.tabSubjects = QWidget()
        self.tabSubjects.setObjectName(u"tabSubjects")
        self.verticalLayout_16 = QVBoxLayout(self.tabSubjects)
        self.verticalLayout_16.setObjectName(u"verticalLayout_16")
        self.verticalLayout_14 = QVBoxLayout()
        self.verticalLayout_14.setObjectName(u"verticalLayout_14")
        self.horizontalLayout_12 = QHBoxLayout()
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.twSubjects = QTableWidget(self.tabSubjects)
        if (self.twSubjects.columnCount() < 3):
            self.twSubjects.setColumnCount(3)
        __qtablewidgetitem9 = QTableWidgetItem()
        self.twSubjects.setHorizontalHeaderItem(0, __qtablewidgetitem9)
        __qtablewidgetitem10 = QTableWidgetItem()
        self.twSubjects.setHorizontalHeaderItem(1, __qtablewidgetitem10)
        __qtablewidgetitem11 = QTableWidgetItem()
        self.twSubjects.setHorizontalHeaderItem(2, __qtablewidgetitem11)
        self.twSubjects.setObjectName(u"twSubjects")
        self.twSubjects.setAutoFillBackground(False)
        self.twSubjects.setFrameShadow(QFrame.Sunken)
        self.twSubjects.setMidLineWidth(0)
        self.twSubjects.setSelectionMode(QAbstractItemView.SingleSelection)
        self.twSubjects.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.twSubjects.setSortingEnabled(False)

        self.horizontalLayout_12.addWidget(self.twSubjects)

        self.verticalLayout_15 = QVBoxLayout()
        self.verticalLayout_15.setObjectName(u"verticalLayout_15")
        self.pb_subjects = QPushButton(self.tabSubjects)
        self.pb_subjects.setObjectName(u"pb_subjects")

        self.verticalLayout_15.addWidget(self.pb_subjects)

        self.pbImportSubjectsFromProject = QPushButton(self.tabSubjects)
        self.pbImportSubjectsFromProject.setObjectName(u"pbImportSubjectsFromProject")

        self.verticalLayout_15.addWidget(self.pbImportSubjectsFromProject)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_15.addItem(self.verticalSpacer_2)

        self.pb_export_subjects = QPushButton(self.tabSubjects)
        self.pb_export_subjects.setObjectName(u"pb_export_subjects")

        self.verticalLayout_15.addWidget(self.pb_export_subjects)


        self.horizontalLayout_12.addLayout(self.verticalLayout_15)


        self.verticalLayout_14.addLayout(self.horizontalLayout_12)

        self.lbSubjectsState = QLabel(self.tabSubjects)
        self.lbSubjectsState.setObjectName(u"lbSubjectsState")

        self.verticalLayout_14.addWidget(self.lbSubjectsState)


        self.verticalLayout_16.addLayout(self.verticalLayout_14)

        self.tabProject.addTab(self.tabSubjects, "")
        self.tabIndependentVariables = QWidget()
        self.tabIndependentVariables.setObjectName(u"tabIndependentVariables")
        self.horizontalLayout_14 = QHBoxLayout(self.tabIndependentVariables)
        self.horizontalLayout_14.setObjectName(u"horizontalLayout_14")
        self.horizontalLayout_13 = QHBoxLayout()
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.twVariables = QTableWidget(self.tabIndependentVariables)
        if (self.twVariables.columnCount() < 5):
            self.twVariables.setColumnCount(5)
        __qtablewidgetitem12 = QTableWidgetItem()
        self.twVariables.setHorizontalHeaderItem(0, __qtablewidgetitem12)
        __qtablewidgetitem13 = QTableWidgetItem()
        self.twVariables.setHorizontalHeaderItem(1, __qtablewidgetitem13)
        __qtablewidgetitem14 = QTableWidgetItem()
        self.twVariables.setHorizontalHeaderItem(2, __qtablewidgetitem14)
        __qtablewidgetitem15 = QTableWidgetItem()
        self.twVariables.setHorizontalHeaderItem(3, __qtablewidgetitem15)
        __qtablewidgetitem16 = QTableWidgetItem()
        self.twVariables.setHorizontalHeaderItem(4, __qtablewidgetitem16)
        self.twVariables.setObjectName(u"twVariables")
        self.twVariables.setAutoFillBackground(False)
        self.twVariables.setFrameShadow(QFrame.Sunken)
        self.twVariables.setMidLineWidth(0)
        self.twVariables.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.twVariables.setDragDropOverwriteMode(False)
        self.twVariables.setAlternatingRowColors(True)
        self.twVariables.setSelectionMode(QAbstractItemView.SingleSelection)
        self.twVariables.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.twVariables.setSortingEnabled(False)
        self.twVariables.horizontalHeader().setProperty(u"showSortIndicator", False)

        self.verticalLayout_2.addWidget(self.twVariables)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.label_2 = QLabel(self.tabIndependentVariables)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setMinimumSize(QSize(120, 0))

        self.horizontalLayout_3.addWidget(self.label_2)

        self.leLabel = QLineEdit(self.tabIndependentVariables)
        self.leLabel.setObjectName(u"leLabel")

        self.horizontalLayout_3.addWidget(self.leLabel)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_3)


        self.verticalLayout_2.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.label_3 = QLabel(self.tabIndependentVariables)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setMinimumSize(QSize(120, 0))

        self.horizontalLayout_5.addWidget(self.label_3)

        self.leDescription = QLineEdit(self.tabIndependentVariables)
        self.leDescription.setObjectName(u"leDescription")

        self.horizontalLayout_5.addWidget(self.leDescription)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_4)


        self.verticalLayout_2.addLayout(self.horizontalLayout_5)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.label_8 = QLabel(self.tabIndependentVariables)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setMinimumSize(QSize(120, 0))

        self.horizontalLayout_6.addWidget(self.label_8)

        self.cbType = QComboBox(self.tabIndependentVariables)
        self.cbType.setObjectName(u"cbType")
        self.cbType.setMinimumSize(QSize(120, 0))

        self.horizontalLayout_6.addWidget(self.cbType)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer_5)


        self.verticalLayout_2.addLayout(self.horizontalLayout_6)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.label_4 = QLabel(self.tabIndependentVariables)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setMinimumSize(QSize(120, 0))

        self.horizontalLayout_7.addWidget(self.label_4)

        self.lePredefined = QLineEdit(self.tabIndependentVariables)
        self.lePredefined.setObjectName(u"lePredefined")

        self.horizontalLayout_7.addWidget(self.lePredefined)

        self.horizontalSpacer_6 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_7.addItem(self.horizontalSpacer_6)


        self.verticalLayout_2.addLayout(self.horizontalLayout_7)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.label_9 = QLabel(self.tabIndependentVariables)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setMinimumSize(QSize(120, 0))

        self.horizontalLayout_8.addWidget(self.label_9)

        self.dte_default_date = QDateTimeEdit(self.tabIndependentVariables)
        self.dte_default_date.setObjectName(u"dte_default_date")

        self.horizontalLayout_8.addWidget(self.dte_default_date)

        self.horizontalSpacer_7 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_8.addItem(self.horizontalSpacer_7)


        self.verticalLayout_2.addLayout(self.horizontalLayout_8)

        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.label_5 = QLabel(self.tabIndependentVariables)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout_9.addWidget(self.label_5)

        self.leSetValues = QLineEdit(self.tabIndependentVariables)
        self.leSetValues.setObjectName(u"leSetValues")

        self.horizontalLayout_9.addWidget(self.leSetValues)

        self.horizontalSpacer_8 = QSpacerItem(40, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_9.addItem(self.horizontalSpacer_8)


        self.verticalLayout_2.addLayout(self.horizontalLayout_9)


        self.horizontalLayout_13.addLayout(self.verticalLayout_2)

        self.verticalLayout_12 = QVBoxLayout()
        self.verticalLayout_12.setObjectName(u"verticalLayout_12")
        self.pbAddVariable = QPushButton(self.tabIndependentVariables)
        self.pbAddVariable.setObjectName(u"pbAddVariable")

        self.verticalLayout_12.addWidget(self.pbAddVariable)

        self.pbRemoveVariable = QPushButton(self.tabIndependentVariables)
        self.pbRemoveVariable.setObjectName(u"pbRemoveVariable")

        self.verticalLayout_12.addWidget(self.pbRemoveVariable)

        self.pbImportVarFromProject = QPushButton(self.tabIndependentVariables)
        self.pbImportVarFromProject.setObjectName(u"pbImportVarFromProject")

        self.verticalLayout_12.addWidget(self.pbImportVarFromProject)

        self.verticalSpacer_4 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_12.addItem(self.verticalSpacer_4)


        self.horizontalLayout_13.addLayout(self.verticalLayout_12)


        self.horizontalLayout_14.addLayout(self.horizontalLayout_13)

        self.tabProject.addTab(self.tabIndependentVariables, "")
        self.tabBehavCodingMap = QWidget()
        self.tabBehavCodingMap.setObjectName(u"tabBehavCodingMap")
        self.verticalLayout_8 = QVBoxLayout(self.tabBehavCodingMap)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.twBehavCodingMap = QTableWidget(self.tabBehavCodingMap)
        if (self.twBehavCodingMap.columnCount() < 2):
            self.twBehavCodingMap.setColumnCount(2)
        __qtablewidgetitem17 = QTableWidgetItem()
        self.twBehavCodingMap.setHorizontalHeaderItem(0, __qtablewidgetitem17)
        __qtablewidgetitem18 = QTableWidgetItem()
        self.twBehavCodingMap.setHorizontalHeaderItem(1, __qtablewidgetitem18)
        self.twBehavCodingMap.setObjectName(u"twBehavCodingMap")
        self.twBehavCodingMap.setAutoFillBackground(False)
        self.twBehavCodingMap.setFrameShadow(QFrame.Sunken)
        self.twBehavCodingMap.setMidLineWidth(0)
        self.twBehavCodingMap.setSelectionMode(QAbstractItemView.SingleSelection)
        self.twBehavCodingMap.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.twBehavCodingMap.setSortingEnabled(False)

        self.horizontalLayout.addWidget(self.twBehavCodingMap)

        self.verticalLayout_4 = QVBoxLayout()
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.pbAddBehaviorsCodingMap = QPushButton(self.tabBehavCodingMap)
        self.pbAddBehaviorsCodingMap.setObjectName(u"pbAddBehaviorsCodingMap")

        self.verticalLayout_4.addWidget(self.pbAddBehaviorsCodingMap)

        self.pbRemoveBehaviorsCodingMap = QPushButton(self.tabBehavCodingMap)
        self.pbRemoveBehaviorsCodingMap.setObjectName(u"pbRemoveBehaviorsCodingMap")

        self.verticalLayout_4.addWidget(self.pbRemoveBehaviorsCodingMap)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_4.addItem(self.verticalSpacer)


        self.horizontalLayout.addLayout(self.verticalLayout_4)


        self.verticalLayout_8.addLayout(self.horizontalLayout)

        self.tabProject.addTab(self.tabBehavCodingMap, "")
        self.tab_time_converters = QWidget()
        self.tab_time_converters.setObjectName(u"tab_time_converters")
        self.verticalLayout_18 = QVBoxLayout(self.tab_time_converters)
        self.verticalLayout_18.setObjectName(u"verticalLayout_18")
        self.label_11 = QLabel(self.tab_time_converters)
        self.label_11.setObjectName(u"label_11")

        self.verticalLayout_18.addWidget(self.label_11)

        self.horizontalLayout_16 = QHBoxLayout()
        self.horizontalLayout_16.setObjectName(u"horizontalLayout_16")
        self.tw_converters = QTableWidget(self.tab_time_converters)
        if (self.tw_converters.columnCount() < 3):
            self.tw_converters.setColumnCount(3)
        __qtablewidgetitem19 = QTableWidgetItem()
        self.tw_converters.setHorizontalHeaderItem(0, __qtablewidgetitem19)
        __qtablewidgetitem20 = QTableWidgetItem()
        self.tw_converters.setHorizontalHeaderItem(1, __qtablewidgetitem20)
        __qtablewidgetitem21 = QTableWidgetItem()
        self.tw_converters.setHorizontalHeaderItem(2, __qtablewidgetitem21)
        self.tw_converters.setObjectName(u"tw_converters")
        self.tw_converters.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tw_converters.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tw_converters.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tw_converters.setSortingEnabled(False)

        self.horizontalLayout_16.addWidget(self.tw_converters)

        self.verticalLayout_17 = QVBoxLayout()
        self.verticalLayout_17.setObjectName(u"verticalLayout_17")
        self.pb_add_converter = QPushButton(self.tab_time_converters)
        self.pb_add_converter.setObjectName(u"pb_add_converter")

        self.verticalLayout_17.addWidget(self.pb_add_converter)

        self.pb_modify_converter = QPushButton(self.tab_time_converters)
        self.pb_modify_converter.setObjectName(u"pb_modify_converter")

        self.verticalLayout_17.addWidget(self.pb_modify_converter)

        self.pb_delete_converter = QPushButton(self.tab_time_converters)
        self.pb_delete_converter.setObjectName(u"pb_delete_converter")

        self.verticalLayout_17.addWidget(self.pb_delete_converter)

        self.pb_load_from_file = QPushButton(self.tab_time_converters)
        self.pb_load_from_file.setObjectName(u"pb_load_from_file")

        self.verticalLayout_17.addWidget(self.pb_load_from_file)

        self.pb_load_from_repo = QPushButton(self.tab_time_converters)
        self.pb_load_from_repo.setObjectName(u"pb_load_from_repo")

        self.verticalLayout_17.addWidget(self.pb_load_from_repo)

        self.verticalSpacer_7 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_17.addItem(self.verticalSpacer_7)


        self.horizontalLayout_16.addLayout(self.verticalLayout_17)


        self.verticalLayout_18.addLayout(self.horizontalLayout_16)

        self.horizontalLayout_17 = QHBoxLayout()
        self.horizontalLayout_17.setObjectName(u"horizontalLayout_17")
        self.label_13 = QLabel(self.tab_time_converters)
        self.label_13.setObjectName(u"label_13")
        self.label_13.setMinimumSize(QSize(120, 0))

        self.horizontalLayout_17.addWidget(self.label_13)

        self.le_converter_name = QLineEdit(self.tab_time_converters)
        self.le_converter_name.setObjectName(u"le_converter_name")

        self.horizontalLayout_17.addWidget(self.le_converter_name)

        self.horizontalSpacer_11 = QSpacerItem(10, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_17.addItem(self.horizontalSpacer_11)


        self.verticalLayout_18.addLayout(self.horizontalLayout_17)

        self.horizontalLayout_10 = QHBoxLayout()
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.label_10 = QLabel(self.tab_time_converters)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setMinimumSize(QSize(120, 0))

        self.horizontalLayout_10.addWidget(self.label_10)

        self.le_converter_description = QLineEdit(self.tab_time_converters)
        self.le_converter_description.setObjectName(u"le_converter_description")

        self.horizontalLayout_10.addWidget(self.le_converter_description)

        self.horizontalSpacer_9 = QSpacerItem(10, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_10.addItem(self.horizontalSpacer_9)


        self.verticalLayout_18.addLayout(self.horizontalLayout_10)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.verticalLayout_9 = QVBoxLayout()
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.label_12 = QLabel(self.tab_time_converters)
        self.label_12.setObjectName(u"label_12")

        self.verticalLayout_9.addWidget(self.label_12)

        self.pb_code_help = QPushButton(self.tab_time_converters)
        self.pb_code_help.setObjectName(u"pb_code_help")

        self.verticalLayout_9.addWidget(self.pb_code_help)

        self.verticalSpacer_5 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_9.addItem(self.verticalSpacer_5)


        self.horizontalLayout_2.addLayout(self.verticalLayout_9)

        self.pteCode = QPlainTextEdit(self.tab_time_converters)
        self.pteCode.setObjectName(u"pteCode")
        font = QFont()
        font.setFamilies([u"Monospace"])
        self.pteCode.setFont(font)

        self.horizontalLayout_2.addWidget(self.pteCode)

        self.verticalLayout_13 = QVBoxLayout()
        self.verticalLayout_13.setObjectName(u"verticalLayout_13")
        self.pb_save_converter = QPushButton(self.tab_time_converters)
        self.pb_save_converter.setObjectName(u"pb_save_converter")

        self.verticalLayout_13.addWidget(self.pb_save_converter)

        self.pb_cancel_converter = QPushButton(self.tab_time_converters)
        self.pb_cancel_converter.setObjectName(u"pb_cancel_converter")

        self.verticalLayout_13.addWidget(self.pb_cancel_converter)

        self.verticalSpacer_6 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_13.addItem(self.verticalSpacer_6)


        self.horizontalLayout_2.addLayout(self.verticalLayout_13)


        self.verticalLayout_18.addLayout(self.horizontalLayout_2)

        self.tabProject.addTab(self.tab_time_converters, "")

        self.verticalLayout_6.addWidget(self.tabProject)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer)

        self.pbCancel = QPushButton(dlgProject)
        self.pbCancel.setObjectName(u"pbCancel")

        self.horizontalLayout_4.addWidget(self.pbCancel)

        self.pbOK = QPushButton(dlgProject)
        self.pbOK.setObjectName(u"pbOK")

        self.horizontalLayout_4.addWidget(self.pbOK)


        self.verticalLayout_6.addLayout(self.horizontalLayout_4)


        self.verticalLayout_7.addLayout(self.verticalLayout_6)


        self.retranslateUi(dlgProject)

        self.tabProject.setCurrentIndex(3)


        QMetaObject.connectSlotsByName(dlgProject)
    # setupUi

    def retranslateUi(self, dlgProject):
        dlgProject.setWindowTitle(QCoreApplication.translate("dlgProject", u"Project", None))
        self.label.setText(QCoreApplication.translate("dlgProject", u"Project name", None))
        self.lbProjectFilePath.setText(QCoreApplication.translate("dlgProject", u"Project file path:", None))
        self.label_7.setText(QCoreApplication.translate("dlgProject", u"Project date and time", None))
        self.dteDate.setDisplayFormat(QCoreApplication.translate("dlgProject", u"yyyy-MM-dd hh:mm", None))
        self.label_6.setText(QCoreApplication.translate("dlgProject", u"Project description", None))
        self.lbTimeFormat.setText(QCoreApplication.translate("dlgProject", u"Project time format", None))
        self.rbSeconds.setText(QCoreApplication.translate("dlgProject", u"seconds", None))
        self.rbHMS.setText(QCoreApplication.translate("dlgProject", u"hh:mm:ss.mss", None))
        self.lb_project_format_version.setText(QCoreApplication.translate("dlgProject", u"Project format version:", None))
        self.tabProject.setTabText(self.tabProject.indexOf(self.tabInformation), QCoreApplication.translate("dlgProject", u"Information", None))
        ___qtablewidgetitem = self.twBehaviors.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("dlgProject", u"Behavior type", None));
        ___qtablewidgetitem1 = self.twBehaviors.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("dlgProject", u"Key", None));
        ___qtablewidgetitem2 = self.twBehaviors.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("dlgProject", u"Code", None));
        ___qtablewidgetitem3 = self.twBehaviors.horizontalHeaderItem(3)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("dlgProject", u"Description", None));
        ___qtablewidgetitem4 = self.twBehaviors.horizontalHeaderItem(4)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("dlgProject", u"Color", None));
        ___qtablewidgetitem5 = self.twBehaviors.horizontalHeaderItem(5)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("dlgProject", u"Category", None));
        ___qtablewidgetitem6 = self.twBehaviors.horizontalHeaderItem(6)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("dlgProject", u"Modifiers", None));
        ___qtablewidgetitem7 = self.twBehaviors.horizontalHeaderItem(7)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("dlgProject", u"Exclusion", None));
        ___qtablewidgetitem8 = self.twBehaviors.horizontalHeaderItem(8)
        ___qtablewidgetitem8.setText(QCoreApplication.translate("dlgProject", u"Modifiers coding map", None));
        self.pb_behavior.setText(QCoreApplication.translate("dlgProject", u"Behavior", None))
        self.pb_import.setText(QCoreApplication.translate("dlgProject", u"Import ethogram", None))
        self.pbBehaviorsCategories.setText(QCoreApplication.translate("dlgProject", u"Behavioral categories", None))
        self.pb_exclusion_matrix.setText(QCoreApplication.translate("dlgProject", u"Exclusion matrix", None))
        self.pbExportEthogram.setText(QCoreApplication.translate("dlgProject", u"Export ethogram", None))
        self.lbObservationsState.setText(QCoreApplication.translate("dlgProject", u"TextLabel", None))
        self.tabProject.setTabText(self.tabProject.indexOf(self.tabEthogram), QCoreApplication.translate("dlgProject", u"Ethogram", None))
        ___qtablewidgetitem9 = self.twSubjects.horizontalHeaderItem(0)
        ___qtablewidgetitem9.setText(QCoreApplication.translate("dlgProject", u"Key", None));
        ___qtablewidgetitem10 = self.twSubjects.horizontalHeaderItem(1)
        ___qtablewidgetitem10.setText(QCoreApplication.translate("dlgProject", u"Subject name", None));
        ___qtablewidgetitem11 = self.twSubjects.horizontalHeaderItem(2)
        ___qtablewidgetitem11.setText(QCoreApplication.translate("dlgProject", u"Description", None));
        self.pb_subjects.setText(QCoreApplication.translate("dlgProject", u"Subjects", None))
        self.pbImportSubjectsFromProject.setText(QCoreApplication.translate("dlgProject", u"Import subjects", None))
        self.pb_export_subjects.setText(QCoreApplication.translate("dlgProject", u"Export subjects", None))
        self.lbSubjectsState.setText(QCoreApplication.translate("dlgProject", u"TextLabel", None))
        self.tabProject.setTabText(self.tabProject.indexOf(self.tabSubjects), QCoreApplication.translate("dlgProject", u"Subjects", None))
        ___qtablewidgetitem12 = self.twVariables.horizontalHeaderItem(0)
        ___qtablewidgetitem12.setText(QCoreApplication.translate("dlgProject", u"Label", None));
        ___qtablewidgetitem13 = self.twVariables.horizontalHeaderItem(1)
        ___qtablewidgetitem13.setText(QCoreApplication.translate("dlgProject", u"Description", None));
        ___qtablewidgetitem14 = self.twVariables.horizontalHeaderItem(2)
        ___qtablewidgetitem14.setText(QCoreApplication.translate("dlgProject", u"Type", None));
        ___qtablewidgetitem15 = self.twVariables.horizontalHeaderItem(3)
        ___qtablewidgetitem15.setText(QCoreApplication.translate("dlgProject", u"Predefined value", None));
        ___qtablewidgetitem16 = self.twVariables.horizontalHeaderItem(4)
        ___qtablewidgetitem16.setText(QCoreApplication.translate("dlgProject", u"Set of values", None));
        self.label_2.setText(QCoreApplication.translate("dlgProject", u"Label", None))
        self.label_3.setText(QCoreApplication.translate("dlgProject", u"Description", None))
        self.label_8.setText(QCoreApplication.translate("dlgProject", u"Type", None))
        self.label_4.setText(QCoreApplication.translate("dlgProject", u"Predefined value", None))
        self.label_9.setText(QCoreApplication.translate("dlgProject", u"Predefined timestamp", None))
        self.dte_default_date.setDisplayFormat(QCoreApplication.translate("dlgProject", u"yyyy-MM-dd hh:mm:ss.zzz", None))
        self.label_5.setText(QCoreApplication.translate("dlgProject", u"Set of values (separated by comma)", None))
        self.pbAddVariable.setText(QCoreApplication.translate("dlgProject", u"Add variable", None))
        self.pbRemoveVariable.setText(QCoreApplication.translate("dlgProject", u"Remove variable", None))
        self.pbImportVarFromProject.setText(QCoreApplication.translate("dlgProject", u"Import variables\n"
"from a BORIS project", None))
        self.tabProject.setTabText(self.tabProject.indexOf(self.tabIndependentVariables), QCoreApplication.translate("dlgProject", u"Independent variables", None))
        ___qtablewidgetitem17 = self.twBehavCodingMap.horizontalHeaderItem(0)
        ___qtablewidgetitem17.setText(QCoreApplication.translate("dlgProject", u"Name", None));
        ___qtablewidgetitem18 = self.twBehavCodingMap.horizontalHeaderItem(1)
        ___qtablewidgetitem18.setText(QCoreApplication.translate("dlgProject", u"Behavior codes", None));
        self.pbAddBehaviorsCodingMap.setText(QCoreApplication.translate("dlgProject", u"Add a behaviors coding map", None))
        self.pbRemoveBehaviorsCodingMap.setText(QCoreApplication.translate("dlgProject", u"Remove behaviors coding map", None))
        self.tabProject.setTabText(self.tabProject.indexOf(self.tabBehavCodingMap), QCoreApplication.translate("dlgProject", u"Behaviors coding map", None))
        self.label_11.setText(QCoreApplication.translate("dlgProject", u"Time converters for external data", None))
        ___qtablewidgetitem19 = self.tw_converters.horizontalHeaderItem(0)
        ___qtablewidgetitem19.setText(QCoreApplication.translate("dlgProject", u"Name", None));
        ___qtablewidgetitem20 = self.tw_converters.horizontalHeaderItem(1)
        ___qtablewidgetitem20.setText(QCoreApplication.translate("dlgProject", u"Description", None));
        ___qtablewidgetitem21 = self.tw_converters.horizontalHeaderItem(2)
        ___qtablewidgetitem21.setText(QCoreApplication.translate("dlgProject", u"Code", None));
        self.pb_add_converter.setText(QCoreApplication.translate("dlgProject", u"Add new converter", None))
        self.pb_modify_converter.setText(QCoreApplication.translate("dlgProject", u"Modify converter", None))
        self.pb_delete_converter.setText(QCoreApplication.translate("dlgProject", u"Delete converter", None))
        self.pb_load_from_file.setText(QCoreApplication.translate("dlgProject", u"Load converters from file", None))
        self.pb_load_from_repo.setText(QCoreApplication.translate("dlgProject", u"Load converters from BORIS repository", None))
        self.label_13.setText(QCoreApplication.translate("dlgProject", u"Name", None))
        self.label_10.setText(QCoreApplication.translate("dlgProject", u"Description", None))
        self.label_12.setText(QCoreApplication.translate("dlgProject", u"Python code", None))
        self.pb_code_help.setText(QCoreApplication.translate("dlgProject", u"Help", None))
        self.pb_save_converter.setText(QCoreApplication.translate("dlgProject", u"Save converter", None))
        self.pb_cancel_converter.setText(QCoreApplication.translate("dlgProject", u"Cancel", None))
        self.tabProject.setTabText(self.tabProject.indexOf(self.tab_time_converters), QCoreApplication.translate("dlgProject", u"Converters", None))
        self.pbCancel.setText(QCoreApplication.translate("dlgProject", u"Cancel", None))
        self.pbOK.setText(QCoreApplication.translate("dlgProject", u"OK", None))
    # retranslateUi

