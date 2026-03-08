import PyInstaller.__main__
import os
import sys
import shutil

# Define paths
base_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(base_dir, 'src')

# Detect Platform
PLATFORM = sys.platform
IS_WIN = PLATFORM == 'win32'
IS_MAC = PLATFORM == 'darwin'
IS_LINUX = PLATFORM.startswith('linux')

print(f"Building Omneva for platform: {PLATFORM.upper()}")

# Bundling options
# --add-data <SRC;DEST> (Windows uses ;)
sep = ';' if IS_WIN else ':'

styles_src = os.path.join(src_dir, 'styles')
assets_src = os.path.join(src_dir, 'assets')

add_data = []
if os.path.isdir(styles_src):
    add_data.append(f'--add-data={styles_src}{sep}src/styles')

# Check assets
if os.path.isdir(assets_src):
    add_data.append(f'--add-data={assets_src}{sep}src/assets')

# Hidden imports to ensure all modules are included
hidden_imports = [
    '--hidden-import=src.ui.converter_panel',
    '--hidden-import=src.ui.transcoder_panel',
    '--hidden-import=src.ui.library_panel',
    '--hidden-import=src.ui.player_widget',
    '--hidden-import=src.ui.queue_panel',
    '--hidden-import=src.ui.settings_dialog',
    '--hidden-import=src.ui.titlebar',
    '--hidden-import=src.ui.download_dialog',
    '--hidden-import=src.ui.tools_dialogs',
    '--hidden-import=src.ui.tabs.video_tab',
    '--hidden-import=src.ui.tabs.audio_tab',
    '--hidden-import=src.ui.tabs.dimensions_tab',
    '--hidden-import=src.ui.tabs.filters_tab',
    '--hidden-import=src.ui.tabs.subtitles_tab',
    '--hidden-import=src.ui.tabs.chapters_tab',
    '--hidden-import=src.ui.tabs.summary_tab',
    '--hidden-import=src.core.vlc_engine',
    '--hidden-import=src.core.ffmpeg_service',
    '--hidden-import=src.core.ffprobe_service',
    '--hidden-import=src.core.queue_manager',
    '--hidden-import=src.core.storage',
    '--hidden-import=src.core.utils',
    '--hidden-import=src.core.downloader',
    '--hidden-import=src.core.playlist_model',
]

# Base Config
args = [
    'main.py',
    '--name=Omneva',
    '--onefile',       # Single executable
    '--windowed',      # No console window
    '--clean',
    '--noconfirm',
] + add_data + hidden_imports

# Platform Specifics
if IS_WIN:
    # Icon
    icon_path = os.path.join(assets_src, 'icon.ico')
    if os.path.isfile(icon_path):
        args.append(f'--icon={icon_path}')
    
elif IS_MAC:
    # macOS Bundle Identifier
    args.append('--osx-bundle-identifier=com.antigravity.omneva')
    # Icon (ICNS)
    icon_path = os.path.join(assets_src, 'icon.icns')
    if os.path.isfile(icon_path):
        args.append(f'--icon={icon_path}')

elif IS_LINUX:
    # Linux Icon (does not embed in binary usually but useful for .desktop)
    # PyInstaller might ignore --icon on Linux for the functional binary, 
    # but strictly speaking strict onefile doesn't have an icon resource like win/mac.
    pass

print(f"Build Arguments: {args}")
print(f"Building from: {base_dir}")

# Run PyInstaller
PyInstaller.__main__.run(args)

print("-" * 50)
print("Build Complete!")
if IS_WIN:
    print(f"Executable: {os.path.join(base_dir, 'dist', 'Omneva.exe')}")
elif IS_MAC:
    print(f"App Bundle: {os.path.join(base_dir, 'dist', 'Omneva.app')}")
else:
    print(f"Binary: {os.path.join(base_dir, 'dist', 'Omneva')}")
