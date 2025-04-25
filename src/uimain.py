import enum
from queue import Empty, Queue
from threading import Thread
from typing import Any

from freewili import FreeWili
from freewili.types import FreeWiliProcessorType
from PySide6 import QtCore, QtGui, QtWidgets

import updater
from ui.main import Ui_FormMain


class ProgressDataType(enum.Enum):
    Progress = QtCore.Qt.ItemDataRole.UserRole + 1000
    Text = QtCore.Qt.ItemDataRole.DisplayRole


class ProgressDelegate(QtWidgets.QStyledItemDelegate):
    """Custom Delegate displaying a Progress bar."""

    def paint(self, painter, option, index):
        """Draw the actual progress bar."""
        progress = index.data(ProgressDataType.Progress.value)
        if not progress:
            progress = 0.0
        text = index.data(ProgressDataType.Text.value)
        if not text:
            text = ""

        opt = QtWidgets.QStyleOptionProgressBar()
        opt.rect = option.rect
        opt.minimum = 0
        if progress < 0:
            opt.maximum = 0
            opt.text = f"{text}"
        else:
            opt.maximum = 100
            opt.text = f"{text} {progress:.1f}%"
        opt.progress = float(progress)
        opt.textVisible = True
        opt.state |= QtWidgets.QStyle.StateFlag.State_Horizontal
        style = option.widget.style() if option.widget is not None else QtWidgets.QApplication.style()
        style.drawControl(QtWidgets.QStyle.ControlElement.CE_ProgressBar, opt, painter, option.widget)


class MainWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        QtWidgets.QWidget.__init__(self, parent)
        self.ui: Ui_FormMain = Ui_FormMain()
        self.ui.setupUi(self)

        self.worker: updater.Worker

        settings = QtCore.QSettings()

        self.header_labels = (
            "Name",
            "Status",
            "Kind",
            "Serial",
        )
        self.progress_delegate = ProgressDelegate(self.ui.treeViewDevices)
        self.ui.treeViewDevices.setItemDelegateForColumn(self.header_labels.index("Status"), self.progress_delegate)

        self.ui.lineEditMainUf2.setText(settings.value("MainUF2Path", ""))
        self.ui.lineEditDisplayUf2.setText(settings.value("DisplayUF2Path", ""))

        self.uf2_button_text = self.ui.pushButtonEnterUf2.text()
        self.reflash_button_text = self.ui.pushButtonReflash.text()
        self.refresh_button_text = self.ui.pushButtonRefresh.text()

        self.restoreGeometry(settings.value("WindowGeometry", self.saveGeometry()))
        # self.restoreState(settings.value("WindowState", self.saveState()))

    @QtCore.Slot()
    def closeEvent(self, event: QtCore.QEvent) -> None:  # noqa: N802
        """Window close event handler."""
        settings = QtCore.QSettings()
        settings.setValue("WindowGeometry", self.saveGeometry())

    @QtCore.Slot()
    def on_toolButtonMainUf2Browse_clicked(self) -> None:  # noqa: N802
        """Button click handler."""
        fname, filter_type = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Open Main Firmware",
            "~/Downloads",
            "UF2 Files (*.uf2);;All Files (*.*)",
        )
        if fname:
            settings = QtCore.QSettings()
            settings.setValue("MainUF2Path", fname)
            self.ui.lineEditMainUf2.setText(fname)

    @QtCore.Slot()
    def on_toolButtonDisplayUf2Browse_clicked(self) -> None:  # noqa: N802
        """Button click handler."""
        fname, filter_type = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Display Firmware", ".", "UF2 Files (*.uf2);;All Files (*.*)"
        )
        if fname:
            settings = QtCore.QSettings()
            settings.setValue("DisplayUF2Path", fname)
            self.ui.lineEditDisplayUf2.setText(fname)

    def add_device(self, model: QtGui.QStandardItemModel, freewili: FreeWili, statuses: dict) -> None:
        """Add a FreeWili device to the treeview."""
        assert isinstance(model, QtGui.QStandardItemModel)
        assert isinstance(freewili, FreeWili)

        parent_item = QtGui.QStandardItem(freewili.device.serial)
        if freewili.main:
            status = ""
            if freewili.main.paths:
                status = freewili.main.paths[0]
            elif freewili.main.port:
                status = freewili.main.port
            parent_item.appendRow(
                [
                    QtGui.QStandardItem(f"Main - {freewili.main.name}"),
                    QtGui.QStandardItem(status),
                    QtGui.QStandardItem(freewili.main.kind.name),
                    QtGui.QStandardItem(freewili.main.serial),
                ]
            )
        if freewili.display:
            status = ""
            if freewili.display.paths:
                status = freewili.display.paths[0]
            elif freewili.display.port:
                status = freewili.display.port
            parent_item.appendRow(
                [
                    QtGui.QStandardItem(f"Display - {freewili.display.name}"),
                    QtGui.QStandardItem(status),
                    QtGui.QStandardItem(freewili.display.kind.name),
                    QtGui.QStandardItem(freewili.display.serial),
                ]
            )

        parent_progress = QtGui.QStandardItem()
        if freewili.device.serial in statuses:
            progress, text = statuses[freewili.device.serial]
            parent_progress.setData(progress, ProgressDataType.Progress.value)
            parent_progress.setData(text, ProgressDataType.Text.value)
        model.appendRow([parent_item, parent_progress])

    @QtCore.Slot()
    def on_pushButtonRefresh_clicked(self) -> None:  # noqa: N802
        """Button click handler."""
        model = self.ui.treeViewDevices.model()
        if not model:
            self.ui.treeViewDevices.setModel(QtGui.QStandardItemModel())
            model = self.ui.treeViewDevices.model()
        # Save the status message
        saved_status = {}
        for i in range(model.rowCount()):
            serial = model.item(i, self.header_labels.index("Name")).data(QtCore.Qt.DisplayRole)
            status_progress = model.item(i, self.header_labels.index("Status")).data(ProgressDataType.Progress.value)
            status_text = model.item(i, self.header_labels.index("Status")).data(ProgressDataType.Text.value)
            saved_status[serial] = (status_progress, status_text)

        model.clear()
        model.setHorizontalHeaderLabels(self.header_labels)
        fw_devices = FreeWili.find_all()

        for fw_device in fw_devices:
            self.add_device(model, fw_device, saved_status)

        self.ui.treeViewDevices.expandAll()
        for x in range(model.columnCount()):
            self.ui.treeViewDevices.resizeColumnToContents(x)
        self.ui.treeViewDevices.setColumnWidth(self.header_labels.index("Status"), 500)
        self.ui.groupBox.setTitle(f"Devices ({len(fw_devices)})")

    @QtCore.Slot()
    def on_pushButtonReflash_clicked(self) -> None:  # noqa: N802
        """Button click handler."""
        if self.ui.pushButtonEnterUf2.text() == "Running...":
            self.worker.quit()
            return
        model = self.ui.treeViewDevices.model()
        if not model:
            return
        if (
            QtWidgets.QMessageBox.warning(
                self,
                "Reflashing",
                "Do not disconnect the Free-Wili(s) or interact with the drives while flashing!",
                QtWidgets.QMessageBox.StandardButton.Ok | QtWidgets.QMessageBox.StandardButton.Cancel,
                QtWidgets.QMessageBox.StandardButton.Cancel,
            )
            != QtWidgets.QMessageBox.StandardButton.Ok
        ):
            return
        fw_devices = FreeWili.find_all()
        selected = self.ui.treeViewDevices.selectionModel().selectedRows()
        devices = []
        for index in selected:
            # We don't care about the children rows
            item = model.itemFromIndex(index)
            if not item.hasChildren():
                continue
            serial = model.item(index.row(), 0).data(QtCore.Qt.DisplayRole)
            for fw_device in fw_devices:
                if fw_device.device.serial == serial:
                    devices.append(fw_device)

        # Lets create the worker and start it
        self.worker = updater.Worker(
            self.run_reflash,
            devices=devices,
            main_uf2_fname=self.ui.lineEditMainUf2.text(),
            display_uf2_fname=self.ui.lineEditDisplayUf2.text(),
            main_enabled=self.ui.groupBoxMainUf2.isChecked(),
            display_enabled=self.ui.groupBoxDisplayUf2.isChecked(),
        )
        self.worker.signals.started.connect(self.reflash_worker_started)
        self.worker.signals.finished.connect(self.reflash_worker_complete)
        QtCore.QThreadPool.globalInstance().start(self.worker)

    @QtCore.Slot()
    def on_pushButtonEnterUf2_clicked(self) -> None:  # noqa: N802
        """Button click handler."""
        if self.ui.pushButtonEnterUf2.text() == "Running...":
            self.worker.quit()
            return

        model = self.ui.treeViewDevices.model()
        if not model:
            return
        if (
            QtWidgets.QMessageBox.warning(
                self,
                "Enter UF2 Bootloader",
                "Do not disconnect the Free-Wili(s).\nWARNING: Firmware needs to be flashed to exit this mode.",
                QtWidgets.QMessageBox.StandardButton.Ok | QtWidgets.QMessageBox.StandardButton.Cancel,
                QtWidgets.QMessageBox.StandardButton.Cancel,
            )
            != QtWidgets.QMessageBox.StandardButton.Ok
        ):
            return
        fw_devices = FreeWili.find_all()
        selected = self.ui.treeViewDevices.selectionModel().selectedRows()
        devices = []
        for index in selected:
            # We don't care about the children rows
            item = model.itemFromIndex(index)
            if not item.hasChildren():
                continue
            serial = model.item(index.row(), 0).data(QtCore.Qt.DisplayRole)
            for fw_device in fw_devices:
                if fw_device.device.serial == serial:
                    devices.append(fw_device)
        # Lets create the worker and start it
        self.worker = updater.Worker(
            self.run_enter_uf2,
            devices=fw_devices,
            main_enabled=self.ui.groupBoxMainUf2.isChecked(),
            display_enabled=self.ui.groupBoxDisplayUf2.isChecked(),
        )
        self.worker.signals.started.connect(self.uf2_worker_started)
        self.worker.signals.finished.connect(self.uf2_worker_complete)
        QtCore.QThreadPool.globalInstance().start(self.worker)

    @classmethod
    def run_enter_uf2(cls, tx_queue: Queue, rx_queue: Queue, *args: Any, **kwargs: Any) -> None:
        """Worker method to enter UF2 bootloader on Free-Wili devices."""
        devices: tuple[FreeWili] = kwargs["devices"]
        main_enabled: bool = kwargs["main_enabled"]
        display_enabled: bool = kwargs["display_enabled"]

        bl_devices: list[updater.FreeWiliBootloader] = []
        for device in devices:
            bl_devices.append(updater.FreeWiliBootloader(device, tx_queue))

        if display_enabled:
            threads = []
            for i, bl_device in enumerate(bl_devices):
                t = Thread(
                    target=bl_device.enter_uf2,
                    args=(FreeWiliProcessorType.Display,),
                )
                t.start()
                threads.append(t)

            for thread in threads:
                thread.join()

        if main_enabled:
            threads = []
            for i, bl_device in enumerate(bl_devices):
                t = Thread(
                    target=bl_device.enter_uf2,
                    args=(FreeWiliProcessorType.Main,),
                )
                t.start()
                threads.append(t)

            for thread in threads:
                thread.join()

    @classmethod
    def run_reflash(cls, tx_queue: Queue, rx_queue: Queue, *args: Any, **kwargs: Any) -> None:
        """Worker method to reflash firmware on Free-Wili devices."""
        devices: tuple[FreeWili] = kwargs["devices"]
        main_uf2_fname: str = kwargs["main_uf2_fname"]
        display_uf2_fname: str = kwargs["display_uf2_fname"]
        main_enabled: bool = kwargs["main_enabled"]
        display_enabled: bool = kwargs["display_enabled"]

        bl_devices: list[updater.FreeWiliBootloader] = []
        for device in devices:
            bl_devices.append(updater.FreeWiliBootloader(device, tx_queue))

        if display_enabled:
            threads = []
            for i, bl_device in enumerate(bl_devices):
                t = Thread(
                    target=bl_device.flash_firmware,
                    args=(
                        display_uf2_fname,
                        FreeWiliProcessorType.Display,
                        i,
                    ),
                )
                t.start()
                threads.append(t)

            for thread in threads:
                thread.join()

        if main_enabled:
            threads = []
            for i, bl_device in enumerate(bl_devices):
                t = Thread(
                    target=bl_device.flash_firmware,
                    args=(
                        main_uf2_fname,
                        FreeWiliProcessorType.Main,
                        i,
                    ),
                )
                t.start()
                threads.append(t)

            for thread in threads:
                thread.join()

    def _parse_queue(self, queue: Queue, max_count: int = 50) -> None:
        for _ in range(max_count):
            try:
                cmd = queue.get_nowait()
                if isinstance(cmd, updater.FreeWiliBootloaderMessage):
                    print(cmd)
                    self.update_device_status(cmd)
                else:
                    print(cmd)
                QtCore.QCoreApplication.processEvents()
            except Empty:
                break

    @QtCore.Slot()
    def uf2_worker_started(self) -> None:
        """Signal for UF2 bootloader worker."""
        self.ui.groupBoxMainUf2.setEnabled(False)
        self.ui.groupBoxDisplayUf2.setEnabled(False)
        self.ui.pushButtonReflash.setEnabled(False)
        self.ui.pushButtonEnterUf2.setText("Running...")
        self.uf2_timer = QtCore.QTimer()
        self.uf2_timer.setInterval(3)
        self.uf2_timer.setSingleShot(False)
        self.uf2_timer.timeout.connect(self._uf2_timer_timeout)
        self.uf2_timer.start()

    @QtCore.Slot()
    def uf2_worker_complete(self) -> None:
        """Signal for UF2 bootloader worker."""
        self.ui.groupBoxMainUf2.setEnabled(True)
        self.ui.groupBoxDisplayUf2.setEnabled(True)
        self.ui.pushButtonReflash.setEnabled(True)
        self.ui.pushButtonEnterUf2.setEnabled(True)
        self.ui.pushButtonEnterUf2.setText(self.uf2_button_text)
        tx_queue, _ = self.worker.get_job_queues()
        self._parse_queue(tx_queue)
        del self.worker
        self.uf2_timer.stop()
        self.on_pushButtonRefresh_clicked()

    @QtCore.Slot()
    def reflash_worker_started(self) -> None:
        """Signal for reflash firmware worker."""
        self.ui.groupBoxMainUf2.setEnabled(False)
        self.ui.groupBoxDisplayUf2.setEnabled(False)
        self.ui.pushButtonEnterUf2.setEnabled(False)
        self.ui.pushButtonReflash.setText("Running...")
        self.reflash_timer = QtCore.QTimer()
        self.reflash_timer.setInterval(3)
        self.reflash_timer.setSingleShot(False)
        self.reflash_timer.timeout.connect(self._reflash_timer_timeout)
        self.reflash_timer.start()

    @QtCore.Slot()
    def reflash_worker_complete(self) -> None:
        """Signal for reflash firmware worker."""
        self.ui.groupBoxMainUf2.setEnabled(True)
        self.ui.groupBoxDisplayUf2.setEnabled(True)
        self.ui.pushButtonReflash.setEnabled(True)
        self.ui.pushButtonEnterUf2.setEnabled(True)
        self.ui.pushButtonReflash.setText(self.reflash_button_text)
        tx_queue, _ = self.worker.get_job_queues()
        self._parse_queue(tx_queue)
        del self.worker
        self.reflash_timer.stop()
        self.on_pushButtonRefresh_clicked()

    @QtCore.Slot()
    def _uf2_timer_timeout(self) -> None:
        tx_queue, _ = self.worker.get_job_queues()
        self._parse_queue(tx_queue)

    @QtCore.Slot()
    def _reflash_timer_timeout(self) -> None:
        tx_queue, _ = self.worker.get_job_queues()
        self._parse_queue(tx_queue)

    def update_device_status(self, msg: updater.FreeWiliBootloaderMessage) -> None:
        """Update the status field in the treeview."""
        model = self.ui.treeViewDevices.model()
        if not model:
            return
        for i in range(model.rowCount()):
            serial = model.item(i, self.header_labels.index("Name")).data(QtCore.Qt.DisplayRole)
            if serial == msg.serial:
                model.setData(
                    model.index(i, self.header_labels.index("Status")),
                    f"{msg.msg} {'' if msg.success else 'Failed'}",
                    ProgressDataType.Text.value,
                )
                model.setData(
                    model.index(i, self.header_labels.index("Status")),
                    msg.progress,
                    ProgressDataType.Progress.value,
                )
                break
