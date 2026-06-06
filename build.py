import PyInstaller.__main__
import os
import sys
import shutil
import subprocess
import tempfile
import argparse

# Define paths
base_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(base_dir, 'src')

# Detect Platform
PLATFORM = sys.platform
IS_WIN = PLATFORM == 'win32'
IS_MAC = PLATFORM == 'darwin'
IS_LINUX = PLATFORM.startswith('linux')

# Parse command line arguments
def parse_arguments():
    parser = argparse.ArgumentParser(description='Cross-platform Omneva Media Player build system')
    parser.add_argument('--platform', choices=['windows', 'linux', 'macos', 'all'], 
                       default='current', help='Target platform to build for')
    parser.add_argument('--package', choices=['portable', 'installer', 'appimage', 'deb', 'dmg', 'pkg', 'all'], 
                       default='all', help='Package type to create')
    parser.add_argument('--build-mode', choices=['onedir', 'onefile'], 
                       default='onefile', help='Build mode: onedir (directory) or onefile (single executable)')
    parser.add_argument('--clean', action='store_true', help='Clean build directories before building')
    return parser.parse_args()

# Cross-platform build functions
def build_for_platform(target_platform, package_types, build_mode='onefile'):
    """Build for a specific target platform regardless of current platform"""
    print(f"Building for target platform: {target_platform} (mode: {build_mode})")
    
    # Only build for current platform for now - cross-platform compilation requires
    # additional setup (Docker, VMs, or cross-compilation tools)
    current_platform = 'windows' if IS_WIN else 'macos' if IS_MAC else 'linux'
    
    if target_platform != current_platform:
        print(f"Note: Cross-platform compilation from {current_platform} to {target_platform} requires Docker/VM setup.")
        print(f"Building for current platform ({current_platform}) instead...")
        target_platform = current_platform
    
    # Build the application for current platform
    build_application(build_mode)
    
    # Create packages based on requested types
    if target_platform == 'windows':
        if package_types in ['all', 'portable']:
            create_windows_portable()
        if package_types in ['all', 'installer']:
            create_windows_installer()
    elif target_platform == 'linux':
        if package_types in ['all', 'portable']:
            create_linux_package()
        if package_types in ['all', 'appimage']:
            create_appimage()
        if package_types in ['all', 'deb']:
            create_deb_package()
    elif target_platform == 'macos':
        if package_types in ['all', 'portable']:
            create_macos_package()
        if package_types in ['all', 'dmg']:
            create_macos_dmg()
        if package_types in ['all', 'pkg']:
            create_macos_pkg()

def build_application(build_mode='onefile'):
    """Build the application using PyInstaller"""
    print(f"Building Omneva for platform: {PLATFORM.upper()} (mode: {build_mode})")

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
        '--hidden-import=src.ui.core.history_service',
        '--hidden-import=src.ui.menus',
        '--hidden-import=src.ui.dialogs.sync_widget',
        '--hidden-import=src.ui.dialogs.video_essential_widget',
        '--hidden-import=src.ui.dialogs.video_crop_widget',
        '--hidden-import=src.ui.dialogs.video_overlay_widget',
        '--hidden-import=src.ui.dialogs.video_advanced_widget',
        '--hidden-import=src.ui.dialogs.equalizer_widget',
        '--hidden-import=src.ui.dialogs.audio_widgets',
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
        f'--{build_mode}',    # Use specified build mode (onedir or onefile)
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
        args.append('--osx-bundle-identifier=com.omneva.omneva')
        args.append('--osx-bundle-name=Omneva')
        args.append('--osx-bundle-info=CFBundleName:Omneva')
        args.append('--osx-bundle-info=CFBundleDisplayName:Omneva Media Player')
        args.append('--osx-bundle-info=CFBundleVersion:1.2.0')
        args.append('--osx-bundle-info=CFBundleShortVersionString:1.2.0')
        args.append('--osx-bundle-info=CFBundleIdentifier:com.omneva.omneva')
        # Icon (ICNS)
        icon_path = os.path.join(assets_src, 'icon.icns')
        if os.path.isfile(icon_path):
            args.append(f'--icon={icon_path}')

    elif IS_LINUX:
        # Linux specific settings
        args.append('--name=omneva')
        # Icon (doesn't embed but useful for .desktop files)
        icon_path = os.path.join(assets_src, 'icon.png')
        if os.path.isfile(icon_path):
            args.append(f'--icon={icon_path}')

    print(f"Build Arguments: {args}")
    print(f"Building from: {base_dir}")

    # Run PyInstaller
    PyInstaller.__main__.run(args)

    print("-" * 50)
    print("Build Complete!")

