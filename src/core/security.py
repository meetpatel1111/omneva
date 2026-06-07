"""Security utilities for validating subprocess inputs and preventing injection attacks."""

import os
import re
from typing import List, Union
from pathlib import Path

from .logger import get_logger


class SecurityValidator:
    """Validates and sanitizes inputs to prevent subprocess injection attacks."""
    
    def __init__(self):
        self.logger = get_logger('security')
        
        # Whitelisted characters for file paths
        self._safe_path_chars = re.compile(r'^[a-zA-Z0-9._\-/\\:]+$')
        
        # Dangerous patterns that could indicate injection
        self._dangerous_patterns = [
            r'[;&|`$()]',  # Command injection characters
            r'\.\.',       # Directory traversal
            r'^\s*rm\b',   # rm command
            r'^\s*del\b',  # del command
            r'^\s*format\b',  # format command
            r'^\s*fdisk\b',   # fdisk command
            r'^\s*mkfs\b',    # mkfs command
            r'<.*>',       # Redirect operators
            r'>>.*',       # Append redirect
        ]
        
        self._dangerous_regex = re.compile('|'.join(self._dangerous_patterns), re.IGNORECASE)
    
    def validate_file_path(self, file_path: Union[str, Path]) -> bool:
        """
        Validate that a file path is safe for subprocess use.
        
        Args:
            file_path: The file path to validate
            
        Returns:
            True if safe, False otherwise
        """
        if not file_path:
            return False
            
        file_path = str(file_path)
        
        # Check for dangerous patterns
        if self._dangerous_regex.search(file_path):
            self.logger.warning(f"Dangerous pattern detected in file path: {file_path}")
            return False
        
        # Check for directory traversal attempts
        if '..' in file_path:
            self.logger.warning(f"Directory traversal attempt detected: {file_path}")
            return False
        
        # Ensure the path doesn't contain command injection characters
        if any(char in file_path for char in [';', '&', '|', '`', '$', '(', ')']):
            self.logger.warning(f"Command injection characters detected in path: {file_path}")
            return False
        
        # Resolve the path and ensure it doesn't go outside expected directories
        try:
            resolved_path = Path(file_path).resolve()
            
            # On Windows, also check for UNC paths that could be dangerous
            if os.name == 'nt' and str(resolved_path).startswith('\\\\'):
                self.logger.warning(f"UNC path detected, may be unsafe: {resolved_path}")
                return False
                
        except (OSError, ValueError) as e:
            self.logger.warning(f"Invalid path detected: {file_path} - {e}")
            return False
        
        return True
    
    def validate_command_args(self, args: List[str]) -> List[str]:
        """
        Validate and sanitize command arguments.
        
        Args:
            args: List of command arguments
            
        Returns:
            Sanitized list of arguments (empty list if validation fails)
        """
        if not args:
            return []
        
        sanitized = []
        
        for i, arg in enumerate(args):
            if not arg:
                continue
                
            # Skip empty arguments
            if not arg.strip():
                continue
            
            # Check each argument for dangerous patterns
            if self._dangerous_regex.search(arg):
                self.logger.warning(f"Dangerous pattern detected in argument {i}: {arg}")
                return []  # Fail fast on any dangerous pattern
            
            # For file path arguments, do additional validation
            if i > 0 and args[0] in ['ffmpeg', 'ffprobe', 'hdiutil', 'cp']:
                if not self.validate_file_path(arg):
                    self.logger.warning(f"Invalid file path in argument {i}: {arg}")
                    return []
            
            sanitized.append(arg)
        
        return sanitized
    
    def safe_subprocess_run(self, cmd: List[str], **kwargs):
        """
        Safely run a subprocess with validated command.
        
        Args:
            cmd: Command and arguments as list
            **kwargs: Additional arguments for subprocess.run()
            
        Returns:
            subprocess result or None if validation fails
        """
        import subprocess
        
        # Validate command
        sanitized_cmd = self.validate_command_args(cmd)
        if not sanitized_cmd:
            self.logger.error(f"Command validation failed: {cmd}")
            return None
        
        try:
            self.logger.debug(f"Running validated command: {' '.join(sanitized_cmd)}")
            return subprocess.run(sanitized_cmd, **kwargs)
        except Exception as e:
            self.logger.error(f"Subprocess execution failed: {e}")
            return None
    
    def safe_subprocess_popen(self, cmd: List[str], **kwargs):
        """
        Safely create a subprocess.Popen with validated command.
        
        Args:
            cmd: Command and arguments as list
            **kwargs: Additional arguments for subprocess.Popen()
            
        Returns:
            subprocess.Popen object or None if validation fails
        """
        import subprocess
        
        # Validate command
        sanitized_cmd = self.validate_command_args(cmd)
        if not sanitized_cmd:
            self.logger.error(f"Command validation failed: {cmd}")
            return None
        
        try:
            self.logger.debug(f"Creating validated process: {' '.join(sanitized_cmd)}")
            return subprocess.Popen(sanitized_cmd, **kwargs)
        except Exception as e:
            self.logger.error(f"Subprocess creation failed: {e}")
            return None


# Global security validator instance
_security_validator = SecurityValidator()

def get_security_validator() -> SecurityValidator:
    """Get the global security validator instance."""
    return _security_validator

def validate_file_path(file_path: Union[str, Path]) -> bool:
    """Convenience function to validate a file path."""
    return _security_validator.validate_file_path(file_path)

def safe_subprocess_run(cmd: List[str], **kwargs):
    """Convenience function to safely run a subprocess."""
    return _security_validator.safe_subprocess_run(cmd, **kwargs)

def safe_subprocess_popen(cmd: List[str], **kwargs):
    """Convenience function to safely create a subprocess.Popen."""
    return _security_validator.safe_subprocess_popen(cmd, **kwargs)
