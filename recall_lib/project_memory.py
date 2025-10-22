#!/usr/bin/env python3
"""
ProjectMemory - Core memory system for project context management
"""
import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from .database import RecallDatabase

from .logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class ProjectMemory:
    """Manages project memory and context for recall system"""

    # Cache configuration
    CACHE_TTL = 300  # 5 minutes in seconds
    MAX_CACHE_SIZE = 50  # Maximum number of projects to cache

    def __init__(self, db_path: str = None):
        self.db = RecallDatabase(db_path)
        self._context_cache: Dict[str, Dict[str, Any]] = (
            {}
        )  # {project_name: {'data': ..., 'timestamp': ...}}

    def _invalidate_cache(self, project_name: str) -> None:
        """Invalidate cache for a specific project"""
        if project_name in self._context_cache:
            del self._context_cache[project_name]

    def _clear_expired_cache(self):
        """Remove expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key
            for key, value in self._context_cache.items()
            if current_time - value["timestamp"] > self.CACHE_TTL
        ]
        for key in expired_keys:
            del self._context_cache[key]

    def _enforce_cache_size(self):
        """Remove oldest entries if cache exceeds max size"""
        if len(self._context_cache) > self.MAX_CACHE_SIZE:
            # Remove oldest entry (FIFO)
            oldest_key = min(self._context_cache.items(), key=lambda x: x[1]["timestamp"])[0]
            del self._context_cache[oldest_key]

    def create_project(
        self,
        name: str,
        description: str = None,
        directory: str = None,
        initial_context: Dict = None,
    ) -> int:
        """Create a new project with optional initial context"""
        project_id = self.db.create_project(name, description, directory)

        if initial_context:
            for category, data in initial_context.items():
                if isinstance(data, dict):
                    for key, value in data.items():
                        self.db.set_context(project_id, category, key, str(value))
                else:
                    self.db.set_context(project_id, category, "info", str(data))

        # Add creation session
        self.db.add_session(
            project_id,
            summary=f"Created project '{name}'",
            accomplishments="Project initialization and setup",
            next_steps="Define architecture and begin development",
        )

        return project_id

    def get_project_context(self, project_name: str) -> Optional[Dict]:
        """Get complete context for a project (with caching)"""
        # Clear expired cache entries
        self._clear_expired_cache()

        # Check cache first
        current_time = time.time()
        if project_name in self._context_cache:
            cached = self._context_cache[project_name]
            if current_time - cached["timestamp"] <= self.CACHE_TTL:
                return cached["data"]

        # Cache miss or expired - fetch from database
        project = self.db.get_project(project_name)
        if not project:
            return None

        project_id = project["id"]

        # Get all context data
        context = self.db.get_context(project_id)

        # Get recent sessions
        recent_sessions = self.db.get_recent_sessions(project_id, limit=3)

        # Build comprehensive context
        full_context = {
            "project": project,
            "context": context,
            "recent_sessions": recent_sessions,
            "last_updated": project["updated_at"],
        }

        # Store in cache
        self._context_cache[project_name] = {"data": full_context, "timestamp": current_time}

        # Enforce cache size limit
        self._enforce_cache_size()

        return full_context

    def update_architecture(self, project_name: str, architecture_data: Dict) -> None:
        """Update project architecture information"""
        project = self.db.get_project(project_name)
        if not project:
            raise ValueError(f"Project '{project_name}' not found")

        project_id = project["id"]

        for key, value in architecture_data.items():
            self.db.set_context(project_id, "architecture", key, str(value))

        # Invalidate cache after update
        self._invalidate_cache(project_name)

    def update_state(self, project_name: str, state_data: Dict) -> None:
        """Update current project state"""
        project = self.db.get_project(project_name)
        if not project:
            raise ValueError(f"Project '{project_name}' not found")

        project_id = project["id"]

        for key, value in state_data.items():
            self.db.set_context(project_id, "state", key, str(value))

        # Invalidate cache after update
        self._invalidate_cache(project_name)

    def record_decision(
        self, project_name: str, decision_key: str, decision_value: str, reasoning: str = None
    ) -> None:
        """Record an architectural or technical decision"""
        project = self.db.get_project(project_name)
        if not project:
            raise ValueError(f"Project '{project_name}' not found")

        project_id = project["id"]

        # Store the decision
        self.db.set_context(project_id, "decisions", decision_key, decision_value)

        # Store reasoning if provided
        if reasoning:
            self.db.set_context(project_id, "reasoning", decision_key, reasoning)

        # Invalidate cache after update
        self._invalidate_cache(project_name)

    def log_session(
        self,
        project_name: str,
        summary: str = None,
        accomplishments: List[str] = None,
        decisions: List[str] = None,
        next_steps: List[str] = None,
        files_changed: List[str] = None,
    ) -> int:
        """Log a development session"""
        project = self.db.get_project(project_name)
        if not project:
            raise ValueError(f"Project '{project_name}' not found")

        project_id = project["id"]

        # Convert lists to formatted strings
        accomplishments_str = "\n• " + "\n• ".join(accomplishments) if accomplishments else None
        decisions_str = "\n• " + "\n• ".join(decisions) if decisions else None
        next_steps_str = "\n• " + "\n• ".join(next_steps) if next_steps else None
        files_changed_str = "\n• " + "\n• ".join(files_changed) if files_changed else None

        result = self.db.add_session(
            project_id,
            summary,
            accomplishments_str,
            decisions_str,
            next_steps_str,
            files_changed_str,
        )

        # Invalidate cache after update
        self._invalidate_cache(project_name)

        return result

    def format_for_claude(self, project_name: str) -> str:
        """Format project context for Claude Code system prompt"""
        context = self.get_project_context(project_name)
        if not context:
            return f"Project '{project_name}' not found in memory."

        project = context["project"]
        ctx = context["context"]
        sessions = context["recent_sessions"]

        # Build formatted context string
        formatted = f"""PROJECT MEMORY LOADED: {project['name'].upper()}

