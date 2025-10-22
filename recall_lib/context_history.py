#!/usr/bin/env python3
"""
Context History Management - View, diff, and rollback project context changes
"""
from typing import Dict, List, Tuple
from .project_memory import ProjectMemory
from .logger import get_logger

logger = get_logger(__name__)


def show_history(project_name: str, limit: int = 20) -> bool:
    """
    Display context change history for a project

    Args:
        project_name: Name of the project
        limit: Maximum number of history entries to show

    Returns:
        True if successful, False otherwise
    """
    memory = ProjectMemory()
    project = memory.db.get_project(project_name)

    if not project:
        from .fuzzy_match import suggest_project
        logger.error(f"❌ Project '{project_name}' not found")
        suggestion = suggest_project(project_name, memory)
        if suggestion:
            logger.info(suggestion)
        return False

    project_id = project['id']
    history = memory.db.get_context_history(project_id, limit)

    if not history:
        logger.info(f"📜 No history available for '{project_name}'")
        logger.info("💡 Context changes will be tracked going forward")
        return True

    current_version = memory.db.get_current_version(project_id)

    logger.info(f"📜 Context History for '{project_name}' (Current: v{current_version})\n")
    logger.info(f"{'Version':<10} {'Date':<20} {'Action':<10} {'Category':<15} {'Key'}")
    logger.info("-" * 80)

    for entry in history:
        version = f"v{entry['version']}"
        date = entry['created_at'][:19]  # Trim milliseconds
        operation = entry['operation']
        category = entry['category']
        key = entry['key']

        # Color code operations
        if operation == 'create':
            op_display = "🆕 create"
        elif operation == 'update':
            op_display = "✏️  update"
        elif operation == 'delete':
            op_display = "🗑️  delete"
        elif operation == 'rollback':
            op_display = "⏪ rollback"
        else:
            op_display = operation

        logger.info(f"{version:<10} {date:<20} {op_display:<10} {category:<15} {key}")

        # Show value changes for updates
        if operation == 'update' and entry['old_value'] and entry['value']:
            old = entry['old_value'][:50] + ('...' if len(entry['old_value']) > 50 else '')
            new = entry['value'][:50] + ('...' if len(entry['value']) > 50 else '')
            logger.info(f"           └─ Changed: '{old}' → '{new}'")

    logger.info(f"\n💡 View diff: recall {project_name} --diff")
    logger.info(f"💡 Rollback: recall {project_name} --rollback <version>")
    return True


def diff_versions(project_name: str, version1: int = None, version2: int = None) -> bool:
    """
    Show differences between two versions of project context

    Args:
        project_name: Name of the project
        version1: First version (default: current - 1)
        version2: Second version (default: current)

    Returns:
        True if successful, False otherwise
    """
    memory = ProjectMemory()
    project = memory.db.get_project(project_name)

    if not project:
        from .fuzzy_match import suggest_project
        logger.error(f"❌ Project '{project_name}' not found")
        suggestion = suggest_project(project_name, memory)
        if suggestion:
            logger.info(suggestion)
        return False

    project_id = project['id']
    current_version = memory.db.get_current_version(project_id)

    # Default to comparing current with previous
    if version2 is None:
        version2 = current_version
    if version1 is None:
        version1 = max(1, version2 - 1)

    if version1 > current_version or version2 > current_version:
        logger.error(f"❌ Version out of range. Current version is {current_version}")
        return False

    # Get context at both versions
    context1 = memory.db.get_context_at_version(project_id, version1)
    context2 = memory.db.get_context_at_version(project_id, version2)

    # Compute diff
    added, removed, modified = _compute_diff(context1, context2)

    logger.info(f"📊 Context Diff for '{project_name}': v{version1} → v{version2}\n")

    if not added and not removed and not modified:
        logger.info("✅ No changes between these versions")
        return True

    # Show additions
    if added:
        logger.info(f"🆕 Added ({len(added)}):")
        for category, key, value in added:
            logger.info(f"  + {category}/{key}: {value[:60]}{'...' if len(value) > 60 else ''}")
        logger.info("")

    # Show removals
    if removed:
        logger.info(f"🗑️  Removed ({len(removed)}):")
        for category, key, value in removed:
            logger.info(f"  - {category}/{key}: {value[:60]}{'...' if len(value) > 60 else ''}")
        logger.info("")

    # Show modifications
    if modified:
        logger.info(f"✏️  Modified ({len(modified)}):")
        for category, key, old_value, new_value in modified:
            logger.info(f"  ~ {category}/{key}:")
            logger.info(f"      Old: {old_value[:60]}{'...' if len(old_value) > 60 else ''}")
            logger.info(f"      New: {new_value[:60]}{'...' if len(new_value) > 60 else ''}")
        logger.info("")

    return True


