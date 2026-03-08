"""Tools Dialogs — Synchronization, Video Effects, and Equalizer."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider, 
    QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox, 
    QPushButton, QDialogButtonBox, QWidget, QGroupBox, QGridLayout,
    QTabWidget, QFormLayout, QTextEdit, QLineEdit, QTreeWidget, QTreeWidgetItem,
    QRadioButton, QButtonGroup
)

from PySide6.QtCore import Qt, QTimer
import vlc

class SyncWidget(QWidget):
    """Audio and Subtitle Synchronization Widget."""
    
    def __init__(self, vlc_engine, parent=None):
        super().__init__(parent)
        self.vlc = vlc_engine
        
        layout = QVBoxLayout(self)
        
        # Audio Sync
        gb_audio = QGroupBox("Audio Track Synchronization")
        l_audio = QGridLayout(gb_audio)
        
        self.sb_audio = QDoubleSpinBox()
        self.sb_audio.setRange(-100.0, 100.0) # Seconds
        self.sb_audio.setSingleStep(0.1)
        self.sb_audio.setSuffix(" s")
        self.sb_audio.setDecimals(3)
        self.sb_audio.setValue(self.vlc.get_audio_delay() / 1000.0)
        self.sb_audio.valueChanged.connect(self._update_audio)
        
        l_audio.addWidget(QLabel("Audio delay:"), 0, 0)
        l_audio.addWidget(self.sb_audio, 0, 1)
        l_audio.addWidget(QLabel("(Positive values delay audio)"), 0, 2)
        
        layout.addWidget(gb_audio)
        
        # Subtitle Sync
        gb_sub = QGroupBox("Subtitle Track Synchronization")
        l_sub = QGridLayout(gb_sub)
        
        self.sb_sub = QDoubleSpinBox()
        self.sb_sub.setRange(-100.0, 100.0)
        self.sb_sub.setSingleStep(0.1)
        self.sb_sub.setSuffix(" s")
        self.sb_sub.setDecimals(3)
        self.sb_sub.setValue(self.vlc.get_subtitle_delay() / 1000.0)
        self.sb_sub.valueChanged.connect(self._update_sub)
        
        l_sub.addWidget(QLabel("Subtitle delay:"), 0, 0)
        l_sub.addWidget(self.sb_sub, 0, 1)
        l_sub.addWidget(QLabel("(Positive values delay subtitles)"), 0, 2)
        
        # Subtitle Speed
        self.sb_sub_fps = QDoubleSpinBox()
        self.sb_sub_fps.setRange(0.01, 240.0)
        self.sb_sub_fps.setSingleStep(1.0)
        self.sb_sub_fps.setValue(1.0) # Default
        self.sb_sub_fps.setSuffix(" fps")
        self.sb_sub_fps.setDecimals(3)
        self.sb_sub_fps.valueChanged.connect(self.vlc.set_subtitle_fps)
        
        l_sub.addWidget(QLabel("Subtitle speed:"), 1, 0)
        l_sub.addWidget(self.sb_sub_fps, 1, 1)
        
        # Duration Factor
        self.sb_sub_dur = QDoubleSpinBox()
        self.sb_sub_dur.setRange(0.1, 20.0)
        self.sb_sub_dur.setSingleStep(0.1)
        self.sb_sub_dur.setValue(1.0)
        self.sb_sub_dur.setDecimals(3)
        self.sb_sub_dur.valueChanged.connect(self.vlc.set_subtitle_duration_factor)
        
        l_sub.addWidget(QLabel("Subtitle duration factor:"), 2, 0)
        l_sub.addWidget(self.sb_sub_dur, 2, 1)
        
        layout.addWidget(gb_sub)
        
        # Reset
        # Reset
        btn_reset = QPushButton("Reset Synchronization")
        btn_reset.clicked.connect(self._reset)
        layout.addWidget(btn_reset)
        
        layout.addStretch()
        
    def _update_audio(self, val):
        # API expects ms
        self.vlc.set_audio_delay(int(val * 1000))
        
    def _update_sub(self, val):
        self.vlc.set_subtitle_delay(int(val * 1000))
        
    def _reset(self):
        self.sb_audio.setValue(0.0)
        self.sb_sub.setValue(0.0)


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
        
        # Video Adjust Options (hardcoded)
        # Enable=0, Contrast=1, Brightness=2, Hue=3, Saturation=4, Gamma=5
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
        s_sharpen.valueChanged.connect(lambda v: self.vlc.set_filter_sharpen(gb_sharpen.isChecked(), v/100.0))
        gb_sharpen.toggled.connect(lambda c: self.vlc.set_filter_sharpen(c, s_sharpen.value()/100.0))
        l_sharpen.addWidget(QLabel("Sigma"))
        l_sharpen.addWidget(s_sharpen)
        vbox_right.addWidget(gb_sharpen)
        
        # Banding (Stub)
        gb_banding = QGroupBox("Banding removal")
        gb_banding.setCheckable(True)
        gb_banding.setChecked(False)
        vbox_right.addWidget(gb_banding)

        # Grain (Stub)
        gb_grain = QGroupBox("Film Grain")
        gb_grain.setCheckable(True)
        gb_grain.setChecked(False)
        vbox_right.addWidget(gb_grain)
        
        vbox_right.addStretch()
        layout.addLayout(vbox_right)

    def _update_val(self, option, value, scale, is_int):
        if is_int:
            self.vlc.set_adjust_int(option, int(value * scale))
        else:
            self.vlc.set_adjust_float(option, value * scale)


class VideoCropWidget(QWidget):
    """Video Crop Settings."""
    def __init__(self, vlc, parent=None):
        super().__init__(parent)
        self.vlc = vlc
        layout = QGridLayout(self)
        
        self.spin_top = QSpinBox()
        self.spin_bot = QSpinBox()
        self.spin_left = QSpinBox()
        self.spin_right = QSpinBox()
        
        for s in [self.spin_top, self.spin_bot, self.spin_left, self.spin_right]:
            s.setRange(0, 9999)
            s.setSuffix(" px")
            s.valueChanged.connect(self._update_crop)
            
        layout.addWidget(QLabel("Top"), 0, 1, Qt.AlignHCenter)
        layout.addWidget(self.spin_top, 1, 1)
        
        layout.addWidget(QLabel("Left"), 2, 0, Qt.AlignHCenter)
        layout.addWidget(self.spin_left, 3, 0)
        
        layout.addWidget(QLabel("Right"), 2, 2, Qt.AlignHCenter)
        layout.addWidget(self.spin_right, 3, 2)
        
        layout.addWidget(QLabel("Bottom"), 4, 1, Qt.AlignHCenter)
        layout.addWidget(self.spin_bot, 5, 1)
        
        layout.setRowStretch(6, 1)

    def _update_crop(self):
        self.vlc.set_crop(
            top=self.spin_top.value(),
            left=self.spin_left.value(),
            bottom=self.spin_bot.value(),
            right=self.spin_right.value()
        )


class VideoColorsWidget(QWidget):
    """Video Colors Settings (Stub)."""
    def __init__(self, vlc, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        
        # Stubs for visual completeness
        layout.addWidget(QCheckBox("Color extraction"), 0, 0)
        layout.addWidget(QCheckBox("Negate colors"), 0, 1)
        layout.addWidget(QCheckBox("Posterize"), 1, 1)
        layout.addWidget(QCheckBox("Sepia"), 2, 1)
        layout.addWidget(QCheckBox("Color threshold"), 1, 0)
        
        layout.setRowStretch(3, 1)


class VideoGeometryWidget(QWidget):
    """Video Geometry Settings (Stub)."""
    def __init__(self, vlc, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        
        layout.addWidget(QCheckBox("Interactive Zoom"), 0, 0)
        layout.addWidget(QCheckBox("Transform"), 1, 0)
        layout.addWidget(QCheckBox("Rotate"), 2, 0)
        layout.addWidget(QCheckBox("Wall"), 0, 1)
        layout.addWidget(QCheckBox("Puzzle game"), 1, 1)
        
        layout.setRowStretch(3, 1)


class VideoOverlayWidget(QWidget):
    """Video Overlay Settings (Logo, Text)."""
    def __init__(self, vlc, parent=None):
        super().__init__(parent)
        self.vlc = vlc
        layout = QHBoxLayout(self)
        
        # Logo
        gb_logo = QGroupBox("Add logo")
        gb_logo.setCheckable(True)
        gb_logo.setChecked(False)
        gb_logo.toggled.connect(self._update_logo)
        l_logo = QGridLayout(gb_logo)
        
        from PySide6.QtWidgets import QLineEdit, QFileDialog
        
        self.txt_logo_path = QLineEdit()
        btn_browse = QPushButton("...")
        btn_browse.clicked.connect(self._browse_logo)
        
        self.spin_logo_top = QSpinBox()
        self.spin_logo_left = QSpinBox()
        self.slider_logo_opacity = QSlider(Qt.Horizontal)
        self.slider_logo_opacity.setRange(0, 255)
        self.slider_logo_opacity.setValue(255)
        
        for w in [self.spin_logo_top, self.spin_logo_left, self.slider_logo_opacity]:
             w.valueChanged.connect(self._update_logo)

        l_logo.addWidget(QLabel("Logo"), 0, 0)
        l_logo.addWidget(self.txt_logo_path, 0, 1)
        l_logo.addWidget(btn_browse, 0, 2)
        
        l_logo.addWidget(QLabel("Top"), 1, 0)
        l_logo.addWidget(self.spin_logo_top, 1, 1)
        l_logo.addWidget(QLabel("Left"), 2, 0)
        l_logo.addWidget(self.spin_logo_left, 2, 1)
        l_logo.addWidget(QLabel("Opacity"), 3, 0)
        l_logo.addWidget(self.slider_logo_opacity, 3, 1, 1, 2)
        
        layout.addWidget(gb_logo)
        
        # Text
        gb_text = QGroupBox("Add text")
        gb_text.setCheckable(True)
        gb_text.setChecked(False)
        gb_text.toggled.connect(self._update_text)
        l_text = QGridLayout(gb_text)
        
        self.txt_input = QLineEdit("VLC")
        self.txt_input.textChanged.connect(self._update_text)
        
        self.combo_pos = QComboBox()
        # 0=Center, 1=Left, 2=Right, 4=Top, 8=Bottom
        self.combo_pos.addItem("Center", 0)
        self.combo_pos.addItem("Top-Left", 5) # 4+1
        self.combo_pos.addItem("Top-Right", 6) # 4+2
        self.combo_pos.addItem("Bottom-Left", 9) # 8+1
        self.combo_pos.addItem("Bottom-Right", 10) # 8+2
        self.combo_pos.currentIndexChanged.connect(self._update_text)
        
        l_text.addWidget(QLabel("Text"), 0, 0)
        l_text.addWidget(self.txt_input, 0, 1)
        l_text.addWidget(QLabel("Position"), 1, 0)
        l_text.addWidget(self.combo_pos, 1, 1)
        
        layout.addWidget(gb_text)
        
    def _browse_logo(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Logo", filter="Images (*.png *.jpg *.jpeg)")
        if f:
            self.txt_logo_path.setText(f)
            self._update_logo()
            
    def _update_logo(self):
        if self.findChild(QGroupBox, "Add logo").isChecked(): # simplified check
             self.vlc.set_logo(
                 self.txt_logo_path.text(),
                 self.slider_logo_opacity.value(),
                 self.spin_logo_left.value(),
                 self.spin_logo_top.value()
             )
        else:
             self.vlc.set_logo(None)

    def _update_text(self):
        if self.findChild(QGroupBox, "Add text").isChecked():
             self.vlc.set_marquee(
                 self.txt_input.text(),
                 self.combo_pos.currentData()
             )
        else:
             self.vlc.set_marquee(None)


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
        l_dn = QGridLayout(gb_dn)
        
        dn_controls = ["Spatial luma strength", "Temporal luma strength", 
                       "Spatial chroma strength", "Temporal chroma strength"]
        for i, name in enumerate(dn_controls):
            l_dn.addWidget(QLabel(name), i, 0)
            sl = QSlider(Qt.Horizontal)
            l_dn.addWidget(sl, i, 1)
            
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


class VideoEffectsWidget(QWidget):
    """Container for Video Effects Tabs."""
    def __init__(self, vlc_engine, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.tabs = QTabWidget()
        self.tabs.addTab(VideoEssentialWidget(vlc_engine), "Essential")
        self.tabs.addTab(VideoCropWidget(vlc_engine), "Crop")
        self.tabs.addTab(VideoColorsWidget(vlc_engine), "Colors")
        self.tabs.addTab(VideoGeometryWidget(vlc_engine), "Geometry")
        self.tabs.addTab(VideoOverlayWidget(vlc_engine), "Overlay")
        self.tabs.addTab(VideoAdvancedWidget(vlc_engine), "Advanced")
        
        layout.addWidget(self.tabs)
            
            
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
        # Note: VLC "set_equalizer(None)" disables it. 
        # "set_equalizer(eq)" enables it.
        # We need to maintain state.
        
        self.combo_presets = QComboBox()
        self.combo_presets.addItems(self.vlc.get_equalizer_presets())
        self.combo_presets.currentIndexChanged.connect(self._apply_preset)
        
        top_layout.addWidget(self.chk_enable)
        top_layout.addWidget(QLabel("Presets:"))
        top_layout.addWidget(self.combo_presets)
        layout.addLayout(top_layout)
        
        # Preamp
        h_layout = QHBoxLayout()
        
        preamp_layout = QVBoxLayout()
        self.slider_preamp = QSlider(Qt.Vertical)
        self.slider_preamp.setRange(-200, 200) # -20.0 to 20.0
        self.slider_preamp.setValue(0)
        self.slider_preamp.valueChanged.connect(lambda v: self.vlc.set_equalizer_preamp(v / 10.0))
        preamp_layout.addWidget(self.slider_preamp, 0, Qt.AlignHCenter)
        preamp_layout.addWidget(QLabel("Preamp"), 0, Qt.AlignHCenter)
        h_layout.addLayout(preamp_layout)
        
        # Bands
        # Standard VLC Bands: 60, 170, 310, 600, 1k, 3k, 6k, 12k, 14k, 16k
        self.bands = [
            "60Hz", "170Hz", "310Hz", "600Hz", "1kHz", 
            "3kHz", "6kHz", "12kHz", "14kHz", "16kHz"
        ]
        self.band_sliders = []
        
        for i, freq in enumerate(self.bands):
            vbox = QVBoxLayout()
            slider = QSlider(Qt.Vertical)
            slider.setRange(-200, 200) # -20dB to +20dB
            slider.setValue(0)
            slider.valueChanged.connect(lambda v, idx=i: self.vlc.set_equalizer_band(idx, v / 10.0))
            
            vbox.addWidget(slider, 0, Qt.AlignHCenter)
            vbox.addWidget(QLabel(freq), 0, Qt.AlignHCenter)
            h_layout.addLayout(vbox)
            self.band_sliders.append(slider)
            
        layout.addLayout(h_layout)
        
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.close)
        layout.addWidget(btns)
        
        self.chk_enable.setChecked(False) # Start disabled
        self._toggle_ui(False)

    def _toggle_eq(self, checked):
        self._toggle_ui(checked)
        if checked:
            # Re-apply current settings
            self.vlc.set_equalizer_preamp(self.slider_preamp.value() / 10.0)
            for i, slider in enumerate(self.band_sliders):
                self.vlc.set_equalizer_band(i, slider.value() / 10.0)
        else:
            self.vlc.player.set_equalizer(None)

    def _toggle_ui(self, enabled):
        self.combo_presets.setEnabled(enabled)
        self.slider_preamp.setEnabled(enabled)
        for slider in self.band_sliders:
            slider.setEnabled(enabled)
            
    def _apply_preset(self, index):
        if self.chk_enable.isChecked():
            self.vlc.set_equalizer_preset(index)
            # Update sliders to match preset? 
            # VLC doesn't give us the band values back easily from the python wrapper if using new_from_preset directly 
            # without parsing.
            # For now, we just apply it.

class CompressorWidget(QWidget):
    """Compressor settings (Stub UI)."""
    def __init__(self, vlc, parent=None):
        super().__init__(parent)
        self.vlc = vlc
        layout = QVBoxLayout(self)
        
        self.chk_enable = QCheckBox("Enable")
        self.chk_enable.toggled.connect(self._toggle_ui)
        layout.addWidget(self.chk_enable)
        
        # Grid of sliders
        grid = QGridLayout()
        layout.addLayout(grid)
        
        # RMS/Peak, Attack, Release, Threshold, Ratio, Knee, Gain
        controls = [
            ("RMS/peak", 0.0, 1.0, 0.2),
            ("Attack", 1.5, 400.0, 25.0), # ms
            ("Release", 2.0, 800.0, 100.0), # ms
            ("Threshold", -30.0, 0.0, -11.0), # dB
            ("Ratio", 1.0, 20.0, 4.0),
            ("Knee radius", 1.0, 10.0, 5.0), # dB
            ("Makeup gain", 0.0, 24.0, 7.0) # dB
        ]
        
        for i, (name, min_v, max_v, def_v) in enumerate(controls):
            lbl = QLabel(name)
            slider = QSlider(Qt.Vertical)
            slider.setRange(int(min_v*10), int(max_v*10))
            slider.setValue(int(def_v*10))
            
            # Label for value
            val_lbl = QLabel(f"{def_v}")
            slider.valueChanged.connect(lambda v, l=val_lbl: l.setText(f"{v/10.0:.1f}"))
            
            vbox = QVBoxLayout()
            vbox.addWidget(slider, 0, Qt.AlignHCenter)
            vbox.addWidget(val_lbl, 0, Qt.AlignHCenter)
            vbox.addWidget(lbl, 0, Qt.AlignHCenter)
            
            grid.addLayout(vbox, 0, i)
            
            # Store for enabling/disabling
            if not hasattr(self, 'ui_controls'): self.ui_controls = []
            self.ui_controls.extend([slider, lbl, val_lbl])

        layout.addStretch()
        
        self._toggle_ui(False) # Start disabled

    def _toggle_ui(self, enabled):
        for w in getattr(self, 'ui_controls', []):
            w.setEnabled(enabled)
        # Also toggle backend
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
        
        # Size, Width, Wet, Dry, Damp
        controls = [
            ("Size", 0, 10, 8.0),
            ("Width", 0, 10, 10.0),
            ("Wet", 0, 10, 4.0),
            ("Dry", 0, 10, 5.0),
            ("Damp", 0, 10, 5.0)
        ]
        
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
            
            if not hasattr(self, 'ui_controls'): self.ui_controls = []
            self.ui_controls.extend([slider, lbl, val_lbl])
        
        layout.addStretch()
        self._toggle_ui(False)

    def _toggle_ui(self, enabled):
        for w in getattr(self, 'ui_controls', []):
            w.setEnabled(enabled)
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
        
        # Delay, Feedback, Crossfeed, Dry mix
        controls = [
            ("Delay time", 0, 100, 20.0),
            ("Feedback gain", 0, 1, 0.3),
            ("Crossfeed", 0, 1, 0.3),
            ("Dry mix", 0, 1, 0.8)
        ]
        
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

            if not hasattr(self, 'ui_controls'): self.ui_controls = []
            self.ui_controls.extend([slider, lbl, val_lbl])
        
        layout.addStretch()
        self._toggle_ui(False)

    def _toggle_ui(self, enabled):
        for w in getattr(self, 'ui_controls', []):
            w.setEnabled(enabled)
        self.vlc.set_stereo_widener(enabled)


class AdvancedAudioWidget(QWidget):
    """Advanced audio settings (Pitch)."""
    def __init__(self, vlc, parent=None):
        super().__init__(parent)
        self.vlc = vlc
        layout = QVBoxLayout(self)
        
        self.chk_enable = QCheckBox("Enable")
        layout.addWidget(self.chk_enable)
        
        h = QHBoxLayout()
        layout.addLayout(h)
        
        slider = QSlider(Qt.Vertical)
        slider.setRange(50, 150) # 0.5x to 1.5x
        slider.setValue(100)
        slider.valueChanged.connect(lambda v: self.vlc.set_pitch(v/100.0))
        
        vbox = QVBoxLayout()
        vbox.addWidget(slider, 0, Qt.AlignHCenter)
        vbox.addWidget(QLabel("Adjust pitch"), 0, Qt.AlignHCenter)
        h.addLayout(vbox)
        h.addStretch()
        
        self.pitch_slider = slider
        
        layout.addStretch()
        self._toggle_ui(False)
        
    def _toggle_ui(self, enabled):
        self.pitch_slider.setEnabled(enabled)
        if not enabled:
            self.vlc.set_pitch(1.0) # Reset to normal
        else:
            self.vlc.set_pitch(self.pitch_slider.value()/100.0)


class AudioEffectsWidget(QWidget):
    """Container for Audio Effects Tabs."""
    def __init__(self, vlc, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        self.tabs = QTabWidget()
        self.tabs.addTab(EqualizerWidget(vlc, self), "Equalizer")
        self.tabs.addTab(CompressorWidget(vlc, self), "Compressor")
        self.tabs.addTab(SpatializerWidget(vlc, self), "Spatializer")
        self.tabs.addTab(StereoWidenerWidget(vlc, self), "Stereo Widener")
        self.tabs.addTab(AdvancedAudioWidget(vlc, self), "Advanced")
        
        layout.addWidget(self.tabs)


class EffectsAndFiltersDialog(QDialog):
    """Unified Effects and Filters Dialog."""
    
    def __init__(self, vlc_engine, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Adjustments and Effects")
        self.resize(600, 450)
        
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        
        # Audio Effects Tab (contains sub-tabs)
        self.tabs.addTab(AudioEffectsWidget(vlc_engine, self), "Audio Effects")
        
        self.tabs.addTab(VideoEffectsWidget(vlc_engine, self), "Video Effects")
        self.tabs.addTab(SyncWidget(vlc_engine, self), "Synchronization")
        
        layout.addWidget(self.tabs)
        
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.close)
        layout.addWidget(btns)


class MediaInfoWidget(QWidget):
    """General Media Info Tab."""
    def __init__(self, vlc_engine, parent=None):
        super().__init__(parent)
        self.vlc = vlc_engine
        layout = QGridLayout(self)
        
        # vlc.Meta IDs
        # To avoid attribute errors if vlc.Meta is not available or methods differ, we use safe access
        # But commonly vlc.Meta.Title etc exist.
        
        self.fields = [
            ("Title", 0),      # vlc.Meta.Title
            ("Artist", 1),     # vlc.Meta.Artist
            ("Album", 4),      # vlc.Meta.Album
            ("Genre", 2),      # vlc.Meta.Genre
            ("Now Playing", 12), # vlc.Meta.NowPlaying
            ("Publisher", 6),   # vlc.Meta.Publisher / Description? No, Publisher is 13 usually.
            ("Copyright", 3),   # vlc.Meta.Copyright
            ("Encoded by", 14)  # vlc.Meta.EncodedBy
        ]
        
        # Use integer constants to be safe
        # Title=0, Artist=1, Genre=2, Copyright=3, Album=4, TrackNumber=5, Description=6, Rating=7, Date=8, Setting=9, URL=10, Language=11, NowPlaying=12, Publisher=13, EncodedBy=14, ArtworkURL=15, TrackID=16
        
        # Verify and adjust if needed.
        _Meta = {
            "Title": 0, "Artist": 1, "Genre": 2, "Copyright": 3, "Album": 4, 
            "TrackNumber": 5, "Description": 6, "Rating": 7, "Date": 8, 
            "Setting": 9, "URL": 10, "Language": 11, "NowPlaying": 12, 
            "Publisher": 13, "EncodedBy": 14, "ArtworkURL": 15, "TrackID": 16
        }
        
        self.fields = [
            ("Title", _Meta["Title"]),
            ("Artist", _Meta["Artist"]),
            ("Album", _Meta["Album"]),
            ("Genre", _Meta["Genre"]),
            ("Now Playing", _Meta["NowPlaying"]),
            ("Publisher", _Meta["Publisher"]),
            ("Copyright", _Meta["Copyright"]),
            ("Encoded by", _Meta["EncodedBy"])
        ]

        self.widgets = {}
        row = 0
        for label, meta_id in self.fields:
            layout.addWidget(QLabel(label), row, 0)
            txt = QLineEdit("")
            txt.setReadOnly(True)
            layout.addWidget(txt, row, 1)
            self.widgets[meta_id] = txt
            row += 1
            
        # Comments / Description
        layout.addWidget(QLabel("Comments"), row, 0)
        self.txt_desc = QTextEdit("")
        self.txt_desc.setReadOnly(True)
        layout.addWidget(self.txt_desc, row, 1)
        
        self._meta_desc_id = _Meta["Description"]
        layout.setRowStretch(row+1, 1)
        self.refresh()

    def refresh(self):
        for meta_id, widget in self.widgets.items():
            val = self.vlc.get_meta(meta_id)
            widget.setText(val if val else "")
        
        desc = self.vlc.get_meta(self._meta_desc_id)
        self.txt_desc.setPlainText(desc if desc else "")


class MediaMetadataWidget(QWidget):
    """Metadata details tab showing raw tags."""
    def __init__(self, vlc_engine, parent=None):
        super().__init__(parent)
        self.vlc = vlc_engine
        layout = QVBoxLayout(self)
        self.txt = QTextEdit()
        self.txt.setReadOnly(True)
        layout.addWidget(self.txt)
        self.refresh()

    def refresh(self):
        try:
            # List many potential vlc.Meta index values
            # Title=0, Artist=1, Genre=2, Copyright=3, Album=4, TrackNumber=5, Description=6, Rating=7, Date=8, Setting=9, URL=10, Language=11, NowPlaying=12, Publisher=13, EncodedBy=14, ArtworkURL=15, TrackID=16
            keys = [
                ("Title", 0), ("Artist", 1), ("Genre", 2), ("Copyright", 3),
                ("Album", 4), ("Track Number", 5), ("Description", 6),
                ("Rating", 7), ("Date", 8), ("Setting", 9), ("URL", 10),
                ("Language", 11), ("Now Playing", 12), ("Publisher", 13),
                ("Encoded By", 14), ("Artwork URL", 15), ("Track ID", 16)
            ]
            keys = [
                ("Title", 0), ("Artist", 1), ("Genre", 2), ("Copyright", 3),
                ("Album", 4), ("Track Number", 5), ("Description", 6),
                ("Rating", 7), ("Date", 8), ("Setting", 9), ("URL", 10),
                ("Language", 11), ("Now Playing", 12), ("Publisher", 13),
                ("Encoded By", 14), ("Artwork URL", 15), ("Track ID", 16)
            ]
            text = ""
            found = False
            for label, mid in keys:
                val = self.vlc.get_meta(mid)
                if val:
                    text += f"{label}: {val}\n"
                    found = True
            
            if not found:
                text = "No metadata found. Try playing the media for a few seconds."
            
            self.txt.setPlainText(text)

        except Exception as e:
            self.txt.setPlainText(f"Error retrieving metadata: {e}")
            print(f"Error in MediaMetadataWidget.refresh: {e}")


class MediaCodecWidget(QWidget):
    """Codec Details Tab (Tree View)."""
    def __init__(self, vlc_engine, parent=None):
        super().__init__(parent)
        self.vlc = vlc_engine
        layout = QVBoxLayout(self)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(1)
        layout.addWidget(self.tree)
        
        self.refresh()
        
    def refresh(self):
        self.tree.clear()
        try:
            # 1. Get VLC Tracks (Base)
            tracks = self.vlc.get_tracks_info()
            
            # 2. Get FFprobe Data (Enrichment)
            ff_data = {}
            if self.vlc.media:
                mrl = self.vlc.media.get_mrl()
                if mrl and mrl.startswith("file:///"):
                    # Parse path
                    import urllib.parse
                    path = urllib.parse.unquote(mrl[8:])
                    # Call FFprobe
                    from src.core.ffprobe_service import FFprobeService
                    ff = FFprobeService()
                    ff_data = ff.get_metadata(path)

            if not tracks:
                item = QTreeWidgetItem(["No track information available."])
                self.tree.addTopLevelItem(item)
                return

            # Helper to find matching ffprobe stream
            def find_ff_stream(t_type_str, t_idx):
                # t_type_str: 'video', 'audio', 'subtitle'
                # t_idx: index within THAT type (logic might vary, let's use global index if possible? No, vlc tracks usually just list.
                # VLC tracks Ids are random.
                # But the ORDER in `tracks` list usually matches file order?
                # Best effort: Match by type and sequence.
                
                # Filter ff streams by type
                if t_type_str == 'video': pool = ff_data.get('video_streams', [])
                elif t_type_str == 'audio': pool = ff_data.get('audio_streams', [])
                elif t_type_str == 'subtitle': pool = ff_data.get('subtitle_streams', [])
                else: return None
                
                # We need to map VLC index to FF index. 
                # This is tricky without stream ID matching.
                # Let's assume sequential mapping for now (1st video track -> 1st ff video stream).
                # We need to count how many of this type we've seen so far in the VLC loop.
                return pool[t_idx] if t_idx < len(pool) else None

            # Counters for type index
            v_cnt, a_cnt, s_cnt = 0, 0, 0

            for i, track in enumerate(tracks):
                # Track type: -1=Unknown, 0=Audio, 1=Video, 2=Subtitle
                t_type_id = track.get('type', -1)
                t_type_str = "unknown"
                ff_info = None

                if t_type_id == 0: 
                    t_type = "Audio"
                    t_type_str = 'audio'
                    ff_info = find_ff_stream('audio', a_cnt)
                    a_cnt += 1
                elif t_type_id == 1: 
                    t_type = "Video"
                    t_type_str = 'video'
                    ff_info = find_ff_stream('video', v_cnt)
                    v_cnt += 1
                elif t_type_id == 2: 
                    t_type = "Subtitle"
                    t_type_str = 'subtitle'
                    ff_info = find_ff_stream('subtitle', s_cnt)
                    s_cnt += 1
                
                # Top Level: Stream N
                stream_item = QTreeWidgetItem([f"Stream {i}"])
                self.tree.addTopLevelItem(stream_item)
                stream_item.setExpanded(True)
                
                # Children
                self._add_item(stream_item, f"Type: {t_type}")
                
                # Codec (Use FFprobe long name if available for better text)
                codec = track.get('codec')
                orig = track.get('original_codec')
                
                codec_display = codec
                if ff_info and ff_info.get('codec_long'):
                    codec_display = f"{ff_info.get('codec_long')} ({codec})"
                elif orig and orig != codec:
                    codec_display = f"{codec} ({orig})"
                
                if codec_display:
                    self._add_item(stream_item, f"Codec: {codec_display}")

                # Language
                lang = track.get('language')
                if not lang and ff_info: lang = ff_info.get('tags', {}).get('language')
                if lang: self._add_item(stream_item, f"Language: {lang}")
                
                # Description
                desc = track.get('description')
                if not desc and ff_info: desc = ff_info.get('tags', {}).get('title') # Title is often used as desc
                if desc: self._add_item(stream_item, f"Description: {desc}")
                
                # Video Details
                vid = track.get('video')
                if t_type_id == 1:
                    # Resolution
                    w, h = 0, 0
                    if vid: 
                        w, h = vid.get('width', 0), vid.get('height', 0)
                    
                    if (w == 0 or h == 0) and ff_info:
                        w, h = ff_info.get('width', 0), ff_info.get('height', 0)

                    if w > 0 and h > 0:
                        self._add_item(stream_item, f"Video resolution: {w}x{h}")
                        # Buffer?
                        self._add_item(stream_item, f"Buffer dimensions: {w}x{h}") # VLC often doubles this, let's just assume match.

                    # Frame Rate
                    fps = 0
                    if vid:
                         num = vid.get('frame_rate_num', 0)
                         den = vid.get('frame_rate_den', 0)
                         if den > 0: fps = num/den
                    
                    if fps == 0 and ff_info:
                         fps = ff_info.get('fps', 0)
                    
                    if fps > 0:
                        self._add_item(stream_item, f"Frame rate: {fps:.6f}") # VLC uses high precision
                    
                    # FFprobe Extras (Color, etc.)
                    if ff_info:
                        pix = ff_info.get('pixel_format')
                        if pix: self._add_item(stream_item, f"Decoded format: {pix}") # Close enough to 'Planar 4:2:0 YUV' etc
                        
                        orient = vid.get('orientation', -1) if vid else -1
                        # Map internal or just skip if -1. 
                        # If VLC gave us -1, maybe we ignore?
                        # Actually FFprobe usually rotates automatically so streams are "upright".
                        # But let's show what VLC said if available.
                        if orient != -1:
                             orient_map = { 0: "Top left", 1: "Top right" } # Simplified
                             self._add_item(stream_item, f"Orientation: {orient_map.get(orient, 'Top left')}")

                        cp = ff_info.get('color_primaries')
                        if cp: self._add_item(stream_item, f"Color primaries: {cp}")
                        
                        ct = ff_info.get('color_transfer')
                        if ct: self._add_item(stream_item, f"Color transfer function: {ct}")
                        
                        cs = ff_info.get('color_space')
                        if cs: self._add_item(stream_item, f"Color space: {cs}")
                        
                        cr = ff_info.get('color_range')
                        if cr: self._add_item(stream_item, f"Color range: {cr}")

                        chroma = ff_info.get('chroma_location')
                        if chroma: self._add_item(stream_item, f"Chroma location: {chroma}")

                # Audio Details
                aud = track.get('audio')
                if t_type_id == 0:
                    ch = 0
                    if aud: ch = aud.get('channels', 0)
                    if ch == 0 and ff_info: ch = ff_info.get('channels', 0)
                    
                    if ch > 0:
                         layout = ""
                         if ff_info: layout = ff_info.get('channel_layout')
                         
                         if layout:
                             self._add_item(stream_item, f"Channels: {ch}")
                             self._add_item(stream_item, f"Decoded channels: {layout}") # e.g. 3F2M/LFE
                         else:
                             msg = str(ch)
                             if ch == 1: msg = "Mono"
                             elif ch == 2: msg = "Stereo"
                             elif ch == 6: msg = "3F2M/LFE" # Guess for 5.1
                             self._add_item(stream_item, f"Channels: {ch}")
                             self._add_item(stream_item, f"Decoded channels: {msg}")

                    rate = 0
                    if aud: rate = aud.get('rate', 0)
                    if rate == 0 and ff_info: rate = int(ff_info.get('sample_rate', 0))
                    
                    if rate > 0:
                        self._add_item(stream_item, f"Sample rate: {rate} Hz")
                    
                    # Decoded Format / Bits
                    if ff_info:
                         s_fmt = ff_info.get('sample_fmt')
                         bits = ff_info.get('bits_per_sample', 0)
                         
                         # Format Mapping Table
                         # Maps technical FFmpeg codes to readable VLC-style descriptions
                         fmt_map = {
                             'fltp': "32 bits float LE (f32l)",
                             'flt':  "32 bits float LE (flt)",
                             'dbl':  "64 bits Double (dbl)",
                             'dblp': "64 bits Double Planar (dblp)",
                             's16':  "16 bits Integer (s16)",
                             's16p': "16 bits Integer Planar (s16p)",
                             's32':  "32 bits Integer (s32)",
                             's32p': "32 bits Integer Planar (s32p)",
                             'u8':   "8 bits Unsigned (u8)",
                             'u8p':  "8 bits Unsigned Planar (u8p)",
                         }

                         # Fallback bits logic if not provided
                         if bits == 0:
                             if 'flt' in s_fmt or 's32' in s_fmt: bits = 32
                             elif 'dbl' in s_fmt: bits = 64
                             elif 's16' in s_fmt: bits = 16
                             elif 'u8' in s_fmt: bits = 8
                         
                         # Get readable description or use raw format
                         desc = fmt_map.get(s_fmt, s_fmt)
                         
                         if desc:
                             self._add_item(stream_item, f"Decoded format: {desc}")
                         
                         if bits > 0:
                             self._add_item(stream_item, f"Decoded bits per sample: {bits}")

                # Subtitle Details
                sub = track.get('subtitle')
                if t_type_id == 2:
                    enc = sub.get('encoding') if sub else None
                    if enc:
                        self._add_item(stream_item, f"Encoding: {enc}")

                # General fields
                tid = track.get('id', -1)
                if tid != -1: self._add_item(stream_item, f"ID: {tid}")
                
                prof = track.get('profile', -1)
                if prof != -1: self._add_item(stream_item, f"Profile: {prof}")
                
                lvl = track.get('level', -1)
                if lvl != -1 and lvl != 0: self._add_item(stream_item, f"Level: {lvl}")
                
                bitrate = track.get('bitrate', 0)
                if bitrate == 0 and ff_info: bitrate = ff_info.get('bitrate', 0)
                
                if bitrate > 0:
                     self._add_item(stream_item, f"Bitrate: {bitrate // 1000} kb/s")

        except Exception as e:
            item = QTreeWidgetItem([f"Error retrieving info: {e}"])
            self.tree.addTopLevelItem(item)
            print(f"Error in MediaCodecWidget.refresh: {e}")
            import traceback
            traceback.print_exc()

    def _add_item(self, parent, text):
        item = QTreeWidgetItem([text])
        parent.addChild(item)


class MediaStatsWidget(QWidget):
    """Statistics Tab."""
    def __init__(self, vlc_engine, parent=None):
        super().__init__(parent)
        self.vlc = vlc_engine
        layout = QGridLayout(self)
        
        self.labels = {}
        
        # Groups matching VLC stats
        groups = [
            ("Audio", ["Decoded audio blocks", "Played audio buffers", "Lost audio buffers"]),
            ("Video", ["Decoded video blocks", "Displayed frames", "Lost frames"]),
            ("Input/Read", ["Media data size", "Input bitrate", "Demuxed data size", "Content bitrate", "Discarded (corrupted)", "Dropped (discontinued)"])
        ]
        
        row = 0
        for grp, items in groups:
            gb = QGroupBox(grp)
            l = QFormLayout(gb)
            for item in items:
                lbl = QLabel("0")
                l.addRow(item, lbl)
                self.labels[item] = lbl
            layout.addWidget(gb, row, 0)
            row += 1

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update)
        self.timer.start(1000)
        self._update()
        
        layout.setRowStretch(row, 1)

    def _update(self):
        # log_debug("MediaStatsWidget._update") 
        # Don't log spam
        try:
            stats = self.vlc.get_stats()
            if not stats: return
            
            # Helper to safely get attributes
            def safe_get(obj, attr, default=0):
                return getattr(obj, attr, default)
            
            def set_lbl(key, val):
                if key in self.labels:
                    self.labels[key].setText(str(val))
            
            set_lbl("Decoded audio blocks", safe_get(stats, 'decoded_audio'))
            set_lbl("Played audio buffers", safe_get(stats, 'played_abuffers'))
            set_lbl("Lost audio buffers", safe_get(stats, 'lost_abuffers'))
            
            set_lbl("Decoded video blocks", safe_get(stats, 'decoded_video'))
            set_lbl("Displayed frames", safe_get(stats, 'displayed_pictures'))
            set_lbl("Lost frames", safe_get(stats, 'lost_pictures'))
            
            read_bytes = safe_get(stats, 'read_bytes')
            set_lbl("Media data size", f"{read_bytes / 1024:.0f} KiB")
            
            input_bitrate = safe_get(stats, 'input_bitrate')
            set_lbl("Input bitrate", f"{input_bitrate * 8000:.0f} kb/s")
            
            demux_read_bytes = safe_get(stats, 'demux_read_bytes')
            set_lbl("Demuxed data size", f"{demux_read_bytes / 1024:.0f} KiB")
            
            demux_bitrate = safe_get(stats, 'demux_bitrate')
            set_lbl("Content bitrate", f"{demux_bitrate * 8000:.0f} kb/s")
            
            set_lbl("Discarded (corrupted)", safe_get(stats, 'demux_corrupted'))
            set_lbl("Dropped (discontinued)", safe_get(stats, 'demux_discontinued'))
        except Exception as e:
            pass

class MediaInfoDialog(QDialog):
    """Media Information Dialog."""
    def __init__(self, vlc_engine, parent=None, initial_tab=0):
        super().__init__(parent)
        self.setWindowTitle("Current Media Information")
        self.resize(600, 500)
        self.vlc = vlc_engine
        
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        self.tab_info = MediaInfoWidget(vlc_engine)
        self.tab_metadata = MediaMetadataWidget(vlc_engine)
        self.tab_codec = MediaCodecWidget(vlc_engine)
        self.tab_stats = MediaStatsWidget(vlc_engine)
        
        self.tabs.addTab(self.tab_info, "General")
        self.tabs.addTab(self.tab_metadata, "Metadata")
        self.tabs.addTab(self.tab_codec, "Codec")
        self.tabs.addTab(self.tab_stats, "Statistics")
        
        if initial_tab > 0 and initial_tab < self.tabs.count():
            self.tabs.setCurrentIndex(initial_tab)
            
        layout.addWidget(self.tabs)
        
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.close)
        layout.addWidget(btns)
        
        self.tabs.currentChanged.connect(self.refresh_current_tab)

    def refresh_current_tab(self):
        idx = self.tabs.currentIndex()
        if idx == 0:
            self.tab_info.refresh()
        elif idx == 1:
            self.tab_metadata.refresh()
        elif idx == 2:
            self.tab_codec.refresh()
        # Stats has its own timer

    def showEvent(self, event):
        self.refresh_current_tab()
        super().showEvent(event)


class ShortcutsHelpDialog(QDialog):
    """VLC-style Keyboard Shortcuts reference."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts help")
        self.resize(500, 600)
        
        layout = QVBoxLayout(self)
        
        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml("""
            <h3>Playback & Speed</h3>
            <ul>
                <li><b>Space</b>: Play/Pause</li>
                <li><b>S</b>: Stop</li>
                <li><b>N / P</b>: Next / Previous file</li>
                <li><b>+ / - / =</b>: Speed Up / Slow Down / Reset</li>
                <li><b>E</b>: Next Frame</li>
            </ul>
            <h3>Navigation (Seeking)</h3>
            <ul>
                <li><b>Shift + Left/Right</b>: Jump 5s</li>
                <li><b>Left/Right</b>: Jump 10s</li>
                <li><b>Ctrl + Left/Right</b>: Jump 1m</li>
                <li><b>Ctrl + Alt + Left/Right</b>: Jump 5m</li>
            </ul>
            <h3>Audio & Subtitles</h3>
            <ul>
                <li><b>Ctrl + Up/Down</b> / <b>Wheel</b>: Volume Control</li>
                <li><b>M</b>: Mute</li>
                <li><b>B</b>: Cycle Audio Track</li>
                <li><b>Shift + A</b>: Cycle Audio Device</li>
                <li><b>V / Alt + V</b>: Cycle Subtitles (Forward/Reverse)</li>
                <li><b>Shift + V</b>: Toggle Subtitles</li>
                <li><b>J / K</b>: Audio Delay Control</li>
                <li><b>G / H</b>: Subtitle Delay Control</li>
                <li><b>Ctrl + 0 / Ctrl+Wheel</b>: Subtitle Scale Reset/Adjust</li>
            </ul>
            <h3>Display</h3>
            <ul>
                <li><b>F / Double Click</b>: Toggle Fullscreen</li>
                <li><b>A / C</b>: Cycle Aspect Ratio / Crop</li>
                <li><b>O</b>: Toggle Autoscale (Fit/Original)</li>
                <li><b>Alt + O / Alt+Shift+O</b>: Video Scale Adjustment</li>
                <li><b>Z / Shift + Z</b>: Zoom (Forward/Reverse)</li>
                <li><b>D / Shift + D</b>: Toggle/Cycle Deinterlacing</li>
                <li><b>W</b>: Toggle Wallpaper Mode (DirectX)</li>

                <li><b>Ctrl + 0 / Ctrl + Wheel</b>: Reset / Scale Subtitles</li>
                <li><b>I</b>: Show Interface/OSD</li>
                <li><b>X / Shift + X</b>: Cycle Program (Next/Prev)</li>
                <li><b>Alt + R/D/C/F</b>: Granular Crop (Top/Left/Bottom/Right)</li>
                <li><b>Alt + 1 / 2 / 3 / 4</b>: Window Resize (1:4, 1:2, 1:1, 2:1)</li>
                <li><b>Page Up / Page Down</b>: 360 Viewpoint (Shrink/Expand)</li>
                <li><b>Ctrl + F1..F10</b>: Set Playlist Bookmark 1..10</li>
                <li><b>F1..F10</b>: Go to Playlist Bookmark 1..10</li>
                <li><b>Shift + S / Shift + R</b>: Snapshot / Record</li>
            </ul>
            <h3>Global</h3>
            <ul>
                <li><b>Ctrl + O / F / D / C</b>: Open File / Folder / Disc / Capture</li>
                <li><b>Ctrl + Q / P / Y</b>: Quit / Preferences / Save Playlist</li>
                <li><b>Ctrl + V / Shift+W</b>: Paste MRL / VLM Config</li>
                <li><b>Shift + G / H</b>: History Back / Forward</li>
                <li><b>Ctrl + A / B / H / M</b>: Advanced / Bookmarks / Minimal / Messages</li>


                <li><b>Shift + F1</b>: This Help</li>

            </ul>
        """)
        layout.addWidget(text)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok)
        btns.accepted.connect(self.accept)
        layout.addWidget(btns)


