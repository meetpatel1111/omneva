"""Thread Manager - Safely manages QThread lifecycle and cleanup."""

from typing import Dict, Optional
from PySide6.QtCore import QObject, QThread
from src.core.logger import get_logger

class ThreadManager:
    """Manages background QThreads to prevent 'destroyed while running' crashes."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
        
    def _init(self):
        self.logger = get_logger('thread_manager')
        # We need to keep a reference to the worker too, as sometimes moving
        # to thread requires the worker to be kept alive in Python.
        self._threads: Dict[int, QThread] = {}
        self._workers: Dict[int, QObject] = {}
        self._next_id = 1
        
    def start_worker(self, worker: QObject, thread: Optional[QThread] = None) -> QThread:
        """
        Move a worker to a QThread, track them, and start the thread.
        Returns the managed QThread.
        """
        if thread is None:
            thread = QThread()
            
        worker.moveToThread(thread)
        
        thread_id = self._next_id
        self._next_id += 1
        
        self._threads[thread_id] = thread
        self._workers[thread_id] = worker
        
        # When thread finishes, remove it from tracking
        # Use a lambda that captures thread_id to ensure we delete the right one
        thread.finished.connect(lambda tid=thread_id: self._remove_thread(tid))
        
        # Also clean up worker when thread finishes
        thread.finished.connect(worker.deleteLater)
        # And delete the thread object itself when finished
        thread.finished.connect(thread.deleteLater)
        
        self.logger.debug(f"Starting thread {thread_id} for worker {type(worker).__name__}")
        thread.start()
        
        return thread
        
    def _remove_thread(self, thread_id: int):
        """Remove a thread from tracking once it finishes naturally."""
        if thread_id in self._threads:
            self.logger.debug(f"Thread {thread_id} finished naturally, removing from tracking")
            del self._threads[thread_id]
        if thread_id in self._workers:
            del self._workers[thread_id]
            
    def cleanup(self, timeout_ms: int = 2000):
        """
        Gracefully stop and wait for all tracked threads.
        Should be called during application shutdown.
        """
        thread_count = len(self._threads)
        if thread_count == 0:
            return
            
        self.logger.info(f"Cleaning up {thread_count} active threads...")
        
        # 1. Ask workers to stop if they support it
        for worker in self._workers.values():
            if hasattr(worker, 'stop'):
                try:
                    worker.stop()
                except Exception as e:
                    self.logger.error(f"Error calling stop() on worker: {e}")
                    
        # 2. Tell all threads to quit their event loops
        for thread in self._threads.values():
            if thread.isRunning():
                thread.quit()
                
        # 3. Wait for threads to finish
        for thread_id, thread in list(self._threads.items()):
            if thread.isRunning():
                self.logger.debug(f"Waiting for thread {thread_id}...")
                if not thread.wait(timeout_ms):
                    self.logger.warning(f"Thread {thread_id} did not finish within timeout, terminating!")
                    # Terminate is dangerous but required if the app is closing
                    # and the thread refuses to yield
                    thread.terminate()
                    thread.wait(500)
                    
        self._threads.clear()
        self._workers.clear()
        self.logger.info("Thread cleanup complete")

# Expose a global instance for easy access
thread_manager = ThreadManager()
