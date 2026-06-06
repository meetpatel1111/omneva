#!/usr/bin/env python3
"""
macOS .app Bundle Helper for Omneva Media Player
Creates proper Info.plist files and enhances macOS app bundles
"""

import os
import sys
import subprocess
import plistlib
from pathlib import Path
from datetime import datetime

def get_script_dir():
    """Get the directory where this script is located"""
    return Path(__file__).parent

def create_info_plist(app_bundle_path, version="1.2.0"):
    """Create a proper Info.plist file for the macOS app bundle"""
    print(f"📝 Creating Info.plist for {app_bundle_path}")
    
    info_plist_path = app_bundle_path / 'Contents' / 'Info.plist'
    
    # Info.plist configuration
    info_dict = {
        'CFBundleName': 'Omneva',
        'CFBundleDisplayName': 'Omneva Media Player',
        'CFBundleIdentifier': 'com.omneva.omneva',
        'CFBundleVersion': version,
        'CFBundleShortVersionString': version,
        'CFBundlePackageType': 'APPL',
        'CFBundleExecutable': 'Omneva',
        'CFBundleIconFile': 'AppIcon',
        'CFBundleInfoDictionaryVersion': '6.0',
        'CFBundleSupportedPlatforms': ['MacOSX'],
        'LSMinimumSystemVersion': '10.15.0',
        'NSHighResolutionCapable': True,
        'NSSupportsAutomaticGraphicsSwitching': True,
        'NSRequiresAquaSystemAppearance': False,
        'CFBundleDocumentTypes': [
            {
                'CFBundleTypeExtensions': ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm', 'mpg', 'mpeg', '3gp', 'm4v'],
                'CFBundleTypeName': 'Video File',
                'CFBundleTypeRole': 'Viewer',
                'LSHandlerRank': 'Alternate'
            },
            {
                'CFBundleTypeExtensions': ['mp3', 'wav', 'flac', 'aac', 'ogg', 'wma', 'm4a', 'opus'],
                'CFBundleTypeName': 'Audio File',
                'CFBundleTypeRole': 'Viewer',
                'LSHandlerRank': 'Alternate'
            }
        ],
        'LSApplicationCategoryType': 'public.app-category.video',
        'NSHumanReadableCopyright': f'© 2026 Meetkumar Patel. All rights reserved.',
        'CFBundleGetInfoString': f'Omneva Media Player {version} - A powerful, feature-rich media player with transcoding capabilities',
        'NSPrincipalClass': 'NSApplication',
        'CFBundleDevelopmentRegion': 'en',
        'CFBundleAllowMixedLocalizations': True,
        'NSRequiresAquaSystemAppearance': False,
        'NSAppTransportSecurity': {
            'NSAllowsArbitraryLoads': True
        },
        'NSDesktopFolderUsageDescription': 'Omneva needs access to your Desktop folder to open media files.',
        'NSDocumentsFolderUsageDescription': 'Omneva needs access to your Documents folder to open media files.',
        'NSDownloadsFolderUsageDescription': 'Omneva needs access to your Downloads folder to open media files.',
        'NSVolumesUsageDescription': 'Omneva needs access to external volumes to play media from drives.',
        'NSCameraUsageDescription': 'Omneva needs camera access for video capture features.',
        'NSMicrophoneUsageDescription': 'Omneva needs microphone access for audio recording features.',
        'CFBundleLocalizations': ['en', 'en_US'],
        'CFBundleSpokenName': 'Omneva'
    }
    
    try:
        # Create Contents directory if it doesn't exist
        contents_dir = app_bundle_path / 'Contents'
        contents_dir.mkdir(parents=True, exist_ok=True)
        
        # Write Info.plist
        with open(info_plist_path, 'wb') as f:
            plistlib.dump(info_dict, f)
        
        print(f"✅ Created Info.plist: {info_plist_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to create Info.plist: {e}")
        return False

