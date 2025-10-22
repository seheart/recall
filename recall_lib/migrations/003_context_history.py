#!/usr/bin/env python3
"""
Migration 003: Add context history tracking

This migration adds a context_history table to track all changes to project context over time.
Enables viewing history, diffs, and rollback functionality.
"""

def upgrade(conn):
    """Add context_history table"""
    # Create context history table
    conn.execute('''
        CREATE TABLE IF NOT EXISTS context_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT,
            old_value TEXT,
            operation TEXT NOT NULL,  -- 'create', 'update', 'delete'
            version INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        )
    ''')

    # Create indexes for performance
    conn.execute('CREATE INDEX IF NOT EXISTS idx_history_project ON context_history(project_id)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_history_version ON context_history(project_id, version)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_history_key ON context_history(project_id, category, key)')

    # Create metadata table to track version numbers per project
    conn.execute('''
        CREATE TABLE IF NOT EXISTS project_metadata (
            project_id INTEGER PRIMARY KEY,
            current_version INTEGER DEFAULT 0,
            last_snapshot_at TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects (id) ON DELETE CASCADE
        )
    ''')

    conn.commit()


def downgrade(conn):
    """Remove context_history table"""
    conn.execute('DROP TABLE IF EXISTS context_history')
    conn.execute('DROP TABLE IF EXISTS project_metadata')
    conn.execute('DROP INDEX IF EXISTS idx_history_project')
    conn.execute('DROP INDEX IF EXISTS idx_history_version')
    conn.execute('DROP INDEX IF EXISTS idx_history_key')
    conn.commit()


# Migration metadata
MIGRATION_ID = 3
DESCRIPTION = "Add context history tracking for versioning and rollback"
