"""Video Settings Tab for Transcoder."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QRadioButton, QSlider, QSpinBox, QCheckBox, QLineEdit,
    QGroupBox, QFormLayout, QFrame
)
from PySide6.QtCore import Qt, Signal

from src.core.ffmpeg_service import FFmpegService

class VideoSettingsTab(QWidget):
    """
    Video encoding settings tab matching HandBrake's layout.
    Allows configuring Encoder, FPS, Quality (RF/Bitrate), and Advanced Options.
    """
    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("videoTab")
        self.ffmpeg = FFmpegService()
        self.hardware_encoders = {}
        self._setup_ui()
        self._connect_signals()
        self._detect_hardware_encoders()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(15)

        # ─── Top Section: Encoder & Quality ──────────────────
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)

        # Left Column: Codec & Framerate
        left_col = QVBoxLayout()
        
        # Video Encoder
        self.combo_encoder = QComboBox()
        self.combo_encoder.addItems([
            "H.264 (x264)", "H.265 (x265)",
            "H.264 (NVENC)", "H.265 (NVENC)",
            "H.264 (QSV)", "H.265 (QSV)",
            "AV1 (SVT-AV1)", "VP9", "VP8",
            "MPEG-4 (mp4v)", "MPEG-2 (mp2v)", "MPEG-1 (mp1v)",
            "Theora", "DV Video (dvsd)",
            "Sorenson v1 (SVQ1)", "Sorenson v3 (SVQ3)"
        ])

        left_col.addWidget(QLabel("Video Encoder:"))
        left_col.addWidget(self.combo_encoder)

        # Framerate
        self.combo_fps = QComboBox()
        self.combo_fps.addItems([
            "Same as source", "23.976", "24", "25", "29.97", "30", "50", "59.94", "60"
        ])
        left_col.addWidget(QLabel("Framerate (FPS):"))
        left_col.addWidget(self.combo_fps)

        # Variable/Constant Framerate
        self.radio_vfr = QRadioButton("Variable Framerate")
        self.radio_cfr = QRadioButton("Constant Framerate")
        self.radio_vfr.setChecked(True)
        
        fps_mode_layout = QVBoxLayout()
        fps_mode_layout.addWidget(self.radio_vfr)
        fps_mode_layout.addWidget(self.radio_cfr)
        left_col.addLayout(fps_mode_layout)

        left_col.addStretch()
        top_layout.addLayout(left_col, 1)

        # Right Column: Quality
        right_col = QVBoxLayout()
        right_col.addWidget(QLabel("Quality:"))

        # Constant Quality (RF)
        rf_layout = QHBoxLayout()
        self.radio_rf = QRadioButton("Constant Quality:")
        self.radio_rf.setChecked(True)
        
        self.spin_rf = QSpinBox()
        self.spin_rf.setRange(0, 51)
        self.spin_rf.setValue(22)
        
        self.slider_rf = QSlider(Qt.Horizontal)
        self.slider_rf.setRange(0, 51)
        self.slider_rf.setValue(22)
        self.slider_rf.setInvertedAppearance(True) # Lower RF is higher quality (usually right is higher quality)
        # Actually in HandBrake slider goes right -> higher quality (lower RF)
        # So 51 (left) -> 0 (right). 
        # range 0-51 inverted: 0(left, bad) is actually 51. 51(right, good) is 0.
        # Let's map slider 0..51 to RF 51..0
        
        rf_layout.addWidget(self.radio_rf)
        rf_layout.addWidget(self.spin_rf)
        rf_layout.addWidget(QLabel("RF"))
        
        right_col.addLayout(rf_layout)
        right_col.addWidget(self.slider_rf)

        # Avg Bitrate
        bitrate_layout = QHBoxLayout()
        self.radio_bitrate = QRadioButton("Avg Bitrate (kbps):")
        self.spin_bitrate = QSpinBox()
        self.spin_bitrate.setRange(100, 500000)
        self.spin_bitrate.setValue(2500)
        self.spin_bitrate.setEnabled(False)
        self.spin_bitrate.setSuffix(" kbps")

        bitrate_layout.addWidget(self.radio_bitrate)
        bitrate_layout.addWidget(self.spin_bitrate)
        right_col.addLayout(bitrate_layout)

        # Multi-pass / Turbo
        self.check_multipass = QCheckBox("2-Pass Encoding")
        self.check_turbo = QCheckBox("Turbo first pass")
        self.check_multipass.setEnabled(False)
        self.check_turbo.setEnabled(False)
        
        checks_layout = QHBoxLayout()
        checks_layout.addWidget(self.check_multipass)
        checks_layout.addWidget(self.check_turbo)
        right_col.addLayout(checks_layout)
        
        right_col.addStretch()
        top_layout.addLayout(right_col, 2)

        main_layout.addLayout(top_layout)

        # ─── Separator ───────────────────────────────────────
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # ─── Encoder Options ─────────────────────────────────
        opts_group = QGroupBox("Encoder Options")
        opts_layout = QFormLayout(opts_group)

        # Preset Slider
        preset_row = QHBoxLayout()
        self.slider_preset = QSlider(Qt.Horizontal)
        self.slider_preset.setRange(0, 9)
        self.slider_preset.setTickPosition(QSlider.TicksBelow)
        self.slider_preset.setTickInterval(1)
        # 0=ultrafast, 1=superfast, ... 5=medium ... 9=placebo
        self.slider_preset.setValue(5) # Medium
        
        self.lbl_preset = QLabel("Medium")
        preset_row.addWidget(self.slider_preset)
        preset_row.addWidget(self.lbl_preset)
        
        opts_layout.addRow("Encoder Preset:", preset_row)

        # Tune
        self.combo_tune = QComboBox()
        self.combo_tune.addItems(["None", "Film", "Animation", "Grain", "Still Image", "Fast Decode", "Zero Latency"])
        opts_layout.addRow("Encoder Tune:", self.combo_tune)

        # Profile
        self.combo_profile = QComboBox()
        self.combo_profile.addItems(["Auto", "Baseline", "Main", "High", "High 10", "High 4:2:2"])
        self.combo_profile.setCurrentText("High")
        opts_layout.addRow("Encoder Profile:", self.combo_profile)

        # Level
        self.combo_level = QComboBox()
        self.combo_level.addItems(["Auto"] + [str(x/10) for x in range(10, 63)]) # 1.0 to 6.2
        opts_layout.addRow("Encoder Level:", self.combo_level)

        # Advanced options
        self.txt_advanced = QLineEdit()
        self.txt_advanced.setPlaceholderText("e.g. keyint=1:min-keyint=1:ref=1")
        opts_layout.addRow("Advanced Options:", self.txt_advanced)

        main_layout.addWidget(opts_group)
        main_layout.addStretch()

    def _detect_hardware_encoders(self):
        """Detect available hardware encoders and update UI accordingly."""
        try:
            self.hardware_encoders = self.ffmpeg.get_available_hardware_encoders()
            self._update_encoder_availability()
        except Exception:
            # If detection fails, assume no hardware encoders available
            self.hardware_encoders = {'nvenc': False, 'qsv': False, 'videotoolbox': False, 'amf': False}
            self._update_encoder_availability()

    def _update_encoder_availability(self):
        """Update encoder dropdown based on available hardware encoders."""
        # Store current selection
        current_selection = self.combo_encoder.currentText()
        
        # Disable hardware encoders that aren't available
        for i in range(self.combo_encoder.count()):
            encoder_text = self.combo_encoder.itemText(i)
            should_disable = False
            tooltip_text = ""
            
            if "NVENC" in encoder_text:
                should_disable = not self.hardware_encoders.get('nvenc', False)
                if should_disable:
                    tooltip_text = "NVIDIA NVENC not available - requires NVIDIA GPU with proper drivers"
                    
            elif "QSV" in encoder_text:
                should_disable = not self.hardware_encoders.get('qsv', False)
                if should_disable:
                    tooltip_text = "Intel Quick Sync Video not available - requires Intel GPU with supported generation"
                    
            elif "VideoToolbox" in encoder_text:
                should_disable = not self.hardware_encoders.get('videotoolbox', False)
                if should_disable:
                    tooltip_text = "macOS VideoToolbox not available - requires macOS with supported hardware"
                    
            elif "AMF" in encoder_text:
                should_disable = not self.hardware_encoders.get('amf', False)
                if should_disable:
                    tooltip_text = "AMD AMF not available - requires AMD GPU with proper drivers"
            
            # Update item state
            model = self.combo_encoder.model()
            item = model.item(i)
            if item:
                item.setEnabled(not should_disable)
                if should_disable:
                    item.setToolTip(tooltip_text)
                else:
                    item.setToolTip("")
        
        # If current selection is disabled, switch to a software encoder
        current_index = self.combo_encoder.findText(current_selection)
        if current_index >= 0:
            current_item = self.combo_encoder.model().item(current_index)
            if current_item and not current_item.isEnabled():
                # Switch to first available software encoder
                for i in range(self.combo_encoder.count()):
                    encoder_text = self.combo_encoder.itemText(i)
                    if ("x264" in encoder_text or "x265" in encoder_text or 
                        "SVT-AV1" in encoder_text or "VP9" in encoder_text or "VP8" in encoder_text or
                        "MPEG-" in encoder_text or "Theora" in encoder_text or "DV Video" in encoder_text or
                        "Sorenson" in encoder_text):
                        item = self.combo_encoder.model().item(i)
                        if item and item.isEnabled():
                            self.combo_encoder.setCurrentIndex(i)
                            break

    def _connect_signals(self):
        # Slider <-> Spinbox for RF
        self.slider_rf.valueChanged.connect(self._on_rf_slider_changed)
        self.spin_rf.valueChanged.connect(self._on_rf_spin_changed)
        
        # Radio buttons enable/disable
        self.radio_rf.toggled.connect(self._toggle_quality_mode)
        self.radio_bitrate.toggled.connect(self._toggle_quality_mode)

        # Preset label update
        self.slider_preset.valueChanged.connect(self._update_preset_label)

    def _on_rf_slider_changed(self, val):
        # Inverted mapping: Slider 0 (left) = 51 (bad), Slider 51 (right) = 0 (good)
        rf_val = 51 - val
        self.spin_rf.blockSignals(True)
        self.spin_rf.setValue(rf_val)
        self.spin_rf.blockSignals(False)

    def _on_rf_spin_changed(self, val):
        slider_val = 51 - val
        self.slider_rf.blockSignals(True)
        self.slider_rf.setValue(slider_val)
        self.slider_rf.blockSignals(False)

    def _toggle_quality_mode(self):
        is_rf = self.radio_rf.isChecked()
        self.slider_rf.setEnabled(is_rf)
        self.spin_rf.setEnabled(is_rf)
        
        self.spin_bitrate.setEnabled(not is_rf)
        self.check_multipass.setEnabled(not is_rf)
        self.check_turbo.setEnabled(not is_rf)

    def _update_preset_label(self, val):
        presets = ["Ultrafast", "Superfast", "Veryfast", "Faster", "Fast", "Medium", "Slow", "Slower", "Veryslow", "Placebo"]
        if 0 <= val < len(presets):
            self.lbl_preset.setText(presets[val])

    def get_settings(self) -> dict:
        """Collect current settings into a text-friendly dict or args list."""
        # Simple extraction logic - returns dict for now
        return {
            "encoder": self.combo_encoder.currentText(),
            "fps": self.combo_fps.currentText(),
            "fps_mode": "vfr" if self.radio_vfr.isChecked() else "cfr",
            "quality_mode": "rf" if self.radio_rf.isChecked() else "bitrate",
            "rf": self.spin_rf.value(),
            "rf_value": self.spin_rf.value(),  # For import compatibility
            "bitrate": self.spin_bitrate.value(),
            "two_pass": self.check_multipass.isChecked(),
            "preset": self.lbl_preset.text().lower(),
            "preset_value": self.slider_preset.value(),  # For import compatibility
            "tune": self.combo_tune.currentText(),
            "profile": self.combo_profile.currentText(),
            "level": self.combo_level.currentText(),
            "advanced": self.txt_advanced.text()
        }
