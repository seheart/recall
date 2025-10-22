#!/usr/bin/env python3
"""
Recall - Project Memory System for Claude Code

Usage:
    recall project-name          # Load project context
    recall project-name --create # Create new project
    recall --list               # List all projects
    recall --status project     # Show project status
"""
import sys
import os
import argparse
from pathlib import Path
from recall_lib.project_memory import ProjectMemory
from recall_lib.access_verifier import AccessVerifier
from recall_lib.logger import get_logger
from recall_lib.rich_output import rich_output
from recall_lib.__version__ import __version__

# Initialize logger
logger = get_logger(__name__)


def create_new_project(memory: ProjectMemory, name: str, interactive: bool = True):
    """Create a new project with optional interactive setup"""
    if memory.project_exists(name):
        logger.error(f"❌ Project '{name}' already exists")
        return False

    logger.info(f"🆕 Creating new project: {name}")

    # Get current directory as default
    current_dir = os.getcwd()
    description = None
    directory = current_dir

    if interactive:
        # Interactive setup
        logger.info(f"\nProject Setup for '{name}':")
        desc_input = input("Description (optional): ").strip()
        if desc_input:
            description = desc_input

        dir_input = input(f"Directory [{current_dir}]: ").strip()
        if dir_input:
            directory = dir_input

        # Architecture questions
        logger.info("\n🏗️ Architecture Information (optional, press Enter to skip):")
        stack = input("Tech stack (e.g., 'React + Node.js + PostgreSQL'): ").strip()
        language = input("Primary language: ").strip()
        framework = input("Framework/library: ").strip()

        # Build initial context
        initial_context = {}
        if stack or language or framework:
            arch = {}
            if stack:
                arch['stack'] = stack
            if language:
                arch['language'] = language
            if framework:
                arch['framework'] = framework
            initial_context['architecture'] = arch

        # Current state
        status = input("Current status (e.g., 'Planning', 'In development'): ").strip()
        if status:
            initial_context['state'] = {'status': status}

    else:
        # Non-interactive - just basic setup
        initial_context = {
            'state': {'status': 'Initialized', 'created_via': 'recall command'}
        }

    try:
        project_id = memory.create_project(name, description, directory, initial_context)
        logger.info(f"✅ Created project '{name}' (ID: {project_id})")
        logger.info(f"📁 Directory: {directory}")
        if description:
            logger.info(f"📝 Description: {description}")

        # Automatically analyze and populate context
        logger.info(f"\n🔍 Analyzing project...")
        from recall_lib.auto_analyzer import auto_populate_recall
        try:
            auto_populate_recall(name, directory)
        except Exception as e:
            logger.warning(f"⚠️  Auto-analysis failed: {e}")

        # Automatically import git history if it's a git repo
        if os.path.exists(os.path.join(directory, '.git')):
            logger.info(f"\n📚 Importing git history...")
            from recall_lib.git_logger import auto_log_from_git
            try:
                auto_log_from_git(name, days_back=30)
            except Exception as e:
                logger.warning(f"⚠️  Git history import failed: {e}")

        logger.info(f"\n🎉 Project '{name}' is ready!")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to create project: {e}")
        return False


