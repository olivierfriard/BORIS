# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'video_equalizer.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QHBoxLayout, QLabel,
    QPushButton, QSizePolicy, QSlider, QSpacerItem,
    QVBoxLayout, QWidget)

class Ui_Equalizer(object):
    def setupUi(self, Equalizer):
        if not Equalizer.objectName():
            Equalizer.setObjectName(u"Equalizer")
        Equalizer.resize(388, 284)
        self.verticalLayout = QVBoxLayout(Equalizer)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label_6 = QLabel(Equalizer)
        self.label_6.setObjectName(u"label_6")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_6.sizePolicy().hasHeightForWidth())
        self.label_6.setSizePolicy(sizePolicy)
        font = QFont()
        font.setBold(True)
        self.label_6.setFont(font)

        self.verticalLayout.addWidget(self.label_6)

        self.cb_player = QComboBox(Equalizer)
        self.cb_player.setObjectName(u"cb_player")

        self.verticalLayout.addWidget(self.cb_player)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.label = QLabel(Equalizer)
        self.label.setObjectName(u"label")
        self.label.setMinimumSize(QSize(70, 0))
        self.label.setMaximumSize(QSize(70, 16777215))

        self.horizontalLayout.addWidget(self.label)

        self.hs_brightness = QSlider(Equalizer)
        self.hs_brightness.setObjectName(u"hs_brightness")
        self.hs_brightness.setMinimumSize(QSize(200, 0))
        self.hs_brightness.setMaximumSize(QSize(200, 16777215))
        self.hs_brightness.setMinimum(-100)
        self.hs_brightness.setValue(0)
        self.hs_brightness.setOrientation(Qt.Horizontal)

        self.horizontalLayout.addWidget(self.hs_brightness)

        self.lb_brightness = QLabel(Equalizer)
        self.lb_brightness.setObjectName(u"lb_brightness")
        self.lb_brightness.setMinimumSize(QSize(25, 0))
        self.lb_brightness.setMaximumSize(QSize(25, 16777215))

        self.horizontalLayout.addWidget(self.lb_brightness)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label_2 = QLabel(Equalizer)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setMinimumSize(QSize(70, 0))
        self.label_2.setMaximumSize(QSize(70, 16777215))

        self.horizontalLayout_2.addWidget(self.label_2)

        self.hs_contrast = QSlider(Equalizer)
        self.hs_contrast.setObjectName(u"hs_contrast")
        self.hs_contrast.setMinimumSize(QSize(200, 0))
        self.hs_contrast.setMaximumSize(QSize(200, 16777215))
        self.hs_contrast.setMinimum(-100)
        self.hs_contrast.setValue(0)
        self.hs_contrast.setOrientation(Qt.Horizontal)

        self.horizontalLayout_2.addWidget(self.hs_contrast)

        self.lb_contrast = QLabel(Equalizer)
        self.lb_contrast.setObjectName(u"lb_contrast")
        self.lb_contrast.setMinimumSize(QSize(25, 0))
        self.lb_contrast.setMaximumSize(QSize(25, 16777215))

        self.horizontalLayout_2.addWidget(self.lb_contrast)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.label_3 = QLabel(Equalizer)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setMinimumSize(QSize(70, 0))
        self.label_3.setMaximumSize(QSize(70, 16777215))

        self.horizontalLayout_3.addWidget(self.label_3)

        self.hs_saturation = QSlider(Equalizer)
        self.hs_saturation.setObjectName(u"hs_saturation")
        self.hs_saturation.setMinimumSize(QSize(200, 0))
        self.hs_saturation.setMaximumSize(QSize(200, 16777215))
        self.hs_saturation.setMinimum(-100)
        self.hs_saturation.setValue(0)
        self.hs_saturation.setOrientation(Qt.Horizontal)

        self.horizontalLayout_3.addWidget(self.hs_saturation)

        self.lb_saturation = QLabel(Equalizer)
        self.lb_saturation.setObjectName(u"lb_saturation")
        self.lb_saturation.setMinimumSize(QSize(25, 0))
        self.lb_saturation.setMaximumSize(QSize(25, 16777215))

        self.horizontalLayout_3.addWidget(self.lb_saturation)


        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.label_4 = QLabel(Equalizer)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setMinimumSize(QSize(70, 0))
        self.label_4.setMaximumSize(QSize(70, 16777215))

        self.horizontalLayout_4.addWidget(self.label_4)

        self.hs_gamma = QSlider(Equalizer)
        self.hs_gamma.setObjectName(u"hs_gamma")
        self.hs_gamma.setMinimumSize(QSize(200, 0))
        self.hs_gamma.setMaximumSize(QSize(200, 16777215))
        self.hs_gamma.setMinimum(-100)
        self.hs_gamma.setValue(0)
        self.hs_gamma.setOrientation(Qt.Horizontal)

        self.horizontalLayout_4.addWidget(self.hs_gamma)

        self.lb_gamma = QLabel(Equalizer)
        self.lb_gamma.setObjectName(u"lb_gamma")
        self.lb_gamma.setMinimumSize(QSize(25, 0))
        self.lb_gamma.setMaximumSize(QSize(25, 16777215))

        self.horizontalLayout_4.addWidget(self.lb_gamma)


        self.verticalLayout.addLayout(self.horizontalLayout_4)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.label_5 = QLabel(Equalizer)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setMinimumSize(QSize(70, 0))
        self.label_5.setMaximumSize(QSize(70, 16777215))

        self.horizontalLayout_5.addWidget(self.label_5)

        self.hs_hue = QSlider(Equalizer)
        self.hs_hue.setObjectName(u"hs_hue")
        self.hs_hue.setMinimumSize(QSize(200, 0))
        self.hs_hue.setMaximumSize(QSize(200, 16777215))
        self.hs_hue.setMinimum(-100)
        self.hs_hue.setValue(0)
        self.hs_hue.setOrientation(Qt.Horizontal)

        self.horizontalLayout_5.addWidget(self.hs_hue)

        self.lb_hue = QLabel(Equalizer)
        self.lb_hue.setObjectName(u"lb_hue")
        self.lb_hue.setMinimumSize(QSize(25, 0))
        self.lb_hue.setMaximumSize(QSize(25, 16777215))

        self.horizontalLayout_5.addWidget(self.lb_hue)


        self.verticalLayout.addLayout(self.horizontalLayout_5)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.pb_reset_all = QPushButton(Equalizer)
        self.pb_reset_all.setObjectName(u"pb_reset_all")

        self.horizontalLayout_6.addWidget(self.pb_reset_all)

        self.pb_reset = QPushButton(Equalizer)
        self.pb_reset.setObjectName(u"pb_reset")

        self.horizontalLayout_6.addWidget(self.pb_reset)


        self.verticalLayout.addLayout(self.horizontalLayout_6)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_7.addItem(self.horizontalSpacer)

        self.pb_close = QPushButton(Equalizer)
        self.pb_close.setObjectName(u"pb_close")

        self.horizontalLayout_7.addWidget(self.pb_close)


        self.verticalLayout.addLayout(self.horizontalLayout_7)


        self.retranslateUi(Equalizer)

        QMetaObject.connectSlotsByName(Equalizer)
    # setupUi

    def retranslateUi(self, Equalizer):
        Equalizer.setWindowTitle(QCoreApplication.translate("Equalizer", u"Video equalizer", None))
        self.label_6.setText(QCoreApplication.translate("Equalizer", u"Video equalizer", None))
        self.label.setText(QCoreApplication.translate("Equalizer", u"Brightness", None))
        self.lb_brightness.setText(QCoreApplication.translate("Equalizer", u"0", None))
        self.label_2.setText(QCoreApplication.translate("Equalizer", u"Contrast", None))
        self.lb_contrast.setText(QCoreApplication.translate("Equalizer", u"0", None))
        self.label_3.setText(QCoreApplication.translate("Equalizer", u"Saturation", None))
        self.lb_saturation.setText(QCoreApplication.translate("Equalizer", u"0", None))
        self.label_4.setText(QCoreApplication.translate("Equalizer", u"Gamma", None))
        self.lb_gamma.setText(QCoreApplication.translate("Equalizer", u"0", None))
        self.label_5.setText(QCoreApplication.translate("Equalizer", u"Hue", None))
        self.lb_hue.setText(QCoreApplication.translate("Equalizer", u"0", None))
        self.pb_reset_all.setText(QCoreApplication.translate("Equalizer", u"Reset all players", None))
        self.pb_reset.setText(QCoreApplication.translate("Equalizer", u"Reset current player", None))
        self.pb_close.setText(QCoreApplication.translate("Equalizer", u"Close", None))
    # retranslateUi

