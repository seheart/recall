#!/usr/bin/env python3
"""
Git Logger - Auto-log sessions from git commits with smart analysis
"""
from datetime import datetime
from pathlib import Path
from .project_memory import ProjectMemory
from .git_utils import get_recent_commits, get_changed_files
from .smart_git_analysis import CommitAnalyzer, get_commit_stats
from .logger import get_logger

logger = get_logger(__name__)


def auto_log_from_git(project_name: str, days_back: int = 7, smart_mode: bool = True) -> bool:
    """Auto-create session logs from recent git commits"""
    memory = ProjectMemory()
    project = memory.db.get_project(project_name)

    if not project:
        logger.error(f"❌ Project '{project_name}' not found")
        return False

    project_dir = project.get("directory")
    if not project_dir:
        logger.error(f"❌ No directory configured for project '{project_name}'")
        return False

    # Get commits from last N days
    since_date = f"{days_back}.days.ago"
    commits = get_recent_commits(project_dir, limit=20, since=since_date)

    if not commits:
        logger.info(f"ℹ️  No git commits found in last {days_back} days")
        return True

    # Analyze commits with smart mode if enabled
    if smart_mode:
        logger.info("🔍 Analyzing commits with smart mode...")
        analyzer = CommitAnalyzer(project_dir)
        commits = analyzer.analyze_commits(commits)

    # Group commits by date
    commits_by_date = {}
    for commit in commits:
        date = commit["date"]
        if date not in commits_by_date:
            commits_by_date[date] = []
        commits_by_date[date].append(commit)

    # Create sessions for each day
    sessions_created = 0
    for date, day_commits in sorted(commits_by_date.items(), reverse=True):
        # Check if these specific commits are already logged
        existing_sessions = memory.db.get_recent_sessions(project["id"], limit=30)

        # Check if any of the commit hashes are already in session summaries/accomplishments
        commit_hashes = [c["hash"] for c in day_commits]
        session_exists = False

        for session in existing_sessions:
            session_text = (
                str(session.get("summary") or "")
                + " "
                + str(session.get("accomplishments") or "")
                + " "
                + str(session.get("files_changed") or "")
            )

            # If any commit hash is found in existing sessions, skip this group
            if any(commit_hash in session_text for commit_hash in commit_hashes):
                session_exists = True
                break

        if session_exists:
            continue

        # Create smart summary if smart mode enabled
        if smart_mode:
            stats = get_commit_stats(day_commits)
            summary = _create_smart_summary(stats, len(day_commits))
            accomplishments = _create_smart_accomplishments(day_commits)
            decisions = _create_smart_decisions(day_commits)
        else:
            # Basic mode
            summary = f"Development work - {len(day_commits)} commit(s)"
            accomplishments = [f"{c['hash']}: {c['message']}" for c in day_commits[:5]]
            decisions = None

        # Get files changed (from first commit of the day)
        commit_ref = (
            day_commits[0]["full_hash"] if "full_hash" in day_commits[0] else day_commits[0]["hash"]
        )
        files_changed = get_changed_files(project_dir, commit_ref, limit=10)

        memory.log_session(
            project_name,
            summary=summary,
            accomplishments=accomplishments,
            decisions=decisions,
            files_changed=files_changed if files_changed else None,
        )

        sessions_created += 1
        if smart_mode:
            type_summary = ", ".join([f"{count} {type}" for type, count in stats["types"].items()])
            logger.info(f"✅ Created session for {date}: {type_summary}")
        else:
            logger.info(f"✅ Created session for {date}: {len(day_commits)} commits")

    if sessions_created > 0:
        logger.info(f"\n🎉 Auto-logged {sessions_created} session(s) from git history")
    else:
        logger.info(f"ℹ️  All recent commits already logged in sessions")

    return True


def _create_smart_summary(stats: dict, total_commits: int) -> str:
    """
    Create smart summary from commit statistics

    Args:
        stats: Statistics dict from get_commit_stats()
        total_commits: Total number of commits

    Returns:
        Human-readable summary string
    """
    parts = [f"{total_commits} commit(s)"]

    if stats.get("types"):
        type_parts = []
        for commit_type, count in sorted(stats["types"].items(), key=lambda x: -x[1]):
            type_parts.append(f"{count} {commit_type}")
        parts.append(f"({', '.join(type_parts)})")

    if stats.get("breaking_changes", 0) > 0:
        parts.append(f"⚠️ {stats['breaking_changes']} breaking change(s)")

    if stats.get("issues_referenced"):
        issues_count = len(stats["issues_referenced"])
        parts.append(f"🔗 {issues_count} issue(s) referenced")

    return " - ".join(parts)


