#!/usr/bin/env python

"""

BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2014 Olivier Friard


  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.
  
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.
  
  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
  MA 02110-1301, USA.

"""

DEBUG = True

from config import *

from PySide.QtCore import *
from PySide.QtGui import *


class ExclusionMatrix(QDialog):

    def __init__(self):
        super(ExclusionMatrix, self).__init__()

        self.label = QLabel()
        self.label.setText('Check behaviors excluded by')

        self.twExclusions = QTableWidget()

        hbox = QVBoxLayout(self)

        hbox.addWidget(self.label)
        hbox.addWidget(self.twExclusions)

        self.pbOK = QPushButton('OK')
        self.pbOK.clicked.connect(self.pbOK_clicked)
        self.pbCancel = QPushButton('Cancel')
        self.pbCancel.clicked.connect(self.pbCancel_clicked)

        hbox2 = QHBoxLayout(self)

        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        hbox2.addItem(spacerItem)

        hbox2.addWidget(self.pbCancel)
        hbox2.addWidget(self.pbOK)

        hbox.addLayout(hbox2)

        self.setLayout(hbox)

        self.setWindowTitle('Behaviors exclusion matrix')
        self.resize(800, 300)


    def pbOK_clicked(self):
        self.accept()

    def pbCancel_clicked(self):
        self.reject()


import dialog

from project_ui import Ui_dlgProject