def load_project_context(memory: ProjectMemory, name: str, verify_access: bool = True):
    """Load and display project context with access verification"""
    from recall_lib.fuzzy_match import suggest_project

    if not memory.project_exists(name):
        logger.error(f"❌ Project '{name}' not found")

        # Try to detect from current directory
        detected = memory.detect_project_from_directory()
        if detected:
            logger.info(f"💡 Found project '{detected}' for current directory")
            choice = input(f"Load '{detected}' instead? (y/n): ").strip().lower()
            if choice == 'y':
                name = detected
            else:
                return False
        else:
            # Show fuzzy match suggestions
            suggestion = suggest_project(name, memory)
            if suggestion:
                logger.info(suggestion)
            return False

    # Load context
    logger.info(f"🧠 Loading project memory: {name}")

    # Verify development access if requested
    if verify_access:
        verifier = AccessVerifier()
        access_results = verifier.verify_all()
        logger.info("")  # Add some space after verification output

    # Check if project context needs refreshing
    from datetime import datetime, timedelta
    project = memory.db.get_project(name)
    if project and project.get('directory') and os.path.exists(project['directory']):
        updated_at = project.get('updated_at')
        if updated_at:
            try:
                updated_time = datetime.fromisoformat(updated_at.replace(' ', 'T'))
                age = datetime.now() - updated_time
                # Refresh if data is older than 1 day
                if age > timedelta(days=1):
                    logger.info(f"🔄 Refreshing project context (last updated {age.days} day(s) ago)...")
                    from recall_lib.auto_analyzer import auto_populate_recall
                    try:
                        auto_populate_recall(name, project['directory'])
                    except Exception as e:
                        logger.debug(f"Context refresh failed: {e}")
            except (ValueError, TypeError):
                pass

    # Get project and context
    project_context = memory.get_project_context(name)

    if project_context:
        project = project_context['project']
        context = project_context['context']
        sessions = project_context['recent_sessions']
        # Try to enrich context if project has a directory
        enriched = {}
        project_dir = project.get('directory')

        if project_dir and os.path.exists(project_dir):
            try:
                from recall_lib.context_enrichment import ContextEnricher
                enricher = ContextEnricher(project_dir, project, memory)
                enriched = enricher.enrich_all()
                logger.info("✨ Enhanced context with auto-discovered information")
            except Exception as e:
                logger.debug(f"Context enrichment failed: {e}")

        # Display enriched context (or fall back to standard if enrichment failed)
        if enriched:
            rich_output.print_enriched_context(project, context, enriched, sessions)
        else:
            # Fallback to original format
            formatted = memory.format_for_claude(name)
            logger.info("\n" + formatted)

        # Show access summary
        if verify_access:
            logger.info("\n" + "="*60)
            logger.info("🔧 DEVELOPMENT ENVIRONMENT STATUS:")
            logger.info(verifier.get_summary_status())
            logger.info("="*60)

        logger.info(f"\n🎯 Project '{name}' context loaded successfully!")

        if verify_access and all(access_results.values()):
            logger.info("🚀 Claude Code has full development access - ready for work!")
        elif verify_access:
            logger.warning("⚠️ Some access issues detected - development capabilities may be limited")

        logger.info("\n💡 This comprehensive context is ready to provide to Claude Code")

        return True
    else:
        logger.error(f"❌ Failed to load context for project '{name}'")
        return False


def list_projects(memory: ProjectMemory):
    """List all projects with tags (using Rich output when available)"""
    projects = memory.list_all_projects()

    if not projects:
        rich_output.print_info("No projects found")
        logger.info("💡 Create your first project with: recall my-project --create")
        return

    # Get tags for all projects
    tags_dict = {}
    for project in projects:
        tags_dict[project['name']] = memory.get_tags(project['name'])

    # Use Rich output (or fallback)
    rich_output.print_project_list(projects, tags_dict)


def search_projects(memory: ProjectMemory, query: str):
    """Search for projects matching the query"""
    projects = memory.search_projects(query)

    if not projects:
        logger.info(f"🔍 No projects found matching '{query}'")
        logger.info("💡 Try a different search term or use 'recall --list' to see all projects")
        return

    logger.info(f"🔍 Found {len(projects)} project(s) matching '{query}':\n")

    for project in projects:
        logger.info(f"• {project['name']}")
        if project.get('description'):
            logger.info(f"  └─ {project['description']}")
        logger.info(f"  └─ Updated: {project['updated_at'][:19]}")
        if project.get('directory'):
            logger.info(f"  └─ Directory: {project['directory']}")
        logger.info("")


def show_project_status(memory: ProjectMemory, name: str):
    """Show detailed status for a project (using Rich output when available)"""
    context = memory.get_project_context(name)
    if not context:
        rich_output.print_error(f"Project '{name}' not found")
        return False

    project = context['project']
    ctx = context['context']
    sessions = context['recent_sessions']

    # Use Rich output (or fallback)
    rich_output.print_project_status(project, ctx, sessions)

    return True