def _create_smart_accomplishments(day_commits: list) -> list:
    """
    Create accomplishments list grouped by commit type

    Args:
        day_commits: List of analyzed commits for the day

    Returns:
        List of formatted accomplishment strings
    """
    accomplishments = []

    # Group by type
    by_type = {}
    for commit in day_commits:
        commit_type = commit.get("type", "other")
        if commit_type not in by_type:
            by_type[commit_type] = []
        by_type[commit_type].append(commit)

    # Type emoji mapping
    type_emojis = {
        "feature": "✨",
        "bugfix": "🐛",
        "refactor": "♻️",
        "docs": "📝",
        "style": "💄",
        "test": "✅",
        "chore": "🔧",
        "perf": "⚡️",
        "ci": "👷",
        "build": "📦",
        "revert": "⏪",
        "enhancement": "⬆️",
        "other": "📌",
    }

    # Format by type (prioritize features and bugfixes)
    priority_order = ["feature", "bugfix", "breaking", "enhancement", "refactor", "perf"]

    # First add priority types
    for commit_type in priority_order:
        if commit_type in by_type:
            for commit in by_type[commit_type][:3]:  # Limit per type
                emoji = type_emojis.get(commit_type, "📌")
                msg = commit["message"][:80] + ("..." if len(commit["message"]) > 80 else "")
                issues = f" ({', '.join(commit.get('issues', []))})" if commit.get("issues") else ""
                breaking = "💥 " if commit.get("is_breaking") else ""
                accomplishments.append(
                    f"{breaking}{emoji} [{commit_type}] {commit['hash']}: {msg}{issues}"
                )

    # Then add other types
    for commit_type, commits in sorted(by_type.items()):
        if commit_type in priority_order:
            continue  # Already added
        for commit in commits[:2]:  # Fewer for non-priority types
            emoji = type_emojis.get(commit_type, "📌")
            msg = commit["message"][:80] + ("..." if len(commit["message"]) > 80 else "")
            accomplishments.append(f"{emoji} [{commit_type}] {commit['hash']}: {msg}")

    return (
        accomplishments
        if accomplishments
        else [f"{c['hash']}: {c['message']}" for c in day_commits[:5]]
    )


def _create_smart_decisions(day_commits: list) -> list:
    """
    Extract breaking changes and significant decisions

    Args:
        day_commits: List of analyzed commits for the day

    Returns:
        List of decision strings, or None if no significant decisions
    """
    decisions = []

    # Extract breaking changes
    for commit in day_commits:
        if commit.get("is_breaking"):
            msg = commit["message"][:100] + ("..." if len(commit["message"]) > 100 else "")
            decisions.append(f"💥 Breaking change in {commit['hash']}: {msg}")

    # Extract scope changes (architectural decisions)
    scopes_seen = set()
    for commit in day_commits:
        scope = commit.get("scope")
        if scope and scope not in scopes_seen:
            scopes_seen.add(scope)
            # Only include if it's a feature or refactor (more likely to be significant)
            if commit.get("type") in ["feature", "refactor"]:
                decisions.append(f"🏗️ Work on '{scope}' component")

    # Extract file category shifts (e.g., database migrations, CI changes)
    significant_categories = ["database", "ci", "docker"]
    for commit in day_commits:
        file_cats = commit.get("file_categories", {})
        for category in significant_categories:
            if file_cats.get(category, 0) > 0:
                msg = commit["message"][:80] + ("..." if len(commit["message"]) > 80 else "")
                decisions.append(f"🔧 {category.capitalize()} changes: {msg}")
                break  # Only one per commit

    return decisions if decisions else None


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        logger.info("Usage: git_logger.py <project-name> [days-back]")
        sys.exit(1)

    project_name = sys.argv[1]
    days_back = int(sys.argv[2]) if len(sys.argv) > 2 else 7

    auto_log_from_git(project_name, days_back)
