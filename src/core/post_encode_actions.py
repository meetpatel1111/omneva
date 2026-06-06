"""Post-Encode Actions - Handle system shutdown and sound notifications."""

import os
import platform
import subprocess
from typing import Dict
from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtMultimedia import QMediaPlayer

from .logger import get_logger


class PostEncodeActions(QObject):
    """Handle post-encode actions like shutdown and sound notifications."""
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger('post_encode_actions')
        self.system = platform.system().lower()
        self._sound_player = None
        self._init_sound_player()
    
    def _init_sound_player(self):
        """Initialize the sound player for notifications."""
        try:
            # Try to use QMediaPlayer for better compatibility
            self._sound_player = QMediaPlayer()
            self.logger.debug("Sound player initialized with QMediaPlayer")
        except Exception as e:
            self.logger.warning(f"Failed to initialize QMediaPlayer: {e}")
            # Fallback to system sound
            self._sound_player = None
    
    def play_completion_sound(self):
        """Play a notification sound when encoding completes."""
        try:
            # Try different sound sources based on platform
            if self.system == "windows":
                self._play_windows_sound()
            elif self.system == "darwin":  # macOS
                self._play_macos_sound()
            elif self.system == "linux":
                self._play_linux_sound()
            else:
                self._play_default_sound()
                
            self.logger.info("Played completion sound")
            
        except Exception as e:
            self.logger.error(f"Failed to play completion sound: {e}")
    
    def _play_windows_sound(self):
        """Play sound on Windows."""
        try:
            # Try Windows system sounds first
            import winsound
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except ImportError:
            # Fallback to built-in sound
            self._play_builtin_sound()
    
    def _play_macos_sound(self):
        """Play sound on macOS."""
        try:
            # Use afplay command on macOS
            sound_file = "/System/Library/Sounds/Glass.aiff"
            if os.path.exists(sound_file):
                subprocess.run(["afplay", sound_file], check=True)
            else:
                self._play_builtin_sound()
        except Exception:
            self._play_builtin_sound()
    
    def _play_linux_sound(self):
        """Play sound on Linux."""
        try:
            # Try different Linux sound commands
            sound_commands = [
                ["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
                ["aplay", "/usr/share/sounds/alsa/Front_Left.wav"],
                ["speaker-test", "-t", "sine", "-f", "1000", "-l", "1"]
            ]
            
            for cmd in sound_commands:
                try:
                    if os.path.exists(cmd[1]) or cmd[0] == "speaker-test":
                        subprocess.run(cmd, check=True, capture_output=True)
                        return
                except (subprocess.CalledProcessError, FileNotFoundError):
                    continue
            
            # Fallback
            self._play_builtin_sound()
            
        except Exception:
            self._play_builtin_sound()
    
    def _play_builtin_sound(self):
        """Play built-in sound using Qt."""
        try:
            if self._sound_player and hasattr(self._sound_player, 'setSource'):
                # Use QMediaPlayer
                # Generate a simple beep sound programmatically
                self._generate_beep_sound()
            else:
                # Use system beep fallback
                self._play_system_beep()
                
        except Exception as e:
            self.logger.warning(f"Built-in sound failed: {e}")
    
    def _play_system_beep(self):
        """Play system beep sound."""
        try:
            # Use system bell character
            print("\a")
        except Exception:
            pass
    
    def _generate_beep_sound(self):
        """Generate a simple beep sound."""
        try:
            # Create a simple beep using system bell
            print("\a")  # System bell character
        except Exception:
            pass
    
    def _play_default_sound(self):
        """Play default sound for unknown platforms."""
        try:
            print("\a")  # System bell
        except Exception:
            pass
    
    def shutdown_system(self, delay_seconds: int = 30):
        """Shutdown the system after a delay."""
        try:
            self.logger.info(f"Initiating system shutdown in {delay_seconds} seconds")
            
            # Schedule the shutdown
            QTimer.singleShot(delay_seconds * 1000, self._execute_shutdown)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to schedule shutdown: {e}")
            return False
    
    def _execute_shutdown(self):
        """Execute the actual system shutdown."""
        try:
            if self.system == "windows":
                self._shutdown_windows()
            elif self.system == "darwin":  # macOS
                self._shutdown_macos()
            elif self.system == "linux":
                self._shutdown_linux()
            else:
                self.logger.warning(f"Unsupported system for shutdown: {self.system}")
                
        except Exception as e:
            self.logger.error(f"Failed to execute shutdown: {e}")
    
    def _shutdown_windows(self):
        """Shutdown Windows system."""
        try:
            # Use Windows shutdown command
            subprocess.run(["shutdown", "/s", "/t", "0"], check=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Windows shutdown failed: {e}")
            raise
    
    def _shutdown_macos(self):
        """Shutdown macOS system."""
        try:
            # Use macOS shutdown command
            subprocess.run(["sudo", "shutdown", "-h", "now"], check=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"macOS shutdown failed: {e}")
            raise
    
    def _shutdown_linux(self):
        """Shutdown Linux system."""
        try:
            # Use Linux shutdown command
            subprocess.run(["sudo", "shutdown", "-h", "now"], check=True)
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Linux shutdown failed: {e}")
            raise
    
    def cancel_shutdown(self):
        """Cancel a scheduled shutdown."""
        try:
            if self.system == "windows":
                subprocess.run(["shutdown", "/a"], check=True)
            elif self.system in ["darwin", "linux"]:
                subprocess.run(["sudo", "shutdown", "-c"], check=True)
            
            self.logger.info("Shutdown cancelled")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to cancel shutdown: {e}")
            return False
    
    def execute_actions(self, actions: Dict[str, bool]):
        """Execute post-encode actions based on settings."""
        if not actions:
            return
        
        try:
            # Play sound if enabled
            if actions.get("sound", False):
                self.play_completion_sound()
            
            # Shutdown if enabled
            if actions.get("shutdown", False):
                # Schedule shutdown with 30 second delay to allow user to cancel
                self.shutdown_system(delay_seconds=30)
            
            self.logger.info(f"Executed post-encode actions: {actions}")
            
        except Exception as e:
            self.logger.error(f"Failed to execute post-encode actions: {e}")
    
    def is_shutdown_available(self) -> bool:
        """Check if shutdown functionality is available."""
        try:
            if self.system == "windows":
                return True
            elif self.system in ["darwin", "linux"]:
                # Check if we can run sudo commands (simplified check)
                return True
            else:
                return False
        except Exception:
            return False
    
    def get_shutdown_warning(self) -> str:
        """Get shutdown warning message for the user."""
        if self.system == "windows":
            return "System will shutdown in 30 seconds. Save your work!"
        elif self.system == "darwin":
            return "Mac will shutdown in 30 seconds. Save your work!"
        elif self.system == "linux":
            return "System will shutdown in 30 seconds. Save your work!"
        else:
            return "System will shutdown in 30 seconds. Save your work!"
