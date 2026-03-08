"""Filters Tab for Transcoder - Denoise, Deinterlace, Sharpen, etc."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QCheckBox, QGroupBox, QGridLayout
)
from PySide6.QtCore import Qt

LABEL_WIDTH = 140


class FiltersTab(QWidget):
    """
    Video Filters settings tab.
    Handles Deinterlace, Denoise, Sharpen, Deblock, Colourspace.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("filtersTab")
        self._setup_ui()

    def _make_row(self, label_text: str, items: list[str]) -> tuple[QHBoxLayout, QComboBox]:
        """Create a label + combobox row with fixed label width."""
        row = QHBoxLayout()
        row.setSpacing(12)
        lbl = QLabel(label_text + ":")
        lbl.setFixedWidth(LABEL_WIDTH)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        combo = QComboBox()
        combo.addItems(items)
        combo.setFixedHeight(28)
        row.addWidget(lbl)
        row.addWidget(combo, 1)
        return row, combo

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # ─── 1. Deinterlacing ────────────────────────────────
        grp1 = QGroupBox("Deinterlacing")
        g1 = QVBoxLayout(grp1)
        g1.setSpacing(8)

        row, self.combo_detelecine = self._make_row("Detelecine", ["Off", "Custom", "Default"])
        g1.addLayout(row)

        row, self.combo_interlace_det = self._make_row("Interlace Detection", ["Off", "Custom", "Default", "LessSensitive", "Fast"])
        g1.addLayout(row)

        row, self.combo_deinterlace = self._make_row("Deinterlace", ["Off", "Yadif", "Decomb", "Bwdif"])
        g1.addLayout(row)

        main_layout.addWidget(grp1)

        # ─── 2. Enhancement ─────────────────────────────────
        grp2 = QGroupBox("Enhancement")
        g2 = QVBoxLayout(grp2)
        g2.setSpacing(8)

        row, self.combo_denoise = self._make_row("Denoise", ["Off", "hqdn3d", "NLMeans"])
        g2.addLayout(row)

        row, self.combo_chroma = self._make_row("Chroma Smooth", ["Off", "Custom", "Ultralight", "Light", "Medium", "Strong", "Stronger", "Very Strong"])
        g2.addLayout(row)

        row, self.combo_sharpen = self._make_row("Sharpen", ["Off", "UnSharp", "LapSharp"])
        g2.addLayout(row)

        row, self.combo_deblock = self._make_row("Deblock", ["Off", "Custom", "Ultralight", "Light", "Medium", "Strong", "Stronger", "Very Strong"])
        g2.addLayout(row)

        main_layout.addWidget(grp2)

        # ─── 3. Color ───────────────────────────────────────
        grp3 = QGroupBox("Color")
        g3 = QVBoxLayout(grp3)
        g3.setSpacing(8)

        row, self.combo_colorspace = self._make_row("Colourspace", ["Off", "Custom", "BT.2020", "BT.709", "BT.601 SMPTE-C", "BT.601 EBU"])
        g3.addLayout(row)

        # Grayscale checkbox aligned with combos
        chk_row = QHBoxLayout()
        chk_row.setSpacing(12)
        spacer_lbl = QLabel("")
        spacer_lbl.setFixedWidth(LABEL_WIDTH)
        self.chk_grayscale = QCheckBox("Grayscale")
        chk_row.addWidget(spacer_lbl)
        chk_row.addWidget(self.chk_grayscale, 1)
        g3.addLayout(chk_row)

        main_layout.addWidget(grp3)

        main_layout.addStretch()

    def get_settings(self) -> dict:
        """Return filter settings."""
        return {
            "detelecine": self.combo_detelecine.currentText(),
            "interlace_detection": self.combo_interlace_det.currentText(),
            "deinterlace": self.combo_deinterlace.currentText(),
            "denoise": self.combo_denoise.currentText(),
            "chroma_smooth": self.combo_chroma.currentText(),
            "sharpen": self.combo_sharpen.currentText(),
            "deblock": self.combo_deblock.currentText(),
            "colorspace": self.combo_colorspace.currentText(),
            "grayscale": self.chk_grayscale.isChecked()
        }
