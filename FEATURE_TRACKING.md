# Omneva Feature Tracking

This file tracks the implementation status of features and improvements for the Omneva media player project.

**Last Updated**: 2026-06-07
**Version**: 1.4.1
**Status**: In Development

---

## Legend
- **Implemented**: Feature is fully implemented and functional
- **Partially Implemented**: Feature has UI or partial backend but lacks full functionality
- **In Progress**: Feature is currently being worked on
- **Planned**: Feature is planned but not started
- **Blocked**: Feature is blocked by dependencies or issues
- **Not Started**: Feature has not been started

---

## High Priority Features

### 1. Thumbnail System
- **File**: `src/ui/library_panel.py`
- **Status**: Implemented
- **Description**: Thumbnail generation and metadata extraction
- **Impact**: Significantly improves library browsing and player experience without crashing
- **Dependencies**: QThread lifecycle management
- **Notes**:
  - `src/core/thread_manager.py` manages QThread lifecycles
  - ThumbnailWorker and LibraryFFprobeWorker are now fully asynchronous
  - PlayerFFprobeWorker is fully asynchronous
  - Application closeEvent properly cleans up all background threads

### 2. Audio Effects
- **File**: `src/ui/dialogs/audio_widgets.py`, `src/core/vlc_engine.py`
- **Status**: Implemented
- **Description**: VLC audio effects (Compressor, Spatializer, Stereo Widener)
- **Impact**: Enhances audio processing capabilities
- **Dependencies**: VLC audio filter APIs
- **Notes**:
  - CompressorWidget, SpatializerWidget, StereoWidenerWidget all exist and functional
  - VLC engine has `set_compressor()`, `set_spatializer()`, `set_stereo_widener()` methods
  - Methods call `enable_audio_filter()` to toggle VLC audio filters
  - UI sliders update VLC engine parameters in real-time

### 3. Video Effects (Colors, Geometry, Atmolight)
- **File**: `src/ui/tools_dialogs.py`
- **Status**: Partially Implemented
- **Description**: VLC video effects tabs
- **Impact**: Completes video effects suite
- **Dependencies**: VLC video filter APIs
- **Notes**:
  - VideoEssentialWidget, VideoCropWidget, VideoOverlayWidget, VideoAdvancedWidget are functional
  - VideoColorsWidget, VideoGeometryWidget, VideoAtmolightWidget are stubs (marked "Stub" in code)
  - Stubs only show placeholder labels (e.g., "Colors settings are not yet available")
  - Missing file: `src/ui/dialogs/video_effects_extra.py`
  - Essential, Crop, Overlay, and Advanced tabs are wired to VLC engine

### 4. Plugin System
- **File**: `src/core/plugin_system.py`, `src/ui/plugin_manager.py`
- **Status**: Partially Implemented
- **Description**: Plugin architecture for third-party extensions
- **Impact**: Demonstrates extensibility and enables third-party extensions
- **Dependencies**: Plugin infrastructure
- **Notes**:
  - `BasePlugin` ABC with lifecycle methods (`on_load`, `on_unload`, `on_enable`, `on_disable`)
  - Event hooks system (`on_media_loaded`, `on_playback_started`, etc.)
  - Plugin manager UI is functional
  - Plugin discovery and loading from multiple directories works
  - Missing: `src/plugins/example_plugin.py` - no example plugin exists
  - No actual plugins have been created yet

### 5. Record Functionality
- **File**: `src/core/vlc_engine.py`, `src/ui/player_widget.py`
- **Status**: Partially Implemented
- **Description**: Video recording during playback
- **Impact**: Adds missing core feature
- **Dependencies**: FFmpeg recording capabilities or VLC sout
- **Notes**:
  - Record button exists in player controls
  - `toggle_record()` in VLC engine takes a snapshot instead of actual recording
  - Missing file: `src/core/vlc_recording.py`
  - True recording requires `--sout` setup on media load or FFmpeg-based recording
  - Saves snapshots to Pictures/Omneva directory