def create_windows_portable():
    """Create Windows portable package"""
    portable_path = os.path.join(base_dir, 'portable_windows')
    
    if os.path.exists(portable_path):
        shutil.rmtree(portable_path)
    
    os.makedirs(portable_path)
    
    # Check if we have onefile (single exe) or onedir (directory)
    onefile_exe = os.path.join(base_dir, 'dist', 'Omneva.exe')
    onedir_dir = os.path.join(base_dir, 'dist', 'Omneva')
    
    if os.path.isfile(onefile_exe):
        # One-file mode - copy the single executable
        shutil.copy2(onefile_exe, os.path.join(portable_path, 'Omneva.exe'))
        # Create launcher script for single file
        launcher_script = f"""@echo off
cd /d "%~dp0"
start Omneva.exe
"""
    elif os.path.isdir(onedir_dir):
        # One-dir mode - copy the entire directory
        shutil.copytree(onedir_dir, os.path.join(portable_path, 'Omneva'))
        # Create launcher script for directory
        launcher_script = f"""@echo off
cd /d "%~dp0Omneva"
start Omneva.exe
"""
    else:
        print("No build output found - skipping portable package creation")
        return
    
    with open(os.path.join(portable_path, 'Run_Omneva.bat'), 'w') as f:
        f.write(launcher_script)
    
    print(f"Windows Portable Package: {portable_path}")

def create_windows_installer():
    """Create Windows installer"""
    try:
        result = subprocess.run(['where', 'iscc'], capture_output=True, text=True)
        if result.returncode == 0:
            subprocess.run(['iscc', 'installer.iss'], cwd=base_dir, check=True)
            print("Windows installer created successfully")
        else:
            print("Inno Setup not found - skipping Windows installer")
    except:
        print("Inno Setup not found - skipping Windows installer")

def create_linux_package():
    """Create Linux package"""
    binary_path = os.path.join(base_dir, 'dist', 'omneva')
    
    # Check if binary exists for this platform
    if not os.path.exists(binary_path):
        print(f"Linux binary not found at {binary_path} - skipping Linux package creation")
        return
    
    linux_package_path = os.path.join(base_dir, 'linux_package_cross')
    
    if os.path.exists(linux_package_path):
        shutil.rmtree(linux_package_path)
    
    os.makedirs(linux_package_path)
    shutil.copy2(binary_path, os.path.join(linux_package_path, 'omneva'))
    
    # Create .desktop file
    desktop_file = f"""[Desktop Entry]
Version=1.0
Type=Application
Name=Omneva Media Player
Comment=A powerful, feature-rich media player with transcoding capabilities
Exec={os.path.join(linux_package_path, 'omneva')}
Icon={os.path.join(linux_package_path, 'assets', 'icon.svg')}
Terminal=false
Categories=AudioVideo;Player;
MimeType=audio/mp3;audio/mp4;audio/mpeg;audio/ogg;audio/wav;video/mp4;video/avi;video/mkv;video/mov;
"""
    
    with open(os.path.join(linux_package_path, 'omneva.desktop'), 'w') as f:
        f.write(desktop_file)
    
    # Create launcher script
    launcher_script = f"""#!/bin/bash
cd "$(dirname "$0")"
./omneva "$@"
"""
    
    launcher_path = os.path.join(linux_package_path, 'run_omneva.sh')
    with open(launcher_path, 'w') as f:
        f.write(launcher_script)
    os.chmod(launcher_path, 0o755)
    
    print(f"Linux Package: {linux_package_path}")

def create_macos_package():
    """Create macOS package"""
    app_bundle_path = os.path.join(base_dir, 'dist', 'Omneva.app')
    
    # Check if app bundle exists for this platform
    if not os.path.exists(app_bundle_path):
        print(f"macOS app bundle not found at {app_bundle_path} - skipping macOS package creation")
        return
    
    macos_package_path = os.path.join(base_dir, 'macos_package_cross')
    
    if os.path.exists(macos_package_path):
        shutil.rmtree(macos_package_path)
    
    shutil.copytree(app_bundle_path, macos_package_path)
    
    print(f"macOS Package: {macos_package_path}")

def create_macos_pkg():
    """Create PKG installer for macOS"""
    app_bundle_path = os.path.join(base_dir, 'dist', 'Omneva.app')
    if not os.path.exists(app_bundle_path):
        print("App bundle not found, skipping PKG creation.")
        return
    
    try:
        subprocess.run(['pkgbuild', '--root', app_bundle_path, '--identifier', 'com.omneva.omneva', 
                       '--version', '1.2.0', '--install-location', '/Applications', 
                       'Omneva-MacOS-Installer.pkg'], cwd=base_dir, check=True)
        print("PKG installer created: Omneva-MacOS-Installer.pkg")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("pkgbuild not found - skipping PKG creation")

