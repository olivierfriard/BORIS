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

from utilities import check_txt_file


class MyMplCanvas(FigureCanvas):

    def __init__(self, parent=None):
        self.fig = Figure()
        self.axes = self.fig.add_subplot(1,1,1)
        
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self, QSizePolicy.Expanding, QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)


class Plot_data(QWidget):
    send_fig = pyqtSignal(float)

    def __init__(self, file_name, interval, color, plot_title, y_label, columns_to_plot):
        super(Plot_data, self).__init__()

        self.myplot = MyMplCanvas(self)

        self.layout = QGridLayout()
        self.layout.addWidget(self.myplot)
        
        self.color = color
        self.plot_title = plot_title
        self.y_label = y_label
        
        r = check_txt_file(file_name)

        all_data = np.loadtxt(file_name, delimiter=r["separator"])
        
        time_column_idx = int(columns_to_plot.split(",")[0]) - 1
        value_column_idx = int(columns_to_plot.split(",")[-1]) - 1
        
        print("time_column_idx,value_column_idx", time_column_idx,value_column_idx)

        data = all_data[:, [time_column_idx, value_column_idx]] # time in 1st column, value in 2nd
        
        del all_data
        
        # time
        min_time_value, max_time_value = min(data[:,0]), max(data[:,0])

        print("min_time_value, max_time_value", min_time_value, max_time_value)

        # variable
        min_var_value, max_var_value = min(data[:,1]), max(data[:,1])
        
        print("min_var_value, max_var_value", min_var_value, max_var_value)
        
        diff = set(np.round(np.diff(data, axis=0)[:,0], 4))
        min_time_step = min(diff)

        print("diff", diff, min_time_step)
        
        if min(diff) == 0:
            print("more values for same time")
            self.close()

        # check if time is not regular
        if len(diff) != 1:
            min_time_step = min(diff)

            # increase display speed
            if min_time_step > 0.1:
                min_time_step = 0.1
            
            x2 = np.arange(min_time_value, max_time_value + min_time_step, min_time_step)
            
            y2 = np.interp(x2, data[:,0], data[:,1])
            print("len(x1)", len(x2))
            print("len(y2)", len(y2))
            
            data = np.array((x2, y2)).T
            
            del x2, y2
            
            print(data)
            
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

        #period = round((data[-1, 0] - data[0, 0]) / len(data), 4)

        max_frequency = 1 / list(diff)[0]

        time_interval = interval * max_frequency

        # plotter and thread are none at the beginning
        self.plotter = Plotter()
        self.plotter.data = data
        self.plotter.max_frequency = max_frequency
        self.plotter.time_interval = time_interval
        self.plotter.min_value, self.plotter.max_value = min_var_value, max_var_value

        self.thread = QThread()

        # connect signals
        self.send_fig.connect(self.plotter.replot)
        self.plotter.return_fig.connect(self.plot)
        #move to thread and start
        self.plotter.moveToThread(self.thread)
        self.thread.start()

    def update_plot(self, time_):
        """
        update plot by signal
        """
        self.send_fig.emit(time_)
        
    def close_plot(self):
        self.thread.quit()
        self.thread.wait()
        self.close()


    # Slot receives data and plots it
    def plot(self, x, y, position_data, position_start, min_value, max_value, position_end, max_frequency):
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
    return_fig = pyqtSignal(object, object, int, float, float, float, float, float)

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
                             position_end, self.max_frequency)

        

if __name__ == '__main__':
    app = QApplication(sys.argv)
    plot_data = Plot_data("ecg_converted.tsv", 60, "b-", "aa", "y lab")
    
    plot_data.show()

    plot_data2 = Plot_data("ecg_converted2.tsv", 120, "r-", "bb", "y lab")
    
    plot_data2.show()

    plot_data.start_update()
    plot_data2.start_update()


    sys.exit(app.exec_())
