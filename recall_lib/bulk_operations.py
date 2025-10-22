#!/usr/bin/env python3
"""
Bulk Operations - Perform actions on multiple projects simultaneously

Supports:
- Bulk tagging
- Bulk analysis
- Bulk git operations
- Bulk export/import
- Query-based selection
"""
from typing import List, Dict, Callable, Optional
from .logger import get_logger
from .project_memory import ProjectMemory

logger = get_logger(__name__)


class BulkOperations:
    """
    Manage bulk operations on multiple projects
    """

    def __init__(self, memory: ProjectMemory = None):
        """
        Initialize bulk operations

        Args:
            memory: ProjectMemory instance
        """
        self.memory = memory or ProjectMemory()

    def select_projects(
        self,
        tags: List[str] = None,
        name_pattern: str = None,
        directory_pattern: str = None,
        limit: int = None
    ) -> List[Dict]:
        """
        Select projects based on criteria

        Args:
            tags: Filter by tags (projects must have ALL tags)
            name_pattern: Filter by name (case-insensitive substring match)
            directory_pattern: Filter by directory path (case-insensitive substring match)
            limit: Maximum number of projects to return

        Returns:
            List of matching project dicts
        """
        all_projects = self.memory.list_all_projects()
        selected = []

        for project in all_projects:
            # Filter by tags
            if tags:
                project_tags = self.memory.get_tags(project['name'])
                if not all(tag in project_tags for tag in tags):
                    continue

            # Filter by name pattern
            if name_pattern:
                if name_pattern.lower() not in project['name'].lower():
                    continue

            # Filter by directory pattern
            if directory_pattern:
                project_dir = project.get('directory', '')
                if directory_pattern.lower() not in project_dir.lower():
                    continue

            selected.append(project)

            # Check limit
            if limit and len(selected) >= limit:
                break

        return selected

    def bulk_add_tag(self, projects: List[Dict], tag: str) -> Dict[str, int]:
        """
        Add a tag to multiple projects

        Args:
            projects: List of project dicts
            tag: Tag to add

        Returns:
            Dict with 'success' and 'failed' counts
        """
        results = {'success': 0, 'failed': 0}

        for project in projects:
            try:
                self.memory.add_tag(project['name'], tag)
                results['success'] += 1
            except Exception as e:
                logger.error(f"Failed to add tag to '{project['name']}': {e}")
                results['failed'] += 1

        logger.info(f"✅ Added tag '{tag}' to {results['success']} project(s)")
        if results['failed'] > 0:
            logger.warning(f"⚠️ Failed for {results['failed']} project(s)")

        return results

    def bulk_remove_tag(self, projects: List[Dict], tag: str) -> Dict[str, int]:
        """
        Remove a tag from multiple projects

        Args:
            projects: List of project dicts
            tag: Tag to remove

        Returns:
            Dict with 'success' and 'failed' counts
        """
        results = {'success': 0, 'failed': 0}

        for project in projects:
            try:
                self.memory.remove_tag(project['name'], tag)
                results['success'] += 1
            except Exception as e:
                logger.error(f"Failed to remove tag from '{project['name']}': {e}")
                results['failed'] += 1

        logger.info(f"✅ Removed tag '{tag}' from {results['success']} project(s)")
        if results['failed'] > 0:
            logger.warning(f"⚠️ Failed for {results['failed']} project(s)")

        return results

    def bulk_analyze(self, projects: List[Dict], show_progress: bool = True) -> Dict[str, int]:
        """
        Analyze multiple projects

        Args:
            projects: List of project dicts
            show_progress: Show progress indicator

        Returns:
            Dict with 'success' and 'failed' counts
        """
        from .auto_analyzer import AutoAnalyzer

        results = {'success': 0, 'failed': 0}

        if show_progress:
            from rich.progress import Progress, SpinnerColumn, TextColumn

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=False,
            ) as progress:
                task = progress.add_task(f"Analyzing {len(projects)} projects...", total=len(projects))

                for project in projects:
                    project_dir = project.get('directory')
                    if not project_dir:
                        results['failed'] += 1
                        progress.advance(task)
                        continue

                    progress.update(task, description=f"Analyzing '{project['name']}'...")

                    try:
                        analyzer = AutoAnalyzer(project_dir, project['name'], self.memory)
                        analyzer.analyze(show_progress=False)
                        results['success'] += 1
                    except Exception as e:
                        logger.error(f"Failed to analyze '{project['name']}': {e}")
                        results['failed'] += 1

                    progress.advance(task)

        else:
            for project in projects:
                project_dir = project.get('directory')
                if not project_dir:
                    results['failed'] += 1
                    continue

                try:
                    analyzer = AutoAnalyzer(project_dir, project['name'], self.memory)
                    analyzer.analyze(show_progress=False)
                    results['success'] += 1
                except Exception as e:
                    logger.error(f"Failed to analyze '{project['name']}': {e}")
                    results['failed'] += 1

        logger.info(f"✅ Analyzed {results['success']} project(s)")
        if results['failed'] > 0:
            logger.warning(f"⚠️ Failed for {results['failed']} project(s)")

        return results

    def bulk_git_log(self, projects: List[Dict], days_back: int = 7, smart_mode: bool = True) -> Dict[str, int]:
        """
        Auto-log git commits for multiple projects

        Args:
            projects: List of project dicts
            days_back: Days back to scan for commits
            smart_mode: Use smart commit analysis

        Returns:
            Dict with 'success' and 'failed' counts
        """
        from .git_logger import auto_log_from_git

        results = {'success': 0, 'failed': 0}

        for project in projects:
            try:
                success = auto_log_from_git(project['name'], days_back, smart_mode)
                if success:
                    results['success'] += 1
                else:
                    results['failed'] += 1
            except Exception as e:
                logger.error(f"Failed git log for '{project['name']}': {e}")
                results['failed'] += 1

        logger.info(f"✅ Git-logged {results['success']} project(s)")
        if results['failed'] > 0:
            logger.warning(f"⚠️ Failed for {results['failed']} project(s)")

        return results

    def bulk_apply_function(
        self,
        projects: List[Dict],
        function: Callable[[Dict], bool],
        description: str = "Processing"
    ) -> Dict[str, int]:
        """
        Apply a custom function to multiple projects

        Args:
            projects: List of project dicts
            function: Function to apply (takes project dict, returns bool for success)
            description: Description for progress indicator

        Returns:
            Dict with 'success' and 'failed' counts
        """
        results = {'success': 0, 'failed': 0}

        for project in projects:
            try:
                success = function(project)
                if success:
                    results['success'] += 1
                else:
                    results['failed'] += 1
            except Exception as e:
                logger.error(f"Failed for '{project['name']}': {e}")
                results['failed'] += 1

        logger.info(f"✅ {description}: {results['success']} success, {results['failed']} failed")

        return results

    def bulk_update_context(
        self,
        projects: List[Dict],
        category: str,
        key: str,
        value: str
    ) -> Dict[str, int]:
        """
        Update context for multiple projects

        Args:
            projects: List of project dicts
            category: Context category
            key: Context key
            value: Context value

        Returns:
            Dict with 'success' and 'failed' counts
        """
        results = {'success': 0, 'failed': 0}

        for project in projects:
            try:
                self.memory.db.set_context(project['id'], category, key, value)
                results['success'] += 1
            except Exception as e:
                logger.error(f"Failed to update context for '{project['name']}': {e}")
                results['failed'] += 1

        logger.info(f"✅ Updated context for {results['success']} project(s)")
        if results['failed'] > 0:
            logger.warning(f"⚠️ Failed for {results['failed']} project(s)")

        return results

    def bulk_export(self, projects: List[Dict], output_file: str) -> bool:
        """
        Export multiple projects to JSON file

        Args:
            projects: List of project dicts
            output_file: Output file path

        Returns:
            True if successful, False otherwise
        """
        import json

        # Build export data
        export_data = {
            'version': '1.0',
            'exported_at': self.memory._get_timestamp(),
            'projects': []
        }

        for project in projects:
            # Get full project data
            project_data = {
                'name': project['name'],
                'description': project.get('description'),
                'directory': project.get('directory'),
                'context': self.memory.get_context(project['name']),
                'sessions': self.memory.db.get_recent_sessions(project['id'], limit=100),
                'tags': self.memory.get_tags(project['name'])
            }

            export_data['projects'].append(project_data)

        # Write to file
        try:
            with open(output_file, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)

            logger.info(f"✅ Exported {len(projects)} project(s) to {output_file}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to export: {e}")
            return False

    def get_summary(self, projects: List[Dict]) -> Dict:
        """
        Get summary statistics for a set of projects

        Args:
            projects: List of project dicts

        Returns:
            Dict with summary statistics
        """
        total_sessions = 0
        all_tags = set()

        for project in projects:
            sessions = self.memory.db.get_recent_sessions(project['id'], limit=1000)
            total_sessions += len(sessions)

            tags = self.memory.get_tags(project['name'])
            all_tags.update(tags)

        return {
            'total_projects': len(projects),
            'total_sessions': total_sessions,
            'unique_tags': len(all_tags),
            'avg_sessions_per_project': total_sessions / len(projects) if projects else 0
        }