### 6. Frame-by-Frame Playback
- **File**: `src/ui/player_widget.py`, `src/core/vlc_engine.py`
- **Status**: Implemented
- **Description**: Advance video by single frames
- **Impact**: Adds precision control for video editing
- **Dependencies**: VLC `next_frame()` API
- **Notes**:
  - Button exists and is connected to `vlc.next_frame()`
  - `next_frame()` method in VLC engine calls `self.player.next_frame()`
  - Functional and working

---

## Medium Priority Features

### 7. Subtitle Sources Expansion
- **File**: `src/ui/subtitle_downloader.py`
- **Status**: Not Started
- **Description**: Add more subtitle sources beyond OpenSubtitles
- **Impact**: Increases subtitle availability
- **Dependencies**: Additional subtitle APIs
- **Notes**: Currently only supports OpenSubtitles API. Addic7ed, Subscene, etc. not implemented.

### 8. YouTube Downloader Enhancements
- **File**: `src/ui/youtube_downloader.py`
- **Status**: Not Started
- **Description**:
  - Add playlist download support
  - Add subtitle download option
  - Add quality presets
  - Add download queue
- **Impact**: Enhances online media capabilities
- **Dependencies**: yt-dlp advanced features
- **Notes**: Basic yt-dlp single-video integration exists. No playlist, subtitle, quality preset, or queue features.

### 9. A-B Loop Enhancement
- **File**: `src/ui/player_widget.py`
- **Status**: Partially Implemented
- **Description**: Loop between two time points
- **Impact**: Better user feedback for loop points
- **Dependencies**: Chapter slider customization
- **Notes**:
  - Basic A-B loop button exists and is functional
  - `_toggle_ab_loop()` sets A and B points and loops between them
  - Missing: Visual markers on seek bar for A and B points
  - No visual indication of loop range on the chapter slider

### 10. Bookmarks System
- **File**: `src/ui/tools_dialogs.py`, `src/core/vlc_engine.py`
- **Status**: Partially Implemented
- **Description**: VLC-style bookmarks (1-10 slots)
- **Impact**: Adds navigation convenience
- **Dependencies**: VLC bookmark API
- **Notes**:
  - VLC engine has `set_bookmark()` and `get_bookmark()` methods - functional
  - BookmarksDialog exists in `tools_dialogs.py` but is not fully functional
  - Dialog has table and buttons but no logic wired to VLC engine
  - Not connected to F1-F10 keyboard shortcuts

### 11. Renderer Integration
- **File**: `src/core/vlc_engine.py`
- **Status**: Partially Implemented
- **Description**: Chromecast, AirPlay, UPnP casting
- **Impact**: Adds streaming capabilities to other devices
- **Dependencies**: VLC renderer APIs
- **Notes**:
  - `start_renderer_discovery()`, `stop_renderer_discovery()`, `set_renderer()` exist in VLC engine
  - Renderer item added/deleted signals are emitted
  - Missing: UI for selecting and casting to discovered renderers
  - No menu items or dialogs for renderer selection

### 12. Enhanced Equalizer
- **File**: `src/ui/dialogs/equalizer_widget.py`
- **Status**: Partially Implemented
- **Description**:
  - Add custom preset saving
  - Add spectrum analyzer visualization
  - Add more bands (15-20)
- **Impact**: Better audio customization
- **Dependencies**: VLC equalizer API
- **Notes**:
  - 10-band equalizer with VLC presets exists and is functional
  - Missing: Custom preset save/load, spectrum analyzer, additional bands

### 13. Metadata Editor Enhancements
- **File**: `src/ui/metadata_editor.py`
- **Status**: Not Started
- **Description**:
  - Add cover art editing
  - Add more metadata fields
  - Add batch editing
  - Add metadata templates
- **Impact**: More comprehensive metadata management
- **Dependencies**: FFmpeg metadata options
- **Notes**: Basic ID3/MP4 editing exists. No cover art, batch editing, or templates.

