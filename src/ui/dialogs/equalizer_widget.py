"""Equalizer Widget — 10-Band Audio Equalizer."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QCheckBox, QComboBox, QDialogButtonBox
)
from PySide6.QtCore import Qt

class EqualizerWidget(QWidget):
    """10-Band Audio Equalizer Widget."""
    
    def __init__(self, vlc_engine, parent=None):
        super().__init__(parent)
        self.vlc = vlc_engine
        
        layout = QVBoxLayout(self)
        
        # Enable / Presets
        top_layout = QHBoxLayout()
        self.chk_enable = QCheckBox("Enable Equalizer")
        self.chk_enable.toggled.connect(self._toggle_eq) 
        
        self.combo_presets = QComboBox()
        if hasattr(self.vlc, 'get_equalizer_presets'):
            self.combo_presets.addItems(self.vlc.get_equalizer_presets())
        self.combo_presets.currentIndexChanged.connect(self._apply_preset)
        
        top_layout.addWidget(self.chk_enable)
        top_layout.addWidget(QLabel("Presets:"))
        top_layout.addWidget(self.combo_presets)
        layout.addLayout(top_layout)
        
        # Preamp & Bands
        h_layout = QHBoxLayout()
        
        preamp_layout = QVBoxLayout()
        self.slider_preamp = QSlider(Qt.Vertical)
        self.slider_preamp.setRange(-200, 200) # -20.0 to 20.0
        self.slider_preamp.setValue(0)
        self.slider_preamp.valueChanged.connect(self._on_preamp_change)
        preamp_layout.addWidget(self.slider_preamp, 0, Qt.AlignHCenter)
        preamp_layout.addWidget(QLabel("Preamp"), 0, Qt.AlignHCenter)
        h_layout.addLayout(preamp_layout)
        
        self.bands = [
            "60Hz", "170Hz", "310Hz", "600Hz", "1kHz", 
            "3kHz", "6kHz", "12kHz", "14kHz", "16kHz"
        ]
        self.band_sliders = []
        
        for i, freq in enumerate(self.bands):
            vbox = QVBoxLayout()
            slider = QSlider(Qt.Vertical)
            slider.setRange(-200, 200)
            slider.setValue(0)
            slider.valueChanged.connect(lambda v, idx=i: self._on_band_change(idx, v))
            
            vbox.addWidget(slider, 0, Qt.AlignHCenter)
            vbox.addWidget(QLabel(freq), 0, Qt.AlignHCenter)
            h_layout.addLayout(vbox)
            self.band_sliders.append(slider)
            
        layout.addLayout(h_layout)
        layout.addStretch()
        
        self.chk_enable.setChecked(False)
        self._toggle_ui(False)

    def _on_preamp_change(self, v):
        if hasattr(self.vlc, 'set_equalizer_preamp'):
            self.vlc.set_equalizer_preamp(v / 10.0)

    def _on_band_change(self, idx, v):
        if hasattr(self.vlc, 'set_equalizer_band'):
            self.vlc.set_equalizer_band(idx, v / 10.0)

    def _toggle_eq(self, checked):
        self._toggle_ui(checked)
        if checked:
            self._on_preamp_change(self.slider_preamp.value())
            for i, slider in enumerate(self.band_sliders):
                self._on_band_change(i, slider.value())
        else:
            if hasattr(self.vlc, 'player'):
                self.vlc.player.set_equalizer(None)

    def _toggle_ui(self, enabled):
        self.combo_presets.setEnabled(enabled)
        self.slider_preamp.setEnabled(enabled)
        for slider in self.band_sliders:
            slider.setEnabled(enabled)
            
    def _apply_preset(self, index):
        if self.chk_enable.isChecked() and hasattr(self.vlc, 'set_equalizer_preset'):
            self.vlc.set_equalizer_preset(index)
