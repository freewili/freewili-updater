import dataclasses
import enum
from pathlib import Path
import platform
from queue import Empty, Queue
import subprocess
from threading import Thread
import threading
import time
from result import Err, Ok
from ui.main import Ui_FormMain

from PySide6 import QtWidgets, QtCore, QtGui
from freewili import FreeWili
from freewili.types import FreeWiliProcessorType
from pyfwfinder import USBDeviceType

import updater


@dataclasses.dataclass(frozen=True)
class DeviceInfo:
    processor_type: FreeWiliProcessorType
    serial: str
    is_uf2_mode: bool


@dataclasses.dataclass(frozen=True)
class NewFreeWiliDevice:
    device: FreeWili
    main_app_version: str
    display_app_version: str


def update_progress(tx_queue: Queue, device: DeviceInfo, msg: str, progress: float) -> None:
    tx_queue.put(
        updater.WorkerCommand.new(
            updater.WorkerCommandType.Progress,
            (device, msg, progress),
        )
    )


def send_file(src, dst, index, device, queue):
    # time.sleep(index)
    try:
        fsize_bytes = Path(src).stat().st_size

        with open(str(src), "rb") as fsrc, open(str(dst), "wb") as fdst:
            written_bytes = 0
            last_written_bytes = 0
            start = time.time()
            last_update = start
            while True:
                buf = fsrc.read(1024)  # Read 1024 bytes at a time
                if not buf:
                    # Randomize the end so all the drivers don't populate at the same time
                    time.sleep(index)
                    break
                written_bytes += 1024
                fdst.write(buf)
                fdst.flush()
                if platform.system() == "Linux":
                    ret = subprocess.call(f"sync -d {dst}", shell=True)
                    if ret != 0:
                        print(ret)
                if time.time() - last_update >= 1.0 and written_bytes != last_written_bytes:
                    update_progress(
                        queue,
                        device,
                        f"Wrote {written_bytes / 1000:.0f}KB of {fsize_bytes / 1000:.0f}KB...",
                        (written_bytes / fsize_bytes) * 100.0,
                    )
                    last_update = time.time()
                    last_written_bytes = written_bytes
            # print()
            fdst.flush()
            end = time.time()
            update_progress(
                queue,
                device,
                f"Wrote {written_bytes / 1000:.1f}KB in {end - start:.1f} seconds...",
                100,
            )
    except Exception as ex:
        print(ex, src, dst, index, device)
        queue.put(
            updater.WorkerCommand.new(
                updater.WorkerCommandType.Error,
                (device, str(ex)),
            )
        )


def update_uf2(src_fname: str, dst_path: str, index: int, device: DeviceInfo, queue: Queue):
    dst = Path(dst_path) / Path(src_fname).name
    send_file(src_fname, dst, index, device, queue)


class MainWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        QtWidgets.QWidget.__init__(self, parent)
        self.ui = Ui_FormMain()
        self.ui.setupUi(self)

        settings = QtCore.QSettings()

        self.header_labels = (
            "Name",
            "Status",
            "Kind",
            "Serial",
        )

        self.ui.lineEditMainUf2.setText(settings.value("MainUF2Path", ""))
        self.ui.lineEditDisplayUf2.setText(settings.value("DisplayUF2Path", ""))

        self.uf2_button_text = self.ui.pushButtonEnterUf2.text()
        self.reflash_button_text = self.ui.pushButtonReflash.text()
        self.refresh_button_text = self.ui.pushButtonRefresh.text()

        self.restoreGeometry(settings.value("WindowGeometry", self.saveGeometry()))
        # self.restoreState(settings.value("WindowState", self.saveState()))

    def closeEvent(self, event):
        settings = QtCore.QSettings()
        settings.setValue("WindowGeometry", self.saveGeometry())

    @QtCore.Slot()
    def on_toolButtonMainUf2Browse_clicked(self):
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
    def on_toolButtonDisplayUf2Browse_clicked(self):
        fname, filter_type = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open Display Firmware", ".", "UF2 Files (*.uf2);;All Files (*.*)"
        )
        if fname:
            settings = QtCore.QSettings()
            settings.setValue("DisplayUF2Path", fname)
            self.ui.lineEditDisplayUf2.setText(fname)

    def add_device(self, model: QtGui.QStandardItemModel, freewili: FreeWili) -> None:
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

        model.appendRow(parent_item)

    @QtCore.Slot()
    def on_pushButtonRefresh_clicked(self):
        model = self.ui.treeViewDevices.model()
        if not model:
            self.ui.treeViewDevices.setModel(QtGui.QStandardItemModel())
            model = self.ui.treeViewDevices.model()
        model.clear()
        model.setHorizontalHeaderLabels(self.header_labels)
        fw_devices = FreeWili.find_all()

        for fw_device in fw_devices:
            self.add_device(model, fw_device)

        self.ui.treeViewDevices.expandAll()
        for x in range(model.columnCount()):
            self.ui.treeViewDevices.resizeColumnToContents(x)
        self.ui.groupBox.setTitle(f"Devices ({len(fw_devices)})")

    @QtCore.Slot()
    def on_pushButtonReflash_clicked(self):
        if self.ui.pushButtonEnterUf2.text() == "Running...":
            self.worker.quit()
            return
        model = self.ui.treeViewDevices.model()
        if not model:
            return
        fw_devices = FreeWili.find_all()
        selected = self.ui.treeViewDevices.selectionModel().selectedRows()
        devices = []
        for i, item in enumerate(selected):
            # We don't care about the children rows
            if item.parent() and item.parent() == model.invisibleRootItem():
                continue
            if not model.item(item.row(), 0):
                continue
            serial = model.item(item.row(), 0).data(QtCore.Qt.DisplayRole)
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
    def on_pushButtonEnterUf2_clicked(self):
        if self.ui.pushButtonEnterUf2.text() == "Running...":
            self.worker.quit()
            return

        model = self.ui.treeViewDevices.model()
        if not model:
            return
        fw_devices = FreeWili.find_all()
        selected = self.ui.treeViewDevices.selectionModel().selectedRows()
        devices = []
        for i, item in enumerate(selected):
            # We don't care about the children rows
            if item.parent() and item.parent() == model.invisibleRootItem():
                continue
            if not model.item(item.row(), 0):
                continue
            serial = model.item(item.row(), 0).data(QtCore.Qt.DisplayRole)
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
    def run_enter_uf2(self, tx_queue: Queue, rx_queue: Queue, *args, **kwargs) -> None:
        devices: tuple[DeviceInfo] = kwargs["devices"]
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
    def run_reflash(self, tx_queue: Queue, rx_queue: Queue, *args, **kwargs) -> None:
        devices: tuple[DeviceInfo] = kwargs["devices"]
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

    def _parse_queue(self, queue: Queue, max_count=50):
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
    def refresh_worker_started(self):
        # self.button.setEnabled(False)
        self.ui.pushButtonRefresh.setText("Running...")
        self.refresh_timer = QtCore.QTimer()
        self.refresh_timer.setInterval(3)
        self.refresh_timer.setSingleShot(False)
        self.refresh_timer.timeout.connect(self.refresh_timer_timeout)
        self.refresh_timer.start()

    @QtCore.Slot()
    def refresh_worker_complete(self):
        self.ui.pushButtonRefresh.setEnabled(True)
        self.ui.pushButtonRefresh.setText(self.refresh_button_text)
        tx_queue, _ = self.worker.get_job_queues()
        self._parse_queue(tx_queue)
        del self.worker
        self.refresh_timer.stop()

    @QtCore.Slot()
    def uf2_worker_started(self):
        self.ui.groupBoxMainUf2.setEnabled(False)
        self.ui.groupBoxDisplayUf2.setEnabled(False)
        self.ui.pushButtonReflash.setEnabled(False)
        self.ui.pushButtonEnterUf2.setText("Running...")
        self.uf2_timer = QtCore.QTimer()
        self.uf2_timer.setInterval(3)
        self.uf2_timer.setSingleShot(False)
        self.uf2_timer.timeout.connect(self.uf2_timer_timeout)
        self.uf2_timer.start()

    @QtCore.Slot()
    def uf2_worker_complete(self):
        self.ui.groupBoxMainUf2.setEnabled(True)
        self.ui.groupBoxDisplayUf2.setEnabled(True)
        self.ui.pushButtonReflash.setEnabled(True)
        self.ui.pushButtonEnterUf2.setEnabled(True)
        self.ui.pushButtonEnterUf2.setText(self.uf2_button_text)
        tx_queue, _ = self.worker.get_job_queues()
        self._parse_queue(tx_queue)
        del self.worker
        self.uf2_timer.stop()

    @QtCore.Slot()
    def reflash_worker_started(self):
        self.ui.groupBoxMainUf2.setEnabled(False)
        self.ui.groupBoxDisplayUf2.setEnabled(False)
        self.ui.pushButtonEnterUf2.setEnabled(False)
        self.ui.pushButtonReflash.setText("Running...")
        self.reflash_timer = QtCore.QTimer()
        self.reflash_timer.setInterval(3)
        self.reflash_timer.setSingleShot(False)
        self.reflash_timer.timeout.connect(self.reflash_timer_timeout)
        self.reflash_timer.start()

    @QtCore.Slot()
    def reflash_worker_complete(self):
        self.ui.groupBoxMainUf2.setEnabled(True)
        self.ui.groupBoxDisplayUf2.setEnabled(True)
        self.ui.pushButtonReflash.setEnabled(True)
        self.ui.pushButtonEnterUf2.setEnabled(True)
        self.ui.pushButtonReflash.setText(self.reflash_button_text)
        tx_queue, _ = self.worker.get_job_queues()
        self._parse_queue(tx_queue)
        del self.worker
        self.reflash_timer.stop()

    @QtCore.Slot()
    def uf2_timer_timeout(self):
        tx_queue, _ = self.worker.get_job_queues()
        self._parse_queue(tx_queue)

    @QtCore.Slot()
    def reflash_timer_timeout(self):
        tx_queue, _ = self.worker.get_job_queues()
        self._parse_queue(tx_queue)

    def update_device_status(self, msg: updater.FreeWiliBootloaderMessage) -> None:
        model = self.ui.treeViewDevices.model()
        if not model:
            return
        for i in range(model.rowCount()):
            serial = model.item(i, self.header_labels.index("Name")).data(QtCore.Qt.DisplayRole)
            if serial == msg.serial:
                model.setData(
                    model.index(i, self.header_labels.index("Status")),
                    f"{msg.msg} {msg.progress if msg.progress else 0:.1f}% {msg.success}",
                    QtCore.Qt.DisplayRole,
                )
                break