📁 PROJECT INFO:
• Name: {project['name']}
• Description: {project.get('description', 'No description')}
• Directory: {project.get('directory', 'Not specified')}
• Last Updated: {project['updated_at']}

"""

        # Add architecture info
        if "architecture" in ctx:
            formatted += "🏗️ ARCHITECTURE:\n"
            for key, value in ctx["architecture"].items():
                formatted += f"• {key}: {value}\n"
            formatted += "\n"

        # Add current state
        if "state" in ctx:
            formatted += "⚡️ CURRENT STATE:\n"
            for key, value in ctx["state"].items():
                formatted += f"• {key}: {value}\n"
            formatted += "\n"

        # Add decisions
        if "decisions" in ctx:
            formatted += "🎯 KEY DECISIONS:\n"
            for key, value in ctx["decisions"].items():
                formatted += f"• {key}: {value}\n"
                # Add reasoning if available
                if "reasoning" in ctx and key in ctx["reasoning"]:
                    formatted += f"  └─ Reasoning: {ctx['reasoning'][key]}\n"
            formatted += "\n"

        # Add environment/setup info
        if "environment" in ctx:
            formatted += "⚙️ ENVIRONMENT:\n"
            for key, value in ctx["environment"].items():
                formatted += f"• {key}: {value}\n"
            formatted += "\n"

        # Add recent sessions
        if sessions:
            formatted += "📝 RECENT WORK:\n"
            for i, session in enumerate(sessions[:2]):  # Show last 2 sessions
                formatted += f"\nSession {i+1} ({session['created_at'][:10]}):\n"
                if session["summary"]:
                    formatted += f"• Summary: {session['summary']}\n"
                if session["accomplishments"]:
                    formatted += f"• Done:{session['accomplishments']}\n"
                if session["next_steps"]:
                    formatted += f"• Next:{session['next_steps']}\n"

        formatted += "\n" + "=" * 60 + "\n"
        formatted += "💡 You now have complete context for this project.\n"
        formatted += (
            "Continue development with full awareness of architecture, decisions, and progress.\n"
        )
        formatted += "=" * 60

        return formatted

    def list_all_projects(self) -> List[Dict]:
        """List all projects with basic info"""
        return self.db.list_projects()

    def search_projects(self, query: str) -> List[Dict]:
        """
        Search for projects by name, description, or directory

        Args:
            query: Search query string

        Returns:
            List of matching projects
        """
        return self.db.search_projects(query)

    def project_exists(self, name: str) -> bool:
        """Check if a project exists"""
        return self.db.get_project(name) is not None

    def detect_project_from_directory(self, directory: str = None) -> Optional[str]:
        """Try to detect project name from current directory"""
        if directory is None:
            directory = os.getcwd()

        # Look for projects that match the current directory
        projects = self.list_all_projects()
        for project in projects:
            if project.get("directory") and os.path.samefile(directory, project["directory"]):
                return project["name"]

        # Try to match by directory name
        dir_name = os.path.basename(directory)
        for project in projects:
            if project["name"] == dir_name:
                return project["name"]

        return None

    def add_tag(self, project_name: str, tag: str) -> bool:
        """
        Add a tag to a project

        Args:
            project_name: Name of the project
            tag: Tag to add (will be normalized to lowercase)

        Returns:
            True if successful, False if project not found
        """
        project = self.db.get_project(project_name)
        if not project:
            return False

        self.db.add_tag(project["id"], tag)
        self._invalidate_cache(project_name)
        return True

    def remove_tag(self, project_name: str, tag: str) -> bool:
        """
        Remove a tag from a project

        Args:
            project_name: Name of the project
            tag: Tag to remove

        Returns:
            True if successful, False if project not found
        """
        project = self.db.get_project(project_name)
        if not project:
            return False

        self.db.remove_tag(project["id"], tag)
        self._invalidate_cache(project_name)
        return True

    def get_tags(self, project_name: str) -> List[str]:
        """
        Get all tags for a project

        Args:
            project_name: Name of the project

        Returns:
            List of tags, or empty list if project not found
        """
        project = self.db.get_project(project_name)
        if not project:
            return []

        return self.db.get_tags(project["id"])

    def get_projects_by_tag(self, tag: str) -> List[Dict]:
        """
        Get all projects with a specific tag

        Args:
            tag: Tag to filter by

        Returns:
            List of projects with the tag
        """
        return self.db.get_projects_by_tag(tag)

    def get_all_tags(self) -> List[Dict[str, any]]:
        """
        Get all tags with project counts

        Returns:
            List of dicts with 'tag' and 'count' keys
        """
        return self.db.get_all_tags()


if __name__ == "__main__":
    # Test the ProjectMemory system
    logger.info("🧠 Testing ProjectMemory system...")

    memory = ProjectMemory()

    # Test project creation with context
    project_id = memory.create_project(
        "recall-system",
        "The recall project memory system itself",
        "/path/to/recall",
        {
            "architecture": {
                "language": "Python 3",
                "database": "SQLite",
                "framework": "None (pure Python)",
            },
            "state": {"current_feature": "Building core memory system", "status": "In development"},
        },
    )
    logger.info(f"✅ Created project with ID: {project_id}")

    # Test recording decisions
    memory.record_decision(
        "recall-system",
        "database_choice",
        "SQLite",
        "Chose SQLite for simplicity and no external dependencies",
    )

    # Test logging session
    memory.log_session(
        "recall-system",
        summary="Built core database and memory classes",
        accomplishments=[
            "Created RecallDatabase class with full schema",
            "Built ProjectMemory class for context management",
            "Added session logging and context formatting",
        ],
        next_steps=[
            "Build recall command script",
            "Create context formatter for Claude Code",
            "Test end-to-end workflow",
        ],
    )

    # Test context formatting for Claude
    formatted = memory.format_for_claude("recall-system")
    logger.info("\n" + "=" * 60)
    logger.info("FORMATTED CONTEXT FOR CLAUDE:")
    logger.info("=" * 60)
    print(formatted)

    logger.info("\n🎉 ProjectMemory test successful!")
