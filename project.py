#!/usr/bin/env python

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2015 Olivier Friard

This file is part of BORIS.

  BORIS is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 3 of the License, or
  any later version.
  
  BORIS is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.
  
  You should have received a copy of the GNU General Public License
  along with this program; if not see <http://www.gnu.org/licenses/>.

"""


from config import *

from PySide.QtCore import *
from PySide.QtGui import *

from add_modifier import *

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


class projectDialog(QDialog, Ui_dlgProject):

    def __init__(self, debug, parent=None ):

        super(projectDialog, self).__init__(parent)
        self.setupUi(self)

        self.DEBUG = debug

        self.lbObservationsState.setText('')
        self.lbSubjectsState.setText('')
        
        self.twBehaviors.setSortingEnabled(False)
        self.twSubjects.setSortingEnabled(False)


        ### ethogram tab
        self.pbAddObservation.clicked.connect(self.pbAddBehavior_clicked)
        self.pbClone.clicked.connect(self.pbClone_clicked)
       
        self.pbRemoveBehavior.clicked.connect(self.pbRemoveBehavior_clicked)
        self.pbRemoveAllBehaviors.clicked.connect(self.pbRemoveAllBehaviors_clicked)

        self.pbExclusionMatrix.clicked.connect(self.pbExclusionMatrix_clicked)

        self.pbImportBehaviorsFromProject.clicked.connect(self.pbImportBehaviorsFromProject_clicked)

        self.pbImportFromJWatcher.clicked.connect(self.pbImportFromJWatcher_clicked)

        self.twBehaviors.cellChanged[int, int].connect(self.twObservations_cellChanged)
        self.twBehaviors.cellDoubleClicked[int, int].connect(self.twObservations_cellDoubleClicked)

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


    def twObservations_cellDoubleClicked(self, row, column):
        if self.DEBUG: print( 'clicked row and column', row, column)
        
        ### check if double click on coding map
        if column == behavioursFields['coding map']:
            self.comboBoxChanged(row)

        if column == behavioursFields['modifiers']:
            
            ### check if behavior has coding map
            if self.twBehaviors.item(row, behavioursFields['coding map'] ).text():
                QMessageBox.warning(self, programName, 'Use the coding map to set/modify the areas')
            else:
                addModifierWindow = addModifierDialog(self.DEBUG, self.twBehaviors.item(row, column).text())
                addModifierWindow.setWindowTitle('Set modifiers')
                if addModifierWindow.exec_():
                    self.twBehaviors.item(row, column).setText( addModifierWindow.getModifiers() )



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

            for x in range(1, len(fields)):
                subjectToMoveUp.append( self.twBehaviors.item( selectedRow , x).text() )
                subjectToMoveDown.append( self.twBehaviors.item( selectedRow - 1, x).text() )

            self.twBehaviors.cellWidget(selectedRow , 0).setCurrentIndex( subjectToMoveDown[0] )
            self.twBehaviors.cellWidget(selectedRow - 1, 0).setCurrentIndex( subjectToMoveUp[0] )

            for x in range(1, len(fields)):
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
            if self.DEBUG: print project[SUBJECTS]

            ### configuration of behaviours
            if project[SUBJECTS]:

                if self.twSubjects.rowCount():
        
                    response = dialog.MessageDialog(programName, 'There are subjects already configured. Do you want to append subjects or replace them?', ['Append', 'Replace', 'Cancel'])
        
                    if response == 'Replace':
                        self.twSubjects.setRowCount(0)
        
                    if response == 'Cancel':
                        return


                for idx in sorted( project[SUBJECTS].keys() ):

                    self.twSubjects.setRowCount(self.twSubjects.rowCount() + 1)

                    for idx2, sbjField in enumerate(subjectsFields):

                        if sbjField in project[SUBJECTS][idx]:
                            self.twSubjects.setItem(self.twSubjects.rowCount() - 1, idx2 , QTableWidgetItem( project[SUBJECTS][idx][ sbjField ] ))
                        else:
                            self.twSubjects.setItem(self.twSubjects.rowCount() - 1, idx2 , QTableWidgetItem( '' ))

                    '''
                    subject_key = project[SUBJECTS][idx]['key']
                    subject_name = project[SUBJECTS][idx]['name']


                    item = QTableWidgetItem( subject_key )
                    self.twSubjects.setItem(self.twSubjects.rowCount() - 1, 0 , item)

                    item = QTableWidgetItem( subject_name )
                    self.twSubjects.setItem(self.twSubjects.rowCount() - 1, 1 , item)
                    '''


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
                            comboBox.addItems(observation_types)
                            comboBox.setCurrentIndex( observation_types.index(project['behaviors_conf'][i][field]) )

                            self.twBehaviors.setCellWidget(self.twBehaviors.rowCount() - 1, fields[field], comboBox)

                        else:
                            item.setText( project['behaviors_conf'][i][field] )
                            
                            if field in ['excluded','coding map']:
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
                        item.setFlags(Qt.ItemIsEnabled)
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


    def pbImportFromJWatcher_clicked(self):
        '''
        import behaviors configuration from JWatcher (GDL file)
        '''
        if self.twBehaviors.rowCount():

            response = dialog.MessageDialog(programName, 'There are behaviors already configured. Do you want to append behaviors or replace them?', ['Append', 'Replace', 'Cancel'])

            if response == 'Replace':
                self.twBehaviors.setRowCount(0)

            if response == 'Cancel':
                return

        fd = QFileDialog(self)
        fileName, dummy = fd.getOpenFileName(self, 'Import behaviors from JWatcher', '', 'Global Definition File (*.gdf);;All files (*)')

        if fileName:
            f = open(fileName, 'r')
            rows_utf8 = f.readlines()
            f.close()

            rows = [ row.decode('utf8') for row in rows_utf8]

            lineRow = 0

            for idx, row in enumerate(rows):
                if row and row[0] == '#':
                    continue

                if 'Behavior.name.' in row and '=' in row:
                    key, code = row.split('=')
                    key = key.replace('Behavior.name.','')
                    ### read description
                    if idx < len(rows) and 'Behavior.description.' in rows[idx+1]:
                        description = rows[idx+1].split('=')[-1]

                    behavior = {'key': key, 'code': code, 'description': description, 'modifiers': '', 'excluded':'', 'coding map':''}

                    self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)

                    signalMapper = QSignalMapper(self)
            
                    for field_type in behavioursFields:
            
                        if field_type == 'type':
            
                            ### add type combobox
                            comboBox = QComboBox()
                            comboBox.addItems( observation_types )
                            comboBox.setCurrentIndex(  0  )   ### event type from jwatcher not known
        
                            signalMapper.setMapping(comboBox, self.twBehaviors.rowCount() - 1)
                            comboBox.currentIndexChanged['int'].connect(signalMapper.map)
                    
                            self.twBehaviors.setCellWidget(self.twBehaviors.rowCount() - 1, behavioursFields[field_type], comboBox)

                        else:
                            item = QTableWidgetItem( behavior[field_type] )
    
                            if field_type in ['excluded', 'coding map', 'modifiers']:
                                item.setFlags(Qt.ItemIsEnabled)

                            self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, behavioursFields[field_type] , item)
        
                    signalMapper.mapped['int'].connect(self.comboBoxChanged)




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


    def twObservations_cellChanged(self, row, column):
        
        if self.DEBUG: print 'twObservations cell changed'

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

        if self.DEBUG: print 'keys', keys

        ### check subjects for key duplication
        for r in range(0, self.twSubjects.rowCount()):
            if self.twSubjects.item(r, fields['key']):

                if self.twSubjects.item(r, fields['key']).text() in keys:
                    self.lbObservationsState.setText('<font color="red">Key found in subjects list at line %d </font>' % (r + 1))
        if self.DEBUG: print 'end tw changed'


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
                    newComboBox.addItems(observation_types)
                    newComboBox.setCurrentIndex( index )
                    
                    self.twBehaviors.setCellWidget(self.twBehaviors.rowCount() - 1, 0, newComboBox)
                    
                else:
                    item = QTableWidgetItem( self.twBehaviors.item( row, fields[field] ))
                    self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, fields[field] ,item)
            


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

        '''
        dlg = dialog.EventType()
        if dlg.exec_():

            ### retrieve event type
            if dlg.rbStateEvent.isChecked():
                response = 'State event'
            elif dlg.rbPointEvent.isChecked():
                response = 'Point event'
            else:
                return
        '''

        response = 'Point event'

        '''
        ### retrieve is coding map is associated
        if dlg.cbCodingMap.isChecked():
            response += ' with coding map'

            ### let user select a coding maop
            fd = QFileDialog(self)
            fileName, dummy = fd.getOpenFileName(self, 'Select a coding map for the event', '', 'BORIS map files (*.boris_map);;All files (*)')
    
            if fileName:
                import json
                new_map = json.loads( open(fileName, 'r').read() )
                self.pj['coding_map'][ new_map['name'] ] = new_map
            else:
                return
        '''

        ### Add behavior to table
        self.twBehaviors.setRowCount(self.twBehaviors.rowCount() + 1)

        signalMapper = QSignalMapper(self)

        for field_type in fields:

            item = QTableWidgetItem()

            if field_type == 'type':

                ### add type combobox
                comboBox = QComboBox()
                comboBox.addItems( observation_types )
                comboBox.setCurrentIndex( observation_types.index( response ) )

                signalMapper.setMapping(comboBox, self.twBehaviors.rowCount() - 1)
                comboBox.currentIndexChanged['int'].connect(signalMapper.map)


                self.twBehaviors.setCellWidget(self.twBehaviors.rowCount() - 1, fields[field_type], comboBox)
            else:

                if field_type in ['excluded', 'coding map', 'modifiers']:
                    item.setFlags(Qt.ItemIsEnabled)

                '''
                if field_type == 'coding map' and dlg.cbCodingMap.isChecked():
                    item.setText(new_map['name'])
                '''
                self.twBehaviors.setItem(self.twBehaviors.rowCount() - 1, fields[field_type] , item)

        signalMapper.mapped['int'].connect(self.comboBoxChanged)


    def comboBoxChanged(self, row):
        '''
        event type combobox changed
        '''
        
        if self.DEBUG: print( 'combo box changed', row)
        
        combobox = self.twBehaviors.cellWidget(row, fields['type'])

        if 'with coding map' in observation_types[combobox.currentIndex()]:
            ### let user select a coding maop
            fd = QFileDialog(self)
            fileName, dummy = fd.getOpenFileName(self, 'Select a coding map for %s behavior' % self.twBehaviors.item(row, behavioursFields['code']).text(), '', 'BORIS map files (*.boris_map);;All files (*)')

            if fileName:
                import json
                new_map = json.loads( open(fileName, 'r').read() )

                if self.DEBUG: print 'new_map', new_map['name']

                self.pj['coding_map'][ new_map['name'] ] = new_map
                
                ### add modifiers from coding map codes
                modifStr = '|'.join(  sorted(new_map['areas'].keys()) )

                self.twBehaviors.item(row, behavioursFields['modifiers']).setText( modifStr )

                self.twBehaviors.item(row, behavioursFields['coding map']).setText( new_map['name'] )

            else:

                ### if coding map already exists do not rest the behavior type if no filename selected
                if not self.twBehaviors.item(row, behavioursFields['coding map']).text():
                    QMessageBox.critical(self, programName,  'No coding map was selected.\nEvent type will be reset to "Point event"' )
                    self.twBehaviors.cellWidget(row, fields['type']).setCurrentIndex(0)
        else:
            self.twBehaviors.item(row, behavioursFields['modifiers']).setText( '')
            self.twBehaviors.item(row, behavioursFields['coding map']).setText( '')


    def pbAddSubject_clicked(self):
        '''
        add a subject
        '''

        if self.DEBUG: print 'add subject'

        self.twSubjects.setRowCount(self.twSubjects.rowCount() + 1)
        item = QTableWidgetItem('')
        self.twSubjects.setItem(self.twSubjects.rowCount() - 1, 0 ,item)


    def pbRemoveSubject_clicked(self):
        '''
        remove selected subject from subjects list
        control before if subject used in observations
        '''
        if not self.twSubjects.selectedIndexes():
            QMessageBox.warning(self, programName, 'First select a subject to remove')
        else:

            response = dialog.MessageDialog(programName, 'Remove the selected subject?', ['Yes', 'Cancel'])
            if response == 'Yes':

                flagDel = False
                if  self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row(), 1):
                    subjectToDelete = self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row(), 1).text()  ### 1: subject name
    
                    if self.DEBUG: print('subject to delete', subjectToDelete)
    
                    subjectsInObs = []
                    for obs in  self.pj['observations']:
                        events = self.pj['observations'][ obs ]['events']
                        for event in events:
                            subjectsInObs.append( event[ 1 ] )  ### 1: subject name
                            
                    if self.DEBUG: print('all subjects in observations',  subjectsInObs)
    
                    if subjectToDelete in subjectsInObs:
                        response = dialog.MessageDialog(programName, 'The subject to remove is used in observations!', ['Remove', 'Cancel'])
                        if response == 'Remove':
                            flagDel = True
                    else:
                        ### code not used
                        flagDel = True

                else:
                    flagDel = True

                if flagDel:
                    self.twSubjects.removeRow(self.twSubjects.selectedIndexes()[0].row())



    def pbDown_behavior_clicked(self):
        '''
        move selected event up
        '''

        if self.twBehaviors.selectedIndexes() and self.twBehaviors.selectedIndexes()[0].row() < self.twBehaviors.rowCount() -1:
            selectedRow = self.twBehaviors.selectedIndexes()[0].row()
            subjectToMoveDown = [self.twBehaviors.cellWidget(selectedRow, 0).currentIndex()]
            subjectToMoveUp = [self.twBehaviors.cellWidget(selectedRow + 1, 0).currentIndex()]

            for x in range(1, len(fields)):
                subjectToMoveDown.append( self.twBehaviors.item( selectedRow , x).text() )
                subjectToMoveUp.append( self.twBehaviors.item( selectedRow+1, x).text() )


            self.twBehaviors.cellWidget(selectedRow + 1, 0).setCurrentIndex( subjectToMoveDown[0] )
            self.twBehaviors.cellWidget(selectedRow , 0).setCurrentIndex( subjectToMoveUp[0] )
            for x in range(1, len(fields)):
                self.twBehaviors.item( selectedRow + 1, x).setText(subjectToMoveDown[x])
                self.twBehaviors.item( selectedRow , x).setText(subjectToMoveUp[x])

            self.twBehaviors.selectRow(selectedRow + 1)


    def pbUp_clicked(self):
        '''
        move selected subject up
        '''

        if self.twSubjects.selectedIndexes() and self.twSubjects.selectedIndexes()[0].row() > 0:

            subjectToMoveUp = []
            subjectToMoveDown = []
            for idx, field in enumerate(subjectsFields):
                subjectToMoveUp.append(self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row(), idx).text()) 
                subjectToMoveDown.append( self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() - 1, idx).text() )

            '''
            self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() - 1, 0).setText(subjectToMoveUp[0])
            self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() - 1, 1).setText(subjectToMoveUp[1])
            self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() - 1, 2).setText(subjectToMoveUp[2])


            self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() , 0).setText(subjectToMoveDown[0])
            self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() , 1).setText(subjectToMoveDown[1])
            self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() , 2).setText(subjectToMoveDown[2])
            '''

            for idx, field in enumerate(subjectsFields):
                self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() - 1, idx).setText(subjectToMoveUp[idx])

            for idx, field in enumerate(subjectsFields):
                self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() , idx).setText(subjectToMoveDown[idx])

            self.twSubjects.selectRow(self.twSubjects.selectedIndexes()[0].row() - 1)


    def pbDown_clicked(self):
        '''
        move selected subject down
        '''

        if self.twSubjects.selectedIndexes() and self.twSubjects.selectedIndexes()[0].row() < self.twSubjects.rowCount() -1:

            subjectToMoveDown = []
            subjectToMoveUp = []
            for idx, field in enumerate(subjectsFields):
                subjectToMoveDown.append( self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() , idx).text() )
                subjectToMoveUp.append( self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() +1,  idx).text() ) 
            '''
            subjectToMoveDown = [ self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() , 0).text() , self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() , 1).text()]
            subjectToMoveUp = [ self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() +1,  0).text() , self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row()+1, 1).text()]
            '''

            for idx, field in enumerate(subjectsFields):
                self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() + 1, idx).setText(subjectToMoveDown[idx])

            for idx, field in enumerate(subjectsFields):
                self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() , idx).setText(subjectToMoveUp[idx])

            '''
            self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() + 1, 0).setText(subjectToMoveDown[0])
            self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() + 1, 1).setText(subjectToMoveDown[1])

            self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() , 0).setText(subjectToMoveUp[0])
            self.twSubjects.item( self.twSubjects.selectedIndexes()[0].row() , 1).setText(subjectToMoveUp[1])
            '''

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

            ### description
            if self.twSubjects.item(row, 2):
                subjectDescription = self.twSubjects.item(row, 2).text()
            else:
                subjectDescription = ''


            self.subjects_conf[ len(self.subjects_conf) ] = { 'key': key, 'name': subjectName, 'description': subjectDescription }


        ### store behaviors
        missing_data = []

        self.obs = {}

        ### coding maps names loaded in pj
        loadedCodingMaps = self.pj['coding_map'].keys()
        if self.DEBUG: print 'loadedCodingMaps', loadedCodingMaps

        for r in range(0, self.twBehaviors.rowCount()):

            row = {}
            for field in fields:

                if field == 'type':
                    combobox = self.twBehaviors.cellWidget(r, fields['type'])
                    if self.DEBUG: print 'combo', observation_types[combobox.currentIndex()]
                    row[field] = observation_types[combobox.currentIndex()]

                else:

                    if self.twBehaviors.item(r, behavioursFields[field]):

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

            ### remove coding map present in ethogram from coding maps names loaded in pj
            if self.twBehaviors.item(r, behavioursFields['coding map']).text():
                if self.twBehaviors.item(r, behavioursFields['coding map']).text() in loadedCodingMaps:
                    loadedCodingMaps.remove( self.twBehaviors.item(r, behavioursFields['coding map']).text() )


        if missing_data:
            QMessageBox.warning(self, programName, 'Missing data in behaviors configuration at row %s !' % (','.join(missing_data)))
            return

        ### delete coding maps loaded in pj and not cited in ethogram
        for loadedCodingMap in loadedCodingMaps:
            del self.pj['coding_map'][ loadedCodingMap ]


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
