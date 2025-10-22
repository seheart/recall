#!/usr/bin/env python3
"""
Incremental Analysis - Smart caching and delta analysis to avoid re-analyzing unchanged code

Tracks:
- File modification times
- Directory structure changes
- Git commit history
- Analysis cache with invalidation
"""
import os
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
from .logger import get_logger

logger = get_logger(__name__)


class IncrementalAnalyzer:
    """
    Manages incremental analysis with smart caching

    Avoids re-analyzing unchanged parts of projects by:
    - Tracking file hashes and modification times
    - Detecting changes via git
    - Caching analysis results
    - Invalidating cache only for changed files
    """

    def __init__(self, database, project_id: int, project_dir: str):
        """
        Initialize incremental analyzer

        Args:
            database: RecallDatabase instance
            project_id: Project ID
            project_dir: Path to project directory
        """
        self.db = database
        self.project_id = project_id
        self.project_dir = Path(project_dir)
        self._cache_key = 'incremental_analysis'

    def get_cached_analysis(self) -> Optional[Dict]:
        """
        Get cached analysis data

        Returns:
            Cached analysis dict or None if not cached/invalid
        """
        conn = self.db._get_connection()
        cursor = conn.execute('''
            SELECT value FROM project_context
            WHERE project_id = ? AND category = 'cache' AND key = ?
        ''', (self.project_id, self._cache_key))

        row = cursor.fetchone()
        if not row:
            return None

        try:
            cache_data = json.loads(row[0])

            # Check if cache is still valid
            if self._is_cache_valid(cache_data):
                return cache_data.get('analysis')
            else:
                logger.debug("Cache invalidated due to file changes")
                return None

        except json.JSONDecodeError:
            return None

    def save_analysis_cache(self, analysis: Dict, file_states: Dict[str, Dict]):
        """
        Save analysis results to cache

        Args:
            analysis: Analysis results dict
            file_states: Dict mapping file paths to their state (hash, mtime)
        """
        cache_data = {
            'analysis': analysis,
            'file_states': file_states,
            'cached_at': datetime.now().isoformat()
        }

        conn = self.db._get_connection()
        conn.execute('''
            INSERT OR REPLACE INTO project_context (project_id, category, key, value)
            VALUES (?, ?, ?, ?)
        ''', (self.project_id, 'cache', self._cache_key, json.dumps(cache_data)))
        conn.commit()

        logger.debug(f"Cached analysis for {len(file_states)} files")

    def get_changed_files(self, since: Optional[str] = None) -> Set[str]:
        """
        Get files that have changed since last analysis

        Args:
            since: Timestamp to check changes since (ISO format)

        Returns:
            Set of changed file paths (relative to project dir)
        """
        # Try git first (most accurate for git repos)
        git_changed = self._get_git_changed_files(since)
        if git_changed is not None:
            return git_changed

        # Fall back to file system checking
        return self._get_filesystem_changed_files(since)

    def _get_git_changed_files(self, since: Optional[str]) -> Optional[Set[str]]:
        """Get changed files via git"""
        try:
            import subprocess

            # Check if it's a git repo
            result = subprocess.run(
                ['git', 'rev-parse', '--git-dir'],
                cwd=self.project_dir,
                capture_output=True,
                timeout=5
            )

            if result.returncode != 0:
                return None

            # Get changed files
            if since:
                # Convert ISO timestamp to git format
                git_since = since.replace('T', ' ').split('.')[0]
                cmd = ['git', 'diff', '--name-only', f'--since={git_since}', 'HEAD']
            else:
                # Get all tracked files that differ from last commit
                cmd = ['git', 'diff', '--name-only', 'HEAD']

            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                changed = set(line.strip() for line in result.stdout.split('\n') if line.strip())
                return changed

        except Exception as e:
            logger.debug(f"Git changed files detection failed: {e}")

        return None

    def _get_filesystem_changed_files(self, since: Optional[str]) -> Set[str]:
        """Get changed files via filesystem scanning"""
        changed = set()

        # Get cached file states
        cache = self.get_cached_analysis()
        if not cache:
            # No cache, all files are "changed"
            return self._get_all_source_files()

        cached_states = cache.get('file_states', {})

        # Check each cached file
        for file_path, cached_state in cached_states.items():
            full_path = self.project_dir / file_path

            if not full_path.exists():
                # File was deleted
                changed.add(file_path)
                continue

            # Check modification time
            current_mtime = full_path.stat().st_mtime
            cached_mtime = cached_state.get('mtime', 0)

            if current_mtime > cached_mtime:
                changed.add(file_path)

        # Check for new files
        current_files = self._get_all_source_files()
        for file_path in current_files:
            if file_path not in cached_states:
                changed.add(file_path)

        return changed

    def _get_all_source_files(self) -> Set[str]:
        """Get all source files in project"""
        source_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.go', '.rs', '.java', '.c', '.cpp', '.rb'}
        source_files = set()

        for root, dirs, files in os.walk(self.project_dir):
            # Skip common directories
            dirs[:] = [d for d in dirs if d not in {'.git', 'node_modules', '__pycache__', 'venv', '.venv', 'target', 'build', 'dist'}]

            for file in files:
                file_path = Path(root) / file
                if file_path.suffix in source_extensions:
                    rel_path = file_path.relative_to(self.project_dir)
                    source_files.add(str(rel_path))

        return source_files

    def get_file_states(self, files: Set[str] = None) -> Dict[str, Dict]:
        """
        Get current state (hash, mtime) of files

        Args:
            files: Specific files to check, or None for all source files

        Returns:
            Dict mapping file paths to state dicts
        """
        if files is None:
            files = self._get_all_source_files()

        states = {}

        for file_path in files:
            full_path = self.project_dir / file_path

            if not full_path.exists():
                continue

            try:
                # Get modification time
                mtime = full_path.stat().st_mtime

                # Calculate hash (for small files only, to avoid performance issues)
                file_hash = None
                if full_path.stat().st_size < 1024 * 1024:  # < 1MB
                    with open(full_path, 'rb') as f:
                        file_hash = hashlib.md5(f.read()).hexdigest()

                states[file_path] = {
                    'mtime': mtime,
                    'hash': file_hash,
                    'size': full_path.stat().st_size
                }

            except Exception as e:
                logger.debug(f"Failed to get state for {file_path}: {e}")

        return states

    def _is_cache_valid(self, cache_data: Dict) -> bool:
        """
        Check if cached analysis is still valid

        Args:
            cache_data: Cached data dict

        Returns:
            True if cache is valid, False otherwise
        """
        cached_states = cache_data.get('file_states', {})

        # Check a sample of files for changes
        sample_size = min(10, len(cached_states))
        sample_files = list(cached_states.keys())[:sample_size]

        for file_path in sample_files:
            full_path = self.project_dir / file_path

            # Check if file still exists
            if not full_path.exists():
                return False

            # Check modification time
            cached_mtime = cached_states[file_path].get('mtime', 0)
            current_mtime = full_path.stat().st_mtime

            if current_mtime > cached_mtime:
                return False

        return True

    def should_analyze(self, force: bool = False) -> bool:
        """
        Determine if project should be analyzed

        Args:
            force: Force analysis even if cache is valid

        Returns:
            True if analysis should run, False if can use cache
        """
        if force:
            return True

        cache = self.get_cached_analysis()
        if not cache:
            return True

        # Check for changes
        changed_files = self.get_changed_files()
        if changed_files:
            logger.info(f"📝 Detected {len(changed_files)} changed file(s)")
            return True

        logger.info("✨ No changes detected, using cached analysis")
        return False

    def invalidate_cache(self):
        """Invalidate analysis cache"""
        conn = self.db._get_connection()
        conn.execute('''
            DELETE FROM project_context
            WHERE project_id = ? AND category = 'cache' AND key = ?
        ''', (self.project_id, self._cache_key))
        conn.commit()

        logger.debug("Invalidated analysis cache")


def get_analysis_diff(old_analysis: Dict, new_analysis: Dict) -> Dict:
    """
    Compare two analysis results and return differences

    Args:
        old_analysis: Previous analysis results
        new_analysis: New analysis results

    Returns:
        Dict with added, removed, and changed items
    """
    diff = {
        'added': {},
        'removed': {},
        'changed': {}
    }

    # Compare top-level keys
    old_keys = set(old_analysis.keys())
    new_keys = set(new_analysis.keys())

    # Added keys
    for key in new_keys - old_keys:
        diff['added'][key] = new_analysis[key]

    # Removed keys
    for key in old_keys - new_keys:
        diff['removed'][key] = old_analysis[key]

    # Changed keys
    for key in old_keys & new_keys:
        if old_analysis[key] != new_analysis[key]:
            diff['changed'][key] = {
                'old': old_analysis[key],
                'new': new_analysis[key]
            }

    return diff
