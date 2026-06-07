import PyInstaller.__main__
import os
import sys
import shutil
import subprocess
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
    parser.add_argument('--package', choices=['portable', 'portable-onefile', 'installer', 'appimage', 'deb', 'dmg', 'pkg', 'all'], 
                       default='all', help='Package type to create (portable-onefile creates single exe for maximum portability)')
    parser.add_argument('--build-mode', choices=['onedir', 'onefile'], 
                       default='onedir', help='Build mode: onedir (directory) for faster startup or onefile (single executable) for portable distribution')
    parser.add_argument('--clean', action='store_true', help='Clean build directories before building')
    parser.add_argument('--sign', action='store_true', help='Sign build artifacts with code signing certificate')
    parser.add_argument('--cert', help='Path to code signing certificate (Windows .p12)')
    parser.add_argument('--identity', help='macOS signing identity (e.g., "Developer ID Application: Your Name")')
    return parser.parse_args()

# Cross-platform build functions
def build_for_platform(target_platform, package_types, build_mode='onedir', args=None):
    """Build for a specific target platform regardless of current platform"""
    print(f"Building for target platform: {target_platform} (mode: {build_mode})")
    
    # Only build for current platform for now - cross-platform compilation requires
    # additional setup (Docker, VMs, or cross-compilation tools)
    current_platform = 'windows' if IS_WIN else 'macos' if IS_MAC else 'linux'
    
    if target_platform != current_platform:
        print(f"Note: Cross-platform compilation from {current_platform} to {target_platform} requires Docker/VM setup.")
        print(f"Building for current platform ({current_platform}) instead...")
        target_platform = current_platform
    
    # Generate icons before building
    if not generate_required_icons():
        print("⚠️  Icon generation failed, continuing with available icons...")
    
    # Build the application for current platform
    build_application(build_mode)
    
    # Create packages based on requested types
    if target_platform == 'windows':
        if package_types in ['all', 'portable']:
            create_windows_portable()
        if package_types in ['all', 'portable-onefile']:
            create_windows_portable_onefile()
        if package_types in ['all', 'installer']:
            create_windows_installer()
        
        # Sign build artifacts if requested
        if args.sign and IS_WIN:
            sign_build_artifacts_windows(args.cert)
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
        
        # Enhance macOS app bundle
        if IS_MAC:
            enhance_macos_bundle()
        
        # Sign build artifacts if requested
        if args.sign and IS_MAC:
            entitlements_path = os.path.join(base_dir, 'entitlements.plist') if os.path.exists(os.path.join(base_dir, 'entitlements.plist')) else None
            sign_build_artifacts_macos(args.identity, entitlements_path)

def generate_required_icons():
    """Generate required icon files from SVG source"""
    print("🎨 Generating required icons from SVG...")
    
    # Import icon generation functions
    import sys
    sys.path.insert(0, base_dir)
    try:
        from generate_icons import find_svg_icon, render_svg_to_png, create_ico_file, create_icns_file
    except ImportError:
        print("❌ generate_icons.py not found. Icon generation disabled.")
        return False
    
    # Find SVG icon
    svg_path = find_svg_icon()
    if not svg_path:
        print("❌ SVG icon not found. Icon generation disabled.")
        return False
    
    print(f"📄 Found SVG icon: {svg_path}")
    
    # Check if icons already exist
    assets_dir = os.path.join(base_dir, 'src', 'assets')
    ico_path = os.path.join(assets_dir, 'icon.ico')
    icns_path = os.path.join(assets_dir, 'icon.icns')
    
    icons_needed = []
    if IS_WIN and not os.path.exists(ico_path):
        icons_needed.append('ico')
    if IS_MAC and not os.path.exists(icns_path):
        icons_needed.append('icns')
    
    if not icons_needed:
        print("✅ All required icons already exist")
        return True
    
    # Generate PNG files at required sizes
    sizes = [16, 32, 48, 64, 128, 256, 512]
    png_paths = []
    
    for size in sizes:
        png_path = render_svg_to_png(svg_path, size)
        if png_path and os.path.exists(png_path):
            png_paths.append(png_path)
    
    if not png_paths:
        print("❌ No PNG files were generated successfully")
        return False
    
    print(f"✅ Generated {len(png_paths)} PNG files")
    
    success = True
    
    # Generate ICO file for Windows
    if 'ico' in icons_needed:
        print("🔧 Generating ICO file for Windows...")
        if create_ico_file(png_paths, ico_path):
            print(f"✅ Created ICO file: {ico_path}")
        else:
            print("❌ Failed to create ICO file")
            success = False
    
    # Generate ICNS file for macOS
    if 'icns' in icons_needed:
        print("🔧 Generating ICNS file for macOS...")
        if create_icns_file(png_paths, icns_path):
            print(f"✅ Created ICNS file: {icns_path}")
        else:
            print("❌ Failed to create ICNS file")
            success = False
    
    # Clean up PNG files
    for png_path in png_paths:
        try:
            os.remove(png_path)
        except Exception:
            pass
    
    return success

