import os
import pathlib
import platform
import subprocess
import time
from typing import Any, Self
from PySide6 import QtCore, QtGui, QtWidgets
import enum
import dataclasses
from queue import Empty, Queue

from freewili import FreeWili
from freewili.types import FreeWiliProcessorType
import pyfwfinder
from result import Err, Ok, UnwrapError
import atomics
from pyfwfinder import USBDeviceType


class WorkerCommandType(enum.Enum):
    Quit = enum.auto()
    Progress = enum.auto()
    Error = enum.auto()
    NewDevice = enum.auto()


@dataclasses.dataclass(frozen=True)
class WorkerCommand:
    command_type: WorkerCommandType
    value: Any = None

    @classmethod
    def quit(cls) -> Self:
        return cls(WorkerCommandType.Quit, None)

    @classmethod
    def new(cls, cmd: WorkerCommandType, value: Any) -> Self:
        return cls(cmd, value)


class WorkerSignals(QtCore.QObject):
    started = QtCore.Signal()
    finished = QtCore.Signal()


class Worker(QtCore.QRunnable):
    def __init__(self, fn, signals=WorkerSignals, *args, **kwargs):
        super(Worker, self).__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = signals()
        self.tx_queue = Queue()
        self.rx_queue = Queue()

        self.kwargs["tx_queue"] = self.tx_queue
        self.kwargs["rx_queue"] = self.rx_queue

        if "thread_name" not in kwargs:
            self.kwargs["thread_name"] = "Default"

    def get_job_queues(self) -> tuple[Queue, Queue]:
        return self.tx_queue, self.rx_queue

    @QtCore.Slot()
    def run(self):
        self.signals.started.emit()
        try:
            self.fn(*self.args, **self.kwargs)
        finally:
            self.signals.finished.emit()

    @QtCore.Slot()
    def quit(self) -> None:
        self.rx_queue.put(WorkerCommand.quit())

    # @Slot(str, Any)
    # def set_value(self, name: str, value: Any) -> None:
    #     self.rx_queue.put(WorkerCommand.set_value(name, value))


@dataclasses.dataclass(frozen=True)
class FreeWiliBootloaderMessage:
    serial: str
    msg: str
    progress: None | float
    success: bool


