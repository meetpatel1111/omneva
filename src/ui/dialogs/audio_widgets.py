"""Audio Widgets — Compressor, Spatializer, and Stereo Widener."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QSlider, QCheckBox
)
from PySide6.QtCore import Qt

class CompressorWidget(QWidget):
    """Compressor settings (Stub UI)."""
    def __init__(self, vlc, parent=None):
        super().__init__(parent)
        self.vlc = vlc
        layout = QVBoxLayout(self)
        
        self.chk_enable = QCheckBox("Enable")
        self.chk_enable.toggled.connect(self._toggle_ui)
        layout.addWidget(self.chk_enable)
        
        grid = QGridLayout()
        layout.addLayout(grid)
        
        controls = [
            ("RMS/peak", 0.0, 1.0, 0.2),
            ("Attack", 1.5, 400.0, 25.0),
            ("Release", 2.0, 800.0, 100.0),
            ("Threshold", -30.0, 0.0, -11.0),
            ("Ratio", 1.0, 20.0, 4.0),
            ("Knee radius", 1.0, 10.0, 5.0),
            ("Makeup gain", 0.0, 24.0, 7.0)
        ]
        
        self.ui_controls = []
        for i, (name, min_v, max_v, def_v) in enumerate(controls):
            lbl = QLabel(name)
            slider = QSlider(Qt.Vertical)
            slider.setRange(int(min_v*10), int(max_v*10))
            slider.setValue(int(def_v*10))
            
            val_lbl = QLabel(f"{def_v}")
            slider.valueChanged.connect(lambda v, l=val_lbl: l.setText(f"{v/10.0:.1f}"))
            
            vbox = QVBoxLayout()
            vbox.addWidget(slider, 0, Qt.AlignHCenter)
            vbox.addWidget(val_lbl, 0, Qt.AlignHCenter)
            vbox.addWidget(lbl, 0, Qt.AlignHCenter)
            grid.addLayout(vbox, 0, i)
            
            self.ui_controls.extend([slider, lbl, val_lbl])

        layout.addStretch()
        self._toggle_ui(False)

    def _toggle_ui(self, enabled):
        for w in self.ui_controls:
            w.setEnabled(enabled)
        if hasattr(self.vlc, 'set_compressor'):
            self.vlc.set_compressor(enabled)


class SpatializerWidget(QWidget):
    """Spatializer settings (Stub UI)."""
    def __init__(self, vlc, parent=None):
        super().__init__(parent)
        self.vlc = vlc
        layout = QVBoxLayout(self)
        
        self.chk_enable = QCheckBox("Enable")
        self.chk_enable.toggled.connect(self._toggle_ui)
        layout.addWidget(self.chk_enable)
        
        grid = QGridLayout()
        layout.addLayout(grid)
        
        controls = [
            ("Size", 0, 10, 8.0),
            ("Width", 0, 10, 10.0),
            ("Wet", 0, 10, 4.0),
            ("Dry", 0, 10, 5.0),
            ("Damp", 0, 10, 5.0)
        ]
        
        self.ui_controls = []
        for i, (name, min_v, max_v, def_v) in enumerate(controls):
            lbl = QLabel(name)
            slider = QSlider(Qt.Vertical)
            slider.setRange(int(min_v*10), int(max_v*10))
            slider.setValue(int(def_v*10))
            
            val_lbl = QLabel(f"{def_v}")
            slider.valueChanged.connect(lambda v, l=val_lbl: l.setText(f"{v/10.0:.1f}"))
            
            vbox = QVBoxLayout()
            vbox.addWidget(slider, 0, Qt.AlignHCenter)
            vbox.addWidget(val_lbl, 0, Qt.AlignHCenter)
            vbox.addWidget(lbl, 0, Qt.AlignHCenter)
            grid.addLayout(vbox, 0, i)
            
            self.ui_controls.extend([slider, lbl, val_lbl])
        
        layout.addStretch()
        self._toggle_ui(False)

    def _toggle_ui(self, enabled):
        for w in self.ui_controls:
            w.setEnabled(enabled)
        if hasattr(self.vlc, 'set_spatializer'):
            self.vlc.set_spatializer(enabled)


class StereoWidenerWidget(QWidget):
    """Stereo Widener settings (Stub UI)."""
    def __init__(self, vlc, parent=None):
        super().__init__(parent)
        self.vlc = vlc
        layout = QVBoxLayout(self)
        
        self.chk_enable = QCheckBox("Enable")
        self.chk_enable.toggled.connect(self._toggle_ui)
        layout.addWidget(self.chk_enable)
        
        grid = QGridLayout()
        layout.addLayout(grid)
        
        controls = [
            ("Delay time", 0, 100, 20.0),
            ("Feedback gain", 0, 1, 0.3),
            ("Crossfeed", 0, 1, 0.3),
            ("Dry mix", 0, 1, 0.8)
        ]
        
        self.ui_controls = []
        for i, (name, min_v, max_v, def_v) in enumerate(controls):
            lbl = QLabel(name)
            slider = QSlider(Qt.Vertical)
            slider.setRange(int(min_v*10), int(max_v*10))
            slider.setValue(int(def_v*10))
            
            val_lbl = QLabel(f"{def_v}")
            slider.valueChanged.connect(lambda v, l=val_lbl: l.setText(f"{v/10.0:.1f}"))
            
            vbox = QVBoxLayout()
            vbox.addWidget(slider, 0, Qt.AlignHCenter)
            vbox.addWidget(val_lbl, 0, Qt.AlignHCenter)
            vbox.addWidget(lbl, 0, Qt.AlignHCenter)
            grid.addLayout(vbox, 0, i)

            self.ui_controls.extend([slider, lbl, val_lbl])
        
        layout.addStretch()
        self._toggle_ui(False)

    def _toggle_ui(self, enabled):
        for w in self.ui_controls:
            w.setEnabled(enabled)
        if hasattr(self.vlc, 'set_stereo_widener'):
            self.vlc.set_stereo_widener(enabled)
