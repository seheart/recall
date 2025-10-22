#!/usr/bin/env python3
"""
Backup Manager for Recall - Export/Import project memories
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List
from .database import RecallDatabase

from .logger import get_logger

# Initialize logger
logger = get_logger(__name__)


class BackupManager:
    """Manages export and import of project memories"""

    def __init__(self, db: RecallDatabase):
        self.db = db

    def export_to_json(self, output_file: str, include_sessions: bool = True) -> bool:
        """
        Export all project data to JSON file

        Args:
            output_file: Path to output JSON file
            include_sessions: Whether to include session history (can be large)

        Returns:
            True if export succeeded
        """
        try:
            with self.db.get_connection() as conn:
                # Get all projects
                projects = []
                cursor = conn.execute("SELECT * FROM projects ORDER BY name")

                for project_row in cursor.fetchall():
                    project = dict(project_row)
                    project_id = project["id"]

                    # Get context for this project
                    context_cursor = conn.execute(
                        "SELECT category, key, value FROM project_context WHERE project_id = ?",
                        (project_id,),
                    )
                    context = {}
                    for ctx_row in context_cursor.fetchall():
                        cat, key, value = ctx_row
                        if cat not in context:
                            context[cat] = {}
                        context[cat][key] = value

                    project["context"] = context

                    # Optionally include sessions
                    if include_sessions:
                        session_cursor = conn.execute(
                            "SELECT * FROM sessions WHERE project_id = ? ORDER BY created_at DESC",
                            (project_id,),
                        )
                        project["sessions"] = [dict(row) for row in session_cursor.fetchall()]

                    projects.append(project)

                # Create backup data structure
                backup_data = {
                    "version": "1.0",
                    "exported_at": datetime.now().isoformat(),
                    "project_count": len(projects),
                    "projects": projects,
                }

                # Write to file
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)

                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(backup_data, f, indent=2, ensure_ascii=False)

                logger.info(f"✅ Exported {len(projects)} project(s) to {output_file}")
                logger.info(f"📊 Backup size: {output_path.stat().st_size / 1024:.1f} KB")
                return True

        except Exception as e:
            logger.error(f"❌ Export failed: {e}")
            return False

    def import_from_json(self, input_file: str, merge: bool = False) -> bool:
        """
        Import project data from JSON file

        Args:
            input_file: Path to input JSON file
            merge: If True, merge with existing data. If False, skip existing projects.

        Returns:
            True if import succeeded
        """
        try:
            # Read backup file
            with open(input_file, "r", encoding="utf-8") as f:
                backup_data = json.load(f)

            if backup_data.get("version") != "1.0":
                logger.warning(f"⚠️ Warning: Unknown backup version {backup_data.get('version')}")

            projects = backup_data.get("projects", [])

            if not projects:
                logger.error("❌ No projects found in backup file")
                return False

            imported_count = 0
            skipped_count = 0
            updated_count = 0

            for project_data in projects:
                name = project_data["name"]

                # Check if project exists
                existing = self.db.get_project(name)

                if existing and not merge:
                    logger.info(f"⏭️ Skipping existing project: {name}")
                    skipped_count += 1
                    continue

                with self.db.get_connection() as conn:
                    if existing:
                        # Update existing project
                        project_id = existing["id"]
                        conn.execute(
                            """
                            UPDATE projects
                            SET description = ?, directory = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """,
                            (
                                project_data.get("description"),
                                project_data.get("directory"),
                                project_id,
                            ),
                        )
                        logger.info(f"🔄 Updated project: {name}")
                        updated_count += 1
                    else:
                        # Create new project
                        cursor = conn.execute(
                            """
                            INSERT INTO projects (name, description, directory, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?)
                        """,
                            (
                                name,
                                project_data.get("description"),
                                project_data.get("directory"),
                                project_data.get("created_at", datetime.now().isoformat()),
                                project_data.get("updated_at", datetime.now().isoformat()),
                            ),
                        )
                        project_id = cursor.lastrowid
                        logger.info(f"✅ Imported project: {name}")
                        imported_count += 1

                    # Import context
                    context = project_data.get("context", {})
                    for category, items in context.items():
                        for key, value in items.items():
                            conn.execute(
                                """
                                INSERT OR REPLACE INTO project_context
                                (project_id, category, key, value, updated_at)
                                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                            """,
                                (project_id, category, key, value),
                            )

                    # Import sessions if present
                    sessions = project_data.get("sessions", [])
                    for session in sessions:
                        conn.execute(
                            """
                            INSERT INTO sessions
                            (project_id, summary, accomplishments, decisions_made, next_steps, files_changed, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                project_id,
                                session.get("summary"),
                                session.get("accomplishments"),
                                session.get("decisions_made"),
                                session.get("next_steps"),
                                session.get("files_changed"),
                                session.get("created_at", datetime.now().isoformat()),
                            ),
                        )

                    conn.commit()

            logger.info(f"\n📊 Import complete:")
            if imported_count > 0:
                logger.info(f"  ✅ Imported: {imported_count} new project(s)")
            if updated_count > 0:
                logger.info(f"  🔄 Updated: {updated_count} existing project(s)")
            if skipped_count > 0:
                logger.info(
                    f"  ⏭️ Skipped: {skipped_count} existing project(s) (use --merge to update)"
                )

            return True

        except FileNotFoundError:
            logger.error(f"❌ Backup file not found: {input_file}")
            return False
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in backup file: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Import failed: {e}")
            return False


if __name__ == "__main__":
    # Test the backup manager
    logger.info("🗄️ Testing Backup Manager...")

    db = RecallDatabase()
    backup = BackupManager(db)

    # Test export
    logger.info("\n📤 Testing export...")
    backup.export_to_json("test_backup.json")

    logger.info("\n✅ Backup manager test complete!")
    logger.info("💡 Use 'recall --export backup.json' to export your projects")
    logger.info("💡 Use 'recall --import backup.json' to restore from backup")
