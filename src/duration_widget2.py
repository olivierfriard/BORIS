"""

widget to edit duration > 24 h or < 0

https://stackoverflow.com/questions/44380202/creating-a-custom-widget-in-pyqt5
"""


from PyQt5.QtWidgets import *
from PyQt5.QtCore import *


class Widget_hhmmss(QWidget):

    my_signal = pyqtSignal(float)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent=parent)
        
        
        lay = QHBoxLayout(self)

        self.sign = QPushButton("+")
        self.sign.clicked.connect(self.change_sign)
        self.sign.setStyleSheet('font-size:12px;')
        lay.addWidget(self.sign)

        self.hours = QSpinBox()
        self.hours.setValue(0)
        self.hours.setMinimum(0)
        self.hours.setMaximum(1000)
        #self.hours.setPrefix("0")
        #self.hours.valueChanged.connect(lambda value, x=self.hours: self.value_changed(value, x, 0, 1000))
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

    def change_sign(self):
        print("change sign")
        self.sign.setText("+" if self.sign.text() == "-" else "-")


    def update_time_value(self):
        #flag_neg = -1 if (self.hours.value() < 0) else 1

        self.my_signal.emit((self.hours.value() * 3600
                             + self.minutes.value() * 60
                             + self.seconds.value()
                             + self.milliseconds.value() / 1000))


    def value_changed(self, new_value, widget, val_min, val_max):
        print("value changed")

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

    my_signal = pyqtSignal(float)

    def __init__(self, parent=None):
        QWidget.__init__(self, parent=parent)
        lay = QHBoxLayout(self)

        self.seconds2 = QDoubleSpinBox()
        self.seconds2.setValue(0)
        self.seconds2.setMinimum(-100_000_000)
        self.seconds2.setMaximum(100_000_000)
        self.seconds2.setDecimals(3)
        self.seconds2.valueChanged.connect(self.value_changed)
        lay.addWidget(self.seconds2)

    def value_changed(self, v):

        self.my_signal.emit(v)


class Duration_widget(QWidget):
    
    time_value = 0.0

    def __init__(self, parent=None):

        QWidget.__init__(self, parent=parent)

        self.time_value = 0

        lay = QHBoxLayout(self)

        self.Stack = QStackedWidget()
        self.w1 = Widget_hhmmss()
        
        self.w1.my_signal.connect(self.w1_emit)
        
        self.w2 = Widget_seconds()
        self.Stack.addWidget(self.w1)
        self.Stack.addWidget(self.w2)
        self.w2.my_signal.connect(self.w1_emit)
        #self.w2.seconds2.valueChanged.connect(self.w2_value_changed)

        lay.addWidget(self.Stack)

        self.format_hhmmss = QRadioButton("hh:mm:ss")
        self.format_hhmmss.setChecked(True)
        self.format_hhmmss.clicked.connect(self.set_format_hhmmss)
        lay.addWidget(self.format_hhmmss)
        self.format_s = QRadioButton("seconds")
        self.format_s.clicked.connect(self.set_format_s)
        lay.addWidget(self.format_s)
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        lay.addItem(spacerItem)


    def w1_emit(self, x):
        print("X", x)
        self.time_value = x


    def set_time(self, new_time):


        self.w1.sign.setText("-" if new_time < 0 else "+")
        #self.time_value = abs(new_time)

        #print("self.w1.time_value", self.w1.time_value)


        h = new_time // 3600
        m = (new_time - h * 3600) // 60
        s = int((new_time - h * 3600 - m * 60))
        ms = (new_time - h * 3600 - m * 60 - s) * 1000

        self.w1.hours.setValue(h)
        self.w1.minutes.setValue(m)
        self.w1.seconds.setValue(s)
        self.w1.milliseconds.setValue(ms)

        # self.w2.seconds2.setValue(- self.w1.time_value if self.w1.sign.text() == "-" else self.w1.time_value)


    def set_format_s(self):

        self.format_s.setChecked(True)
        self.w2.seconds2.setValue( self.time_value)
        self.Stack.setCurrentIndex(1)


    def set_format_hhmmss(self):

        self.format_hhmmss.setChecked(True)
        self.set_time(self.time_value)

        self.Stack.setCurrentIndex(0)


    def get_time(self):
        """
        return time displayed by widget
        """
        return - self.time_value if self.w1.sign.text() == "-" else self.time_value


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    w = Duration_widget()
    w.show()
    sys.exit(app.exec_())
