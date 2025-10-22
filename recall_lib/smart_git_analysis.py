#!/usr/bin/env python3
"""
Smart Git Analysis - Categorize commits, extract issues, detect patterns
"""
import re
from pathlib import Path
from typing import Dict, List, Set, Optional
from .git_utils import get_recent_commits, get_changed_files
from .logger import get_logger

logger = get_logger(__name__)


class CommitAnalyzer:
    """Analyzes git commits to extract rich metadata"""

    # Commit type patterns (Conventional Commits + common variations)
    TYPE_PATTERNS = {
        "feature": [r"^feat:", r"^feature:", r"^add:", r"^new:", r"\[feature\]", r"\[feat\]"],
        "bugfix": [r"^fix:", r"^bugfix:", r"^bug:", r"^hotfix:", r"\[fix\]", r"\[bugfix\]"],
        "refactor": [r"^refactor:", r"^refact:", r"^ref:", r"\[refactor\]"],
        "docs": [r"^docs?:", r"^documentation:", r"\[docs\]"],
        "style": [r"^style:", r"^format:", r"\[style\]"],
        "test": [r"^test:", r"^tests?:", r"\[test\]"],
        "chore": [r"^chore:", r"^maint:", r"^maintenance:", r"\[chore\]"],
        "perf": [r"^perf:", r"^performance:", r"\[perf\]"],
        "ci": [r"^ci:", r"\[ci\]", r"\.github/workflows"],
        "build": [r"^build:", r"\[build\]"],
        "revert": [r"^revert:", r"revert\s+"],
    }

    # Issue reference patterns
    ISSUE_PATTERNS = [
        r"#(\d+)",  # GitHub issues: #123
        r"GH-(\d+)",  # GitHub: GH-123
        r"([A-Z]+-\d+)",  # Jira: PROJECT-123
        r"closes?\s+#(\d+)",  # Closes #123
        r"fixes?\s+#(\d+)",  # Fixes #123
        r"resolves?\s+#(\d+)",  # Resolves #123
    ]

    # Breaking change patterns
    BREAKING_PATTERNS = [
        r"BREAKING[ -]CHANGE",
        r"!:",  # Conventional Commits breaking change indicator
        r"\[breaking\]",
        r"breaking:",
    ]

    # File type categorization
    FILE_CATEGORIES = {
        "code": [".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rb", ".java", ".c", ".cpp", ".rs"],
        "config": [".json", ".yaml", ".yml", ".toml", ".ini", ".conf", ".env"],
        "docs": [".md", ".rst", ".txt", "README", "CHANGELOG", "LICENSE"],
        "tests": ["test_", "_test.", ".test.", ".spec."],
        "styles": [".css", ".scss", ".sass", ".less"],
        "templates": [".html", ".jinja", ".j2", ".hbs"],
        "database": [".sql", ".db", "migration", "alembic"],
        "ci": [".github/", ".gitlab-ci", "Jenkinsfile", ".travis", ".circleci"],
        "docker": ["Dockerfile", "docker-compose", ".dockerignore"],
    }

    def __init__(self, directory: str):
        self.directory = directory

    def analyze_commit(self, commit: Dict) -> Dict:
        """
        Analyze a single commit and extract metadata

        Args:
            commit: Commit dict with 'hash', 'message', 'date' keys

        Returns:
            Enhanced commit dict with analysis metadata
        """
        message = commit["message"]
        commit_hash = commit["full_hash"]

        # Get changed files
        changed_files = get_changed_files(self.directory, commit_hash, limit=100)

        # Analyze commit type
        commit_type = self._detect_commit_type(message)

        # Extract issue references
        issues = self._extract_issues(message)

        # Detect breaking changes
        is_breaking = self._is_breaking_change(message)

        # Categorize files changed
        file_categories = self._categorize_files(changed_files)

        # Detect scope (from conventional commits)
        scope = self._extract_scope(message)

        # Enhanced commit data
        return {
            **commit,  # Include original data
            "type": commit_type,
            "scope": scope,
            "issues": issues,
            "is_breaking": is_breaking,
            "files_changed": changed_files,
            "file_categories": file_categories,
            "files_count": len(changed_files),
        }

    def _detect_commit_type(self, message: str) -> str:
        """
        Detect commit type from message

        Args:
            message: Commit message

        Returns:
            Commit type string ('feature', 'bugfix', etc.) or 'other'
        """
        message_lower = message.lower()

        for commit_type, patterns in self.TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return commit_type

        # Default heuristics
        if any(word in message_lower for word in ["add", "implement", "create", "introduce"]):
            return "feature"
        elif any(word in message_lower for word in ["fix", "bug", "issue", "error"]):
            return "bugfix"
        elif any(word in message_lower for word in ["update", "improve", "enhance", "optimize"]):
            return "enhancement"

        return "other"

    def _extract_issues(self, message: str) -> List[str]:
        """Extract issue references from commit message"""
        issues = set()

        for pattern in self.ISSUE_PATTERNS:
            matches = re.findall(pattern, message, re.IGNORECASE)
            for match in matches:
                # Normalize the issue reference
                if isinstance(match, tuple):
                    match = match[0]
                issues.add(match)

        return sorted(list(issues))

    def _is_breaking_change(self, message: str) -> bool:
        """Detect if commit contains breaking changes"""
        for pattern in self.BREAKING_PATTERNS:
            if re.search(pattern, message, re.IGNORECASE):
                return True
        return False

    def _extract_scope(self, message: str) -> Optional[str]:
        """
        Extract scope from conventional commit format

        Example: "feat(auth): add login" → scope is "auth"
        """
        match = re.match(r"^[a-z]+\(([a-z0-9-_]+)\):", message, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _categorize_files(self, files: List[str]) -> Dict[str, int]:
        """
        Categorize changed files by type

        Args:
            files: List of file paths

        Returns:
            Dict mapping category to count
        """
        categories = {}

        for filepath in files:
            file_lower = filepath.lower()
            ext = Path(filepath).suffix

            # Check each category
            matched = False
            for category, patterns in self.FILE_CATEGORIES.items():
                for pattern in patterns:
                    if pattern.startswith("."):
                        # Extension match
                        if ext == pattern:
                            categories[category] = categories.get(category, 0) + 1
                            matched = True
                            break
                    else:
                        # Substring match
                        if pattern in file_lower:
                            categories[category] = categories.get(category, 0) + 1
                            matched = True
                            break
                if matched:
                    break

            if not matched:
                categories["other"] = categories.get("other", 0) + 1

        return categories

    def analyze_commits(self, commits: List[Dict]) -> List[Dict]:
        """
        Analyze multiple commits

        Args:
            commits: List of commit dicts

        Returns:
            List of enhanced commit dicts
        """
        from rich.progress import Progress, SpinnerColumn, TextColumn

        analyzed = []

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("Analyzing commits...", total=len(commits))

            for commit in commits:
                analyzed.append(self.analyze_commit(commit))
                progress.advance(task)

        return analyzed


def get_commit_stats(analyzed_commits: List[Dict]) -> Dict:
    """
    Get aggregate statistics from analyzed commits

    Args:
        analyzed_commits: List of commits from analyze_commits()

    Returns:
        Dict with statistics
    """
    if not analyzed_commits:
        return {}

    # Count by type
    type_counts = {}
    for commit in analyzed_commits:
        commit_type = commit.get("type", "other")
        type_counts[commit_type] = type_counts.get(commit_type, 0) + 1

    # Count breaking changes
    breaking_count = sum(1 for c in analyzed_commits if c.get("is_breaking", False))

    # Aggregate file categories
    total_files_by_category = {}
    for commit in analyzed_commits:
        for category, count in commit.get("file_categories", {}).items():
            total_files_by_category[category] = total_files_by_category.get(category, 0) + count

    # Extract all issues
    all_issues = set()
    for commit in analyzed_commits:
        all_issues.update(commit.get("issues", []))

    # Most active scopes
    scope_counts = {}
    for commit in analyzed_commits:
        scope = commit.get("scope")
        if scope:
            scope_counts[scope] = scope_counts.get(scope, 0) + 1

    return {
        "total_commits": len(analyzed_commits),
        "types": type_counts,
        "breaking_changes": breaking_count,
        "files_by_category": total_files_by_category,
        "issues_referenced": sorted(list(all_issues)),
        "scopes": scope_counts,
    }


def format_commit_summary(commit: Dict) -> str:
    """
    Format a single analyzed commit for display

    Args:
        commit: Analyzed commit dict

    Returns:
        Formatted string
    """
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

    commit_type = commit.get("type", "other")
    emoji = type_emojis.get(commit_type, "📌")

    parts = [
        f"{emoji} [{commit_type}]",
        f"{commit['hash']}:",
        commit["message"][:80] + ("..." if len(commit["message"]) > 80 else ""),
    ]

    if commit.get("is_breaking"):
        parts.insert(0, "💥 BREAKING")

    if commit.get("issues"):
        parts.append(f"({', '.join(commit['issues'])})")

    return " ".join(parts)


if __name__ == "__main__":
    import sys

    # Test the smart git analysis
    logger.info("🧪 Testing Smart Git Analysis...")

    if len(sys.argv) < 2:
        logger.info("Usage: smart_git_analysis.py <project-directory>")
        sys.exit(1)

    project_dir = sys.argv[1]

    # Get recent commits
    commits = get_recent_commits(project_dir, limit=10)
    logger.info(f"Found {len(commits)} commits\n")

    # Analyze them
    analyzer = CommitAnalyzer(project_dir)
    analyzed = analyzer.analyze_commits(commits)

    # Show results
    for commit in analyzed:
        logger.info(format_commit_summary(commit))

    # Show stats
    logger.info("\n" + "=" * 60)
    stats = get_commit_stats(analyzed)
    logger.info(f"Total Commits: {stats['total_commits']}")
    logger.info(f"Breaking Changes: {stats['breaking_changes']}")
    logger.info(f"Types: {stats['types']}")
    if stats["issues_referenced"]:
        logger.info(f"Issues: {', '.join(stats['issues_referenced'])}")
