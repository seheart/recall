#!/usr/bin/env python3
"""
Automated version bumping for Recall
Uses semantic versioning: MAJOR.MINOR.PATCH

Usage:
    python bump_version.py patch    # Bug fixes (0.6.2 -> 0.6.3)
    python bump_version.py minor    # New features (0.6.2 -> 0.7.0)
    python bump_version.py major    # Breaking changes (0.6.2 -> 1.0.0)
"""

import sys
import re
from pathlib import Path
import subprocess


def get_current_version():
    """Read current version from VERSION file"""
    version_file = Path(__file__).parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "0.0.0"


def bump_version(bump_type="patch"):
    """
    Bump version based on type

    Args:
        bump_type: 'major', 'minor', or 'patch'

    Returns:
        New version string
    """
    current = get_current_version()
    major, minor, patch = map(int, current.split("."))

    if bump_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif bump_type == "minor":
        minor += 1
        patch = 0
    else:  # patch
        patch += 1

    new_version = f"{major}.{minor}.{patch}"
    return new_version


def update_version_files(version):
    """Update VERSION and __version__.py"""
    base_dir = Path(__file__).parent

    # Update VERSION
    (base_dir / "VERSION").write_text(f"{version}\n")

    # Update __version__.py
    version_py = base_dir / "recall_lib" / "__version__.py"
    major, minor, patch = version.split(".")
    content = f'''"""Recall version information"""
__version__ = "{version}"
__version_info__ = ({major}, {minor}, {patch})
'''
    version_py.write_text(content)

    print(f"✅ Updated VERSION to {version}")
    print(f"✅ Updated recall_lib/__version__.py to {version}")


def create_git_tag(version):
    """Create and push git tag"""
    try:
        # Create tag
        subprocess.run(["git", "tag", "-a", f"v{version}", "-m", f"Release v{version}"], check=True)
        print(f"✅ Created git tag v{version}")

        # Ask to push
        push = input("Push tag to remote? (y/n): ").strip().lower()
        if push == "y":
            subprocess.run(["git", "push", "origin", f"v{version}"], check=True)
            print(f"✅ Pushed tag v{version} to remote")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Git tag failed: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python bump_version.py [major|minor|patch]")
        print(f"Current version: {get_current_version()}")
        print("\nExamples:")
        print("  python bump_version.py patch    # Bug fixes (0.6.2 -> 0.6.3)")
        print("  python bump_version.py minor    # New features (0.6.2 -> 0.7.0)")
        print("  python bump_version.py major    # Breaking changes (0.6.2 -> 1.0.0)")
        sys.exit(1)

    bump_type = sys.argv[1].lower()
    if bump_type not in ["major", "minor", "patch"]:
        print("❌ Invalid bump type. Use: major, minor, or patch")
        sys.exit(1)

    current = get_current_version()
    new = bump_version(bump_type)

    print(f"📦 Bumping version: {current} → {new}")
    print(f"   Type: {bump_type}")

    # Confirm
    confirm = input("\nProceed? (y/n): ").strip().lower()
    if confirm != "y":
        print("❌ Cancelled")
        sys.exit(0)

    # Update files
    update_version_files(new)

    # Create git tag
    create_git_tag(new)

    print(f"\n🎉 Version bumped to {new}!")
    print(f"\n💡 Next steps:")
    print(f"   1. Update CHANGELOG.md: python generate_changelog.py {new}")
    print(f"   2. Commit changes: git add VERSION recall_lib/__version__.py CHANGELOG.md")
    print(f"   3. Push: git commit -m 'chore: Bump version to v{new}' && git push")


if __name__ == "__main__":
    main()
