# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'converters.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QPlainTextEdit, QPushButton,
    QSizePolicy, QSpacerItem, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget)

class Ui_converters(object):
    def setupUi(self, converters):
        if not converters.objectName():
            converters.setObjectName(u"converters")
        converters.resize(1029, 530)
        self.verticalLayout = QVBoxLayout(converters)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.label_4 = QLabel(converters)
        self.label_4.setObjectName(u"label_4")

        self.verticalLayout.addWidget(self.label_4)

        self.tw_converters = QTableWidget(converters)
        if (self.tw_converters.columnCount() < 3):
            self.tw_converters.setColumnCount(3)
        __qtablewidgetitem = QTableWidgetItem()
        self.tw_converters.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.tw_converters.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.tw_converters.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        self.tw_converters.setObjectName(u"tw_converters")
        self.tw_converters.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tw_converters.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tw_converters.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tw_converters.setSortingEnabled(True)

        self.verticalLayout.addWidget(self.tw_converters)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.pb_add_converter = QPushButton(converters)
        self.pb_add_converter.setObjectName(u"pb_add_converter")

        self.horizontalLayout.addWidget(self.pb_add_converter)

        self.pb_modify_converter = QPushButton(converters)
        self.pb_modify_converter.setObjectName(u"pb_modify_converter")

        self.horizontalLayout.addWidget(self.pb_modify_converter)

        self.pb_delete_converter = QPushButton(converters)
        self.pb_delete_converter.setObjectName(u"pb_delete_converter")

        self.horizontalLayout.addWidget(self.pb_delete_converter)

        self.pb_load_from_file = QPushButton(converters)
        self.pb_load_from_file.setObjectName(u"pb_load_from_file")

        self.horizontalLayout.addWidget(self.pb_load_from_file)

        self.pb_load_from_repo = QPushButton(converters)
        self.pb_load_from_repo.setObjectName(u"pb_load_from_repo")

        self.horizontalLayout.addWidget(self.pb_load_from_repo)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer)


        self.verticalLayout.addLayout(self.horizontalLayout)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.label_2 = QLabel(converters)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setMinimumSize(QSize(120, 0))

        self.horizontalLayout_3.addWidget(self.label_2)

        self.le_converter_name = QLineEdit(converters)
        self.le_converter_name.setObjectName(u"le_converter_name")

        self.horizontalLayout_3.addWidget(self.le_converter_name)

        self.horizontalSpacer_3 = QSpacerItem(10, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_3)


        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.label_3 = QLabel(converters)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setMinimumSize(QSize(120, 0))

        self.horizontalLayout_5.addWidget(self.label_3)

        self.le_converter_description = QLineEdit(converters)
        self.le_converter_description.setObjectName(u"le_converter_description")

        self.horizontalLayout_5.addWidget(self.le_converter_description)

        self.horizontalSpacer_4 = QSpacerItem(10, 20, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_4)


        self.verticalLayout.addLayout(self.horizontalLayout_5)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.label = QLabel(converters)
        self.label.setObjectName(u"label")

        self.verticalLayout_3.addWidget(self.label)

        self.pb_code_help = QPushButton(converters)
        self.pb_code_help.setObjectName(u"pb_code_help")

        self.verticalLayout_3.addWidget(self.pb_code_help)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer_2)


        self.horizontalLayout_2.addLayout(self.verticalLayout_3)

        self.pteCode = QPlainTextEdit(converters)
        self.pteCode.setObjectName(u"pteCode")
        font = QFont()
        font.setFamilies([u"Monospace"])
        self.pteCode.setFont(font)

        self.horizontalLayout_2.addWidget(self.pteCode)

        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.pb_save_converter = QPushButton(converters)
        self.pb_save_converter.setObjectName(u"pb_save_converter")

        self.verticalLayout_2.addWidget(self.pb_save_converter)

        self.pb_cancel_converter = QPushButton(converters)
        self.pb_cancel_converter.setObjectName(u"pb_cancel_converter")

        self.verticalLayout_2.addWidget(self.pb_cancel_converter)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer)


        self.horizontalLayout_2.addLayout(self.verticalLayout_2)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_2)

        self.pb_cancel_widget = QPushButton(converters)
        self.pb_cancel_widget.setObjectName(u"pb_cancel_widget")

        self.horizontalLayout_4.addWidget(self.pb_cancel_widget)

        self.pbOK = QPushButton(converters)
        self.pbOK.setObjectName(u"pbOK")

        self.horizontalLayout_4.addWidget(self.pbOK)


        self.verticalLayout.addLayout(self.horizontalLayout_4)


        self.retranslateUi(converters)

        QMetaObject.connectSlotsByName(converters)
    # setupUi

    def retranslateUi(self, converters):
        converters.setWindowTitle(QCoreApplication.translate("converters", u"Time converters", None))
        self.label_4.setText(QCoreApplication.translate("converters", u"Converters", None))
        ___qtablewidgetitem = self.tw_converters.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("converters", u"Name", None));
        ___qtablewidgetitem1 = self.tw_converters.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("converters", u"Description", None));
        ___qtablewidgetitem2 = self.tw_converters.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("converters", u"Code", None));
        self.pb_add_converter.setText(QCoreApplication.translate("converters", u"Add new converter", None))
        self.pb_modify_converter.setText(QCoreApplication.translate("converters", u"Modify converter", None))
        self.pb_delete_converter.setText(QCoreApplication.translate("converters", u"Delete converter", None))
        self.pb_load_from_file.setText(QCoreApplication.translate("converters", u"Load converters from file", None))
        self.pb_load_from_repo.setText(QCoreApplication.translate("converters", u"Load converters from BORIS repository", None))
        self.label_2.setText(QCoreApplication.translate("converters", u"Name", None))
        self.label_3.setText(QCoreApplication.translate("converters", u"Description", None))
        self.label.setText(QCoreApplication.translate("converters", u"Python code", None))
        self.pb_code_help.setText(QCoreApplication.translate("converters", u"Help", None))
        self.pb_save_converter.setText(QCoreApplication.translate("converters", u"Save converter", None))
        self.pb_cancel_converter.setText(QCoreApplication.translate("converters", u"Cancel", None))
        self.pb_cancel_widget.setText(QCoreApplication.translate("converters", u"Cancel", None))
        self.pbOK.setText(QCoreApplication.translate("converters", u"OK", None))
    # retranslateUi