### 14. Transcoder Presets Management
- **File**: `src/core/ffmpeg_service.py`
- **Status**: Not Started
- **Description**:
  - Add custom preset saving/loading
  - Add preset categories/folders
  - Add preset sharing (import/export)
- **Impact**: Better preset management
- **Dependencies**: Preset system exists
- **Notes**: 93 presets exist across multiple categories (General, Web, Device, Apple, Android, etc.). No custom save/load or import/export.

### 15. Queue Manager Enhancements
- **File**: `src/core/queue_manager.py`
- **Status**: Not Started
- **Description**:
  - Add job prioritization
  - Add job dependencies
  - Add batch job creation
  - Add job scheduling
- **Impact**: Better batch processing control
- **Dependencies**: Queue system exists
- **Notes**: Basic queue with SQLite persistence exists. No prioritization, dependencies, batch creation, or scheduling.

---

## Low Priority Features

### 16. Keyboard Navigation Enhancements
- **File**: `src/ui/keyboard_navigation.py`
- **Status**: Partially Implemented
- **Description**:
  - Add more Vim commands
  - Add command palette
  - Add key binding customization
- **Impact**: Better power user experience
- **Dependencies**: Keyboard navigation system exists
- **Notes**:
  - Vim-style normal/insert/visual modes exist
  - Basic navigation (hjkl, search, etc.) implemented
  - Missing: Command palette, key binding customization UI

### 17. Search Enhancements
- **File**: `src/ui/library_panel.py`
- **Status**: Not Started
- **Description**:
  - Add advanced search (by duration, codec, etc.)
  - Add search history
  - Add search filters
- **Impact**: Better file discovery
- **Dependencies**: File system model exists
- **Notes**: Basic recursive file search exists. No advanced filters or history.

### 18. Network Bookmarks Enhancements
- **File**: `src/ui/network_bookmarks.py`
- **Status**: Not Started
- **Description**:
  - Add bookmark categories/folders
  - Add bookmark testing
  - Add bookmark auto-refresh
- **Impact**: Better stream management
- **Dependencies**: Bookmark system exists
- **Notes**: Basic URL bookmarking exists. No categories, testing, or auto-refresh.

### 19. Audio Visualizer Enhancements
- **File**: `src/ui/audio_visualizer.py`
- **Status**: Partially Implemented
- **Description**:
  - Add more visualization types (waveform, oscilloscope, etc.)
  - Add visualization customization
  - Add visualization presets
- **Impact**: Better visual experience
- **Dependencies**: FFT analysis exists
- **Notes**: FFT bar visualization exists and functional. No waveform, oscilloscope, or customization.

### 20. Crash Recovery Enhancements
- **File**: `src/core/recovery_service.py`
- **Status**: Partially Implemented
- **Description**:
  - Add more state to recover (playlist, settings, etc.)
  - Add recovery history
  - Add selective recovery options
- **Impact**: Better crash recovery
- **Dependencies**: Recovery system exists
- **Notes**: Basic autosave every 5 minutes exists. Recovers current file, position, volume, page, recent files. No playlist recovery, history, or selective options.

### 21. Update System Enhancements
- **File**: `src/core/updater.py`
- **Status**: Not Started
- **Description**:
  - Add delta updates (download only changed files)
  - Add update verification (checksums)
  - Add rollback capability
- **Impact**: Better update experience
- **Dependencies**: GitHub API exists
- **Notes**: GitHub releases/tags checking exists. No delta updates, checksum verification, or rollback.

### 22. Telemetry Enhancements
- **File**: `src/core/telemetry.py`
- **Status**: Not Started
- **Description**:
  - Add performance metrics collection
  - Add usage analytics (with opt-in)
  - Add anonymous feature usage tracking
- **Impact**: Better understanding of user needs
- **Dependencies**: Sentry integration exists
- **Notes**: Basic Sentry crash reporting exists (disabled by default). No performance metrics or usage analytics.

