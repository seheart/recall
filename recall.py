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
from project_memory import ProjectMemory
from access_verifier import AccessVerifier


def create_new_project(memory: ProjectMemory, name: str, interactive: bool = True):
    """Create a new project with optional interactive setup"""
    if memory.project_exists(name):
        print(f"❌ Project '{name}' already exists")
        return False

    print(f"🆕 Creating new project: {name}")

    # Get current directory as default
    current_dir = os.getcwd()
    description = None
    directory = current_dir

    if interactive:
        # Interactive setup
        print(f"\nProject Setup for '{name}':")
        desc_input = input("Description (optional): ").strip()
        if desc_input:
            description = desc_input

        dir_input = input(f"Directory [{current_dir}]: ").strip()
        if dir_input:
            directory = dir_input

        # Architecture questions
        print("\n🏗️ Architecture Information (optional, press Enter to skip):")
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
        print(f"✅ Created project '{name}' (ID: {project_id})")
        print(f"📁 Directory: {directory}")
        if description:
            print(f"📝 Description: {description}")
        return True
    except Exception as e:
        print(f"❌ Failed to create project: {e}")
        return False


def load_project_context(memory: ProjectMemory, name: str, verify_access: bool = True):
    """Load and display project context with access verification"""
    if not memory.project_exists(name):
        print(f"❌ Project '{name}' not found")

        # Try to detect from current directory
        detected = memory.detect_project_from_directory()
        if detected:
            print(f"💡 Found project '{detected}' for current directory")
            choice = input(f"Load '{detected}' instead? (y/n): ").strip().lower()
            if choice == 'y':
                name = detected
            else:
                return False
        else:
            print("💡 Create this project with: recall {} --create".format(name))
            return False

    # Load context
    print(f"🧠 Loading project memory: {name}")

    # Verify development access if requested
    if verify_access:
        verifier = AccessVerifier()
        access_results = verifier.verify_all()
        print()  # Add some space after verification output

    context = memory.get_project_context(name)

    if context:
        formatted = memory.format_for_claude(name)
        print("\n" + formatted)

        # Show access summary
        if verify_access:
            print("\n" + "="*60)
            print("🔧 DEVELOPMENT ENVIRONMENT STATUS:")
            print(verifier.get_summary_status())
            print("="*60)

        print(f"\n🎯 Project '{name}' context loaded successfully!")

        if verify_access and all(access_results.values()):
            print("🚀 Claude Code has full development access - ready for work!")
        elif verify_access:
            print("⚠️ Some access issues detected - development capabilities may be limited")

        print("\n💡 Copy the PROJECT MEMORY section above to provide to Claude Code")

        # Generate and display status report
        from status_reporter import generate_status_report
        print("\n")
        status_report = generate_status_report(name)
        print(status_report)

        return True
    else:
        print(f"❌ Failed to load context for project '{name}'")
        return False


def list_projects(memory: ProjectMemory):
    """List all projects"""
    projects = memory.list_all_projects()

    if not projects:
        print("📝 No projects found")
        print("💡 Create your first project with: recall my-project --create")
        return

    print(f"📚 Found {len(projects)} project(s):\n")

    for project in projects:
        print(f"• {project['name']}")
        if project.get('description'):
            print(f"  └─ {project['description']}")
        print(f"  └─ Updated: {project['updated_at'][:19]}")
        if project.get('directory'):
            print(f"  └─ Directory: {project['directory']}")
        print()


def show_project_status(memory: ProjectMemory, name: str):
    """Show detailed status for a project"""
    context = memory.get_project_context(name)
    if not context:
        print(f"❌ Project '{name}' not found")
        return False

    project = context['project']
    ctx = context['context']
    sessions = context['recent_sessions']

    print(f"📊 Status for project: {project['name']}")
    print("=" * 50)

    print(f"Created: {project['created_at'][:19]}")
    print(f"Updated: {project['updated_at'][:19]}")

    if project.get('description'):
        print(f"Description: {project['description']}")

    if project.get('directory'):
        print(f"Directory: {project['directory']}")

    # Show current state
    if 'state' in ctx:
        print("\n⚡ Current State:")
        for key, value in ctx['state'].items():
            print(f"  • {key}: {value}")

    # Show architecture
    if 'architecture' in ctx:
        print("\n🏗️ Architecture:")
        for key, value in ctx['architecture'].items():
            print(f"  • {key}: {value}")

    # Show recent activity
    if sessions:
        print(f"\n📝 Recent Sessions ({len(sessions)}):")
        for session in sessions[:3]:
            print(f"\n  Session {session['created_at'][:19]}:")
            if session['summary']:
                print(f"    Summary: {session['summary']}")
            if session['accomplishments']:
                print(f"    Done: {session['accomplishments'].strip()}")

    return True


