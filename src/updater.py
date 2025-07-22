import dataclasses
import enum
import os
import pathlib
import platform
import subprocess
import threading
import time
from queue import Queue
from typing import Any, Self

import result
from freewili import FreeWili
from freewili.types import FreeWiliProcessorType
from pyfwfinder import USBDeviceType
from PySide6 import QtCore
from result import UnwrapError


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
    def __init__(self, freewili: FreeWili, msg_queue: Queue, uf2_barrier: threading.Barrier, bl_barrier: threading.Barrier):
        assert isinstance(freewili, FreeWili)
        assert isinstance(msg_queue, Queue)
        assert isinstance(uf2_barrier, threading.Barrier)
        assert isinstance(bl_barrier, threading.Barrier)
        self.uf2_barrier = uf2_barrier
        self.bl_barrier = bl_barrier
        self.msg_queue = msg_queue
        self.freewili = freewili
        self._quit = False
        self._debug_print = True

    def quit(self):
        self._quit = True

    def _message(self, msg: str, success: bool, progress: None | float = 0) -> None:
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
        delay_sec: float = 10.0,
    ) -> bool:
        if not usb_types:
            usb_types: None | tuple[USBDeviceType] = (
                USBDeviceType.Serial,
                USBDeviceType.SerialMain,
                USBDeviceType.SerialDisplay,
                USBDeviceType.MassStorage,
            )
        assert isinstance(usb_types, (tuple, list))
        assert isinstance(processor_type, FreeWiliProcessorType)
        assert isinstance(timeout_sec, (int, float))

        self._message(f"Waiting for {processor_type.name}...", True, -1)
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
                        self._message(f"{processor_type.name} {usb_device.kind.name} ready", True, -1)
                        return True
                time.sleep(0.1)
            return False
        finally:
            start = time.time()
            while (time.time() - start) < delay_sec:
                if self._quit:
                    break
                time.sleep(0.01)

    def enter_uf2(self, index: int, processor_type: FreeWiliProcessorType) -> bool:
        assert isinstance(processor_type, FreeWiliProcessorType)

        if not self._wait_for_device(None, processor_type, delay_sec=1):
            self._message("Device no longer exists", False)
            return False

        time.sleep(index/2.0)
        try:
            self.uf2_barrier.wait(90.0)
        except threading.BrokenBarrierError:
            self._message("Oh snap, another device failed, aborting!", False, 100.0)
            return False

        self._message(f"Entering UF2 bootloader on {processor_type.name}...", True)
        try:
            # We might already be in UF2 bootloader, lets check here
            usb_device = self.freewili.get_usb_device(processor_type)
            if usb_device and usb_device.kind == USBDeviceType.MassStorage:
                self._message(f"{processor_type.name} already in UF2 bootloader", True)
                try:
                    self.uf2_barrier.wait(90.0)
                except threading.BrokenBarrierError:
                    self._message("Oh snap, another device failed, aborting!", False, 100.0)
                    return False
                return True
            uf2_count_attempts: int = 3
            while True:
                try:
                    self._message(f"Entering UF2 bootloader on {processor_type.name} ({uf2_count_attempts})...", True)
                    self.freewili.get_serial_from(processor_type).expect(
                        f"Failed to get serial on processor {processor_type.name}"
                    ).reset_to_uf2_bootloader().expect(f"Failed to enter UF2 bootloader on {processor_type.name}")
                    self._message(f"{processor_type.name} entered UF2 bootloader", True)
                    break
                except result.UnwrapError as ex:
                    # For some reason we were getting Input/Output errors when we had 20+ devices connected.
                    uf2_count_attempts -= 1
                    if uf2_count_attempts <= 0:
                        self.uf2_barrier.abort()
                        raise ex
                    self._message(f"Retrying UF2 bootloader on {processor_type.name} ({uf2_count_attempts})", True)
                    time.sleep(6.0)
            self._message("Waiting for device driver...", True, -1)
            if not self._wait_for_device((USBDeviceType.MassStorage,), processor_type):
                self._message(f"{processor_type.name} no longer exists", False)
                return False
            self._message(f"{processor_type.name} entered UF2 bootloader", True)
            try:
                self.uf2_barrier.wait(90.0)
            except threading.BrokenBarrierError:
                self._message("Oh snap, another device failed, aborting!", False, 100.0)
                return False
            return True
        except UnwrapError as ex:
            self._message(f"Failed to enter UF2 Bootloader: {str(ex)}", False)
            self.uf2_barrier.abort()
            return False

    def flash_firmware(
        self,
        uf2_fname: str | pathlib.Path,
        processor_type: FreeWiliProcessorType,
        delay_sec: int | float = 0.0,
        index: int = 0,
    ) -> bool:
        delay_sec *= 2
        assert isinstance(processor_type, FreeWiliProcessorType)
        if isinstance(uf2_fname, str):
            uf2_fname = pathlib.Path(uf2_fname)

        if not uf2_fname.exists():
            self._message(f"{uf2_fname} isn't valid", False, 100.0)
            return False
        if not self.enter_uf2(index, processor_type):
            self._message(f"Failed to enter UF2 bootloader on {processor_type.name}", False, 100.0)
            return False

        try:
            self.bl_barrier.wait(90.0)
        except threading.BrokenBarrierError:
            self._message("Oh snap, another device failed, aborting!", False, 100.0)
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
            self._message("Failed to find drive path", False, 100)
            return False
        self._message(f"{processor_type.name} Uploading {uf2_fname.name} to {path}...", True, -1)

        try:
            self.bl_barrier.wait(90.0)
        except threading.BrokenBarrierError:
            self._message("Oh snap, another device failed, aborting!", False, 100.0)
            return False
        # update our destination path with the filename
        path = path / uf2_fname.name
        try:
            fsize_bytes = uf2_fname.stat().st_size
            start = time.time()
            written_bytes = 0
            last_written_bytes = 0
            last_update = start
            read_size = 4096 * 10
            with open(str(uf2_fname), "rb") as fsrc, open(str(path), "wb") as fdst:
                while True:
                    buf = fsrc.read(read_size)  # Read 4096*10 bytes at a time
                    if not buf:
                        break
                    written_bytes += len(buf)
                    # Randomize the end so all the drivers don't populate at the same time
                    if written_bytes >= fsize_bytes:
                        self._message("Waiting...", True, 98)
                        try:
                            # Display takes about 170 seconds to write. Timeout on the devil.
                            max_wait = 400
                            elapsed = time.time() - start
                            if elapsed >= max_wait:
                                elapsed = max_wait
                            self.bl_barrier.wait(max_wait - elapsed)
                        except threading.BrokenBarrierError:
                            self._message("Oh snap, another device failed, aborting!", False, 100.0)
                            return False
                        #self._message(f"Finalizing in {delay_sec} seconds...", True, 99)
                        #time.sleep(delay_sec)
                    write_attempts = 6
                    while write_attempts > 0:
                        try:
                            fdst.write(buf)
                            break
                        except OSError as ex:
                            write_attempts -= 1
                            if write_attempts <= 0:
                                self._message(f"Failed to write to {path}: {str(ex)}", False, 100.0)
                                return False
                            self._message(f"Retrying write to {path} ({write_attempts})", True, 10)
                            time.sleep(0.5)
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
                            f"{processor_type.name} {written_bytes / 1000:.0f}KB of {fsize_bytes / 1000:.0f}KB...",
                            True,
                            (written_bytes / fsize_bytes) * 100.0,
                        )
                        last_update = time.time()
                        last_written_bytes = written_bytes
                fdst.flush()
            end = time.time()
            self._message(
                f"Complete: {processor_type.name} {written_bytes / 1000:.1f}KB in {end - start:.1f} seconds...",
                True,
                100.0,
            )
            try:
                self.bl_barrier.wait(30.0)
            except threading.BrokenBarrierError:
                self._message("Oh snap, another device failed, aborting!", False, 100.0)
                return False
            if not self._wait_for_device(
                (USBDeviceType.Serial, USBDeviceType.SerialMain, USBDeviceType.SerialDisplay),
                processor_type,
                delay_sec=6.0,
            ):
                self._message("Device no longer exists", False, 100.0)
                return False
            self._message(
                f"Complete: {processor_type.name} {written_bytes / 1000:.1f}KB in {end - start:.1f} seconds...",
                True,
                100.0,
            )
            try:
                self.bl_barrier.wait(30.0)
            except threading.BrokenBarrierError:
                self._message("Oh snap, another device failed, aborting!", False, 100.0)
                return False
            return True
        except Exception as ex:
            import traceback
            exception_type = type(ex).__name__
            exception_message = str(ex) if str(ex) else "No message"
            traceback_str = traceback.format_exc()

            self._message(
                f"Exception: {exception_type}: {exception_message}",
                False,
                100.0
            )
            # Print full traceback for debugging
            print(f"Full traceback for {exception_type}:")
            print(traceback_str)
        return False
