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
        self.project_dir = Path(project_dir)
        self.project = project
        self.memory = memory
        self.context = {}

    def enrich_all(self) -> Dict:
        """
        Gather all enriched context

        Returns:
            Dict with enriched context sections
        """
        enriched = {
            'current_state': self._get_current_state(),
            'recent_activity': self._get_recent_activity(),
            'current_focus': self._get_current_focus(),
            'todos_and_issues': self._get_todos_and_issues(),
            'key_files': self._get_key_files(),
            'quick_commands': self._get_quick_commands(),
            'code_intelligence': self._get_code_intelligence(),
            'warnings': self._get_warnings(),
            'suggestions': self._get_suggestions(),
        }

        return enriched

    def _get_current_state(self) -> Dict:
        """Get current project state with health indicators"""
        state = {
            'status': 'Unknown',
            'last_active': None,
            'health': 'unknown',
            'health_emoji': '⚪',
        }

        # Get last session
        sessions = self.memory.db.get_recent_sessions(self.project['id'], limit=1)
        if sessions:
            last_session = sessions[0]
            created_at = datetime.fromisoformat(last_session['created_at'])
            time_diff = datetime.now() - created_at

            if time_diff < timedelta(hours=24):
                state['last_active'] = 'Today'
            elif time_diff < timedelta(days=2):
                state['last_active'] = 'Yesterday'
            elif time_diff < timedelta(days=7):
                state['last_active'] = f'{time_diff.days} days ago'
            else:
                state['last_active'] = f'{time_diff.days // 7} weeks ago'

        # Check git status for health
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                changes = result.stdout.strip()
                if not changes:
                    state['health'] = 'clean'
                    state['health_emoji'] = '🟢'
                elif len(changes.split('\n')) < 10:
                    state['health'] = 'active'
                    state['health_emoji'] = '🟡'
                else:
                    state['health'] = 'many_changes'
                    state['health_emoji'] = '🟠'
        except Exception:
            pass

        # Get status from context
        project_context = self.memory.get_project_context(self.project['name'])
        if project_context and 'context' in project_context:
            context = project_context['context']
            if 'state' in context and 'status' in context['state']:
                state['status'] = context['state']['status']

        return state

    def _get_recent_activity(self) -> Dict:
        """Get recent activity summary"""
        activity = {
            'commits': [],
            'sessions': 0,
            'key_changes': [],
            'time_range': '7 days',
        }

        # Get recent commits
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'log', '--oneline', '--since=7.days.ago'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                commit_lines = [line for line in result.stdout.split('\n') if line.strip()]
                activity['commits'] = commit_lines[:10]  # Last 10
        except Exception:
            pass

        # Get recent sessions
        sessions = self.memory.db.get_recent_sessions(self.project['id'], limit=10)
        activity['sessions'] = len(sessions)

        # Extract key changes from session accomplishments
        for session in sessions[:3]:
            accomplishments = session.get('accomplishments')
            if accomplishments:
                if isinstance(accomplishments, str):
                    activity['key_changes'].append(accomplishments[:100])
                elif isinstance(accomplishments, list):
                    for acc in accomplishments[:2]:
                        activity['key_changes'].append(str(acc)[:100])

        return activity

    def _get_current_focus(self) -> Dict:
        """Get what the project is currently focused on"""
        focus = {
            'working_on': None,
            'blockers': [],
            'next_steps': [],
            'open_questions': [],
        }

        # Get latest session
        sessions = self.memory.db.get_recent_sessions(self.project['id'], limit=1)
        if sessions:
            latest = sessions[0]

            # Working on
            summary = latest.get('summary', '')
            if summary:
                focus['working_on'] = summary

            # Next steps from context
            project_context = self.memory.get_project_context(self.project['name'])
            if project_context and 'context' in project_context:
                context = project_context['context']
            else:
                context = {}

            if 'state' in context:
                if 'next_steps' in context['state']:
                    ns = context['state']['next_steps']
                    if isinstance(ns, str):
                        focus['next_steps'] = [ns]
                    elif isinstance(ns, list):
                        focus['next_steps'] = ns

                if 'blockers' in context['state']:
                    b = context['state']['blockers']
                    if isinstance(b, str):
                        focus['blockers'] = [b]
                    elif isinstance(b, list):
                        focus['blockers'] = b

        return focus

    def _get_todos_and_issues(self) -> Dict:
        """Scan codebase for TODO/FIXME/HACK comments"""
        todos = {
            'todo': [],
            'fixme': [],
            'hack': [],
            'total': 0,
        }

        # Extensions to scan
        code_extensions = {'.py', '.js', '.jsx', '.ts', '.tsx', '.go', '.rs', '.java', '.c', '.cpp', '.rb'}

        # Scan files
        for ext in code_extensions:
            try:
                for file_path in self.project_dir.rglob(f'*{ext}'):
                    # Skip common directories
                    if any(part in file_path.parts for part in ['node_modules', '.git', '__pycache__', 'venv', '.venv', 'target', 'build', 'dist']):
                        continue

                    if file_path.stat().st_size > 500_000:  # Skip files > 500KB
                        continue

                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            for line_num, line in enumerate(f, 1):
                                line_stripped = line.strip()

                                # Check for TODO
                                if 'TODO' in line_stripped:
                                    comment = self._extract_comment(line_stripped)
                                    if comment:
                                        rel_path = file_path.relative_to(self.project_dir)
                                        todos['todo'].append({
                                            'file': str(rel_path),
                                            'line': line_num,
                                            'text': comment
                                        })

                                # Check for FIXME
                                elif 'FIXME' in line_stripped:
                                    comment = self._extract_comment(line_stripped)
                                    if comment:
                                        rel_path = file_path.relative_to(self.project_dir)
                                        todos['fixme'].append({
                                            'file': str(rel_path),
                                            'line': line_num,
                                            'text': comment
                                        })

                                # Check for HACK
                                elif 'HACK' in line_stripped:
                                    comment = self._extract_comment(line_stripped)
                                    if comment:
                                        rel_path = file_path.relative_to(self.project_dir)
                                        todos['hack'].append({
                                            'file': str(rel_path),
                                            'line': line_num,
                                            'text': comment
                                        })

                    except Exception:
                        continue

            except Exception:
                continue

        # Limit results
        todos['todo'] = todos['todo'][:20]
        todos['fixme'] = todos['fixme'][:20]
        todos['hack'] = todos['hack'][:10]
        todos['total'] = len(todos['todo']) + len(todos['fixme']) + len(todos['hack'])

        return todos

    def _extract_comment(self, line: str) -> Optional[str]:
        """Extract comment text from a line"""
        # Try to find comment after // or #
        for marker in ['//', '#']:
            if marker in line:
                comment = line.split(marker, 1)[1].strip()
                # Remove TODO/FIXME/HACK prefix
                for prefix in ['TODO:', 'TODO', 'FIXME:', 'FIXME', 'HACK:', 'HACK']:
                    comment = comment.replace(prefix, '').strip()
                return comment[:100]  # Limit length
        return None

    def _get_key_files(self) -> List[Dict]:
        """Get recently modified key files"""
        key_files = []

        # Find recently modified files
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'log', '--name-only', '--pretty=format:', '--since=7.days.ago'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Count file modifications
                file_counts = {}
                for line in result.stdout.split('\n'):
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

                        key_files.append({
                            'path': file_path,
                            'modifications': count,
                            'last_modified': time_ago,
                        })

        except Exception:
            pass

        return key_files

    def _get_quick_commands(self) -> Dict:
        """Detect quick commands from project files"""
        commands = {
            'test': None,
            'run': None,
            'build': None,
            'lint': None,
            'deploy': None,
        }

        # Check package.json
        package_json = self.project_dir / 'package.json'
        if package_json.exists():
            try:
                import json
                with open(package_json) as f:
                    data = json.load(f)
                    scripts = data.get('scripts', {})

                    if 'test' in scripts:
                        commands['test'] = f"npm test"
                    if 'start' in scripts:
                        commands['run'] = f"npm start"
                    if 'build' in scripts:
                        commands['build'] = f"npm run build"
                    if 'lint' in scripts:
                        commands['lint'] = f"npm run lint"
            except Exception:
                pass

        # Check Makefile
        makefile = self.project_dir / 'Makefile'
        if makefile.exists():
            try:
                with open(makefile) as f:
                    content = f.read()
                    if 'test:' in content:
                        commands['test'] = 'make test'
                    if 'run:' in content:
                        commands['run'] = 'make run'
                    if 'build:' in content:
                        commands['build'] = 'make build'
            except Exception:
                pass

        # Check for common Python patterns
        if (self.project_dir / 'pytest.ini').exists() or (self.project_dir / 'setup.py').exists():
            if not commands['test']:
                commands['test'] = 'pytest'

        # Check for Go
        if (self.project_dir / 'go.mod').exists():
            commands['test'] = 'go test ./...'
            commands['build'] = 'go build'
            commands['run'] = 'go run .'

        # Check for Rust
        if (self.project_dir / 'Cargo.toml').exists():
            commands['test'] = 'cargo test'
            commands['build'] = 'cargo build'
            commands['run'] = 'cargo run'

        return {k: v for k, v in commands.items() if v}

    def _get_code_intelligence(self) -> Dict:
        """Extract code intelligence from project"""
        intelligence = {
            'entry_points': [],
            'key_functions': [],
            'recent_changes': [],
        }

        # Detect entry points
        entry_files = ['main.py', 'app.py', 'index.js', 'main.go', 'main.rs', 'server.py']
        for entry_file in entry_files:
            entry_path = self.project_dir / entry_file
            if entry_path.exists():
                intelligence['entry_points'].append(entry_file)

        # Could add more sophisticated analysis here
        # For now, keep it simple

        return intelligence

    def _get_warnings(self) -> List[str]:
        """Generate smart warnings"""
        warnings = []

        # Check staleness
        sessions = self.memory.db.get_recent_sessions(self.project['id'], limit=1)
        if sessions:
            last_session = sessions[0]
            created_at = datetime.fromisoformat(last_session['created_at'])
            days_since = (datetime.now() - created_at).days

            if days_since > 30:
                warnings.append(f"⚠️  No activity in {days_since} days - project may be stale")
            elif days_since > 14:
                warnings.append(f"ℹ️  No activity in {days_since} days")

        # Check for uncommitted changes
        try:
            import subprocess
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                changes = result.stdout.strip()
                if changes:
                    num_changes = len(changes.split('\n'))
                    if num_changes > 20:
                        warnings.append(f"⚠️  {num_changes} uncommitted changes - consider committing")
        except Exception:
            pass

        return warnings

    def _get_suggestions(self) -> List[str]:
        """Generate smart suggestions"""
        suggestions = []

        # Check for README
        if not (self.project_dir / 'README.md').exists():
            suggestions.append("📝 Consider adding a README.md file")

        # Check for tests
        test_dirs = ['tests', 'test', '__tests__']
        has_tests = any((self.project_dir / d).exists() for d in test_dirs)
        if not has_tests:
            suggestions.append("✅ Consider adding a tests directory")

        # Check for .gitignore
        if not (self.project_dir / '.gitignore').exists():
            suggestions.append("🚫 Consider adding a .gitignore file")

        return suggestions

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
