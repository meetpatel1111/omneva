"""Sync Widget — Audio and Subtitle Synchronization."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, 
    QSpinBox, QPushButton
)
from PySide6.QtCore import Qt

class SyncWidget(QWidget):
    """Audio and Subtitle Synchronization Widget."""

    def __init__(self, vlc_engine, parent=None):
        super().__init__(parent)
        self.vlc = vlc_engine
        
        layout = QVBoxLayout(self)
        
        # Audio Synchronization
        audio_group = QVBoxLayout()
        audio_group.addWidget(QLabel("<b>Audio</b>"))
        
        h_audio = QHBoxLayout()
        h_audio.addWidget(QLabel("Audio track synchronization:"))
        self.spin_audio = QSpinBox()
        self.spin_audio.setRange(-600000, 600000)
        self.spin_audio.setSuffix(" ms")
        self.spin_audio.setSingleStep(50)
        self.spin_audio.valueChanged.connect(self._update_audio)
        h_audio.addWidget(self.spin_audio)
        audio_group.addLayout(h_audio)
        
        layout.addLayout(audio_group)
        layout.addSpacing(10)
        
        # Subtitle Synchronization
        sub_group = QVBoxLayout()
        sub_group.addWidget(QLabel("<b>Subtitles/Video</b>"))
        
        h_sub = QHBoxLayout()
        h_sub.addWidget(QLabel("Subtitle track synchronization:"))
        self.spin_sub = QSpinBox()
        self.spin_sub.setRange(-600000, 600000)
        self.spin_sub.setSuffix(" ms")
        self.spin_sub.setSingleStep(50)
        self.spin_sub.valueChanged.connect(self._update_sub)
        h_sub.addWidget(self.spin_sub)
        sub_group.addLayout(h_sub)
        
        h_sub_speed = QHBoxLayout()
        h_sub_speed.addWidget(QLabel("Subtitle speed:"))
        self.spin_sub_speed = QSpinBox()
        self.spin_sub_speed.setRange(1, 1000)
        self.spin_sub_speed.setSuffix(" fps")
        self.spin_sub_speed.setValue(1) # Placeholder
        h_sub_speed.addWidget(self.spin_sub_speed)
        sub_group.addLayout(h_sub_speed)
        
        layout.addLayout(sub_group)
        layout.addSpacing(20)
        
        btn_reset = QPushButton("Reset Synchronization")
        btn_reset.clicked.connect(self._reset)
        layout.addWidget(btn_reset)
        
        layout.addStretch()

    def _update_audio(self, val):
        # VLC API uses microseconds but often exposed as ms in UI
        self.vlc.player.audio_set_delay(val * 1000)

    def _update_sub(self, val):
        self.vlc.set_subtitle_delay(val)

    def _reset(self):
        self.spin_audio.setValue(0)
        self.spin_sub.setValue(0)
        self.vlc.player.audio_set_delay(0)
        self.vlc.set_subtitle_delay(0)
