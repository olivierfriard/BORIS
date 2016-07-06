try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

import sys


class BehaviorsMap(QWidget):

    clickSignal = pyqtSignal(str)

    def __init__(self, behaviorsList, parent = None):
        super(BehaviorsMap, self).__init__(parent)

        self.setWindowTitle("Behaviors map")

        self.grid = QGridLayout(self)

        dim = int(len(behaviorsList)**0.5 + 0.999)

        c = 0
        for i in range(1, dim + 1):
            for j in range(1, dim + 1):
                if c >= len(behaviorsList):
                    break
                self.addWidget(behaviorsList[c],i,j)
                c += 1


    def addWidget(self, behaviorCode,i,j):

        self.grid.addWidget(Test(),i,j)

        index = self.grid.count() - 1

        widget = self.grid.itemAt(index).widget()

        if widget is not None:
            widget.pushButton.setText(behaviorCode)
            widget.pushButton.clicked.connect(lambda: self.click(behaviorCode))

    def click(self, behaviorCode):
        self.clickSignal.emit(behaviorCode)



class Test(QWidget):
    def __init__( self, parent=None):
        super(Test, self).__init__(parent)

        self.pushButton = QPushButton()
        self.pushButton.setStyleSheet("background-color: red; border-radius: 0px; min-width: 50px;max-width: 200px; min-height:50px; max-height:200px")

        layout = QHBoxLayout()
        layout.addWidget(self.pushButton)
        self.setLayout(layout)


'''
app = QApplication(sys.argv)
behaviorsMap = BehaviorsMap(["AA","BB", "CC", "DD","EE","FF","GG","HH", "JJ"])
behaviorsMap.show()
app.exec_()
'''
