# AGENTS.md

## Project Overview

**Omneva** is a comprehensive media player application built with Python and PySide6 (Qt). It features VLC-based video playback, FFmpeg transcoding, YouTube downloading, and a plugin system.

**Version**: 1.4.1  
**Language**: Python 3.x  
**UI Framework**: PySide6 (Qt6)  
**Media Engine**: python-vlc (LibVLC)  
**Transcoding**: FFmpeg/FFprobe

---

## Setup Commands

### Initial Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Install VLC (if not already installed)
# Windows: Download from videolan.org
# macOS: brew install vlc
# Linux: sudo apt install vlc

# Install FFmpeg (if not already installed)
# Windows: Download from ffmpeg.org or use the built-in downloader
# macOS: brew install ffmpeg
# Linux: sudo apt install ffmpeg

# Install yt-dlp for YouTube downloading
pip install yt-dlp
```

### Running the Application
```bash
# Run the application
python main.py

# Run with specific mode
python main.py --mode player  # Start in player mode
python main.py --mode transcoder  # Start in transcoder mode
```

### Building
```bash
# Build executable with PyInstaller
python build.py

# Build installer (Windows)
python build.py --installer
```

### Testing
```bash
# Run tests (if test suite exists)
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html
```

---

## Code Style

### Python Style
- Follow PEP 8 style guidelines
- Use type hints for function signatures
- Use docstrings for all public functions and classes
- Maximum line length: 120 characters
- Use f-strings for string formatting
- Prefer list comprehensions over map/filter

### Qt/PySide6 Style
- Use PySide6 (not PyQt6)
- Use Signal/Slot for communication between components
- Prefer composition over inheritance for Qt widgets
- Use objectName for styling with QSS
- Always clean up resources in __del__ or close methods

### Naming Conventions
- Classes: PascalCase (e.g., `VideoPlayer`, `TranscoderPanel`)
- Functions/Methods: snake_case (e.g., `load_media`, `setup_ui`)
- Constants: UPPER_SNAKE_CASE (e.g., `MAX_CACHE_SIZE`)
- Private members: single underscore prefix (e.g., `_current_file`)
- Signals: descriptive names (e.g., `media_loaded`, `progress_updated`)

### File Organization
- One class per file (usually)
- Group related classes in the same directory
- Use `__init__.py` for package exports
- Keep UI components in `src/ui/`
- Keep core logic in `src/core/`

---

## Project Structure

```
omneva/
├── main.py                    # Application entry point
├── build.py                   # Build script for PyInstaller
├── installer.iss              # Inno Setup installer script
├── requirements.txt           # Python dependencies
├── AGENTS.md                  # This file
├── FEATURE_TRACKING.md       # Feature implementation tracking
│
├── src/
│   ├── app.py                 # Application wrapper and initialization
│   ├── main_window.py         # Main window with navigation
│   │
│   ├── core/                  # Core business logic
│   │   ├── vlc_engine.py      # VLC playback engine wrapper
│   │   ├── ffmpeg_service.py  # FFmpeg transcoding service
│   │   ├── ffprobe_service.py # FFprobe metadata extraction
│   │   ├── queue_manager.py   # Job queue management
│   │   ├── queue_persistence.py # SQLite job persistence
│   │   ├── playlist_model.py  # Qt table model for playlist
│   │   ├── history_service.py # Playback history management
│   │   ├── recovery_service.py # Crash recovery and autosave
│   │   ├── security.py        # Input validation and security
│   │   ├── storage.py         # Settings and database manager
│   │   ├── logger.py          # Centralized logging
│   │   ├── utils.py           # Utility functions
│   │   ├── telemetry.py       # Crash reporting and analytics
│   │   ├── updater.py         # Auto-update system
│   │   ├── downloader.py      # Dependency download manager
│   │   ├── plugin_system.py   # Plugin architecture
│   │   └── post_encode_actions.py # Post-encoding actions
│   │
│   ├── ui/                    # User interface components
│   │   ├── player_widget.py   # Main video player widget
│   │   ├── library_panel.py   # Media browser and playlist
│   │   ├── transcoder_panel.py # HandBrake-style transcoder
│   │   ├── converter_panel.py # Quick format converter
│   │   ├── queue_panel.py     # Job queue visualization
│   │   ├── youtube_downloader.py # yt-dlp integration
│   │   ├── metadata_editor.py # ID3/MP4 metadata editor
│   │   ├── subtitle_downloader.py # OpenSubtitles integration
│   │   ├── plugin_manager.py  # Plugin management UI
│   │   ├── mini_player.py     # Picture-in-picture mode
│   │   ├── audio_visualizer.py # FFT audio visualization
│   │   ├── network_bookmarks.py # Stream URL bookmarks
│   │   ├── keyboard_navigation.py # Vim-style shortcuts
│   │   ├── titlebar.py        # Custom frameless titlebar
│   │   ├── menus.py           # Menu bar factory
│   │   ├── settings_dialog.py # Application preferences
│   │   ├── tools_dialogs.py   # Various tool dialogs
│   │   ├── update_dialog.py   # Update notification dialog
│   │   ├── download_dialog.py # Dependency download progress
│   │   ├── telemetry_settings.py # Telemetry configuration
│   │   ├── telemetry_integration.py # Telemetry helpers
│   │   ├── update_integration.py # Update system helpers
│   │   ├── metadata_integration.py # Metadata editor helpers
│   │   ├── subtitle_integration.py # Subtitle downloader helpers
│   │   ├── plugin_integration.py # Plugin system helpers
│   │   └── keyboard_integration.py # Keyboard navigation helpers
│   │
│   ├── ui/dialogs/            # Dialog widgets
│   │   ├── equalizer_widget.py # 10-band audio equalizer
│   │   ├── audio_widgets.py   # Audio effects (compressor, spatializer)
│   │   ├── video_essential_widget.py # Essential video effects
│   │   ├── video_crop_widget.py # Video cropping
│   │   ├── video_overlay_widget.py # Video overlays
│   │   ├── video_advanced_widget.py # Advanced video effects
│   │   ├── sync_widget.py     # Audio/subtitle synchronization
│   │   └── snapshot_preview_dialog.py # Snapshot preview
│   │
│   ├── ui/tabs/               # Transcoder tab widgets
│   │   ├── summary_tab.py     # Format selection and overview
│   │   ├── dimensions_tab.py  # Cropping, scaling, orientation
│   │   ├── filters_tab.py     # Video filters
│   │   ├── video_tab.py       # Video encoder settings
│   │   ├── audio_tab.py       # Audio track management
│   │   ├── subtitles_tab.py   # Subtitle track management
│   │   └── chapters_tab.py    # Chapter marker management
│   │
│   ├── ui/widgets/            # Custom widgets
│   │   └── chapter_slider.py  # Seek slider with chapter markers
│   │
│   └── ui/styles/              # QSS themes
│       ├── dark_theme.qss     # Dark theme
│       └── light_theme.qss    # Light theme
│
├── src/assets/                # Icons and resources
│   ├── play.svg
│   ├── stop.svg
│   └── ... (other icons)
│
└── tests/                     # Test files (if any)
```

---

## Development Workflow

### Branch Strategy
- `main` - Stable production branch
- `develop` - Development branch for new features
- `feature/*` - Feature branches
- `bugfix/*` - Bug fix branches
- `hotfix/*` - Critical hotfixes

### Commit Message Format
Follow conventional commits:
```
feat: add new feature
fix: fix bug
docs: update documentation
style: code style changes
refactor: code refactoring
test: add/update tests
chore: maintenance tasks
```

### Code Review Process
1. Create feature branch from `develop`
2. Implement changes with tests
3. Update documentation
4. Create pull request to `develop`
5. Review and address feedback
6. Merge after approval

### Release Process
1. Update version in `main.py` and `AGENTS.md`
2. Update `FEATURE_TRACKING.md` with completed features
3. Create release notes
4. Tag release in git
5. Build executable and installer
6. Test on target platforms
7. Deploy

---

## Important Implementation Notes

### VLC Integration
- VLC must be embedded using `set_window(win_id)` with the widget's window ID
- Always re-embed VLC when switching between windows (e.g., main player ↔ mini player)
- Store window IDs before switching to enable proper re-embedding
- VLC requires proper thread cleanup to avoid crashes

### Threading
- **CRITICAL**: QThread destruction issues exist in the codebase
- Many threading operations are currently disabled due to crashes
- Thumbnail generation is disabled in library panel
- FFprobe workers are disabled in some panels
- When implementing threading, ensure proper cleanup on widget destruction
- Use QThreadPool for short-lived tasks
- Use QThread for long-running operations with proper lifecycle management

### Security
- Always use `safe_subprocess_run` or `safe_subprocess_popen` from `src/core/security.py`
- Validate all file paths before subprocess execution
- Never trust user input for subprocess commands
- Use the SecurityValidator for path and argument validation

### VLC Engine
- The VLC engine is a singleton-like wrapper around python-vlc
- Use signals for communication between VLC and UI
- VLC events can be unreliable; use polling as fallback
- Hardware acceleration is enabled by default
- Plugin path must be set for PyInstaller compatibility

### FFmpeg Service
- FFmpeg operations are long-running; use threading
- The service includes 60+ encoding presets
- Hardware encoder detection is automatic (NVENC, QSV, VideoToolbox, AMF)
- Use the TranscodeJob dataclass for job representation
- Progress tracking is built-in with speed calculation

### FFprobe Service
- FFprobe operations use LRU caching (100 entries max)
- Cache key includes file path, mtime, and size
- Use threading for metadata extraction to avoid UI blocking
- Cache invalidation is automatic when file changes

### Plugin System
- Plugin infrastructure is complete but no plugins exist yet
- Plugins can extend menus, toolbars, and settings
- Plugins have lifecycle methods: on_load, on_unload, on_enable, on_disable
- Plugin directories: App data, project plugins, development plugins
- Event hooks: on_media_loaded, on_playback_started, etc.

### State Persistence
- Application state is autosaved every 5 minutes
- Recovery state includes: current file, position, volume, jobs
- Recovery state older than 24 hours is ignored
- Queue jobs are persisted in SQLite database
- Settings are stored in QSettings (INI format)

### UI Components
- Use lazy loading for tabs and panels
- Dark theme is default with purple accents (#6c5ce7)
- Light theme is available as alternative
- Custom widgets use objectName for styling
- VLC-style interface with familiar layout

### Transcoder
- HandBrake-style interface with tabs
- 60+ encoding presets organized by category
- Lazy-loaded tabs for performance
- Import/Export custom presets as JSON
- Autosave for transcoder state
- Queue integration for batch processing

---

## Known Issues

### Threading System
- **Status**: Critical
- **Issue**: QThread destruction causes crashes
- **Impact**: Thumbnails, metadata extraction, and other background operations are disabled
- **Workaround**: Using synchronous operations temporarily
- **Fix Needed**: Implement proper thread lifecycle management

### Stub Implementations
- Audio effects (Compressor, Spatializer, Stereo Widener) are stubs
- Video effects (Colors, Geometry, Atmolight) are stubs
- Record functionality button exists but doesn't work
- Frame-by-frame button exists but doesn't work
- Bookmarks dialog exists but not fully functional

### Mini Player
- **Status**: Recently Fixed
- **Issue**: VLC not properly embedded
- **Fix**: Added proper VLC embedding and window switching
- **Note**: Now functional with 320x240 size

---

## Testing Guidelines

### Unit Tests
- Write unit tests for all new functions
- Use pytest for testing framework
- Mock VLC and FFmpeg operations in tests
- Test error handling and edge cases
- Aim for >80% code coverage

### Integration Tests
- Test VLC integration with mock media
- Test FFmpeg operations with sample files
- Test UI components with Qt test framework
- Test plugin loading and lifecycle
- Test state persistence and recovery

### Manual Testing
- Test on Windows, macOS, and Linux
- Test with various media formats
- Test transcoding with different presets
- Test YouTube downloading
- Test crash recovery

---

## Dependencies

### Core Dependencies
- PySide6 >= 6.0.0 - Qt6 bindings
- python-vlc >= 3.0.0 - VLC media player
- requests >= 2.0.0 - HTTP requests
- sentry-sdk >= 1.0.0 - Error reporting (optional)

### Optional Dependencies
- yt-dlp >= 2023.0.0 - YouTube downloading
- Pillow >= 9.0.0 - Image processing
- opensubtitles-api >= 0.0.0 - Subtitle downloading

### System Dependencies
- VLC media player (for playback)
- FFmpeg (for transcoding)
- FFprobe (for metadata extraction)

---

## Feature Tracking

See `FEATURE_TRACKING.md` for detailed feature implementation status.

### Current Priority
1. Fix threading system (Critical)
2. Implement audio effects
3. Implement video effects
4. Create example plugins
5. Implement record functionality

---

## Code Patterns

### Signal/Slot Pattern
```python
class MyWidget(QWidget):
    # Define signals
    data_changed = Signal(dict)
    error_occurred = Signal(str)
    
    def __init__(self):
        super().__init__()
        # Connect signals
        self.data_changed.connect(self._on_data_changed)
```

### Worker Thread Pattern
```python
class MyWorker(QObject):
    finished = Signal(result_type)
    error = Signal(str)
    
    def do_work(self):
        try:
            result = self._process()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
```

### Singleton Pattern
```python
class MyManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

### Dataclass Pattern
```python
from dataclasses import dataclass

@dataclass
class MyData:
    id: str
    name: str
    status: str = "pending"
```

---

## Common Tasks

### Adding a New UI Component
1. Create widget class in appropriate `src/ui/` directory
2. Use objectName for styling
3. Implement lazy loading if complex
4. Add to main window or parent component
5. Connect signals/slots
6. Update documentation

### Adding a New Transcoder Preset
1. Add preset to `PRESETS` dict in `src/core/ffmpeg_service.py`
2. Include name, container, video codec, audio codec, quality settings
3. Test with various media files
4. Update documentation

### Adding a New Plugin
1. Create plugin class inheriting from `BasePlugin`
2. Implement required methods (on_load, on_unload, etc.)
3. Add plugin metadata (name, version, description)
4. Place in plugin directory
5. Test loading and lifecycle

### Adding a New Menu Item
1. Add action in `src/ui/menus.py` MenuFactory
2. Set keyboard shortcut if needed
3. Connect to handler in main window
4. Update documentation

---

## Debugging Tips

### VLC Issues
- Check VLC installation path
- Verify plugin path is set correctly
- Check window ID embedding
- Look for VLC error messages in logs
- Test with different media formats

### FFmpeg Issues
- Check FFmpeg installation
- Verify command arguments are safe
- Check FFmpeg output for errors
- Test with simple commands first
- Use `safe_subprocess_run` for validation

### Threading Issues
- Check thread cleanup on widget destruction
- Verify signal connections are proper
- Look for race conditions
- Use proper thread synchronization
- Check for deadlocks

### UI Issues
- Check QSS styling with objectName
- Verify layout constraints
- Check signal/slot connections
- Look for memory leaks
- Test on different platforms

---

## Logging

### Log Levels
- DEBUG: Detailed information for debugging
- INFO: General information about program execution
- WARNING: Warning messages for potential issues
- ERROR: Error messages for failures
- CRITICAL: Critical errors that prevent execution

### Log Location
- File: `~/.omneva/logs/omneva.log`
- Console: INFO level and above
- Rotation: 10MB max size, 5 backup files

### Using Logger
```python
from src.core.logger import get_logger

logger = get_logger('my_module')
logger.info("Information message")
logger.error("Error message", exc_info=True)
```

---

## Performance Considerations

### FFprobe Caching
- LRU cache with 100 entries max
- Cache key includes file path, mtime, and size
- Automatic invalidation on file changes
- Monitor cache hit rate

### Lazy Loading
- Tabs and panels loaded on first access
- Reduces initial startup time
- Improves memory usage
- Implement for complex components

### Threading
- Use threading for long-running operations
- Avoid blocking UI thread
- Proper thread cleanup is critical
- Use QThreadPool for short tasks

---

## Security Considerations

### Input Validation
- Always validate file paths
- Use SecurityValidator for subprocess arguments
- Never trust user input
- Sanitize all command arguments

### Subprocess Execution
- Use `safe_subprocess_run` or `safe_subprocess_popen`
- Validate all arguments before execution
- Use absolute paths for binaries
- Check for dangerous patterns

### Network Operations
- Validate URLs before downloading
- Use timeouts for network requests
- Check file types after download
- Limit download sizes

---

## Platform-Specific Notes

### Windows
- VLC path: Check Program Files, Program Files (x86), LOCALAPPDATA
- FFmpeg path: Check local deps, settings, PATH
- Use `os.add_dll_directory` for VLC DLL loading
- PyInstaller: Use --plugin-path for VLC plugins

### macOS
- VLC path: Check /Applications/VLC.app, /usr/local/lib
- FFmpeg path: Check local deps, settings, PATH
- Use bundle structure for PyInstaller
- Handle app bundle paths correctly

### Linux
- VLC path: Check /usr/lib, /usr/lib64, /usr/local/lib
- FFmpeg path: Check system PATH
- Use system packages when possible
- Handle different distributions

---

## Contact and Support

### Documentation
- Main documentation: See inline docstrings
- Feature tracking: `FEATURE_TRACKING.md`
- This file: `AGENTS.md`

### Issues
- Report bugs in issue tracker
- Include logs and reproduction steps
- Specify platform and version
- Attach sample files if relevant

### Contributing
- Follow code style guidelines
- Write tests for new features
- Update documentation
- Submit pull requests

---

## Version History

### 1.4.1 (Current)
- Fixed mini player VLC embedding
- Added VLC window switching
- Increased mini player size
- Created feature tracking system
- Created AGENTS.md

### Previous Versions
- See git history for details

---

## Notes for AI Agents

### When Working on This Codebase
1. Read this file first for context
2. Check `FEATURE_TRACKING.md` for implementation status
3. Follow code style guidelines
4. Use proper threading patterns (when fixed)
5. Validate all inputs for security
6. Test on multiple platforms if possible
7. Update documentation for changes
8. Update `FEATURE_TRACKING.md` for completed features

### Common Pitfalls
- Don't use threading without proper cleanup (currently broken)
- Don't skip input validation (security risk)
- Don't forget to re-embed VLC when switching windows
- Don't use stub implementations as final code
- Don't forget to update documentation

### Best Practices
- Always use type hints
- Write docstrings for public APIs
- Use signals/slots for component communication
- Implement proper error handling
- Test edge cases
- Follow existing patterns
- Keep UI responsive
- Use caching where appropriate

---

**Last Updated**: 2025-01-18  
**Maintained By**: Development Team  
**For Use By**: AI Agents and Developers
