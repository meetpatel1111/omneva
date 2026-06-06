#!/usr/bin/env python3
"""
Code Signing Script for Omneva Media Player
Supports Windows (signtool.exe) and macOS (codesign) code signing
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def get_script_dir():
    """Get the directory where this script is located"""
    return Path(__file__).parent

def find_executable(name, search_paths=None):
    """Find an executable in system PATH or custom search paths"""
    try:
        # Try system PATH first
        result = subprocess.run(['where' if sys.platform == 'win32' else 'which', name], 
                              capture_output=True, text=True, check=True)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    # Try custom search paths
    if search_paths:
        for path in search_paths:
            exe_path = Path(path) / name
            if exe_path.exists():
                return str(exe_path)
    
    return None

def sign_windows_executable(exe_path, cert_path=None, timestamp_url=None, description="Omneva Media Player"):
    """Sign a Windows executable using signtool.exe"""
    print(f"Signing Windows executable: {exe_path}")
    
    # Find signtool.exe
    signtool_paths = [
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64",
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22000.0\x64",
        r"C:\Program Files (x86)\Windows Kits\8.1\bin\x64",
        r"C:\Program Files\Microsoft SDKs\Windows\v7.1\Bin",
        r"C:\Program Files (x86)\Microsoft SDKs\Windows\v10.0A\bin\NETFX 4.8 Tools"
    ]
    
    signtool = find_executable('signtool.exe', signtool_paths)
    if not signtool:
        print("❌ signtool.exe not found. Please install Windows SDK or Visual Studio.")
        print("   Available from: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/")
        return False
    
    print(f"✅ Found signtool.exe at: {signtool}")
    
    # Build signing command
    cmd = [signtool, 'sign']
    
    if cert_path:
        cmd.extend(['/f', cert_path])
        print(f"📋 Using certificate: {cert_path}")
    else:
        # Use test signing for development
        cmd.extend(['/f', get_script_dir() / 'test_cert.p12', '/p', 'test123'])
        print("📋 Using test certificate (development mode)")
    
    if timestamp_url:
        cmd.extend(['/t', timestamp_url])
    else:
        # Use public timestamp server
        cmd.extend(['/t', 'http://timestamp.digicert.com'])
    
    cmd.extend(['/d', description])
    cmd.extend(['/du', 'https://github.com/pmeet464/omneva'])
    cmd.append(str(exe_path))
    
    try:
        print(f"🔐 Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ Windows executable signed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to sign Windows executable: {e}")
        print(f"   stdout: {e.stdout}")
        print(f"   stderr: {e.stderr}")
        return False

def sign_macos_bundle(bundle_path, identity=None, entitlements=None):
    """Sign a macOS .app bundle using codesign"""
    print(f"Signing macOS bundle: {bundle_path}")
    
    # Check if codesign is available
    try:
        subprocess.run(['codesign', '--help'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ codesign not found. Please install Xcode Command Line Tools.")
        print("   Run: xcode-select --install")
        return False
    
    print("✅ Found codesign")
    
    # Build signing command
    cmd = ['codesign', '--force', '--verify', '--verbose']
    
    if identity:
        cmd.extend(['--sign', identity])
        print(f"📋 Using signing identity: {identity}")
    else:
        # Use ad-hoc signing for development
        cmd.extend(['--sign', '-'])
        print("📋 Using ad-hoc signing (development mode)")
    
    if entitlements and os.path.exists(entitlements):
        cmd.extend(['--entitlements', entitlements])
        print(f"📋 Using entitlements: {entitlements}")
    
    cmd.append(str(bundle_path))
    
    try:
        print(f"🔐 Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("✅ macOS bundle signed successfully!")
        
        # Verify the signature
        verify_cmd = ['codesign', '--verify', '--verbose', str(bundle_path)]
        verify_result = subprocess.run(verify_cmd, capture_output=True, text=True, check=True)
        print("✅ Signature verified successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to sign macOS bundle: {e}")
        print(f"   stdout: {e.stdout}")
        print(f"   stderr: {e.stderr}")
        return False

def create_test_certificate():
    """Create a test certificate for development signing (Windows only)"""
    if sys.platform != 'win32':
        print("⚠️  Test certificate creation is Windows-only")
        return False
    
    print("Creating test certificate for development...")
    
    # Find makecert.exe
    makecert_paths = [
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64",
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22000.0\x64",
        r"C:\Program Files\Microsoft SDKs\Windows\v7.1\Bin"
    ]
    
    makecert = find_executable('makecert.exe', makecert_paths)
    if not makecert:
        print("❌ makecert.exe not found for test certificate creation")
        return False
    
    script_dir = get_script_dir()
    cert_path = script_dir / 'test_cert.p12'
    
    # Create test certificate
    try:
        cmd = [
            makecert,
            '-r', '-pe', '-n', 'CN=Omneva Test Certificate',
            '-eku', '1.3.6.1.5.5.7.3.3', '-ss', 'My',
            '-sr', 'CurrentUser', '-sky', 'exchange',
            '-sp', 'Microsoft RSA SChannel Cryptographic Provider',
            '-sy', '12', str(cert_path)
        ]
        
        subprocess.run(cmd, check=True)
        print(f"✅ Test certificate created: {cert_path}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create test certificate: {e}")
        return False

def sign_build_artifacts(build_dir=None, cert_path=None, identity=None):
    """Sign all build artifacts in the specified directory"""
    if build_dir is None:
        build_dir = get_script_dir() / 'dist'
    
    build_dir = Path(build_dir)
    if not build_dir.exists():
        print(f"❌ Build directory not found: {build_dir}")
        return False
    
    print(f"🔍 Scanning build directory: {build_dir}")
    
    signed_count = 0
    
    if sys.platform == 'win32':
        # Sign Windows executables
        for exe_path in build_dir.glob('*.exe'):
            if sign_windows_executable(exe_path, cert_path):
                signed_count += 1
        
        # Sign executables in subdirectories (onedir builds)
        for sub_dir in build_dir.iterdir():
            if sub_dir.is_dir():
                for exe_path in sub_dir.glob('*.exe'):
                    if sign_windows_executable(exe_path, cert_path):
                        signed_count += 1
    
    elif sys.platform == 'darwin':
        # Sign macOS .app bundles
        for app_bundle in build_dir.glob('*.app'):
            if sign_macos_bundle(app_bundle, identity):
                signed_count += 1
        
        # Sign .app bundles in subdirectories
        for sub_dir in build_dir.iterdir():
            if sub_dir.is_dir():
                for app_bundle in sub_dir.glob('*.app'):
                    if sign_macos_bundle(app_bundle, identity):
                        signed_count += 1
    
    else:
        print("⚠️  Code signing not supported on this platform")
        return False
    
    print(f"✅ Successfully signed {signed_count} artifacts")
    return signed_count > 0

def main():
    parser = argparse.ArgumentParser(description='Code signing script for Omneva Media Player')
    parser.add_argument('--cert', help='Path to code signing certificate (Windows .p12 or macOS identity)')
    parser.add_argument('--identity', help='macOS signing identity (e.g., "Developer ID Application: Your Name")')
    parser.add_argument('--entitlements', help='Path to entitlements file (macOS only)')
    parser.add_argument('--build-dir', help='Build directory containing artifacts to sign')
    parser.add_argument('--create-test-cert', action='store_true', help='Create test certificate for development')
    parser.add_argument('--target', help='Specific file or bundle to sign')
    
    args = parser.parse_args()
    
    print("🔐 Omneva Code Signing Script")
    print("=" * 50)
    
    if args.create_test_cert:
        return create_test_certificate()
    
    if args.target:
        # Sign specific target
        target = Path(args.target)
        if not target.exists():
            print(f"❌ Target not found: {target}")
            return False
        
        if sys.platform == 'win32' and target.suffix == '.exe':
            return sign_windows_executable(target, args.cert)
        elif sys.platform == 'darwin' and target.suffix == '.app':
            return sign_macos_bundle(target, args.identity, args.entitlements)
        else:
            print(f"❌ Unsupported target: {target}")
            return False
    
    else:
        # Sign all build artifacts
        return sign_build_artifacts(args.build_dir, args.cert, args.identity)

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