class AboutDialog(QDialog):
    """About Omneva Dialog."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About Omneva")
        self.resize(350, 200)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        title = QLabel("Omneva Media Suite")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        version = QLabel("Version 1.0.0")
        layout.addWidget(version)
        
        desc = QLabel("A powerful, cross-platform media player powered by VLC and FFmpeg.")
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc)
        
        author = QLabel("Built by Antigravity")
        layout.addWidget(author)
        
        btns = QDialogButtonBox(QDialogButtonBox.Ok)
        btns.accepted.connect(self.accept)
        layout.addWidget(btns)


class MessagesDialog(QDialog):
    """VLC-style Messages Dialog (Log viewer)."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Messages")
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("background: #111; color: #0f0; font-family: 'Consolas', 'Monaco', monospace;")
        layout.addWidget(self.log_text)
        
        self.log_text.append("[System] Omneva Media Player Started")
        self.log_text.append("[VLC] LibVLC loaded successfully")
        
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.reject)
        
        btn_clear = btns.addButton("Clear", QDialogButtonBox.ActionRole)
        btn_clear.clicked.connect(self.log_text.clear)
        
        layout.addWidget(btns)


class OpenDiscDialog(QDialog):
    """VLC-style Open Disc Dialog."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Open Disc")
        self.setFixedWidth(400)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Disc Type
        type_group = QGroupBox("Disc Selection")
        type_layout = QHBoxLayout(type_group)
        self.radio_dvd = QRadioButton("DVD")
        self.radio_bluray = QRadioButton("Blu-ray")
        self.radio_audio_cd = QRadioButton("Audio CD / SVCD")
        self.radio_dvd.setChecked(True)
        
        type_layout.addWidget(self.radio_dvd)
        type_layout.addWidget(self.radio_bluray)
        type_layout.addWidget(self.radio_audio_cd)
        layout.addWidget(type_group)
        
        # Disc Device
        dev_layout = QHBoxLayout()
        dev_layout.addWidget(QLabel("Disc device:"))
        self.drive_combo = QComboBox()
        self._find_drives()
        dev_layout.addWidget(self.drive_combo, 1)
        self.btn_browse = QPushButton("Browse...")
        dev_layout.addWidget(self.btn_browse)
        layout.addLayout(dev_layout)
        
        # Options
        options_group = QGroupBox("Starting Position")
        options_layout = QFormLayout(options_group)
        self.spin_title = QSpinBox()
        self.spin_chapter = QSpinBox()
        options_layout.addRow("Title:", self.spin_title)
        options_layout.addRow("Chapter:", self.spin_chapter)
        layout.addWidget(options_group)
        
        btns = QDialogButtonBox(QDialogButtonBox.Open | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

        self.btn_browse.clicked.connect(self._browse_drive)

    def _find_drives(self):
        """Find optical drives on Windows."""
        import os
        if os.name == 'nt':
            import string
            from ctypes import windll
            bitmask = windll.kernel32.GetLogicalDrives()
            for letter in string.ascii_uppercase:
                if bitmask & 1:
                    drive = f"{letter}:\\"
                    # DRIVE_CDROM = 5
                    if windll.kernel32.GetDriveTypeW(drive) == 5:
                        self.drive_combo.addItem(drive)
                bitmask >>= 1
        
        if self.drive_combo.count() == 0:
            self.drive_combo.addItem("D:\\") # Default fallback

    def _browse_drive(self):
        path = QFileDialog.getExistingDirectory(self, "Select Disc Drive")
        if path:
            if not path.endswith("\\") and not path.endswith("/"):
                path += "\\"
            self.drive_combo.setEditText(path)

    def get_mrl(self) -> str:
        """Construct VLC MRL."""
        drive = self.drive_combo.currentText()
        if self.radio_bluray.isChecked(): protocol = "bluray://"
        elif self.radio_audio_cd.isChecked(): protocol = "cdda://"
        else: protocol = "dvd://"
        
        # Title/Chapter options
        mrl = f"{protocol}{drive}"
        # We could add @title:chapter here if needed for direct jump
        return mrl


class VideoEffectsDialog(QDialog):
    """VLC-style Video Effects (Adjustments and Filters)."""
    def __init__(self, vlc_engine, parent=None):
        super().__init__(parent)
        self.vlc = vlc_engine
        self.setWindowTitle("Video Effects")
        self.resize(350, 450)
        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        # ─── Adjust Tab ───
        self.adjust_tab = QWidget()
        adj_layout = QVBoxLayout(self.adjust_tab)
        
        self.chk_enable_adj = QCheckBox("Enable")
        adj_layout.addWidget(self.chk_enable_adj)
        
        from vlc import VideoAdjustOption
        self.sliders = {}
        for label, opt in [
            ("Brightness", VideoAdjustOption.Brightness),
            ("Contrast", VideoAdjustOption.Contrast),
            ("Saturation", VideoAdjustOption.Saturation),
            ("Gamma", VideoAdjustOption.Gamma),
            ("Hue", VideoAdjustOption.Hue)
        ]:
            row = QVBoxLayout()
            row.addWidget(QLabel(label))
            s = QSlider(Qt.Horizontal)
            s.setRange(0, 200) # 100 is default (1.0)
            if label == "Hue": s.setRange(-180, 180); s.setValue(0)
            else: s.setValue(100)
            
            s.valueChanged.connect(lambda v, o=opt: self._on_adjust_changed(o, v))
            row.addWidget(s)
            adj_layout.addLayout(row)
            self.sliders[opt] = s

        self.tabs.addTab(self.adjust_tab, "Essential")
        
        # ─── Geometry Tab ───
        self.geom_tab = QWidget()
        geom_layout = QVBoxLayout(self.geom_tab)
        
        self.chk_transform = QCheckBox("Transform")
        self.combo_rotate = QComboBox()
        self.combo_rotate.addItems(["Rotate by 90 degrees", "Rotate by 180 degrees", "Rotate by 270 degrees", "Flip horizontally", "Flip vertically"])
        self.combo_rotate.setEnabled(False)
        
        geom_layout.addWidget(self.chk_transform)
        geom_layout.addWidget(self.combo_rotate)
        
        self.chk_rotate_arbitrary = QCheckBox("Rotate")
        self.dial_rotate = QSlider(Qt.Horizontal) # Use slider as simpler dial
        self.dial_rotate.setRange(0, 360)
        self.dial_rotate.setEnabled(False)
        geom_layout.addWidget(self.chk_rotate_arbitrary)
        geom_layout.addWidget(self.dial_rotate)
        
        geom_layout.addStretch()
        self.tabs.addTab(self.geom_tab, "Geometry")
        
        layout.addWidget(self.tabs)
        
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(self.close)
        layout.addWidget(btns)

        # Signals
        self.chk_enable_adj.toggled.connect(self.vlc.enable_video_adjust)
        self.chk_transform.toggled.connect(self._toggle_transform)
        self.combo_rotate.currentIndexChanged.connect(self._on_transform_changed)

    def _on_adjust_changed(self, option, value):
        if not self.chk_enable_adj.isChecked():
            return
        if option == 4: # Hue
            self.vlc.set_adjust_int(option, value)
        else:
            self.vlc.set_adjust_float(option, value / 100.0)

    def _toggle_transform(self, enabled):
        self.combo_rotate.setEnabled(enabled)
        if not enabled:
            self.vlc.set_rotate(0)
        else:
            self._on_transform_changed(self.combo_rotate.currentIndex())

    def _on_transform_changed(self, index):
        angles = [90, 180, 270, -1, -2]
        self.vlc.set_rotate(angles[index])



