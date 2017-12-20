'''

https://stackoverflow.com/questions/41156260/how-to-use-a-qthread-to-update-a-matplotlib-figure-with-pyqt

'''


from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import sys
import numpy as np
import time

from utilities import check_txt_file, txt2np_array


class MyMplCanvas(FigureCanvas):

    def __init__(self, parent=None):
        self.fig = Figure()
        self.axes = self.fig.add_subplot(1, 1, 1)
        
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)


class Plot_data(QWidget):
    send_fig = pyqtSignal(float)

    def __init__(self, file_name, interval, time_offset, color, plot_title, y_label, columns_to_plot, substract_first_value):
        super(Plot_data, self).__init__()

        self.myplot = MyMplCanvas(self)

        self.button_plus = QPushButton("+", self)
        self.button_plus.clicked.connect(lambda: self.zoom(-1))
        
        self.button_minus = QPushButton("-", self)
        self.button_minus.clicked.connect(lambda: self.zoom(1))

        self.layout = QVBoxLayout()
        
        self.hlayout1 = QHBoxLayout()
        self.hlayout1.addWidget(QLabel("Zoom"))
        self.hlayout1.addWidget(self.button_plus)
        self.hlayout1.addWidget(self.button_minus)
        self.hlayout1.addItem( QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        self.hlayout2 = QHBoxLayout()
        self.hlayout2.addWidget(QLabel("Value"))
        self.lb_value = QLabel("")
        self.hlayout2.addWidget(self.lb_value)
        self.hlayout2.addItem( QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        self.layout.addLayout(self.hlayout1)
        self.layout.addLayout(self.hlayout2)
        self.layout.addWidget(self.myplot)
        
        self.setLayout(self.layout)
        
        self.color = color
        self.plot_title = plot_title
        self.time_offset = time_offset
        self.y_label = y_label
        self.error_msg = ""

        
        result, data = txt2np_array(file_name, columns_to_plot, substract_first_value)
        if not result:
            self.error_msg = data
            return

        print(data)
        print(data.shape)


        if data.shape == (0,):
            self.error_msg = "Empty input file"
            return
        # time
        min_time_value, max_time_value = min(data[:,0]), max(data[:,0])

        '''
        print("min_time_value, max_time_value", min_time_value, max_time_value)
        '''

        # variable
        min_var_value, max_var_value = min(data[:,1]), max(data[:,1])
        
        '''
        print("min_var_value, max_var_value", min_var_value, max_var_value)
        '''
        
        diff = set(np.round(np.diff(data, axis=0)[:,0], 4))
        min_time_step = min(diff)

        '''
        print("diff", diff, min_time_step)
        '''

        if min(diff) == 0:
            self.error_msg = "more values for same time"
            return

        # check if time is not regular
        if len(diff) != 1:
            min_time_step = min(diff)

            # increase display speed
            if min_time_step > 0.1:
                min_time_step = 0.1
            
            x2 = np.arange(min_time_value, max_time_value + min_time_step, min_time_step)
            
            y2 = np.interp(x2, data[:,0], data[:,1])
            '''
            print("len(x1)", len(x2))
            print("len(y2)", len(y2))
            '''

            data = np.array((x2, y2)).T
            
            del x2, y2
            
            '''print(data)'''
            
            # time
            min_time_value, max_time_value = min(data[:,0]), max(data[:,0])
            # variable
            min_var_value, max_var_value = min(data[:,1]), max(data[:,1])

            diff = set(np.round(np.diff(data, axis=0)[:,0], 4))


        # check if time starts from 0
        if min_time_value != 0:
            
            x =  np.arange(0, min_time_value, min_time_step)
            # head = np.array( (x, np.array([np.nan]*len(x))) ).T 
            data = np.append(np.array( (x, np.array([np.nan] * len(x))) ).T , data, axis=0)
            del x

        min_value, max_value = min(data[:, 1]), max(data[:, 1])

        max_frequency = 1 / list(diff)[0]

        self.time_interval = interval * max_frequency

        # plotter and thread are none at the beginning
        self.plotter = Plotter()
        self.plotter.data = data
        self.plotter.max_frequency = max_frequency
        self.plotter.time_interval = self.time_interval
        self.plotter.min_value, self.plotter.max_value = min_var_value, max_var_value

        self.thread = QThread()

        # connect signals
        self.send_fig.connect(self.plotter.replot)
        self.plotter.return_fig.connect(self.plot)
        #move to thread and start
        self.plotter.moveToThread(self.thread)
        self.thread.start()


    def zoom(self, z):
        if z == -1 and self.plotter.time_interval < 10:
            return
        self.plotter.time_interval = round(self.plotter.time_interval + z * self.plotter.time_interval/2)


    def update_plot(self, time_):
        """
        update plot by signal
        """
        self.send_fig.emit(time_ + self.time_offset)


    def close_plot(self):
        self.thread.quit()
        self.thread.wait()
        self.close()


    # Slot receives data and plots it
    def plot(self, x, y, position_data, position_start, min_value, max_value, position_end, max_frequency, time_interval):


        if x[0] == 0:
            self.lb_value.setText(str(round(y[position_data], 3)))
        else:
            self.lb_value.setText(str(round(y[len(y) // 2], 3)))

        self.myplot.axes.clear()
        
        self.myplot.axes.set_title(self.plot_title)
        
        self.myplot.axes.set_xlim(position_start , position_end)

        self.myplot.axes.set_xticklabels([str(int(w / max_frequency)) for w in self.myplot.axes.get_xticks()])

        self.myplot.axes.set_ylim((min_value, max_value))
        
        self.myplot.axes.set_ylabel(self.y_label)
        
        self.myplot.axes.axvline(x=position_data, color="red", linestyle='-')

        self.myplot.axes.plot(x, y, self.color)

        self.myplot.draw()


class Plotter(QObject):
    return_fig = pyqtSignal(object, object, int, float, float, float, float, float, float)

    @pyqtSlot(float)
    def replot(self, time_): # time_ in s

        current_time = time_

        position_data = int(current_time * self.max_frequency)

        position_start = position_data - self.time_interval // 2
        position_end = position_data + self.time_interval // 2

        if position_start < 0:
            data1 = 0
            data2 = int(position_start + self.time_interval)
        else:
            data1 = int(position_start)
            data2 = int(position_end)
            
        x = np.arange(data1, data2, 1)
        y = self.data[data1:data2][:,1]
        
        # check if values are enough
        if len(y) < len(x):
            # complete with nan until len of x
            y = np.append(y, [np.nan] * (len(x) - len(y)))

        self.return_fig.emit(x, y,
                             position_data,
                             position_start,
                             self.min_value, self.max_value,
                             position_end,
                             self.max_frequency,
                             self.time_interval)

