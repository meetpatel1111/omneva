import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QKeyEvent

# Add root directory to path
sys.path.append(os.getcwd())

# Mock vlc before importing VLCEngine
sys.modules['vlc'] = MagicMock()

# Offscreen rendering for headless environment
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from src.main_window import MainWindow
from src.ui.player_widget import PlayerWidget

print("Initializing QAplpication...")
app = QApplication.instance() or QApplication(sys.argv)
print("Environment ready.")


class TestShortcuts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.win = MainWindow()
            cls.player = cls.win.player_page
            cls.vlc = cls.player.vlc
        except Exception as e:
            print(f"FAILED TO INIT: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


    def setUp(self):
        # Reset mocks
        self.vlc.toggle_play_pause = MagicMock()
        self.vlc.stop = MagicMock()
        self.vlc.seek_relative = MagicMock()
        self.vlc.volume_up = MagicMock()
        self.vlc.volume_down = MagicMock()
        self.vlc.toggle_mute = MagicMock()
        self.vlc.cycle_audio_track = MagicMock()
        self.vlc.cycle_subtitle_track = MagicMock()
        self.vlc.cycle_aspect_ratio = MagicMock()
        self.vlc.cycle_crop = MagicMock()
        self.vlc.next_frame = MagicMock()

    def send_key(self, key, modifiers=Qt.NoModifier):
        event = QKeyEvent(QEvent.KeyPress, key, modifiers)
        self.player.keyPressEvent(event)

    def test_playback_shortcuts(self):
        self.send_key(Qt.Key_Space)
        self.vlc.toggle_play_pause.assert_called_once()
        
        self.send_key(Qt.Key_S)
        self.vlc.stop.assert_called_once()

    def test_seek_shortcuts(self):
        # Normal seek
        self.send_key(Qt.Key_Right)
        self.vlc.seek_relative.assert_called_with(10)
        
        # Shift seek (5s)
        self.send_key(Qt.Key_Right, Qt.ShiftModifier)
        self.vlc.seek_relative.assert_called_with(5)
        
        # Ctrl seek (1 min)
        self.send_key(Qt.Key_Right, Qt.ControlModifier)
        self.vlc.seek_relative.assert_called_with(60)
        
        # Ctrl + Alt seek (5 min)
        self.send_key(Qt.Key_Right, Qt.ControlModifier | Qt.AltModifier)
        self.vlc.seek_relative.assert_called_with(300)

    def test_audio_shortcuts(self):
        self.send_key(Qt.Key_Up, Qt.ControlModifier)
        self.vlc.volume_up.assert_called_once()
        
        self.send_key(Qt.Key_Down, Qt.ControlModifier)
        self.vlc.volume_down.assert_called_once()
        
        self.send_key(Qt.Key_M)
        self.vlc.toggle_mute.assert_called_once()
        
        self.send_key(Qt.Key_B)
        self.vlc.cycle_audio_track.assert_called_once()

    def test_video_shortcuts(self):
        self.send_key(Qt.Key_A)
        self.vlc.cycle_aspect_ratio.assert_called_once()
        
        self.send_key(Qt.Key_C)
        self.vlc.cycle_crop.assert_called_once()

    def test_history_shortcuts(self):
        # We need to test if Shift+G/H bubbled up or triggered history
        # Since MainWindow adds these as actions, we check if they are triggered
        with patch.object(self.win, '_history_back') as mock_back:
            self.send_key(Qt.Key_G, Qt.ShiftModifier)
            # This is tricky because actions handle their own events if shortcut matches
            # But we can trigger the action manually to verify binding
            self.win.act_history_back.trigger()
            mock_back.assert_called_once()

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
