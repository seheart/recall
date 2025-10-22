#!/usr/bin/env python3
"""
Helper functions for managing issues, blockers, and documentation links
"""
from .project_memory import ProjectMemory
from .logger import get_logger

logger = get_logger(__name__)


def add_issue(project_name: str, issue_key: str, description: str) -> bool:
    """Add a known issue to project context"""
    memory = ProjectMemory()
    project = memory.db.get_project(project_name)
    if not project:
        logger.error(f"❌ Project '{project_name}' not found")
        return False

    memory.db.set_context(project["id"], "issues", issue_key, description)
    logger.info(f"✅ Added issue '{issue_key}' to {project_name}")
    return True


def add_blocker(project_name: str, blocker_key: str, description: str) -> bool:
    """Add a blocker to project context"""
    memory = ProjectMemory()
    project = memory.db.get_project(project_name)
    if not project:
        logger.error(f"❌ Project '{project_name}' not found")
        return False

    memory.db.set_context(project["id"], "blockers", blocker_key, description)
    logger.info(f"🚫 Added blocker '{blocker_key}' to {project_name}")
    return True


def remove_issue(project_name: str, issue_key: str) -> bool:
    """Remove a resolved issue"""
    memory = ProjectMemory()
    project = memory.db.get_project(project_name)
    if not project:
        logger.error(f"❌ Project '{project_name}' not found")
        return False

    conn = memory.db.get_connection()
    conn.execute(
        """
        DELETE FROM project_context
        WHERE project_id = ? AND category = 'issues' AND key = ?
    """,
        (project["id"], issue_key),
    )
    conn.commit()
    conn.close()

    logger.info(f"✅ Removed issue '{issue_key}' from {project_name}")
    return True


def remove_blocker(project_name: str, blocker_key: str) -> bool:
    """Remove a resolved blocker"""
    memory = ProjectMemory()
    project = memory.db.get_project(project_name)
    if not project:
        logger.error(f"❌ Project '{project_name}' not found")
        return False

    conn = memory.db.get_connection()
    conn.execute(
        """
        DELETE FROM project_context
        WHERE project_id = ? AND category = 'blockers' AND key = ?
    """,
        (project["id"], blocker_key),
    )
    conn.commit()
    conn.close()

    logger.info(f"✅ Removed blocker '{blocker_key}' from {project_name}")
    return True


def add_doc_link(project_name: str, doc_name: str, url: str) -> bool:
    """Add a documentation link"""
    memory = ProjectMemory()
    project = memory.db.get_project(project_name)
    if not project:
        logger.error(f"❌ Project '{project_name}' not found")
        return False

    memory.db.set_context(project["id"], "documentation", doc_name, url)
    logger.info(f"📚 Added documentation link '{doc_name}' to {project_name}")
    return True


def add_integration(project_name: str, service_name: str, details: str) -> bool:
    """Add third-party service integration info"""
    memory = ProjectMemory()
    project = memory.db.get_project(project_name)
    if not project:
        logger.error(f"❌ Project '{project_name}' not found")
        return False

    memory.db.set_context(project["id"], "integrations", service_name, details)
    logger.info(f"🔌 Added integration '{service_name}' to {project_name}")
    return True


def add_convention(project_name: str, convention_type: str, description: str) -> bool:
    """Add code convention or pattern"""
    memory = ProjectMemory()
    project = memory.db.get_project(project_name)
    if not project:
        logger.error(f"❌ Project '{project_name}' not found")
        return False

    memory.db.set_context(project["id"], "conventions", convention_type, description)
    logger.info(f"📐 Added convention '{convention_type}' to {project_name}")
    return True


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        logger.info(
            """
Usage:
  helpers.py add-issue <project> <key> <description>
  helpers.py add-blocker <project> <key> <description>
  helpers.py remove-issue <project> <key>
  helpers.py remove-blocker <project> <key>
  helpers.py add-doc <project> <name> <url>
  helpers.py add-integration <project> <service> <details>
  helpers.py add-convention <project> <type> <description>
        """
        )
        sys.exit(1)

    command = sys.argv[1]

    if command == "add-issue" and len(sys.argv) >= 5:
        add_issue(sys.argv[2], sys.argv[3], " ".join(sys.argv[4:]))
    elif command == "add-blocker" and len(sys.argv) >= 5:
        add_blocker(sys.argv[2], sys.argv[3], " ".join(sys.argv[4:]))
    elif command == "remove-issue" and len(sys.argv) >= 4:
        remove_issue(sys.argv[2], sys.argv[3])
    elif command == "remove-blocker" and len(sys.argv) >= 4:
        remove_blocker(sys.argv[2], sys.argv[3])
    elif command == "add-doc" and len(sys.argv) >= 5:
        add_doc_link(sys.argv[2], sys.argv[3], sys.argv[4])
    elif command == "add-integration" and len(sys.argv) >= 5:
        add_integration(sys.argv[2], sys.argv[3], " ".join(sys.argv[4:]))
    elif command == "add-convention" and len(sys.argv) >= 5:
        add_convention(sys.argv[2], sys.argv[3], " ".join(sys.argv[4:]))
    else:
        logger.info("Invalid command or arguments")
        sys.exit(1)
