# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'observation.ui'
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
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QDateTimeEdit,
    QDoubleSpinBox, QGroupBox, QHBoxLayout, QHeaderView,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QRadioButton, QSizePolicy, QSpacerItem,
    QSpinBox, QSplitter, QStackedWidget, QTabWidget,
    QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout,
    QWidget)

class Ui_Form(object):
    def setupUi(self, Form):
        if not Form.objectName():
            Form.setObjectName(u"Form")
        Form.resize(1278, 677)
        self.verticalLayout_6 = QVBoxLayout(Form)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.label = QLabel(Form)
        self.label.setObjectName(u"label")

        self.horizontalLayout_2.addWidget(self.label)

        self.lb_star = QLabel(Form)
        self.lb_star.setObjectName(u"lb_star")
        font = QFont()
        font.setPointSize(14)
        self.lb_star.setFont(font)
        self.lb_star.setStyleSheet(u"color: red")

        self.horizontalLayout_2.addWidget(self.lb_star)

        self.leObservationId = QLineEdit(Form)
        self.leObservationId.setObjectName(u"leObservationId")

        self.horizontalLayout_2.addWidget(self.leObservationId)

        self.label_8 = QLabel(Form)
        self.label_8.setObjectName(u"label_8")

        self.horizontalLayout_2.addWidget(self.label_8)

        self.dteDate = QDateTimeEdit(Form)
        self.dteDate.setObjectName(u"dteDate")
        self.dteDate.setCalendarPopup(True)

        self.horizontalLayout_2.addWidget(self.dteDate)


        self.verticalLayout_6.addLayout(self.horizontalLayout_2)

        self.splitter = QSplitter(Form)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.layoutWidget = QWidget(self.splitter)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.verticalLayout_2 = QVBoxLayout(self.layoutWidget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.label_9 = QLabel(self.layoutWidget)
        self.label_9.setObjectName(u"label_9")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.label_9.sizePolicy().hasHeightForWidth())
        self.label_9.setSizePolicy(sizePolicy)
        self.label_9.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.verticalLayout_2.addWidget(self.label_9)

        self.teDescription = QTextEdit(self.layoutWidget)
        self.teDescription.setObjectName(u"teDescription")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.teDescription.sizePolicy().hasHeightForWidth())
        self.teDescription.setSizePolicy(sizePolicy1)
        self.teDescription.setMaximumSize(QSize(16777215, 16777215))
        self.teDescription.setAcceptDrops(False)

        self.verticalLayout_2.addWidget(self.teDescription)

        self.cb_time_offset = QCheckBox(self.layoutWidget)
        self.cb_time_offset.setObjectName(u"cb_time_offset")

        self.verticalLayout_2.addWidget(self.cb_time_offset)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.lbTimeOffset = QLabel(self.layoutWidget)
        self.lbTimeOffset.setObjectName(u"lbTimeOffset")

        self.horizontalLayout_6.addWidget(self.lbTimeOffset)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_6.addItem(self.horizontalSpacer_2)


        self.verticalLayout_2.addLayout(self.horizontalLayout_6)

        self.cb_observation_time_interval = QCheckBox(self.layoutWidget)
        self.cb_observation_time_interval.setObjectName(u"cb_observation_time_interval")

        self.verticalLayout_2.addWidget(self.cb_observation_time_interval)

        self.splitter.addWidget(self.layoutWidget)
        self.layoutWidget1 = QWidget(self.splitter)
        self.layoutWidget1.setObjectName(u"layoutWidget1")
        self.verticalLayout_11 = QVBoxLayout(self.layoutWidget1)
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.verticalLayout_11.setContentsMargins(0, 0, 0, 0)
        self.label_3 = QLabel(self.layoutWidget1)
        self.label_3.setObjectName(u"label_3")

        self.verticalLayout_11.addWidget(self.label_3)

        self.twIndepVariables = QTableWidget(self.layoutWidget1)
        if (self.twIndepVariables.columnCount() < 3):
            self.twIndepVariables.setColumnCount(3)
        __qtablewidgetitem = QTableWidgetItem()
        self.twIndepVariables.setHorizontalHeaderItem(0, __qtablewidgetitem)
        __qtablewidgetitem1 = QTableWidgetItem()
        self.twIndepVariables.setHorizontalHeaderItem(1, __qtablewidgetitem1)
        __qtablewidgetitem2 = QTableWidgetItem()
        self.twIndepVariables.setHorizontalHeaderItem(2, __qtablewidgetitem2)
        self.twIndepVariables.setObjectName(u"twIndepVariables")

        self.verticalLayout_11.addWidget(self.twIndepVariables)

        self.splitter.addWidget(self.layoutWidget1)

        self.verticalLayout_6.addWidget(self.splitter)

        self.gb_observation_type = QGroupBox(Form)
        self.gb_observation_type.setObjectName(u"gb_observation_type")
        self.horizontalLayout_7 = QHBoxLayout(self.gb_observation_type)
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.rb_media_files = QRadioButton(self.gb_observation_type)
        self.rb_media_files.setObjectName(u"rb_media_files")

        self.horizontalLayout_4.addWidget(self.rb_media_files)

        self.rb_live = QRadioButton(self.gb_observation_type)
        self.rb_live.setObjectName(u"rb_live")

        self.horizontalLayout_4.addWidget(self.rb_live)

        self.rb_images = QRadioButton(self.gb_observation_type)
        self.rb_images.setObjectName(u"rb_images")
        self.rb_images.setEnabled(True)

        self.horizontalLayout_4.addWidget(self.rb_images)

        self.horizontalSpacer_4 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_4.addItem(self.horizontalSpacer_4)


        self.horizontalLayout_7.addLayout(self.horizontalLayout_4)


        self.verticalLayout_6.addWidget(self.gb_observation_type)

        self.sw_observation_type = QStackedWidget(Form)
        self.sw_observation_type.setObjectName(u"sw_observation_type")
        self.page = QWidget()
        self.page.setObjectName(u"page")
        self.sw_observation_type.addWidget(self.page)
        self.pg_media_files = QWidget()
        self.pg_media_files.setObjectName(u"pg_media_files")
        self.verticalLayout_7 = QVBoxLayout(self.pg_media_files)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.tabWidget = QTabWidget(self.pg_media_files)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tab_player_1 = QWidget()
        self.tab_player_1.setObjectName(u"tab_player_1")
        self.verticalLayout = QVBoxLayout(self.tab_player_1)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.twVideo1 = QTableWidget(self.tab_player_1)
        if (self.twVideo1.columnCount() < 7):
            self.twVideo1.setColumnCount(7)
        __qtablewidgetitem3 = QTableWidgetItem()
        self.twVideo1.setHorizontalHeaderItem(0, __qtablewidgetitem3)
        __qtablewidgetitem4 = QTableWidgetItem()
        self.twVideo1.setHorizontalHeaderItem(1, __qtablewidgetitem4)
        __qtablewidgetitem5 = QTableWidgetItem()
        self.twVideo1.setHorizontalHeaderItem(2, __qtablewidgetitem5)
        __qtablewidgetitem6 = QTableWidgetItem()
        self.twVideo1.setHorizontalHeaderItem(3, __qtablewidgetitem6)
        __qtablewidgetitem7 = QTableWidgetItem()
        self.twVideo1.setHorizontalHeaderItem(4, __qtablewidgetitem7)
        __qtablewidgetitem8 = QTableWidgetItem()
        self.twVideo1.setHorizontalHeaderItem(5, __qtablewidgetitem8)
        __qtablewidgetitem9 = QTableWidgetItem()
        self.twVideo1.setHorizontalHeaderItem(6, __qtablewidgetitem9)
        self.twVideo1.setObjectName(u"twVideo1")
        self.twVideo1.setEditTriggers(QAbstractItemView.EditTrigger.AnyKeyPressed|QAbstractItemView.EditTrigger.DoubleClicked|QAbstractItemView.EditTrigger.EditKeyPressed)
        self.twVideo1.setAlternatingRowColors(True)
        self.twVideo1.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.twVideo1.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.twVideo1.setTextElideMode(Qt.TextElideMode.ElideNone)

        self.verticalLayout_3.addWidget(self.twVideo1)


        self.verticalLayout.addLayout(self.verticalLayout_3)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.pbAddVideo = QPushButton(self.tab_player_1)
        self.pbAddVideo.setObjectName(u"pbAddVideo")

        self.horizontalLayout_3.addWidget(self.pbAddVideo)

        self.pbRemoveVideo = QPushButton(self.tab_player_1)
        self.pbRemoveVideo.setObjectName(u"pbRemoveVideo")

        self.horizontalLayout_3.addWidget(self.pbRemoveVideo)

        self.pb_use_media_file_name_as_obsid = QPushButton(self.tab_player_1)
        self.pb_use_media_file_name_as_obsid.setObjectName(u"pb_use_media_file_name_as_obsid")

        self.horizontalLayout_3.addWidget(self.pb_use_media_file_name_as_obsid)

        self.horizontalSpacer_6 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_3.addItem(self.horizontalSpacer_6)


        self.verticalLayout.addLayout(self.horizontalLayout_3)

        self.horizontalLayout_15 = QHBoxLayout()
        self.horizontalLayout_15.setObjectName(u"horizontalLayout_15")
        self.cbVisualizeSpectrogram = QCheckBox(self.tab_player_1)
        self.cbVisualizeSpectrogram.setObjectName(u"cbVisualizeSpectrogram")

        self.horizontalLayout_15.addWidget(self.cbVisualizeSpectrogram)

        self.cb_visualize_waveform = QCheckBox(self.tab_player_1)
        self.cb_visualize_waveform.setObjectName(u"cb_visualize_waveform")

        self.horizontalLayout_15.addWidget(self.cb_visualize_waveform)

        self.cb_media_creation_date_as_offset = QCheckBox(self.tab_player_1)
        self.cb_media_creation_date_as_offset.setObjectName(u"cb_media_creation_date_as_offset")
        self.cb_media_creation_date_as_offset.setEnabled(False)

        self.horizontalLayout_15.addWidget(self.cb_media_creation_date_as_offset)

        self.horizontalSpacer_11 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_15.addItem(self.horizontalSpacer_11)


        self.verticalLayout.addLayout(self.horizontalLayout_15)

        self.horizontalLayout_12 = QHBoxLayout()
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.label_5 = QLabel(self.tab_player_1)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout_12.addWidget(self.label_5)

        self.sb_media_scan_sampling = QSpinBox(self.tab_player_1)
        self.sb_media_scan_sampling.setObjectName(u"sb_media_scan_sampling")
        self.sb_media_scan_sampling.setMaximum(1000000)

        self.horizontalLayout_12.addWidget(self.sb_media_scan_sampling)

        self.label_2 = QLabel(self.tab_player_1)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout_12.addWidget(self.label_2)

        self.sb_image_display_duration = QSpinBox(self.tab_player_1)
        self.sb_image_display_duration.setObjectName(u"sb_image_display_duration")
        self.sb_image_display_duration.setMinimum(1)
        self.sb_image_display_duration.setMaximum(86400)

        self.horizontalLayout_12.addWidget(self.sb_image_display_duration)

        self.horizontalSpacer_8 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_12.addItem(self.horizontalSpacer_8)


        self.verticalLayout.addLayout(self.horizontalLayout_12)

        self.cbCloseCurrentBehaviorsBetweenVideo = QCheckBox(self.tab_player_1)
        self.cbCloseCurrentBehaviorsBetweenVideo.setObjectName(u"cbCloseCurrentBehaviorsBetweenVideo")
        self.cbCloseCurrentBehaviorsBetweenVideo.setEnabled(False)

        self.verticalLayout.addWidget(self.cbCloseCurrentBehaviorsBetweenVideo)

        self.tabWidget.addTab(self.tab_player_1, "")
        self.tab_data_files = QWidget()
        self.tab_data_files.setObjectName(u"tab_data_files")
        self.verticalLayout_17 = QVBoxLayout(self.tab_data_files)
        self.verticalLayout_17.setObjectName(u"verticalLayout_17")
        self.splitter_5 = QSplitter(self.tab_data_files)
        self.splitter_5.setObjectName(u"splitter_5")
        self.splitter_5.setOrientation(Qt.Orientation.Vertical)
        self.layoutWidget_4 = QWidget(self.splitter_5)
        self.layoutWidget_4.setObjectName(u"layoutWidget_4")
        self.verticalLayout_15 = QVBoxLayout(self.layoutWidget_4)
        self.verticalLayout_15.setObjectName(u"verticalLayout_15")
        self.verticalLayout_15.setContentsMargins(0, 0, 0, 0)
        self.label_7 = QLabel(self.layoutWidget_4)
        self.label_7.setObjectName(u"label_7")

        self.verticalLayout_15.addWidget(self.label_7)

        self.tw_data_files = QTableWidget(self.layoutWidget_4)
        if (self.tw_data_files.columnCount() < 9):
            self.tw_data_files.setColumnCount(9)
        __qtablewidgetitem10 = QTableWidgetItem()
        self.tw_data_files.setHorizontalHeaderItem(0, __qtablewidgetitem10)
        __qtablewidgetitem11 = QTableWidgetItem()
        self.tw_data_files.setHorizontalHeaderItem(1, __qtablewidgetitem11)
        __qtablewidgetitem12 = QTableWidgetItem()
        self.tw_data_files.setHorizontalHeaderItem(2, __qtablewidgetitem12)
        __qtablewidgetitem13 = QTableWidgetItem()
        self.tw_data_files.setHorizontalHeaderItem(3, __qtablewidgetitem13)
        __qtablewidgetitem14 = QTableWidgetItem()
        self.tw_data_files.setHorizontalHeaderItem(4, __qtablewidgetitem14)
        __qtablewidgetitem15 = QTableWidgetItem()
        self.tw_data_files.setHorizontalHeaderItem(5, __qtablewidgetitem15)
        __qtablewidgetitem16 = QTableWidgetItem()
        self.tw_data_files.setHorizontalHeaderItem(6, __qtablewidgetitem16)
        __qtablewidgetitem17 = QTableWidgetItem()
        self.tw_data_files.setHorizontalHeaderItem(7, __qtablewidgetitem17)
        __qtablewidgetitem18 = QTableWidgetItem()
        self.tw_data_files.setHorizontalHeaderItem(8, __qtablewidgetitem18)
        self.tw_data_files.setObjectName(u"tw_data_files")
        self.tw_data_files.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)

        self.verticalLayout_15.addWidget(self.tw_data_files)

        self.splitter_5.addWidget(self.layoutWidget_4)
        self.layoutWidget_5 = QWidget(self.splitter_5)
        self.layoutWidget_5.setObjectName(u"layoutWidget_5")
        self.verticalLayout_16 = QVBoxLayout(self.layoutWidget_5)
        self.verticalLayout_16.setObjectName(u"verticalLayout_16")
        self.verticalLayout_16.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.pb_add_data_file = QPushButton(self.layoutWidget_5)
        self.pb_add_data_file.setObjectName(u"pb_add_data_file")

        self.horizontalLayout_5.addWidget(self.pb_add_data_file)

        self.pb_remove_data_file = QPushButton(self.layoutWidget_5)
        self.pb_remove_data_file.setObjectName(u"pb_remove_data_file")

        self.horizontalLayout_5.addWidget(self.pb_remove_data_file)

        self.pb_view_data_head = QPushButton(self.layoutWidget_5)
        self.pb_view_data_head.setObjectName(u"pb_view_data_head")

        self.horizontalLayout_5.addWidget(self.pb_view_data_head)

        self.pb_plot_data = QPushButton(self.layoutWidget_5)
        self.pb_plot_data.setObjectName(u"pb_plot_data")

        self.horizontalLayout_5.addWidget(self.pb_plot_data)

        self.horizontalSpacer_7 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_5.addItem(self.horizontalSpacer_7)


        self.verticalLayout_16.addLayout(self.horizontalLayout_5)

        self.verticalSpacer_4 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_16.addItem(self.verticalSpacer_4)

        self.splitter_5.addWidget(self.layoutWidget_5)

        self.verticalLayout_17.addWidget(self.splitter_5)

        self.tabWidget.addTab(self.tab_data_files, "")

        self.verticalLayout_7.addWidget(self.tabWidget)

        self.sw_observation_type.addWidget(self.pg_media_files)
        self.pg_live = QWidget()
        self.pg_live.setObjectName(u"pg_live")
        self.verticalLayout_4 = QVBoxLayout(self.pg_live)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_8 = QVBoxLayout()
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.label_4 = QLabel(self.pg_live)
        self.label_4.setObjectName(u"label_4")

        self.horizontalLayout_8.addWidget(self.label_4)

        self.sbScanSampling = QSpinBox(self.pg_live)
        self.sbScanSampling.setObjectName(u"sbScanSampling")
        self.sbScanSampling.setMaximum(1000000)

        self.horizontalLayout_8.addWidget(self.sbScanSampling)

        self.label_6 = QLabel(self.pg_live)
        self.label_6.setObjectName(u"label_6")

        self.horizontalLayout_8.addWidget(self.label_6)

        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_8.addItem(self.horizontalSpacer)


        self.verticalLayout_8.addLayout(self.horizontalLayout_8)

        self.cb_start_from_current_time = QCheckBox(self.pg_live)
        self.cb_start_from_current_time.setObjectName(u"cb_start_from_current_time")

        self.verticalLayout_8.addWidget(self.cb_start_from_current_time)

        self.rb_day_time = QRadioButton(self.pg_live)
        self.rb_day_time.setObjectName(u"rb_day_time")
        self.rb_day_time.setEnabled(False)
        self.rb_day_time.setChecked(True)

        self.verticalLayout_8.addWidget(self.rb_day_time)

        self.rb_epoch_time = QRadioButton(self.pg_live)
        self.rb_epoch_time.setObjectName(u"rb_epoch_time")
        self.rb_epoch_time.setEnabled(False)

        self.verticalLayout_8.addWidget(self.rb_epoch_time)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_8.addItem(self.verticalSpacer_2)


        self.verticalLayout_4.addLayout(self.verticalLayout_8)

        self.sw_observation_type.addWidget(self.pg_live)
        self.pg_images = QWidget()
        self.pg_images.setObjectName(u"pg_images")
        self.verticalLayout_5 = QVBoxLayout(self.pg_images)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.lw_images_directory = QListWidget(self.pg_images)
        self.lw_images_directory.setObjectName(u"lw_images_directory")

        self.horizontalLayout_9.addWidget(self.lw_images_directory)


        self.verticalLayout_5.addLayout(self.horizontalLayout_9)

        self.lb_images_info = QLabel(self.pg_images)
        self.lb_images_info.setObjectName(u"lb_images_info")

        self.verticalLayout_5.addWidget(self.lb_images_info)

        self.horizontalLayout_14 = QHBoxLayout()
        self.horizontalLayout_14.setObjectName(u"horizontalLayout_14")
        self.pb_add_directory = QPushButton(self.pg_images)
        self.pb_add_directory.setObjectName(u"pb_add_directory")

        self.horizontalLayout_14.addWidget(self.pb_add_directory)

        self.pb_remove_directory = QPushButton(self.pg_images)
        self.pb_remove_directory.setObjectName(u"pb_remove_directory")

        self.horizontalLayout_14.addWidget(self.pb_remove_directory)

        self.horizontalSpacer_10 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_14.addItem(self.horizontalSpacer_10)


        self.verticalLayout_5.addLayout(self.horizontalLayout_14)

        self.horizontalLayout_13 = QHBoxLayout()
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.pb_use_img_dir_as_obsid = QPushButton(self.pg_images)
        self.pb_use_img_dir_as_obsid.setObjectName(u"pb_use_img_dir_as_obsid")

        self.horizontalLayout_13.addWidget(self.pb_use_img_dir_as_obsid)

        self.horizontalSpacer_9 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_13.addItem(self.horizontalSpacer_9)


        self.verticalLayout_5.addLayout(self.horizontalLayout_13)

        self.groupBox = QGroupBox(self.pg_images)
        self.groupBox.setObjectName(u"groupBox")
        self.horizontalLayout_11 = QHBoxLayout(self.groupBox)
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.horizontalLayout_10 = QHBoxLayout()
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.rb_no_time = QRadioButton(self.groupBox)
        self.rb_no_time.setObjectName(u"rb_no_time")

        self.horizontalLayout_10.addWidget(self.rb_no_time)

        self.rb_use_exif = QRadioButton(self.groupBox)
        self.rb_use_exif.setObjectName(u"rb_use_exif")

        self.horizontalLayout_10.addWidget(self.rb_use_exif)

        self.rb_time_lapse = QRadioButton(self.groupBox)
        self.rb_time_lapse.setObjectName(u"rb_time_lapse")

        self.horizontalLayout_10.addWidget(self.rb_time_lapse)

        self.sb_time_lapse = QDoubleSpinBox(self.groupBox)
        self.sb_time_lapse.setObjectName(u"sb_time_lapse")
        self.sb_time_lapse.setDecimals(3)
        self.sb_time_lapse.setMaximum(86400.000000000000000)

        self.horizontalLayout_10.addWidget(self.sb_time_lapse)

        self.horizontalSpacer_5 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_10.addItem(self.horizontalSpacer_5)


        self.horizontalLayout_11.addLayout(self.horizontalLayout_10)


        self.verticalLayout_5.addWidget(self.groupBox)

        self.sw_observation_type.addWidget(self.pg_images)

        self.verticalLayout_6.addWidget(self.sw_observation_type)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalSpacer_3 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout.addItem(self.horizontalSpacer_3)

        self.pbCancel = QPushButton(Form)
        self.pbCancel.setObjectName(u"pbCancel")

        self.horizontalLayout.addWidget(self.pbCancel)

        self.pbSave = QPushButton(Form)
        self.pbSave.setObjectName(u"pbSave")

        self.horizontalLayout.addWidget(self.pbSave)

        self.pbLaunch = QPushButton(Form)
        self.pbLaunch.setObjectName(u"pbLaunch")

        self.horizontalLayout.addWidget(self.pbLaunch)


        self.verticalLayout_6.addLayout(self.horizontalLayout)


        self.retranslateUi(Form)

        self.sw_observation_type.setCurrentIndex(1)
        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(Form)
    # setupUi

    def retranslateUi(self, Form):
        Form.setWindowTitle(QCoreApplication.translate("Form", u"New observation", None))
        self.label.setText(QCoreApplication.translate("Form", u"Observation id", None))
        self.lb_star.setText(QCoreApplication.translate("Form", u"*", None))
        self.label_8.setText(QCoreApplication.translate("Form", u"Date and time", None))
        self.dteDate.setDisplayFormat(QCoreApplication.translate("Form", u"yyyy-MM-dd hh:mm:ss.zzz", None))
        self.label_9.setText(QCoreApplication.translate("Form", u"Description", None))
        self.cb_time_offset.setText(QCoreApplication.translate("Form", u"Time offset", None))
        self.lbTimeOffset.setText(QCoreApplication.translate("Form", u"Time value", None))
        self.cb_observation_time_interval.setText(QCoreApplication.translate("Form", u"Limit observation to a time interval", None))
        self.label_3.setText(QCoreApplication.translate("Form", u"Independent variables", None))
        ___qtablewidgetitem = self.twIndepVariables.horizontalHeaderItem(0)
        ___qtablewidgetitem.setText(QCoreApplication.translate("Form", u"Variable", None));
        ___qtablewidgetitem1 = self.twIndepVariables.horizontalHeaderItem(1)
        ___qtablewidgetitem1.setText(QCoreApplication.translate("Form", u"Type", None));
        ___qtablewidgetitem2 = self.twIndepVariables.horizontalHeaderItem(2)
        ___qtablewidgetitem2.setText(QCoreApplication.translate("Form", u"Value", None));
        self.gb_observation_type.setTitle(QCoreApplication.translate("Form", u"Observation type", None))
        self.rb_media_files.setText(QCoreApplication.translate("Form", u"Observation from media file(s)", None))
        self.rb_live.setText(QCoreApplication.translate("Form", u"Live observation", None))
        self.rb_images.setText(QCoreApplication.translate("Form", u"Observation from pictures", None))
        ___qtablewidgetitem3 = self.twVideo1.horizontalHeaderItem(0)
        ___qtablewidgetitem3.setText(QCoreApplication.translate("Form", u"Player", None));
        ___qtablewidgetitem4 = self.twVideo1.horizontalHeaderItem(1)
        ___qtablewidgetitem4.setText(QCoreApplication.translate("Form", u"Offset (seconds)", None));
        ___qtablewidgetitem5 = self.twVideo1.horizontalHeaderItem(2)
        ___qtablewidgetitem5.setText(QCoreApplication.translate("Form", u"Path", None));
        ___qtablewidgetitem6 = self.twVideo1.horizontalHeaderItem(3)
        ___qtablewidgetitem6.setText(QCoreApplication.translate("Form", u"Duration", None));
        ___qtablewidgetitem7 = self.twVideo1.horizontalHeaderItem(4)
        ___qtablewidgetitem7.setText(QCoreApplication.translate("Form", u"FPS", None));
        ___qtablewidgetitem8 = self.twVideo1.horizontalHeaderItem(5)
        ___qtablewidgetitem8.setText(QCoreApplication.translate("Form", u"Video", None));
        ___qtablewidgetitem9 = self.twVideo1.horizontalHeaderItem(6)
        ___qtablewidgetitem9.setText(QCoreApplication.translate("Form", u"Audio", None));
        self.pbAddVideo.setText(QCoreApplication.translate("Form", u"Add media", None))
        self.pbRemoveVideo.setText(QCoreApplication.translate("Form", u"Remove selected media", None))
        self.pb_use_media_file_name_as_obsid.setText(QCoreApplication.translate("Form", u"Use media file name as observation id", None))
        self.cbVisualizeSpectrogram.setText(QCoreApplication.translate("Form", u"Visualize the sound spectrogram for the player #1", None))
        self.cb_visualize_waveform.setText(QCoreApplication.translate("Form", u"Visualize the waveform for the player #1", None))
        self.cb_media_creation_date_as_offset.setText(QCoreApplication.translate("Form", u"Use the media creation date/time as offset", None))
        self.label_5.setText(QCoreApplication.translate("Form", u"Scan sampling every (s)", None))
        self.label_2.setText(QCoreApplication.translate("Form", u"Image display duration (s)", None))
        self.cbCloseCurrentBehaviorsBetweenVideo.setText(QCoreApplication.translate("Form", u"Stop ongoing state events between successive media files", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_player_1), QCoreApplication.translate("Form", u"Media files", None))
        self.label_7.setText(QCoreApplication.translate("Form", u"Data files to plot", None))
        ___qtablewidgetitem10 = self.tw_data_files.horizontalHeaderItem(0)
        ___qtablewidgetitem10.setText(QCoreApplication.translate("Form", u"Path", None));
        ___qtablewidgetitem11 = self.tw_data_files.horizontalHeaderItem(1)
        ___qtablewidgetitem11.setText(QCoreApplication.translate("Form", u"Columns to plot", None));
        ___qtablewidgetitem12 = self.tw_data_files.horizontalHeaderItem(2)
        ___qtablewidgetitem12.setText(QCoreApplication.translate("Form", u"Plot title", None));
        ___qtablewidgetitem13 = self.tw_data_files.horizontalHeaderItem(3)
        ___qtablewidgetitem13.setText(QCoreApplication.translate("Form", u"Variable name", None));
        ___qtablewidgetitem14 = self.tw_data_files.horizontalHeaderItem(4)
        ___qtablewidgetitem14.setText(QCoreApplication.translate("Form", u"Converters", None));
        ___qtablewidgetitem15 = self.tw_data_files.horizontalHeaderItem(5)
        ___qtablewidgetitem15.setText(QCoreApplication.translate("Form", u"Time interval (s)", None));
        ___qtablewidgetitem16 = self.tw_data_files.horizontalHeaderItem(6)
        ___qtablewidgetitem16.setText(QCoreApplication.translate("Form", u"Start position (s)", None));
        ___qtablewidgetitem17 = self.tw_data_files.horizontalHeaderItem(7)
        ___qtablewidgetitem17.setText(QCoreApplication.translate("Form", u"Substract first value", None));
        ___qtablewidgetitem18 = self.tw_data_files.horizontalHeaderItem(8)
        ___qtablewidgetitem18.setText(QCoreApplication.translate("Form", u"Color", None));
        self.pb_add_data_file.setText(QCoreApplication.translate("Form", u"Add data file", None))
        self.pb_remove_data_file.setText(QCoreApplication.translate("Form", u"Remove selected data file", None))
        self.pb_view_data_head.setText(QCoreApplication.translate("Form", u"View data from file", None))
        self.pb_plot_data.setText(QCoreApplication.translate("Form", u"Show plot", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_data_files), QCoreApplication.translate("Form", u"Data files", None))
        self.label_4.setText(QCoreApplication.translate("Form", u"Scan sampling every", None))
        self.label_6.setText(QCoreApplication.translate("Form", u"seconds", None))
        self.cb_start_from_current_time.setText(QCoreApplication.translate("Form", u"Start from current time", None))
        self.rb_day_time.setText(QCoreApplication.translate("Form", u"Day time", None))
        self.rb_epoch_time.setText(QCoreApplication.translate("Form", u"Epoch time (seconds since 1970-01-01)", None))
        self.lb_images_info.setText(QCoreApplication.translate("Form", u"Image info:", None))
        self.pb_add_directory.setText(QCoreApplication.translate("Form", u"Add directory", None))
        self.pb_remove_directory.setText(QCoreApplication.translate("Form", u"Remove directory", None))
        self.pb_use_img_dir_as_obsid.setText(QCoreApplication.translate("Form", u"Use the pictures directory as observation id", None))
        self.groupBox.setTitle(QCoreApplication.translate("Form", u"Time", None))
        self.rb_no_time.setText(QCoreApplication.translate("Form", u"No time", None))
        self.rb_use_exif.setText(QCoreApplication.translate("Form", u"Use the EXIF DateTimeOriginal tag", None))
        self.rb_time_lapse.setText(QCoreApplication.translate("Form", u"Time lapse (s)", None))
        self.pbCancel.setText(QCoreApplication.translate("Form", u"Cancel", None))
        self.pbSave.setText(QCoreApplication.translate("Form", u"Save", None))
        self.pbLaunch.setText(QCoreApplication.translate("Form", u"Start", None))
    # retranslateUi

