"""
Background thread management for PDF Toolbox.
Prevents UI freezing during long PDF operations.
"""

from PySide6.QtCore import QThread, Signal, QObject
from typing import Callable, Any


class WorkerSignals(QObject):
    """Defines signals available from a running worker thread."""

    finished = Signal(object)  # Result data
    error = Signal(tuple)      # (exception_type, value, traceback)
    progress = Signal(int)     # Progress percentage 0-100
    status = Signal(str)       # Status message


class WorkerThread(QThread):
    """
    Worker thread for running long operations without freezing the UI.

    Usage:
        worker = WorkerThread(target=my_function, args=(arg1, arg2))
        worker.signals.finished.connect(on_finished)
        worker.signals.progress.connect(on_progress)
        worker.start()
    """

    def __init__(
        self,
        target: Callable,
        args: tuple = (),
        kwargs: dict = None,
        parent: QObject = None,
    ):
        super().__init__(parent)
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}
        self.signals = WorkerSignals()
        self._is_cancelled = False

    def run(self):
        """Execute the target function in background thread."""
        try:
            # Inject signals into kwargs so target can report progress
            self.kwargs["_signals"] = self.signals
            result = self.target(*self.args, **self.kwargs)
            if not self._is_cancelled:
                self.signals.finished.emit(result)
        except Exception as e:
            import traceback
            self.signals.error.emit((type(e), e, traceback.format_exc()))

    def cancel(self):
        """Request cancellation of the running operation."""
        self._is_cancelled = True
        self.signals.status.emit("正在取消...")


class ThreadManager:
    """
    Manages multiple worker threads with lifecycle control.

    Ensures threads are properly cleaned up when no longer needed.
    """

    def __init__(self):
        self._threads: list[WorkerThread] = []

    def run(
        self,
        target: Callable,
        args: tuple = (),
        kwargs: dict = None,
        on_finished: Callable = None,
        on_error: Callable = None,
        on_progress: Callable = None,
        on_status: Callable = None,
    ) -> WorkerThread:
        """
        Create and start a worker thread with optional callbacks.

        Returns the WorkerThread instance for further control.
        """
        worker = WorkerThread(target, args, kwargs)

        if on_finished:
            worker.signals.finished.connect(on_finished)
        if on_error:
            worker.signals.error.connect(on_error)
        if on_progress:
            worker.signals.progress.connect(on_progress)
        if on_status:
            worker.signals.status.connect(on_status)

        # Clean up thread when done
        worker.finished.connect(lambda: self._cleanup(worker))

        self._threads.append(worker)
        worker.start()
        return worker

    def _cleanup(self, worker: WorkerThread):
        """Remove finished thread from tracking list."""
        if worker in self._threads:
            self._threads.remove(worker)
            worker.deleteLater()

    def cancel_all(self):
        """Cancel all running threads."""
        for worker in self._threads[:]:
            worker.cancel()

    @property
    def active_count(self) -> int:
        """Number of currently running threads."""
        return len([t for t in self._threads if t.isRunning()])

