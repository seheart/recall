#!/usr/bin/env python3
"""
ProjectMemory - Core memory system for project context management
"""
import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from database import RecallDatabase


class ProjectMemory:
    """Manages project memory and context for recall system"""

    def __init__(self, db_path: str = None):
        self.db = RecallDatabase(db_path)

    def create_project(self, name: str, description: str = None,
                      directory: str = None, initial_context: Dict = None) -> int:
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
            next_steps="Define architecture and begin development"
        )

        return project_id

    def get_project_context(self, project_name: str) -> Optional[Dict]:
        """Get complete context for a project"""
        project = self.db.get_project(project_name)
        if not project:
            return None

        project_id = project['id']

        # Get all context data
        context = self.db.get_context(project_id)

        # Get recent sessions
        recent_sessions = self.db.get_recent_sessions(project_id, limit=3)

        # Build comprehensive context
        full_context = {
            'project': project,
            'context': context,
            'recent_sessions': recent_sessions,
            'last_updated': project['updated_at']
        }

        return full_context

    def update_architecture(self, project_name: str, architecture_data: Dict):
        """Update project architecture information"""
        project = self.db.get_project(project_name)
        if not project:
            raise ValueError(f"Project '{project_name}' not found")

        project_id = project['id']

        for key, value in architecture_data.items():
            self.db.set_context(project_id, "architecture", key, str(value))

    def update_state(self, project_name: str, state_data: Dict):
        """Update current project state"""
        project = self.db.get_project(project_name)
        if not project:
            raise ValueError(f"Project '{project_name}' not found")

        project_id = project['id']

        for key, value in state_data.items():
            self.db.set_context(project_id, "state", key, str(value))

    def record_decision(self, project_name: str, decision_key: str,
                       decision_value: str, reasoning: str = None):
        """Record an architectural or technical decision"""
        project = self.db.get_project(project_name)
        if not project:
            raise ValueError(f"Project '{project_name}' not found")

        project_id = project['id']

        # Store the decision
        self.db.set_context(project_id, "decisions", decision_key, decision_value)

        # Store reasoning if provided
        if reasoning:
            self.db.set_context(project_id, "reasoning", decision_key, reasoning)

    def log_session(self, project_name: str, summary: str = None,
                   accomplishments: List[str] = None, decisions: List[str] = None,
                   next_steps: List[str] = None, files_changed: List[str] = None):
        """Log a development session"""
        project = self.db.get_project(project_name)
        if not project:
            raise ValueError(f"Project '{project_name}' not found")

        project_id = project['id']

        # Convert lists to formatted strings
        accomplishments_str = "\n• " + "\n• ".join(accomplishments) if accomplishments else None
        decisions_str = "\n• " + "\n• ".join(decisions) if decisions else None
        next_steps_str = "\n• " + "\n• ".join(next_steps) if next_steps else None
        files_changed_str = "\n• " + "\n• ".join(files_changed) if files_changed else None

        return self.db.add_session(
            project_id, summary, accomplishments_str,
            decisions_str, next_steps_str, files_changed_str
        )

    def format_for_claude(self, project_name: str) -> str:
        """Format project context for Claude Code system prompt"""
        context = self.get_project_context(project_name)
        if not context:
            return f"Project '{project_name}' not found in memory."

        project = context['project']
        ctx = context['context']
        sessions = context['recent_sessions']

        # Build formatted context string
        formatted = f"""PROJECT MEMORY LOADED: {project['name'].upper()}

📁 PROJECT INFO:
• Name: {project['name']}
• Description: {project.get('description', 'No description')}
• Directory: {project.get('directory', 'Not specified')}
• Last Updated: {project['updated_at']}

"""

        # Add architecture info
        if 'architecture' in ctx:
            formatted += "🏗️ ARCHITECTURE:\n"
            for key, value in ctx['architecture'].items():
                formatted += f"• {key}: {value}\n"
            formatted += "\n"

        # Add current state
        if 'state' in ctx:
            formatted += "⚡ CURRENT STATE:\n"
            for key, value in ctx['state'].items():
                formatted += f"• {key}: {value}\n"
            formatted += "\n"

        # Add decisions
        if 'decisions' in ctx:
            formatted += "🎯 KEY DECISIONS:\n"
            for key, value in ctx['decisions'].items():
                formatted += f"• {key}: {value}\n"
                # Add reasoning if available
                if 'reasoning' in ctx and key in ctx['reasoning']:
                    formatted += f"  └─ Reasoning: {ctx['reasoning'][key]}\n"
            formatted += "\n"

        # Add environment/setup info
        if 'environment' in ctx:
            formatted += "⚙️ ENVIRONMENT:\n"
            for key, value in ctx['environment'].items():
                formatted += f"• {key}: {value}\n"
            formatted += "\n"

        # Add recent sessions
        if sessions:
            formatted += "📝 RECENT WORK:\n"
            for i, session in enumerate(sessions[:2]):  # Show last 2 sessions
                formatted += f"\nSession {i+1} ({session['created_at'][:10]}):\n"
                if session['summary']:
                    formatted += f"• Summary: {session['summary']}\n"
                if session['accomplishments']:
                    formatted += f"• Done:{session['accomplishments']}\n"
                if session['next_steps']:
                    formatted += f"• Next:{session['next_steps']}\n"

        formatted += "\n" + "="*60 + "\n"
        formatted += "💡 You now have complete context for this project.\n"
        formatted += "Continue development with full awareness of architecture, decisions, and progress.\n"
        formatted += "="*60

        return formatted

    def list_all_projects(self) -> List[Dict]:
        """List all projects with basic info"""
        return self.db.list_projects()

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
            if project.get('directory') and os.path.samefile(directory, project['directory']):
                return project['name']

        # Try to match by directory name
        dir_name = os.path.basename(directory)
        for project in projects:
            if project['name'] == dir_name:
                return project['name']

        return None


if __name__ == "__main__":
    # Test the ProjectMemory system
    print("🧠 Testing ProjectMemory system...")

    memory = ProjectMemory()

    # Test project creation with context
    project_id = memory.create_project(
        "recall-system",
        "The recall project memory system itself",
        "/home/seth/Projects/recall",
        {
            "architecture": {
                "language": "Python 3",
                "database": "SQLite",
                "framework": "None (pure Python)"
            },
            "state": {
                "current_feature": "Building core memory system",
                "status": "In development"
            }
        }
    )
    print(f"✅ Created project with ID: {project_id}")

    # Test recording decisions
    memory.record_decision(
        "recall-system",
        "database_choice",
        "SQLite",
        "Chose SQLite for simplicity and no external dependencies"
    )

    # Test logging session
    memory.log_session(
        "recall-system",
        summary="Built core database and memory classes",
        accomplishments=[
            "Created RecallDatabase class with full schema",
            "Built ProjectMemory class for context management",
            "Added session logging and context formatting"
        ],
        next_steps=[
            "Build recall command script",
            "Create context formatter for Claude Code",
            "Test end-to-end workflow"
        ]
    )

    # Test context formatting for Claude
    formatted = memory.format_for_claude("recall-system")
    print("\n" + "="*60)
    print("FORMATTED CONTEXT FOR CLAUDE:")
    print("="*60)
    print(formatted)

    print("\n🎉 ProjectMemory test successful!")