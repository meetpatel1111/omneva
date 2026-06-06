"""Audio Visualizer - FFT bar visualization overlay for audio files."""

import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
from PySide6.QtCore import Qt, QTimer, Signal, QRectF, QPointF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient
from src.core.logger import get_logger


class AudioVisualizerWidget(QWidget):
    """FFT bar visualization widget for audio playback."""
    
    # Signals
    visualization_updated = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.logger = get_logger('audio_visualizer')
        
        # Visualization settings
        self.bar_count = 32  # Number of frequency bars
        self.bar_width = 8
        self.bar_spacing = 2
        self.min_height = 5
        self.max_height = 100
        
        # Data storage
        self.fft_data = np.zeros(self.bar_count)
        self.smoothed_data = np.zeros(self.bar_count)
        self.smoothing_factor = 0.7
        
        # Visualization state
        self.is_active = False
        self.is_audio_only = False
        self.colors = self._create_color_scheme()
        
        # Animation
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.setInterval(50)  # 20 FPS
        
        # Widget properties
        self.setFixedSize(
            self.bar_count * (self.bar_width + self.bar_spacing),
            self.max_height + 20
        )
        self.setAttribute(Qt.WA_TransparentBackground, True)
        
        self.logger.debug("Audio visualizer widget initialized")
    
    def _create_color_scheme(self):
        """Create color scheme for visualization bars."""
        return {
            'background': QColor(0, 0, 0, 180),  # Semi-transparent black
            'bar_low': QColor(100, 200, 255),      # Light blue for low frequencies
            'bar_mid': QColor(50, 150, 255),      # Medium blue for mid frequencies  
            'bar_high': QColor(0, 100, 255),      # Dark blue for high frequencies
            'peak': QColor(255, 255, 255),        # White for peaks
            'gradient': True
        }
    
    def start_visualization(self):
        """Start the audio visualization."""
        if not self.is_active:
            self.is_active = True
            self.animation_timer.start()
            self.show()
            self.logger.info("Audio visualization started")
    
    def stop_visualization(self):
        """Stop the audio visualization."""
        if self.is_active:
            self.is_active = False
            self.animation_timer.stop()
            self.hide()
            self.fft_data.fill(0)
            self.smoothed_data.fill(0)
            self.update()
            self.logger.info("Audio visualization stopped")
    
    def set_audio_only_mode(self, audio_only):
        """Set whether we're in audio-only mode (show full visualization)."""
        self.is_audio_only = audio_only
        if audio_only:
            # Expand for full-screen audio visualization
            self.setFixedSize(
                self.bar_count * (self.bar_width + self.bar_spacing) * 2,
                self.max_height * 2
            )
        else:
            # Compact overlay mode for video
            self.setFixedSize(
                self.bar_count * (self.bar_width + self.bar_spacing),
                self.max_height + 20
            )
    
    def update_fft_data(self, fft_data):
        """Update FFT data from audio analysis."""
        if not self.is_active:
            return
        
        try:
            # Normalize and interpolate FFT data
            if len(fft_data) > 0:
                # Take logarithm for better frequency distribution
                fft_data = np.log10(np.abs(fft_data) + 1e-10)
                
                # Resample to our bar count
                if len(fft_data) != self.bar_count:
                    indices = np.linspace(0, len(fft_data) - 1, self.bar_count, dtype=int)
                    self.fft_data = fft_data[indices]
                else:
                    self.fft_data = fft_data
                
                # Normalize to 0-1 range
                if np.max(self.fft_data) > 0:
                    self.fft_data = self.fft_data / np.max(self.fft_data)
                
                # Apply smoothing
                self.smoothed_data = (
                    self.smoothing_factor * self.smoothed_data + 
                    (1 - self.smoothing_factor) * self.fft_data
                )
                
                self.visualization_updated.emit()
                
        except Exception as e:
            self.logger.error(f"Failed to update FFT data: {e}")
    
    def _update_animation(self):
        """Update animation frame."""
        if self.is_active:
            self.update()
    
    def paintEvent(self, event):
        """Paint the visualization bars."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        
        # Draw background (semi-transparent)
        if self.is_audio_only:
            # Full screen mode - darker background
            background_brush = QBrush(QColor(0, 0, 0, 200))
        else:
            # Overlay mode - lighter background
            background_brush = QBrush(self.colors['background'])
        
        painter.fillRect(self.rect(), background_brush)
        
        # Draw frequency bars
        self._draw_bars(painter)
        
        painter.end()
    
    def _draw_bars(self, painter):
        """Draw frequency bars with gradient colors."""
        width = self.width()
        height = self.height()
        
        for i in range(self.bar_count):
            # Calculate bar position and height
            x = i * (self.bar_width + self.bar_spacing) + 10
            bar_height = int(self.smoothed_data[i] * (height - 30))
            bar_height = max(self.min_height, bar_height)
            
            # Bar position (bottom-aligned)
            bar_y = height - bar_height - 10
            
            # Create gradient for bar
            gradient = QLinearGradient(x, bar_y + bar_height, x, bar_y)
            
            # Color based on frequency range
            if i < self.bar_count // 3:
                # Low frequencies - light blue to medium blue
                gradient.setColorAt(0, self.colors['bar_low'])
                gradient.setColorAt(1, self.colors['bar_mid'])
            elif i < 2 * self.bar_count // 3:
                # Mid frequencies - medium blue
                gradient.setColorAt(0, self.colors['bar_mid'])
                gradient.setColorAt(1, self.colors['bar_high'])
            else:
                # High frequencies - dark blue
                gradient.setColorAt(0, self.colors['bar_high'])
                gradient.setColorAt(1, QColor(0, 50, 200))
            
            # Draw bar
            painter.fillRect(x, bar_y, self.bar_width, bar_height, gradient)
            
            # Draw peak indicator
            if self.smoothed_data[i] > 0.8:
                peak_y = bar_y - 2
                painter.fillRect(x, peak_y, self.bar_width, 2, self.colors['peak'])
    
    def set_colors(self, color_scheme):
        """Set custom color scheme."""
        self.colors.update(color_scheme)
        self.update()
    
    def set_bar_count(self, count):
        """Set number of frequency bars."""
        self.bar_count = max(16, min(64, count))  # Limit between 16-64
        self.fft_data = np.zeros(self.bar_count)
        self.smoothed_data = np.zeros(self.bar_count)
        
        # Update widget size
        new_width = self.bar_count * (self.bar_width + self.bar_spacing)
        if self.is_audio_only:
            new_width *= 2
        self.setFixedSize(new_width + 20, self.height())
        
        self.logger.debug(f"Bar count updated to {self.bar_count}")
    
    def set_smoothing(self, factor):
        """Set smoothing factor for animations."""
        self.smoothing_factor = max(0.1, min(0.9, factor))
        self.logger.debug(f"Smoothing factor set to {self.smoothing_factor}")


class AudioVisualizerController:
    """Controller for managing audio visualizations."""
    
    def __init__(self, parent_widget):
        self.parent_widget = parent_widget
        self.visualizer = None
        self.logger = get_logger('audio_visualizer_controller')
        self.analysis_timer = QTimer()
        self.analysis_timer.timeout.connect(self._analyze_audio)
        self.analysis_timer.setInterval(100)  # 10 Hz analysis rate
        
        # Audio analysis (simplified - in real implementation would use VLC audio callbacks)
        self.is_analyzing = False
        self.mock_data_phase = 0
        
    def create_visualizer(self, parent=None):
        """Create the visualizer widget."""
        if self.visualizer is None:
            self.visualizer = AudioVisualizerWidget(parent)
            self.logger.debug("Audio visualizer created")
        return self.visualizer
    
    def start_analysis(self, vlc_engine=None):
        """Start audio analysis for visualization."""
        if not self.is_analyzing:
            self.is_analyzing = True
            self.vlc_engine = vlc_engine
            self.analysis_timer.start()
            self.logger.info("Audio analysis started")
    
    def stop_analysis(self):
        """Stop audio analysis."""
        if self.is_analyzing:
            self.is_analyzing = False
            self.analysis_timer.stop()
            if self.visualizer:
                self.visualizer.stop_visualization()
            self.logger.info("Audio analysis stopped")
    
    def _analyze_audio(self):
        """Analyze audio and update visualization (mock implementation)."""
        if not self.is_analyzing or not self.visualizer:
            return
        
        try:
            # Mock FFT data generation (in real implementation would get from VLC)
            self.mock_data_phase += 0.1
            mock_fft = np.random.random(64)  # Generate random frequency data
            
            # Add some structure to make it look realistic
            for i in range(len(mock_fft)):
                # Simulate bass frequencies (lower indices)
                if i < 10:
                    mock_fft[i] *= 1.5 + 0.5 * np.sin(self.mock_data_phase * 2)
                # Simulate mid frequencies
                elif i < 30:
                    mock_fft[i] *= 0.8 + 0.3 * np.sin(self.mock_data_phase * 3 + i * 0.1)
                # Simulate high frequencies
                else:
                    mock_fft[i] *= 0.5 + 0.2 * np.random.random()
            
            # Update visualizer
            self.visualizer.update_fft_data(mock_fft)
            
        except Exception as e:
            self.logger.error(f"Audio analysis failed: {e}")
    
    def show_visualization(self, audio_only=False):
        """Show audio visualization."""
        if not self.visualizer:
            self.create_visualizer(self.parent_widget)
        
        self.visualizer.set_audio_only_mode(audio_only)
        self.visualizer.start_visualization()
        self.start_analysis()
        
        # Position visualizer
        if audio_only:
            # Center on parent widget
            parent_rect = self.parent_widget.rect()
            vis_rect = self.visualizer.rect()
            x = (parent_rect.width() - vis_rect.width()) // 2
            y = (parent_rect.height() - vis_rect.height()) // 2
            self.visualizer.move(x, y)
        else:
            # Bottom-right corner for overlay
            parent_rect = self.parent_widget.rect()
            vis_rect = self.visualizer.rect()
            x = parent_rect.width() - vis_rect.width() - 20
            y = parent_rect.height() - vis_rect.height() - 20
            self.visualizer.move(x, y)
        
        self.logger.info(f"Audio visualization shown (audio_only={audio_only})")
    
    def hide_visualization(self):
        """Hide audio visualization."""
        self.stop_analysis()
        if self.visualizer:
            self.visualizer.stop_visualization()
        self.logger.info("Audio visualization hidden")
    
    def is_active(self):
        """Check if visualization is active."""
        return self.visualizer is not None and self.visualizer.is_active
