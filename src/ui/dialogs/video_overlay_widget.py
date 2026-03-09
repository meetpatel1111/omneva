"""Video Overlay Widget — Logo and Marquee Text Controls."""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout, 
    QLabel, QLineEdit, QSpinBox, QSlider, QComboBox, QPushButton, QFileDialog
)
from PySide6.QtCore import Qt

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
        # positions usually mapped in vlc engine
        self.combo_pos.addItem("Center", 0)
        self.combo_pos.addItem("Top-Left", 5) 
        self.combo_pos.addItem("Top-Right", 6)
        self.combo_pos.addItem("Bottom-Left", 9)
        self.combo_pos.addItem("Bottom-Right", 10)
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
        if hasattr(self.vlc, 'set_logo'):
             if self.findChild(QGroupBox, "Add logo").isChecked():
                  self.vlc.set_logo(
                      self.txt_logo_path.text(),
                      self.slider_logo_opacity.value(),
                      self.spin_logo_left.value(),
                      self.spin_logo_top.value()
                  )
             else:
                  self.vlc.set_logo(None)

    def _update_text(self):
        if hasattr(self.vlc, 'set_marquee'):
             if self.findChild(QGroupBox, "Add text").isChecked():
                  self.vlc.set_marquee(
                      self.txt_input.text(),
                      self.combo_pos.currentData()
                  )
             else:
                  self.vlc.set_marquee(None)