### 23. Custom Aspect Ratio
- **File**: `src/ui/menus.py`
- **Status**: Not Started
- **Description**: Add custom aspect ratio input
- **Impact**: More flexibility for video display
- **Dependencies**: VLC aspect ratio API
- **Notes**: Preset aspect ratios (16:9, 4:3, 1:1, etc.) exist in menu. No custom input dialog.

### 24. Custom Crop
- **File**: `src/ui/dialogs/video_crop_widget.py`
- **Status**: Not Started
- **Description**: Add percentage-based crop
- **Impact**: More intuitive cropping
- **Dependencies**: VLC crop API
- **Notes**: Pixel-based crop exists. No percentage-based option.

### 25. Playback Speed Presets
- **File**: `src/ui/player_widget.py`
- **Status**: Not Started
- **Description**: Add speed presets (0.5x, 1.25x, 1.5x, 2x, etc.)
- **Impact**: Better speed control
- **Dependencies**: VLC speed API
- **Notes**: Manual speed adjustment via `]`/`[` keys exists. No preset menu.

### 26. Subtitle Sync Enhancements
- **File**: `src/ui/dialogs/sync_widget.py`
- **Status**: Partially Implemented
- **Description**: Add sync preview and fine-tuning
- **Impact**: Better subtitle synchronization
- **Dependencies**: VLC subtitle delay API
- **Notes**: Basic delay adjustment exists in SyncWidget and via keyboard shortcuts. No sync preview or fine-tuning UI.

### 27. Audio Delay Enhancements
- **File**: `src/core/vlc_engine.py`
- **Status**: Partially Implemented
- **Description**: Add audio delay presets
- **Impact**: Better audio sync
- **Dependencies**: VLC audio delay API
- **Notes**: Basic delay adjustment via `set_audio_delay()` exists. No preset delays.

### 28. Playlist Enhancements
- **File**: `src/core/playlist_model.py`
- **Status**: Not Started
- **Description**:
  - Add playlist folders/categories
  - Add smart playlists (by genre, artist, etc.)
  - Add playlist shuffle by album/artist
  - Add playlist history
- **Impact**: Better playlist management
- **Dependencies**: Playlist model exists
- **Notes**: Basic playlist with drag-drop exists. No folders, smart playlists, or history.

### 29. Screenshot Enhancements
- **File**: `src/ui/player_widget.py`
- **Status**: Not Started
- **Description**:
  - Add screenshot format selection (PNG, JPG, WEBP)
  - Add screenshot quality settings
  - Add burst screenshot
  - Add auto-screenshot at intervals
- **Impact**: Better screenshot options
- **Dependencies**: VLC snapshot API
- **Notes**: Basic snapshot button exists. No format selection, burst, or auto-screenshot.

### 30. Video Filters Enhancement
- **File**: `src/ui/tabs/filters_tab.py`
- **Status**: Not Started
- **Description**:
  - Add filter preview
  - Add custom filter parameters
  - Add filter presets
- **Impact**: Better video processing
- **Dependencies**: FFmpeg filter options
- **Notes**: Basic filter options exist in transcoder. No preview, custom parameters, or presets.

---

## Technical Improvements

### 31. Threading System Fix
- **Files**: Multiple files with disabled threading
- **Status**: Blocked (Critical)
- **Description**: Implement proper thread lifecycle management to fix QThread destruction issues
- **Impact**: Enables background operations (thumbnails, metadata, etc.)
- **Dependencies**: QThread, QThreadPool
- **Notes**:
  - Library panel thumbnails disabled (sync fallback)
  - FFprobe workers disabled in some panels
  - Missing file: `src/core/thread_manager.py`
  - Need proper thread cleanup on widget destruction
  - Workers exist but are not started due to crash risk

### 32. Security Enhancements
- **File**: `src/core/security.py`
- **Status**: Partially Implemented
- **Description**:
  - Add sandboxing for subprocess execution
  - Add file type validation
  - Add URL validation for network streams
