#!/usr/bin/env python3
"""
Database schema and initialization for Recall project memory system
"""
import sqlite3
import os
from datetime import datetime
from typing import Dict, List, Optional

from .logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class RecallDatabase:
    """Manages the SQLite database for project memories"""

    def __init__(self, db_path: str = None, auto_migrate: bool = True, use_pool: bool = True):
        if db_path is None:
            # Default to user data directory (~/.local/share/recall)
            data_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "recall")
            os.makedirs(data_dir, exist_ok=True)
            db_path = os.path.join(data_dir, "projects.db")

        self.db_path = db_path
        self.use_pool = use_pool
        self._pool = None

        # Initialize connection pool if enabled
        if self.use_pool:
            from .connection_pool import get_global_pool

            self._pool = get_global_pool(self.db_path, pool_size=5)

        self.init_database()

        # Run migrations automatically (unless disabled)
        if auto_migrate:
            from .migrations import auto_migrate

            auto_migrate(self.db_path)

    def get_connection(self):
        """
        Get database connection (from pool if enabled, otherwise direct connection)

        Note: When using pool, connection should be used with context manager
        """
        if self.use_pool and self._pool:
            return self._pool.connection()
        else:
            # Fallback to direct connection
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            return conn

    def init_database(self):
        """Initialize database with required tables"""
        with self.get_connection() as conn:
            # Projects table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    directory TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Project context (flexible key-value storage)
            conn.execute(
                """
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
            """
            )

            # Session history
            conn.execute(
                """
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
            """
            )

            # Project tags table (for categorization and filtering)
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS project_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    tag TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                    UNIQUE(project_id, tag)
                )
            """
            )

            # Create indexes for performance
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_context_project ON project_context(project_id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_context_category ON project_context(category)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_project ON project_tags(project_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_tags_tag ON project_tags(tag)")

            conn.commit()

        # Set restrictive file permissions on database (owner read/write only)
        try:
            if os.path.exists(self.db_path):
                os.chmod(self.db_path, 0o600)  # rw------- (owner only)
                logger.debug(f"Set database file permissions to 0600: {self.db_path}")
        except (OSError, PermissionError) as e:
            logger.warning(f"Could not set database file permissions: {e}")

    def create_project(self, name: str, description: str = None, directory: str = None) -> int:
        """Create a new project and return its ID"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO projects (name, description, directory) VALUES (?, ?, ?)",
                (name, description, directory),
            )
            conn.commit()
            return cursor.lastrowid

    def get_project(self, name: str) -> Optional[Dict]:
        """Get project by name"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    id, name, description, directory,
                    datetime(created_at, 'localtime') as created_at,
                    datetime(updated_at, 'localtime') as updated_at
                FROM projects
                WHERE name = ?
            """,
                (name,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_projects(self) -> List[Dict]:
        """List all projects"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    id, name, description, directory,
                    datetime(created_at, 'localtime') as created_at,
                    datetime(updated_at, 'localtime') as updated_at
                FROM projects
                ORDER BY name ASC
            """
            )
            return [dict(row) for row in cursor.fetchall()]

    def search_projects(self, query: str) -> List[Dict]:
        """
        Search projects by name, description, or directory
        Uses case-insensitive LIKE matching across all fields

        Args:
            query: Search query string

        Returns:
            List of matching projects, ordered by relevance
        """
        with self.get_connection() as conn:
            # Use LIKE for fuzzy matching, case-insensitive
            search_pattern = f"%{query}%"
            cursor = conn.execute(
                """
                SELECT
                    id, name, description, directory,
                    datetime(created_at, 'localtime') as created_at,
                    datetime(updated_at, 'localtime') as updated_at,
                    -- Calculate relevance score (exact name match gets highest priority)
                    CASE
                        WHEN LOWER(name) = LOWER(?) THEN 100
                        WHEN LOWER(name) LIKE LOWER(?) THEN 50
                        WHEN LOWER(description) LIKE LOWER(?) THEN 30
                        WHEN LOWER(directory) LIKE LOWER(?) THEN 20
                        ELSE 10
                    END as relevance
                FROM projects
                WHERE
                    LOWER(name) LIKE LOWER(?)
                    OR LOWER(description) LIKE LOWER(?)
                    OR LOWER(directory) LIKE LOWER(?)
                ORDER BY relevance DESC, updated_at DESC
            """,
                (
                    query,
                    search_pattern,
                    search_pattern,
                    search_pattern,
                    search_pattern,
                    search_pattern,
                    search_pattern,
                ),
            )
            return [dict(row) for row in cursor.fetchall()]

    def update_project_timestamp(self, project_id: int) -> None:
        """Update project's last modified timestamp"""
        with self.get_connection() as conn:
            conn.execute(
                "UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (project_id,)
            )
            conn.commit()

    def set_context(
        self, project_id: int, category: str, key: str, value: str, track_history: bool = True
    ) -> None:
        """
        Set a context value for a project

        Args:
            project_id: Project ID
            category: Context category
            key: Context key
            value: Context value
            track_history: If True, record change in context_history
        """
        with self.get_connection() as conn:
            # Get old value if it exists (for history tracking)
            old_value = None
            operation = "create"

            if track_history:
                cursor = conn.execute(
                    "SELECT value FROM project_context WHERE project_id = ? AND category = ? AND key = ?",
                    (project_id, category, key),
                )
                row = cursor.fetchone()
                if row:
                    old_value = row["value"]
                    operation = (
                        "update" if old_value != value else "update"
                    )  # Still track even if same value

            # Insert or update the context value
            conn.execute(
                """
                INSERT OR REPLACE INTO project_context
                (project_id, category, key, value, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
                (project_id, category, key, value),
            )

            # Track history if enabled
            if track_history:
                self._record_context_history(
                    conn, project_id, category, key, value, old_value, operation
                )

            conn.commit()

            # Update project timestamp
            self.update_project_timestamp(project_id)

    def _get_next_version(self, conn, project_id: int) -> int:
        """Get and increment version number for project (atomic operation)"""
        try:
            # Try modern SQLite 3.35+ atomic upsert with RETURNING
            cursor = conn.execute(
                """
                INSERT INTO project_metadata (project_id, current_version)
                VALUES (?, 1)
                ON CONFLICT(project_id) DO UPDATE SET
                    current_version = current_version + 1
                RETURNING current_version
            """,
                (project_id,),
            )

            row = cursor.fetchone()
            return row["current_version"] if row else 1

        except sqlite3.OperationalError as e:
            error_str = str(e)
            # Fallback for older SQLite versions (< 3.35) or missing table
            if "RETURNING" in error_str or "no such table" in error_str:
                # Create table if it doesn't exist
                try:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS project_metadata (
                            project_id INTEGER PRIMARY KEY,
                            current_version INTEGER DEFAULT 0,
                            last_snapshot_at TIMESTAMP,
                            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
                        )
                    """
                    )
                except sqlite3.OperationalError:
                    pass  # Table might exist now

                # Ensure metadata row exists
                conn.execute(
                    """
                    INSERT OR IGNORE INTO project_metadata (project_id, current_version)
                    VALUES (?, 0)
                """,
                    (project_id,),
                )

                # Increment and get version atomically within transaction
                conn.execute(
                    """
                    UPDATE project_metadata
                    SET current_version = current_version + 1
                    WHERE project_id = ?
                """,
                    (project_id,),
                )

                cursor = conn.execute(
                    "SELECT current_version FROM project_metadata WHERE project_id = ?",
                    (project_id,),
                )
                row = cursor.fetchone()
                return row["current_version"] if row else 1
            else:
                raise

    def _record_context_history(
        self,
        conn,
        project_id: int,
        category: str,
        key: str,
        value: str,
        old_value: str,
        operation: str,
    ) -> None:
        """Record a context change in history"""
        version = self._get_next_version(conn, project_id)

        try:
            conn.execute(
                """
                INSERT INTO context_history
                (project_id, category, key, value, old_value, operation, version)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (project_id, category, key, value, old_value, operation, version),
            )
        except sqlite3.OperationalError as e:
            # If table doesn't exist (e.g., in tests), create it
            if "no such table" in str(e):
                try:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS context_history (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            project_id INTEGER NOT NULL,
                            category TEXT NOT NULL,
                            key TEXT NOT NULL,
                            value TEXT,
                            old_value TEXT,
                            operation TEXT NOT NULL,
                            version INTEGER NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
                        )
                    """
                    )
                    # Retry the insert
                    conn.execute(
                        """
                        INSERT INTO context_history
                        (project_id, category, key, value, old_value, operation, version)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (project_id, category, key, value, old_value, operation, version),
                    )
                except sqlite3.OperationalError:
                    # If it still fails, just skip history tracking
                    pass
            else:
                raise

    def get_context(self, project_id: int, category: str = None) -> Dict:
        """Get context for a project, optionally filtered by category"""
        with self.get_connection() as conn:
            if category:
                cursor = conn.execute(
                    "SELECT category, key, value FROM project_context WHERE project_id = ? AND category = ?",
                    (project_id, category),
                )
            else:
                cursor = conn.execute(
                    "SELECT category, key, value FROM project_context WHERE project_id = ?",
                    (project_id,),
                )

            # Organize by category
            context = {}
            for row in cursor.fetchall():
                cat, key, value = row
                if cat not in context:
                    context[cat] = {}
                context[cat][key] = value

            return context

    def add_session(
        self,
        project_id: int,
        summary: str = None,
        accomplishments: str = None,
        decisions_made: str = None,
        next_steps: str = None,
        files_changed: str = None,
    ) -> int:
        """Add a session record"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sessions
                (project_id, summary, accomplishments, decisions_made, next_steps, files_changed)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (project_id, summary, accomplishments, decisions_made, next_steps, files_changed),
            )
            conn.commit()

            # Update project timestamp
            self.update_project_timestamp(project_id)

            return cursor.lastrowid

    def get_recent_sessions(self, project_id: int, limit: int = 5) -> List[Dict]:
        """Get recent sessions for a project"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    id, project_id, summary, accomplishments,
                    decisions_made, next_steps, files_changed,
                    datetime(created_at, 'localtime') as created_at
                FROM sessions
                WHERE project_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
            """,
                (project_id, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def add_tag(self, project_id: int, tag: str) -> None:
        """Add a tag to a project"""
        with self.get_connection() as conn:
            try:
                conn.execute(
                    "INSERT INTO project_tags (project_id, tag) VALUES (?, ?)",
                    (project_id, tag.lower().strip()),
                )
                conn.commit()
            except sqlite3.IntegrityError:
                # Tag already exists (UNIQUE constraint) - ignore
                pass

    def remove_tag(self, project_id: int, tag: str) -> None:
        """Remove a tag from a project"""
        with self.get_connection() as conn:
            conn.execute(
                "DELETE FROM project_tags WHERE project_id = ? AND tag = ?",
                (project_id, tag.lower().strip()),
            )
            conn.commit()

    def get_tags(self, project_id: int) -> List[str]:
        """Get all tags for a project"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT tag FROM project_tags WHERE project_id = ? ORDER BY tag", (project_id,)
            )
            return [row["tag"] for row in cursor.fetchall()]

    def get_projects_by_tag(self, tag: str) -> List[Dict]:
        """Get all projects with a specific tag"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT DISTINCT
                    p.id, p.name, p.description, p.directory,
                    datetime(p.created_at, 'localtime') as created_at,
                    datetime(p.updated_at, 'localtime') as updated_at
                FROM projects p
                INNER JOIN project_tags t ON p.id = t.project_id
                WHERE t.tag = ?
                ORDER BY p.updated_at DESC
            """,
                (tag.lower().strip(),),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_all_tags(self) -> List[Dict[str, any]]:
        """Get all tags with project counts"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT tag, COUNT(DISTINCT project_id) as count
                FROM project_tags
                GROUP BY tag
                ORDER BY tag ASC
            """
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_context_history(self, project_id: int, limit: int = 50) -> List[Dict]:
        """
        Get context change history for a project

        Args:
            project_id: Project ID
            limit: Maximum number of history entries to return

        Returns:
            List of history entries, newest first
        """
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    id, project_id, category, key, value, old_value,
                    operation, version,
                    datetime(created_at, 'localtime') as created_at
                FROM context_history
                WHERE project_id = ?
                ORDER BY version DESC, created_at DESC
                LIMIT ?
            """,
                (project_id, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_context_at_version(self, project_id: int, version: int) -> Dict:
        """
        Reconstruct project context as it was at a specific version

        Args:
            project_id: Project ID
            version: Version number to reconstruct

        Returns:
            Context dict at that version
        """
        with self.get_connection() as conn:
            # Get all changes up to and including this version
            cursor = conn.execute(
                """
                SELECT category, key, value, operation
                FROM context_history
                WHERE project_id = ? AND version <= ?
                ORDER BY version ASC, created_at ASC
            """,
                (project_id, version),
            )

            context = {}
            for row in cursor.fetchall():
                cat, key, value, operation = (
                    row["category"],
                    row["key"],
                    row["value"],
                    row["operation"],
                )

                if operation == "delete":
                    # Remove from context
                    if cat in context and key in context[cat]:
                        del context[cat][key]
                        if not context[cat]:  # Remove empty category
                            del context[cat]
                else:  # 'create' or 'update'
                    if cat not in context:
                        context[cat] = {}
                    context[cat][key] = value

            return context

    def get_current_version(self, project_id: int) -> int:
        """Get current version number for a project"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT current_version FROM project_metadata WHERE project_id = ?", (project_id,)
            )
            row = cursor.fetchone()
            return row["current_version"] if row else 0

    def rollback_to_version(self, project_id: int, target_version: int) -> bool:
        """
        Rollback project context to a specific version

        Args:
            project_id: Project ID
            target_version: Version number to rollback to

        Returns:
            True if successful, False otherwise
        """
        with self.get_connection() as conn:
            # Get context at target version
            target_context = self.get_context_at_version(project_id, target_version)

            # Clear current context
            conn.execute("DELETE FROM project_context WHERE project_id = ?", (project_id,))

            # Restore context from target version (without tracking history to avoid recursion)
            for category, items in target_context.items():
                for key, value in items.items():
                    conn.execute(
                        """
                        INSERT INTO project_context (project_id, category, key, value, updated_at)
                        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                        (project_id, category, key, value),
                    )

            # Record rollback in history
            version = self._get_next_version(conn, project_id)
            conn.execute(
                """
                INSERT INTO context_history
                (project_id, category, key, value, old_value, operation, version)
                VALUES (?, 'meta', 'rollback', ?, NULL, 'rollback', ?)
            """,
                (project_id, f"Rolled back to version {target_version}", version),
            )

            conn.commit()
            return True


if __name__ == "__main__":
    # Test the database
    logger.info("🗄️ Initializing Recall database...")
    db = RecallDatabase()

    # Test project creation
    try:
        project_id = db.create_project("test-api", "Test API server project", "/path/to/test-api")
        logger.info(f"✅ Created test project with ID: {project_id}")

        # Test context storage
        db.set_context(project_id, "architecture", "stack", "Node.js + Express + PostgreSQL")
        db.set_context(project_id, "architecture", "auth", "JWT tokens")
        db.set_context(project_id, "state", "current_feature", "User authentication")
        db.set_context(project_id, "decisions", "database", "Chose PostgreSQL for ACID compliance")

        # Test context retrieval
        context = db.get_context(project_id)
        logger.info(f"✅ Stored context: {context}")

        # Test session logging
        session_id = db.add_session(
            project_id,
            summary="Implemented JWT authentication system",
            accomplishments="Login/logout endpoints, token validation middleware",
            decisions_made="Used bcrypt for password hashing, 24h token expiry",
            next_steps="Add password reset functionality, implement user roles",
        )
        logger.info(f"✅ Created session with ID: {session_id}")

        logger.info("\n🎉 Database test successful!")

    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
