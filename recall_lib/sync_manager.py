"""
Sync Manager - Cross-machine database synchronization
Handles syncing recall database between computers using SSH/rsync

Security Features:
    - Input validation for all user-provided parameters
    - Command injection prevention using proper escaping
    - Path traversal protection
    - Automatic backup creation before destructive operations
    - File locking to prevent concurrent modification
    - Integrity verification after pull operations
    - Secure configuration storage with proper permissions
"""
import subprocess
import os
import shutil
import json
import stat
import re
import sqlite3
import threading
import fcntl
from shlex import quote
from pathlib import Path
from typing import Dict, Tuple, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Security logger for audit trail
security_logger = logging.getLogger('recall.security')
security_handler = logging.FileHandler(
    os.path.expanduser('~/.local/share/recall/security.log')
)
security_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
)
security_logger.addHandler(security_handler)
security_logger.setLevel(logging.WARNING)


class SyncManager:
    """Manages database synchronization between machines using SSH/rsync.

    This class provides secure cross-machine synchronization of the Recall
    database using SSH for authentication and rsync for efficient file transfer.

    Thread Safety:
        Uses file locking to ensure thread-safe backup operations.
    """

    # Configuration constants
    DEFAULT_SSH_TIMEOUT = 10
    DEFAULT_RSYNC_TIMEOUT = 300  # 5 minutes
    MAX_RSYNC_TIMEOUT = 3600  # 1 hour
    DEFAULT_BACKUP_RETENTION = 5

    def __init__(self, db_path: str, ssh_timeout: int = None,
                 rsync_timeout: int = None, backup_retention: int = None):
        self.db_path = Path(db_path).expanduser()
        self.backup_dir = self.db_path.parent / "sync_backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.db_path.parent / "sync_config.json"
        self._lock_file = self.backup_dir / ".lock"
        self._backup_lock = threading.Lock()

        # Timeouts
        self.ssh_timeout = min(ssh_timeout or self.DEFAULT_SSH_TIMEOUT, 30)
        self.rsync_timeout = min(
            rsync_timeout or self.DEFAULT_RSYNC_TIMEOUT,
            self.MAX_RSYNC_TIMEOUT
        )
        self.backup_retention = backup_retention or self.DEFAULT_BACKUP_RETENTION

    def validate_host(self, host: str) -> Tuple[bool, str]:
        """Validate SSH host format and prevent command injection.

        Args:
            host: SSH host in format [user@]hostname or [user@]IP

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not host or not isinstance(host, str):
            return False, "Host is required"

        if len(host) > 255:
            return False, "Host too long"

        # Allow: user@hostname, hostname, IP addresses
        pattern = r'^([a-zA-Z0-9_-]+@)?([a-zA-Z0-9.-]+|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})$'
        if not re.match(pattern, host):
            return False, "Invalid host format"

        # Prevent command injection characters
        dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '\n', '\r', '\\']
        if any(char in host for char in dangerous_chars):
            return False, "Host contains invalid characters"

        return True, ""

    def validate_remote_path(self, remote_path: str) -> Tuple[bool, str]:
        """Validate remote path for safety and prevent path traversal.

        Args:
            remote_path: Remote file path

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not remote_path or not isinstance(remote_path, str):
            return False, "Remote path cannot be empty"

        if len(remote_path) > 500:
            return False, "Remote path too long"

        # Check for path traversal attempts
        if '..' in remote_path:
            return False, "Path traversal not allowed"

        # Prevent dangerous system paths
        dangerous_prefixes = [
            '/etc/', '/bin/', '/usr/bin/', '/sbin/', '/boot/',
            '/sys/', '/proc/', '/dev/', '/root/'
        ]
        for prefix in dangerous_prefixes:
            if remote_path.startswith(prefix):
                return False, f"Cannot sync to system directory: {prefix}"

        # Command injection prevention
        dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '\n', '\r']
        if any(char in remote_path for char in dangerous_chars):
            return False, "Remote path contains invalid characters"

        return True, ""

    def validate_ssh_key(self, ssh_key: str) -> Tuple[bool, str]:
        """Validate SSH key path.

        Args:
            ssh_key: Path to SSH private key

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            ssh_key_path = Path(ssh_key).expanduser()

            if not ssh_key_path.exists():
                return False, f"SSH key not found: {ssh_key}"

            if not ssh_key_path.is_file():
                return False, "SSH key must be a file"

            # Check permissions aren't too open
            st = ssh_key_path.stat()
            if st.st_mode & (stat.S_IRGRP | stat.S_IROTH):
                return False, "SSH key permissions too open (should be 0600)"

            return True, ""
        except Exception as e:
            return False, f"Invalid SSH key path: {e}"

    def _validate_sync_params(self, host: str, remote_path: str,
                             ssh_key: Optional[str] = None) -> Tuple[bool, str]:
        """Validate all sync operation parameters.

        Args:
            host: SSH host
            remote_path: Remote file path
            ssh_key: Optional SSH key path

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate host
        valid, error_msg = self.validate_host(host)
        if not valid:
            security_logger.warning(f"Invalid host format attempted: {host[:50]}")
            return False, error_msg

        # Validate remote path
        valid, error_msg = self.validate_remote_path(remote_path)
        if not valid:
            security_logger.warning(f"Invalid remote path attempted: {remote_path[:50]}")
            return False, error_msg

        # Validate SSH key if provided
        if ssh_key:
            valid, error_msg = self.validate_ssh_key(ssh_key)
            if not valid:
                security_logger.warning(f"Invalid SSH key attempted: {ssh_key[:50]}")
                return False, error_msg

        return True, ""

    def save_config(self, host: str, remote_path: str, ssh_key: Optional[str] = None):
        """Save sync configuration with secure permissions.

        Args:
            host: SSH host
            remote_path: Remote file path
            ssh_key: Optional SSH key path
        """
        config = {
            "host": host,
            "remote_path": remote_path,
        }
        if ssh_key:
            config["ssh_key"] = ssh_key

        # Write to temporary file first
        temp_file = self.config_file.with_suffix('.tmp')
        temp_file.write_text(json.dumps(config, indent=2))

        # Set restrictive permissions (owner read/write only)
        os.chmod(temp_file, stat.S_IRUSR | stat.S_IWUSR)

        # Atomic rename
        temp_file.rename(self.config_file)

        logger.info(f"Saved sync config to {self.config_file}")

    def load_config(self) -> Dict[str, str]:
        """Load sync configuration.

        Returns:
            Dictionary with configuration values
        """
        if not self.config_file.exists():
            return {}

        # Verify file permissions
        st = self.config_file.stat()
        if st.st_mode & (stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH):
            logger.warning(f"Config file has insecure permissions: {oct(st.st_mode)}")

        try:
            return json.loads(self.config_file.read_text())
        except json.JSONDecodeError:
            # Fallback to old format for backward compatibility
            config = {}
            for line in self.config_file.read_text().strip().split("\n"):
                if "=" in line:
                    key, value = line.split("=", 1)
                    config[key] = value
            return config

    def verify_database_integrity(self, db_path: Path) -> Tuple[bool, str]:
        """Verify SQLite database integrity.

        Args:
            db_path: Path to database file

        Returns:
            Tuple of (is_valid, message)
        """
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            conn.close()

            if result == "ok":
                return True, "Database integrity OK"
            else:
                return False, f"Database integrity check failed: {result}"
        except Exception as e:
            return False, f"Failed to check integrity: {e}"

    def create_backup(self) -> Path:
        """Create a backup of the local database with file locking.

        Returns:
            Path to created backup file
        """
        with self._backup_lock:
            # Acquire file lock for cross-process safety
            lock_fd = None
            try:
                lock_fd = open(self._lock_file, 'w')
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)

                # Check if database exists
                if not self.db_path.exists():
                    raise FileNotFoundError(f"Database not found: {self.db_path}")

                # Add microseconds to timestamp to avoid collisions
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                backup_path = self.backup_dir / f"backup_{timestamp}.db"

                # Use atomic copy via temporary file
                temp_backup = backup_path.with_suffix('.tmp')
                shutil.copy2(self.db_path, temp_backup)

                # Set secure permissions
                os.chmod(temp_backup, stat.S_IRUSR | stat.S_IWUSR)

                # Atomic rename
                temp_backup.rename(backup_path)

                logger.info(f"Created backup at {backup_path}")

                # Keep only last N backups
                backups = sorted(self.backup_dir.glob("backup_*.db"), reverse=True)
                for old_backup in backups[self.backup_retention:]:
                    try:
                        old_backup.unlink()
                        logger.info(f"Removed old backup: {old_backup}")
                    except OSError as e:
                        logger.warning(f"Could not remove old backup {old_backup}: {e}")

                return backup_path
            finally:
                if lock_fd:
                    fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                    lock_fd.close()

    def test_connection(self, host: str, ssh_key: Optional[str] = None) -> Tuple[bool, str]:
        """Test SSH connection to remote host.

        Args:
            host: SSH host
            ssh_key: Optional SSH key path

        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate inputs
            valid, error_msg = self.validate_host(host)
            if not valid:
                return False, f"❌ {error_msg}"

            if ssh_key:
                valid, error_msg = self.validate_ssh_key(ssh_key)
                if not valid:
                    return False, f"❌ {error_msg}"

            cmd = ["ssh"]
            if ssh_key:
                ssh_key_path = str(Path(ssh_key).expanduser())
                cmd.extend(["-i", ssh_key_path])

            cmd.extend([
                "-o", "ConnectTimeout=5",
                "-o", "BatchMode=yes",
                "-o", "StrictHostKeyChecking=accept-new",
                host,
                "echo", "OK"
            ])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.ssh_timeout
            )

            if result.returncode == 0:
                logger.info(f"SSH connection test successful to {host}")
                return True, "✅ Connection successful"
            else:
                error_msg = result.stderr.strip()
                security_logger.warning(f"SSH connection failed to {host}: {error_msg[:100]}")
                return False, f"❌ Connection failed: {error_msg}"

        except subprocess.TimeoutExpired:
            return False, f"❌ Connection timeout ({self.ssh_timeout}s)"
        except Exception as e:
            logger.error(f"Connection test error: {e}")
            return False, f"❌ Error: {str(e)}"

    def push_to_remote(self, host: str, remote_path: str,
                       ssh_key: Optional[str] = None) -> Tuple[bool, str]:
        """Push local database to remote server using rsync.

        Args:
            host: SSH host
            remote_path: Remote file path
            ssh_key: Optional SSH key path

        Returns:
            Tuple of (success, message)
        """
        try:
            # Validate all inputs
            valid, error_msg = self._validate_sync_params(host, remote_path, ssh_key)
            if not valid:
                return False, f"❌ {error_msg}"

            # Try to acquire exclusive database lock
            try:
                conn = sqlite3.connect(self.db_path, timeout=5.0)
                conn.execute("BEGIN IMMEDIATE")

                # Create backup
                backup_path = self.create_backup()

                conn.commit()
                conn.close()
            except sqlite3.OperationalError as e:
                return False, f"❌ Database is locked, cannot sync: {e}"

            # Build rsync command
            cmd = ["rsync", "-avz", "--progress"]

            if ssh_key:
                ssh_key_path = str(Path(ssh_key).expanduser())
                # Use quote() to prevent command injection
                ssh_cmd = f"ssh -i {quote(ssh_key_path)}"
                cmd.extend(["-e", ssh_cmd])

            cmd.extend([str(self.db_path), f"{host}:{remote_path}"])

            logger.info(f"Pushing to remote: {host}:{remote_path}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.rsync_timeout
            )

            if result.returncode == 0:
                msg = f"✅ Successfully pushed database to {host}\n📦 Backup saved: {backup_path.name}"
                logger.info(f"Successfully pushed to {host}")
                return True, msg
            else:
                error_msg = result.stderr.strip()
                security_logger.warning(f"Push failed to {host}: {error_msg[:100]}")
                return False, f"❌ Push failed: {error_msg}"

        except subprocess.TimeoutExpired:
            return False, f"❌ Push timeout ({self.rsync_timeout}s)"
        except Exception as e:
            logger.error(f"Push error: {e}")
            return False, f"❌ Error: {str(e)}"

    def pull_from_remote(self, host: str, remote_path: str,
                        ssh_key: Optional[str] = None) -> Tuple[bool, str]:
        """Pull database from remote server using rsync.

        Args:
            host: SSH host
            remote_path: Remote file path
            ssh_key: Optional SSH key path

        Returns:
            Tuple of (success, message)
        """
        temp_db = None
        try:
            # Validate all inputs
            valid, error_msg = self._validate_sync_params(host, remote_path, ssh_key)
            if not valid:
                return False, f"❌ {error_msg}"

            # Create backup first
            backup_path = self.create_backup()

            # Download to temporary file first
            temp_db = self.db_path.with_suffix('.tmp')

            # Build rsync command
            cmd = ["rsync", "-avz", "--progress"]

            if ssh_key:
                ssh_key_path = str(Path(ssh_key).expanduser())
                # Use quote() to prevent command injection
                ssh_cmd = f"ssh -i {quote(ssh_key_path)}"
                cmd.extend(["-e", ssh_cmd])

            cmd.extend([f"{host}:{remote_path}", str(temp_db)])

            logger.info(f"Pulling from remote: {host}:{remote_path}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.rsync_timeout
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip()
                security_logger.warning(f"Pull failed from {host}: {error_msg[:100]}")
                return False, f"❌ Pull failed: {error_msg}"

            # Verify integrity of downloaded database
            valid, integrity_msg = self.verify_database_integrity(temp_db)
            if not valid:
                if temp_db.exists():
                    temp_db.unlink()
                return False, f"❌ Downloaded database is corrupted: {integrity_msg}"

            # Atomic rename
            temp_db.rename(self.db_path)

            msg = f"✅ Successfully pulled database from {host}\n📦 Backup saved: {backup_path.name}"
            logger.info(f"Successfully pulled from {host}")
            return True, msg

        except subprocess.TimeoutExpired:
            if temp_db and temp_db.exists():
                temp_db.unlink()
            return False, f"❌ Pull timeout ({self.rsync_timeout}s)"
        except Exception as e:
            if temp_db and temp_db.exists():
                temp_db.unlink()
            logger.error(f"Pull error: {e}")
            return False, f"❌ Error: {str(e)}"

    def get_db_size(self) -> str:
        """Get database file size in human-readable format.

        Returns:
            Formatted size string
        """
        if not self.db_path.exists():
            return "0 B"

        size_bytes = self.db_path.stat().st_size

        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0

        return f"{size_bytes:.1f} TB"

    def get_last_sync_time(self) -> Optional[str]:
        """Get timestamp of last sync from most recent backup.

        Returns:
            Formatted timestamp string or None
        """
        backups = sorted(self.backup_dir.glob("backup_*.db"), reverse=True)
        if not backups:
            return None

        # Extract timestamp from filename: backup_20231022_143022_123456.db
        timestamp_str = backups[0].stem.replace("backup_", "")
        try:
            # Handle both old and new timestamp formats
            if len(timestamp_str) > 15:
                # New format with microseconds
                dt = datetime.strptime(timestamp_str[:15], "%Y%m%d_%H%M%S")
            else:
                dt = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse timestamp from backup filename: {e}")
            return None
