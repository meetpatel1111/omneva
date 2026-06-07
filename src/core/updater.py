"""Auto-update System - GitHub Releases JSON endpoint and changelog dialog."""

import os
import json
import requests
import threading
from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal, QTimer
from src.core.logger import get_logger
from src.core.storage import storage


class UpdateChecker(QObject):
    """Checks for updates from GitHub Releases."""
    
    # Signals
    update_available = Signal(dict)  # release information
    no_update_available = Signal()  # no updates
    check_failed = Signal(str)  # error message
    check_completed = Signal()  # check completed
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger('update_checker')
        
        self.github_api_url = "https://api.github.com/repos/meetkumar1111/omneva/releases"
        self.github_tags_url = "https://api.github.com/repos/meetkumar1111/omneva/git/refs/tags"
        self.current_version = "1.4.1"
        self.check_interval = 24 * 60 * 60 * 1000  # 24 hours in milliseconds
        
        self.auto_check_timer = QTimer()
        self.auto_check_timer.timeout.connect(self._auto_check)
        self.auto_check_timer.setSingleShot(True)
        
        self.logger.debug("Update checker initialized")
    
    def set_current_version(self, version: str):
        """Set the current application version."""
        self.current_version = version
        self.logger.debug(f"Current version set to: {version}")
    
    def check_for_updates(self, force: bool = False) -> bool:
        """Check for updates immediately or start auto-check."""
        if force:
            # Check immediately in a separate thread
            thread = threading.Thread(target=self._check_updates_thread, daemon=True)
            thread.start()
            return True
        else:
            # Start auto-check timer
            self.auto_check_timer.start(5000)  # Start after 5 seconds
            return True
    
    def _auto_check(self):
        """Automatic check for updates."""
        self._check_updates_thread()
        
        # Schedule next check
        self.auto_check_timer.start(self.check_interval)
    
    def _get_tags_from_github(self):
        """Get tags from GitHub API."""
        try:
            response = requests.get(
                self.github_tags_url,
                headers={
                    'Accept': 'application/vnd.github.v3+json',
                    'User-Agent': 'Omneva-Updater/1.4.0'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                tags = response.json()
                return tags
            else:
                self.logger.error(f"GitHub tags API request failed: {response.status_code}")
                return []
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error getting tags: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Unexpected error getting tags: {e}")
            return []
    
    def _get_latest_tag_info(self, tags):
        """Get the latest tag information from tags list."""
        if not tags:
            return None
        
        # Sort tags by date (most recent first)
        latest_tag = None
        
        for tag in tags:
            tag_name = tag.get('ref', '').replace('refs/tags/', '')
            
            # Skip if not a version tag (starts with 'v')
            if not tag_name.startswith('v'):
                continue
            
            # Extract version number
            version = tag_name.lstrip('v')
            
            # Check if it's a newer version
            if self._is_newer_version(version):
                # Get the commit date
                commit = tag.get('object', {})
                if commit.get('type') == 'commit':
                    commit_sha = commit.get('sha')
                    if commit_sha:
                        # Get commit details (this would require another API call)
                        # For now, use the tag as latest
                        if not latest_tag or version > latest_tag.get('version', '0'):
                            latest_tag = {
                                'tag_name': tag_name,
                                'version': version,
                                'name': f"Release {tag_name}",
                                'body': f"Tag {tag_name} created",
                                'published_at': tag.get('object', {}).get('url', ''),
                                'assets': [],
                                'prerelease': False,
                                'draft': False,
                                'is_tag': True
                            }
        
        return latest_tag
    
    def _check_updates_thread(self):
        """Check for updates in a separate thread (releases and tags)."""
        try:
            self.logger.info("Checking for updates...")
            
            # Get releases from GitHub API
            releases_response = requests.get(
                self.github_api_url,
                headers={
                    'Accept': 'application/vnd.github.v3+json',
                    'User-Agent': 'Omneva-Updater/1.4.0'
                },
                timeout=30
            )
            
            # Get tags from GitHub API
            tags = self._get_tags_from_github()
            latest_tag = self._get_latest_tag_info(tags)
            
            # Process releases
            releases = []
            if releases_response.status_code == 200:
                releases = releases_response.json()
            else:
                self.logger.warning(f"GitHub releases API request failed: {releases_response.status_code}")
            
            # Combine releases and tags based on user preference
            all_updates = []
            config = get_update_config()
            prefer_tags = config.get('prefer_tags', False)
            stable_only = config.get('stable_only', True)
            
            if prefer_tags:
                # User prefers tags, add tags first
                if latest_tag:
                    all_updates.append(latest_tag)
                
                # Add releases as fallback
                if releases:
                    for release in releases:
                        if stable_only and not self._is_stable_release(release):
                            continue
                        all_updates.append(release)
            else:
                # User prefers releases (default)
                if releases:
                    for release in releases:
                        if stable_only and not self._is_stable_release(release):
                            continue
                        all_updates.append(release)
                
                # Add tags as fallback
                if not all_updates and latest_tag:
                    all_updates.append(latest_tag)
            
            if all_updates:
                # Get the most recent update
                latest_update = all_updates[0]
                
                # Check if this is a newer version
                tag_name = latest_update.get('tag_name', '').lstrip('v')
                if self._is_newer_version(tag_name):
                    self.update_available.emit(latest_update)
                    
                    update_type = "release" if not latest_update.get('is_tag') else "tag"
                    self.logger.info(f"Update available from {update_type}: {latest_update.get('tag_name')}")
                else:
                    self.no_update_available.emit()
                    self.logger.info("No updates available")
            else:
                self.no_update_available.emit()
                self.logger.info("No releases or tags found")
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error checking for updates: {e}"
            self.logger.error(error_msg)
            self.check_failed.emit(error_msg)
            
        except Exception as e:
            error_msg = f"Unexpected error checking for updates: {e}"
            self.logger.error(error_msg)
            self.check_failed.emit(error_msg)
        
        finally:
            self.check_completed.emit()
    
    def _is_newer_version(self, version: str) -> bool:
        """Compare versions to check if available version is newer."""
        try:
            # Remove 'v' prefix if present
            version = version.lstrip('v')
            current = self.current_version.lstrip('v')
            
            # Split into parts
            version_parts = [int(part) for part in version.split('.')]
            current_parts = [int(part) for part in current.split('.')]
            
            # Pad shorter version with zeros
            max_length = max(len(version_parts), len(current_parts))
            version_parts.extend([0] * (max_length - len(version_parts)))
            current_parts.extend([0] * (max_length - len(current_parts)))
            
            # Compare versions
            for vp, cp in zip(version_parts, current_parts):
                if vp > cp:
                    return True
                elif vp < cp:
                    return False
            
            return False  # Versions are equal
            
        except Exception as e:
            self.logger.error(f"Error comparing versions: {e}")
            return False
    
    def _is_stable_release(self, release_info: Dict[str, Any]) -> bool:
        """Check if the release is a stable release (not pre-release/beta)."""
        try:
            tag_name = release_info.get('tag_name', '').lstrip('v')
            name = release_info.get('name', '').lower()
            
            # Check for pre-release indicators
            prerelease_indicators = [
                'alpha', 'beta', 'rc', 'pre', 'dev', 'test', 'nightly',
                'preview', 'experimental', 'unstable'
            ]
            
            # Check tag name
            for indicator in prerelease_indicators:
                if indicator in tag_name.lower():
                    return False
            
            # Check release name
            for indicator in prerelease_indicators:
                if indicator in name:
                    return False
            
            # Check if it's a pre-release version format (e.g., 1.4.0-beta.1)
            if '-' in tag_name:
                parts = tag_name.split('-')
                if len(parts) > 1:
                    suffix = parts[1].lower()
                    for indicator in prerelease_indicators:
                        if indicator in suffix:
                            return False
            
            return True  # It's a stable release
            
        except Exception as e:
            self.logger.error(f"Error checking release stability: {e}")
            return False  # Default to stable if we can't determine
    
    def get_download_url(self, release_info: Dict[str, Any]) -> Optional[str]:
        """Get download URL for the latest release."""
        try:
            assets = release_info.get('assets', [])
            
            # Look for Windows installer first
            for asset in assets:
                name = asset.get('name', '').lower()
                if 'windows' in name and ('.exe' in name or '.msi' in name):
                    return asset.get('browser_download_url')
            
            # Look for macOS installer
            for asset in assets:
                name = asset.get('name', '').lower()
                if 'macos' in name or 'darwin' in name or '.dmg' in name:
                    return asset.get('browser_download_url')
            
            # Look for Linux AppImage or similar
            for asset in assets:
                name = asset.get('name', '').lower()
                if 'linux' in name or '.appimage' in name or '.deb' in name or '.rpm' in name:
                    return asset.get('browser_download_url')
            
            # Return first asset if no specific one found
            if assets:
                return assets[0].get('browser_download_url')
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting download URL: {e}")
            return None
    
    def get_changelog(self, release_info: Dict[str, Any]) -> str:
        """Get formatted changelog for the release or tag."""
        try:
            body = release_info.get('body', '')
            tag_name = release_info.get('tag_name', '')
            name = release_info.get('name', '')
            published_at = release_info.get('published_at', '')
            is_tag = release_info.get('is_tag', False)
            
            # Format changelog
            changelog = f"# {name or tag_name}\n\n"
            
            if is_tag:
                changelog += "**Type:** Git Tag\n"
                changelog += f"**Tag:** {tag_name}\n\n"
                if body:
                    changelog += f"**Description:** {body}\n\n"
                else:
                    changelog += "**Description:** Tag created for version release\n\n"
                changelog += "**Note:** This is a git tag, not a formal GitHub release.\n"
                changelog += "Download links may not be available for tags.\n\n"
            else:
                if published_at:
                    from datetime import datetime
                    try:
                        # Parse GitHub date format
                        pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                        formatted_date = pub_date.strftime('%B %d, %Y')
                        changelog += f"Published: {formatted_date}\n\n"
                    except Exception:
                        changelog += f"Published: {published_at}\n\n"
                
                changelog += body
            
            return changelog
            
        except Exception as e:
            self.logger.error(f"Error formatting changelog: {e}")
            return "Error loading changelog"
    
    def start_auto_check(self):
        """Start automatic update checking."""
        self.auto_check_timer.start(5000)  # Start after 5 seconds
        self.logger.info("Auto update checking started")
    
    def stop_auto_check(self):
        """Stop automatic update checking."""
        self.auto_check_timer.stop()
        self.logger.info("Auto update checking stopped")


class UpdateDownloader(QObject):
    """Handles downloading update installers."""
    
    # Signals
    download_progress = Signal(int)  # progress percentage
    download_completed = Signal(str)  # file path
    download_failed = Signal(str)  # error message
    
    def __init__(self):
        super().__init__()
        self.logger = get_logger('update_downloader')
        
        self.download_thread = None
        self.should_stop = False
        
        self.logger.debug("Update downloader initialized")
    
    def download_update(self, url: str, filename: str = None) -> bool:
        """Download update installer."""
        try:
            if self.download_thread and self.download_thread.is_alive():
                self.logger.warning("Download already in progress")
                return False
            
            # Generate filename if not provided
            if not filename:
                filename = os.path.basename(url) or "omneva_update.exe"
            
            self.should_stop = False
            
            # Start download in separate thread
            self.download_thread = threading.Thread(
                target=self._download_thread_func,
                args=(url, filename),
                daemon=True
            )
            self.download_thread.start()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start download: {e}")
            self.download_failed.emit(str(e))
            return False
    
    def _download_thread_func(self, url: str, filename: str):
        """Download function for thread."""
        try:
            # Create download directory
            download_dir = os.path.join(storage.app_data_dir, 'updates')
            os.makedirs(download_dir, exist_ok=True)
            
            file_path = os.path.join(download_dir, filename)
            
            # Download file
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if self.should_stop:
                        break
                    
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Report progress
                    if total_size > 0:
                        progress = int((downloaded / total_size) * 100)
                        self.download_progress.emit(progress)
            
            if not self.should_stop:
                self.download_completed.emit(file_path)
                self.logger.info(f"Download completed: {file_path}")
            else:
                # Clean up partial download
                if os.path.exists(file_path):
                    os.remove(file_path)
                self.logger.info("Download cancelled")
                
        except Exception as e:
            self.logger.error(f"Download failed: {e}")
            self.download_failed.emit(str(e))
    
    def cancel_download(self):
        """Cancel current download."""
        self.should_stop = True
        self.logger.info("Download cancellation requested")


class UpdateConfig:
    """Update configuration management."""
    
    def __init__(self):
        self.logger = get_logger('update_config')
        self.config_file = os.path.join(storage.app_data_dir, 'update_config.json')
        
        self.default_config = {
            'auto_check_enabled': True,
            'check_interval_hours': 24,
            'last_check_time': None,
            'last_check_version': None,
            'skip_version': None,
            'download_path': '',
            'beta_updates': False,
            'stable_only': True,
            'prefer_tags': False
        }
        
        self.config = self._load_config()
        
        self.logger.debug("Update config initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load update configuration from file."""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                
                # Merge with defaults
                merged_config = self.default_config.copy()
                merged_config.update(config)
                
                self.logger.debug("Update config loaded from file")
                return merged_config
            else:
                self.logger.debug("Using default update config")
                return self.default_config.copy()
                
        except Exception as e:
            self.logger.error(f"Failed to load update config: {e}")
            return self.default_config.copy()
    
    def save_config(self):
        """Save update configuration to file."""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            self.logger.debug("Update config saved")
            
        except Exception as e:
            self.logger.error(f"Failed to save update config: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value."""
        self.config[key] = value
        self.save_config()
    
    def should_check_for_updates(self) -> bool:
        """Check if it's time to check for updates."""
        if not self.get('auto_check_enabled', True):
            return False
        
        last_check = self.get('last_check_time')
        if not last_check:
            return True
        
        from datetime import datetime, timedelta
        
        try:
            last_check_dt = datetime.fromisoformat(last_check)
            interval_hours = self.get('check_interval_hours', 24)
            
            return datetime.now() > last_check_dt + timedelta(hours=interval_hours)
            
        except Exception as e:
            self.logger.error(f"Error checking update timing: {e}")
            return True
    
    def update_last_check(self, version: str = None):
        """Update last check time and version."""
        from datetime import datetime
        
        self.set('last_check_time', datetime.now().isoformat())
        if version:
            self.set('last_check_version', version)


# Global instances
_update_checker = None
_update_downloader = None
_update_config = None


def get_update_checker() -> UpdateChecker:
    """Get the global update checker instance."""
    global _update_checker
    if _update_checker is None:
        _update_checker = UpdateChecker()
    return _update_checker


def get_update_downloader() -> UpdateDownloader:
    """Get the global update downloader instance."""
    global _update_downloader
    if _update_downloader is None:
        _update_downloader = UpdateDownloader()
    return _update_downloader


def get_update_config() -> UpdateConfig:
    """Get the global update config instance."""
    global _update_config
    if _update_config is None:
        _update_config = UpdateConfig()
    return _update_config


def initialize_updater(current_version: str = "1.4.1"):
    """Initialize the update system."""
    checker = get_update_checker()
    checker.set_current_version(current_version)
    
    # Start auto-check if enabled
    config = get_update_config()
    if config.should_check_for_updates():
        checker.start_auto_check()
    
    return checker
