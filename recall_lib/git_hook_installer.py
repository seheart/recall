#!/usr/bin/env python3
"""
Git Hook Installer for Recall
Automatically update recall after each git commit
"""
import os
import sys
from pathlib import Path
from typing import Dict

from .logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class GitHookInstaller:
    """Install git hooks to auto-update recall"""

    def __init__(self, project_dir: str, project_name: str, smart: bool = False, quiet: bool = False):
        self.project_dir = Path(project_dir).resolve()
        self.project_name = project_name
        self.git_dir = self.project_dir / '.git'
        self.hooks_dir = self.git_dir / 'hooks'
        self.smart = smart
        self.quiet = quiet

    def is_git_repo(self) -> bool:
        """Check if directory is a git repository"""
        return self.git_dir.exists() and self.git_dir.is_dir()

    def get_recall_path(self) -> str:
        """Get path to recall.py"""
        # Assume recall.py is in ~/Projects/recall/
        recall_path = Path.home() / 'Projects' / 'recall' / 'recall.py'
        if recall_path.exists():
            return str(recall_path)
        return None

    def install_post_commit_hook(self) -> bool:
        """
        Install post-commit hook to auto-update recall

        The hook will:
        - Run after each git commit
        - Update recall with latest commit info
        - If smart mode: also run analyze to detect tech changes
        - Run silently in background
        """
        if not self.is_git_repo():
            logger.error(f"❌ Not a git repository: {self.project_dir}")
            return False

        recall_path = self.get_recall_path()
        if not recall_path:
            logger.error("❌ Could not find recall.py")
            logger.info("💡 Make sure recall is installed at ~/Projects/recall/")
            return False

        # Create hooks directory if it doesn't exist
        self.hooks_dir.mkdir(parents=True, exist_ok=True)

        hook_file = self.hooks_dir / 'post-commit'

        # Output redirection based on quiet flag
        output_redirect = "> /dev/null 2>&1" if self.quiet else ""

        # Build hook content based on mode
        if self.smart:
            # Smart hook: log commits AND analyze for tech changes
            hook_content = f"""#!/bin/sh
# Recall Smart Auto-Update Hook
# Automatically updates recall after each commit with intelligent analysis

echo "🔄 Updating recall memory..."

# 1. Log the commit as a session
{recall_path} {self.project_name} --git-log --days 1 {output_redirect}

# 2. Smart analyze: detect tech changes, auto-tag, update context
{recall_path} {self.project_name} --analyze {output_redirect}

echo "✅ Recall updated: commit logged + tech stack analyzed"

# Exit successfully (don't block commit)
exit 0
"""
        else:
            # Standard hook: just log commits
            hook_content = f"""#!/bin/sh
# Recall auto-update hook
# Automatically update recall after each commit

# Run recall git-log in background to update project memory
{recall_path} {self.project_name} --git-log --days 1 > /dev/null 2>&1 &

# Exit successfully (don't block commit)
exit 0
"""

        try:
            # Check if hook already exists
            if hook_file.exists():
                logger.warning(f"⚠️ Post-commit hook already exists")
                choice = input("Replace existing hook? (y/n): ").strip().lower()
                if choice != 'y':
                    logger.error("❌ Installation cancelled")
                    return False

            # Write hook file
            hook_file.write_text(hook_content)

            # Make executable
            hook_file.chmod(0o755)

            hook_type = "Smart" if self.smart else "Standard"
            logger.info(f"✅ Installed {hook_type} post-commit hook at {hook_file}")
            logger.info(f"📝 Recall will now auto-update after each commit to {self.project_name}")

            if self.smart:
                logger.info("\n🧠 Smart Mode Enabled:")
                logger.info("  • Logs each commit as a session")
                logger.info("  • Auto-analyzes project for tech changes")
                logger.info("  • Auto-tags new frameworks/languages")
                logger.info("  • Updates context with latest info")
                logger.info("  ⏱️  Adds ~2-3 seconds per commit")
            else:
                logger.info("\n💡 Standard Mode:")
                logger.info("  • Logs commits as sessions only")
                logger.info("  • Runs silently in background")

            logger.info("\n💡 To disable, delete: .git/hooks/post-commit")

            return True

        except Exception as e:
            logger.error(f"❌ Failed to install hook: {e}")
            return False

    def uninstall_post_commit_hook(self) -> bool:
        """Uninstall the post-commit hook"""
        hook_file = self.hooks_dir / 'post-commit'

        if not hook_file.exists():
            logger.error("❌ No post-commit hook found")
            return False

        try:
            hook_file.unlink()
            logger.info("✅ Uninstalled post-commit hook")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to uninstall hook: {e}")
            return False

    def check_hook_status(self) -> Dict:
        """Check if hook is installed and working"""
        hook_file = self.hooks_dir / 'post-commit'

        status = {
            'git_repo': self.is_git_repo(),
            'hook_exists': hook_file.exists(),
            'hook_executable': hook_file.exists() and os.access(hook_file, os.X_OK),
            'recall_found': self.get_recall_path() is not None
        }

        return status


def install_hook_for_project(project_name: str, project_dir: str = None, smart: bool = False, quiet: bool = False) -> bool:
    """
    Install git hook for a recall project

    Args:
        project_name: Name of recall project
        project_dir: Project directory (defaults to current directory)
        smart: Enable smart mode (auto-analyze on each commit)
        quiet: Suppress hook output

    Returns:
        True if installation succeeded
    """
    if project_dir is None:
        project_dir = os.getcwd()

    installer = GitHookInstaller(project_dir, project_name, smart=smart, quiet=quiet)

    hook_type = "Smart" if smart else "Standard"
    logger.info(f"🔧 Installing {hook_type} auto-update hook for '{project_name}'")
    logger.info(f"📁 Project directory: {project_dir}")
    logger.info("")

    # Check prerequisites
    if not installer.is_git_repo():
        logger.error("❌ Directory is not a git repository")
        return False

    recall_path = installer.get_recall_path()
    if not recall_path:
        logger.error("❌ Could not find recall.py")
        return False

    # Install hook
    return installer.install_post_commit_hook()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.info("Usage: python git_hook_installer.py <project-name> [project-dir]")
        logger.info("\nExample:")
        logger.info("  python git_hook_installer.py my-api")
        logger.info("  python git_hook_installer.py ant312 /home/seth/Projects/ant312")
        sys.exit(1)

    project_name = sys.argv[1]
    project_dir = sys.argv[2] if len(sys.argv) > 2 else None

    success = install_hook_for_project(project_name, project_dir)
    sys.exit(0 if success else 1)
