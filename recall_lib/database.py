#!/usr/bin/env python3
"""
Database schema and initialization for Recall project memory system
"""
import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Optional

class RecallDatabase:
    """Manages the SQLite database for project memories"""

    def __init__(self, db_path: str = None):
        if db_path is None:
            # Default to recall directory
            recall_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(recall_dir, 'projects.db')

        self.db_path = db_path
        self.init_database()

    def get_connection(self):
        """Get database connection with row factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn

    def init_database(self):
        """Initialize database with required tables"""
        with self.get_connection() as conn:
            # Projects table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    directory TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Project context (flexible key-value storage)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS project_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    category TEXT NOT NULL,  -- 'architecture', 'state', 'decisions', etc.
                    key TEXT NOT NULL,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                    UNIQUE(project_id, category, key)
                )
            ''')

            # Session history
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    summary TEXT,
                    accomplishments TEXT,
                    decisions_made TEXT,
                    next_steps TEXT,
                    files_changed TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
                )
            ''')

            # Create indexes for performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_context_project ON project_context(project_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_context_category ON project_context(category)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id)')

            conn.commit()

    def create_project(self, name: str, description: str = None, directory: str = None) -> int:
        """Create a new project and return its ID"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'INSERT INTO projects (name, description, directory) VALUES (?, ?, ?)',
                (name, description, directory)
            )
            conn.commit()
            return cursor.lastrowid

    def get_project(self, name: str) -> Optional[Dict]:
        """Get project by name"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM projects WHERE name = ?',
                (name,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_projects(self) -> List[Dict]:
        """List all projects"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                'SELECT * FROM projects ORDER BY updated_at DESC'
            )
            return [dict(row) for row in cursor.fetchall()]

    def update_project_timestamp(self, project_id: int):
        """Update project's last modified timestamp"""
        with self.get_connection() as conn:
            conn.execute(
                'UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (project_id,)
            )
            conn.commit()

    def set_context(self, project_id: int, category: str, key: str, value: str):
        """Set a context value for a project"""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO project_context
                (project_id, category, key, value, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (project_id, category, key, value))
            conn.commit()

            # Update project timestamp
            self.update_project_timestamp(project_id)

    def get_context(self, project_id: int, category: str = None) -> Dict:
        """Get context for a project, optionally filtered by category"""
        with self.get_connection() as conn:
            if category:
                cursor = conn.execute(
                    'SELECT category, key, value FROM project_context WHERE project_id = ? AND category = ?',
                    (project_id, category)
                )
            else:
                cursor = conn.execute(
                    'SELECT category, key, value FROM project_context WHERE project_id = ?',
                    (project_id,)
                )

            # Organize by category
            context = {}
            for row in cursor.fetchall():
                cat, key, value = row
                if cat not in context:
                    context[cat] = {}
                context[cat][key] = value

            return context

    def add_session(self, project_id: int, summary: str = None,
                   accomplishments: str = None, decisions_made: str = None,
                   next_steps: str = None, files_changed: str = None) -> int:
        """Add a session record"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                INSERT INTO sessions
                (project_id, summary, accomplishments, decisions_made, next_steps, files_changed)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (project_id, summary, accomplishments, decisions_made, next_steps, files_changed))
            conn.commit()

            # Update project timestamp
            self.update_project_timestamp(project_id)

            return cursor.lastrowid

    def get_recent_sessions(self, project_id: int, limit: int = 5) -> List[Dict]:
        """Get recent sessions for a project"""
        with self.get_connection() as conn:
            cursor = conn.execute('''
                SELECT * FROM sessions
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (project_id, limit))
            return [dict(row) for row in cursor.fetchall()]


if __name__ == "__main__":
    # Test the database
    print("🗄️ Initializing Recall database...")
    db = RecallDatabase()

    # Test project creation
    try:
        project_id = db.create_project(
            "test-api",
            "Test API server project",
            "/home/seth/Projects/test-api"
        )
        print(f"✅ Created test project with ID: {project_id}")

        # Test context storage
        db.set_context(project_id, "architecture", "stack", "Node.js + Express + PostgreSQL")
        db.set_context(project_id, "architecture", "auth", "JWT tokens")
        db.set_context(project_id, "state", "current_feature", "User authentication")
        db.set_context(project_id, "decisions", "database", "Chose PostgreSQL for ACID compliance")

        # Test context retrieval
        context = db.get_context(project_id)
        print(f"✅ Stored context: {context}")

        # Test session logging
        session_id = db.add_session(
            project_id,
            summary="Implemented JWT authentication system",
            accomplishments="Login/logout endpoints, token validation middleware",
            decisions_made="Used bcrypt for password hashing, 24h token expiry",
            next_steps="Add password reset functionality, implement user roles"
        )
        print(f"✅ Created session with ID: {session_id}")

        print("\n🎉 Database test successful!")

    except Exception as e:
        print(f"❌ Database test failed: {e}")