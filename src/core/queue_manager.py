"""Queue Manager — Background job processing with QThread workers."""

import uuid
from PySide6.QtCore import QObject, QThread, Signal

from src.core.ffmpeg_service import FFmpegService, TranscodeJob


class TranscodeWorker(QObject):
    """Worker that runs a single transcode job in a QThread."""

    progress = Signal(str, float, str)   # job_id, percent, speed
    completed = Signal(str)              # job_id
    failed = Signal(str, str)            # job_id, error

    def __init__(self, ffmpeg: FFmpegService, job: TranscodeJob):
        super().__init__()
        self.ffmpeg = ffmpeg
        self.job = job

    def run(self):
        """Execute the job (called from QThread)."""
        def on_progress(percent, speed):
            self.progress.emit(self.job.id, percent, speed)

        result = self.ffmpeg.transcode(self.job, on_progress)

        if result.status == "completed":
            self.completed.emit(self.job.id)
        else:
            self.failed.emit(self.job.id, result.error)


class QueueManager(QObject):
    """Manages a queue of transcode/conversion jobs with QThread workers."""

    # Signals
    job_added = Signal(str)              # job_id
    job_started = Signal(str)            # job_id
    job_progress = Signal(str, float, str)  # job_id, percent, speed
    job_completed = Signal(str)          # job_id
    job_failed = Signal(str, str)        # job_id, error
    queue_empty = Signal()

    def __init__(self, ffmpeg_service: FFmpegService = None, max_concurrent: int = 1):
        super().__init__()
        self.ffmpeg = ffmpeg_service or FFmpegService()
        self.max_concurrent = max_concurrent

        self._jobs: dict[str, TranscodeJob] = {}
        self._pending: list[str] = []
        self._active_threads: dict[str, QThread] = {}
        self._active_workers: dict[str, TranscodeWorker] = {}

    def add_job(
        self,
        input_path: str,
        output_path: str,
        options: dict = None,
        duration: float = 0,
    ) -> str:
        """Add a job to the queue. Returns job_id."""
        job_id = str(uuid.uuid4())[:8]
        opts = options or {}
        opts["duration"] = duration

        job = TranscodeJob(
            id=job_id,
            input_path=input_path,
            output_path=output_path,
            options=opts,
        )
        self._jobs[job_id] = job
        self._pending.append(job_id)
        self.job_added.emit(job_id)

        self._process_next()
        return job_id

    def get_job(self, job_id: str) -> TranscodeJob | None:
        return self._jobs.get(job_id)

    def get_all_jobs(self) -> list[TranscodeJob]:
        return list(self._jobs.values())

    def cancel_job(self, job_id: str):
        """Cancel a pending or running job."""
        job = self._jobs.get(job_id)
        if not job:
            return

        if job.status == "pending" and job_id in self._pending:
            self._pending.remove(job_id)
            job.status = "cancelled"
        elif job.status == "running":
            self.ffmpeg.cancel(job_id)
            job.status = "cancelled"
            self._cleanup_thread(job_id)

    def clear_completed(self):
        """Remove completed/failed/cancelled jobs."""
        to_remove = [
            jid for jid, job in self._jobs.items()
            if job.status in ("completed", "failed", "cancelled")
        ]
        for jid in to_remove:
            del self._jobs[jid]

    def _process_next(self):
        """Start next pending job if we have capacity."""
        print(f"DEBUG: Processing next job. Pending: {len(self._pending)}, Active: {len(self._active_threads)}")
        while self._pending and len(self._active_threads) < self.max_concurrent:
            job_id = self._pending.pop(0)
            job = self._jobs.get(job_id)
            if not job:
                continue

            self._start_job(job)

    def _start_job(self, job: TranscodeJob):
        """Start a job in a new QThread."""
        print(f"DEBUG: Starting job {job.id}")
        thread = QThread()
        worker = TranscodeWorker(self.ffmpeg, job)
        worker.moveToThread(thread)

        # Connect signals
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_progress)
        worker.completed.connect(self._on_completed)
        worker.failed.connect(self._on_failed)

        # Cleanup on finish
        worker.completed.connect(lambda jid: self._cleanup_thread(jid))
        worker.failed.connect(lambda jid, _: self._cleanup_thread(jid))
        worker.completed.connect(thread.quit)
        worker.failed.connect(lambda *_: thread.quit())
        thread.finished.connect(thread.deleteLater)

        self._active_threads[job.id] = thread
        self._active_workers[job.id] = worker
        
        # Kepp reference to avoid GC? (It's in the dict, so it's fine)

        job.status = "running"
        self.job_started.emit(job.id)
        thread.start()
        print(f"DEBUG: Thread started for job {job.id}")

    def _on_progress(self, job_id: str, percent: float, speed: str):
        job = self._jobs.get(job_id)
        if job:
            job.progress = percent
        self.job_progress.emit(job_id, percent, speed)

    def _on_completed(self, job_id: str):
        job = self._jobs.get(job_id)
        if job:
            job.status = "completed"
            job.progress = 100.0
        self.job_completed.emit(job_id)
        self._process_next()

        if not self._pending and not self._active_threads:
            self.queue_empty.emit()

    def _on_failed(self, job_id: str, error: str):
        job = self._jobs.get(job_id)
        if job:
            job.status = "failed"
            job.error = error
        self.job_failed.emit(job_id, error)
        self._process_next()

    def _cleanup_thread(self, job_id: str):
        self._active_threads.pop(job_id, None)
        self._active_workers.pop(job_id, None)
