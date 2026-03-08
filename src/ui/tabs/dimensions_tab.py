"""Dimensions Tab for Transcoder - Cropping, Scaling, and Orientation."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QSpinBox, QGroupBox, QGridLayout, QFrame
)
from PySide6.QtCore import Qt, Signal

class DimensionsTab(QWidget):
    """
    Dimensions/Geometry settings tab.
    Handles cropping, rotation, resolution scaling, and borders/padding.
    """
    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dimensionsTab")
        self._source_width = 1920
        self._source_height = 1080
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(20)

        # ─── Source Info ────────────────────────────────────
        info_layout = QHBoxLayout()
        self.lbl_source_dim = QLabel("Source Dimensions: 1920x1080")
        self.lbl_source_dim.setStyleSheet("font-weight: bold; color: #ccc;")
        info_layout.addWidget(self.lbl_source_dim)
        info_layout.addStretch()
        main_layout.addLayout(info_layout)

        # ─── Grid Layout for 3 Groups ───────────────────────
        grid = QGridLayout()
        grid.setSpacing(20)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        # ─── 1. Orientation & Cropping ──────────────────────
        grp_crop = QGroupBox("Orientation and Cropping")
        crop_layout = QGridLayout(grp_crop)
        crop_layout.setVerticalSpacing(10)

        # Flip / Rotation
        crop_layout.addWidget(QLabel("Flip:"), 0, 0)
        self.chk_flip = QCheckBox("Horizontal")
        crop_layout.addWidget(self.chk_flip, 0, 1)

        crop_layout.addWidget(QLabel("Rotation:"), 1, 0)
        self.combo_rotation = QComboBox()
        self.combo_rotation.addItems(["0", "90", "180", "270"])
        crop_layout.addWidget(self.combo_rotation, 1, 1)

        # Cropping Mode
        crop_layout.addWidget(QLabel("Cropping:"), 2, 0)
        self.combo_crop_mode = QComboBox()
        self.combo_crop_mode.addItems(["None", "Custom"]) # Auto not impl yet
        crop_layout.addWidget(self.combo_crop_mode, 2, 1)

        # Crop Spinboxes (Diamond layout)
        self.spin_crop_top = self._create_spinbox()
        self.spin_crop_bottom = self._create_spinbox()
        self.spin_crop_left = self._create_spinbox()
        self.spin_crop_right = self._create_spinbox()

        # Layout for crop spins: 
        #       Top
        # Left      Right
        #      Bottom
        crop_spins = QGridLayout()
        crop_spins.addWidget(self.spin_crop_top, 0, 1)
        crop_spins.addWidget(self.spin_crop_left, 1, 0)
        crop_spins.addWidget(self.spin_crop_right, 1, 2)
        crop_spins.addWidget(self.spin_crop_bottom, 2, 1)
        
        # Add labels
        crop_spins.addWidget(QLabel("Top"), 0, 0, Qt.AlignRight)
        crop_spins.addWidget(QLabel("Bottom"), 2, 0, Qt.AlignRight)
        
        # Add to main crop layout at row 3, spanning 2 cols
        crop_layout.addLayout(crop_spins, 3, 0, 1, 2)
        crop_layout.setRowStretch(4, 1) # Push up

        grid.addWidget(grp_crop, 0, 0)

        # ─── 2. Resolution and Scaling ──────────────────────
        grp_scale = QGroupBox("Resolution and Scaling")
        scale_layout = QGridLayout(grp_scale)
        scale_layout.setVerticalSpacing(10)

        # Res Limit
        scale_layout.addWidget(QLabel("Resolution Limit:"), 0, 0)
        self.combo_res_limit = QComboBox()
        self.combo_res_limit.addItems([
            "No Limit", "4320p 8K", "2160p 4K", "1440p 2K", 
            "1080p HD", "720p HD", "576p PAL", "480p NTSC"
        ])
        self.combo_res_limit.setCurrentText("1080p HD")
        scale_layout.addWidget(self.combo_res_limit, 0, 1)

        # Anamorphic
        scale_layout.addWidget(QLabel("Anamorphic:"), 1, 0)
        self.combo_anamorphic = QComboBox()
        self.combo_anamorphic.addItems(["None", "Strict", "Loose"])
        scale_layout.addWidget(self.combo_anamorphic, 1, 1)

        # Scaled Size
        scale_layout.addWidget(QLabel("Scaled Size:"), 2, 0)
        
        size_layout = QHBoxLayout()
        self.spin_width = self._create_spinbox(1920, 7680)
        self.spin_height = self._create_spinbox(1080, 4320)
        size_layout.addWidget(self.spin_width)
        size_layout.addWidget(QLabel("x"))
        size_layout.addWidget(self.spin_height)
        scale_layout.addLayout(size_layout, 2, 1)

        # Optimal Size / Upscale
        self.chk_optimal = QCheckBox("Optimal Size")
        self.chk_optimal.setChecked(True)
        scale_layout.addWidget(self.chk_optimal, 3, 1)
        
        self.chk_upscale = QCheckBox("Allow Upscaling")
        scale_layout.addWidget(self.chk_upscale, 4, 1)
        
        scale_layout.setRowStretch(5, 1)
        grid.addWidget(grp_scale, 0, 1)

        # ─── 3. Borders ─────────────────────────────────────
        grp_borders = QGroupBox("Borders")
        border_layout = QGridLayout(grp_borders)
        border_layout.setVerticalSpacing(10)

        # Fill (Color? or Logic?) HandBrake has Fill: None/Custom
        border_layout.addWidget(QLabel("Fill:"), 0, 0)
        self.combo_fill = QComboBox()
        self.combo_fill.addItems(["None", "Custom"])
        border_layout.addWidget(self.combo_fill, 0, 1)

        # Border Spinboxes
        self.spin_bor_top = self._create_spinbox()
        self.spin_bor_bottom = self._create_spinbox()
        self.spin_bor_left = self._create_spinbox()
        self.spin_bor_right = self._create_spinbox()

        bor_spins = QGridLayout()
        bor_spins.addWidget(self.spin_bor_top, 0, 1)
        bor_spins.addWidget(self.spin_bor_left, 1, 0)
        bor_spins.addWidget(self.spin_bor_right, 1, 2)
        bor_spins.addWidget(self.spin_bor_bottom, 2, 1)
        
        border_layout.addLayout(bor_spins, 1, 0, 1, 2)
        
        # Color
        border_layout.addWidget(QLabel("Color:"), 2, 0)
        self.combo_color = QComboBox()
        self.combo_color.addItems(["Black", "White"])
        border_layout.addWidget(self.combo_color, 2, 1)
        
        border_layout.setRowStretch(3, 1)
        grid.addWidget(grp_borders, 0, 2)

        main_layout.addLayout(grid)
        main_layout.addStretch()

    def _create_spinbox(self, default=0, max_val=9999):
        sb = QSpinBox()
        sb.setRange(0, max_val)
        sb.setValue(default)
        sb.setButtonSymbols(QSpinBox.NoButtons) # Cleaner look like screenshot
        sb.setAlignment(Qt.AlignCenter)
        return sb

    def _connect_signals(self):
        # Toggle crop spins
        self.combo_crop_mode.currentIndexChanged.connect(self._update_crop_state)
        self._update_crop_state()
        
        # Toggle sizing
        self.chk_optimal.toggled.connect(self._update_size_state)
        self._update_size_state()
        
        # Toggle borders
        self.combo_fill.currentIndexChanged.connect(self._update_border_state)
        self._update_border_state()

        # Connect changes to signal
        self.spin_width.valueChanged.connect(self.settings_changed)
        self.spin_height.valueChanged.connect(self.settings_changed)

        # Connect Resolution Limit
        self.combo_res_limit.currentTextChanged.connect(self._update_resolution_limit)

    def _update_crop_state(self):
        enabled = self.combo_crop_mode.currentText() == "Custom"
        self.spin_crop_top.setEnabled(enabled)
        self.spin_crop_bottom.setEnabled(enabled)
        self.spin_crop_left.setEnabled(enabled)
        self.spin_crop_right.setEnabled(enabled)

    def _update_size_state(self):
        # If optimal is checked, disable manual size? 
        # HandBrake allows editing even if Optimal is checked usually, 
        # but let's assume Optimal locks it to auto-calc.
        optimal = self.chk_optimal.isChecked()
        self.spin_width.setEnabled(not optimal)
        self.spin_height.setEnabled(not optimal)
        
        if optimal:
            self._update_resolution_limit()

    def _update_border_state(self):
        enabled = self.combo_fill.currentText() == "Custom"
        self.spin_bor_top.setEnabled(enabled)
        self.spin_bor_bottom.setEnabled(enabled)
        self.spin_bor_left.setEnabled(enabled)
        self.spin_bor_right.setEnabled(enabled)
        self.combo_color.setEnabled(enabled)

    def _update_resolution_limit(self):
        """Calculate scaled dimensions based on resolution limit."""
        if not self.chk_optimal.isChecked():
            return

        limit_text = self.combo_res_limit.currentText()
        # "No Limit", "4320p 8K", "2160p 4K", "1440p 2K", "1080p HD", ...
        
        target_h = 1080 # Default fallback
        if "4320p" in limit_text: target_h = 4320
        elif "2160p" in limit_text: target_h = 2160
        elif "1440p" in limit_text: target_h = 1440
        elif "1080p" in limit_text: target_h = 1080
        elif "720p" in limit_text: target_h = 720
        elif "576p" in limit_text: target_h = 576
        elif "480p" in limit_text: target_h = 480
        elif "No Limit" in limit_text:
            # Just use source dimensions
            self.spin_width.setValue(self._source_width)
            self.spin_height.setValue(self._source_height)
            return

        # Calculate aspect ratio
        if self._source_height == 0:
            return

        aspect = self._source_width / self._source_height
        
        # New height is min(source_height, target_h) unless upscaling allowed
        if not self.chk_upscale.isChecked() and self._source_height <= target_h:
            new_h = self._source_height
        else:
            new_h = target_h
            
        new_w = int(new_h * aspect)
        
        # Ensure divisible by 2 (standard requirement)
        if new_w % 2 != 0: new_w += 1
        if new_h % 2 != 0: new_h += 1

        self.spin_width.blockSignals(True)
        self.spin_height.blockSignals(True)
        self.spin_width.setValue(new_w)
        self.spin_height.setValue(new_h)
        self.spin_width.blockSignals(False)
        self.spin_height.blockSignals(False)

    def set_source_dimensions(self, width: int, height: int):
        """Update source info and defaults."""
        self._source_width = width
        self._source_height = height
        self.lbl_source_dim.setText(f"Source Dimensions: {width}x{height} Storage, {width}x{height} Display")
        self._update_resolution_limit()

    def get_settings(self) -> dict:
        """Return dimensions settings."""
        return {
            "width": self.spin_width.value(),
            "height": self.spin_height.value(),
            "flip": self.chk_flip.isChecked(),
            "rotation": int(self.combo_rotation.currentText()),
            "crop_mode": self.combo_crop_mode.currentText(),
            "crop": (
                self.spin_crop_top.value(), 
                self.spin_crop_bottom.value(), 
                self.spin_crop_left.value(), 
                self.spin_crop_right.value()
            ),
            "border_mode": self.combo_fill.currentText(),
            "borders": (
                self.spin_bor_top.value(), 
                self.spin_bor_bottom.value(), 
                self.spin_bor_left.value(), 
                self.spin_bor_right.value()
            ),
            "border_color": self.combo_color.currentText()
        }
