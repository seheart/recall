#!/usr/bin/env python3
"""
Database Migrations - Version tracking and schema evolution
"""
import sqlite3
from typing import List, Callable
from pathlib import Path
from .logger import get_logger

logger = get_logger(__name__)


class Migration:
    """Represents a single database migration"""

    def __init__(self, version: int, name: str, up: Callable, down: Callable = None):
        self.version = version
        self.name = name
        self.up = up  # Function to apply migration
        self.down = down  # Function to rollback migration (optional)


class MigrationManager:
    """Manages database schema migrations"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.migrations: List[Migration] = []
        self._register_migrations()

    def _get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_migrations_table(self):
        """Create migrations tracking table if it doesn't exist"""
        with self._get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def get_current_version(self) -> int:
        """Get the current schema version"""
        self._init_migrations_table()

        with self._get_connection() as conn:
            cursor = conn.execute(
                'SELECT MAX(version) as version FROM schema_migrations'
            )
            row = cursor.fetchone()
            return row['version'] if row['version'] is not None else 0

    def _register_migrations(self):
        """Register all migrations in order"""

        # Migration 1: Add project_tags table (v1)
        def migration_001_up(conn):
            """Add project tags support"""
            # Check if table already exists
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='project_tags'"
            )
            if cursor.fetchone():
                logger.info("  └─ project_tags table already exists, skipping")
                return

            conn.execute('''
                CREATE TABLE project_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    tag TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE,
                    UNIQUE(project_id, tag)
                )
            ''')
            conn.execute('CREATE INDEX idx_tags_project ON project_tags(project_id)')
            conn.execute('CREATE INDEX idx_tags_tag ON project_tags(tag)')
            logger.info("  └─ Created project_tags table with indexes")

        self.migrations.append(Migration(
            version=1,
            name="add_project_tags_table",
            up=migration_001_up
        ))

        # Migration 2: Add search indexes (v2)
        def migration_002_up(conn):
            """Add indexes for better search performance"""
            # Check if indexes exist
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_projects_name'"
            )
            if cursor.fetchone():
                logger.info("  └─ Search indexes already exist, skipping")
                return

            conn.execute('CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_projects_directory ON projects(directory)')
            logger.info("  └─ Created search optimization indexes")

        self.migrations.append(Migration(
            version=2,
            name="add_search_indexes",
            up=migration_002_up
        ))

        # Migration 3: Add template metadata (v3)
        def migration_003_up(conn):
            """Add column to track project templates"""
            # Check if column exists
            cursor = conn.execute('PRAGMA table_info(projects)')
            columns = [row[1] for row in cursor.fetchall()]

            if 'template_used' not in columns:
                conn.execute('ALTER TABLE projects ADD COLUMN template_used TEXT')
                logger.info("  └─ Added template_used column to projects")
            else:
                logger.info("  └─ template_used column already exists, skipping")

        self.migrations.append(Migration(
            version=3,
            name="add_template_metadata",
            up=migration_003_up
        ))

    def migrate_to_latest(self) -> bool:
        """
        Apply all pending migrations to bring database to latest version

        Returns:
            True if successful, False otherwise
        """
        current_version = self.get_current_version()
        logger.info(f"📊 Current database version: {current_version}")

        pending_migrations = [m for m in self.migrations if m.version > current_version]

        if not pending_migrations:
            logger.info("✅ Database is up to date")
            return True

        logger.info(f"🔄 Applying {len(pending_migrations)} migration(s)...\n")

        try:
            with self._get_connection() as conn:
                for migration in pending_migrations:
                    logger.info(f"Applying migration {migration.version}: {migration.name}")

                    # Apply the migration
                    migration.up(conn)

                    # Record migration
                    conn.execute(
                        'INSERT INTO schema_migrations (version, name) VALUES (?, ?)',
                        (migration.version, migration.name)
                    )

                    conn.commit()
                    logger.info(f"✅ Migration {migration.version} applied successfully\n")

            new_version = self.get_current_version()
            logger.info(f"🎉 Database migrated to version {new_version}")
            return True

        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            return False

    def rollback_migration(self, target_version: int) -> bool:
        """
        Rollback to a specific version (if rollback functions are defined)

        Args:
            target_version: Version to rollback to

        Returns:
            True if successful, False otherwise
        """
        current_version = self.get_current_version()

        if target_version >= current_version:
            logger.warning(f"Already at version {current_version}, no rollback needed")
            return True

        migrations_to_rollback = [
            m for m in reversed(self.migrations)
            if current_version >= m.version > target_version
        ]

        if not migrations_to_rollback:
            logger.warning("No migrations to rollback")
            return True

        logger.info(f"🔄 Rolling back {len(migrations_to_rollback)} migration(s)...\n")

        try:
            with self._get_connection() as conn:
                for migration in migrations_to_rollback:
                    if not migration.down:
                        logger.error(f"❌ Migration {migration.version} has no rollback function")
                        return False

                    logger.info(f"Rolling back migration {migration.version}: {migration.name}")

                    # Rollback the migration
                    migration.down(conn)

                    # Remove migration record
                    conn.execute(
                        'DELETE FROM schema_migrations WHERE version = ?',
                        (migration.version,)
                    )

                    conn.commit()
                    logger.info(f"✅ Migration {migration.version} rolled back\n")

            new_version = self.get_current_version()
            logger.info(f"🎉 Database rolled back to version {new_version}")
            return True

        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False

    def get_migration_status(self) -> List[dict]:
        """
        Get status of all migrations

        Returns:
            List of migration status dictionaries
        """
        current_version = self.get_current_version()

        status = []
        for migration in self.migrations:
            status.append({
                'version': migration.version,
                'name': migration.name,
                'applied': migration.version <= current_version,
                'has_rollback': migration.down is not None
            })

        return status


def auto_migrate(db_path: str) -> bool:
    """
    Automatically run migrations on database initialization

    Args:
        db_path: Path to database file

    Returns:
        True if successful
    """
    manager = MigrationManager(db_path)
    return manager.migrate_to_latest()