class FreeWiliBootloader:
    def __init__(self, freewili: FreeWili, msg_queue: Queue = Queue()):
        assert isinstance(freewili, FreeWili)
        assert isinstance(msg_queue, Queue)
        self.msg_queue = msg_queue
        self.freewili = freewili
        self._quit = False
        self._debug_print = True

    def quit(self):
        self._quit = True

    def _message(self, msg: str, success: bool, progress: None | float = None):
        assert isinstance(msg, str)
        assert isinstance(success, bool)
        if progress is not None:
            assert isinstance(progress, (int, float))

        self.msg_queue.put(FreeWiliBootloaderMessage(self.freewili.device.serial, msg, progress, success))
        if self._debug_print:
            print(f"{self.freewili.device.serial}: {msg} {progress} {success}")

    def _wait_for_device(
        self,
        usb_types: None | tuple[USBDeviceType],
        processor_type: FreeWiliProcessorType,
        timeout_sec: float = 30.0,
        delay_sec: float = 6.0,
    ) -> bool:
        if not usb_types:
            usb_types = (
                USBDeviceType.Serial,
                USBDeviceType.SerialMain,
                USBDeviceType.SerialDisplay,
                USBDeviceType.MassStorage,
            )
        assert isinstance(usb_types, (tuple, list))
        assert isinstance(processor_type, FreeWiliProcessorType)
        assert isinstance(timeout_sec, (int, float))

        self._message(f"Waiting for {processor_type.name}...", True)
        start = time.time()
        try:
            while (time.time() - start) < timeout_sec:
                if self._quit:
                    return False
                try:
                    devices = FreeWili.find_all()
                except RuntimeError as _ex:
                    continue
                for device in devices:
                    if self.freewili.device.serial != device.device.serial:
                        continue
                    usb_device = device.get_usb_device(processor_type)
                    if not usb_device:
                        continue
                    if usb_device.kind in usb_types:
                        self._message(f"{processor_type.name} {usb_device.kind.name} ready", True)
                        return True
                time.sleep(0.1)
        finally:
            start = time.time()
            while (time.time() - start) < delay_sec:
                if self._quit:
                    return False
                time.sleep(0.01)
        return False

    def enter_uf2(self, processor_type: FreeWiliProcessorType) -> bool:
        assert isinstance(processor_type, FreeWiliProcessorType)

        if not self._wait_for_device(None, processor_type):
            self._message("Device no longer exists", False)
            return False

        self._message("Entering UF2 bootloader...", True)
        try:
            # We might already be in UF2 bootloader, lets check here
            usb_device = self.freewili.get_usb_device(processor_type)
            if usb_device and usb_device.kind == USBDeviceType.MassStorage:
                self._message("Entered UF2 bootloader", True)
                return True
            self.freewili.get_serial_from(processor_type).expect(
                f"Failed to get serial on processor {processor_type.name}"
            ).reset_to_uf2_bootloader().expect(f"Failed to enter UF2 bootloader on {processor_type.name}")
            self._message("Waiting for device driver...", True)
            if not self._wait_for_device((USBDeviceType.MassStorage,), processor_type):
                self._message("Device no longer exists", False)
                return False
            self._message("Entered UF2 bootloader", True)
            return True
        except UnwrapError as ex:
            self._message(str(ex), False)
            return False

    def flash_firmware(
        self,
        uf2_fname: str | pathlib.Path,
        processor_type: FreeWiliProcessorType,
        delay_sec: int | float = 0.0,
    ) -> bool:
        assert isinstance(processor_type, FreeWiliProcessorType)
        if isinstance(uf2_fname, str):
            uf2_fname = pathlib.Path(uf2_fname)

        if not uf2_fname.exists():
            self._message(f"{uf2_fname} isn't valid", False)
            return False
        if not self.enter_uf2(processor_type):
            return False

        # Need to find the actual path, self.freewili might be stale
        devices = FreeWili.find_all()
        path: None | str = None
        for device in devices:
            if self.freewili.device.serial != device.device.serial:
                continue
            if processor_type == FreeWiliProcessorType.Main and device.main and device.main.paths:
                path = pathlib.Path(device.main.paths[0])
                break
            elif processor_type == FreeWiliProcessorType.Display and device.display and device.display.paths:
                path = pathlib.Path(device.display.paths[0])
                break
        if not path:
            self._message("Failed to find drive path", False)
            return False
        self._message(f"Uploading {uf2_fname.name} to {path}...", True)

        # update our destination path with the filename
        path = path / uf2_fname.name
        try:
            fsize_bytes = uf2_fname.stat().st_size
            start = time.time()
            written_bytes = 0
            last_written_bytes = 0
            last_update = start
            with open(str(uf2_fname), "rb") as fsrc, open(str(path), "wb") as fdst:
                while True:
                    buf = fsrc.read(4096*10)  # Read 4096*10 bytes at a time
                    if not buf:
                        # Randomize the end so all the drivers don't populate at the same time
                        time.sleep(delay_sec*2)
                        break
                    written_bytes += len(buf)
                    fdst.write(buf)
                    fdst.flush()
                    if platform.system() == "Linux":
                        ret = subprocess.call(f"sync -d {path}", shell=True)
                        if ret != 0:
                            print(ret)
                    else:
                        try:
                            os.fsync(fdst.fileno())
                            pass
                        except OSError as ex:
                            print(ex)
                    if time.time() - last_update >= 1.0 and written_bytes != last_written_bytes:
                        self._message(
                            f"Wrote {written_bytes / 1000:.0f}KB of {fsize_bytes / 1000:.0f}KB...",
                            True,
                            (written_bytes / fsize_bytes) * 100.0,
                        )
                        last_update = time.time()
                        last_written_bytes = written_bytes
                fdst.flush()
            end = time.time()
            self._message(
                f"Wrote {written_bytes / 1000:.1f}KB in {end - start:.1f} seconds...",
                True,
                100.0,
            )
            return True
        except Exception as ex:
            self._message(
                str(ex),
                False,
            )
        return False


if __name__ == "__main__":
    fw_bootloader = FreeWiliBootloader(FreeWili.find_first().expect("Failed to find any devices"))
    # print(fw_bootloader.enter_uf2(FreeWiliProcessorType.Main))
    print(fw_bootloader.flash_firmware("/home/drebbe/Downloads/FreeWiliDisplayV44.uf2", FreeWiliProcessorType.Display))
    time.sleep(3)
    print(fw_bootloader.flash_firmware("/home/drebbe/Downloads/FreeWiliMainv48.uf2", FreeWiliProcessorType.Main))

    while True:
        try:
            msg = fw_bootloader.msg_queue.get_nowait()
            print(msg)
        except Empty:
            break
