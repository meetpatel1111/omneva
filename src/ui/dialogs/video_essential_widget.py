"""Video Essential Widget — Image Adjust, Sharpen, and Filters."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout, QLabel, QSlider
)
from PySide6.QtCore import Qt

class VideoEssentialWidget(QWidget):
    """Essential Video Effects (Image Adjust, Sharpen, etc.)."""

    def __init__(self, vlc, parent=None):
        super().__init__(parent)
        self.vlc = vlc
        layout = QHBoxLayout(self)
        
        # Left: Image Adjust
        gb_adjust = QGroupBox("Image adjust")
        gb_adjust.setCheckable(True)
        gb_adjust.setChecked(False)
        gb_adjust.toggled.connect(self.vlc.enable_video_adjust)
        
        grid_adjust = QGridLayout(gb_adjust)
        
        # Option IDs: Contrast=1, Brightness=2, Hue=3, Saturation=4, Gamma=5
        _OPT_HUE = 3
        _OPT_BRIGHTNESS = 2
        _OPT_CONTRAST = 1
        _OPT_SATURATION = 4
        _OPT_GAMMA = 5
        
        self.adjust_controls = [
            ("Hue", _OPT_HUE, 0, 360, 0, 1.0, True),
            ("Brightness", _OPT_BRIGHTNESS, 0, 200, 100, 0.01, False),
            ("Contrast", _OPT_CONTRAST, 0, 200, 100, 0.01, False),
            ("Saturation", _OPT_SATURATION, 0, 300, 100, 0.01, False),
            ("Gamma", _OPT_GAMMA, 1, 1000, 100, 0.01, False),
        ]
        
        self.sliders = {}
        for i, (name, opt, min_v, max_v, def_v, scale, is_int) in enumerate(self.adjust_controls):
            lbl = QLabel(name)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(min_v, max_v)
            slider.setValue(def_v)
            slider.valueChanged.connect(lambda v, o=opt, s=scale, is_i=is_int: self._update_val(o, v, s, is_i))
            grid_adjust.addWidget(lbl, i, 0)
            grid_adjust.addWidget(slider, i, 1)
            self.sliders[name] = slider

        layout.addWidget(gb_adjust)
        
        # Right: Filters (Sharpen, Banding, Grain)
        vbox_right = QVBoxLayout()
        
        # Sharpen
        gb_sharpen = QGroupBox("Sharpen")
        gb_sharpen.setCheckable(True)
        gb_sharpen.setChecked(False)
        l_sharpen = QVBoxLayout(gb_sharpen)
        s_sharpen = QSlider(Qt.Horizontal)
        s_sharpen.setRange(0, 500) # 0.0 to 5.0
        
        # Note: set_filter_sharpen must exist on vlc engine
        def _on_sharpen_change():
            if hasattr(self.vlc, 'set_filter_sharpen'):
                self.vlc.set_filter_sharpen(gb_sharpen.isChecked(), s_sharpen.value()/100.0)

        s_sharpen.valueChanged.connect(_on_sharpen_change)
        gb_sharpen.toggled.connect(lambda c: _on_sharpen_change())
        
        l_sharpen.addWidget(QLabel("Sigma"))
        l_sharpen.addWidget(s_sharpen)
        vbox_right.addWidget(gb_sharpen)
        
        # Banding (Stub)
        vbox_right.addWidget(QGroupBox("Banding removal", checkable=True, checked=False))

        # Grain (Stub)
        vbox_right.addWidget(QGroupBox("Film Grain", checkable=True, checked=False))
        
        vbox_right.addStretch()
        layout.addLayout(vbox_right)

    def _update_val(self, option, value, scale, is_int):
        if is_int:
            if hasattr(self.vlc, 'set_adjust_int'):
                self.vlc.set_adjust_int(option, int(value * scale))
        else:
            if hasattr(self.vlc, 'set_adjust_float'):
                self.vlc.set_adjust_float(option, value * scale)
            # Fallback to direct player access if vlc engine doesn't wrap these yet
            elif hasattr(self.vlc, 'player'):
                self.vlc.player.video_set_adjust_float(option, value * scale)
