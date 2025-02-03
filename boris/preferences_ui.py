# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'preferences.ui'
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
    QDoubleSpinBox, QFormLayout, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPlainTextEdit, QPushButton, QSizePolicy, QSpacerItem,
    QSpinBox, QTabWidget, QVBoxLayout, QWidget)

class Ui_prefDialog(object):
    def setupUi(self, prefDialog):
        if not prefDialog.objectName():
            prefDialog.setObjectName(u"prefDialog")
        prefDialog.setWindowModality(Qt.WindowModality.WindowModal)
        prefDialog.resize(904, 554)
        self.gridLayout = QGridLayout(prefDialog)
        self.gridLayout.setObjectName(u"gridLayout")
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.tabWidget = QTabWidget(prefDialog)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabWidget.setEnabled(True)
        self.tab_project = QWidget()
        self.tab_project.setObjectName(u"tab_project")
        self.verticalLayout_5 = QVBoxLayout(self.tab_project)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.horizontalLayout_14 = QHBoxLayout()
        self.horizontalLayout_14.setObjectName(u"horizontalLayout_14")
        self.label = QLabel(self.tab_project)
        self.label.setObjectName(u"label")

        self.horizontalLayout_14.addWidget(self.label)

        self.cbTimeFormat = QComboBox(self.tab_project)
        self.cbTimeFormat.addItem("")
        self.cbTimeFormat.addItem("")
        self.cbTimeFormat.setObjectName(u"cbTimeFormat")

        self.horizontalLayout_14.addWidget(self.cbTimeFormat)


        self.verticalLayout_5.addLayout(self.horizontalLayout_14)

        self.horizontalLayout_15 = QHBoxLayout()
        self.horizontalLayout_15.setObjectName(u"horizontalLayout_15")
        self.label_6 = QLabel(self.tab_project)
        self.label_6.setObjectName(u"label_6")

        self.horizontalLayout_15.addWidget(self.label_6)

        self.sbAutomaticBackup = QSpinBox(self.tab_project)
        self.sbAutomaticBackup.setObjectName(u"sbAutomaticBackup")
        self.sbAutomaticBackup.setMinimum(-10000)
        self.sbAutomaticBackup.setMaximum(10000)
        self.sbAutomaticBackup.setValue(10)

        self.horizontalLayout_15.addWidget(self.sbAutomaticBackup)


        self.verticalLayout_5.addLayout(self.horizontalLayout_15)

        self.horizontalLayout_13 = QHBoxLayout()
        self.horizontalLayout_13.setObjectName(u"horizontalLayout_13")
        self.label_3 = QLabel(self.tab_project)
        self.label_3.setObjectName(u"label_3")

        self.horizontalLayout_13.addWidget(self.label_3)

        self.leSeparator = QLineEdit(self.tab_project)
        self.leSeparator.setObjectName(u"leSeparator")

        self.horizontalLayout_13.addWidget(self.leSeparator)


        self.verticalLayout_5.addLayout(self.horizontalLayout_13)

        self.cbCheckForNewVersion = QCheckBox(self.tab_project)
        self.cbCheckForNewVersion.setObjectName(u"cbCheckForNewVersion")

        self.verticalLayout_5.addWidget(self.cbCheckForNewVersion)

        self.horizontalLayout_11 = QHBoxLayout()
        self.horizontalLayout_11.setObjectName(u"horizontalLayout_11")
        self.lb_hwdec = QLabel(self.tab_project)
        self.lb_hwdec.setObjectName(u"lb_hwdec")

        self.horizontalLayout_11.addWidget(self.lb_hwdec)

        self.cb_hwdec = QComboBox(self.tab_project)
        self.cb_hwdec.setObjectName(u"cb_hwdec")

        self.horizontalLayout_11.addWidget(self.cb_hwdec)


        self.verticalLayout_5.addLayout(self.horizontalLayout_11)

        self.horizontalLayout_9 = QHBoxLayout()
        self.horizontalLayout_9.setObjectName(u"horizontalLayout_9")
        self.lb_project_file_indent = QLabel(self.tab_project)
        self.lb_project_file_indent.setObjectName(u"lb_project_file_indent")

        self.horizontalLayout_9.addWidget(self.lb_project_file_indent)

        self.combo_project_file_indentation = QComboBox(self.tab_project)
        self.combo_project_file_indentation.setObjectName(u"combo_project_file_indentation")

        self.horizontalLayout_9.addWidget(self.combo_project_file_indentation)


        self.verticalLayout_5.addLayout(self.horizontalLayout_9)

        self.cb_check_integrity_at_opening = QCheckBox(self.tab_project)
        self.cb_check_integrity_at_opening.setObjectName(u"cb_check_integrity_at_opening")

        self.verticalLayout_5.addWidget(self.cb_check_integrity_at_opening)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_5.addItem(self.verticalSpacer_2)

        self.tabWidget.addTab(self.tab_project, "")
        self.tab_observations = QWidget()
        self.tab_observations.setObjectName(u"tab_observations")
        self.verticalLayout = QVBoxLayout(self.tab_observations)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.label_4 = QLabel(self.tab_observations)
        self.label_4.setObjectName(u"label_4")

        self.horizontalLayout_4.addWidget(self.label_4)

        self.sbffSpeed = QSpinBox(self.tab_observations)
        self.sbffSpeed.setObjectName(u"sbffSpeed")
        self.sbffSpeed.setMinimum(0)
        self.sbffSpeed.setMaximum(10000)
        self.sbffSpeed.setValue(10)

        self.horizontalLayout_4.addWidget(self.sbffSpeed)


        self.verticalLayout.addLayout(self.horizontalLayout_4)

        self.cb_adapt_fast_jump = QCheckBox(self.tab_observations)
        self.cb_adapt_fast_jump.setObjectName(u"cb_adapt_fast_jump")

        self.verticalLayout.addWidget(self.cb_adapt_fast_jump)

        self.horizontalLayout_5 = QHBoxLayout()
        self.horizontalLayout_5.setObjectName(u"horizontalLayout_5")
        self.label_5 = QLabel(self.tab_observations)
        self.label_5.setObjectName(u"label_5")

        self.horizontalLayout_5.addWidget(self.label_5)

        self.sbSpeedStep = QDoubleSpinBox(self.tab_observations)
        self.sbSpeedStep.setObjectName(u"sbSpeedStep")
        self.sbSpeedStep.setDecimals(1)
        self.sbSpeedStep.setMinimum(0.100000000000000)
        self.sbSpeedStep.setMaximum(10.000000000000000)
        self.sbSpeedStep.setSingleStep(0.100000000000000)
        self.sbSpeedStep.setValue(0.100000000000000)

        self.horizontalLayout_5.addWidget(self.sbSpeedStep)


        self.verticalLayout.addLayout(self.horizontalLayout_5)

        self.horizontalLayout_6 = QHBoxLayout()
        self.horizontalLayout_6.setObjectName(u"horizontalLayout_6")
        self.label_2 = QLabel(self.tab_observations)
        self.label_2.setObjectName(u"label_2")

        self.horizontalLayout_6.addWidget(self.label_2)

        self.sbRepositionTimeOffset = QSpinBox(self.tab_observations)
        self.sbRepositionTimeOffset.setObjectName(u"sbRepositionTimeOffset")
        self.sbRepositionTimeOffset.setMinimum(-10000)
        self.sbRepositionTimeOffset.setMaximum(10000)
        self.sbRepositionTimeOffset.setValue(-3)

        self.horizontalLayout_6.addWidget(self.sbRepositionTimeOffset)


        self.verticalLayout.addLayout(self.horizontalLayout_6)

        self.cbConfirmSound = QCheckBox(self.tab_observations)
        self.cbConfirmSound.setObjectName(u"cbConfirmSound")

        self.verticalLayout.addWidget(self.cbConfirmSound)

        self.cbCloseSameEvent = QCheckBox(self.tab_observations)
        self.cbCloseSameEvent.setObjectName(u"cbCloseSameEvent")

        self.verticalLayout.addWidget(self.cbCloseSameEvent)

        self.horizontalLayout_8 = QHBoxLayout()
        self.horizontalLayout_8.setObjectName(u"horizontalLayout_8")
        self.label_8 = QLabel(self.tab_observations)
        self.label_8.setObjectName(u"label_8")

        self.horizontalLayout_8.addWidget(self.label_8)

        self.sbBeepEvery = QSpinBox(self.tab_observations)
        self.sbBeepEvery.setObjectName(u"sbBeepEvery")

        self.horizontalLayout_8.addWidget(self.sbBeepEvery)


        self.verticalLayout.addLayout(self.horizontalLayout_8)

        self.cb_display_subtitles = QCheckBox(self.tab_observations)
        self.cb_display_subtitles.setObjectName(u"cb_display_subtitles")

        self.verticalLayout.addWidget(self.cb_display_subtitles)

        self.cbTrackingCursorAboveEvent = QCheckBox(self.tab_observations)
        self.cbTrackingCursorAboveEvent.setObjectName(u"cbTrackingCursorAboveEvent")

        self.verticalLayout.addWidget(self.cbTrackingCursorAboveEvent)

        self.cbAlertNoFocalSubject = QCheckBox(self.tab_observations)
        self.cbAlertNoFocalSubject.setObjectName(u"cbAlertNoFocalSubject")

        self.verticalLayout.addWidget(self.cbAlertNoFocalSubject)

        self.cb_pause_before_addevent = QCheckBox(self.tab_observations)
        self.cb_pause_before_addevent.setObjectName(u"cb_pause_before_addevent")

        self.verticalLayout.addWidget(self.cb_pause_before_addevent)

        self.verticalSpacer_4 = QSpacerItem(20, 391, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_4)

        self.tabWidget.addTab(self.tab_observations, "")
        self.tab_analysis_plugins = QWidget()
        self.tab_analysis_plugins.setObjectName(u"tab_analysis_plugins")
        self.horizontalLayout_17 = QHBoxLayout(self.tab_analysis_plugins)
        self.horizontalLayout_17.setObjectName(u"horizontalLayout_17")
        self.verticalLayout_11 = QVBoxLayout()
        self.verticalLayout_11.setObjectName(u"verticalLayout_11")
        self.label_13 = QLabel(self.tab_analysis_plugins)
        self.label_13.setObjectName(u"label_13")

        self.verticalLayout_11.addWidget(self.label_13)

        self.lv_all_plugins = QListWidget(self.tab_analysis_plugins)
        self.lv_all_plugins.setObjectName(u"lv_all_plugins")

        self.verticalLayout_11.addWidget(self.lv_all_plugins)

        self.label_15 = QLabel(self.tab_analysis_plugins)
        self.label_15.setObjectName(u"label_15")

        self.verticalLayout_11.addWidget(self.label_15)

        self.horizontalLayout_16 = QHBoxLayout()
        self.horizontalLayout_16.setObjectName(u"horizontalLayout_16")
        self.le_personal_plugins_dir = QLineEdit(self.tab_analysis_plugins)
        self.le_personal_plugins_dir.setObjectName(u"le_personal_plugins_dir")
        self.le_personal_plugins_dir.setReadOnly(True)

        self.horizontalLayout_16.addWidget(self.le_personal_plugins_dir)

        self.pb_browse_plugins_dir = QPushButton(self.tab_analysis_plugins)
        self.pb_browse_plugins_dir.setObjectName(u"pb_browse_plugins_dir")

        self.horizontalLayout_16.addWidget(self.pb_browse_plugins_dir)


        self.verticalLayout_11.addLayout(self.horizontalLayout_16)

        self.lw_personal_plugins = QListWidget(self.tab_analysis_plugins)
        self.lw_personal_plugins.setObjectName(u"lw_personal_plugins")

        self.verticalLayout_11.addWidget(self.lw_personal_plugins)


        self.horizontalLayout_17.addLayout(self.verticalLayout_11)

        self.verticalLayout_12 = QVBoxLayout()
        self.verticalLayout_12.setObjectName(u"verticalLayout_12")
        self.label_14 = QLabel(self.tab_analysis_plugins)
        self.label_14.setObjectName(u"label_14")

        self.verticalLayout_12.addWidget(self.label_14)

        self.pte_plugin_description = QPlainTextEdit(self.tab_analysis_plugins)
        self.pte_plugin_description.setObjectName(u"pte_plugin_description")
        self.pte_plugin_description.setReadOnly(True)

        self.verticalLayout_12.addWidget(self.pte_plugin_description)


        self.horizontalLayout_17.addLayout(self.verticalLayout_12)

        self.tabWidget.addTab(self.tab_analysis_plugins, "")
        self.tab_ffmpeg = QWidget()
        self.tab_ffmpeg.setObjectName(u"tab_ffmpeg")
        self.verticalLayout_4 = QVBoxLayout(self.tab_ffmpeg)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_3 = QVBoxLayout()
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.lbFFmpegPath = QLabel(self.tab_ffmpeg)
        self.lbFFmpegPath.setObjectName(u"lbFFmpegPath")
        self.lbFFmpegPath.setScaledContents(False)
        self.lbFFmpegPath.setWordWrap(True)

        self.verticalLayout_3.addWidget(self.lbFFmpegPath)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")

        self.verticalLayout_3.addLayout(self.horizontalLayout)

        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.lbFFmpegCacheDir = QLabel(self.tab_ffmpeg)
        self.lbFFmpegCacheDir.setObjectName(u"lbFFmpegCacheDir")

        self.horizontalLayout_3.addWidget(self.lbFFmpegCacheDir)

        self.leFFmpegCacheDir = QLineEdit(self.tab_ffmpeg)
        self.leFFmpegCacheDir.setObjectName(u"leFFmpegCacheDir")

        self.horizontalLayout_3.addWidget(self.leFFmpegCacheDir)

        self.pbBrowseFFmpegCacheDir = QPushButton(self.tab_ffmpeg)
        self.pbBrowseFFmpegCacheDir.setObjectName(u"pbBrowseFFmpegCacheDir")

        self.horizontalLayout_3.addWidget(self.pbBrowseFFmpegCacheDir)


        self.verticalLayout_3.addLayout(self.horizontalLayout_3)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer)


        self.verticalLayout_4.addLayout(self.verticalLayout_3)

        self.tabWidget.addTab(self.tab_ffmpeg, "")
        self.tab_spectro = QWidget()
        self.tab_spectro.setObjectName(u"tab_spectro")
        self.verticalLayout_8 = QVBoxLayout(self.tab_spectro)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.horizontalLayout_7 = QHBoxLayout()
        self.horizontalLayout_7.setObjectName(u"horizontalLayout_7")
        self.label_7 = QLabel(self.tab_spectro)
        self.label_7.setObjectName(u"label_7")

        self.horizontalLayout_7.addWidget(self.label_7)

        self.cbSpectrogramColorMap = QComboBox(self.tab_spectro)
        self.cbSpectrogramColorMap.setObjectName(u"cbSpectrogramColorMap")

        self.horizontalLayout_7.addWidget(self.cbSpectrogramColorMap)


        self.verticalLayout_8.addLayout(self.horizontalLayout_7)

        self.horizontalLayout_10 = QHBoxLayout()
        self.horizontalLayout_10.setObjectName(u"horizontalLayout_10")
        self.label_12 = QLabel(self.tab_spectro)
        self.label_12.setObjectName(u"label_12")

        self.horizontalLayout_10.addWidget(self.label_12)

        self.sb_time_interval = QSpinBox(self.tab_spectro)
        self.sb_time_interval.setObjectName(u"sb_time_interval")
        self.sb_time_interval.setMinimum(2)
        self.sb_time_interval.setMaximum(360)
        self.sb_time_interval.setValue(10)

        self.horizontalLayout_10.addWidget(self.sb_time_interval)


        self.verticalLayout_8.addLayout(self.horizontalLayout_10)

        self.verticalSpacer_3 = QSpacerItem(20, 319, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_8.addItem(self.verticalSpacer_3)

        self.tabWidget.addTab(self.tab_spectro, "")
        self.tab_colors = QWidget()
        self.tab_colors.setObjectName(u"tab_colors")
        self.verticalLayout_10 = QVBoxLayout(self.tab_colors)
        self.verticalLayout_10.setObjectName(u"verticalLayout_10")
        self.horizontalLayout_12 = QHBoxLayout()
        self.horizontalLayout_12.setObjectName(u"horizontalLayout_12")
        self.verticalLayout_6 = QVBoxLayout()
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.label_10 = QLabel(self.tab_colors)
        self.label_10.setObjectName(u"label_10")
        self.label_10.setOpenExternalLinks(True)

        self.verticalLayout_6.addWidget(self.label_10)

        self.te_behav_colors = QPlainTextEdit(self.tab_colors)
        self.te_behav_colors.setObjectName(u"te_behav_colors")

        self.verticalLayout_6.addWidget(self.te_behav_colors)

        self.pb_reset_behav_colors = QPushButton(self.tab_colors)
        self.pb_reset_behav_colors.setObjectName(u"pb_reset_behav_colors")

        self.verticalLayout_6.addWidget(self.pb_reset_behav_colors)


        self.horizontalLayout_12.addLayout(self.verticalLayout_6)

        self.verticalLayout_9 = QVBoxLayout()
        self.verticalLayout_9.setObjectName(u"verticalLayout_9")
        self.label_11 = QLabel(self.tab_colors)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setOpenExternalLinks(True)

        self.verticalLayout_9.addWidget(self.label_11)

        self.te_category_colors = QPlainTextEdit(self.tab_colors)
        self.te_category_colors.setObjectName(u"te_category_colors")

        self.verticalLayout_9.addWidget(self.te_category_colors)

        self.pb_reset_category_colors = QPushButton(self.tab_colors)
        self.pb_reset_category_colors.setObjectName(u"pb_reset_category_colors")

        self.verticalLayout_9.addWidget(self.pb_reset_category_colors)


        self.horizontalLayout_12.addLayout(self.verticalLayout_9)


        self.verticalLayout_10.addLayout(self.horizontalLayout_12)

        self.tabWidget.addTab(self.tab_colors, "")
        self.tab_interface = QWidget()
        self.tab_interface.setObjectName(u"tab_interface")
        self.verticalLayout_7 = QVBoxLayout(self.tab_interface)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.formLayout = QFormLayout()
        self.formLayout.setObjectName(u"formLayout")
        self.label_9 = QLabel(self.tab_interface)
        self.label_9.setObjectName(u"label_9")

        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label_9)

        self.sb_toolbar_icon_size = QSpinBox(self.tab_interface)
        self.sb_toolbar_icon_size.setObjectName(u"sb_toolbar_icon_size")
        self.sb_toolbar_icon_size.setMinimum(12)
        self.sb_toolbar_icon_size.setMaximum(128)
        self.sb_toolbar_icon_size.setValue(24)

        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.sb_toolbar_icon_size)


        self.verticalLayout_7.addLayout(self.formLayout)

        self.verticalSpacer_5 = QSpacerItem(20, 386, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_7.addItem(self.verticalSpacer_5)

        self.tabWidget.addTab(self.tab_interface, "")

        self.verticalLayout_2.addWidget(self.tabWidget)

        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalSpacer = QSpacerItem(241, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)

        self.pb_refresh = QPushButton(prefDialog)
        self.pb_refresh.setObjectName(u"pb_refresh")

        self.horizontalLayout_2.addWidget(self.pb_refresh)

        self.pbCancel = QPushButton(prefDialog)
        self.pbCancel.setObjectName(u"pbCancel")

        self.horizontalLayout_2.addWidget(self.pbCancel)

        self.pbOK = QPushButton(prefDialog)
        self.pbOK.setObjectName(u"pbOK")

        self.horizontalLayout_2.addWidget(self.pbOK)


        self.verticalLayout_2.addLayout(self.horizontalLayout_2)


        self.gridLayout.addLayout(self.verticalLayout_2, 0, 0, 1, 1)


        self.retranslateUi(prefDialog)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(prefDialog)
    # setupUi

    def retranslateUi(self, prefDialog):
        prefDialog.setWindowTitle(QCoreApplication.translate("prefDialog", u"Preferences", None))
        self.label.setText(QCoreApplication.translate("prefDialog", u"Default project time format", None))
        self.cbTimeFormat.setItemText(0, QCoreApplication.translate("prefDialog", u"seconds", None))
        self.cbTimeFormat.setItemText(1, QCoreApplication.translate("prefDialog", u"hh:mm:ss.mss", None))

        self.label_6.setText(QCoreApplication.translate("prefDialog", u"Auto-save project every (minutes)", None))
        self.label_3.setText(QCoreApplication.translate("prefDialog", u"Separator for behavioural strings (events export)", None))
        self.leSeparator.setText(QCoreApplication.translate("prefDialog", u"|", None))
        self.cbCheckForNewVersion.setText(QCoreApplication.translate("prefDialog", u"Check for new version and news", None))
        self.lb_hwdec.setText(QCoreApplication.translate("prefDialog", u"MPV player hardware video decoding", None))
        self.lb_project_file_indent.setText(QCoreApplication.translate("prefDialog", u"Project file indentation type", None))
        self.cb_check_integrity_at_opening.setText(QCoreApplication.translate("prefDialog", u"Check project integrity when opening and saving project (recommended)", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_project), QCoreApplication.translate("prefDialog", u"Project", None))
        self.label_4.setText(QCoreApplication.translate("prefDialog", u"Fast forward/backward value (seconds)", None))
        self.cb_adapt_fast_jump.setText(QCoreApplication.translate("prefDialog", u"Adapt the fast forward/backward jump to playback speed", None))
        self.label_5.setText(QCoreApplication.translate("prefDialog", u"Playback speed step value", None))
        self.label_2.setText(QCoreApplication.translate("prefDialog", u"Time offset for video/audio reposition (seconds)", None))
        self.cbConfirmSound.setText(QCoreApplication.translate("prefDialog", u"Play sound when a key is pressed", None))
        self.cbCloseSameEvent.setText(QCoreApplication.translate("prefDialog", u"Close the same current event independently of modifiers", None))
        self.label_8.setText(QCoreApplication.translate("prefDialog", u"Beep every (seconds)", None))
        self.cb_display_subtitles.setText(QCoreApplication.translate("prefDialog", u"Display subtitles", None))
        self.cbTrackingCursorAboveEvent.setText(QCoreApplication.translate("prefDialog", u"Tracking cursor above current event", None))
        self.cbAlertNoFocalSubject.setText(QCoreApplication.translate("prefDialog", u"Alert if focal subject is not set", None))
        self.cb_pause_before_addevent.setText(QCoreApplication.translate("prefDialog", u"Pause media before \"Add event\" command", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_observations), QCoreApplication.translate("prefDialog", u"Observations", None))
        self.label_13.setText(QCoreApplication.translate("prefDialog", u"BORIS plugins", None))
        self.label_15.setText(QCoreApplication.translate("prefDialog", u"Personal plugins", None))
        self.pb_browse_plugins_dir.setText(QCoreApplication.translate("prefDialog", u"Browse", None))
        self.label_14.setText(QCoreApplication.translate("prefDialog", u"Plugin info", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_analysis_plugins), QCoreApplication.translate("prefDialog", u"Analysis plugins", None))
        self.lbFFmpegPath.setText(QCoreApplication.translate("prefDialog", u"FFmpeg path:", None))
        self.lbFFmpegCacheDir.setText(QCoreApplication.translate("prefDialog", u"FFmpeg cache directory", None))
        self.pbBrowseFFmpegCacheDir.setText(QCoreApplication.translate("prefDialog", u"...", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_ffmpeg), QCoreApplication.translate("prefDialog", u"FFmpeg framework", None))
        self.label_7.setText(QCoreApplication.translate("prefDialog", u"Spectrogram color map", None))
        self.label_12.setText(QCoreApplication.translate("prefDialog", u"Default time interval (s)", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_spectro), QCoreApplication.translate("prefDialog", u"Spectrogram/Wave form", None))
        self.label_10.setText(QCoreApplication.translate("prefDialog", u"<html><head/><body><p>List of colors for behaviors. See <a href=\"https://matplotlib.org/api/colors_api.html\"><span style=\" text-decoration: underline; color:#0000ff;\">matplotlib colors</span></a></p></body></html>", None))
        self.pb_reset_behav_colors.setText(QCoreApplication.translate("prefDialog", u"Reset colors to default", None))
        self.label_11.setText(QCoreApplication.translate("prefDialog", u"<html><head/><body><p>List of colors for behavioral categories. See <a href=\"https://matplotlib.org/api/colors_api.html\"><span style=\" text-decoration: underline; color:#0000ff;\">matplotlib colors</span></a></p></body></html>", None))
        self.pb_reset_category_colors.setText(QCoreApplication.translate("prefDialog", u"Reset colors to default", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_colors), QCoreApplication.translate("prefDialog", u"Plot colors", None))
        self.label_9.setText(QCoreApplication.translate("prefDialog", u"Toolbar icons size", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_interface), QCoreApplication.translate("prefDialog", u"Interface", None))
        self.pb_refresh.setText(QCoreApplication.translate("prefDialog", u"Refresh", None))
        self.pbCancel.setText(QCoreApplication.translate("prefDialog", u"Cancel", None))
        self.pbOK.setText(QCoreApplication.translate("prefDialog", u"OK", None))
    # retranslateUi

