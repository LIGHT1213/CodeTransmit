﻿'''
@Author: your name
@Date: 2020-03-13 09:44:52
@LastEditTime: 2020-03-16 15:21:40
@LastEditors: Please set LastEditors
@Description: In User Settings Edit
@FilePath: \codeTransmit\mainwindow.py
'''
# This Python file uses the following encoding: utf-8
import sys, os
from PySide2.QtWidgets import QApplication, QMainWindow, QFileDialog, QCheckBox, QMessageBox, QTableWidgetItem
from PySide2.QtCore import Qt, QThread
from uiWindow import Ui_MainWindow

import codecs 
import chardet 
import threading

#转换后的编码类型
UTF8_BOM = 0
UTF8 = 1
GB2312 = 2
JIS = 3

FILE = 0
FOLDER = 1

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.initForm()
        self.connectSlots()

        self.__path = None                                  #处理的文件/文件夹路径
        self.__fileSuffix = ['.c', '.h', '.cpp', '.hpp']    #内置可勾选的文件类型
        self.__customFileSuffix = []                        #自定义的文件类型
        self.__encodeType = 'UTF-8-SIG'                     #默认的编码类型
        self.__encodeTypeArr = ['UTF-8-SIG', 'utf-8', 'GB2312' ,'shift-jis']
        self.__fileOrFolder = FOLDER                        #默认处理文件夹
        self.__mWorker = None                               #私有线程变量

    def initForm(self):
        self.ui.tableWidget.setColumnCount(2)
        self.ui.tableWidget.setHorizontalHeaderLabels(["文件名","转换前类型"])
        self.ui.tableWidget.horizontalHeader().setStretchLastSection(True)
        self.ui.tableWidget.setColumnWidth(0, 165)
        self.ui.tableWidget.setColumnWidth(1, 70)

    def setFilePath(self, path):
        self.__path = path

    def getFileSuffix(self):
        return self.__fileSuffix

    def addFileSuffix(self, item):
        self.__fileSuffix.append(item)

    def removeFileSuffix(self, item):
        self.__fileSuffix.remove(item)
    
    def clearFileSuffix(self):
        self.__fileSuffix.clear()

    def setEncodeType(self, type):
        self.__encodeType = type

    def connectSlots(self):
        self.ui.btnChooseFolder.clicked.connect(self.onOpenFolderClicked)
        self.ui.btnChooseFile.clicked.connect(self.onOpenFileClicked)
        self.ui.btnClear.clicked.connect(self.onBtnClearClicked)
        self.ui.comboBox.currentIndexChanged.connect(self.onCbEncodeIndexChanged)
        self.ui.btnCustomCheck.clicked.connect(self.onCustomEncodeCheck)
        fileTypeArr = self.ui.groupBox.findChildren(QCheckBox)
        for index, item in enumerate(fileTypeArr):
            item.stateChanged.connect(self.onFileTypeChanged)
        self.ui.btnTransmit.clicked.connect(self.onTransmitClicked)

    def onOpenFileClicked(self):
        fileName = QFileDialog.getOpenFileName(self, "", ".")
        if (fileName is None):
            self.ui.textBrowser.append("open file failed: fileName is None!")
            return

        self.setFilePath(fileName[0])
        self.__fileOrFolder = FILE
        self.ui.labelPath.setText(fileName[0])

    def onOpenFolderClicked(self):
        folderName = QFileDialog.getExistingDirectory(self, "", ".")
        if (folderName is None):
            self.ui.textBrowser.append("open folder failed:folderName is None!")
            return
        
        self.setFilePath(folderName)
        self.__fileOrFolder = FOLDER
        self.ui.labelPath.setText(folderName)

    def onBtnClearClicked(self):
        self.ui.textBrowser.clear()
        self.ui.tableWidget.clearContents()
        self.ui.tableWidget.setRowCount(0)

    def onCbEncodeIndexChanged(self, index):
        self.setEncodeType(self.__encodeTypeArr[index])
        self.ui.textBrowser.append("Set encodeType: %s" % self.__encodeTypeArr[index])
    
    def onCustomEncodeCheck(self):
        customStr = self.ui.leditCustomEncode.text()
        customArr = customStr.split(' ')

        for index, item in enumerate(customArr):
            if(len(item) < 2):
                QMessageBox.critical(self, "Error!", "自定义后缀无效:长度至少为2!")
                return
            if(item[0] != '.'):
                QMessageBox.critical(self, "Error!", "自定义后缀无效:必须以 '.' 打头!")
                return
            if(item.count('.',) > 1):
                QMessageBox.critical(self, "Error!", "自定义后缀无效:一种格式中不能出现多个 '.'!")
                return
            #移除后缀重复的元素
            if (item not in self.__fileSuffix) and (item not in self.__customFileSuffix):
                self.__customFileSuffix.append(item)
    
    def onFileTypeChanged(self, state):
        checkBox = QCheckBox.sender(self)
        itemText = checkBox.text()
        if(False == state):
            if itemText in self.__fileSuffix:
                self.removeFileSuffix(itemText)
        else:
            if itemText not in self.__fileSuffix:
                self.addFileSuffix(itemText)
            if itemText in self.__customFileSuffix:
                self.__customFileSuffix.remove(itemText)

    def enableWidgets(self, enabled):
        self.ui.groupBoxPath.setEnabled(enabled)
        self.ui.groupBoxEncode.setEnabled(enabled)
        self.ui.btnTransmit.setEnabled(enabled)
        self.ui.btnClear.setEnabled(enabled)

    def onTransmitClicked(self):
        if self.__path is None:
            QMessageBox.warning(self, "Warning!", "请先选择'文件'或'文件夹'路径!")
            return

        self.ui.tableWidget.clearContents()
        self.ui.tableWidget.setRowCount(0)

        if self.__fileOrFolder == FILE:
            self.convert(self.__path, self.__encodeType)
        elif self.__fileOrFolder == FOLDER:
            if 0 == len(self.__fileSuffix) and 0 == len(self.__customFileSuffix):
                QMessageBox.critical(self, "Error!", "请设置需要处理的文件后缀格式!")
                return
            self.enableWidgets(False)
            self.__mWorker = threading.Thread(target=self.explore, args=(self.__path,))
            self.__mWorker.start()
        else:
            QMessageBox.critical(self, "Error!", "文件类型错误，无法转换!")
        QApplication.processEvents()

    def explore(self, dir):
        for root, dirs, files in os.walk(dir):
            for file in files:
                suffix = os.path.splitext(file)[1]
                # if suffix == '.h' or suffix == '.c' or suffix == '.cpp' or suffix == '.hpp' or suffix == '.bat': 
                #     path = os.path.join(root,file)
                #     self.convert(path)
                if self.__fileSuffix:
                    for item in self.__fileSuffix:
                        if(item == suffix):
                            path = os.path.join(root,file)
                            self.convert(path, self.__encodeType)
                if self.__customFileSuffix:
                    for item in self.__customFileSuffix:
                        if(item == suffix):
                            path = os.path.join(root,file)
                            self.convert(path, self.__encodeType)

        self.ui.textBrowser.append("explore over!")
        self.enableWidgets(True)

    def convert(self, filePath, out_enc="UTF-8-SIG"):
        try: 
            content = codecs.open(filePath,'rb').read()
            source_encoding = chardet.detect(content)['encoding']

            if source_encoding != None:
                if source_encoding == out_enc:
                    # self.ui.textBrowser.append("此文件格式无需转换: %s" % filePath)
                    return
                
                rouCount = self.ui.tableWidget.rowCount()
                self.ui.tableWidget.insertRow(rouCount)
                self.ui.tableWidget.setItem(rouCount, 0, QTableWidgetItem(filePath.split('\\')[-1]))
                self.ui.tableWidget.setItem(rouCount, 1, QTableWidgetItem(source_encoding))
                self.ui.tableWidget.item(rouCount, 0).setTextAlignment(Qt.AlignCenter)
                self.ui.tableWidget.item(rouCount, 1).setTextAlignment(Qt.AlignCenter)

                content = content.decode(source_encoding).encode(out_enc)
                codecs.open(filePath,'wb').write(content)
            else :
                self.ui.textBrowser.append("此文件无法识别编码: %s" % filePath)
        except Exception as err: 
            self.ui.textBrowser.append("%s:%s"%(filePath, err))
    

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
