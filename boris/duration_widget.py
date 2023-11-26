"""

widget to edit duration > 24 h or < 0

https://stackoverflow.com/questions/44380202/creating-a-custom-widget-in-pyqt5
"""

from decimal import Decimal as dec

from PyQt5.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QSpinBox,
    QLabel,
    QSpacerItem,
    QSizePolicy,
    QDoubleSpinBox,
    QStackedWidget,
    QRadioButton,
)

from PyQt5.QtCore import pyqtSignal

from . import config as cfg


class Widget_hhmmss(QWidget):
    time_changed_signal = pyqtSignal(float)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent=parent)

        lay = QHBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)

        self.sign = QPushButton("+")
        self.sign.clicked.connect(self.change_sign)
        self.sign.setStyleSheet("font-size:12px;")
        lay.addWidget(self.sign)

        self.hours = QSpinBox()
        self.hours.setValue(0)
        self.hours.setMinimum(0)
        self.hours.setMaximum(2**31 - 1)
        self.hours.valueChanged.connect(self.update_time_value)
        lay.addWidget(self.hours)
        lay.addWidget(QLabel(":"))

        self.minutes = QSpinBox()
        self.minutes.setMinimum(-1)
        self.minutes.setMaximum(60)
        self.minutes.setPrefix("0")
        self.minutes.valueChanged.connect(lambda value, x=self.minutes: self.value_changed(value, x, 0, 59))
        lay.addWidget(self.minutes)
        lay.addWidget(QLabel(":"))

        self.seconds = QSpinBox()
        self.seconds.setMinimum(-1)
        self.seconds.setMaximum(60)
        self.seconds.setPrefix("0")
        self.seconds.valueChanged.connect(lambda value, x=self.seconds: self.value_changed(value, x, 0, 59))
        lay.addWidget(self.seconds)
        lay.addWidget(QLabel(":"))

        self.milliseconds = QSpinBox()
        self.milliseconds.setMinimum(-1)
        self.milliseconds.setMaximum(1000)
        self.milliseconds.setPrefix("00")
        self.milliseconds.valueChanged.connect(lambda value, x=self.milliseconds: self.value_changed(value, x, 0, 999))
        lay.addWidget(self.milliseconds)

        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        lay.addItem(spacerItem)
        self.setLayout(lay)

    def change_sign(self):
        """
        sign has changed
        """
        self.sign.setText("+" if self.sign.text() == "-" else "-")
        self.update_time_value()

    def update_time_value(self):
        new_time = self.hours.value() * 3600 + self.minutes.value() * 60 + self.seconds.value() + self.milliseconds.value() / 1000
        if self.sign.text() == "-":
            new_time = -new_time

        self.time_changed_signal.emit(new_time)

    def value_changed(self, new_value, widget, val_min, val_max):
        """
        time value changed
        """

        if new_value > val_max:
            widget.setValue(val_min)
            widget.setPrefix("0" if val_max < 100 else "00")
            self.update_time_value()
            return

        if new_value < val_min:
            widget.setValue(val_max)
            widget.setPrefix("")
            self.update_time_value()
            return

        if new_value < 10:
            widget.setPrefix("0" if val_max < 100 else "00")
        elif new_value < 100:
            widget.setPrefix("" if val_max < 100 else "0")
        else:
            widget.setPrefix("")

        self.update_time_value()


class Widget_seconds(QWidget):
    time_changed_signal = pyqtSignal(float)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent=parent)
        lay = QHBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)

        self.seconds2 = QDoubleSpinBox()
        self.seconds2.setValue(0)
        self.seconds2.setMinimum(-100_000_000)
        self.seconds2.setMaximum(100_000_000)
        self.seconds2.setDecimals(3)
        self.seconds2.valueChanged.connect(self.value_changed)
        lay.addWidget(self.seconds2)

        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        lay.addItem(spacerItem)

        self.setLayout(lay)

    def value_changed(self, v):
        self.time_changed_signal.emit(v)


class Duration_widget(QWidget):
    def __init__(self, time_value=0, parent=None):
        super().__init__()

        self.time_value = dec(time_value).quantize(dec(".001"))

        lay = QHBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)

        self.Stack = QStackedWidget()

        self.w1 = Widget_hhmmss()
        self.w1.time_changed_signal.connect(self.time_changed)
        self.Stack.addWidget(self.w1)

        self.w2 = Widget_seconds()
        self.w2.time_changed_signal.connect(self.time_changed)
        self.Stack.addWidget(self.w2)

        lay.addWidget(self.Stack)

        self.format_hhmmss = QRadioButton("HH:MM:SS:MS")
        self.format_hhmmss.setChecked(True)
        self.format_hhmmss.clicked.connect(self.set_format_hhmmss)
        lay.addWidget(self.format_hhmmss)
        self.format_s = QRadioButton("seconds")
        self.format_s.clicked.connect(self.set_format_s)
        lay.addWidget(self.format_s)

        lay.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.setLayout(lay)

        self.set_time(self.time_value)

    def time_changed(self, x):
        """
        widget time has changed
        """
        self.time_value = x

    def set_time(self, new_time):
        if new_time.is_nan():
            return

        self.w1.sign.setText("-" if new_time < 0 else "+")

        h = int(abs(new_time) // 3600)
        m = int((abs(new_time) - h * 3600) // 60)
        s = int((abs(new_time) - h * 3600 - m * 60))
        ms = round((abs(new_time) - h * 3600 - m * 60 - s) * 1000)

        self.w1.hours.setValue(h)
        self.w1.minutes.setValue(m)
        self.w1.seconds.setValue(s)
        self.w1.milliseconds.setValue(ms)

        self.w2.seconds2.setValue(new_time)

        self.time_value = new_time

    def set_format_s(self):
        """
        switch to seconds widget
        """

        self.format_s.setChecked(True)
        self.w2.seconds2.setValue(self.time_value)
        self.Stack.setCurrentIndex(1)

    def set_format_hhmmss(self):
        """
        switch to HHMMSS widget
        """

        self.format_hhmmss.setChecked(True)
        self.set_time(self.time_value)
        self.Stack.setCurrentIndex(0)

    def set_format(self, time_format):
        """
        switch time format in base of time_format value
        """
        if time_format in [cfg.HHMMSS, cfg.HHMMSSZZZ]:
            self.set_format_hhmmss()
        if time_format in [cfg.S]:
            self.set_format_s()

    def get_time(self) -> dec:
        """
        return time displayed by widget in seconds
        """
        return dec(self.time_value).quantize(dec(".001"))
