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
import logging
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

    def __init__(self, file_name, interval, time_offset, color, plot_title, y_label, columns_to_plot,
                       substract_first_value, converters, column_converter, log_level="",):
        super(Plot_data, self).__init__()

        if log_level:
            logging.basicConfig(level=log_level)

        d = {}
        # convert dict keys in int:
        for k in column_converter:
            d[int(k)] = column_converter[k]
        column_converter = dict(d)
        
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

        result, error_msg, data = txt2np_array(file_name,
                                               columns_to_plot,
                                               substract_first_value,
                                               converters=converters,
                                               column_converter=column_converter,
                                               ) # txt2np_array defined in utilities.py

        if not result:
            self.error_msg = error_msg
            return

        logging.debug("data[50]: {}".format(data[:50]))
        logging.debug("shape: {}".format(data.shape))

        if data.shape == (0,):
            self.error_msg = "Empty input file"
            return

        # time
        min_time_value, max_time_value = min(data[:,0]), max(data[:,0])

        # variable
        min_var_value, max_var_value = min(data[:,1]), max(data[:,1])

        # check if time is linear
        diff = set(np.round(np.diff(data, axis=0)[:,0], 4))
        if min(diff) == 0:
            self.error_msg = "more values for same time"
            return

        logging.debug("diff: {}".format(diff))
        min_time_step = min(diff)
        logging.debug("min_time_step: {}".format(min_time_step))


        # check if sampling rate is not constant
        if len(diff) != 1:
            logging.debug("len diff != 1")
            min_time_step = min(diff)
            logging.debug("min_time_step: {}".format(min_time_step))

            # increase display speed
            if min_time_step > 0.1:
                min_time_step = 0.1
            
            x2 = np.arange(min_time_value, max_time_value + min_time_step, min_time_step)
            y2 = np.interp(x2, data[:,0], data[:,1])

            data = np.array((x2, y2)).T

            logging.debug("data[:,0]: {}".format(data[:,0]))
            del x2, y2

            # time
            min_time_value, max_time_value = min(data[:,0]), max(data[:,0])
            # variable
            min_var_value, max_var_value = min(data[:,1]), max(data[:,1])

            diff = set(np.round(np.diff(data, axis=0)[:,0], 4))
            min_time_step = min(diff)


        # subsampling
        data = data[0::int(0.04 / min_time_step)]
        
        min_time_step = 0.04

        logging.debug("new data after subsampling: {}".format(data[:50]))

        min_value, max_value = min(data[:, 1]), max(data[:, 1])

        max_frequency = 1 / min_time_step

        self.time_interval = interval * max_frequency

        # plotter and thread are none at the beginning
        self.plotter = Plotter()
        self.plotter.data = data
        self.plotter.max_frequency = max_frequency

        #self.plotter.time_interval = time_interval
        self.plotter.min_value = min_var_value
        self.plotter.max_value = max_var_value

        self.plotter.min_time_value = min_time_value
        self.plotter.max_time_value = max_time_value

        
        self.plotter.min_time_step = min_time_step
        
        # interval must be even
        interval += 1 if interval % 2 else 0
        self.plotter.interval = interval


        self.thread = QThread()

        # connect signals
        self.send_fig.connect(self.plotter.replot)
        self.plotter.return_fig.connect(self.plot)
        #move to thread and start
        self.plotter.moveToThread(self.thread)
        self.thread.start()


    def zoom(self, z):
        if z == -1 and self.plotter.interval <= 10:
            return
            
        if z == 1 and self.plotter.interval > 3600:
            return

        new_interval = round(self.plotter.interval + z * self.plotter.interval/2)
        new_interval += 1 if new_interval % 2 else 0

        self.plotter.interval = new_interval


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
    def plot(self, x, y, position_data, position_start, min_value, max_value, position_end):

        logging.debug("len x (plot): {}".format(len(x)))
        logging.debug("len y (plot): {}".format(len(y)))

        # print current value
        if x[0] == 0:
            self.lb_value.setText(str(round(y[position_data], 3)))
        else:
            self.lb_value.setText(str(round(y[len(y) // 2], 3)))

        try:
            self.myplot.axes.clear()
            self.myplot.axes.set_xlim(position_start , position_end)
    
            self.myplot.axes.set_ylim((min_value, max_value))
    
            self.myplot.axes.plot(x, y)
            self.myplot.axes.axvline(x=position_data, color="red", linestyle='-')
    
            self.myplot.draw()
        except:
            logging.debug("error")
            pass # only for protection agains crash


class Plotter(QObject):
    return_fig = pyqtSignal(np.ndarray, # x array
                            np.ndarray, #y array
                            float, # position_data
                            float, #position start
                            float, #min value
                            float, #max value
                            float # position end
                            )

    @pyqtSlot(float)
    def replot(self, time_): # time_ in s

        current_time = time_
        
        logging.debug("============================================")
        
        '''
        print("============================================")
        print("current time", current_time)
        print("self.min_time_value <= current_time <= self.max_time_value", self.min_time_value <= current_time <= self.max_time_value)
        '''

        logging.debug("current_time: {}".format(current_time))

        current_discrete_time = round(round( current_time / self.min_time_step ) * self.min_time_step, 2)
        logging.debug("current_discrete_time: {}".format(current_discrete_time))
        logging.debug("self.interval: {}".format(self.interval))


        freq_interval = int(round(self.interval / self.min_time_step))
        '''
        print("freq interval", freq_interval)
        '''

        if self.min_time_value <= current_discrete_time <= self.max_time_value:
            
                logging.debug("self.min_time_value <= current_discrete_time <= self.max_time_value")

                idx = np.where(self.data[:,0] == current_discrete_time)[0]
                '''
                print("idx 1", idx)
                print(self.data[:20])
                '''
                if not len(idx):
                    idx = np.where(abs(self.data[:,0] - current_discrete_time) <= 0.02)[0]
                    '''
                    print("idx 2", idx)
                    '''

                if len(idx):

                    position_data = idx[0]
                    
                    logging.debug("position data: {}".format(position_data))
                    
                    #print(current_discrete_time, position_data, self.data[position_data:position_data+1][:,1])

                    position_start = int(position_data - freq_interval // 2)
                    '''
                    print("position_start", position_start)
                    '''

                    flag_i, flag_j  = False, False

                    if position_start < 0:
                        i = np.array([np.nan]*abs(position_start)).T
                        flag_i = True

                        logging.debug("len(i): {}".format(len(i)))

                        position_start =0

                    position_end = int(position_data + freq_interval // 2)
                    '''print("position_end", position_end)'''
        
                    if position_end >= len(self.data):
                        j = np.array([np.nan] * abs(position_end - len(self.data))).T
                        flag_j = True
                        
                        '''
                        print("len j", len(j))
                        '''
        
                        position_end = len(self.data)
        
                    d = self.data[position_start:position_end][:,1]
        
                    if flag_i:
                        d = np.append(i , d, axis=0)
                
                    if flag_j:
                        d = np.append(d, j, axis=0)
                    
                    '''
                    print("len d", len(d))
                    '''
                else:
                    # not known problem
                    #return nan data
                    d = np.array([np.nan] * int(self.interval /self.min_time_step)).T

                    
        elif current_time > self.max_time_value:

            logging.debug("self.interval/self.min_time_step/2: {}".format(self.interval/self.min_time_step/2))

            
            #print((current_time - self.max_time_value)/self.min_time_step)
            
            #dim_footer = int((current_time - self.max_time_value)/self.min_time_step +  self.interval/self.min_time_step/2)
            dim_footer = int(round((current_time - self.max_time_value)/self.min_time_step +  self.interval / self.min_time_step / 2))

            footer = np.array([np.nan] * dim_footer ).T
            logging.debug("len footer: {}".format(len(footer)))

            a = (self.interval/2 - (current_time - self.max_time_value)) / self.min_time_step
            logging.debug("a: {}".format(a)) 

            if a >= 0:
                
                logging.debug("a>=0")

                st = int(round(len(self.data) - a))
                logging.debug("st: {}".format(st))

                flag_i = False
                if st < 0:
                    i = np.array([np.nan] * abs(st)).T
                    st = 0
                    flag_i = True

                d = np.append(self.data[st:len(self.data)][:,1] , footer, axis=0)

                if flag_i:
                    d = np.append(i, d, axis=0)

                logging.debug("len d a>=0: {}".format(len(d)))

            else: # a <0
                logging.debug("a<0")
                d = np.array([np.nan] * int(self.interval /self.min_time_step)).T
            
                logging.debug("len d a<0: {}".format(len(d)))

        elif current_time < self.min_time_value:

            x = (self.min_time_value - current_time) / self.min_time_step
            dim_header = int(round(self.interval / self.min_time_step / 2 + x))
            header = np.array([np.nan] * dim_header ).T

            '''
            print("len header", len(header))
            '''

            b = int(round(self.interval / self.min_time_step / 2 - x))
            '''
            print("b", b)
            '''

            if b >= 0:
                d = np.append(header, self.data[0:b][:,1],  axis=0)
                if len(d) < freq_interval:
                    d = np.append(d, np.array([np.nan] * int(freq_interval - len(d))).T,  axis=0)

            else:
                d = np.array([np.nan] * int(self.interval /self.min_time_step)).T

        y = d
        logging.debug("len y: {}".format(len(y)))

        
        logging.debug("self.min_time_step: {}".format(self.min_time_step))
        
        x = np.arange(current_time - self.interval//2, current_time + self.interval//2, self.min_time_step)
        #x = np.arange(round(current_discrete_time - self.interval//2,2), round(current_discrete_time + self.interval//2, 2), self.min_time_step)

        logging.debug("len x 1: {}".format(len(x)))

        self.return_fig.emit(x, y,
                             current_discrete_time, #position_data
                             current_discrete_time - self.interval//2, #position_start
                             self.min_value,
                             self.max_value,
                             current_discrete_time + self.interval//2 #position_end,
                             )