def create_app_directory_structure(app_bundle_path):
    """Create proper macOS app bundle directory structure"""
    print(f"📁 Creating app bundle structure for {app_bundle_path}")
    
    try:
        # Create standard macOS app bundle structure
        directories = [
            app_bundle_path / 'Contents',
            app_bundle_path / 'Contents' / 'MacOS',
            app_bundle_path / 'Contents' / 'Resources',
            app_bundle_path / 'Contents' / 'Frameworks',
            app_bundle_path / 'Contents' / 'SharedSupport'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"  📁 Created: {directory}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to create directory structure: {e}")
        return False

def copy_resources_to_bundle(app_bundle_path, source_dir):
    """Copy necessary resources to the app bundle"""
    print(f"📦 Copying resources to app bundle...")
    
    resources_dir = app_bundle_path / 'Contents' / 'Resources'
    source_path = Path(source_dir)
    
    resources_to_copy = [
        ('styles', 'styles'),
        ('assets', 'assets'),
    ]
    
    try:
        for src_subdir, dst_subdir in resources_to_copy:
            src_path = source_path / src_subdir
            dst_path = resources_dir / dst_subdir
            
            if src_path.exists():
                if dst_path.exists():
                    import shutil
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
                print(f"  📁 Copied: {src_subdir} → Resources/{dst_subdir}")
            else:
                print(f"  ⚠️  Source not found: {src_path}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to copy resources: {e}")
        return False

def copy_icon_to_bundle(app_bundle_path):
    """Copy the app icon to the bundle"""
    print(f"🎨 Copying app icon to bundle...")
    
    resources_dir = app_bundle_path / 'Contents' / 'Resources'
    icon_path = get_script_dir() / 'src' / 'assets' / 'icon.icns'
    
    try:
        if icon_path.exists():
            import shutil
            icon_bundle_path = resources_dir / 'AppIcon.icns'
            shutil.copy2(icon_path, icon_bundle_path)
            print(f"  🎨 Copied icon: {icon_bundle_path}")
            return True
        else:
            print(f"  ⚠️  Icon not found: {icon_path}")
            return False
    except Exception as e:
        print(f"❌ Failed to copy icon: {e}")
        return False

def create_pkg_info(app_bundle_path):
    """Create PkgInfo file for the app bundle"""
    print(f"📄 Creating PkgInfo file...")
    
    pkg_info_path = app_bundle_path / 'Contents' / 'PkgInfo'
    
    try:
        # PkgInfo content for macOS application
        pkg_info_content = "APPLomne"
        
        with open(pkg_info_path, 'wb') as f:
            f.write(pkg_info_content.encode('ascii'))
        
        print(f"  📄 Created: {pkg_info_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to create PkgInfo: {e}")
        return False

def create_version_plist(app_bundle_path, version="1.2.0"):
    """Create version.plist file for the app bundle"""
    print(f"📄 Creating version.plist file...")
    
    version_plist_path = app_bundle_path / 'Contents' / 'version.plist'
    
    version_dict = {
        'BuildVersion': version,
        'CFBundleVersion': version,
        'SourceVersion': version,
        'ProjectName': 'Omneva',
        'ProductName': 'Omneva Media Player'
    }
    
    try:
        with open(version_plist_path, 'wb') as f:
            plistlib.dump(version_dict, f)
        
        print(f"  📄 Created: {version_plist_path}")
        return True
    except Exception as e:
        print(f"❌ Failed to create version.plist: {e}")
        return False

