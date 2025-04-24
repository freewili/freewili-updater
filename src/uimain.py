import dataclasses
import enum
from pathlib import Path
from queue import Empty, Queue
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


def update_progress(
    tx_queue: Queue, device: DeviceInfo, msg: str, progress: float
) -> None:
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
                if (
                    time.time() - last_update >= 1.0
                    and written_bytes != last_written_bytes
                ):
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


def update_uf2(
    src_fname: str, dst_path: str, index: int, device: DeviceInfo, queue: Queue
):
    dst = Path(dst_path) / Path(src_fname).name
    send_file(src_fname, dst, index, device, queue)


class MainWidget(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget | None = None):
        QtWidgets.QWidget.__init__(self, parent)
        self.ui = Ui_FormMain()
        self.ui.setupUi(self)

        settings = QtCore.QSettings()

        self.header_labels = (
            "Type",
            "Serial",
            "Kind",
            "Version",
            "Path",
            "Name",
            "Serial",
            "Status",
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

    @QtCore.Slot()
    def on_pushButtonRefresh_clicked(self):
        if self.ui.pushButtonRefresh.text() == "Running...":
            self.worker.quit()
            return
        model = self.ui.treeViewDevices.model()
        if not model:
            return
        
        model.clear()
        model.setHorizontalHeaderLabels(self.header_labels)

        
        
        # Lets create the worker and start it
        self.worker = updater.Worker(self.run_refresh)
        self.worker.signals.started.connect(self.refresh_worker_started)
        self.worker.signals.finished.connect(self.refresh_worker_complete)
        QtCore.QThreadPool.globalInstance().start(self.worker)

        # fw_devices = FreeWili.find_all()
        # selected = self.ui.treeViewDevices.selectionModel().selectedRows()
        # devices = []
        # for i, item in enumerate(selected):
        #     name = model.item(item.row(), 0).data(QtCore.Qt.DisplayRole)
        #     serial = model.item(item.row(), 1).data(QtCore.Qt.DisplayRole)
        #     kind = model.item(item.row(), 2).data(QtCore.Qt.DisplayRole)
        #     for device in fw_devices:
        #         if device.device.serial != serial:
        #             continue
        #         if name == "Main" and self.ui.groupBoxMainUf2.isChecked():
        #             devices.append(
        #                 DeviceInfo(
        #                     FreeWiliProcessorType.Main,
        #                     device.device.serial,
        #                     "MassStorage" in kind,
        #                 )
        #             )
        #         elif name == "Display" and self.ui.groupBoxDisplayUf2.isChecked():
        #             devices.append(
        #                 DeviceInfo(
        #                     FreeWiliProcessorType.Display,
        #                     device.device.serial,
        #                     "MassStorage" in kind,
        #                 )
        #             )

        # devices = FreeWili.find_all()

        # model = self.ui.treeViewDevices.model()
        # if not model:
        #     self.ui.treeViewDevices.setModel(QtGui.QStandardItemModel())
        #     model = self.ui.treeViewDevices.model()
        # model.clear()
        # header_labels = (
        #     "Type",
        #     "Serial",
        #     "Kind",
        #     "Version",
        #     "Path",
        #     "Name",
        #     "Serial",
        #     "Status",
        # )
        # model.setHorizontalHeaderLabels(header_labels)
        # devices_to_poll = []
        # for device in devices:
        #     if device.main:
        #         version = ""
        #         # if device.main_serial:
        #         #     match device.main_serial.get_app_info():
        #         #         case Ok(app_version):
        #         #             version = f"v{app_version.version}"
        #         #         case Err(msg):
        #         #             version = msg
        #         model.appendRow(
        #             [
        #                 QtGui.QStandardItem("Main"),
        #                 QtGui.QStandardItem(f"{device.device.serial}"),
        #                 QtGui.QStandardItem(device.main.kind.name),
        #                 QtGui.QStandardItem(version),
        #                 QtGui.QStandardItem(
        #                     " ".join(device.main.paths if device.main.paths else "")
        #                 ),
        #                 QtGui.QStandardItem(device.main.name),
        #                 QtGui.QStandardItem(device.main.serial),
        #             ]
        #         )
        #     if device.display:
        #         version = ""
        #         # if device.display_serial:
        #         #     match device.display_serial.get_app_info():
        #         #         case Ok(app_version):
        #         #             version = f"v{app_version.version}"
        #         #         case Err(msg):
        #         #             version = msg
        #         model.appendRow(
        #             [
        #                 QtGui.QStandardItem("Display"),
        #                 QtGui.QStandardItem(f"{device.device.serial}"),
        #                 QtGui.QStandardItem(device.display.kind.name),
        #                 QtGui.QStandardItem(version),
        #                 QtGui.QStandardItem(
        #                     " ".join(
        #                         device.display.paths if device.display.paths else ""
        #                     )
        #                 ),
        #                 QtGui.QStandardItem(device.display.name),
        #                 QtGui.QStandardItem(device.display.serial),
        #             ]
        #         )
        # for x in range(model.columnCount()):
        #     self.ui.treeViewDevices.resizeColumnToContents(x)
        # self.ui.groupBox.setTitle(f"Devices ({len(devices)})")

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
            name = model.item(item.row(), 0).data(QtCore.Qt.DisplayRole)
            serial = model.item(item.row(), 1).data(QtCore.Qt.DisplayRole)
            kind = model.item(item.row(), 2).data(QtCore.Qt.DisplayRole)
            for device in fw_devices:
                if device.device.serial != serial:
                    continue
                if name == "Main" and self.ui.groupBoxMainUf2.isChecked():
                    devices.append(
                        DeviceInfo(
                            FreeWiliProcessorType.Main,
                            device.device.serial,
                            "MassStorage" in kind,
                        )
                    )
                elif name == "Display" and self.ui.groupBoxDisplayUf2.isChecked():
                    devices.append(
                        DeviceInfo(
                            FreeWiliProcessorType.Display,
                            device.device.serial,
                            "MassStorage" in kind,
                        )
                    )
        # Lets create the worker and start it
        self.worker = updater.Worker(
            self.run_reflash,
            devices=devices,
            main_uf2_fname=self.ui.lineEditMainUf2.text(),
            display_uf2_fname=self.ui.lineEditDisplayUf2.text(),
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
        devices = FreeWili.find_all()
        selected = self.ui.treeViewDevices.selectionModel().selectedRows()
        serial_devices = []
        for item in selected:
            name = model.item(item.row(), 0).data(QtCore.Qt.DisplayRole)
            serial = model.item(item.row(), 1).data(QtCore.Qt.DisplayRole)
            kind = model.item(item.row(), 2).data(QtCore.Qt.DisplayRole)
            for device in devices:
                if device.device.serial != serial:
                    continue
                if name == "Main" and "Serial" in kind:
                    serial_devices.append(
                        DeviceInfo(
                            FreeWiliProcessorType.Main, device.device.serial, False
                        )
                    )
                elif name == "Display" and "Serial" in kind:
                    serial_devices.append(
                        DeviceInfo(
                            FreeWiliProcessorType.Display, device.device.serial, False
                        )
                    )
        # Lets create the worker and start it
        self.worker = updater.Worker(self.run_enter_uf2, devices=serial_devices)
        self.worker.signals.started.connect(self.uf2_worker_started)
        self.worker.signals.finished.connect(self.uf2_worker_complete)
        QtCore.QThreadPool.globalInstance().start(self.worker)

    @classmethod
    def run_refresh(self, tx_queue: Queue, rx_queue: Queue, *args, **kwargs) -> None:
        devices = FreeWili.find_all()
        app_versions = {}
        app_versions_lock = threading.Lock()

        def poll_app_version(device):
            main_version = ""
            if device.main_serial:
                match device.main_serial.get_app_info():
                    case Ok(version):
                        main_version = f"v{version}"
                    case Err(msg):
                        main_version = msg
            display_version = ""
            if device.display_serial:
                match device.display_serial.get_app_info():
                    case Ok(version):
                        display_version = f"v{version}"
                    case Err(msg):
                        display_version = msg
            with app_versions_lock:
                app_versions[device.device.serial] = (main_version, display_version)

        threads = []
        for device in devices:
            t = threading.Thread(target=poll_app_version, args=(device,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        for device in devices:
            main_version, display_version = app_versions[device.device.serial]
            tx_queue.put(
                updater.WorkerCommand.new(
                    updater.WorkerCommandType.NewDevice,
                    NewFreeWiliDevice(device, main_version, display_version),
                )
            )

    @classmethod
    def enter_uf2(self, tx_queue: Queue, rx_queue: Queue, *args, **kwargs) -> bool:
        devices = FreeWili.find_all()
        uf2_devices: tuple[DeviceInfo] = kwargs["devices"]
        errors_occurred = False
        for device in devices:
            for uf2_device in uf2_devices:
                # Only match the device we want to put into UF2
                if device.device.serial != uf2_device.serial:
                    continue
                # Skip if we are already in UF2
                if uf2_device.is_uf2_mode:
                    tx_queue.put(
                        updater.WorkerCommand.new(
                            updater.WorkerCommandType.Progress,
                            (uf2_device, "Already in UF2 bootloader...", 0),
                        )
                    )
                    continue
                # Lets go
                tx_queue.put(
                    updater.WorkerCommand.new(
                        updater.WorkerCommandType.Progress,
                        (uf2_device, "Entering UF2 bootloader...", 0),
                    )
                )
                match device.reset_to_uf2_bootloader(uf2_device.processor_type):
                    case Ok(_):
                        tx_queue.put(
                            updater.WorkerCommand.new(
                                updater.WorkerCommandType.Progress,
                                (uf2_device, "Entered UF2", 100),
                            )
                        )
                    case Err(msg):
                        errors_occurred = True
                        tx_queue.put(
                            updater.WorkerCommand.new(
                                updater.WorkerCommandType.Error, (uf2_device, msg)
                            )
                        )
        return not errors_occurred

    @classmethod
    def run_enter_uf2(self, tx_queue: Queue, rx_queue: Queue, *args, **kwargs) -> None:
        try:
            if not self.enter_uf2(tx_queue, rx_queue, *args, **kwargs):
                return
        except Exception as _ex:
            return

    @classmethod
    def run_reflash(self, tx_queue: Queue, rx_queue: Queue, *args, **kwargs) -> None:
        def _wait(
            devices,
            delay_sec: float,
            msg: str,
            processor_types: tuple[FreeWiliProcessorType],
        ):
            start = time.time()
            elapsed = time.time() - start
            while elapsed <= bootloader_delay_sec:
                elapsed = time.time() - start
                # Update status
                for device in devices:
                    if device.processor_type in processor_types:
                        update_progress(
                            tx_queue,
                            device,
                            f"{msg}: Waiting {bootloader_delay_sec - elapsed:.1f} second(s)",
                            ((bootloader_delay_sec - elapsed) / bootloader_delay_sec)
                            * 100.0,
                        )
                try:
                    # check if we need to quit
                    value: updater.WorkerCommand = rx_queue.get_nowait()
                    if value == updater.WorkerCommandType.Quit:
                        for device in devices:
                            update_progress(tx_queue, device, "Done", 100)
                        return
                except Empty:
                    pass
                time.sleep(0.250)
            # Update status
            for device in devices:
                if device.processor_type in processor_types:
                    update_progress(tx_queue, device, f"{msg}: Done waiting", 100)

        bootloader_delay_sec = 15.0
        devices: tuple[DeviceInfo] = kwargs["devices"]
        # Lets make sure everything is in UF2 bootloader first
        try:
            if not self.enter_uf2(tx_queue, rx_queue, *args, **kwargs):
                return
        except Exception as _ex:
            return

        _wait(
            devices,
            bootloader_delay_sec,
            "UF2 driver settle",
            (FreeWiliProcessorType.Main, FreeWiliProcessorType.Display),
        )

        fw_devices = FreeWili.find_all()
        # Finally, lets reflash
        main_threads = []
        display_threads = []
        for fw_device in fw_devices:
            for i, device in enumerate(devices):
                # Only match the device we want to reflash
                if (
                    fw_device.device.serial != device.serial
                    and fw_device.main.kind != USBDeviceType.MassStorage
                ):
                    continue
                if device.processor_type is FreeWiliProcessorType.Main:
                    t = Thread(
                        target=update_uf2,
                        args=(
                            kwargs["main_uf2_fname"],
                            fw_device.main.paths[0],
                            i,
                            device,
                            tx_queue,
                        ),
                    )
                    main_threads.append(t)
                elif device.processor_type is FreeWiliProcessorType.Display:
                    t = Thread(
                        target=update_uf2,
                        args=(
                            kwargs["display_uf2_fname"],
                            fw_device.display.paths[0],
                            i,
                            device,
                            tx_queue,
                        ),
                    )
                    display_threads.append(t)

        for t in display_threads:
            t.start()
        for t in display_threads:
            t.join()

        _wait(
            devices,
            bootloader_delay_sec,
            "Display reboot",
            (FreeWiliProcessorType.Main,),
        )

        for t in main_threads:
            t.start()
        for t in main_threads:
            t.join()

        _wait(
            devices,
            bootloader_delay_sec,
            "Driver settle",
            (FreeWiliProcessorType.Main, FreeWiliProcessorType.Display),
        )

        for device in devices:
            update_progress(tx_queue, device, "Done.", 100)

    def _parse_queue(self, queue: Queue, max_count=50):
        for _ in range(max_count):
            try:
                cmd = queue.get_nowait()
                if cmd.command_type == updater.WorkerCommandType.Progress:
                    self.update_device_status(*cmd.value)
                    print(*cmd.value)
                    QtCore.QCoreApplication.processEvents()
                elif cmd.command_type == updater.WorkerCommandType.Error:
                    self.update_device_status(cmd.value[0], cmd.value[1], 0)
                elif cmd.command_type == updater.WorkerCommandType.NewDevice:
                    self.create_new_device() # TODO
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
        # self.button.setEnabled(False)
        self.ui.pushButtonEnterUf2.setText("Running...")
        self.uf2_timer = QtCore.QTimer()
        self.uf2_timer.setInterval(3)
        self.uf2_timer.setSingleShot(False)
        self.uf2_timer.timeout.connect(self.uf2_timer_timeout)
        self.uf2_timer.start()

    @QtCore.Slot()
    def uf2_worker_complete(self):
        self.ui.pushButtonEnterUf2.setEnabled(True)
        self.ui.pushButtonEnterUf2.setText(self.uf2_button_text)
        tx_queue, _ = self.worker.get_job_queues()
        self._parse_queue(tx_queue)
        del self.worker
        self.uf2_timer.stop()

    @QtCore.Slot()
    def reflash_worker_started(self):
        # self.button.setEnabled(False)
        self.ui.pushButtonReflash.setText("Running...")
        self.reflash_timer = QtCore.QTimer()
        self.reflash_timer.setInterval(3)
        self.reflash_timer.setSingleShot(False)
        self.reflash_timer.timeout.connect(self.reflash_timer_timeout)
        self.reflash_timer.start()

    @QtCore.Slot()
    def reflash_worker_complete(self):
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

    def update_device_status(
        self, device: DeviceInfo, msg: str, progress: float
    ) -> None:
        model = self.ui.treeViewDevices.model()
        if not model:
            return
        for i in range(model.rowCount()):
            processor_type = model.item(i, 0).data(QtCore.Qt.DisplayRole)
            serial = model.item(i, 1).data(QtCore.Qt.DisplayRole)
            if processor_type == device.processor_type.name and serial == device.serial:
                model.setData(
                    model.index(i, 7), f"{msg} {progress:.1f}%", QtCore.Qt.DisplayRole
                )
                break