def create_appimage():
    """Create AppImage for Linux distribution"""
    if not IS_LINUX:
        return
    
    print("Creating AppImage...")
    
    appdir_path = os.path.join(base_dir, 'Omneva.AppDir')
    if os.path.exists(appdir_path):
        shutil.rmtree(appdir_path)
    
    # Create AppDir structure
    os.makedirs(os.path.join(appdir_path, 'usr', 'bin'))
    os.makedirs(os.path.join(appdir_path, 'usr', 'share', 'applications'))
    os.makedirs(os.path.join(appdir_path, 'usr', 'share', 'icons', 'hicolor', '256x256', 'apps'))
    
    # Copy binary
    shutil.copy2(os.path.join(base_dir, 'dist', 'omneva'), os.path.join(appdir_path, 'usr', 'bin'))
    
    # Copy desktop file
    desktop_src = os.path.join(base_dir, 'linux_package_cross', 'omneva.desktop')
    if os.path.exists(desktop_src):
        shutil.copy2(desktop_src, os.path.join(appdir_path, 'usr', 'share', 'applications'))
    
    # Copy icon
    icon_src = os.path.join(base_dir, 'src', 'assets', 'icon.svg')
    icon_dst = os.path.join(appdir_path, 'usr', 'share', 'icons', 'hicolor', '256x256', 'apps', 'omneva.png')
    if os.path.exists(icon_src):
        try:
            # Try to convert SVG to PNG using ImageMagick
            subprocess.run(['convert', icon_src, '-resize', '256x256', icon_dst], check=False, capture_output=True)
        except:
            # Fallback: copy SVG as PNG
            shutil.copy2(icon_src, icon_dst)
    
    # Create AppRun script
    apprun_content = '''#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
exec "${HERE}/usr/bin/omneva" "$@"
'''
    
    apprun_path = os.path.join(appdir_path, 'AppRun')
    with open(apprun_path, 'w') as f:
        f.write(apprun_content)
    os.chmod(apprun_path, 0o755)
    
    # Create desktop file in AppDir
    desktop_content = '''[Desktop Entry]
Type=Application
Name=Omneva Media Player
Exec=AppRun
Icon=omneva
Categories=AudioVideo;Player;
Comment=A powerful, feature-rich media player
'''
    
    with open(os.path.join(appdir_path, 'omneva.desktop'), 'w') as f:
        f.write(desktop_content)
    
    # Download appimagetool if not exists
    appimagetool = os.path.join(base_dir, 'appimagetool-x86_64.AppImage')
    if not os.path.exists(appimagetool):
        print("Downloading appimagetool...")
        try:
            subprocess.run(['wget', '-q', 'https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage'], 
                         cwd=base_dir, check=True)
            os.chmod(appimagetool, 0o755)
        except:
            print("Warning: Could not download appimagetool. Skipping AppImage creation.")
            return
    
    # Create AppImage
    try:
        subprocess.run([appimagetool, appdir_path, 'Omneva-x86_64.AppImage'], cwd=base_dir, check=True)
        print("AppImage created: Omneva-x86_64.AppImage")
    except subprocess.CalledProcessError:
        print("Warning: AppImage creation failed.")
    
    # Clean up
    if os.path.exists(appdir_path):
        shutil.rmtree(appdir_path)

def create_deb_package():
    """Create DEB package for Debian/Ubuntu"""
    if not IS_LINUX:
        return
    
    print("Creating DEB package...")
    
    debdir_path = os.path.join(base_dir, 'deb_package')
    if os.path.exists(debdir_path):
        shutil.rmtree(debdir_path)
    
    # Create DEB structure
    os.makedirs(os.path.join(debdir_path, 'DEBIAN'))
    os.makedirs(os.path.join(debdir_path, 'usr', 'bin'))
    os.makedirs(os.path.join(debdir_path, 'usr', 'share', 'applications'))
    os.makedirs(os.path.join(debdir_path, 'usr', 'share', 'icons', 'hicolor', '256x256', 'apps'))
    
    # Create control file
    control_content = '''Package: omneva
Version: 1.2.0
Section: multimedia
Priority: optional
Architecture: amd64
Depends: python3, python3-pyside6, python3-vlc, libvlc5
Maintainer: Meetkumar Patel <pmeet464@gmail.com>
Description: A powerful, feature-rich media player with transcoding capabilities
 Omneva Media Player is a comprehensive media player that supports
 various audio and video formats with advanced features like transcoding,
 playlist management, and more.
'''
    
    with open(os.path.join(debdir_path, 'DEBIAN', 'control'), 'w') as f:
        f.write(control_content)
    
    # Copy files
    shutil.copy2(os.path.join(base_dir, 'dist', 'omneva'), os.path.join(debdir_path, 'usr', 'bin'))
    
    desktop_src = os.path.join(base_dir, 'linux_package_cross', 'omneva.desktop')
    if os.path.exists(desktop_src):
        shutil.copy2(desktop_src, os.path.join(debdir_path, 'usr', 'share', 'applications'))
    
    icon_src = os.path.join(base_dir, 'src', 'assets', 'icon.svg')
    icon_dst = os.path.join(debdir_path, 'usr', 'share', 'icons', 'hicolor', '256x256', 'apps', 'omneva.png')
    if os.path.exists(icon_src):
        shutil.copy2(icon_src, icon_dst)
    
    # Build DEB
    try:
        subprocess.run(['dpkg-deb', '--build', debdir_path, 'omneva_1.0.0_amd64.deb'], cwd=base_dir, check=True)
        print("DEB package created: omneva_1.0.0_amd64.deb")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Warning: dpkg-deb not found. Skipping DEB package creation.")
    
    # Clean up
    if os.path.exists(debdir_path):
        shutil.rmtree(debdir_path)

