#!/usr/bin/env python3
"""
Unit tests for git_utils module
"""
import pytest
import tempfile
import os
import subprocess
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from recall_lib.git_utils import (
    is_git_repo,
    get_recent_commits,
    get_changed_files,
    get_status,
    get_branch_name,
    get_remote_url,
    GitError
)


@pytest.fixture
def git_repo():
    """Create a temporary git repository for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Initialize git repo
        subprocess.run(['git', 'init'], cwd=tmpdir, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=tmpdir, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'], cwd=tmpdir, capture_output=True)

        # Create a test file and commit
        test_file = Path(tmpdir) / 'test.txt'
        test_file.write_text('Hello, World!')
        subprocess.run(['git', 'add', '.'], cwd=tmpdir, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'], cwd=tmpdir, capture_output=True)

        yield tmpdir


@pytest.fixture
def non_git_dir():
    """Create a temporary non-git directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_is_git_repo_true(git_repo):
    """Test is_git_repo returns True for git repositories"""
    assert is_git_repo(git_repo) is True


def test_is_git_repo_false(non_git_dir):
    """Test is_git_repo returns False for non-git directories"""
    assert is_git_repo(non_git_dir) is False


def test_get_recent_commits(git_repo):
    """Test getting recent commits"""
    commits = get_recent_commits(git_repo, limit=5)

    assert len(commits) == 1
    assert commits[0]['message'] == 'Initial commit'
    assert 'hash' in commits[0]
    assert 'full_hash' in commits[0]
    assert 'date' in commits[0]


def test_get_recent_commits_with_limit(git_repo):
    """Test commit limit"""
    # Create multiple commits
    for i in range(5):
        test_file = Path(git_repo) / f'file{i}.txt'
        test_file.write_text(f'Content {i}')
        subprocess.run(['git', 'add', '.'], cwd=git_repo, capture_output=True)
        subprocess.run(['git', 'commit', '-m', f'Commit {i}'], cwd=git_repo, capture_output=True)

    commits = get_recent_commits(git_repo, limit=3)
    assert len(commits) == 3


def test_get_recent_commits_non_git_dir(non_git_dir):
    """Test get_recent_commits on non-git directory"""
    commits = get_recent_commits(non_git_dir)
    assert commits == []


def test_get_changed_files(git_repo):
    """Test getting files changed in a commit"""
    # Get the initial commit hash
    commits = get_recent_commits(git_repo, limit=1)
    commit_hash = commits[0]['full_hash']

    files = get_changed_files(git_repo, commit_hash)
    assert 'test.txt' in files


def test_get_status_clean_repo(git_repo):
    """Test git status on clean repository"""
    status = get_status(git_repo)

    assert status['has_changes'] is False
    assert len(status['staged_files']) == 0
    assert len(status['unstaged_files']) == 0
    assert len(status['untracked_files']) == 0


def test_get_status_with_untracked_files(git_repo):
    """Test git status with untracked files"""
    # Create a new file without adding it
    new_file = Path(git_repo) / 'untracked.txt'
    new_file.write_text('Untracked content')

    status = get_status(git_repo)

    assert status['has_changes'] is True
    assert 'untracked.txt' in status['untracked_files']


def test_get_status_with_staged_files(git_repo):
    """Test git status with staged files"""
    # Create and stage a new file
    new_file = Path(git_repo) / 'staged.txt'
    new_file.write_text('Staged content')
    subprocess.run(['git', 'add', 'staged.txt'], cwd=git_repo, capture_output=True)

    status = get_status(git_repo)

    assert status['has_changes'] is True
    assert 'staged.txt' in status['staged_files']


def test_get_status_with_unstaged_changes(git_repo):
    """Test git status with unstaged changes"""
    # Modify existing file without staging
    test_file = Path(git_repo) / 'test.txt'
    test_file.write_text('Modified content')

    status = get_status(git_repo)

    assert status['has_changes'] is True
    assert 'test.txt' in status['unstaged_files']


def test_get_branch_name(git_repo):
    """Test getting current branch name"""
    branch = get_branch_name(git_repo)

    # Default branch is usually 'master' or 'main'
    assert branch in ['master', 'main']


def test_get_branch_name_non_git_dir(non_git_dir):
    """Test get_branch_name on non-git directory"""
    branch = get_branch_name(non_git_dir)
    assert branch is None


def test_get_remote_url(git_repo):
    """Test getting remote URL"""
    # Add a remote
    subprocess.run(
        ['git', 'remote', 'add', 'origin', 'https://github.com/test/repo.git'],
        cwd=git_repo,
        capture_output=True
    )

    remote = get_remote_url(git_repo)
    assert remote == 'https://github.com/test/repo.git'


def test_get_remote_url_no_remote(git_repo):
    """Test get_remote_url when no remote exists"""
    remote = get_remote_url(git_repo)
    assert remote is None


def test_get_remote_url_non_git_dir(non_git_dir):
    """Test get_remote_url on non-git directory"""
    remote = get_remote_url(non_git_dir)
    assert remote is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
