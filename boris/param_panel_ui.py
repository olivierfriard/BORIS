# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'param_panel.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QFrame,
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QRadioButton, QSizePolicy, QSpacerItem,
    QSpinBox, QVBoxLayout, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.resize(1037, 890)
        self.verticalLayout_4 = QVBoxLayout(Dialog)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.lbSubjects = QLabel(Dialog)
        self.lbSubjects.setObjectName(u"lbSubjects")

        self.verticalLayout_2.addWidget(self.lbSubjects)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.pbSelectAllSubjects = QPushButton(Dialog)
        self.pbSelectAllSubjects.setObjectName(u"pbSelectAllSubjects")

        self.horizontalLayout_3.addWidget(self.pbSelectAllSubjects)

        self.pbUnselectAllSubjects = QPushButton(Dialog)
        self.pbUnselectAllSubjects.setObjectName(u"pbUnselectAllSubjects")

        self.horizontalLayout_3.addWidget(self.pbUnselectAllSubjects)

        self.pbReverseSubjectsSelection = QPushButton(Dialog)
        self.pbReverseSubjectsSelection.setObjectName(u"pbReverseSubjectsSelection")

        self.horizontalLayout_3.addWidget(self.pbReverseSubjectsSelection)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_4)


        self.verticalLayout_2.addLayout(self.horizontalLayout_3)

        self.lwSubjects = QListWidget(Dialog)
        self.lwSubjects.setObjectName(u"lwSubjects")

        self.verticalLayout_2.addWidget(self.lwSubjects)

        self.lbBehaviors = QLabel(Dialog)
        self.lbBehaviors.setObjectName(u"lbBehaviors")

        self.verticalLayout_2.addWidget(self.lbBehaviors)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.pbSelectAllBehaviors = QPushButton(Dialog)
        self.pbSelectAllBehaviors.setObjectName(u"pbSelectAllBehaviors")

        self.horizontalLayout_4.addWidget(self.pbSelectAllBehaviors)

        self.pbUnselectAllBehaviors = QPushButton(Dialog)
        self.pbUnselectAllBehaviors.setObjectName(u"pbUnselectAllBehaviors")

        self.horizontalLayout_4.addWidget(self.pbUnselectAllBehaviors)

        self.pbReverseBehaviorsSelection = QPushButton(Dialog)
        self.pbReverseBehaviorsSelection.setObjectName(u"pbReverseBehaviorsSelection")

        self.horizontalLayout_4.addWidget(self.pbReverseBehaviorsSelection)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_5)


        self.verticalLayout_2.addLayout(self.horizontalLayout_4)

        self.lwBehaviors = QListWidget(Dialog)
        self.lwBehaviors.setObjectName(u"lwBehaviors")

        self.verticalLayout_2.addWidget(self.lwBehaviors)

        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.cbIncludeModifiers = QCheckBox(Dialog)
        self.cbIncludeModifiers.setObjectName(u"cbIncludeModifiers")

        self.horizontalLayout_9.addWidget(self.cbIncludeModifiers)

        self.cb_exclude_non_coded_modifiers = QCheckBox(Dialog)
        self.cb_exclude_non_coded_modifiers.setObjectName(u"cb_exclude_non_coded_modifiers")
        self.cb_exclude_non_coded_modifiers.setChecked(True)

        self.horizontalLayout_9.addWidget(self.cb_exclude_non_coded_modifiers)

        self.cbExcludeBehaviors = QCheckBox(Dialog)
        self.cbExcludeBehaviors.setObjectName(u"cbExcludeBehaviors")

        self.horizontalLayout_9.addWidget(self.cbExcludeBehaviors)

        self.horizontalSpacer_7 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_9.addItem(self.horizontalSpacer_7)


        self.verticalLayout_2.addLayout(self.horizontalLayout_9)

        self.frm_time_bin_size = QFrame(Dialog)
        self.frm_time_bin_size.setObjectName(u"frm_time_bin_size")
        self.frm_time_bin_size.setFrameShape(QFrame.StyledPanel)
        self.frm_time_bin_size.setFrameShadow(QFrame.Raised)
        self.horizontalLayout_8 = QHBoxLayout(self.frm_time_bin_size)
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.lb_time_bin_size = QLabel(self.frm_time_bin_size)
        self.lb_time_bin_size.setObjectName(u"lb_time_bin_size")

        self.horizontalLayout_7.addWidget(self.lb_time_bin_size)

        self.sb_time_bin_size = QSpinBox(self.frm_time_bin_size)
        self.sb_time_bin_size.setObjectName(u"sb_time_bin_size")
        self.sb_time_bin_size.setMaximum(86400)
        self.sb_time_bin_size.setSingleStep(10)

        self.horizontalLayout_7.addWidget(self.sb_time_bin_size)

        self.horizontalSpacer_8 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_7.addItem(self.horizontalSpacer_8)


        self.horizontalLayout_8.addLayout(self.horizontalLayout_7)


        self.verticalLayout_2.addWidget(self.frm_time_bin_size)

        self.frm_time = QFrame(Dialog)
        self.frm_time.setObjectName(u"frm_time")
        self.frm_time.setFrameShape(QFrame.StyledPanel)
        self.frm_time.setFrameShadow(QFrame.Raised)
        self.verticalLayout_3 = QVBoxLayout(self.frm_time)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.lb_time_interval = QLabel(self.frm_time)
        self.lb_time_interval.setObjectName(u"lb_time_interval")

        self.verticalLayout_3.addWidget(self.lb_time_interval)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.rb_observed_events = QRadioButton(self.frm_time)
        self.rb_observed_events.setObjectName(u"rb_observed_events")

        self.horizontalLayout_5.addWidget(self.rb_observed_events)

        self.rb_user_defined = QRadioButton(self.frm_time)
        self.rb_user_defined.setObjectName(u"rb_user_defined")

        self.horizontalLayout_5.addWidget(self.rb_user_defined)

        self.rb_obs_interval = QRadioButton(self.frm_time)
        self.rb_obs_interval.setObjectName(u"rb_obs_interval")

        self.horizontalLayout_5.addWidget(self.rb_obs_interval)

        self.rb_media_duration = QRadioButton(self.frm_time)
        self.rb_media_duration.setObjectName(u"rb_media_duration")
        self.rb_media_duration.setCheckable(True)
        self.rb_media_duration.setChecked(False)

        self.horizontalLayout_5.addWidget(self.rb_media_duration)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_3)


        self.verticalLayout_3.addLayout(self.horizontalLayout_5)

        self.frm_time_interval = QFrame(self.frm_time)
        self.frm_time_interval.setObjectName(u"frm_time_interval")
        self.frm_time_interval.setFrameShape(QFrame.StyledPanel)
        self.frm_time_interval.setFrameShadow(QFrame.Raised)
        self.verticalLayout = QVBoxLayout(self.frm_time_interval)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.lbStartTime = QLabel(self.frm_time_interval)
        self.lbStartTime.setObjectName(u"lbStartTime")

        self.horizontalLayout.addWidget(self.lbStartTime)

        self.label_2 = QLabel(self.frm_time_interval)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout.addWidget(self.label_2)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_2)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.lbEndTime = QLabel(self.frm_time_interval)
        self.lbEndTime.setObjectName(u"lbEndTime")

        self.horizontalLayout_6.addWidget(self.lbEndTime)

        self.label_3 = QLabel(self.frm_time_interval)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout_6.addWidget(self.label_3)

        self.horizontalSpacer_6 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer_6)


        self.verticalLayout.addLayout(self.horizontalLayout_6)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.verticalLayout_3.addWidget(self.frm_time_interval)


        self.verticalLayout_2.addWidget(self.frm_time)

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


        self.verticalLayout_2.addLayout(self.horizontalLayout_2)


        self.verticalLayout_4.addLayout(self.verticalLayout_2)


        self.retranslateUi(Dialog)

        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"Parameters", None))
        self.lbSubjects.setText(QCoreApplication.translate("Dialog", u"Subjects", None))
        self.pbSelectAllSubjects.setText(QCoreApplication.translate("Dialog", u"Select all", None))
        self.pbUnselectAllSubjects.setText(QCoreApplication.translate("Dialog", u"Unselect all", None))
        self.pbReverseSubjectsSelection.setText(QCoreApplication.translate("Dialog", u"Reverse selection", None))
        self.lbBehaviors.setText(QCoreApplication.translate("Dialog", u"Behaviors", None))
        self.pbSelectAllBehaviors.setText(QCoreApplication.translate("Dialog", u"Select all", None))
        self.pbUnselectAllBehaviors.setText(QCoreApplication.translate("Dialog", u"Unselect all", None))
        self.pbReverseBehaviorsSelection.setText(QCoreApplication.translate("Dialog", u"Reverse selection", None))
        self.cbIncludeModifiers.setText(QCoreApplication.translate("Dialog", u"Include modifiers", None))
        self.cb_exclude_non_coded_modifiers.setText(QCoreApplication.translate("Dialog", u"Exclude non coded modifiers", None))
        self.cbExcludeBehaviors.setText(QCoreApplication.translate("Dialog", u"Exclude behaviors without events", None))
        self.lb_time_bin_size.setText(QCoreApplication.translate("Dialog", u"Time bin size (s)", None))
        self.lb_time_interval.setText(QCoreApplication.translate("Dialog", u"Time interval", None))
        self.rb_observed_events.setText(QCoreApplication.translate("Dialog", u"Observed events", None))
        self.rb_user_defined.setText(QCoreApplication.translate("Dialog", u"User defined", None))
        self.rb_obs_interval.setText(QCoreApplication.translate("Dialog", u"Interval of observation", None))
        self.rb_media_duration.setText(QCoreApplication.translate("Dialog", u"Media file(s) duration", None))
        self.lbStartTime.setText(QCoreApplication.translate("Dialog", u"Start time", None))
        self.label_2.setText("")
        self.lbEndTime.setText(QCoreApplication.translate("Dialog", u"End time", None))
        self.label_3.setText("")
        self.pbCancel.setText(QCoreApplication.translate("Dialog", u"Cancel", None))
        self.pbOK.setText(QCoreApplication.translate("Dialog", u"OK", None))
    # retranslateUi