def _compute_diff(context1: Dict, context2: Dict) -> Tuple[List, List, List]:
    """
    Compute differences between two context dictionaries

    Args:
        context1: First context dict
        context2: Second context dict

    Returns:
        Tuple of (added, removed, modified) lists
    """
    added = []
    removed = []
    modified = []

    # Find all unique keys across both contexts
    all_categories = set(context1.keys()) | set(context2.keys())

    for category in all_categories:
        cat1 = context1.get(category, {})
        cat2 = context2.get(category, {})

        all_keys = set(cat1.keys()) | set(cat2.keys())

        for key in all_keys:
            if key in cat2 and key not in cat1:
                # Added in context2
                added.append((category, key, cat2[key]))
            elif key in cat1 and key not in cat2:
                # Removed in context2
                removed.append((category, key, cat1[key]))
            elif key in cat1 and key in cat2:
                if cat1[key] != cat2[key]:
                    # Modified
                    modified.append((category, key, cat1[key], cat2[key]))

    return added, removed, modified


def rollback_context(project_name: str, target_version: int, confirm: bool = False) -> bool:
    """
    Rollback project context to a specific version

    Args:
        project_name: Name of the project
        target_version: Version number to rollback to
        confirm: If True, skip confirmation prompt

    Returns:
        True if successful, False otherwise
    """
    memory = ProjectMemory()
    project = memory.db.get_project(project_name)

    if not project:
        from .fuzzy_match import suggest_project
        logger.error(f"❌ Project '{project_name}' not found")
        suggestion = suggest_project(project_name, memory)
        if suggestion:
            logger.info(suggestion)
        return False

    project_id = project['id']
    current_version = memory.db.get_current_version(project_id)

    if target_version > current_version or target_version < 1:
        logger.error(f"❌ Invalid version. Must be between 1 and {current_version}")
        return False

    if target_version == current_version:
        logger.info(f"✅ Already at version {current_version}")
        return True

    # Show what will change
    logger.info(f"⏪ Rolling back '{project_name}' from v{current_version} to v{target_version}\n")

    current_context = memory.db.get_context_at_version(project_id, current_version)
    target_context = memory.db.get_context_at_version(project_id, target_version)

    added, removed, modified = _compute_diff(target_context, current_context)

    logger.info("This will:")
    if added:
        logger.info(f"  🗑️  Remove {len(added)} items")
    if removed:
        logger.info(f"  🆕 Restore {len(removed)} items")
    if modified:
        logger.info(f"  ✏️  Revert {len(modified)} changes")

    # Confirmation
    if not confirm:
        response = input("\n⚠️  Proceed with rollback? (yes/no): ").strip().lower()
        if response not in ['yes', 'y']:
            logger.info("❌ Rollback cancelled")
            return False

    # Perform rollback
    logger.info("\n⏳ Rolling back...")
    success = memory.db.rollback_to_version(project_id, target_version)

    if success:
        # Invalidate cache
        memory._invalidate_cache(project_name)

        new_version = memory.db.get_current_version(project_id)
        logger.info(f"✅ Rollback complete! Now at v{new_version}")
        logger.info(f"💡 View history: recall {project_name} --history")
        return True
    else:
        logger.error("❌ Rollback failed")
        return False


if __name__ == "__main__":
    import sys

    # Test the context history system
    logger.info("🧪 Testing Context History...")

    if len(sys.argv) < 2:
        logger.info("Usage: context_history.py <project-name>")
        sys.exit(1)

    project_name = sys.argv[1]

    # Show history
    show_history(project_name, limit=10)
