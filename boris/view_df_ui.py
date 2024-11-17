# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'view_df.ui'
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
from PySide6.QtWidgets import (QApplication, QHBoxLayout, QHeaderView, QLabel,
    QPushButton, QSizePolicy, QSpacerItem, QTableView,
    QVBoxLayout, QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(400, 300)
        self.verticalLayout_2 = QVBoxLayout(Form)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.lb_plugin_info = QLabel(Form)
        self.lb_plugin_info.setObjectName(u"lb_plugin_info")

        self.verticalLayout_2.addWidget(self.lb_plugin_info)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.tv_df = QTableView(Form)
        self.tv_df.setObjectName(u"tv_df")

        self.verticalLayout.addWidget(self.tv_df)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)

        self.pb_save = QPushButton(Form)
        self.pb_save.setObjectName(u"pb_save")

        self.horizontalLayout.addWidget(self.pb_save)

        self.pb_close = QPushButton(Form)
        self.pb_close.setObjectName(u"pb_close")

        self.horizontalLayout.addWidget(self.pb_close)


        self.verticalLayout.addLayout(self.horizontalLayout)


        self.verticalLayout_2.addLayout(self.verticalLayout)


        self.retranslateUi(Form)

        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"Form", None))
        self.lb_plugin_info.setText(QCoreApplication.translate("Form", u"TextLabel", None))
        self.pb_save.setText(QCoreApplication.translate("Form", u"Save results", None))
        self.pb_close.setText(QCoreApplication.translate("Form", u"Close", None))
    # retranslateUi

