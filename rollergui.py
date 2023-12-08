
#!/usr/bin/env python

import re
import sys
from collections import ChainMap
import math
import dump_data
import io

from PyQt5.QtCore import Qt, QBuffer, QFile, QIODevice
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget,
        QTableWidgetItem, QItemDelegate, QLineEdit, QMenu,
        QAction, QFileDialog, QMessageBox, QInputDialog,QDialog
        )


cellre = re.compile(r'\b[A-Z][0-9]\b')

def cellname(i, j):
    return f'{chr(ord("A")+j)}{i+1}'

class SpreadSheetDelegate(QItemDelegate):
    def __init__(self, parent=None):
        super(SpreadSheetDelegate, self).__init__(parent)

    def createEditor(self, parent, styleOption, index):
        editor = QLineEdit(parent)
        editor.editingFinished.connect(self.commitAndCloseEditor)
        return editor

    def commitAndCloseEditor(self):
        editor = self.sender()
        self.commitData.emit(editor)
        self.closeEditor.emit(editor, QItemDelegate.NoHint)

    def setEditorData(self, editor, index):
        editor.setText(index.model().data(index, Qt.EditRole))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.text())
    

class SpreadSheetItem(QTableWidgetItem):
    def __init__(self, siblings):
        super(SpreadSheetItem, self).__init__()
        self.siblings = siblings
        self.value = 0
        self.deps = set()
        self.reqs = set()

    def formula(self):
        return super().data(Qt.DisplayRole)

    def data(self, role):
        if role == Qt.EditRole:
            return self.formula()
        if role == Qt.DisplayRole:
            return self.display()

        return super(SpreadSheetItem, self).data(role)

    def calculate(self):
        formula = self.formula()

        if formula is None:
            self.value = 0
            return
        if formula[0] != '=':
            try:
                self.value = eval(formula)
            except:
                self.value = formula
            return
        formula = formula.upper()
        currentreqs = set(cellre.findall(formula))

        name = cellname(self.row(), self.column())

        # Add this cell to the new requirement's dependents
        for r in currentreqs - self.reqs:
            self.siblings[r].deps.add(name)
        # Add remove this cell from dependents no longer referenced
        for r in self.reqs - currentreqs:
            self.siblings[r].deps.remove(name)

        # Look up the values of our required cells
        reqvalues = {r: self.siblings[r].value for r in currentreqs}
        # Build an environment with these values and basic math functions
        environment = ChainMap(math.__dict__, reqvalues)
        # Note that eval is DANGEROUS and should not be used in production
        if formula[0]=='=':
            try:
                self.value = eval(formula[1:], {}, environment)
            except:
                return (None,'Formula ERROR...', f'Cannot Calculate formula {formula}', QMessageBox.Ok)
                
                
        self.reqs = currentreqs
        return

    def propagate(self):
        for d in self.deps:
            self.siblings[d].calculate()
            self.siblings[d].propagate()

    def display(self):
        if self.calculate():
            print('error')
            # QMessageBox.critical(None,"Format Error", "you can't do that...",QMessageBox.Ok)
            return str(self.value)
        
        self.propagate()
        return str(self.value)


