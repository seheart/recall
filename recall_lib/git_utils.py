#!/usr/bin/env python3
"""
Git utilities - Centralized git operations with error handling
"""
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from .logger import get_logger

logger = get_logger(__name__)


class GitError(Exception):
    """Exception raised for git operation errors"""
    pass


def is_git_repo(directory: str) -> bool:
    """
    Check if directory is a git repository

    Args:
        directory: Path to directory

    Returns:
        True if directory contains a .git folder
    """
    return (Path(directory) / '.git').exists()


def run_git_command(
    args: List[str],
    cwd: str,
    timeout: int = 10,
    check: bool = False
) -> Tuple[int, str, str]:
    """
    Run a git command and return results

    Args:
        args: Git command arguments (e.g., ['git', 'status'])
        cwd: Working directory
        timeout: Command timeout in seconds
        check: If True, raise GitError on non-zero return code

    Returns:
        Tuple of (returncode, stdout, stderr)

    Raises:
        GitError: If check=True and command fails
    """
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if check and result.returncode != 0:
            raise GitError(f"Git command failed: {' '.join(args)}\n{result.stderr}")

        return result.returncode, result.stdout, result.stderr

    except subprocess.TimeoutExpired as e:
        logger.error(f"Git command timed out after {timeout}s: {' '.join(args)}")
        raise GitError(f"Git command timed out: {' '.join(args)}")
    except Exception as e:
        logger.error(f"Error running git command: {e}")
        raise GitError(f"Git command error: {e}")


def get_recent_commits(
    directory: str,
    limit: int = 10,
    since: Optional[str] = None,
    format: str = "%H|||%s|||%ad"
) -> List[Dict[str, str]]:
    """
    Get recent git commits

    Args:
        directory: Project directory
        limit: Maximum number of commits
        since: Date string (e.g., "7.days.ago", "2024-01-01")
        format: Git log format string

    Returns:
        List of commit dictionaries with keys: hash, message, date
    """
    if not is_git_repo(directory):
        logger.warning(f"Not a git repository: {directory}")
        return []

    cmd = ['git', 'log', f'-{limit}', f'--pretty=format:{format}', '--date=iso']
    if since:
        cmd.append(f'--since={since}')

    try:
        returncode, stdout, stderr = run_git_command(cmd, directory)

        if returncode != 0:
            logger.warning(f"Git log failed: {stderr}")
            return []

        commits = []
        for line in stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split('|||')
            if len(parts) == 3:
                commits.append({
                    'hash': parts[0][:7],  # Short hash
                    'full_hash': parts[0],
                    'message': parts[1],
                    'date': parts[2][:10]  # Just the date part
                })

        return commits

    except GitError as e:
        logger.error(f"Error getting commits: {e}")
        return []


def get_changed_files(directory: str, commit_hash: str, limit: int = 10) -> List[str]:
    """
    Get files changed in a specific commit

    Args:
        directory: Project directory
        commit_hash: Commit hash
        limit: Maximum number of files to return

    Returns:
        List of file paths
    """
    if not is_git_repo(directory):
        return []

    try:
        cmd = ['git', 'show', '--pretty=', '--name-only', commit_hash]
        returncode, stdout, stderr = run_git_command(cmd, directory)

        if returncode != 0:
            logger.warning(f"Git show failed: {stderr}")
            return []

        files = [f for f in stdout.strip().split('\n') if f]
        return files[:limit]

    except GitError as e:
        logger.error(f"Error getting changed files: {e}")
        return []


def get_status(directory: str) -> Dict[str, any]:
    """
    Get git repository status

    Args:
        directory: Project directory

    Returns:
        Dictionary with status information:
        - has_changes: bool
        - staged_files: List[str]
        - unstaged_files: List[str]
        - untracked_files: List[str]
    """
    if not is_git_repo(directory):
        return {
            'has_changes': False,
            'staged_files': [],
            'unstaged_files': [],
            'untracked_files': []
        }

    try:
        cmd = ['git', 'status', '--porcelain']
        returncode, stdout, stderr = run_git_command(cmd, directory)

        if returncode != 0:
            logger.warning(f"Git status failed: {stderr}")
            return {'has_changes': False, 'staged_files': [], 'unstaged_files': [], 'untracked_files': []}

        staged = []
        unstaged = []
        untracked = []

        # Don't strip stdout - leading spaces are part of porcelain format!
        for line in stdout.split('\n'):
            if not line or not line.strip():  # Skip empty lines
                continue

            status_code = line[:2]
            filename = line[3:]

            # Staged changes (first character)
            if status_code[0] in ['A', 'M', 'D', 'R', 'C']:
                staged.append(filename)

            # Unstaged changes (second character)
            if status_code[1] in ['M', 'D']:
                unstaged.append(filename)

            # Untracked files
            if status_code == '??':
                untracked.append(filename)

        return {
            'has_changes': len(staged) + len(unstaged) + len(untracked) > 0,
            'staged_files': staged,
            'unstaged_files': unstaged,
            'untracked_files': untracked
        }

    except GitError as e:
        logger.error(f"Error getting git status: {e}")
        return {'has_changes': False, 'staged_files': [], 'unstaged_files': [], 'untracked_files': []}


def get_branch_name(directory: str) -> Optional[str]:
    """
    Get current git branch name

    Args:
        directory: Project directory

    Returns:
        Branch name or None if not a git repo
    """
    if not is_git_repo(directory):
        return None

    try:
        cmd = ['git', 'branch', '--show-current']
        returncode, stdout, stderr = run_git_command(cmd, directory)

        if returncode == 0:
            return stdout.strip()

        return None

    except GitError:
        return None


def get_remote_url(directory: str, remote: str = 'origin') -> Optional[str]:
    """
    Get remote URL for a git repository

    Args:
        directory: Project directory
        remote: Remote name (default: 'origin')

    Returns:
        Remote URL or None
    """
    if not is_git_repo(directory):
        return None

    try:
        cmd = ['git', 'remote', 'get-url', remote]
        returncode, stdout, stderr = run_git_command(cmd, directory)

        if returncode == 0:
            return stdout.strip()

        return None

    except GitError:
        return None
