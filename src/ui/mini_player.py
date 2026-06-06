"""Mini Player / PiP Mode - Small floating widget with video and minimal controls."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFrame, QSizePolicy, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QRect
from PySide6.QtGui import QIcon, QPalette, QColor
from src.core.logger import get_logger
from src.core.vlc_engine import VLCEngine


class MiniPlayer(QWidget):
    """Small floating widget (200x150) with video + minimal controls, always on top."""
    
    # Signals
    close_requested = Signal()
    restore_main_window = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger('mini_player')
        self.vlc_engine = None
        self.current_media = None
        self.is_playing = False
        
        # Window properties
        self.setWindowFlags(
            Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        
        # Fixed size for mini player
        self.setFixedSize(200, 150)
        
        # Initialize UI
        self._setup_ui()
        self._setup_animations()
        
        # Position widget (default top-right corner)
        self._position_widget()
        
        self.logger.debug("Mini player initialized")
    
    def _setup_ui(self):
        """Setup the mini player UI."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        
        # Video area (placeholder for now)
        self.video_frame = QFrame()
        self.video_frame.setObjectName("miniVideoFrame")
        self.video_frame.setFixedHeight(100)
        self.video_frame.setStyleSheet("""
            QFrame#miniVideoFrame {
                background-color: #000000;
                border: 1px solid #333333;
                border-radius: 4px;
            }
        """)
        
        # Video placeholder label
        self.video_label = QLabel("No Video")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 10px;
                background-color: transparent;
            }
        """)
        
        video_layout = QVBoxLayout(self.video_frame)
        video_layout.setContentsMargins(0, 0, 0, 0)
        video_layout.addWidget(self.video_label)
        
        # Control bar
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(4)
        
        # Play/Pause button
        self.play_pause_btn = QPushButton("▶")
        self.play_pause_btn.setFixedSize(20, 20)
        self.play_pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #6200ea;
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7c4dff;
            }
            QPushButton:pressed {
                background-color: #5300cc;
            }
        """)
        self.play_pause_btn.clicked.connect(self._toggle_play_pause)
        
        # Close button
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(16, 16)
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff5252;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff6659;
            }
            QPushButton:pressed {
                background-color: #e53935;
            }
        """)
        self.close_btn.clicked.connect(self.close_requested.emit)
        
        # Restore main window button
        self.restore_btn = QPushButton("⬈")
        self.restore_btn.setFixedSize(16, 16)
        self.restore_btn.setStyleSheet("""
            QPushButton {
                background-color: #424242;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #616161;
            }
            QPushButton:pressed {
                background-color: #303030;
            }
        """)
        self.restore_btn.clicked.connect(self.restore_main_window.emit)
        
        # Add controls to layout
        control_layout.addWidget(self.play_pause_btn)
        control_layout.addStretch()
        control_layout.addWidget(self.restore_btn)
        control_layout.addWidget(self.close_btn)
        
        # Add to main layout
        layout.addWidget(self.video_frame)
        layout.addLayout(control_layout)
        
        # Set overall stylesheet
        self.setStyleSheet("""
            MiniPlayer {
                background-color: #1e1e1e;
                border: 1px solid #6200ea;
                border-radius: 6px;
            }
        """)
    
    def _setup_animations(self):
        """Setup fade animations."""
        self.opacity_effect = QGraphicsOpacityEffect()
        self.setGraphicsEffect(self.opacity_effect)
        
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(150)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
    
    def _position_widget(self):
        """Position the widget in top-right corner of screen."""
        from PySide6.QtGui import QGuiApplication
        
        screen = QGuiApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            x = screen_geometry.right() - self.width() - 20
            y = screen_geometry.top() + 20
            self.move(x, y)
    
    def set_vlc_engine(self, vlc_engine):
        """Set the VLC engine for video playback."""
        self.vlc_engine = vlc_engine
        if self.vlc_engine:
            # In a real implementation, we would embed the VLC widget here
            # For now, we'll use a placeholder
            self.video_label.setText("Video Ready")
    
    def load_media(self, media_path):
        """Load and play media in mini player."""
        self.current_media = media_path
        self.video_label.setText("Playing...")
        
        if self.vlc_engine and media_path:
            try:
                # Set media in VLC engine
                self.vlc_engine.set_media(media_path)
                self.vlc_engine.play()
                self.is_playing = True
                self._update_play_button()
                self.logger.info(f"Loaded media in mini player: {media_path}")
            except Exception as e:
                self.logger.error(f"Failed to load media in mini player: {e}")
                self.video_label.setText("Error")
    
    def _toggle_play_pause(self):
        """Toggle play/pause state."""
        if not self.current_media:
            return
        
        try:
            if self.is_playing:
                if self.vlc_engine:
                    self.vlc_engine.pause()
                self.is_playing = False
            else:
                if self.vlc_engine:
                    self.vlc_engine.play()
                self.is_playing = True
            
            self._update_play_button()
            self.logger.debug(f"Mini player play/pause toggled: {self.is_playing}")
        except Exception as e:
            self.logger.error(f"Failed to toggle play/pause: {e}")
    
    def _update_play_button(self):
        """Update play/pause button appearance."""
        if self.is_playing:
            self.play_pause_btn.setText("⏸")
        else:
            self.play_pause_btn.setText("▶")
    
    def show_with_animation(self):
        """Show mini player with fade-in animation."""
        self.show()
        self.fade_animation.start()
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging."""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging."""
        if event.buttons() == Qt.LeftButton and hasattr(self, 'drag_position'):
            new_pos = event.globalPosition().toPoint() - self.drag_position
            self.move(new_pos)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if hasattr(self, 'drag_position'):
            delattr(self, 'drag_position')
    
    def closeEvent(self, event):
        """Handle close event."""
        self.logger.debug("Mini player closed")
        # Stop playback if active
        if self.is_playing and self.vlc_engine:
            try:
                self.vlc_engine.stop()
            except:
                pass
        event.accept()


class MiniPlayerController:
    """Controller for managing mini player instances."""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.mini_player = None
        self.logger = get_logger('mini_player_controller')
    
    def show_mini_player(self, media_path=None):
        """Show mini player with optional media."""
        if self.mini_player is None:
            self.mini_player = MiniPlayer()
            self.mini_player.close_requested.connect(self._on_close_requested)
            self.mini_player.restore_main_window.connect(self._on_restore_main_window)
            
            # Set VLC engine from main window
            if hasattr(self.main_window, 'vlc_engine'):
                self.mini_player.set_vlc_engine(self.main_window.vlc_engine)
        
        # Load media if provided
        if media_path:
            self.mini_player.load_media(media_path)
        
        # Show mini player
        self.mini_player.show_with_animation()
        self.logger.info("Mini player shown")
    
    def hide_mini_player(self):
        """Hide mini player."""
        if self.mini_player:
            self.mini_player.close()
            self.mini_player = None
            self.logger.info("Mini player hidden")
    
    def _on_close_requested(self):
        """Handle close requested from mini player."""
        self.hide_mini_player()
    
    def _on_restore_main_window(self):
        """Handle restore main window requested from mini player."""
        self.hide_mini_player()
        if self.main_window:
            self.main_window.show()
            self.main_window.raise_()
            self.main_window.activateWindow()
    
    def is_active(self):
        """Check if mini player is active."""
        return self.mini_player is not None and self.mini_player.isVisible()