def enhance_pyinstaller_bundle(dist_dir, app_name="Omneva"):
    """Enhance a PyInstaller-generated macOS app bundle"""
    print("🔧 Enhancing PyInstaller macOS app bundle...")
    
    dist_path = Path(dist_dir)
    app_bundle_path = dist_path / f"{app_name}.app"
    
    if not app_bundle_path.exists():
        print(f"❌ App bundle not found: {app_bundle_path}")
        return False
    
    print(f"📦 Found app bundle: {app_bundle_path}")
    
    success = True
    
    # Create proper directory structure
    if not create_app_directory_structure(app_bundle_path):
        success = False
    
    # Create Info.plist
    if not create_info_plist(app_bundle_path):
        success = False
    
    # Create PkgInfo
    if not create_pkg_info(app_bundle_path):
        success = False
    
    # Create version.plist
    if not create_version_plist(app_bundle_path):
        success = False
    
    # Copy resources
    src_dir = get_script_dir() / 'src'
    if not copy_resources_to_bundle(app_bundle_path, src_dir):
        success = False
    
    # Copy icon
    if not copy_icon_to_bundle(app_bundle_path):
        success = False
    
    # Set proper permissions
    try:
        executable_path = app_bundle_path / 'Contents' / 'MacOS' / app_name
        if executable_path.exists():
            os.chmod(executable_path, 0o755)
            print(f"  🔒 Set executable permissions: {executable_path}")
    except Exception as e:
        print(f"⚠️  Failed to set executable permissions: {e}")
    
    return success

def fix_pyinstaller_bundle(dist_dir, app_name="Omneva"):
    """Fix common issues with PyInstaller macOS bundles"""
    print("🔧 Fixing PyInstaller macOS bundle issues...")
    
    dist_path = Path(dist_dir)
    app_bundle_path = dist_path / f"{app_name}.app"
    
    if not app_bundle_path.exists():
        print(f"❌ App bundle not found: {app_bundle_path}")
        return False
    
    # Fix common PyInstaller issues
    fixes_applied = 0
    
    # Fix 1: Ensure executable is in the right place
    macos_dir = app_bundle_path / 'Contents' / 'MacOS'
    executable_path = macos_dir / app_name
    
    if not executable_path.exists():
        # Look for executable in root of bundle
        root_executable = app_bundle_path / app_name
        if root_executable.exists():
            import shutil
            shutil.move(str(root_executable), str(executable_path))
            print(f"  📝 Moved executable to: {executable_path}")
            fixes_applied += 1
    
    # Fix 2: Copy external dependencies if needed
    frameworks_dir = app_bundle_path / 'Contents' / 'Frameworks'
    if frameworks_dir.exists():
        # Check for VLC frameworks that might need to be copied
        vlc_frameworks = [
            '/Applications/VLC.app/Contents/Frameworks/libvlc.dylib',
            '/Applications/VLC.app/Contents/Frameworks/libvlccore.dylib'
        ]
        
        for framework in vlc_frameworks:
            framework_path = Path(framework)
            if framework_path.exists():
                import shutil
                dest_framework = frameworks_dir / framework_path.name
                if not dest_framework.exists():
                    shutil.copy2(framework_path, dest_framework)
                    print(f"  📦 Copied framework: {framework_path.name}")
                    fixes_applied += 1
    
    print(f"✅ Applied {fixes_applied} fixes to PyInstaller bundle")
    return fixes_applied > 0

def main():
    """Main function to enhance macOS app bundle"""
    import argparse
    
    parser = argparse.ArgumentParser(description='macOS app bundle helper for Omneva Media Player')
    parser.add_argument('--dist-dir', default='dist', help='PyInstaller dist directory')
    parser.add_argument('--app-name', default='Omneva', help='Application name')
    parser.add_argument('--version', default='1.2.0', help='Application version')
    parser.add_argument('--fix-only', action='store_true', help='Only fix PyInstaller issues, don\'t recreate structure')
    
    args = parser.parse_args()
    
    print("🍎 macOS App Bundle Helper for Omneva")
    print("=" * 50)
    
    success = True
    
    if args.fix_only:
        # Only fix PyInstaller issues
        if not fix_pyinstaller_bundle(args.dist_dir, args.app_name):
            success = False
    else:
        # Full enhancement
        if not enhance_pyinstaller_bundle(args.dist_dir, args.app_name):
            success = False
        
        # Also fix PyInstaller issues
        if not fix_pyinstaller_bundle(args.dist_dir, args.app_name):
            success = False
    
    if success:
        print("\n✅ macOS app bundle enhancement completed successfully!")
        print(f"📦 Enhanced bundle: {args.dist_dir}/{args.app_name}.app")
    else:
        print("\n❌ Some issues occurred during bundle enhancement")
    
    return success

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