- **Impact**: Better security
- **Dependencies**: Security module exists
- **Notes**: `safe_subprocess_run()` and `safe_subprocess_popen()` exist with path validation. No sandboxing, file type validation, or URL validation.

### 33. Performance Optimizations
- **Files**: Multiple files
- **Status**: Not Started
- **Description**:
  - Optimize FFprobe cache size and eviction policy
  - Implement lazy loading for large directories
  - Add debouncing for file system events
- **Impact**: Better performance
- **Dependencies**: Cache system exists
- **Notes**: FFprobe cache exists with 100-entry LRU eviction. Could benefit from tuning.

### 34. Error Handling
- **Files**: Multiple files
- **Status**: Partially Implemented
- **Description**:
  - Add more specific error messages
  - Add error recovery mechanisms
  - Add user-friendly error dialogs
- **Impact**: Better user experience
- **Dependencies**: Error handling exists
- **Notes**: Basic error handling and logging exists. Could be more user-friendly.

### 35. Accessibility
- **File**: `src/ui/settings_dialog.py`
- **Status**: Not Started
- **Description**:
  - Add high contrast mode
  - Add screen reader support
  - Add keyboard navigation for all UI elements
- **Impact**: Better accessibility
- **Dependencies**: Qt accessibility APIs
- **Notes**: Basic font scaling exists. No high contrast mode or screen reader support.

---

## New Feature Suggestions

### 36. Media Server Mode
- **Status**: Not Started
- **Description**: Run as DLNA/UPnP media server
- **Impact**: Share media to other devices on the network
- **Dependencies**: DLNA/UPnP libraries
- **Priority**: Medium

### 37. Cloud Storage Integration
- **Status**: Not Started
- **Description**: Integrate with cloud storage (Google Drive, Dropbox, etc.)
- **Impact**: Access media from anywhere
- **Dependencies**: Cloud storage APIs
- **Priority**: Medium

### 38. Subtitle Editor
- **Status**: Not Started
- **Description**: Built-in subtitle editor with timeline
- **Impact**: Edit subtitles without external tools
- **Dependencies**: Subtitle parsing/editing libraries
- **Priority**: Medium

### 39. Video Editor
- **Status**: Not Started
- **Description**: Basic video editing (trim, cut, merge)
- **Impact**: Basic video editing capabilities
- **Dependencies**: FFmpeg editing features
- **Priority**: Low

### 40. Audio Converter
- **Status**: Not Started
- **Description**: Dedicated audio conversion panel
- **Impact**: Better audio format conversion
- **Dependencies**: FFmpeg audio encoding
- **Priority**: Low

### 41. DVD/Blu-ray Ripper
- **Status**: Not Started
- **Description**: Add DVD/Blu-ray ripping support
- **Impact**: Disc-to-digital conversion
- **Dependencies**: libdvdcss, MakeMKV
- **Priority**: Low

### 42. Media Library Database
- **Status**: Not Started
- **Description**: SQLite database for media library with search/filter
- **Impact**: Better media organization
- **Dependencies**: SQLite, metadata extraction
- **Priority**: Medium

### 43. Social Sharing
- **Status**: Not Started
- **Description**: Share to social media platforms
- **Impact**: Social media integration
- **Dependencies**: Social media APIs
- **Priority**: Low

### 44. Remote Control
- **Status**: Not Started
- **Description**: Web-based remote control interface
- **Impact**: Control from other devices
- **Dependencies**: Web server, WebSocket
- **Priority**: Low

### 45. Skins/Themes
- **Status**: Partially Implemented
- **Description**: Custom skin/theme system
- **Impact**: UI customization
- **Dependencies**: QSS theming system
- **Notes**: Dark and Light QSS themes exist. No custom skin loading or theme marketplace.

---

## Implementation Log

