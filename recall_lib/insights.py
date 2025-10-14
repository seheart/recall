#!/usr/bin/env python3
"""
Cross-Project Insights for Recall
Analyze patterns and trends across all projects
"""
from datetime import datetime, timedelta
from typing import Dict, List
from collections import Counter
from .database import RecallDatabase


class InsightsGenerator:
    """Generate insights across all projects"""

    def __init__(self, db: RecallDatabase):
        self.db = db

    def get_project_activity(self, days: int = 7) -> Dict:
        """Get project activity summary for last N days"""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        with self.db.get_connection() as conn:
            # Projects with recent activity
            cursor = conn.execute('''
                SELECT name, updated_at FROM projects
                WHERE updated_at >= ?
                ORDER BY updated_at DESC
            ''', (cutoff_date,))
            active_projects = [dict(row) for row in cursor.fetchall()]

            # Projects without recent activity
            cursor = conn.execute('''
                SELECT name, updated_at FROM projects
                WHERE updated_at < ?
                ORDER BY updated_at DESC
            ''', (cutoff_date,))
            stale_projects = [dict(row) for row in cursor.fetchall()]

            # Total session count in period
            cursor = conn.execute('''
                SELECT COUNT(*) as count FROM sessions
                WHERE created_at >= ?
            ''', (cutoff_date,))
            session_count = cursor.fetchone()['count']

            return {
                'active_projects': active_projects,
                'stale_projects': stale_projects,
                'session_count': session_count,
                'days': days
            }

    def get_tech_stack_summary(self) -> Dict:
        """Analyze technology usage across projects"""
        with self.db.get_connection() as conn:
            # Get all tech stacks
            cursor = conn.execute('''
                SELECT p.name, c.value FROM project_context c
                JOIN projects p ON c.project_id = p.id
                WHERE c.category = 'architecture' AND c.key IN ('stack', 'language', 'framework')
                ORDER BY p.name
            ''')

            tech_by_project = {}
            all_tech = []

            for row in cursor.fetchall():
                project_name = row['name']
                tech = row['value']

                if project_name not in tech_by_project:
                    tech_by_project[project_name] = []

                tech_by_project[project_name].append(tech)
                all_tech.append(tech.lower())

            # Count popular technologies
            tech_counter = Counter(all_tech)

            return {
                'projects_by_tech': tech_by_project,
                'popular_tech': tech_counter.most_common(10),
                'total_projects': len(tech_by_project)
            }

    def get_project_statistics(self) -> Dict:
        """Get overall project statistics"""
        with self.db.get_connection() as conn:
            # Total projects
            cursor = conn.execute('SELECT COUNT(*) as count FROM projects')
            total_projects = cursor.fetchone()['count']

            # Projects by status
            cursor = conn.execute('''
                SELECT c.value, COUNT(*) as count
                FROM project_context c
                WHERE c.category = 'state' AND c.key = 'status'
                GROUP BY c.value
                ORDER BY count DESC
            ''')
            by_status = dict(cursor.fetchall())

            # Most active project (by session count)
            cursor = conn.execute('''
                SELECT p.name, COUNT(s.id) as session_count
                FROM projects p
                LEFT JOIN sessions s ON p.id = s.project_id
                GROUP BY p.id
                ORDER BY session_count DESC
                LIMIT 1
            ''')
            most_active_row = cursor.fetchone()
            most_active = dict(most_active_row) if most_active_row else None

            # Newest project
            cursor = conn.execute('''
                SELECT name, created_at FROM projects
                ORDER BY created_at DESC
                LIMIT 1
            ''')
            newest_row = cursor.fetchone()
            newest = dict(newest_row) if newest_row else None

            return {
                'total_projects': total_projects,
                'by_status': by_status,
                'most_active': most_active,
                'newest': newest
            }

    def generate_insights_report(self, days: int = 7) -> str:
        """Generate a comprehensive insights report"""
        report = []
        report.append("=" * 60)
        report.append("📊 RECALL INSIGHTS - Cross-Project Analysis")
        report.append("=" * 60)
        report.append("")

        # Overall statistics
        stats = self.get_project_statistics()
        report.append(f"📚 Total Projects: {stats['total_projects']}")

        if stats['by_status']:
            report.append("\n🎯 Projects by Status:")
            for status, count in stats['by_status'].items():
                report.append(f"  • {status}: {count}")

        if stats['most_active']:
            report.append(f"\n🔥 Most Active: {stats['most_active']['name']} " +
                         f"({stats['most_active']['session_count']} sessions)")

        if stats['newest']:
            created_date = stats['newest']['created_at'][:10]
            report.append(f"\n🆕 Newest Project: {stats['newest']['name']} (created {created_date})")

        # Recent activity
        activity = self.get_project_activity(days)
        report.append(f"\n📅 Activity (Last {days} Days):")
        report.append(f"  • Active projects: {len(activity['active_projects'])}")
        report.append(f"  • Work sessions: {activity['session_count']}")

        if activity['active_projects']:
            report.append(f"\n✅ Recently Active:")
            for proj in activity['active_projects'][:5]:  # Show top 5
                updated = proj['updated_at'][:10]
                report.append(f"  • {proj['name']} (updated {updated})")

        if activity['stale_projects']:
            report.append(f"\n⚠️ Needs Attention ({len(activity['stale_projects'])} projects):")
            for proj in activity['stale_projects'][:3]:  # Show top 3
                updated = proj['updated_at'][:10]
                report.append(f"  • {proj['name']} (last updated {updated})")

        # Tech stack analysis
        tech_summary = self.get_tech_stack_summary()
        if tech_summary['popular_tech']:
            report.append(f"\n🛠️ Technology Trends:")
            for tech, count in tech_summary['popular_tech'][:5]:
                report.append(f"  • {tech.title()}: {count} project(s)")

        report.append("")
        report.append("=" * 60)
        report.append("💡 Use 'recall --list' to see all projects")
        report.append("💡 Use 'recall <project> --status' for project details")
        report.append("=" * 60)

        return "\n".join(report)


if __name__ == "__main__":
    # Test the insights generator
    print("📊 Testing Insights Generator...")

    db = RecallDatabase()
    insights = InsightsGenerator(db)

    # Generate report
    report = insights.generate_insights_report(days=30)
    print("\n" + report)

    print("\n✅ Insights generator test complete!")