def create_macos_dmg():
    """Create DMG installer for macOS"""
    if not IS_MAC:
        return
    
    print("Creating DMG installer...")
    
    app_bundle_path = os.path.join(base_dir, 'dist', 'Omneva.app')
    if not os.path.exists(app_bundle_path):
        print("App bundle not found, skipping DMG creation.")
        return
    
    dmg_name = "Omneva-MacOS"
    dmg_file = f"{dmg_name}.dmg"
    dmg_temp = "dmg_temp"
    
    # Clean up existing files
    if os.path.exists(dmg_temp):
        shutil.rmtree(dmg_temp)
    if os.path.exists(dmg_file):
        os.remove(dmg_file)
    
    # Create temporary directory for DMG
    os.makedirs(dmg_temp)
    
    # Copy app bundle to DMG temp directory
    shutil.copytree(app_bundle_path, os.path.join(dmg_temp, 'Omneva.app'))
    
    # Create Applications folder symlink
    os.symlink('/Applications', os.path.join(dmg_temp, 'Applications'))
    
    # Create DMG
    try:
        subprocess.run(['hdiutil', 'create', '-volname', dmg_name, '-srcfolder', dmg_temp, '-ov', '-format', 'UDZO', dmg_file], 
                     cwd=base_dir, check=True)
        print(f"DMG installer created: {dmg_file}")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Warning: hdiutil not found. Skipping DMG creation.")
    
    # Clean up
    if os.path.exists(dmg_temp):
        shutil.rmtree(dmg_temp)

def clean_build_directories():
    """Clean all build directories"""
    print("Cleaning build directories...")
    
    directories_to_clean = ['build', 'dist', 'portable', 'portable_windows', 'linux_package', 'linux_package_cross', 
                           'macos_package', 'macos_package_cross', 'installer_output']
    
    for dir_name in directories_to_clean:
        dir_path = os.path.join(base_dir, dir_name)
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            print(f"Cleaned: {dir_path}")
    
    # Clean build artifacts
    artifacts_to_clean = ['*.spec', '*.AppImage', '*.dmg', '*.pkg', '*.deb', 'appimagetool-*.AppImage']
    
    for artifact in artifacts_to_clean:
        try:
            import glob
            for file_path in glob.glob(os.path.join(base_dir, artifact)):
                os.remove(file_path)
                print(f"Cleaned: {file_path}")
        except:
            pass

def main():
    """Main build function with cross-platform support"""
    args = parse_arguments()
    
    # Clean if requested
    if args.clean:
        clean_build_directories()
    
    # Build for specified platforms
    if args.platform == 'all':
        platforms = ['windows', 'linux', 'macos']
    elif args.platform == 'current':
        if IS_WIN:
            platforms = ['windows']
        elif IS_MAC:
            platforms = ['macos']
        else:
            platforms = ['linux']
    else:
        platforms = [args.platform]
    
    # Build for each platform
    for platform in platforms:
        build_for_platform(platform, args.package, args.build_mode)
    
    print("\n" + "=" * 50)
    print("Cross-Platform Build Complete!")
    print("=" * 50)
    print("Available packages:")
    
    for platform in platforms:
        if platform == 'windows':
            print(f"  Windows:")
            print(f"    - portable_windows/ (portable)")
            print(f"    - installer_output/ (installer)")
        elif platform == 'linux':
            print(f"  Linux:")
            print(f"    - linux_package_cross/ (binary)")
            if args.package in ['all', 'appimage']:
                print(f"    - *.AppImage (AppImage)")
            if args.package in ['all', 'deb']:
                print(f"    - *.deb (DEB package)")
        elif platform == 'macos':
            print(f"  macOS:")
            print(f"    - macos_package_cross/ (app bundle)")
            if args.package in ['all', 'dmg']:
                print(f"    - *.dmg (DMG installer)")
            if args.package in ['all', 'pkg']:
                print(f"    - *.pkg (PKG installer)")

if __name__ == '__main__':
    main()