def build_application(build_mode='onedir'):
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
        args.append('--osx-bundle-info=CFBundleVersion:1.4.1')
        args.append('--osx-bundle-info=CFBundleShortVersionString:1.4.1')
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
        launcher_script = """@echo off
cd /d "%~dp0"
start Omneva.exe
"""
    elif os.path.isdir(onedir_dir):
        # One-dir mode - copy the entire directory
        shutil.copytree(onedir_dir, os.path.join(portable_path, 'Omneva'))
        # Create launcher script for directory
        launcher_script = """@echo off
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
    except Exception:
        print("Inno Setup not found - skipping Windows installer")

def create_windows_portable_onefile():
    """Create Windows portable package using onefile mode for maximum portability"""
    print("Creating Windows portable package (onefile mode)...")
    
    portable_path = os.path.join(base_dir, 'portable_windows_onefile')
    if os.path.exists(portable_path):
        shutil.rmtree(portable_path)
    os.makedirs(portable_path)
    
    # Build in onefile mode specifically
    build_application('onefile')
    
    # Copy the single executable
    onefile_exe = os.path.join(base_dir, 'dist', 'Omneva.exe')
    if os.path.isfile(onefile_exe):
        shutil.copy2(onefile_exe, os.path.join(portable_path, 'Omneva.exe'))
        
        # Create launcher script for single file
        launcher_script = """@echo off
cd /d "%~dp0"
start Omneva.exe
"""
        
        with open(os.path.join(portable_path, 'Run_Omneva.bat'), 'w') as f:
            f.write(launcher_script)
        
        # Create README for portable package
        readme_content = """# Omneva Media Player - Portable Version

## Installation
No installation required! Simply extract this folder and run Omneva.exe.

## Usage
- Double-click Omneva.exe to start the application
- Or use Run_Omneva.bat for command-line launch

## Features
- Complete media player with transcoding capabilities
- Hardware acceleration support
- Batch preset management
- Job queue persistence
- Post-encode automation

## System Requirements
- Windows 10/11 (64-bit)
- DirectX 11 compatible graphics
- 4GB RAM recommended

## Notes
This portable version includes all dependencies and doesn't require installation.
Settings and data are stored in your user profile directory.

Version: 1.2.0
"""
        
        with open(os.path.join(portable_path, 'README.txt'), 'w') as f:
            f.write(readme_content)
        
        print(f"Windows Portable OneFile Package: {portable_path}")
    else:
        print("No onefile build output found - skipping portable-onefile package creation")

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
    launcher_script = """#!/bin/bash
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
                       '--version', '1.4.1', '--install-location', '/Applications', 
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
        except Exception:
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
        except Exception:
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
Version: 1.4.1
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
        except Exception:
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
        build_for_platform(platform, args.package, args.build_mode, args)
    
    print("\n" + "=" * 50)
    print("Cross-Platform Build Complete!")
    print("=" * 50)
    print("Available packages:")
    
    for platform in platforms:
        if platform == 'windows':
            print("  Windows:")
            print("    - portable_windows/ (portable)")
            print("    - installer_output/ (installer)")
        elif platform == 'linux':
            print("  Linux:")
            print("    - linux_package_cross/ (binary)")
            if args.package in ['all', 'appimage']:
                print("    - *.AppImage (AppImage)")
            if args.package in ['all', 'deb']:
                print("    - *.deb (DEB package)")
        elif platform == 'macos':
            print("  macOS:")
            print("    - macos_package_cross/ (app bundle)")
            if args.package in ['all', 'dmg']:
                print("    - *.dmg (DMG installer)")
            if args.package in ['all', 'pkg']:
                print("    - *.pkg (PKG installer)")