class DlgProject(QDialog, Ui_dlgProject):

    def __init__(self, debug, parent=None ):

        super(DlgProject, self).__init__(parent)
        self.setupUi(self)

        self.DEBUG = debug

        self.lbObservationsState.setText('')
        self.lbSubjectsState.setText('')
        
        self.twBehaviors.setSortingEnabled(False)
        self.twSubjects.setSortingEnabled(False)


        ### behaviors tab
        self.pbAddObservation.clicked.connect(self.pbAddBehavior_clicked)
        self.pbClone.clicked.connect(self.pbClone_clicked)
         
        self.pbExclusionMatrix.clicked.connect(self.pbExclusionMatrix_clicked)
        
        self.pbRemoveBehavior.clicked.connect(self.pbRemoveBehavior_clicked)
        self.pbRemoveAllBehaviors.clicked.connect(self.pbRemoveAllBehaviors_clicked)

        self.pbImportBehaviorsFromProject.clicked.connect(self.pbImportBehaviorsFromProject_clicked)
 
 
        ''' FIXME 2014-04-28 set buttons to not visible'''
        #self.pbSaveConfiguration.setVisible(False)
        #self.pbLoadConfiguration.setVisible(False)
        
        self.pbSaveConfiguration.clicked.connect(self.pbExportConfiguration_clicked)
        self.pbLoadConfiguration.clicked.connect(self.pbImportConfiguration_clicked)
        

        self.twBehaviors.cellChanged[int, int].connect(self.twObservations_cellChanged)

        self.cbAlphabeticalOrder_behavior.stateChanged.connect(self.cbAlphabeticalOrder_behavior_stateChanged)
        self.pbUp_behavior.clicked.connect(self.pbUp_behavior_clicked)
        self.pbDown_behavior.clicked.connect(self.pbDown_behavior_clicked)


        ### subjects
        self.pbAddSubject.clicked.connect(self.pbAddSubject_clicked)
        self.pbRemoveSubject.clicked.connect(self.pbRemoveSubject_clicked)
        self.twSubjects.cellChanged[int, int].connect(self.twSubjects_cellChanged)

        self.cbAlphabeticalOrder.stateChanged.connect(self.cbAlphabeticalOrder_stateChanged)
        self.pbUp.clicked.connect(self.pbUp_clicked)
        self.pbDown.clicked.connect(self.pbDown_clicked)        

        self.pbImportSubjectsFromProject.clicked.connect(self.pbImportSubjectsFromProject_clicked)

        ''' FIXME 2014-04-28 set buttons to not visible'''
        self.pbSaveSubjects.setVisible(False)
        self.pbLoadSubjects.setVisible(False)
        

        ''' FIXME 2014-04-28 buttons are not more available
        use import from project instead 
        self.pbSaveSubjects.clicked.connect(self.pbSaveSubjects_clicked)
        self.pbLoadSubjects.clicked.connect(self.pbLoadSubjects_clicked)
        '''

        ### independent variables tab
        self.pbAddVariable.clicked.connect(self.pbAddVariable_clicked)
        self.pbRemoveVariable.clicked.connect(self.pbRemoveVariable_clicked)

        self.cbAlphabeticalOrderVar.stateChanged.connect(self.cbAlphabeticalOrderVar_stateChanged)
        self.pbUpVar.clicked.connect(self.pbUpVar_clicked)
        self.pbDownVar.clicked.connect(self.pbDownVar_clicked)

        self.pbImportVarFromProject.clicked.connect(self.pbImportVarFromProject_clicked)

        ### observations
        self.pbRemoveObservation.clicked.connect(self.pbRemoveObservation_clicked)


        self.pbOK.clicked.connect(self.pbOK_clicked)
        self.pbCancel.clicked.connect(self.pbCancel_clicked)


    def pbAddVariable_clicked(self):
        '''
        add an independent variable
        '''
        if self.DEBUG: print 'add an independent variable'

        self.twVariables.setRowCount(self.twVariables.rowCount() + 1)

        for idx, field in enumerate(tw_indVarFields):

            if field == 'type':
                ### add type combobox
                comboBox = QComboBox()
                comboBox.addItem( NUMERIC )
                comboBox.addItem( TEXT )

                comboBox.setCurrentIndex( 0 )
        
                self.twVariables.setCellWidget(self.twVariables.rowCount() - 1, idx, comboBox)
            else:
                self.twVariables.setItem(self.twVariables.rowCount() - 1, idx , QTableWidgetItem(''))

    def pbRemoveVariable_clicked(self):
        '''
        remove the selected independent variable
        '''
        if self.DEBUG: print 'remove selected independent variable'

        if not self.twVariables.selectedIndexes():
            QMessageBox.warning(self, programName, 'First select a variable to remove')
        else:

            response = dialog.MessageDialog(programName, 'Remove the selected variable?', ['Yes', 'Cancel'])
            if response == 'Yes':
                self.twVariables.removeRow(self.twVariables.selectedIndexes()[0].row())

    def cbAlphabeticalOrderVar_stateChanged(self):
        '''
        change order of independent variables
        '''
        self.pbUpVar.setEnabled( not self.cbAlphabeticalOrderVar.isChecked())
        self.pbDownVar.setEnabled( not self.cbAlphabeticalOrderVar.isChecked())
        if self.cbAlphabeticalOrderVar.isChecked():
            self.twVariables.sortByColumn(0, Qt.AscendingOrder)   ### order by variable label


    def pbUp_behavior_clicked(self):
        ### move up selected behavior

        if self.twBehaviors.selectedIndexes() and self.twBehaviors.selectedIndexes()[0].row() > 0:

            selectedRow = self.twBehaviors.selectedIndexes()[0].row()
            subjectToMoveUp = [ self.twBehaviors.cellWidget(selectedRow, 0).currentIndex() ]
            subjectToMoveDown = [self.twBehaviors.cellWidget(selectedRow - 1, 0).currentIndex() ]

            for x in range(1, 5+1):
                subjectToMoveUp.append( self.twBehaviors.item( selectedRow , x).text() )
                subjectToMoveDown.append( self.twBehaviors.item( selectedRow - 1, x).text() )

            self.twBehaviors.cellWidget(selectedRow , 0).setCurrentIndex( subjectToMoveDown[0] )
            self.twBehaviors.cellWidget(selectedRow - 1, 0).setCurrentIndex( subjectToMoveUp[0] )

            for x in range(1, 5+1):
                self.twBehaviors.item( selectedRow , x).setText(subjectToMoveDown[x])
                self.twBehaviors.item( selectedRow - 1, x).setText(subjectToMoveUp[x])

            self.twBehaviors.selectRow(selectedRow - 1)



    def pbUpVar_clicked(self):
        '''
        move selected variable up
        '''
        if self.twVariables.selectedIndexes() and self.twVariables.selectedIndexes()[0].row() > 0:

            selectedRow = self.twVariables.selectedIndexes()[0].row()

            varToMoveUp, varToMoveDown = [], []

            for x in range(len(tw_indVarFields)):
                if x == 2:   ### type
                    varToMoveUp.append( self.twVariables.cellWidget(selectedRow, x).currentIndex() )
                    varToMoveDown.append( self.twVariables.cellWidget(selectedRow - 1, x).currentIndex() )
                else:
                    varToMoveUp.append( self.twVariables.item( selectedRow , x).text() )
                    varToMoveDown.append( self.twVariables.item( selectedRow - 1, x).text() )

            for x in range(len(tw_indVarFields)):
                if x == 2:   ### type
                    self.twVariables.cellWidget(selectedRow , x).setCurrentIndex( varToMoveDown[x] )
                    self.twVariables.cellWidget(selectedRow - 1, x).setCurrentIndex( varToMoveUp[x] )

                else:
                    self.twVariables.item( selectedRow , x).setText(varToMoveDown[x])
                    self.twVariables.item( selectedRow - 1, x).setText(varToMoveUp[x])

            self.twVariables.selectRow(selectedRow - 1)


    def pbDownVar_clicked(self):
        '''
        move selected variable down
        '''
        if self.twVariables.selectedIndexes() and self.twVariables.selectedIndexes()[0].row() < self.twVariables.rowCount() -1:
            selectedRow = self.twVariables.selectedIndexes()[0].row()
            subjectToMoveDown, subjectToMoveUp = [], []

            for x in range(len(tw_indVarFields)):
                if x == 2:   ### type
                    subjectToMoveDown.append( self.twVariables.cellWidget(selectedRow, x).currentIndex() )
                    subjectToMoveUp.append( self.twVariables.cellWidget(selectedRow + 1, x).currentIndex() )
                else:
                    subjectToMoveDown.append( self.twVariables.item( selectedRow , x).text() )
                    subjectToMoveUp.append( self.twVariables.item( selectedRow+1, x).text() )

            for x in range(len(tw_indVarFields)):
                if x == 2:   ### type
                    self.twVariables.cellWidget(selectedRow + 1, x).setCurrentIndex( subjectToMoveDown[x] )
                    self.twVariables.cellWidget(selectedRow , x).setCurrentIndex( subjectToMoveUp[x] )

                else:
                    self.twVariables.item( selectedRow + 1, x).setText(subjectToMoveDown[x])
                    self.twVariables.item( selectedRow , x).setText(subjectToMoveUp[x])

            self.twVariables.selectRow(selectedRow + 1)

    def pbImportVarFromProject_clicked(self):
        '''
        import independent variables from another project
        '''

        fd = QFileDialog(self)
        fileName, dummy = fd.getOpenFileName(self, 'Import independent variables from project file', '', 'Project files (*.boris);;All files (*)')
        if fileName:

            import json
            s = open(fileName, 'r').read()

            project = json.loads(s)

            ### independent variables
            if project[ INDEPENDENT_VARIABLES ]:

                ### check if variables are already present
                if self.twVariables.rowCount():
    
                    response = dialog.MessageDialog(programName, 'There are independent variables already configured. Do you want to append independent variables or replace them?', ['Append', 'Replace', 'Cancel'])
        
                    if response == 'Replace':
                        self.twVariables.setRowCount(0)
        
                    if response == 'Cancel':
                        return

                for i in sorted( project[ INDEPENDENT_VARIABLES ].keys() ):

                    self.twVariables.setRowCount(self.twVariables.rowCount() + 1)
    
                    for idx,field in enumerate( tw_indVarFields ):

                        item = QTableWidgetItem()

                        if field == 'type':

                            comboBox = QComboBox()
                            comboBox.addItem(NUMERIC)
                            comboBox.addItem(TEXT)
                            if project[INDEPENDENT_VARIABLES][i][field] == NUMERIC:
                                comboBox.setCurrentIndex( 0 )
                            if project[INDEPENDENT_VARIABLES][i][field] == TEXT:
                                comboBox.setCurrentIndex( 1 )

                            self.twVariables.setCellWidget(self.twVariables.rowCount() - 1, idx, comboBox)

                        else:
                            item.setText( project[INDEPENDENT_VARIABLES][i][field] )

                            self.twVariables.setItem(self.twVariables.rowCount() - 1, idx, item)

                self.twVariables.resizeColumnsToContents()

            else:
                QMessageBox.warning(self, programName,  'No independent variables found in project' )





    def cbAlphabeticalOrder_stateChanged(self):
        '''
        change order of subject
        '''
        self.pbUp.setEnabled( not self.cbAlphabeticalOrder.isChecked())
        self.pbDown.setEnabled( not self.cbAlphabeticalOrder.isChecked())
        if self.cbAlphabeticalOrder.isChecked():
            self.twSubjects.sortByColumn(1, Qt.AscendingOrder)   ### order by subject name

    def cbAlphabeticalOrder_behavior_stateChanged(self):

        self.pbUp_behavior.setEnabled( not self.cbAlphabeticalOrder_behavior.isChecked())
        self.pbDown_behavior.setEnabled( not self.cbAlphabeticalOrder_behavior.isChecked())
        if self.cbAlphabeticalOrder_behavior.isChecked():
            self.twBehaviors.sortByColumn(2, Qt.AscendingOrder)   ### order by code ascending



    def pbImportSubjectsFromProject_clicked(self):
        '''
        import subjects from another project
        '''
        fd = QFileDialog(self)
        fileName, dummy = fd.getOpenFileName(self, 'Import subjects from project file', '', 'Project files (*.boris);;All files (*)')

        if fileName:

            import json
            s = open(fileName, 'r').read()

            project = json.loads(s)
            if self.DEBUG: print project['subjects_conf']

            ### configuration of behaviours
            if project['subjects_conf']:

                if self.twSubjects.rowCount():
        
                    response = dialog.MessageDialog(programName, 'There are subjects already configured. Do you want to append subjects or replace them?', ['Append', 'Replace', 'Cancel'])
        
                    if response == 'Replace':
                        self.twSubjects.setRowCount(0)
        
                    if response == 'Cancel':
                        return


                for i in sorted( project['subjects_conf'].keys() ):

                    subject_key = project['subjects_conf'][i]['key']
                    subject_name = project['subjects_conf'][i]['name']

                    self.twSubjects.setRowCount(self.twSubjects.rowCount() + 1)

                    item = QTableWidgetItem( subject_key )
                    self.twSubjects.setItem(self.twSubjects.rowCount() - 1, 0 , item)

                    item = QTableWidgetItem( subject_name )
                    self.twSubjects.setItem(self.twSubjects.rowCount() - 1, 1 , item)


                self.twSubjects.resizeColumnsToContents()
            else:
                QMessageBox.warning(self, programName,  'No subjects configuration found in project' )


    def pbImportBehaviorsFromProject_clicked(self):
        '''
        import behaviors from another project
        '''

        fd = QFileDialog(self)
        fileName, dummy = fd.getOpenFileName(self, 'Import behaviors from project file', '', 'Project files (*.boris);;All files (*)')
        if fileName:

            import json
            s = open(fileName, 'r').read()

            project = json.loads(s)
            if self.DEBUG: print project['behaviors_conf']

            ### configuration of behaviours
            if project['behaviors_conf']:

                if self.twBehaviors.rowCount():

                    response = dialog.MessageDialog(programName, 'There are behaviors already configured. Do you want to append behaviors or replace them?', ['Append', 'Replace', 'Cancel'])
        
                    if response == 'Replace':
                        self.twBehaviors.setRowCount(0)
        
                    if response == 'Cancel':
                        return


                for i in sorted( project['behaviors_conf'].keys() ):

                    self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)
    
                    for field in project['behaviors_conf'][i]:

                        item = QTableWidgetItem()

                        if field == 'type':

                            comboBox = QComboBox()
                            for observation in observation_types:
                                comboBox.addItem(observation)
                            comboBox.setCurrentIndex( observation_types.index(project['behaviors_conf'][i][field]) )

                            self.twBehaviors.setCellWidget(self.twBehaviors.rowCount() - 1, 0, comboBox)

                        else:
                            item.setText( project['behaviors_conf'][i][field] )
                            
                            if field == 'excluded':
                                item.setFlags(Qt.ItemIsEnabled)

                            self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, fields[field] ,item)

                self.twBehaviors.resizeColumnsToContents()

            else:
                QMessageBox.warning(self, programName,  'No behaviors configuration found in project' )


    def pbExclusionMatrix_clicked(self):

        if self.DEBUG: print 'exclusion matrix'

        ex = ExclusionMatrix()

        headers = []
        excl = {}
        new_excl = {}

        for r in range(0, self.twBehaviors.rowCount()):

            combobox = self.twBehaviors.cellWidget(r, 0)

            if 'State' in observation_types[combobox.currentIndex()]:

                if self.twBehaviors.item(r, fields['code']):
                    headers.append( self.twBehaviors.item(r, fields['code']).text() )
                    excl[ self.twBehaviors.item(r, fields['code']).text() ] = self.twBehaviors.item(r, fields['excluded']).text().split(',')
                    new_excl[ self.twBehaviors.item(r, fields['code']).text() ] = []

        if self.DEBUG: print 'exclusion matrix', excl

        ex.twExclusions.setColumnCount( len( headers ) )
        
        ex.twExclusions.setRowCount( len( headers ) )
        
        ex.twExclusions.setHorizontalHeaderLabels ( headers)

        for r in range(0, len( headers ) ):

            for c in range(0, len( headers )):

                if c > r:

                    checkBox = QCheckBox()
                    
                    if headers[ c ] in excl[ headers[r] ] or headers[ r ] in excl[ headers[c] ]:

                        checkBox.setChecked(True)

                    ex.twExclusions.setCellWidget(r, c, checkBox)

        ex.twExclusions.setVerticalHeaderLabels ( headers)


        if ex.exec_():

            for r in range(0, len( headers )):

                for c in range(0, len( headers )):
                    if c > r:
                        checkBox = ex.twExclusions.cellWidget( r,c )
                        if checkBox.isChecked():

                            s1 = headers[c]
                            s2 = headers[r]
                            if not s2 in new_excl[s1]:
                                new_excl[s1].append(s2)
                            if not s1 in new_excl[s2]:
                                new_excl[s2].append(s1)

            if self.DEBUG: print 'new exclusion matrix', new_excl

            for r in range(0, self.twBehaviors.rowCount()):
                for e in excl:
                    if e == self.twBehaviors.item(r, fields['code']).text():
                        item = QTableWidgetItem( ','.join(new_excl[e]) )
                        self.twBehaviors.setItem(r, fields['excluded'] , item)


    def pbRemoveAllBehaviors_clicked(self):

        if self.twBehaviors.rowCount():

            response = dialog.MessageDialog(programName, 'Remove all behaviors?', ['Yes', 'Cancel'])

            if response == 'Yes':

                ### extract all codes to delete
                codesToDelete = []
                row_mem = {}
                for r in range(self.twBehaviors.rowCount()-1, -1, -1):
                    if self.twBehaviors.item(r, 2).text():
                        codesToDelete.append( self.twBehaviors.item(r, 2).text() )
                        row_mem[ self.twBehaviors.item(r, 2).text() ] = r

                ### extract all codes used in observations
                codesInObs = []
                for obs in  self.pj['observations']:
                    events = self.pj['observations'][ obs ]['events']
                    for event in events:
                        codesInObs.append( event[2] )

                for codeToDelete in codesToDelete:
                    ### if code to delete used in obs ask confirmation
                    if codeToDelete in codesInObs:
                        response = dialog.MessageDialog(programName, 'The code <b>%s</b> is used in observations!' % codeToDelete, ['Remove', 'Cancel'])
                        if response == 'Remove':
                            self.twBehaviors.removeRow(row_mem[ codeToDelete ] )
                    else: ### remove without asking
                        self.twBehaviors.removeRow(row_mem[ codeToDelete ] )


    def pbImportConfiguration_clicked(self):
        '''
        open and parse a configuration file
        '''
        if self.twBehaviors.rowCount():

            response = dialog.MessageDialog(programName, 'There are behaviors already configured. Do you want to append behaviors or replace them?', ['Append', 'Replace', 'Cancel'])

            if response == 'Replace':
                self.twBehaviors.setRowCount(0)

            if response == 'Cancel':
                return

        fd = QFileDialog(self)
        fileName, dummy = fd.getOpenFileName(self, 'Import behaviors configuration file', '', 'Text files (*.txt *.tsv);;All files (*)')

        if fileName:
            f = open(fileName, 'r')
            rows_utf8 = f.readlines()

            rows = [ row.decode('utf8') for row in rows_utf8]

            f.close()
            lineRow = 0
            
            self.configurationFileName = fileName
            
            for row in rows:
                lineRow += 1

                if self.DEBUG: print row

                if row.strip() and row.strip()[0] != '#':
                    if '\t' in row:
                        try:
                            sp = row.replace('\n','').split('\t')
                            print 'sp', sp

                            
                            if len(sp) == len(fields):   ### ethogram with excluded behaviours (6 fields)
                                row = {}
                                row['type'], row['key'], row['code'], row['description'], row['modifiers'], row['excluded'] = sp

                            ### backward compatibility
                            elif len(sp) == 5:   ### without excluded states
                                row = {}
                                row['type'], row['key'], row['code'], row['description'], row['modifiers'] = sp
                                row['excluded'] = ''

                            elif len(sp) != len(fields):
                                QMessageBox.warning(self, programName, 'Error in configuration file at line %d' % lineRow)
                                return

                        except:
                            QMessageBox.warning(self, programName, 'Error in configuration file at line %d' % lineRow)
                            return

                        self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)

                        for field in row:

                            item = QTableWidgetItem()

                            if field == 'type':

                                comboBox = QComboBox()
                                for observation in observation_types:
                                    comboBox.addItem(observation)
                                comboBox.setCurrentIndex( observation_types.index(row[field]) )

                                self.twBehaviors.setCellWidget(self.twBehaviors.rowCount() - 1, 0, comboBox)

                            else:
                                item.setText( row[field] )
                                
                                if field == 'excluded':
                                    item.setFlags(Qt.ItemIsEnabled)
                                    
                                self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, fields[field] ,item)

                            
                            '''
                            item = QTableWidgetItem(row[field])
                            ### if type editable = false
                            if field in ['excluded']:
                                item.setFlags(Qt.ItemIsEnabled)
                                
                            self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, fields[field] ,item)
                            '''

    def pbExportConfiguration_clicked(self):
        '''
        export configuration of observations
        '''
        fd = QFileDialog(self)

        fileName, filter = fd.getSaveFileName(self, 'Save configuration', '', 'Text files (*.txt *.tsv);;All files (*)')

        if fileName:
            f = open(fileName, 'w')
            f.write('### behaviors configuration file for use with %s\n\n' % programName)

            for r in range(0, self.twBehaviors.rowCount()):

                row = {}
                for field in fields:

                    if field == 'type':
                        combobox = self.twBehaviors.cellWidget(r,0)
                        if self.DEBUG: print 'combo', observation_types[combobox.currentIndex()]
                        
                        row[field] = observation_types[combobox.currentIndex()]
                    else:

                        if self.twBehaviors.item(r, fields[field]):
                            row[field] = self.twBehaviors.item(r, fields[field]).text()
                        else:
                            row[field] = ''

                if (row['type']) and (row['key']) and (row['code']):
                    print 'type', type(row['key'])

                    s = row['type'] + '\t' + row['key'] + '\t' +  row['code'] + '\t' +  row['description'] + '\t' +  row['modifiers'] + '\t' + row['excluded'] + '\n'

                    s2 = s.encode('UTF-8')

                    f.write(s2)

            f.close()

    ''' FIXME 2014-04-28 bug in import subjects from file
    def pbSaveSubjects_clicked(self):
        
        #export subjects to plain text file
        
        fd = QFileDialog(self)

        fileName, filter = fd.getSaveFileName(self, 'Export subjects configuration', '', 'Text files (*.txt *.tsv);;All files (*)')

        if fileName:
            f = open(fileName, 'w')
            f.write('### subjects configuration file for use with %s\n\n' % programName)

            for r in range(0, self.twSubjects.rowCount()):

                suject_key = self.twSubjects.item(r, 0).text()
                suject_name = self.twSubjects.item(r, 1).text()

                s = (suject_key + '\t' + suject_name + '\n').encode('utf-8')

                print s

                f.write(s)

            f.close()


    def pbLoadSubjects_clicked(self):

        #import subjects from file

        if self.twSubjects.rowCount():

            response = dialog.MessageDialog(programName, 'There are subjects already configured. Do you want to append subjects or replace them?', ['Append', 'Replace', 'Cancel'])

            if response == 'Replace':
                self.twSubjects.setRowCount(0)

            if response == 'Cancel':
                return

        fd = QFileDialog(self)
        fileName = fd.getOpenFileName(self, 'Import subjects configuration file', '', 'Text files (*.txt *.tsv);;All files (*)')[0]

        if fileName:
            f = open(fileName, 'r')
            rows_utf8 = f.readlines()

            rows = [ row.decode('utf8') for row in rows_utf8]

            f.close()
            lineRow = 0
            
            self.configurationFileName = fileName
            
            for row in rows:
                lineRow += 1

                if self.DEBUG: print row

                if row.strip() and row.strip()[0] != '#':
                    if '\t' in row:
                        try:
                            suject_key, subject_name = row.replace('\n','').split('\t')

                        except:
                            QMessageBox.warning(self, programName, 'Error in subjects configuration file at line %d' % lineRow)
                            return

                        self.twSubjects.setRowCount(self.twSubjects.rowCount() + 1)

                        item = QTableWidgetItem( subject_key )
                        self.twSubjects.setItem(self.twSubjects.rowCount() - 1, 0 , item)

                        item = QTableWidgetItem( suject_name )
                        self.twSubjects.setItem(self.twSubjects.rowCount() - 1, 1 , item)

    '''

    def twObservations_cellChanged(self, row, column):

        keys = []
        codes = []
        
        self.lbObservationsState.setText('')
        
        for r in range(0, self.twBehaviors.rowCount()):
            
            ### check key
            if self.twBehaviors.item(r, fields['key']):
                if self.twBehaviors.item(r, fields['key']).text().upper() not in ['F1','F2','F3','F4','F5','F6','F7','F8','F9','F10','F11','F12'] \
                   and  len(self.twBehaviors.item(r, fields['key']).text()) > 1:
                    self.lbObservationsState.setText('<font color="red">Key length &gt; 1</font>')
                    return
                
                keys.append(self.twBehaviors.item(r, fields['key']).text())
                
                ### convert to upper text
                
                self.twBehaviors.item(r, fields['key']).setText( self.twBehaviors.item(r, fields['key']).text().upper() )
                


            ### check code
            if self.twBehaviors.item(r, fields['code']):
                if self.twBehaviors.item(r, fields['code']).text() in codes:
                    self.lbObservationsState.setText('<font color="red">Code duplicated at line %d </font>' % (r + 1))
                else:
                    if self.twBehaviors.item(r, fields['code']).text():
                        codes.append(self.twBehaviors.item(r, fields['code']).text())

        if self.DEBUG: print keys

        ### check subjects for key duplication
        for r in range(0, self.twSubjects.rowCount()):
            if self.twSubjects.item(r, 1):

                if self.twSubjects.item(r, 1).text() in keys:
                    self.lbObservationsState.setText('<font color="red">Key found in subjects list at line %d </font>' % (r + 1))


    def pbClone_clicked(self):
        '''
        clone the selected configuration
        '''
        if not self.twBehaviors.selectedIndexes():
            QMessageBox.about(self, programName, 'First select an observation')
        else:
            self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)
            
            row = self.twBehaviors.selectedIndexes()[0].row()
            for field in fields:
                
                if field == 'type':
                    item = QTableWidgetItem( )
                    combobox = self.twBehaviors.cellWidget(row, 0)
                    index = combobox.currentIndex()
                    
                    newComboBox = QComboBox()
                    for observation in observation_types:
                        newComboBox.addItem(observation)
                    newComboBox.setCurrentIndex( index )
                    
                    self.twBehaviors.setCellWidget(self.twBehaviors.rowCount() - 1, 0, newComboBox)
                    
                else:
                    item = QTableWidgetItem( self.twBehaviors.item( row, fields[field] ))
                    self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, fields[field] ,item)
            
            '''self.twBehaviors.removeRow(self.twBehaviors.selectedIndexes()[0].row())'''


    def pbRemoveBehavior_clicked(self):
        
        
        if self.DEBUG: print 'remove behavior'

        if not self.twBehaviors.selectedIndexes():
            QMessageBox.warning(self, programName, 'First select a behaviour to remove')
        else:

            response = dialog.MessageDialog(programName, 'Remove the selected behavior?', ['Yes', 'Cancel'])
            if response == 'Yes':
                            
                ### check if behavior already used in observations
                
                codeToDelete = self.twBehaviors.item( self.twBehaviors.selectedIndexes()[0].row(), 2).text()

                codesInObs = []
                for obs in  self.pj['observations']:
                    events = self.pj['observations'][ obs ]['events']
                    for event in events:
                        codesInObs.append( event[2] )
                        
                if self.DEBUG: print 'all codes in observations',  codesInObs

                if codeToDelete in codesInObs:
                    response = dialog.MessageDialog(programName, 'The code to remove is used in observations!', ['Remove', 'Cancel'])
                    if response == 'Remove':
                        self.twBehaviors.removeRow(self.twBehaviors.selectedIndexes()[0].row())

                else:
                    ### code not used
                    self.twBehaviors.removeRow(self.twBehaviors.selectedIndexes()[0].row())


    def pbAddBehavior_clicked(self):
        '''
        add a behavior
        '''

        if self.DEBUG: print 'add behavior configuration'

        response = dialog.MessageDialog(programName, 'Choose a type of behavior', ['Cancel'] + observation_types)
        
        if response == 'Cancel':
            return

        self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)


        for field_type in fields:

            item = QTableWidgetItem()
            
            if field_type == 'type':

                ### add type combobox
                comboBox = QComboBox()

                for observation in observation_types:
                    comboBox.addItem(observation)
                comboBox.setCurrentIndex( observation_types.index(response) )

                self.twBehaviors.setCellWidget(self.twBehaviors.rowCount() - 1, 0, comboBox)
            else:
                self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, fields[field_type] , QTableWidgetItem(''))


    def pbAddSubject_clicked(self):
        '''
        add a subject
        '''

        if self.DEBUG: print 'add subject'

        self.twSubjects.setRowCount(self.twSubjects.rowCount() + 1)
        item = QTableWidgetItem('')
        self.twSubjects.setItem(self.twSubjects.rowCount() - 1, 0 ,item)

    def pbRemoveSubject_clicked(self):
        if not self.twSubjects.selectedIndexes():
            QMessageBox.warning(self, programName, 'First select a subject to remove')
        else:

            response = dialog.MessageDialog(programName, 'Remove the selected subject?', ['Yes', 'Cancel'])
            if response == 'Yes':

                subjectToDelete = self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row(), 1).text()  ### 1: subject name

                if self.DEBUG: print 'subject to delete', subjectToDelete

                subjectsInObs = []
                for obs in  self.pj['observations']:
                    events = self.pj['observations'][ obs ]['events']
                    for event in events:
                        subjectsInObs.append( event[ 1 ] )  ### 1: subject name
                        
                if self.DEBUG: print 'all subjects in observations',  subjectsInObs

                if subjectToDelete in subjectsInObs:
                    response = dialog.MessageDialog(programName, 'The subject to remove is used in observations!', ['Remove', 'Cancel'])
                    if response == 'Remove':
                        self.twSubjects.removeRow(self.twSubjects.selectedIndexes()[0].row())

                else:
                    ### code not used
                    self.twSubjects.removeRow(self.twSubjects.selectedIndexes()[0].row())


    def pbDown_behavior_clicked(self):
        '''
        move selected event up
        '''
        

        if self.twBehaviors.selectedIndexes() and self.twBehaviors.selectedIndexes()[0].row() < self.twBehaviors.rowCount() -1:
            selectedRow = self.twBehaviors.selectedIndexes()[0].row()
            subjectToMoveDown = [self.twBehaviors.cellWidget(selectedRow, 0).currentIndex()]
            subjectToMoveUp = [self.twBehaviors.cellWidget(selectedRow + 1, 0).currentIndex()]

            for x in range(1, 5+1):
                subjectToMoveDown.append( self.twBehaviors.item( selectedRow , x).text() )
                subjectToMoveUp.append( self.twBehaviors.item( selectedRow+1, x).text() )


            self.twBehaviors.cellWidget(selectedRow + 1, 0).setCurrentIndex( subjectToMoveDown[0] )
            self.twBehaviors.cellWidget(selectedRow , 0).setCurrentIndex( subjectToMoveUp[0] )
            for x in range(1, 5+1):
                self.twBehaviors.item( selectedRow + 1, x).setText(subjectToMoveDown[x])
                self.twBehaviors.item( selectedRow , x).setText(subjectToMoveUp[x])

            self.twBehaviors.selectRow(selectedRow + 1)




    def pbUp_clicked(self):
        '''
        move selected subject up
        '''

        if self.twSubjects.selectedIndexes() and self.twSubjects.selectedIndexes()[0].row() > 0:

            subjectToMoveUp = [ self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row(), 0).text() , self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row(), 1).text()]
            subjectToMoveDown = [ self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() - 1, 0).text() , self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() -1, 1).text()]

            self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() - 1, 0).setText(subjectToMoveUp[0])
            self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() - 1, 1).setText(subjectToMoveUp[1])

            self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() , 0).setText(subjectToMoveDown[0])
            self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() , 1).setText(subjectToMoveDown[1])
            
            self.twSubjects.selectRow(self.twSubjects.selectedIndexes()[0].row() - 1)

    def pbDown_clicked(self):
        '''
        move selected subject down
        '''

        if self.twSubjects.selectedIndexes() and self.twSubjects.selectedIndexes()[0].row() < self.twSubjects.rowCount() -1:

            subjectToMoveDown = [ self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() , 0).text() , self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() , 1).text()]
            subjectToMoveUp = [ self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() +1,  0).text() , self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row()+1, 1).text()]

            self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() + 1, 0).setText(subjectToMoveDown[0])
            self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() + 1, 1).setText(subjectToMoveDown[1])

            self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() , 0).setText(subjectToMoveUp[0])
            self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() , 1).setText(subjectToMoveUp[1])

            self.twSubjects.selectRow(self.twSubjects.selectedIndexes()[0].row() + 1)


    def twSubjects_cellChanged(self, row, column):
        '''
        check if subject not unique
        '''
        
        if self.DEBUG: print 'subject cell changed', row, column
        
        subjects = []
        keys = []
        
        self.lbSubjectsState.setText('')
        
        for r in range(0, self.twSubjects.rowCount()):
            
            ### check key
            if self.twSubjects.item(r, 0):
                
                ### check key length
                if self.twSubjects.item(r, 0).text().upper() not in ['F' + str(i) for i in range(1,13)] \
                   and  len(self.twSubjects.item(r, 0).text()) > 1:
                    self.lbSubjectsState.setText('<font color="red">Key length &gt; 1</font>')
                    return

                if self.twSubjects.item(r, 0).text() in keys:
                    self.lbSubjectsState.setText('<font color="red">Key duplicated at line %d </font>' % (r + 1))
                else:
                    if self.twSubjects.item(r, 0).text():
                        keys.append(self.twSubjects.item(r, 0).text())

                ### convert to upper text
                self.twSubjects.item(r, 0).setText( self.twSubjects.item(r, 0).text().upper() )


            ### check subject
            if self.twSubjects.item(r, 1):

                if self.twSubjects.item(r, 1).text() in subjects:
                    self.lbSubjectsState.setText('<font color="red">Subject duplicated at line %d </font>' % (r + 1))
                else:
                    if self.twSubjects.item(r, 1).text():
                        subjects.append(self.twSubjects.item(r, 1).text())


        ### check behaviours keys
        for r in range(0, self.twBehaviors.rowCount()):
            
            ### check key
            if self.twBehaviors.item(r, fields['key']):
                if self.twBehaviors.item(r, fields['key']).text() in keys:
                    self.lbSubjectsState.setText('<font color="red">Key found in behaviours configuration at line %d </font>' % (r + 1))


    def pbRemoveObservation_clicked(self):
        '''
        remove first selected observation
        '''
        
        if self.DEBUG:
            print 'remove observation'
            print 'self.pj', self.pj
        
        if not self.twObservations.selectedIndexes():
            QMessageBox.warning(self, programName, 'First select an observation to remove')
        else:

            response = dialog.MessageDialog(programName, 'Are you sure to remove the selected observation?', ['Yes', 'Cancel'])

            if response == 'Yes':
                
                obs_id = self.twObservations.item( self.twObservations.selectedIndexes()[0].row(), 0).text()
                
                if self.DEBUG: print 'obs to delete', obs_id
                del self.pj['observations'][ obs_id ]
                self.twObservations.removeRow(self.twObservations.selectedIndexes()[0].row())


    def pbOK_clicked(self):
        '''
        verify behaviours and subjects configuration
        '''

        if self.lbObservationsState.text():
            QMessageBox.warning(self, programName, self.lbObservationsState.text())
            return

        if self.lbSubjectsState.text():
            QMessageBox.warning(self, programName, self.lbSubjectsState.text())
            return


        ### store subjects
        self.subjects_conf = {}

        for row in range(0, self.twSubjects.rowCount()):
            
            ### check key
            if self.twSubjects.item(row, 0):
                key = self.twSubjects.item(row, 0).text()
            else:
                key = ''

            ### check subject name
            if self.twSubjects.item(row, 1):
                subjectName = self.twSubjects.item(row, 1).text()
                if '|' in subjectName:
                    QMessageBox.warning(self, programName, 'The pipe (|) character is not allowed in subject name <b>%s</b> !' % subjectName)
                    return

            else:
                QMessageBox.warning(self, programName, 'Missing subject name in subjects configuration at row %d !' % row)
                return

            self.subjects_conf[ len(self.subjects_conf) ] = { 'key': key, 'name': subjectName }


        ### store behaviors
        missing_data = []

        self.obs = {}

        for r in range(0, self.twBehaviors.rowCount()):

            row = {}
            for field in fields:

                if field == 'type':
                    combobox = self.twBehaviors.cellWidget(r,0)

                    if self.DEBUG: print 'combo', observation_types[combobox.currentIndex()]

                    row[field] = observation_types[combobox.currentIndex()]

                else:
                    if self.twBehaviors.item(r, fields[field]):

                        ### check for | char in code
                        if field == 'code' and '|' in self.twBehaviors.item(r, fields[field]).text():
                            QMessageBox.warning(self, programName, 'The pipe (|) character is not allowed in code <b>%s</b> !' % self.twBehaviors.item(r, fields[field]).text())
                            return

                        row[field] = self.twBehaviors.item(r, fields[field]).text()
                    else:
                        row[field] = ''

            if (row['type']) and (row['key']) and (row['code']):

                self.obs[ len(self.obs) ] = row

            else:

                missing_data.append(str(r + 1))

        if missing_data:
            QMessageBox.warning(self, programName, 'Missing data in behaviors configuration at row %s !' % (','.join(missing_data)))
            return


        ### check independent variables
        self.indVar = {}
        for r in range(0, self.twVariables.rowCount()):
            row = {}
            for idx, field in enumerate(tw_indVarFields):

                if field == 'type':

                    combobox = self.twVariables.cellWidget(r, idx)

                    if combobox.currentIndex() == 0:
                        row[field] = NUMERIC

                    if combobox.currentIndex() == 1:
                        row[field] = TEXT

                else:
                
                    if self.twVariables.item(r, idx):
                        row[field] = self.twVariables.item(r, idx).text()
                    else:
                        row[field] = ''

            self.indVar[ len(self.indVar) ] = row

        if self.DEBUG: print 'ind var', self.indVar
        self.accept()


    def pbCancel_clicked(self):
        self.reject()
