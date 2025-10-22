#!/usr/bin/env python3
"""
Generate CHANGELOG from git commits

Usage:
    python generate_changelog.py 0.7.0
"""

import subprocess
from datetime import datetime
from pathlib import Path
import sys

def get_commits_since_tag(tag):
    """Get commits since last tag"""
    try:
        if tag:
            result = subprocess.run(
                ['git', 'log', f'{tag}..HEAD', '--pretty=format:%h|%s|%an|%ad', '--date=short'],
                capture_output=True,
                text=True,
                check=True
            )
        else:
            # No previous tag, get all commits
            result = subprocess.run(
                ['git', 'log', '--pretty=format:%h|%s|%an|%ad', '--date=short'],
                capture_output=True,
                text=True,
                check=True
            )

        commits = []
        for line in result.stdout.split('\n'):
            if line:
                parts = line.split('|')
                if len(parts) == 4:
                    hash, msg, author, date = parts
                    commits.append({'hash': hash, 'message': msg, 'author': author, 'date': date})
        return commits
    except Exception as e:
        print(f"⚠️  Failed to get commits: {e}")
        return []

def categorize_commit(message):
    """Categorize commit by message"""
    msg_lower = message.lower()

    # Features
    if any(word in msg_lower for word in ['feat:', 'add:', 'implement', 'new feature', 'enhance']):
        return 'features'

    # Fixes
    if any(word in msg_lower for word in ['fix:', 'bug:', 'bugfix', 'hotfix', 'patch', 'resolve']):
        return 'fixes'

    # Documentation
    if any(word in msg_lower for word in ['docs:', 'documentation', 'readme']):
        return 'documentation'

    # Refactoring
    if any(word in msg_lower for word in ['refactor:', 'clean', 'improve', 'optimize']):
        return 'refactoring'

    # Testing
    if any(word in msg_lower for word in ['test:', 'tests']):
        return 'testing'

    # Chores/Maintenance
    if any(word in msg_lower for word in ['chore:', 'update', 'bump', 'deps']):
        return 'chores'

    return 'other'

def generate_changelog(version):
    """Generate changelog entry for new version"""
    # Get last tag
    try:
        result = subprocess.run(['git', 'describe', '--tags', '--abbrev=0'],
                              capture_output=True, text=True)
        last_tag = result.stdout.strip() if result.returncode == 0 else None
    except:
        last_tag = None

    print(f"📊 Analyzing commits since {last_tag if last_tag else 'beginning'}...")

    # Get commits
    commits = get_commits_since_tag(last_tag)

    if not commits:
        print("⚠️  No commits since last tag")
        return

    print(f"📝 Found {len(commits)} commit(s)")

    # Categorize commits
    categories = {
        'features': [],
        'fixes': [],
        'documentation': [],
        'refactoring': [],
        'testing': [],
        'chores': [],
        'other': []
    }

    for commit in commits:
        cat = categorize_commit(commit['message'])
        categories[cat].append(commit)

    # Generate changelog entry
    today = datetime.now().strftime('%Y-%m-%d')
    entry = f"\n## [v{version}] - {today}\n\n"

    # Add summary
    total_changes = len(commits)
    entry += f"**{total_changes} changes** in this release\n\n"

    if categories['features']:
        entry += "### ✨ Added\n"
        for c in categories['features']:
            entry += f"- {c['message']} ([{c['hash']}](../../commit/{c['hash']}))\n"
        entry += "\n"

    if categories['fixes']:
        entry += "### 🐛 Fixed\n"
        for c in categories['fixes']:
            entry += f"- {c['message']} ([{c['hash']}](../../commit/{c['hash']}))\n"
        entry += "\n"

    if categories['refactoring']:
        entry += "### 🔨 Changed\n"
        for c in categories['refactoring']:
            entry += f"- {c['message']} ([{c['hash']}](../../commit/{c['hash']}))\n"
        entry += "\n"

    if categories['documentation']:
        entry += "### 📚 Documentation\n"
        for c in categories['documentation']:
            entry += f"- {c['message']} ([{c['hash']}](../../commit/{c['hash']}))\n"
        entry += "\n"

    if categories['testing']:
        entry += "### 🧪 Testing\n"
        for c in categories['testing']:
            entry += f"- {c['message']} ([{c['hash']}](../../commit/{c['hash']}))\n"
        entry += "\n"

    # Read existing CHANGELOG
    changelog_file = Path(__file__).parent / "CHANGELOG.md"
    if changelog_file.exists():
        existing = changelog_file.read_text()
    else:
        existing = """# Changelog

All notable changes to Recall will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

"""

    # Insert new entry after header
    lines = existing.split('\n')
    header_end = 0
    for i, line in enumerate(lines):
        if line.startswith('## '):
            header_end = i
            break

    if header_end == 0:
        # No existing entries, add after header
        # Find end of header (first blank line after title)
        for i, line in enumerate(lines):
            if i > 0 and not line.strip():
                header_end = i + 1
                break
        if header_end == 0:
            header_end = len(lines)

    new_content = lines[:header_end] + [entry] + lines[header_end:]

    changelog_file.write_text('\n'.join(new_content))
    print(f"✅ Updated CHANGELOG.md with {len(commits)} commit(s)")
    print(f"📊 Breakdown:")
    for category, items in categories.items():
        if items:
            print(f"   • {category.title()}: {len(items)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_changelog.py <version>")
        print("\nExample:")
        print("  python generate_changelog.py 0.7.0")
        sys.exit(1)

    version = sys.argv[1].replace('v', '')  # Remove 'v' prefix if present
    generate_changelog(version)
