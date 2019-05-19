"""

widget to edit duration > 24 h or < 0

https://stackoverflow.com/questions/44380202/creating-a-custom-widget-in-pyqt5
"""


from PyQt5.QtWidgets import *


class Duration_widget(QWidget):

    #time_value = 0

    class Widget_hhmmss(QWidget):

        time_value = 0

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

            self.time_value =  (self.hours.value() * 3600 + self.minutes.value() * 60 + self.seconds.value() + self.milliseconds.value() / 1000)
            print("self.time_value", self.time_value)


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

        def __init__(self, parent=None):
            QWidget.__init__(self, parent=parent)
            lay = QHBoxLayout(self)

            self.seconds2 = QDoubleSpinBox()
            self.seconds2.setValue(0)
            self.seconds2.setMinimum(-100_000_000)
            self.seconds2.setMaximum(100_000_000)
            self.seconds2.setDecimals(3)
            lay.addWidget(self.seconds2)


    def __init__(self, parent=None):

        QWidget.__init__(self, parent=parent)
        lay = QHBoxLayout(self)

        self.Stack = QStackedWidget()
        self.w1 =self.Widget_hhmmss()
        self.w2 =self.Widget_seconds()
        self.Stack.addWidget(self.w1)
        self.Stack.addWidget(self.w2)

        lay.addWidget(self.Stack)

        format_hhmmss = QRadioButton("hh:mm:ss")
        format_hhmmss.setChecked(True)
        format_hhmmss.clicked.connect(self.set_format_hhmmss)
        lay.addWidget(format_hhmmss)
        format_s = QRadioButton("seconds")
        format_s.clicked.connect(self.set_format_s)
        lay.addWidget(format_s)
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        lay.addItem(spacerItem)


    def set_format_s(self):

        self.w2.seconds2.setValue(- self.w1.time_value if self.w1.sign.text() == "-" else self.w1.time_value)
        self.Stack.setCurrentIndex(1)

    def set_format_hhmmss(self):

        self.w1.sign.setText("-" if self.w2.seconds2.value() < 0 else "+")
        self.w1.time_value = abs(self.w2.seconds2.value())
        print(self.w1.time_value)

        h = self.w1.time_value // 3600
        m = (self.w1.time_value - h * 3600) // 60
        s = int((self.w1.time_value - h * 3600 - m * 60))
        ms = (self.w1.time_value - h * 3600 - m * 60 - s) * 1000

        self.w1.hours.setValue(h)
        self.w1.minutes.setValue(m)
        self.w1.seconds.setValue(s)
        self.w1.milliseconds.setValue(ms)

        self.Stack.setCurrentIndex(0)


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    w = Duration_widget()
    w.show()
    sys.exit(app.exec_())
