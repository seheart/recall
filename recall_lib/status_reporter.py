#!/usr/bin/env python3
"""
Status Reporter - Comprehensive development readiness report
"""
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple
from .project_memory import ProjectMemory
from .access_verifier import AccessVerifier

from .logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class StatusReporter:
    """Generates comprehensive status reports for project development readiness"""

    def __init__(self, project_name: str, memory: ProjectMemory):
        self.project_name = project_name
        self.memory = memory
        self.project = memory.db.get_project(project_name)
        self.context = memory.get_project_context(project_name)
        self.checks = []
        self.warnings = []
        self.info = []

    def generate_report(self) -> str:
        """Generate comprehensive status report"""
        self.check_project_exists()
        self.check_directory()
        self.check_git_status()
        self.check_dependencies()
        self.check_environment()
        self.check_dev_tools()
        self.check_tests()
        self.check_known_issues()
        self.check_documentation()

        return self.format_report()

    def check_project_exists(self):
        """Verify project exists in recall"""
        if self.project:
            self.checks.append(('✅', 'Project exists in recall database'))
        else:
            self.checks.append(('❌', f"Project '{self.project_name}' not found"))

    def check_directory(self):
        """Verify project directory exists and is accessible"""
        if not self.project:
            return

        project_dir = self.project.get('directory')
        if not project_dir:
            self.warnings.append('⚠️  No directory configured for project')
            return

        if os.path.exists(project_dir):
            if os.access(project_dir, os.R_OK | os.W_OK):
                self.checks.append(('✅', f'Directory accessible: {project_dir}'))
            else:
                self.checks.append(('❌', f'Directory not writable: {project_dir}'))
        else:
            self.checks.append(('❌', f'Directory does not exist: {project_dir}'))

    def check_git_status(self):
        """Check git repository status"""
        if not self.project:
            return

        project_dir = self.project.get('directory')
        if not project_dir or not os.path.exists(project_dir):
            return

        git_dir = Path(project_dir) / '.git'
        if not git_dir.exists():
            self.info.append('ℹ️  Not a git repository')
            return

        try:
            # Check for uncommitted changes
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                uncommitted = result.stdout.strip().split('\n') if result.stdout.strip() else []
                if len(uncommitted) == 0:
                    self.checks.append(('✅', 'Git repository clean (no uncommitted changes)'))
                else:
                    self.warnings.append(f'⚠️  {len(uncommitted)} uncommitted changes in git')

            # Check current branch
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
                self.info.append(f'ℹ️  Current branch: {branch}')

        except Exception as e:
            self.warnings.append(f'⚠️  Git status check failed: {e}')

    def check_dependencies(self):
        """Check if dependencies are installed"""
        if not self.project:
            return

        project_dir = self.project.get('directory')
        if not project_dir or not os.path.exists(project_dir):
            return

        # Node.js projects
        if (Path(project_dir) / 'package.json').exists():
            if (Path(project_dir) / 'node_modules').exists():
                self.checks.append(('✅', 'Node.js dependencies installed (node_modules/ exists)'))
            else:
                self.checks.append(('❌', 'Node.js dependencies NOT installed - run: npm install'))

        # Python projects
        if (Path(project_dir) / 'requirements.txt').exists():
            # Check if virtualenv exists
            venv_dirs = ['.venv', 'venv', 'env']
            venv_found = False
            for vdir in venv_dirs:
                if (Path(project_dir) / vdir).exists():
                    self.checks.append(('✅', f'Python virtual environment found: {vdir}/'))
                    venv_found = True
                    break
            if not venv_found:
                self.warnings.append('⚠️  No Python virtual environment found - consider creating one')

    def check_environment(self):
        """Check environment configuration"""
        if not self.project:
            return

        project_dir = self.project.get('directory')
        if not project_dir or not os.path.exists(project_dir):
            return

        # Check for .env file
        if (Path(project_dir) / '.env').exists():
            self.checks.append(('✅', '.env file exists'))
        elif (Path(project_dir) / '.env.example').exists():
            self.warnings.append('⚠️  .env.example exists but no .env file - copy and configure')

        # Check environment context in recall
        ctx = self.context.get('context', {}) if self.context else {}
        if 'environment' in ctx or 'environment_config' in ctx:
            self.info.append('ℹ️  Environment configuration documented in recall')

    def check_dev_tools(self):
        """Verify development tools are available"""
        verifier = AccessVerifier()
        results = verifier.verify_all()

        if results.get('local'):
            self.checks.append(('✅', 'Local system access confirmed'))
        else:
            self.checks.append(('❌', 'Local system access issues'))

        if results.get('github'):
            self.checks.append(('✅', 'GitHub access configured'))
        else:
            self.warnings.append('⚠️  GitHub access not configured')

        if results.get('server'):
            self.checks.append(('✅', 'SSH server access configured'))
        else:
            self.info.append('ℹ️  No SSH server access configured')

        if results.get('tools'):
            self.checks.append(('✅', 'Development tools available'))

    def check_tests(self):
        """Check testing setup"""
        if not self.context:
            return

        ctx = self.context.get('context', {})

        # Check for testing context
        if 'testing' in ctx:
            self.checks.append(('✅', f'Tests configured: {ctx["testing"]}'))
        else:
            self.info.append('ℹ️  No test configuration detected')

    def check_known_issues(self):
        """Report known issues and blockers"""
        if not self.context:
            return

        ctx = self.context.get('context', {})

        # Check for issues in context
        if 'issues' in ctx:
            issue_count = len(ctx['issues'])
            self.warnings.append(f'⚠️  {issue_count} known issue(s) documented')

        if 'blockers' in ctx:
            blocker_count = len(ctx['blockers'])
            self.checks.append(('❌', f'{blocker_count} blocker(s) preventing development'))

    def check_documentation(self):
        """Check for documentation"""
        if not self.project:
            return

        project_dir = self.project.get('directory')
        if not project_dir or not os.path.exists(project_dir):
            return

        # Check for README
        if (Path(project_dir) / 'README.md').exists():
            self.checks.append(('✅', 'README.md exists'))

        # Check for docs directory
        if (Path(project_dir) / 'docs').exists():
            self.info.append('ℹ️  docs/ directory found')

        # Check for documentation links in context
        ctx = self.context.get('context', {}) if self.context else {}
        if 'documentation' in ctx:
            self.info.append('ℹ️  External documentation links in recall')

    def format_report(self) -> str:
        """Format the status report"""
        lines = []
        lines.append("=" * 70)
        lines.append(f"🔍 DEVELOPMENT READINESS REPORT: {self.project_name.upper()}")
        lines.append("=" * 70)

        if self.checks:
            lines.append("\n📋 SYSTEM CHECKS:")
            for icon, msg in self.checks:
                lines.append(f"  {icon} {msg}")

        if self.warnings:
            lines.append("\n⚠️  WARNINGS:")
            for msg in self.warnings:
                lines.append(f"  {msg}")

        if self.info:
            lines.append("\n💡 INFORMATION:")
            for msg in self.info:
                lines.append(f"  {msg}")

        # Overall status
        lines.append("\n" + "=" * 70)

        errors = [c for c in self.checks if c[0] == '❌']
        warnings = len(self.warnings)

        if errors:
            lines.append(f"❌ NOT READY - {len(errors)} critical issue(s) must be resolved")
        elif warnings > 0:
            lines.append(f"⚠️  READY WITH WARNINGS - {warnings} warning(s) to address")
        else:
            lines.append("✅ ALL SYSTEMS GO - Ready for development!")

        lines.append("=" * 70)

        return "\n".join(lines)


def generate_status_report(project_name: str) -> str:
    """Generate and return status report for a project"""
    memory = ProjectMemory()
    reporter = StatusReporter(project_name, memory)
    return reporter.generate_report()


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        logger.info("Usage: status_reporter.py <project-name>")
        sys.exit(1)

    report = generate_status_report(sys.argv[1])
    print(report)
