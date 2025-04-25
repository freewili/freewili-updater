# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QGridLayout, QGroupBox,
    QHeaderView, QLabel, QLineEdit, QPushButton,
    QSizePolicy, QTabWidget, QTextEdit, QToolButton,
    QTreeView, QWidget)
from . import main_rc

class Ui_FormMain(object):
    def setupUi(self, FormMain):
        if not FormMain.objectName():
            FormMain.setObjectName(u"FormMain")
        FormMain.resize(883, 558)
        self.gridLayout_5 = QGridLayout(FormMain)
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.groupBox = QGroupBox(FormMain)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_4 = QGridLayout(self.groupBox)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.pushButtonEnterUf2 = QPushButton(self.groupBox)
        self.pushButtonEnterUf2.setObjectName(u"pushButtonEnterUf2")

        self.gridLayout_4.addWidget(self.pushButtonEnterUf2, 3, 2, 1, 1)

        self.labelSpinner = QLabel(self.groupBox)
        self.labelSpinner.setObjectName(u"labelSpinner")
        self.labelSpinner.setMinimumSize(QSize(50, 50))
        self.labelSpinner.setMaximumSize(QSize(50, 50))

        self.gridLayout_4.addWidget(self.labelSpinner, 3, 1, 1, 1)

        self.pushButtonReflash = QPushButton(self.groupBox)
        self.pushButtonReflash.setObjectName(u"pushButtonReflash")

        self.gridLayout_4.addWidget(self.pushButtonReflash, 3, 0, 1, 1)

        self.tabWidget = QTabWidget(self.groupBox)
        self.tabWidget.setObjectName(u"tabWidget")
        self.tabFirmware = QWidget()
        self.tabFirmware.setObjectName(u"tabFirmware")
        self.gridLayout_6 = QGridLayout(self.tabFirmware)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.groupBoxFirmware = QGroupBox(self.tabFirmware)
        self.groupBoxFirmware.setObjectName(u"groupBoxFirmware")
        self.gridLayout = QGridLayout(self.groupBoxFirmware)
        self.gridLayout.setObjectName(u"gridLayout")
        self.groupBoxMainUf2 = QGroupBox(self.groupBoxFirmware)
        self.groupBoxMainUf2.setObjectName(u"groupBoxMainUf2")
        self.groupBoxMainUf2.setCheckable(True)
        self.gridLayout_2 = QGridLayout(self.groupBoxMainUf2)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.lineEditMainUf2 = QLineEdit(self.groupBoxMainUf2)
        self.lineEditMainUf2.setObjectName(u"lineEditMainUf2")

        self.gridLayout_2.addWidget(self.lineEditMainUf2, 0, 0, 1, 1)

        self.toolButtonMainUf2Browse = QToolButton(self.groupBoxMainUf2)
        self.toolButtonMainUf2Browse.setObjectName(u"toolButtonMainUf2Browse")

        self.gridLayout_2.addWidget(self.toolButtonMainUf2Browse, 0, 1, 1, 1)


        self.gridLayout.addWidget(self.groupBoxMainUf2, 0, 0, 1, 1)

        self.groupBoxDisplayUf2 = QGroupBox(self.groupBoxFirmware)
        self.groupBoxDisplayUf2.setObjectName(u"groupBoxDisplayUf2")
        self.groupBoxDisplayUf2.setCheckable(True)
        self.gridLayout_3 = QGridLayout(self.groupBoxDisplayUf2)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.lineEditDisplayUf2 = QLineEdit(self.groupBoxDisplayUf2)
        self.lineEditDisplayUf2.setObjectName(u"lineEditDisplayUf2")

        self.gridLayout_3.addWidget(self.lineEditDisplayUf2, 0, 0, 1, 1)

        self.toolButtonDisplayUf2Browse = QToolButton(self.groupBoxDisplayUf2)
        self.toolButtonDisplayUf2Browse.setObjectName(u"toolButtonDisplayUf2Browse")

        self.gridLayout_3.addWidget(self.toolButtonDisplayUf2Browse, 0, 1, 1, 1)


        self.gridLayout.addWidget(self.groupBoxDisplayUf2, 1, 0, 1, 1)


        self.gridLayout_6.addWidget(self.groupBoxFirmware, 0, 0, 1, 1)

        self.tabWidget.addTab(self.tabFirmware, "")
        self.tabLog = QWidget()
        self.tabLog.setObjectName(u"tabLog")
        self.gridLayout_7 = QGridLayout(self.tabLog)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.textEditLog = QTextEdit(self.tabLog)
        self.textEditLog.setObjectName(u"textEditLog")

        self.gridLayout_7.addWidget(self.textEditLog, 0, 0, 1, 1)

        self.pushButtonLogClear = QPushButton(self.tabLog)
        self.pushButtonLogClear.setObjectName(u"pushButtonLogClear")

        self.gridLayout_7.addWidget(self.pushButtonLogClear, 1, 0, 1, 1)

        self.tabWidget.addTab(self.tabLog, "")

        self.gridLayout_4.addWidget(self.tabWidget, 2, 0, 1, 3)

        self.pushButtonRefresh = QPushButton(self.groupBox)
        self.pushButtonRefresh.setObjectName(u"pushButtonRefresh")

        self.gridLayout_4.addWidget(self.pushButtonRefresh, 1, 0, 1, 3)

        self.treeViewDevices = QTreeView(self.groupBox)
        self.treeViewDevices.setObjectName(u"treeViewDevices")
        self.treeViewDevices.setStyleSheet(u"background-image: url(:/images/fw-logo.png);\n"
"background-position: center center;\n"
"background-repeat: no-repeat;\n"
"background-attachment:fixed;")
        self.treeViewDevices.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        self.gridLayout_4.addWidget(self.treeViewDevices, 0, 0, 1, 3)

        self.gridLayout_4.setRowStretch(0, 1)

        self.gridLayout_5.addWidget(self.groupBox, 0, 0, 1, 1)


        self.retranslateUi(FormMain)

        self.tabWidget.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(FormMain)
    # setupUi

    def retranslateUi(self, FormMain):
        FormMain.setWindowTitle(QCoreApplication.translate("FormMain", u"Free-Wili Firmware Updater", None))
        self.groupBox.setTitle(QCoreApplication.translate("FormMain", u"Devices", None))
        self.pushButtonEnterUf2.setText(QCoreApplication.translate("FormMain", u"&Enter UF2 on Selected", None))
        self.labelSpinner.setText("")
        self.pushButtonReflash.setText(QCoreApplication.translate("FormMain", u"&Reflash Selected", None))
        self.groupBoxFirmware.setTitle(QCoreApplication.translate("FormMain", u"Firmware", None))
        self.groupBoxMainUf2.setTitle(QCoreApplication.translate("FormMain", u"Main UF2", None))
        self.toolButtonMainUf2Browse.setText(QCoreApplication.translate("FormMain", u"...", None))
        self.groupBoxDisplayUf2.setTitle(QCoreApplication.translate("FormMain", u"Display UF2", None))
        self.toolButtonDisplayUf2Browse.setText(QCoreApplication.translate("FormMain", u"...", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabFirmware), QCoreApplication.translate("FormMain", u"Firmware", None))
        self.pushButtonLogClear.setText(QCoreApplication.translate("FormMain", u"&Clear", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabLog), QCoreApplication.translate("FormMain", u"Log", None))
        self.pushButtonRefresh.setText(QCoreApplication.translate("FormMain", u"&Refresh", None))
    # retranslateUi

