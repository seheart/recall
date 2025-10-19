#!/usr/bin/env python3
"""
Git Logger - Auto-log sessions from git commits
"""
from datetime import datetime
from pathlib import Path
from .project_memory import ProjectMemory
from .git_utils import get_recent_commits, get_changed_files
from .logger import get_logger

logger = get_logger(__name__)


def auto_log_from_git(project_name: str, days_back: int = 7) -> bool:
    """Auto-create session logs from recent git commits"""
    memory = ProjectMemory()
    project = memory.db.get_project(project_name)

    if not project:
        logger.error(f"❌ Project '{project_name}' not found")
        return False

    project_dir = project.get('directory')
    if not project_dir:
        logger.error(f"❌ No directory configured for project '{project_name}'")
        return False

    # Get commits from last N days
    since_date = f"{days_back}.days.ago"
    commits = get_recent_commits(project_dir, limit=20, since=since_date)

    if not commits:
        logger.info(f"ℹ️  No git commits found in last {days_back} days")
        return True

    # Group commits by date
    commits_by_date = {}
    for commit in commits:
        date = commit['date']
        if date not in commits_by_date:
            commits_by_date[date] = []
        commits_by_date[date].append(commit)

    # Create sessions for each day
    sessions_created = 0
    for date, day_commits in sorted(commits_by_date.items(), reverse=True):
        # Check if these specific commits are already logged
        existing_sessions = memory.db.get_recent_sessions(project['id'], limit=30)

        # Check if any of the commit hashes are already in session summaries/accomplishments
        commit_hashes = [c['hash'] for c in day_commits]
        session_exists = False

        for session in existing_sessions:
            session_text = (str(session.get('summary') or '') + ' ' +
                          str(session.get('accomplishments') or '') + ' ' +
                          str(session.get('files_changed') or ''))

            # If any commit hash is found in existing sessions, skip this group
            if any(commit_hash in session_text for commit_hash in commit_hashes):
                session_exists = True
                break

        if session_exists:
            continue

        # Create summary from commit messages
        summary = f"Development work - {len(day_commits)} commit(s)"
        accomplishments = [f"{c['hash']}: {c['message']}" for c in day_commits[:5]]

        # Get files changed (from first commit of the day)
        # Use full_hash for git operations
        commit_ref = day_commits[0]['full_hash'] if 'full_hash' in day_commits[0] else day_commits[0]['hash']
        files_changed = get_changed_files(project_dir, commit_ref, limit=10)

        memory.log_session(
            project_name,
            summary=summary,
            accomplishments=accomplishments,
            files_changed=files_changed if files_changed else None
        )

        sessions_created += 1
        logger.info(f"✅ Created session for {date}: {len(day_commits)} commits")

    if sessions_created > 0:
        logger.info(f"\n🎉 Auto-logged {sessions_created} session(s) from git history")
    else:
        logger.info(f"ℹ️  All recent commits already logged in sessions")

    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        logger.info("Usage: git_logger.py <project-name> [days-back]")
        sys.exit(1)

    project_name = sys.argv[1]
    days_back = int(sys.argv[2]) if len(sys.argv) > 2 else 7

    auto_log_from_git(project_name, days_back)