def main():
    """Main entry point for recall command"""
    parser = argparse.ArgumentParser(
        description="Recall - Project Memory System for Claude Code",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  recall my-api                    Load my-api project context (with verification)
  recall my-api --claude          Load context + launch Claude Code (context in clipboard!)
  recall my-api --create          Create new project
  recall --list                   List all projects
  recall my-api --status          Show project status
  recall my-api --analyze         Auto-analyze project and populate context
  recall my-api --git-log         Auto-log sessions from git commits
  recall my-api --git-log --days 30   Log from last 30 days
  recall --verify-only            Check GitHub/server access only
  recall my-api --no-verify       Load context without access verification
        """
    )

    parser.add_argument('project', nargs='?', help='Project name')
    parser.add_argument('--create', action='store_true', help='Create new project')
    parser.add_argument('--list', action='store_true', help='List all projects')
    parser.add_argument('--status', action='store_true', help='Show project status')
    parser.add_argument('--non-interactive', action='store_true', help='Non-interactive mode')
    parser.add_argument('--no-verify', action='store_true', help='Skip access verification')
    parser.add_argument('--verify-only', action='store_true', help='Only run access verification')
    parser.add_argument('--analyze', action='store_true', help='Auto-analyze project and populate context')
    parser.add_argument('--git-log', action='store_true', help='Auto-log sessions from git commits')
    parser.add_argument('--days', type=int, default=7, help='Days back for git log (default: 7)')
    parser.add_argument('--claude', action='store_true', help='Load context and launch Claude Code')

    args = parser.parse_args()

    # Initialize memory system
    try:
        memory = ProjectMemory()
    except Exception as e:
        print(f"❌ Failed to initialize memory system: {e}")
        return 1

    # Handle different commands
    if args.verify_only:
        # Only run access verification
        verifier = AccessVerifier()
        results = verifier.verify_all()
        print("\n" + verifier.get_detailed_results())
        return 0 if all(results.values()) else 1

    if args.list:
        list_projects(memory)
        return 0

    if not args.project:
        # Try to detect project from current directory
        detected = memory.detect_project_from_directory()
        if detected:
            print(f"🔍 Auto-detected project: {detected}")
            args.project = detected
        else:
            parser.print_help()
            print(f"\n💡 No project specified and none detected in current directory")
            print("💡 Use 'recall --list' to see available projects")
            return 1

    project_name = args.project

    if args.create:
        success = create_new_project(memory, project_name, not args.non_interactive)
        return 0 if success else 1

    if args.status:
        success = show_project_status(memory, project_name)
        return 0 if success else 1

    if args.analyze:
        # Auto-analyze and populate context
        from auto_analyzer import auto_populate_recall
        project = memory.db.get_project(project_name)
        if not project:
            print(f"❌ Project '{project_name}' not found")
            return 1
        success = auto_populate_recall(project_name, project.get('directory'))
        return 0 if success else 1

    if args.git_log:
        # Auto-log from git commits
        from git_logger import auto_log_from_git
        success = auto_log_from_git(project_name, args.days)
        return 0 if success else 1

    if args.claude:
        # Load context and launch Claude Code
        import subprocess
        import tempfile
        from pathlib import Path

        # Verify access first
        print("🔍 Verifying development environment access...")
        verifier = AccessVerifier()
        access_results = verifier.verify_all()

        # Generate context
        context = memory.get_project_context(project_name)
        if not context:
            print(f"❌ Project '{project_name}' not found")
            return 1

        formatted = memory.format_for_claude(project_name)

        # Add readiness report
        from status_reporter import generate_status_report
        readiness = generate_status_report(project_name)

        formatted_full = formatted + "\n\n" + readiness

        # Save to file
        context_file = Path.home() / '.claude' / f'recall_{project_name}.txt'
        context_file.parent.mkdir(parents=True, exist_ok=True)

        with open(context_file, 'w') as f:
            f.write(formatted_full)

        # Copy to clipboard if available
        try:
            subprocess.run(['wl-copy'], input=formatted_full.encode(), check=True, capture_output=True)
        except:
            pass

        # Launch cdev with context piped to stdin
        print(f"🚀 Launching Claude Code with {project_name} context...\n")
        try:
            subprocess.run(['cdev'], input=formatted_full.encode(), check=False)
        except Exception as e:
            print(f"❌ Failed to launch cdev: {e}")
            print(f"\n💡 Context saved to: {context_file}")
            print("💡 You can manually run: cdev")
            return 1

        return 0

    # Default action: load context and launch Claude Code
    # Same behavior as --claude flag
    import subprocess
    from pathlib import Path

    # Verify access first
    print("🔍 Verifying development environment access...")
    verifier = AccessVerifier()
    access_results = verifier.verify_all()

    # Generate context
    context = memory.get_project_context(project_name)
    if not context:
        print(f"❌ Project '{project_name}' not found")
        return 1

    formatted = memory.format_for_claude(project_name)

    # Add readiness report
    from status_reporter import generate_status_report
    readiness = generate_status_report(project_name)

    formatted_full = formatted + "\n\n" + readiness

    # Save to file
    context_file = Path.home() / '.claude' / f'recall_{project_name}.txt'
    context_file.parent.mkdir(parents=True, exist_ok=True)

    with open(context_file, 'w') as f:
        f.write(formatted_full)

    # Copy to clipboard if available
    try:
        subprocess.run(['wl-copy'], input=formatted_full.encode(), check=True, capture_output=True)
    except:
        pass

    # Launch cdev with context piped to stdin
    print(f"🚀 Launching Claude Code with {project_name} context...\n")
    try:
        subprocess.run(['cdev'], input=formatted_full.encode(), check=False)
    except Exception as e:
        print(f"❌ Failed to launch cdev: {e}")
        print(f"\n💡 Context saved to: {context_file}")
        print("💡 You can manually run: cdev")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())