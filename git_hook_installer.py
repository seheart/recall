#!/usr/bin/env python3
"""
Git Hook Installer for Recall
Automatically update recall after each git commit
"""
import os
import sys
from pathlib import Path
from typing import Dict


class GitHookInstaller:
    """Install git hooks to auto-update recall"""

    def __init__(self, project_dir: str, project_name: str):
        self.project_dir = Path(project_dir).resolve()
        self.project_name = project_name
        self.git_dir = self.project_dir / '.git'
        self.hooks_dir = self.git_dir / 'hooks'

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
        - Run silently in background
        """
        if not self.is_git_repo():
            print(f"❌ Not a git repository: {self.project_dir}")
            return False

        recall_path = self.get_recall_path()
        if not recall_path:
            print("❌ Could not find recall.py")
            print("💡 Make sure recall is installed at ~/Projects/recall/")
            return False

        # Create hooks directory if it doesn't exist
        self.hooks_dir.mkdir(parents=True, exist_ok=True)

        hook_file = self.hooks_dir / 'post-commit'

        # Hook script content
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
                print(f"⚠️ Post-commit hook already exists")
                choice = input("Replace existing hook? (y/n): ").strip().lower()
                if choice != 'y':
                    print("❌ Installation cancelled")
                    return False

            # Write hook file
            hook_file.write_text(hook_content)

            # Make executable
            hook_file.chmod(0o755)

            print(f"✅ Installed post-commit hook at {hook_file}")
            print(f"📝 Recall will now auto-update after each commit to {self.project_name}")
            print("\n💡 The hook runs silently in the background")
            print("💡 To disable, delete: .git/hooks/post-commit")

            return True

        except Exception as e:
            print(f"❌ Failed to install hook: {e}")
            return False

    def uninstall_post_commit_hook(self) -> bool:
        """Uninstall the post-commit hook"""
        hook_file = self.hooks_dir / 'post-commit'

        if not hook_file.exists():
            print("❌ No post-commit hook found")
            return False

        try:
            hook_file.unlink()
            print("✅ Uninstalled post-commit hook")
            return True
        except Exception as e:
            print(f"❌ Failed to uninstall hook: {e}")
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


def install_hook_for_project(project_name: str, project_dir: str = None) -> bool:
    """
    Install git hook for a recall project

    Args:
        project_name: Name of recall project
        project_dir: Project directory (defaults to current directory)

    Returns:
        True if installation succeeded
    """
    if project_dir is None:
        project_dir = os.getcwd()

    installer = GitHookInstaller(project_dir, project_name)

    print(f"🔧 Installing auto-update hook for '{project_name}'")
    print(f"📁 Project directory: {project_dir}")
    print()

    # Check prerequisites
    if not installer.is_git_repo():
        print("❌ Directory is not a git repository")
        return False

    recall_path = installer.get_recall_path()
    if not recall_path:
        print("❌ Could not find recall.py")
        return False

    # Install hook
    return installer.install_post_commit_hook()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python git_hook_installer.py <project-name> [project-dir]")
        print("\nExample:")
        print("  python git_hook_installer.py my-api")
        print("  python git_hook_installer.py ant312 /home/seth/Projects/ant312")
        sys.exit(1)

    project_name = sys.argv[1]
    project_dir = sys.argv[2] if len(sys.argv) > 2 else None

    success = install_hook_for_project(project_name, project_dir)
    sys.exit(0 if success else 1)
