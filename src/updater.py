from typing import Any, Self
from PySide6 import QtCore, QtGui, QtWidgets
import enum
import dataclasses
from queue import Empty, Queue

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