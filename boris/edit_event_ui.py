# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'edit_event.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGroupBox,
    QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
    QSizePolicy, QSpacerItem, QSpinBox, QVBoxLayout,
    QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(600, 638)
        self.verticalLayout_3 = QVBoxLayout(Form)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.gb_time = QGroupBox(Form)
        self.gb_time.setObjectName(u"gb_time")
        self.verticalLayout = QVBoxLayout(self.gb_time)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.cb_set_time_na = QCheckBox(self.gb_time)
        self.cb_set_time_na.setObjectName(u"cb_set_time_na")

        self.horizontalLayout_8.addWidget(self.cb_set_time_na)

        self.horizontalSpacer_7 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_8.addItem(self.horizontalSpacer_7)


        self.verticalLayout.addLayout(self.horizontalLayout_8)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.lb_time = QLabel(self.gb_time)
        self.lb_time.setObjectName(u"lb_time")

        self.horizontalLayout_3.addWidget(self.lb_time)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.horizontalLayout_3.addLayout(self.horizontalLayout_2)

        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.pb_set_to_current_time = QPushButton(self.gb_time)
        self.pb_set_to_current_time.setObjectName(u"pb_set_to_current_time")

        self.horizontalLayout_9.addWidget(self.pb_set_to_current_time)

        self.horizontalSpacer_8 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_9.addItem(self.horizontalSpacer_8)


        self.verticalLayout.addLayout(self.horizontalLayout_9)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.verticalLayout_3.addWidget(self.gb_time)

        self.gb_image_index = QGroupBox(Form)
        self.gb_image_index.setObjectName(u"gb_image_index")
        self.verticalLayout_2 = QVBoxLayout(self.gb_image_index)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.sb_image_idx = QSpinBox(self.gb_image_index)
        self.sb_image_idx.setObjectName(u"sb_image_idx")
        self.sb_image_idx.setMaximum(10000000)

        self.horizontalLayout_7.addWidget(self.sb_image_idx)

        self.pb_set_to_current_image_index = QPushButton(self.gb_image_index)
        self.pb_set_to_current_image_index.setObjectName(u"pb_set_to_current_image_index")

        self.horizontalLayout_7.addWidget(self.pb_set_to_current_image_index)

        self.horizontalSpacer_6 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_7.addItem(self.horizontalSpacer_6)


        self.verticalLayout_2.addLayout(self.horizontalLayout_7)


        self.verticalLayout_3.addWidget(self.gb_image_index)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.lbSubject = QLabel(Form)
        self.lbSubject.setObjectName(u"lbSubject")

        self.horizontalLayout_4.addWidget(self.lbSubject)

        self.cobSubject = QComboBox(Form)
        self.cobSubject.setObjectName(u"cobSubject")

        self.horizontalLayout_4.addWidget(self.cobSubject)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_2)


        self.verticalLayout_3.addLayout(self.horizontalLayout_4)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.label_2 = QLabel(Form)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout_5.addWidget(self.label_2)

        self.cobCode = QComboBox(Form)
        self.cobCode.setObjectName(u"cobCode")

        self.horizontalLayout_5.addWidget(self.cobCode)

        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_3)


        self.verticalLayout_3.addLayout(self.horizontalLayout_5)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.lb_frame_idx = QLabel(Form)
        self.lb_frame_idx.setObjectName(u"lb_frame_idx")

        self.horizontalLayout_6.addWidget(self.lb_frame_idx)

        self.sb_frame_idx = QSpinBox(Form)
        self.sb_frame_idx.setObjectName(u"sb_frame_idx")
        self.sb_frame_idx.setMinimum(0)
        self.sb_frame_idx.setMaximum(100000000)

        self.horizontalLayout_6.addWidget(self.sb_frame_idx)

        self.cb_set_frame_idx_na = QCheckBox(Form)
        self.cb_set_frame_idx_na.setObjectName(u"cb_set_frame_idx_na")

        self.horizontalLayout_6.addWidget(self.cb_set_frame_idx_na)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer_5)


        self.verticalLayout_3.addLayout(self.horizontalLayout_6)

        self.label_4 = QLabel(Form)
        self.label_4.setObjectName(u"label_4")

        self.verticalLayout_3.addWidget(self.label_4)

        self.leComment = QPlainTextEdit(Form)
        self.leComment.setObjectName(u"leComment")

        self.verticalLayout_3.addWidget(self.leComment)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_4)

        self.pbCancel = QPushButton(Form)
        self.pbCancel.setObjectName(u"pbCancel")

        self.horizontalLayout.addWidget(self.pbCancel)

        self.pbOK = QPushButton(Form)
        self.pbOK.setObjectName(u"pbOK")

        self.horizontalLayout.addWidget(self.pbOK)


        self.verticalLayout_3.addLayout(self.horizontalLayout)


        self.retranslateUi(Form)

        self.pbOK.setDefault(True)


        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Edit event", None))
        self.gb_time.setTitle(QCoreApplication.translate("Form", u"Time", None))
        self.cb_set_time_na.setText(QCoreApplication.translate("Form", u"Set time to NA", None))
        self.lb_time.setText("")
        self.pb_set_to_current_time.setText(QCoreApplication.translate("Form", u"Set to current time", None))
        self.gb_image_index.setTitle(QCoreApplication.translate("Form", u"Image index", None))
        self.pb_set_to_current_image_index.setText(QCoreApplication.translate("Form", u"Set to current image index", None))
        self.lbSubject.setText(QCoreApplication.translate("Form", u"Subject", None))
        self.label_2.setText(QCoreApplication.translate("Form", u"Behavior", None))
        self.lb_frame_idx.setText(QCoreApplication.translate("Form", u"Frame index", None))
        self.cb_set_frame_idx_na.setText(QCoreApplication.translate("Form", u"Set NA", None))
        self.label_4.setText(QCoreApplication.translate("Form", u"Comment", None))
        self.pbCancel.setText(QCoreApplication.translate("Form", u"Cancel", None))
        self.pbOK.setText(QCoreApplication.translate("Form", u"OK", None))
    # retranslateUi