class SpreadSheet(QMainWindow):
    
    loadedProgram: dump_data.RollerProgram
    RollerFile: QBuffer
    currentFile: io.BufferedReader = None
    qf: QFile = None
        
    def _createMenuBar(self):
        menuBar = self.menuBar()
        
        # Creating menus using a QMenu object
        fileMenu = QMenu("&File", self)
        menuBar.addMenu(fileMenu)
        fileMenu.addAction(self.newAction)
        fileMenu.addAction(self.openAction)
        fileMenu.addAction(self.displayAction)
        fileMenu.addAction(self.saveAction)
        fileMenu.addAction(self.exitAction)
        
        # Creating menus using a title
        editMenu = menuBar.addMenu("&Edit")
        helpMenu = menuBar.addMenu("&Help")
        
    def _createActions(self):
        self.newAction = QAction(self)
        self.newAction.setText("&New")
        # Creating actions using the second constructor
        self.openAction = QAction("&Set file...", self)
        self.displayAction = QAction("&Display Program", self)
        self.saveAction = QAction("&Save", self)
        self.exitAction = QAction("&Exit", self)
        
    def _connectActions(self):
        self.newAction.triggered.connect(self.newFile)
        self.openAction.triggered.connect(self.openFile)
        self.displayAction.triggered.connect(self.displayProgram)
        self.exitAction.triggered.connect(self.close)
        
        
    def __init__(self, rows, cols, parent=None):
        super(SpreadSheet, self).__init__(parent)

        self.rows = rows
        self.cols = cols

        self.cells = {}
        self._createActions()
        self._createMenuBar()
        self.create_widgets()
        self._connectActions()
      

    def create_widgets(self):
        table = self.table = QTableWidget(self.rows, self.cols, self)

        # headers = [chr(ord('A') + j) for j in range(self.cols)]
        headers = ['Axis', 'Value']
        table.setHorizontalHeaderLabels(headers)

        table.setItemDelegate(SpreadSheetDelegate(self))

        for i in range(self.rows):
            for j in range(self.cols):
                cell = SpreadSheetItem(self.cells)
                self.cells[cellname(i, j)] = cell
                self.table.setItem(i, j, cell)

        self.setCentralWidget(table)
    
    def closeEvent(self,event):
        result = QMessageBox.question(self,
                      "Confirm Exit...",
                      "Are you sure you want to exit ?",
                      QMessageBox.Yes| QMessageBox.No)
        event.ignore()

        if result == QMessageBox.Yes:
            event.accept()
            if self.currentFile:
                self.currentFile.close()
        
    def newFile(self):
        pass
        
    def openFile(self):
        # print("open clicked")
        if self.currentFile:
            result = QMessageBox.question( self,
                                          'Switch Files...',
                                          'Do you want to discard Changes and open a new File?',
                                          QMessageBox.Yes| QMessageBox.No)
            
            if result == QMessageBox.No:
                return
            
        dialog= QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
        dialog.setNameFilter("Roller Programs (*.emi)")
        dialog.setViewMode(QFileDialog.ViewMode.Detail)
        for cell in self.cells:
            self.cells[cell].setData(Qt.DisplayRole, '0')
        self.setWindowTitle('')
        
        # self.qf = QFile('./roller/em0.emi')
        # self.qf.open(QIODevice.ReadOnly)
        # self.qf.seek(2000)
        # print(self.qf.read(2000))
        
        if dialog.exec():
            filenames = dialog.selectedFiles()
            f = filenames[0]
            # print(f)
            self.currentFile = open(f,'rb+')
            # print(self.currentFile.read(200))
        
        
    def displayProgram(self):
        # print('display clicked')
        if not self.currentFile:
            self.openFile()
        programList = dump_data.get_program_list(self.currentFile)
        chosen = QInputDialog()
        chosen.setOptions(QInputDialog.UseListViewForComboBoxItems)
        name, ok = chosen.getItem(self,"choose Program",'programs', programList,0, False)
        # for name in programList:
        #     # print(f'{name}: {programList[name]}')
        #     print(f'\n\n{dump_data.get_program(self.currentFile, programList[name])}\n')
        self.setWindowTitle(name)
        program = dump_data.get_program(self.currentFile, programList[name])
        print(f'\n\n{program}\n')
        for cell in self.cells:
            self.cells[cell].setData(Qt.DisplayRole, '0')
        # self.table.clear()
        row = 1
        for line in program.lines:
            # self.table.insertRow()
            self.table.selectRow(row)
            test = self.table.selectionModel().selection()
            self.cells['A' + str(row)].setData(Qt.DisplayRole,line[0].name)
            self.cells['B' + str(row)].setData(Qt.DisplayRole,str(line[1]))
            row = row + 1
        

if __name__ == '__main__':
    app = QApplication(sys.argv)
    sheet = SpreadSheet(50, 2)
    sheet.resize(520, 200)
    sheet.show()
    sys.exit(app.exec_())