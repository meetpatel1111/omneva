"""Queue Persistence - SQLite database for job queue persistence."""

import os
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import asdict

from src.core.ffmpeg_service import TranscodeJob
from .logger import get_logger


class QueuePersistence:
    """SQLite database for persisting transcode jobs across application restarts."""
    
    def __init__(self, db_path: str = None):
        self.logger = get_logger('queue_persistence')
        
        # Default database path in user data directory
        if db_path is None:
            from PySide6.QtCore import QStandardPaths
            data_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "omneva_queue.db")
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize the SQLite database with required tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS jobs (
                        id TEXT PRIMARY KEY,
                        input_path TEXT NOT NULL,
                        output_path TEXT NOT NULL,
                        options TEXT,  -- JSON string
                        status TEXT DEFAULT 'pending',
                        progress REAL DEFAULT 0.0,
                        error TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        completed_at TIMESTAMP NULL
                    )
                """)
                
                # Create index for faster queries
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_jobs_status 
                    ON jobs(status)
                """)
                
                conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_jobs_created_at 
                    ON jobs(created_at)
                """)
                
                conn.commit()
                self.logger.info(f"Queue persistence database initialized: {self.db_path}")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise
    
    def save_job(self, job: TranscodeJob) -> bool:
        """Save or update a job in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Convert options dict to JSON string
                options_json = json.dumps(job.options) if job.options else None
                
                conn.execute("""
                    INSERT OR REPLACE INTO jobs 
                    (id, input_path, output_path, options, status, progress, error, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    job.id, job.input_path, job.output_path, 
                    options_json, job.status, job.progress, job.error
                ))
                
                conn.commit()
                self.logger.debug(f"Saved job {job.id} to database")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to save job {job.id}: {e}")
            return False
    
    def update_job_status(self, job_id: str, status: str, progress: float = None, error: str = None) -> bool:
        """Update job status, progress, and/or error."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                updates = ["status = ?", "updated_at = CURRENT_TIMESTAMP"]
                params = [status]
                
                if progress is not None:
                    updates.append("progress = ?")
                    params.append(progress)
                
                if error is not None:
                    updates.append("error = ?")
                    params.append(error)
                
                if status == "completed":
                    updates.append("completed_at = CURRENT_TIMESTAMP")
                
                params.append(job_id)
                
                conn.execute(f"""
                    UPDATE jobs 
                    SET {', '.join(updates)}
                    WHERE id = ?
                """, params)
                
                conn.commit()
                self.logger.debug(f"Updated job {job_id} status to {status}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to update job {job_id}: {e}")
            return False
    
    def load_pending_jobs(self) -> List[TranscodeJob]:
        """Load all pending jobs from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, input_path, output_path, options, status, progress, error
                    FROM jobs 
                    WHERE status IN ('pending', 'running')
                    ORDER BY created_at ASC
                """)
                
                jobs = []
                for row in cursor.fetchall():
                    job_id, input_path, output_path, options_json, status, progress, error = row
                    
                    # Parse options from JSON
                    options = json.loads(options_json) if options_json else {}
                    
                    job = TranscodeJob(
                        id=job_id,
                        input_path=input_path,
                        output_path=output_path,
                        options=options,
                        progress=progress or 0.0,
                        status=status,
                        error=error or ""
                    )
                    
                    jobs.append(job)
                
                self.logger.info(f"Loaded {len(jobs)} pending jobs from database")
                return jobs
                
        except Exception as e:
            self.logger.error(f"Failed to load pending jobs: {e}")
            return []
    
    def get_job_history(self, limit: int = 100) -> List[Dict]:
        """Get job history (completed, failed, cancelled jobs)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, input_path, output_path, status, progress, error, 
                           created_at, updated_at, completed_at
                    FROM jobs 
                    WHERE status NOT IN ('pending', 'running')
                    ORDER BY updated_at DESC
                    LIMIT ?
                """, (limit,))
                
                history = []
                for row in cursor.fetchall():
                    (job_id, input_path, output_path, status, progress, error,
                     created_at, updated_at, completed_at) = row
                    
                    history.append({
                        'id': job_id,
                        'input_path': input_path,
                        'output_path': output_path,
                        'status': status,
                        'progress': progress,
                        'error': error,
                        'created_at': created_at,
                        'updated_at': updated_at,
                        'completed_at': completed_at
                    })
                
                return history
                
        except Exception as e:
            self.logger.error(f"Failed to get job history: {e}")
            return []
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
                conn.commit()
                
                if cursor.rowcount > 0:
                    self.logger.debug(f"Deleted job {job_id} from database")
                    return True
                else:
                    self.logger.warning(f"Job {job_id} not found in database")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Failed to delete job {job_id}: {e}")
            return False
    
    def clear_completed_jobs(self, older_than_days: int = 30) -> int:
        """Clear completed jobs older than specified days."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    DELETE FROM jobs 
                    WHERE status IN ('completed', 'failed', 'cancelled')
                    AND updated_at < datetime('now', '-{} days')
                """.format(older_than_days))
                
                conn.commit()
                deleted_count = cursor.rowcount
                self.logger.info(f"Cleared {deleted_count} old completed jobs")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Failed to clear completed jobs: {e}")
            return 0
    
    def get_statistics(self) -> Dict:
        """Get queue statistics."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        status,
                        COUNT(*) as count
                    FROM jobs 
                    GROUP BY status
                """)
                
                stats = {}
                for status, count in cursor.fetchall():
                    stats[status] = count
                
                # Get total jobs
                cursor = conn.execute("SELECT COUNT(*) FROM jobs")
                stats['total'] = cursor.fetchone()[0]
                
                return stats
                
        except Exception as e:
            self.logger.error(f"Failed to get statistics: {e}")
            return {'total': 0}
