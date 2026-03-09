"""Video Advanced Widget — Advanced Video Effects."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QSlider, QSpinBox, QCheckBox
)
from PySide6.QtCore import Qt

class VideoAdvancedWidget(QWidget):
    """Advanced Video Effects (Blur, Clone, Denoiser, etc.)."""
    def __init__(self, vlc, parent=None):
        super().__init__(parent)
        self.vlc = vlc
        layout = QHBoxLayout(self)
        
        # Left Column: Anti-Flicker, Motion Blur, Spatial Blur, Clone
        vbox_left = QVBoxLayout()
        
        # Anti-Flickering
        gb_af = QGroupBox("Anti-Flickering")
        gb_af.setCheckable(True)
        gb_af.setChecked(False)
        l_af = QHBoxLayout(gb_af)
        s_af = QSlider(Qt.Horizontal)
        s_af.setRange(0, 100)
        l_af.addWidget(QLabel("Soften"))
        l_af.addWidget(s_af)
        vbox_left.addWidget(gb_af)
        
        # Motion Blur
        gb_mb = QGroupBox("Motion blur")
        gb_mb.setCheckable(True)
        gb_mb.setChecked(False)
        l_mb = QHBoxLayout(gb_mb)
        s_mb = QSlider(Qt.Horizontal)
        s_mb.setRange(1, 127)
        l_mb.addWidget(QLabel("Factor"))
        l_mb.addWidget(s_mb)
        vbox_left.addWidget(gb_mb)
        
        # Spatial Blur
        gb_sb = QGroupBox("Spatial blur")
        gb_sb.setCheckable(True)
        gb_sb.setChecked(False)
        l_sb = QHBoxLayout(gb_sb)
        s_sb = QSlider(Qt.Horizontal)
        s_sb.setRange(0, 50)
        l_sb.addWidget(QLabel("Sigma"))
        l_sb.addWidget(s_sb)
        vbox_left.addWidget(gb_sb)

        # Clone
        gb_clone = QGroupBox("Clone")
        gb_clone.setCheckable(True)
        gb_clone.setChecked(False)
        l_clone = QHBoxLayout(gb_clone)
        sp_clone = QSpinBox()
        sp_clone.setRange(1, 100)
        sp_clone.setValue(2)
        l_clone.addWidget(QLabel("Number of clones"))
        l_clone.addWidget(sp_clone)
        vbox_left.addWidget(gb_clone)
        
        vbox_left.addStretch()
        layout.addLayout(vbox_left)
        
        # Right Column: Denoiser and Checkbox list
        vbox_right = QVBoxLayout()
        
        # Denoiser
        gb_dn = QGroupBox("Denoiser")
        gb_dn.setCheckable(True)
        gb_dn.setChecked(False)
        l_dn = QVBoxLayout(gb_dn)
        
        dn_controls = ["Spatial luma strength", "Temporal luma strength", 
                       "Spatial chroma strength", "Temporal chroma strength"]
        for name in dn_controls:
            h = QHBoxLayout()
            h.addWidget(QLabel(name))
            h.addWidget(QSlider(Qt.Horizontal))
            l_dn.addLayout(h)
            
        vbox_right.addWidget(gb_dn)
        
        # Checkboxes
        checks = [
            "Anaglyph 3D", "Mirror", "Psychedelic", 
            "Waves", "Water effect", "Motion detect"
        ]
        for name in checks:
            vbox_right.addWidget(QCheckBox(name))
            
        vbox_right.addStretch()
        layout.addLayout(vbox_right)
