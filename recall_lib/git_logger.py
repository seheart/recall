#!/usr/bin/env python3
"""
Git Logger - Auto-log sessions from git commits
"""
import subprocess
from datetime import datetime
from pathlib import Path
from .project_memory import ProjectMemory


def get_recent_commits(project_dir: str, since_date: str = None, limit: int = 10):
    """Get recent git commits"""
    if not Path(project_dir).exists():
        return []

    if not (Path(project_dir) / '.git').exists():
        return []

    try:
        cmd = ['git', 'log', f'-{limit}', '--pretty=format:%H|||%s|||%ad', '--date=iso']
        if since_date:
            cmd.append(f'--since={since_date}')

        result = subprocess.run(
            cmd,
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            return []

        commits = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            parts = line.split('|||')
            if len(parts) == 3:
                commits.append({
                    'hash': parts[0][:7],
                    'message': parts[1],
                    'date': parts[2][:10]
                })

        return commits

    except Exception as e:
        print(f"Error getting commits: {e}")
        return []


def get_changed_files(project_dir: str, commit_hash: str):
    """Get files changed in a commit"""
    try:
        result = subprocess.run(
            ['git', 'show', '--pretty=', '--name-only', commit_hash],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            files = [f for f in result.stdout.strip().split('\n') if f]
            return files[:10]  # Limit to 10 files

        return []

    except Exception as e:
        return []


def auto_log_from_git(project_name: str, days_back: int = 7):
    """Auto-create session logs from recent git commits"""
    memory = ProjectMemory()
    project = memory.db.get_project(project_name)

    if not project:
        print(f"❌ Project '{project_name}' not found")
        return False

    project_dir = project.get('directory')
    if not project_dir:
        print(f"❌ No directory configured for project '{project_name}'")
        return False

    # Get commits from last N days
    since_date = f"{days_back}.days.ago"
    commits = get_recent_commits(project_dir, since_date, limit=20)

    if not commits:
        print(f"ℹ️  No git commits found in last {days_back} days")
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
        files_changed = get_changed_files(project_dir, day_commits[0]['hash'] + '^!')

        memory.log_session(
            project_name,
            summary=summary,
            accomplishments=accomplishments,
            files_changed=files_changed if files_changed else None
        )

        sessions_created += 1
        print(f"✅ Created session for {date}: {len(day_commits)} commits")

    if sessions_created > 0:
        print(f"\n🎉 Auto-logged {sessions_created} session(s) from git history")
    else:
        print(f"ℹ️  All recent commits already logged in sessions")

    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: git_logger.py <project-name> [days-back]")
        sys.exit(1)

    project_name = sys.argv[1]
    days_back = int(sys.argv[2]) if len(sys.argv) > 2 else 7

    auto_log_from_git(project_name, days_back)
