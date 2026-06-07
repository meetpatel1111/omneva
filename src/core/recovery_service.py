"""Recovery Service - Handles crash recovery and autosave functionality."""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

from .logger import get_logger


@dataclass
class RecoveryState:
    """Represents the application state for recovery."""
    timestamp: float
    session_id: str
    current_file: Optional[str] = None
    current_position: float = 0.0
    current_volume: int = 100
    current_page: int = 0  # Main window page index
    recent_files: list = None
    transcoder_jobs: list = None
    queue_jobs: list = None
    
    def __post_init__(self):
        if self.recent_files is None:
            self.recent_files = []
        if self.transcoder_jobs is None:
            self.transcoder_jobs = []
        if self.queue_jobs is None:
            self.queue_jobs = []


class RecoveryService:
    """Manages application state recovery and autosave."""
    
    def __init__(self):
        self.logger = get_logger('recovery')
        self.session_id = self._generate_session_id()
        self.last_autosave_time = 0
        self.autosave_interval = 300  # 5 minutes in seconds
        self._recovery_file = None
        self._setup_recovery_file()
        
    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        return f"session_{int(time.time())}_{os.getpid()}"
    
    def _setup_recovery_file(self):
        """Setup the recovery file path."""
        try:
            # Get the app data directory from storage
            app_data_dir = Path.home() / '.omneva'
            app_data_dir.mkdir(parents=True, exist_ok=True)
            
            self._recovery_file = app_data_dir / 'recovery.json'
            self.logger.debug(f"Recovery file: {self._recovery_file}")
        except Exception as e:
            self.logger.error(f"Failed to setup recovery file: {e}")
            self._recovery_file = None
    
    def save_state(self, state: RecoveryState) -> bool:
        """Save the current application state."""
        if not self._recovery_file:
            return False
            
        try:
            # Add session ID and timestamp if not present
            if not state.session_id:
                state.session_id = self.session_id
            if not state.timestamp:
                state.timestamp = time.time()
            
            # Convert to dict and save
            state_dict = asdict(state)
            
            # Create backup of existing file
            backup_file = self._recovery_file.with_suffix('.json.bak')
            if self._recovery_file.exists():
                backup_file.write_bytes(self._recovery_file.read_bytes())
            
            # Write new state
            with open(self._recovery_file, 'w', encoding='utf-8') as f:
                json.dump(state_dict, f, indent=2, ensure_ascii=False)
            
            self.last_autosave_time = time.time()
            self.logger.debug(f"State saved to {self._recovery_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
            return False
    
    def load_state(self) -> Optional[RecoveryState]:
        """Load the last saved application state."""
        if not self._recovery_file or not self._recovery_file.exists():
            return None
            
        try:
            with open(self._recovery_file, 'r', encoding='utf-8') as f:
                state_dict = json.load(f)
            
            # Convert dict to RecoveryState
            state = RecoveryState(**state_dict)
            
            # Check if the recovery state is recent (within last 24 hours)
            current_time = time.time()
            if current_time - state.timestamp > 86400:  # 24 hours
                self.logger.info("Recovery state is older than 24 hours, ignoring")
                return None
            
            self.logger.info(f"Loaded recovery state from session {state.session_id}")
            return state
            
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")
            return None
    
    def should_autosave(self) -> bool:
        """Check if autosave should be performed."""
        current_time = time.time()
        return current_time - self.last_autosave_time >= self.autosave_interval
    
    def autosave_if_needed(self, current_state: Dict[str, Any]) -> bool:
        """Perform autosave if needed."""
        if not self.should_autosave():
            return False
            
        # Convert current state to RecoveryState
        recovery_state = RecoveryState(
            timestamp=time.time(),
            session_id=self.session_id,
            current_file=current_state.get('current_file'),
            current_position=current_state.get('current_position', 0.0),
            current_volume=current_state.get('current_volume', 100),
            current_page=current_state.get('current_page', 0),
            recent_files=current_state.get('recent_files', []),
            transcoder_jobs=current_state.get('transcoder_jobs', []),
            queue_jobs=current_state.get('queue_jobs', [])
        )
        
        return self.save_state(recovery_state)
    
    def clear_recovery_state(self):
        """Clear the recovery state file."""
        if not self._recovery_file:
            return
            
        try:
            if self._recovery_file.exists():
                self._recovery_file.unlink()
                self.logger.info("Recovery state cleared")
                
            # Also remove backup file
            backup_file = self._recovery_file.with_suffix('.json.bak')
            if backup_file.exists():
                backup_file.unlink()
                
        except Exception as e:
            self.logger.error(f"Failed to clear recovery state: {e}")
    
    def check_for_crash_recovery(self) -> Optional[RecoveryState]:
        """Check if there's a recovery state from a previous crash."""
        state = self.load_state()
        if state:
            # Generate a new session ID for this recovery session
            self.session_id = self._generate_session_id()
            return state
        return None
    
    def get_recovery_info(self) -> Dict[str, Any]:
        """Get information about available recovery state."""
        if not self._recovery_file or not self._recovery_file.exists():
            return {"available": False}
            
        try:
            state = self.load_state()
            if state:
                return {
                    "available": True,
                    "session_id": state.session_id,
                    "timestamp": state.timestamp,
                    "date": datetime.fromtimestamp(state.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                    "current_file": state.current_file,
                    "has_recent_files": len(state.recent_files) > 0,
                    "has_jobs": len(state.transcoder_jobs) > 0 or len(state.queue_jobs) > 0
                }
        except Exception as e:
            self.logger.error(f"Failed to get recovery info: {e}")
            
        return {"available": False}


# Global recovery service instance
_recovery_service = RecoveryService()

def get_recovery_service() -> RecoveryService:
    """Get the global recovery service instance."""
    return _recovery_service

def save_app_state(state: Dict[str, Any]) -> bool:
    """Convenience function to save application state."""
    return _recovery_service.autosave_if_needed(state)

def check_crash_recovery() -> Optional[RecoveryState]:
    """Convenience function to check for crash recovery."""
    return _recovery_service.check_for_crash_recovery()

def clear_recovery_state():
    """Convenience function to clear recovery state."""
    _recovery_service.clear_recovery_state()