### 2026-06-07 (Audit Update)
- Updated feature tracking to accurately reflect codebase state
- Corrected status of features previously marked as implemented but still missing files
- Identified missing files: `src/core/thread_manager.py`, `src/ui/dialogs/video_effects_extra.py`, `src/plugins/example_plugin.py`, `src/core/vlc_recording.py`
- Verified 93 FFmpeg presets exist
- Confirmed audio effects are functional (not stubs)
- Confirmed video color/geometry/atmolight tabs are stubs
- Confirmed thumbnail system uses sync fallback due to disabled threads
- Confirmed frame-by-frame playback is functional
- Confirmed A-B loop works but lacks visual markers
- Confirmed bookmarks engine methods exist but dialog is not wired
- Confirmed renderer discovery exists but no casting UI
- Confirmed record button takes snapshots, not actual recordings

### 2025-01-18
- Fixed mini player VLC embedding issue
- Added VLC window switching between main player and mini player
- Increased mini player size from 200x150 to 320x240
- Created this feature tracking file
- Created AGENTS.md for AI agent context
- Added audio effects widgets with VLC integration calls
- Added video effects stub widgets
- Added plugin system infrastructure
- Added basic recovery/autosave system

---

## Statistics

- **Total Features**: 45
- **Implemented**: 9 (20%)
- **Partially Implemented**: 12 (27%)
- **In Progress**: 0 (0%)
- **Planned**: 0 (0%)
- **Blocked**: 1 (2%)
- **Not Started**: 23 (51%)

### Implemented Features
1. Frame-by-Frame Playback
2. Audio Effects (Compressor, Spatializer, Stereo Widener)
3. FFprobe LRU Caching
4. FFmpeg Presets (93 presets)
5. Converter Panel
6. System Tray
7. Crash Recovery (basic)
8. Plugin System Infrastructure
9. Mini Player VLC Embedding

### Partially Implemented Features
1. Thumbnail System (sync fallback only)
2. Video Effects (some tabs are stubs)
3. Plugin System (no example plugins)
4. Record Functionality (snapshot fallback)
5. A-B Loop (no visual markers)
6. Bookmarks System (engine works, dialog not wired)
7. Renderer Integration (discovery works, no UI)
8. Enhanced Equalizer (no custom save/spectrum)
9. Keyboard Navigation (no command palette/custom bindings)
10. Audio Visualizer (only FFT bars)
11. Crash Recovery (basic only)
12. Subtitle Sync (basic delay only)
13. Audio Delay (no presets)
14. Security (basic path validation only)
15. Error Handling (basic only)
16. Themes (dark/light only, no custom skins)

---

## Priority Breakdown

- **High Priority**: 6 features (13%)
- **Medium Priority**: 15 features (33%)
- **Low Priority**: 15 features (33%)
- **Technical**: 5 features (11%)
- **New Features**: 10 features (22%)

---

## Next Steps

1. **Fix Threading System (Critical)** - Create `src/core/thread_manager.py` and enable background workers
2. **Implement Actual Recording** - Create `src/core/vlc_recording.py` with FFmpeg-based recording
3. **Complete Video Effects** - Replace stub tabs (Colors, Geometry, Atmolight) with actual VLC integrations
4. **Create Example Plugin** - Create `src/plugins/example_plugin.py` to demonstrate system
5. **Add A-B Loop Visual Markers** - Show loop range on the chapter slider
6. **Wire Bookmarks Dialog** - Connect BookmarksDialog to VLC engine methods
7. **Add Renderer Casting UI** - Menu/dialog for selecting Chromecast/AirPlay devices
8. **Subtitle Sources Expansion** - Add Addic7ed, Subscene integrations
9. **YouTube Downloader Enhancements** - Playlist support, subtitle download, quality presets
10. **Equalizer Enhancements** - Custom preset save/load, spectrum analyzer

---

## Notes

- Most UI components exist but some lack full backend integration
- Threading issues are the primary blocker for background operations
- Plugin system infrastructure is complete and ready for use
- Security and performance optimizations should be done alongside feature implementation
- Several claimed implementations in the original log were inaccurate - files were never created
- The VLC engine is comprehensive; most missing features are UI/integration layers