# Code Signing Functions
def sign_build_artifacts_windows(cert_path=None):
    """Sign Windows build artifacts using signtool.exe"""
    print("🔐 Signing Windows build artifacts...")
    
    # Import sign.py functions
    import sys
    sys.path.insert(0, base_dir)
    try:
        from sign import sign_windows_executable, find_executable
    except ImportError:
        print("❌ sign.py not found. Code signing disabled.")
        return False
    
    # Find signtool.exe
    signtool_paths = [
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64",
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22000.0\x64",
        r"C:\Program Files (x86)\Windows Kits\8.1\bin\x64",
        r"C:\Program Files\Microsoft SDKs\Windows\v7.1\Bin"
    ]
    
    signtool = find_executable('signtool.exe', signtool_paths)
    if not signtool:
        print("❌ signtool.exe not found. Please install Windows SDK.")
        print("   Available from: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/")
        return False
    
    print(f"✅ Found signtool.exe at: {signtool}")
    
    signed_count = 0
    dist_dir = os.path.join(base_dir, 'dist')
    
    # Sign main executable
    exe_path = os.path.join(dist_dir, 'Omneva.exe')
    if os.path.exists(exe_path):
        if sign_windows_executable(exe_path, cert_path):
            signed_count += 1
    
    # Sign executables in onedir builds
    onedir_path = os.path.join(dist_dir, 'Omneva')
    if os.path.exists(onedir_path):
        for exe_file in os.listdir(onedir_path):
            if exe_file.endswith('.exe'):
                exe_full_path = os.path.join(onedir_path, exe_file)
                if sign_windows_executable(exe_full_path, cert_path):
                    signed_count += 1
    
    print(f"✅ Successfully signed {signed_count} Windows artifacts")
    return signed_count > 0

def sign_build_artifacts_macos(identity=None, entitlements=None):
    """Sign macOS build artifacts using codesign"""
    print("🔐 Signing macOS build artifacts...")
    
    # Import sign.py functions
    import sys
    sys.path.insert(0, base_dir)
    try:
        from sign import sign_macos_bundle
    except ImportError:
        print("❌ sign.py not found. Code signing disabled.")
        return False
    
    # Check if codesign is available
    try:
        subprocess.run(['codesign', '--help'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ codesign not found. Please install Xcode Command Line Tools.")
        print("   Run: xcode-select --install")
        return False
    
    print("✅ Found codesign")
    
    signed_count = 0
    dist_dir = os.path.join(base_dir, 'dist')
    
    # Sign .app bundles
    for item in os.listdir(dist_dir):
        if item.endswith('.app'):
            app_path = os.path.join(dist_dir, item)
            if sign_macos_bundle(app_path, identity, entitlements):
                signed_count += 1
    
    print(f"✅ Successfully signed {signed_count} macOS artifacts")
    return signed_count > 0

def enhance_macos_bundle():
    """Enhance macOS app bundle with proper structure and metadata"""
    print("🍎 Enhancing macOS app bundle...")
    
    # Import macOS bundle helper functions
    import sys
    sys.path.insert(0, base_dir)
    try:
        from build_macos import enhance_pyinstaller_bundle, fix_pyinstaller_bundle
    except ImportError:
        print("❌ build_macos.py not found. macOS bundle enhancement disabled.")
        return False
    
    dist_dir = os.path.join(base_dir, 'dist')
    app_name = 'Omneva'
    
    # Check if app bundle exists
    app_bundle_path = os.path.join(dist_dir, f'{app_name}.app')
    if not os.path.exists(app_bundle_path):
        print(f"❌ App bundle not found: {app_bundle_path}")
        return False
    
    print(f"📦 Found app bundle: {app_bundle_path}")
    
    success = True
    
    # Enhance the bundle
    if not enhance_pyinstaller_bundle(dist_dir, app_name):
        print("⚠️  Bundle enhancement had some issues")
        success = False
    
    # Fix PyInstaller issues
    if not fix_pyinstaller_bundle(dist_dir, app_name):
        print("⚠️  PyInstaller fixes had some issues")
        success = False
    
    if success:
        print("✅ macOS app bundle enhancement completed successfully!")
    else:
        print("⚠️  macOS app bundle enhancement completed with warnings")
    
    return success

if __name__ == '__main__':
    main()
