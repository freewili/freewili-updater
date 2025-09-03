# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
##
## Created by: Qt User Interface Compiler version 6.9.2
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
    QSizePolicy, QTextEdit, QToolButton, QTreeView,
    QVBoxLayout, QWidget)
import main_rc

class Ui_FormMain(object):
    def setupUi(self, FormMain):
        if not FormMain.objectName():
            FormMain.setObjectName(u"FormMain")
        FormMain.resize(883, 558)
        self.gridLayout = QGridLayout(FormMain)
        self.gridLayout.setObjectName(u"gridLayout")
        self.groupBox = QGroupBox(FormMain)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_4 = QGridLayout(self.groupBox)
        self.gridLayout_4.setObjectName(u"gridLayout_4")
        self.treeViewDevices = QTreeView(self.groupBox)
        self.treeViewDevices.setObjectName(u"treeViewDevices")
        self.treeViewDevices.setStyleSheet(u"QTreeView {\n"
"    background-image: url(:/images/fw-logo.png);\n"
"    background-position: center center;\n"
"    background-repeat: no-repeat;\n"
"    background-attachment: fixed;\n"
"}\n"
"QTreeView::header {\n"
"    background-image: none;\n"
"}")
        self.treeViewDevices.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        self.gridLayout_4.addWidget(self.treeViewDevices, 0, 0, 1, 2)

        self.gridLayout_5 = QGridLayout()
        self.gridLayout_5.setObjectName(u"gridLayout_5")
        self.pushButtonReflash = QPushButton(self.groupBox)
        self.pushButtonReflash.setObjectName(u"pushButtonReflash")

        self.gridLayout_5.addWidget(self.pushButtonReflash, 2, 1, 1, 1)

        self.pushButtonRefresh = QPushButton(self.groupBox)
        self.pushButtonRefresh.setObjectName(u"pushButtonRefresh")

        self.gridLayout_5.addWidget(self.pushButtonRefresh, 2, 0, 1, 1)


        self.gridLayout_4.addLayout(self.gridLayout_5, 2, 0, 1, 1)

        self.groupBoxFirmware = QGroupBox(self.groupBox)
        self.groupBoxFirmware.setObjectName(u"groupBoxFirmware")
        self.verticalLayout = QVBoxLayout(self.groupBoxFirmware)
        self.verticalLayout.setObjectName(u"verticalLayout")
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


        self.verticalLayout.addWidget(self.groupBoxMainUf2)

        self.groupBoxDisplayUf2 = QGroupBox(self.groupBoxFirmware)
        self.groupBoxDisplayUf2.setObjectName(u"groupBoxDisplayUf2")
        self.groupBoxDisplayUf2.setCheckable(True)
        self.gridLayout_3 = QGridLayout(self.groupBoxDisplayUf2)
        self.gridLayout_3.setObjectName(u"gridLayout_3")
        self.toolButtonDisplayUf2Browse = QToolButton(self.groupBoxDisplayUf2)
        self.toolButtonDisplayUf2Browse.setObjectName(u"toolButtonDisplayUf2Browse")

        self.gridLayout_3.addWidget(self.toolButtonDisplayUf2Browse, 0, 1, 1, 1)

        self.lineEditDisplayUf2 = QLineEdit(self.groupBoxDisplayUf2)
        self.lineEditDisplayUf2.setObjectName(u"lineEditDisplayUf2")

        self.gridLayout_3.addWidget(self.lineEditDisplayUf2, 0, 0, 1, 1)


        self.verticalLayout.addWidget(self.groupBoxDisplayUf2)


        self.gridLayout_4.addWidget(self.groupBoxFirmware, 1, 0, 1, 2)

        self.labelSpinner = QLabel(self.groupBox)
        self.labelSpinner.setObjectName(u"labelSpinner")
        self.labelSpinner.setMinimumSize(QSize(50, 50))
        self.labelSpinner.setMaximumSize(QSize(50, 50))

        self.gridLayout_4.addWidget(self.labelSpinner, 2, 1, 1, 1)


        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)

        self.groupBoxDetails = QGroupBox(FormMain)
        self.groupBoxDetails.setObjectName(u"groupBoxDetails")
        self.gridLayout_7 = QGridLayout(self.groupBoxDetails)
        self.gridLayout_7.setObjectName(u"gridLayout_7")
        self.labelDetails = QLabel(self.groupBoxDetails)
        self.labelDetails.setObjectName(u"labelDetails")
        self.labelDetails.setMinimumSize(QSize(200, 200))

        self.gridLayout_7.addWidget(self.labelDetails, 0, 0, 1, 1)

        self.groupBoxConsole = QGroupBox(self.groupBoxDetails)
        self.groupBoxConsole.setObjectName(u"groupBoxConsole")
        self.gridLayout_6 = QGridLayout(self.groupBoxConsole)
        self.gridLayout_6.setObjectName(u"gridLayout_6")
        self.textEditLog = QTextEdit(self.groupBoxConsole)
        self.textEditLog.setObjectName(u"textEditLog")

        self.gridLayout_6.addWidget(self.textEditLog, 0, 0, 1, 1)

        self.pushButtonLogClear = QPushButton(self.groupBoxConsole)
        self.pushButtonLogClear.setObjectName(u"pushButtonLogClear")

        self.gridLayout_6.addWidget(self.pushButtonLogClear, 1, 0, 1, 1)


        self.gridLayout_7.addWidget(self.groupBoxConsole, 1, 0, 1, 1)


        self.gridLayout.addWidget(self.groupBoxDetails, 0, 1, 1, 1)

        self.gridLayout.setColumnStretch(0, 2)
        self.gridLayout.setColumnStretch(1, 1)

        self.retranslateUi(FormMain)

        QMetaObject.connectSlotsByName(FormMain)
    # setupUi

    def retranslateUi(self, FormMain):
        FormMain.setWindowTitle(QCoreApplication.translate("FormMain", u"Free-Wili Firmware Updater", None))
        self.groupBox.setTitle(QCoreApplication.translate("FormMain", u"Devices", None))
        self.pushButtonReflash.setText(QCoreApplication.translate("FormMain", u"&Reflash Selected", None))
        self.pushButtonRefresh.setText(QCoreApplication.translate("FormMain", u"&Refresh", None))
        self.groupBoxFirmware.setTitle(QCoreApplication.translate("FormMain", u"Firmware", None))
        self.groupBoxMainUf2.setTitle(QCoreApplication.translate("FormMain", u"Main UF2", None))
        self.toolButtonMainUf2Browse.setText(QCoreApplication.translate("FormMain", u"...", None))
        self.groupBoxDisplayUf2.setTitle(QCoreApplication.translate("FormMain", u"Display UF2", None))
        self.toolButtonDisplayUf2Browse.setText(QCoreApplication.translate("FormMain", u"...", None))
        self.labelSpinner.setText("")
        self.groupBoxDetails.setTitle(QCoreApplication.translate("FormMain", u"Details", None))
        self.labelDetails.setText(QCoreApplication.translate("FormMain", u"TextLabel", None))
        self.groupBoxConsole.setTitle(QCoreApplication.translate("FormMain", u"Console", None))
        self.pushButtonLogClear.setText(QCoreApplication.translate("FormMain", u"&Clear", None))
    # retranslateUi