def main():
    """Main entry point for recall command"""
    parser = argparse.ArgumentParser(
        description="Recall - Project Memory System for Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  recall my-api                    Load my-api project context (with verification)
  recall my-api --create          Create new project
  recall my-api --create --template api-server  Create project from template
  recall --list-templates         Show all available project templates
  recall --list                   List all projects
  recall --search "api"           Search for projects by name, description, or directory
  recall my-api --status          Show project status
  recall my-api --analyze         Auto-analyze project and populate context
  recall my-api --git-log         Auto-log sessions from git commits
  recall my-api --git-log --days 30   Log from last 30 days
  recall --verify-only            Check GitHub/server access only
  recall my-api --no-verify       Load context without access verification

  TAG MANAGEMENT:
  recall my-api --add-tag "web"   Add a tag to a project
  recall my-api --remove-tag "web" Remove a tag from a project
  recall my-api --tags            Show all tags for a project
  recall --list-tags              List all tags with project counts
  recall --tag "web"              List all projects with a specific tag

  BACKUP & INSIGHTS:
  recall --export backup.json     Export all projects to JSON backup file
  recall --import backup.json     Import projects from backup (skip existing)
  recall --import backup.json --merge  Import and merge with existing projects
  recall --insights               Show cross-project analytics and trends
  recall --insights --days 30     Show insights for last 30 days
  recall my-api --install-hook    Install git post-commit hook for auto-updates
        """
    )

    parser.add_argument('project', nargs='?', help='Project name')
    parser.add_argument('--create', action='store_true', help='Create new project')
    parser.add_argument('--template', type=str, metavar='TEMPLATE', help='Use a project template (use with --create)')
    parser.add_argument('--list-templates', action='store_true', help='List all available project templates')
    parser.add_argument('--list', action='store_true', help='List all projects')
    parser.add_argument('--search', type=str, metavar='QUERY', help='Search projects by name, description, or directory')
    parser.add_argument('--status', action='store_true', help='Show project status')
    parser.add_argument('--add-tag', type=str, metavar='TAG', help='Add a tag to the project')
    parser.add_argument('--remove-tag', type=str, metavar='TAG', help='Remove a tag from the project')
    parser.add_argument('--tags', action='store_true', help='Show tags for the project')
    parser.add_argument('--list-tags', action='store_true', help='List all tags with counts')
    parser.add_argument('--tag', type=str, metavar='TAG', help='List projects with a specific tag')
    parser.add_argument('--non-interactive', action='store_true', help='Non-interactive mode')
    parser.add_argument('--no-verify', action='store_true', help='Skip access verification')
    parser.add_argument('--verify-only', action='store_true', help='Only run access verification')
    parser.add_argument('--analyze', action='store_true', help='Auto-analyze project and populate context')
    parser.add_argument('--git-log', action='store_true', help='Auto-log sessions from git commits')
    parser.add_argument('--days', type=int, default=7, help='Days back for git log (default: 7)')
    parser.add_argument('--claude', action='store_true', help='Load project context (alias for default behavior)')
    parser.add_argument('--export', type=str, metavar='FILE', help='Export all projects to JSON file')
    parser.add_argument('--import', type=str, metavar='FILE', dest='import_file', help='Import projects from JSON file')
    parser.add_argument('--merge', action='store_true', help='Merge imported data with existing (use with --import)')
    parser.add_argument('--insights', action='store_true', help='Show cross-project insights and analytics')
    parser.add_argument('--install-hook', action='store_true', help='Install git post-commit hook for auto-updates')
    parser.add_argument('--smart', action='store_true', help='Enable smart mode for git hook (auto-analyze on each commit)')
    parser.add_argument('--quiet', action='store_true', help='Suppress git hook output')
    parser.add_argument('--migrate', action='store_true', help='Run database migrations and show status')
    parser.add_argument('--migration-status', action='store_true', help='Show current migration status')
    parser.add_argument('--dashboard', action='store_true', help='Start the live Flask dashboard server')
    parser.add_argument('--config', action='store_true', help='Show current configuration')
    parser.add_argument('--config-init', action='store_true', help='Create default configuration file')
    parser.add_argument('--config-edit', action='store_true', help='Open configuration file in editor')
    parser.add_argument('--history', action='store_true', help='Show context change history')
    parser.add_argument('--history-limit', type=int, default=20, metavar='N', help='Number of history entries to show (default: 20)')
    parser.add_argument('--diff', action='store_true', help='Show differences between context versions')
    parser.add_argument('--diff-versions', type=str, metavar='V1:V2', help='Compare specific versions (e.g., --diff-versions 5:10)')
    parser.add_argument('--rollback', type=int, metavar='VERSION', help='Rollback context to a specific version')
    parser.add_argument('--yes', action='store_true', help='Skip confirmation prompts')
    parser.add_argument('--plugins', action='store_true', help='List loaded plugins')
    parser.add_argument('--plugin-command', type=str, metavar='PLUGIN:CMD', help='Execute plugin command (e.g., example:stats)')
    parser.add_argument('--version', action='version', version=f'Recall v{__version__}')

    args = parser.parse_args()

    # Initialize memory system
    try:
        memory = ProjectMemory()
    except Exception as e:
        logger.error(f"❌ Failed to initialize memory system: {e}")
        return 1

    # Initialize plugin system
    from recall_lib.config import get_config
    from recall_lib.plugin_manager import get_plugin_manager

    config = get_config()
    plugin_manager = get_plugin_manager(config.config)

    # Load plugins if configured
    if config.config.get('plugins') or config.config.get('plugin_dir'):
        try:
            plugin_manager.load_all_plugins()
        except Exception as e:
            logger.warning(f"⚠️ Plugin initialization failed: {e}")

    # Handle different commands
    if args.migrate or args.migration_status:
        # Database migrations
        from recall_lib.migrations import MigrationManager

        # Initialize with auto_migrate=False to avoid double-migration
        from recall_lib.database import RecallDatabase
        db = RecallDatabase(auto_migrate=False)
        manager = MigrationManager(db.db_path)

        if args.migration_status:
            # Show migration status
            status = manager.get_migration_status()
            current_version = manager.get_current_version()

            logger.info(f"📊 Current Schema Version: {current_version}\n")
            logger.info("Migration Status:")
            logger.info("-" * 60)

            for mig in status:
                status_icon = "✅" if mig['applied'] else "⏳"
                rollback_info = " (rollback available)" if mig['has_rollback'] else ""
                logger.info(f"{status_icon} v{mig['version']}: {mig['name']}{rollback_info}")

            pending = [m for m in status if not m['applied']]
            if pending:
                logger.info(f"\n💡 {len(pending)} pending migration(s). Run 'recall --migrate' to apply.")
            else:
                logger.info("\n✅ All migrations applied")

            return 0

        if args.migrate:
            # Run migrations
            success = manager.migrate_to_latest()
            return 0 if success else 1

    if args.config or args.config_init or args.config_edit:
        # Configuration management
        from recall_lib.config import get_config
        import subprocess

        if args.config_init:
            # Create default configuration file
            config = get_config()
            config.create_default_config()
            return 0

        elif args.config_edit:
            # Open configuration file in editor
            config = get_config()
            config_path = config._get_global_config_path()

            # Ensure config file exists
            if not config_path.exists():
                logger.info("📝 Configuration file doesn't exist yet. Creating it...")
                config.create_default_config()

            # Open in editor (use $EDITOR or fall back to nano/vim)
            editor = os.environ.get('EDITOR', 'nano')
            try:
                subprocess.run([editor, str(config_path)], check=True)
                logger.info("✅ Configuration updated")
            except Exception as e:
                logger.error(f"❌ Failed to open editor: {e}")
                logger.info(f"💡 Edit manually: {config_path}")
                return 1
            return 0

        else:  # args.config
            # Show current configuration
            config = get_config()
            config.show()
            return 0

    if args.plugins:
        # List loaded plugins
        plugins = plugin_manager.list_plugins()

        if not plugins:
            logger.info("📦 No plugins loaded")
            logger.info(f"💡 Add plugins to: {config._get_global_config_path()}")
            logger.info("💡 Or create plugins in: ./plugins/ directory")
            return 0

        logger.info(f"📦 Loaded Plugins ({len(plugins)}):\n")
        for plugin in plugins:
            status = "🟢 enabled" if plugin['enabled'] else "🔴 disabled"
            logger.info(f"  {plugin['name']} v{plugin['version']} [{status}]")
            logger.info(f"     {plugin['description']}")
            logger.info(f"     Author: {plugin['author']}")

            # Show config schema
            if plugin['config_schema']:
                logger.info(f"     Configuration:")
                for key, spec in plugin['config_schema'].items():
                    required = " (required)" if spec.get('required') else ""
                    default = f" [default: {spec.get('default')}]" if 'default' in spec else ""
                    logger.info(f"       - {key}: {spec.get('type', 'any')}{required}{default}")

            logger.info("")

        return 0

    if args.plugin_command:
        # Execute plugin command
        try:
            result = plugin_manager.execute_command(args.plugin_command)
            if result is not None:
                logger.info(f"✅ Command result: {result}")
            return 0
        except ValueError as e:
            logger.error(f"❌ {e}")
            return 1
        except Exception as e:
            logger.error(f"❌ Command execution failed: {e}")
            return 1

    if args.dashboard:
        # Start the live Flask dashboard server
        import subprocess
        import sys

        # Get the directory where recall.py is located (resolve symlinks)
        recall_dir = os.path.dirname(os.path.realpath(__file__))
        dashboard_app = os.path.join(recall_dir, 'dashboard_app.py')

        if not os.path.exists(dashboard_app):
            logger.error(f"❌ Dashboard app not found: {dashboard_app}")
            return 1

        logger.info("🧠 Starting Recall Dashboard server...")
        logger.info("💡 Press Ctrl+C to stop")

        # Run the Flask dashboard app (it will take over the terminal)
        try:
            result = subprocess.run([sys.executable, dashboard_app])
            return result.returncode
        except KeyboardInterrupt:
            logger.info("\n👋 Dashboard server stopped")
            return 0

    if args.list_templates:
        # List all available templates
        from recall_lib.templates import list_templates
        templates = list_templates()

        # Use Rich output (or fallback)
        rich_output.print_templates_list(templates)
        return 0

    if args.verify_only:
        # Only run access verification
        verifier = AccessVerifier()
        results = verifier.verify_all()
        logger.info("\n" + verifier.get_detailed_results())
        return 0 if all(results.values()) else 1

    # Export/Import commands (don't require project name)
    if args.export:
        from recall_lib.backup_manager import BackupManager
        backup = BackupManager(memory.db)
        success = backup.export_to_json(args.export, include_sessions=True)
        return 0 if success else 1

    if args.import_file:
        from recall_lib.backup_manager import BackupManager
        backup = BackupManager(memory.db)
        success = backup.import_from_json(args.import_file, merge=args.merge)
        return 0 if success else 1

    # Insights command (doesn't require project name)
    if args.insights:
        from recall_lib.insights import InsightsGenerator
        insights = InsightsGenerator(memory.db)
        report = insights.generate_insights_report(days=args.days)
        logger.info(report)
        return 0

    if args.list:
        list_projects(memory)
        return 0

    if args.search:
        search_projects(memory, args.search)
        return 0

    if args.list_tags:
        # List all tags with counts
        tags = memory.get_all_tags()
        if not tags:
            rich_output.print_info("No tags found")
            return 0

        # Use Rich output (or fallback)
        rich_output.print_tags_list(tags)
        return 0

    if args.tag:
        # List projects by tag
        projects = memory.get_projects_by_tag(args.tag)
        if not projects:
            logger.info(f"📝 No projects found with tag '{args.tag}'")
            return 0

        logger.info(f"🏷️  Projects tagged '{args.tag}' ({len(projects)}):\n")
        for project in projects:
            logger.info(f"• {project['name']}")
            if project.get('description'):
                logger.info(f"  └─ {project['description']}")
            logger.info(f"  └─ Updated: {project['updated_at'][:19]}")
            logger.info("")
        return 0

    if not args.project:
        # Try to detect project from current directory
        detected = memory.detect_project_from_directory()
        if detected:
            logger.info(f"🔍 Auto-detected project: {detected}")
            args.project = detected
        else:
            parser.print_help()
            logger.info(f"\n💡 No project specified and none detected in current directory")
            logger.info("💡 Use 'recall --list' to see available projects")
            return 1

    project_name = args.project

    if args.create:
        success = create_new_project(memory, project_name, not args.non_interactive)
        if success and args.template:
            # Apply template after creation
            from recall_lib.templates import apply_template
            template_success = apply_template(memory, project_name, args.template)
            if not template_success:
                logger.warning(f"⚠️  Project created but template '{args.template}' could not be applied")
                logger.info("💡 Use 'recall --list-templates' to see available templates")
        return 0 if success else 1

    if args.status:
        success = show_project_status(memory, project_name)
        return 0 if success else 1

    if args.add_tag:
        # Add a tag to the project
        success = memory.add_tag(project_name, args.add_tag)
        if success:
            rich_output.print_success(f"Added tag '{args.add_tag}' to project '{project_name}'")
            return 0
        else:
            rich_output.print_error(f"Failed to add tag - project '{project_name}' not found")
            return 1

    if args.remove_tag:
        # Remove a tag from the project
        success = memory.remove_tag(project_name, args.remove_tag)
        if success:
            rich_output.print_success(f"Removed tag '{args.remove_tag}' from project '{project_name}'")
            return 0
        else:
            rich_output.print_error(f"Failed to remove tag - project '{project_name}' not found")
            return 1

    if args.tags:
        # Show tags for the project
        tags = memory.get_tags(project_name)
        if not tags:
            logger.info(f"📝 Project '{project_name}' has no tags")
            logger.info(f"💡 Add tags with: recall {project_name} --add-tag \"tagname\"")
            return 0

        logger.info(f"🏷️  Tags for '{project_name}':\n")
        for tag in tags:
            logger.info(f"  • {tag}")
        return 0

    if args.analyze:
        # Auto-analyze and populate context
        from recall_lib.auto_analyzer import auto_populate_recall
        from recall_lib.fuzzy_match import suggest_project
        project = memory.db.get_project(project_name)
        if not project:
            logger.error(f"❌ Project '{project_name}' not found")
            suggestion = suggest_project(project_name, memory)
            if suggestion:
                logger.info(suggestion)
            return 1
        success = auto_populate_recall(project_name, project.get('directory'))
        return 0 if success else 1

    if args.git_log:
        # Auto-log from git commits
        from recall_lib.git_logger import auto_log_from_git
        success = auto_log_from_git(project_name, args.days)
        return 0 if success else 1

    if args.install_hook:
        # Install git post-commit hook
        from recall_lib.git_hook_installer import install_hook_for_project
        from recall_lib.fuzzy_match import suggest_project
        project = memory.db.get_project(project_name)
        if not project:
            logger.error(f"❌ Project '{project_name}' not found")
            suggestion = suggest_project(project_name, memory)
            if suggestion:
                logger.info(suggestion)
            return 1
        success = install_hook_for_project(
            project_name,
            project.get('directory'),
            smart=args.smart,
            quiet=args.quiet
        )
        return 0 if success else 1

    if args.history:
        # Show context change history
        from recall_lib.context_history import show_history
        success = show_history(project_name, limit=args.history_limit)
        return 0 if success else 1

    if args.diff:
        # Show diff between versions
        from recall_lib.context_history import diff_versions

        # Parse version range if provided
        version1, version2 = None, None
        if args.diff_versions:
            try:
                parts = args.diff_versions.split(':')
                if len(parts) == 2:
                    version1 = int(parts[0])
                    version2 = int(parts[1])
                else:
                    logger.error("❌ Invalid version format. Use: --diff-versions V1:V2 (e.g., 5:10)")
                    return 1
            except ValueError:
                logger.error("❌ Invalid version numbers")
                return 1

        success = diff_versions(project_name, version1, version2)
        return 0 if success else 1

    if args.rollback is not None:
        # Rollback to a specific version
        from recall_lib.context_history import rollback_context
        success = rollback_context(project_name, args.rollback, confirm=args.yes)
        return 0 if success else 1

    # Default action: load context and display report only
    success = load_project_context(memory, project_name, not args.no_verify)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())