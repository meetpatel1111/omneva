"""Centralized logging configuration for Omneva."""

import logging
import logging.handlers
import os
from pathlib import Path


class OmnevaLogger:
    """Centralized logger with file rotation and console output."""
    
    def __init__(self):
        self.logger = logging.getLogger('omneva')
        self.logger.setLevel(logging.DEBUG)
        
        # Prevent duplicate handlers
        if self.logger.handlers:
            return
            
        # Create logs directory
        log_dir = Path.home() / '.omneva' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # File handler with rotation (10MB max, keep 5 files)
        log_file = log_dir / 'omneva.log'
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, 
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def get_logger(self, name: str = None) -> logging.Logger:
        """Get a logger instance with optional name."""
        if name:
            return self.logger.getChild(name)
        return self.logger


# Global logger instance
_logger_instance = OmnevaLogger()

def get_logger(name: str = None) -> logging.Logger:
    """Get the Omneva logger instance."""
    return _logger_instance.get_logger(name)
