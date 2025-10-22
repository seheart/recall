#!/usr/bin/env python3
"""
Context Enrichment - Gather comprehensive context for maximum Claude intelligence

Auto-discovers and includes:
- TODO/FIXME/HACK comments
- Recent errors and warnings
- Test status and coverage
- Code snippets and key functions
- Dependencies and vulnerabilities
- Quick commands from project files
- Smart suggestions and warnings
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from .logger import get_logger

logger = get_logger(__name__)


class ContextEnricher:
    """
    Enriches project context with auto-discovered information
    """

    def __init__(self, project_dir: str, project: Dict, memory):
        """
        Initialize context enricher

        Args:
            project_dir: Path to project directory
            project: Project dict from database
            memory: ProjectMemory instance
        """
        # Validate and resolve path to prevent traversal attacks
        self.project_dir = self._validate_project_path(project_dir)
        self.project = project
        self.memory = memory
        self.context = {}

    def _validate_project_path(self, path: str) -> Path:
        """
        Validate project path to prevent directory traversal attacks

        Args:
            path: Project directory path

        Returns:
            Validated and resolved Path object

        Raises:
            ValueError: If path is invalid or unsafe
        """
        try:
            # Resolve the path (follows symlinks, converts to absolute)
            resolved_path = Path(path).resolve()

            # Check the path exists and is a directory
            if not resolved_path.exists():
                raise ValueError(f"Path does not exist: {path}")

            if not resolved_path.is_dir():
                raise ValueError(f"Path is not a directory: {path}")

            # Ensure path is within user's home directory or /tmp for safety
            home = Path.home().resolve()
            tmp = Path("/tmp").resolve()

            try:
                # Try to make path relative to home
                resolved_path.relative_to(home)
            except ValueError:
                # Not under home, check if under /tmp
                try:
                    resolved_path.relative_to(tmp)
                except ValueError:
                    # Not under home or /tmp - reject
                    logger.warning(f"Rejected path outside safe directories: {path}")
                    raise ValueError(f"Path must be within home directory or /tmp: {path}")

            return resolved_path

        except (OSError, RuntimeError) as e:
            logger.error(f"Path validation error for {path}: {e}")
            raise ValueError(f"Invalid or unsafe project path: {path}")

    def enrich_all(self) -> Dict:
        """
        Gather all enriched context

        Returns:
            Dict with enriched context sections
        """
        enriched = {
            "current_state": self._get_current_state(),
            "recent_activity": self._get_recent_activity(),
            "current_focus": self._get_current_focus(),
            "hot_files": self._get_hot_files(),
            "entry_points": self._get_entry_points(),
            "workflows": self._get_workflows(),
            "external_integrations": self._get_external_integrations(),
            "working_tree": self._get_working_tree(),
            "architecture_patterns": self._get_architecture_patterns(),
            "file_relationships": self._get_file_relationships(),
            "health_metrics": self._get_health_metrics(),
            "known_issues": self._get_known_issues_detailed(),
            "todos_and_issues": self._get_todos_and_issues(),
            "key_files": self._get_key_files(),
            "quick_commands": self._get_quick_commands(),
            "code_intelligence": self._get_code_intelligence(),
            "warnings": self._get_warnings(),
            "suggestions": self._get_suggestions(),
        }

        return enriched

    def _get_current_state(self) -> Dict:
        """Get current project state with health indicators"""
        state = {
            "status": "Unknown",
            "last_active": None,
            "health": "unknown",
            "health_emoji": "⚪",
        }

        # Get last session
        sessions = self.memory.db.get_recent_sessions(self.project["id"], limit=1)
        if sessions:
            last_session = sessions[0]
            created_at = datetime.fromisoformat(last_session["created_at"])
            time_diff = datetime.now() - created_at

            if time_diff < timedelta(hours=24):
                state["last_active"] = "Today"
            elif time_diff < timedelta(days=2):
                state["last_active"] = "Yesterday"
            elif time_diff < timedelta(days=7):
                state["last_active"] = f"{time_diff.days} days ago"
            else:
                state["last_active"] = f"{time_diff.days // 7} weeks ago"

        # Check git status for health
        try:
            import subprocess

            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                changes = result.stdout.strip()
                if not changes:
                    state["health"] = "clean"
                    state["health_emoji"] = "🟢"
                elif len(changes.split("\n")) < 10:
                    state["health"] = "active"
                    state["health_emoji"] = "🟡"
                else:
                    state["health"] = "many_changes"
                    state["health_emoji"] = "🟠"
        except Exception:
            pass

        # Get status from context
        project_context = self.memory.get_project_context(self.project["name"])
        if project_context and "context" in project_context:
            context = project_context["context"]
            if "state" in context and "status" in context["state"]:
                state["status"] = context["state"]["status"]

        return state

    def _get_recent_activity(self) -> Dict:
        """Get recent activity summary"""
        activity = {
            "commits": [],
            "sessions": 0,
            "key_changes": [],
            "time_range": "7 days",
        }

        # Get recent commits
        try:
            import subprocess

            result = subprocess.run(
                ["git", "log", "--oneline", "--since=7.days.ago"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                commit_lines = [line for line in result.stdout.split("\n") if line.strip()]
                activity["commits"] = commit_lines[:10]  # Last 10
        except Exception:
            pass

        # Get recent sessions
        sessions = self.memory.db.get_recent_sessions(self.project["id"], limit=10)
        activity["sessions"] = len(sessions)

        # Extract key changes from session accomplishments
        for session in sessions[:3]:
            accomplishments = session.get("accomplishments")
            if accomplishments:
                if isinstance(accomplishments, str):
                    activity["key_changes"].append(accomplishments[:100])
                elif isinstance(accomplishments, list):
                    for acc in accomplishments[:2]:
                        activity["key_changes"].append(str(acc)[:100])

        return activity

    def _get_current_focus(self) -> Dict:
        """Get what the project is currently focused on"""
        focus = {
            "working_on": None,
            "blockers": [],
            "next_steps": [],
            "open_questions": [],
        }

        # Get latest session
        sessions = self.memory.db.get_recent_sessions(self.project["id"], limit=1)
        if sessions:
            latest = sessions[0]

            # Working on
            summary = latest.get("summary", "")
            if summary:
                focus["working_on"] = summary

            # Next steps from context
            project_context = self.memory.get_project_context(self.project["name"])
            if project_context and "context" in project_context:
                context = project_context["context"]
            else:
                context = {}

            if "state" in context:
                if "next_steps" in context["state"]:
                    ns = context["state"]["next_steps"]
                    if isinstance(ns, str):
                        focus["next_steps"] = [ns]
                    elif isinstance(ns, list):
                        focus["next_steps"] = ns

                if "blockers" in context["state"]:
                    b = context["state"]["blockers"]
                    if isinstance(b, str):
                        focus["blockers"] = [b]
                    elif isinstance(b, list):
                        focus["blockers"] = b

        return focus

    def _get_todos_and_issues(self) -> Dict:
        """Scan codebase for TODO/FIXME/HACK comments (with resource limits)"""
        todos = {
            "todo": [],
            "fixme": [],
            "hack": [],
            "total": 0,
        }

        # Resource limits to prevent excessive scanning
        MAX_FILE_SIZE = 500_000  # 500KB per file
        MAX_FILES_SCANNED = 10000  # Maximum number of files to scan
        MAX_TOTAL_BYTES = 50_000_000  # 50MB total data read

        files_scanned = 0
        total_bytes_read = 0

        # Extensions to scan
        code_extensions = {
            ".py",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".go",
            ".rs",
            ".java",
            ".c",
            ".cpp",
            ".rb",
        }

        # Scan files
        for ext in code_extensions:
            try:
                for file_path in self.project_dir.rglob(f"*{ext}"):
                    # Check file count limit
                    if files_scanned >= MAX_FILES_SCANNED:
                        logger.warning(f"Reached max file scan limit ({MAX_FILES_SCANNED} files)")
                        break

                    # Skip common directories
                    if any(
                        part in file_path.parts
                        for part in [
                            "node_modules",
                            ".git",
                            "__pycache__",
                            "venv",
                            ".venv",
                            "target",
                            "build",
                            "dist",
                        ]
                    ):
                        continue

                    file_size = file_path.stat().st_size
                    if file_size > MAX_FILE_SIZE:  # Skip files > 500KB
                        continue

                    # Check total bytes limit
                    if total_bytes_read + file_size > MAX_TOTAL_BYTES:
                        logger.warning(f"Reached max total bytes limit ({MAX_TOTAL_BYTES} bytes)")
                        break

                    files_scanned += 1
                    total_bytes_read += file_size

                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            for line_num, line in enumerate(f, 1):
                                line_stripped = line.strip()

                                # Check for TODO
                                if "TODO" in line_stripped:
                                    comment = self._extract_comment(line_stripped)
                                    if comment:
                                        rel_path = file_path.relative_to(self.project_dir)
                                        todos["todo"].append(
                                            {
                                                "file": str(rel_path),
                                                "line": line_num,
                                                "text": comment,
                                            }
                                        )

                                # Check for FIXME
                                elif "FIXME" in line_stripped:
                                    comment = self._extract_comment(line_stripped)
                                    if comment:
                                        rel_path = file_path.relative_to(self.project_dir)
                                        todos["fixme"].append(
                                            {
                                                "file": str(rel_path),
                                                "line": line_num,
                                                "text": comment,
                                            }
                                        )

                                # Check for HACK
                                elif "HACK" in line_stripped:
                                    comment = self._extract_comment(line_stripped)
                                    if comment:
                                        rel_path = file_path.relative_to(self.project_dir)
                                        todos["hack"].append(
                                            {
                                                "file": str(rel_path),
                                                "line": line_num,
                                                "text": comment,
                                            }
                                        )

                    except Exception:
                        continue

            except Exception:
                continue

        # Limit results
        todos["todo"] = todos["todo"][:20]
        todos["fixme"] = todos["fixme"][:20]
        todos["hack"] = todos["hack"][:10]
        todos["total"] = len(todos["todo"]) + len(todos["fixme"]) + len(todos["hack"])

        return todos

    def _extract_comment(self, line: str) -> Optional[str]:
        """Extract comment text from a line"""
        # Try to find comment after // or #
        for marker in ["//", "#"]:
            if marker in line:
                comment = line.split(marker, 1)[1].strip()
                # Remove TODO/FIXME/HACK prefix
                for prefix in ["TODO:", "TODO", "FIXME:", "FIXME", "HACK:", "HACK"]:
                    comment = comment.replace(prefix, "").strip()
                return comment[:100]  # Limit length
        return None

    def _get_key_files(self) -> List[Dict]:
        """Get recently modified key files"""
        key_files = []

        # Find recently modified files
        try:
            import subprocess

            result = subprocess.run(
                ["git", "log", "--name-only", "--pretty=format:", "--since=7.days.ago"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                # Count file modifications
                file_counts = {}
                for line in result.stdout.split("\n"):
                    if line.strip():
                        file_counts[line.strip()] = file_counts.get(line.strip(), 0) + 1

                # Sort by modification count
                sorted_files = sorted(file_counts.items(), key=lambda x: -x[1])

                # Get top files with their last modified time
                for file_path, count in sorted_files[:10]:
                    full_path = self.project_dir / file_path
                    if full_path.exists():
                        mtime = datetime.fromtimestamp(full_path.stat().st_mtime)
                        time_ago = self._time_ago(mtime)

                        key_files.append(
                            {
                                "path": file_path,
                                "modifications": count,
                                "last_modified": time_ago,
                            }
                        )

        except Exception:
            pass

        return key_files

    def _get_quick_commands(self) -> Dict:
        """Detect quick commands from project files"""
        commands = {
            "test": None,
            "run": None,
            "build": None,
            "lint": None,
            "deploy": None,
        }

        # Check package.json
        package_json = self.project_dir / "package.json"
        if package_json.exists():
            try:
                import json

                with open(package_json) as f:
                    data = json.load(f)
                    scripts = data.get("scripts", {})

                    if "test" in scripts:
                        commands["test"] = f"npm test"
                    if "start" in scripts:
                        commands["run"] = f"npm start"
                    if "build" in scripts:
                        commands["build"] = f"npm run build"
                    if "lint" in scripts:
                        commands["lint"] = f"npm run lint"
            except Exception:
                pass

        # Check Makefile
        makefile = self.project_dir / "Makefile"
        if makefile.exists():
            try:
                with open(makefile) as f:
                    content = f.read()
                    if "test:" in content:
                        commands["test"] = "make test"
                    if "run:" in content:
                        commands["run"] = "make run"
                    if "build:" in content:
                        commands["build"] = "make build"
            except Exception:
                pass

        # Check for common Python patterns
        if (self.project_dir / "pytest.ini").exists() or (self.project_dir / "setup.py").exists():
            if not commands["test"]:
                commands["test"] = "pytest"

        # Check for Go
        if (self.project_dir / "go.mod").exists():
            commands["test"] = "go test ./..."
            commands["build"] = "go build"
            commands["run"] = "go run ."

        # Check for Rust
        if (self.project_dir / "Cargo.toml").exists():
            commands["test"] = "cargo test"
            commands["build"] = "cargo build"
            commands["run"] = "cargo run"

        return {k: v for k, v in commands.items() if v}

    def _get_code_intelligence(self) -> Dict:
        """Extract code intelligence from project"""
        intelligence = {
            "entry_points": [],
            "key_functions": [],
            "recent_changes": [],
        }

        # Detect entry points
        entry_files = ["main.py", "app.py", "index.js", "main.go", "main.rs", "server.py"]
        for entry_file in entry_files:
            entry_path = self.project_dir / entry_file
            if entry_path.exists():
                intelligence["entry_points"].append(entry_file)

        # Could add more sophisticated analysis here
        # For now, keep it simple

        return intelligence

    def _get_warnings(self) -> List[str]:
        """Generate smart warnings"""
        warnings = []

        # Check staleness
        sessions = self.memory.db.get_recent_sessions(self.project["id"], limit=1)
        if sessions:
            last_session = sessions[0]
            created_at = datetime.fromisoformat(last_session["created_at"])
            days_since = (datetime.now() - created_at).days

            if days_since > 30:
                warnings.append(f"⚠️  No activity in {days_since} days - project may be stale")
            elif days_since > 14:
                warnings.append(f"ℹ️  No activity in {days_since} days")

        # Check for uncommitted changes
        try:
            import subprocess

            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                changes = result.stdout.strip()
                if changes:
                    num_changes = len(changes.split("\n"))
                    if num_changes > 20:
                        warnings.append(
                            f"⚠️  {num_changes} uncommitted changes - consider committing"
                        )
        except Exception:
            pass

        return warnings

    def _get_suggestions(self) -> List[str]:
        """Generate smart suggestions"""
        suggestions = []

        # Check for README
        if not (self.project_dir / "README.md").exists():
            suggestions.append("📝 Consider adding a README.md file")

        # Check for tests
        test_dirs = ["tests", "test", "__tests__"]
        has_tests = any((self.project_dir / d).exists() for d in test_dirs)
        if not has_tests:
            suggestions.append("✅ Consider adding a tests directory")

        # Check for .gitignore
        if not (self.project_dir / ".gitignore").exists():
            suggestions.append("🚫 Consider adding a .gitignore file")

        return suggestions

    def _get_hot_files(self) -> List[Dict]:
        """Get most frequently modified files"""
        project_context = self.memory.get_project_context(self.project["name"])
        if not project_context or "context" not in project_context:
            return []

        context = project_context["context"]
        hot_files_str = None

        # Look for hot_files in various categories
        for category in context.values():
            if isinstance(category, dict) and "hot_files" in category:
                hot_files_str = category["hot_files"]
                break

        if not hot_files_str:
            return []

        # Parse "file.js (5 changes), file2.py (3 changes)" format
        hot_files = []
        for item in hot_files_str.split(", "):
            if "(" in item:
                file_part = item.split(" (")[0]
                count_part = item.split(" (")[1].rstrip(")")
                hot_files.append({"file": file_part, "changes": count_part})

        return hot_files

    def _get_entry_points(self) -> List[str]:
        """Get project entry points"""
        project_context = self.memory.get_project_context(self.project["name"])
        if not project_context or "context" not in project_context:
            return []

        context = project_context["context"]
        entry_points_str = None

        for category in context.values():
            if isinstance(category, dict) and "entry_points" in category:
                entry_points_str = category["entry_points"]
                break

        if not entry_points_str:
            return []

        return entry_points_str.split(", ")

    def _get_workflows(self) -> Dict[str, str]:
        """Get common workflows"""
        project_context = self.memory.get_project_context(self.project["name"])
        if not project_context or "context" not in project_context:
            return {}

        context = project_context["context"]
        workflows_str = None

        for category in context.values():
            if isinstance(category, dict) and "workflows" in category:
                workflows_str = category["workflows"]
                break

        if not workflows_str:
            return {}

        # Parse "test: pytest | build: npm run build" format
        workflows = {}
        for item in workflows_str.split(" | "):
            if ": " in item:
                key, value = item.split(": ", 1)
                workflows[key] = value

        return workflows

    def _get_external_integrations(self) -> List[str]:
        """Get external integrations"""
        project_context = self.memory.get_project_context(self.project["name"])
        if not project_context or "context" not in project_context:
            return []

        context = project_context["context"]
        integrations_str = None

        for category in context.values():
            if isinstance(category, dict) and "external_integrations" in category:
                integrations_str = category["external_integrations"]
                break

        if not integrations_str:
            return []

        return integrations_str.split(", ")

    def _get_working_tree(self) -> Dict:
        """Get working tree state"""
        project_context = self.memory.get_project_context(self.project["name"])
        if not project_context or "context" not in project_context:
            return {}

        context = project_context["context"]
        working_tree = {}

        for category in context.values():
            if isinstance(category, dict):
                if "working_tree_modified" in category:
                    working_tree["modified"] = category["working_tree_modified"].split(", ")
                if "working_tree_staged" in category:
                    working_tree["staged"] = category["working_tree_staged"]
                if "working_tree_branch" in category:
                    working_tree["branch"] = category["working_tree_branch"]

        return working_tree

    def _get_architecture_patterns(self) -> List[str]:
        """Get architecture patterns"""
        project_context = self.memory.get_project_context(self.project["name"])
        if not project_context or "context" not in project_context:
            return []

        context = project_context["context"]
        patterns_str = None

        for category in context.values():
            if isinstance(category, dict) and "architecture_patterns" in category:
                patterns_str = category["architecture_patterns"]
                break

        if not patterns_str:
            return []

        return patterns_str.split(", ")

    def _get_file_relationships(self) -> List[str]:
        """Get file relationships"""
        project_context = self.memory.get_project_context(self.project["name"])
        if not project_context or "context" not in project_context:
            return []

        context = project_context["context"]
        relationships_str = None

        for category in context.values():
            if isinstance(category, dict) and "file_relationships" in category:
                relationships_str = category["file_relationships"]
                break

        if not relationships_str:
            return []

        return relationships_str.split(" | ")

    def _get_health_metrics(self) -> List[str]:
        """Get health metrics"""
        project_context = self.memory.get_project_context(self.project["name"])
        if not project_context or "context" not in project_context:
            return []

        context = project_context["context"]
        metrics_str = None

        for category in context.values():
            if isinstance(category, dict) and "health_metrics" in category:
                metrics_str = category["health_metrics"]
                break

        if not metrics_str:
            return []

        return metrics_str.split(", ")

    def _get_known_issues_detailed(self) -> List[str]:
        """Get known issues with details"""
        project_context = self.memory.get_project_context(self.project["name"])
        if not project_context or "context" not in project_context:
            return []

        context = project_context["context"]
        issues_str = None

        for category in context.values():
            if isinstance(category, dict) and "known_issues" in category:
                issues_str = category["known_issues"]
                break

        if not issues_str:
            return []

        return issues_str.split(" | ")

    def _time_ago(self, dt: datetime) -> str:
        """Convert datetime to human-readable time ago"""
        diff = datetime.now() - dt

        if diff < timedelta(hours=1):
            minutes = int(diff.total_seconds() / 60)
            return f"{minutes}m ago"
        elif diff < timedelta(days=1):
            hours = int(diff.total_seconds() / 3600)
            return f"{hours}h ago"
        elif diff < timedelta(days=7):
            return f"{diff.days}d ago"
        elif diff < timedelta(days=30):
            weeks = diff.days // 7
            return f"{weeks}w ago"
        else:
            months = diff.days // 30
            return f"{months}mo ago"
