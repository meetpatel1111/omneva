"""Queue Manager — Background job processing with QThread workers."""

import uuid
from PySide6.QtCore import QObject, QThread, Signal

from src.core.ffmpeg_service import FFmpegService, TranscodeJob
from .logger import get_logger
from .queue_persistence import QueuePersistence
from .post_encode_actions import PostEncodeActions


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
        self.logger = get_logger('queue_manager')
        self.ffmpeg = ffmpeg_service or FFmpegService()
        self.max_concurrent = max_concurrent

        self._jobs: dict[str, TranscodeJob] = {}
        self._pending: list[str] = []
        self._active_threads: dict[str, QThread] = {}
        self._active_workers: dict[str, TranscodeWorker] = {}
        
        # Initialize queue persistence and post-encode actions
        self.persistence = QueuePersistence()
        self.post_encode_actions = PostEncodeActions()
        self._load_pending_jobs()
        self._post_encode_settings = {}  # Will be updated from UI

    def _load_pending_jobs(self):
        """Load pending jobs from persistence database."""
        try:
            pending_jobs = self.persistence.load_pending_jobs()
            for job in pending_jobs:
                self._jobs[job.id] = job
                if job.status == "pending":
                    self._pending.append(job.id)
                elif job.status == "running":
                    # Reset running jobs to pending on restart
                    job.status = "pending"
                    self._pending.append(job.id)
                    self.persistence.update_job_status(job.id, "pending")
                
                self.logger.info(f"Loaded {len(pending_jobs)} jobs from persistence")
                
        except Exception as e:
            self.logger.error(f"Failed to load pending jobs: {e}")

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
        
        # Save job to persistence
        self.persistence.save_job(job)
        
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
            self.persistence.update_job_status(job_id, "cancelled")
        elif job.status == "running":
            self.ffmpeg.cancel(job_id)
            job.status = "cancelled"
            self.persistence.update_job_status(job_id, "cancelled")
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
        self.logger.debug(f"Processing next job. Pending: {len(self._pending)}, Active: {len(self._active_threads)}")
        while self._pending and len(self._active_threads) < self.max_concurrent:
            job_id = self._pending.pop(0)
            job = self._jobs.get(job_id)
            if not job:
                continue

            self._start_job(job)

    def _start_job(self, job: TranscodeJob):
        """Start a job in a new QThread."""
        self.logger.debug(f"Starting job {job.id}")
        
        # Update job status to running
        job.status = "running"
        self.persistence.update_job_status(job.id, "running")
        
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
        self.logger.debug(f"Thread started for job {job.id}")

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
            self.persistence.update_job_status(job_id, "completed", 100.0)
        self.job_completed.emit(job_id)
        self._process_next()

        if not self._pending and not self._active_threads:
            self.queue_empty.emit()
            # Check for post-encode actions when queue becomes empty
            self._check_and_execute_post_encode_actions()

    def _on_failed(self, job_id: str, error: str):
        job = self._jobs.get(job_id)
        if job:
            job.status = "failed"
            job.error = error
            self.persistence.update_job_status(job_id, "failed", error=error)
        self.job_failed.emit(job_id, error)
        self._process_next()

    def _cleanup_thread(self, job_id: str):
        self._active_threads.pop(job_id, None)
        self._active_workers.pop(job_id, None)

    def get_job_history(self, limit: int = 100) -> list[dict]:
        """Get job history from persistence."""
        return self.persistence.get_job_history(limit)
    
    def get_queue_statistics(self) -> dict:
        """Get queue statistics from persistence."""
        return self.persistence.get_statistics()
    
    def clear_old_jobs(self, older_than_days: int = 30) -> int:
        """Clear old completed jobs from persistence."""
        return self.persistence.clear_completed_jobs(older_than_days)

    def set_post_encode_actions(self, actions: dict):
        """Update post-encode action settings from UI."""
        self._post_encode_settings = actions
        self.logger.debug(f"Post-encode actions updated: {actions}")

    def _check_and_execute_post_encode_actions(self):
        """Check if queue is empty and execute post-encode actions if configured."""
        if not self._pending and not self._active_threads and self._post_encode_settings:
            # Queue is empty, check if any post-encode actions are enabled
            if self._post_encode_settings.get("sound", False) or self._post_encode_settings.get("shutdown", False):
                self.logger.info("Queue empty, executing post-encode actions")
                self.post_encode_actions.execute_actions(self._post_encode_settings)
