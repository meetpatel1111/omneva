"""Video Crop Widget — Video Cropping Controls."""

from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QSpinBox
from PySide6.QtCore import Qt

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
        # Note: vlc engine must support adjust_pixel_crop or direct crop geometry
        if hasattr(self.vlc, 'set_crop'):
            self.vlc.set_crop(
                top=self.spin_top.value(),
                left=self.spin_left.value(),
                bottom=self.spin_bot.value(),
                right=self.spin_right.value()
            )
        elif hasattr(self.vlc, 'adjust_pixel_crop'):
             # Handle granular updates if that's what's supported
             pass
