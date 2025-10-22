#!/usr/bin/env python3
"""
Rich Output - Enhanced CLI output using Rich library with fallbacks
"""
from typing import List, Dict, Optional
import sys

# Try to import Rich, but gracefully degrade if not available
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.syntax import Syntax
    from rich.markdown import Markdown
    from rich import box
    from rich.progress import Progress, SpinnerColumn, TextColumn

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from .logger import get_logger

logger = get_logger(__name__)


class RichOutput:
    """Enhanced output using Rich library with fallbacks"""

    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.enabled = RICH_AVAILABLE

    def print(self, text: str, style: str = None) -> None:
        """Print text with optional styling"""
        if self.enabled and style:
            self.console.print(text, style=style)
        else:
            print(text)

    def print_panel(self, content: str, title: str = None, style: str = "cyan") -> None:
        """Print content in a panel"""
        if self.enabled:
            panel = Panel(content, title=title, border_style=style, box=box.ROUNDED)
            self.console.print(panel)
        else:
            if title:
                print(f"\n=== {title} ===")
            print(content)
            print("=" * 60)

    def print_table(
        self, title: str, columns: List[str], rows: List[List[str]], show_header: bool = True
    ) -> None:
        """Print data in a table format"""
        if self.enabled:
            table = Table(title=title, box=box.ROUNDED, show_header=show_header)

            for col in columns:
                table.add_column(col, style="cyan")

            for row in rows:
                table.add_row(*[str(cell) for cell in row])

            self.console.print(table)
        else:
            # Fallback to simple text table
            if title:
                print(f"\n{title}")
                print("-" * 60)

            if show_header:
                print(" | ".join(columns))
                print("-" * 60)

            for row in rows:
                print(" | ".join(str(cell) for cell in row))

    def print_markdown(self, markdown_text: str) -> None:
        """Print markdown-formatted text"""
        if self.enabled:
            md = Markdown(markdown_text)
            self.console.print(md)
        else:
            print(markdown_text)

    def print_success(self, message: str) -> None:
        """Print success message"""
        if self.enabled:
            self.console.print(f"✅ {message}", style="bold green")
        else:
            print(f"✅ {message}")

    def print_error(self, message: str) -> None:
        """Print error message"""
        if self.enabled:
            self.console.print(f"❌ {message}", style="bold red")
        else:
            print(f"❌ {message}")

    def print_warning(self, message: str) -> None:
        """Print warning message"""
        if self.enabled:
            self.console.print(f"⚠️  {message}", style="bold yellow")
        else:
            print(f"⚠️  {message}")

    def print_info(self, message: str) -> None:
        """Print info message"""
        if self.enabled:
            self.console.print(f"ℹ️  {message}", style="bold blue")
        else:
            print(f"ℹ️  {message}")

    def print_project_list(
        self, projects: List[Dict], tags_dict: Dict[str, List[str]] = None
    ) -> None:
        """Print projects in an enhanced format"""
        if not projects:
            self.print_info("No projects found")
            return

        if self.enabled:
            table = Table(title=f"📚 Projects ({len(projects)})", box=box.ROUNDED, show_header=True)
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Tags", style="magenta")
            table.add_column("Description", style="white")
            table.add_column("Updated", style="green")

            for project in projects:
                name = project["name"]
                tags = tags_dict.get(name, []) if tags_dict else []
                tags_str = ", ".join(tags) if tags else "-"
                desc = project.get("description", "-")
                if desc and len(desc) > 50:
                    desc = desc[:47] + "..."
                updated = project["updated_at"][:10]

                table.add_row(name, tags_str, desc, updated)

            self.console.print(table)
        else:
            # Fallback
            print(f"\n📚 Projects ({len(projects)}):\n")
            for project in projects:
                name = project["name"]
                tags = tags_dict.get(name, []) if tags_dict else []
                tags_str = f" 🏷️  [{', '.join(tags)}]" if tags else ""
                print(f"• {name}{tags_str}")
                if project.get("description"):
                    print(f"  └─ {project['description']}")
                print(f"  └─ Updated: {project['updated_at'][:19]}")
                print()

    def print_tags_list(self, tags: List[Dict]) -> None:
        """Print tags with counts"""
        if not tags:
            self.print_info("No tags found")
            return

        if self.enabled:
            table = Table(title=f"🏷️  All Tags ({len(tags)})", box=box.ROUNDED)
            table.add_column("Tag", style="cyan")
            table.add_column("Projects", style="green", justify="right")

            for tag_info in tags:
                table.add_row(tag_info["tag"], str(tag_info["count"]))

            self.console.print(table)
        else:
            print(f"\n🏷️  All Tags ({len(tags)}):\n")
            for tag_info in tags:
                print(
                    f"  • {tag_info['tag']} ({tag_info['count']} project{'s' if tag_info['count'] > 1 else ''})"
                )

    def print_templates_list(self, templates: List[Dict]) -> None:
        """Print available templates"""
        if self.enabled:
            table = Table(title=f"📋 Project Templates ({len(templates)})", box=box.ROUNDED)
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Name", style="green")
            table.add_column("Tags", style="magenta")
            table.add_column("Description", style="white")

            for tmpl in templates:
                tags_str = ", ".join(tmpl["tags"]) if tmpl["tags"] else "-"
                table.add_row(tmpl["id"], tmpl["name"], tags_str, tmpl["description"])

            self.console.print(table)
            self.console.print(
                "\n💡 [bold cyan]Use with:[/] recall my-project --create --template <template-id>"
            )
        else:
            print(f"\n📋 Available Project Templates ({len(templates)}):\n")
            for tmpl in templates:
                tags_str = f" [{', '.join(tmpl['tags'])}]" if tmpl["tags"] else ""
                print(f"• {tmpl['id']:<15} - {tmpl['name']}{tags_str}")
                print(f"  └─ {tmpl['description']}")
                print()
            print("💡 Use with: recall my-project --create --template <template-id>")

    def print_project_status(self, project: Dict, context: Dict, sessions: List[Dict]) -> None:
        """Print detailed project status"""
        if self.enabled:
            # Project header panel
            header = f"[bold]{project['name']}[/bold]\n"
            if project.get("description"):
                header += f"{project['description']}\n"
            header += f"\n📁 {project.get('directory', 'Not specified')}"
            header += f"\n🕒 Updated: {project['updated_at'][:19]}"

            self.console.print(Panel(header, title="📊 Project Status", border_style="cyan"))

            # Architecture
            if "architecture" in context:
                arch_text = "\n".join(f"• {k}: {v}" for k, v in context["architecture"].items())
                self.console.print(Panel(arch_text, title="🏗️  Architecture", border_style="blue"))

            # Current State
            if "state" in context:
                state_text = "\n".join(f"• {k}: {v}" for k, v in context["state"].items())
                self.console.print(
                    Panel(state_text, title="⚡️ Current State", border_style="yellow")
                )

            # Recent Sessions
            if sessions:
                self.console.print(
                    f"\n[bold cyan]📝 Recent Sessions ({len(sessions)}):[/bold cyan]"
                )
                for session in sessions[:3]:
                    session_text = f"[bold]{session['created_at'][:19]}[/bold]\n"
                    if session["summary"]:
                        session_text += f"• {session['summary']}\n"
                    if session["accomplishments"]:
                        session_text += f"✓ {session['accomplishments'][:100]}"

                    self.console.print(Panel(session_text, border_style="green", box=box.SIMPLE))
        else:
            # Fallback to simple output
            print(f"\n📊 Status for project: {project['name']}")
            print("=" * 50)
            if project.get("description"):
                print(f"Description: {project['description']}")
            print(f"Directory: {project.get('directory', 'Not specified')}")
            print(f"Updated: {project['updated_at'][:19]}")

            if "architecture" in context:
                print("\n🏗️  Architecture:")
                for k, v in context["architecture"].items():
                    print(f"  • {k}: {v}")

            if "state" in context:
                print("\n⚡️ Current State:")
                for k, v in context["state"].items():
                    print(f"  • {k}: {v}")

            if sessions:
                print(f"\n📝 Recent Sessions ({len(sessions)}):")
                for session in sessions[:3]:
                    print(f"\n  {session['created_at'][:19]}:")
                    if session["summary"]:
                        print(f"    • {session['summary']}")

    def print_enriched_context(
        self, project: Dict, context: Dict, enriched: Dict, sessions: List[Dict]
    ) -> None:
        """Print comprehensive enriched context for maximum Claude intelligence"""
        project_name = project["name"]

        if self.enabled:
            from rich.tree import Tree
            from rich.text import Text

            # Header
            self.console.print(f"\n[bold cyan]{'='*80}[/bold cyan]")
            self.console.print(
                f"[bold white]📦 PROJECT:[/bold white] [bold cyan]{project_name.upper()}[/bold cyan]"
            )
            self.console.print(f"[bold cyan]{'='*80}[/bold cyan]\n")

            # Current State
            state = enriched.get("current_state", {})
            state_panel = f"""[bold]Status:[/bold] {state.get('status', 'Unknown')}
[bold]Last Active:[/bold] {state.get('last_active', 'Unknown')}
[bold]Health:[/bold] {state.get('health_emoji', '⚪')} {state.get('health', 'Unknown').replace('_', ' ').title()}"""

            if project.get("directory"):
                state_panel += f"\n[bold]Directory:[/bold] {project['directory']}"

            self.console.print(Panel(state_panel, title="📍 CURRENT STATE", border_style="green"))

            # Architecture
            if "architecture" in context and context["architecture"]:
                arch = context["architecture"]
                arch_lines = []
                for key, value in arch.items():
                    arch_lines.append(f"[bold]{key.replace('_', ' ').title()}:[/bold] {value}")

                if arch_lines:
                    self.console.print(
                        Panel("\n".join(arch_lines), title="🏗️  ARCHITECTURE", border_style="blue")
                    )

            # Architecture Patterns
            patterns = enriched.get("architecture_patterns", [])
            if patterns:
                patterns_text = "\n".join(f"  • {pattern}" for pattern in patterns)
                self.console.print(
                    Panel(patterns_text, title="🎨 ARCHITECTURE PATTERNS", border_style="blue")
                )

            # Hot Files
            hot_files = enriched.get("hot_files", [])
            if hot_files:
                hot_text = "\n".join(
                    f"  🔥 [cyan]{f['file']}[/cyan] - {f['changes']}" for f in hot_files
                )
                self.console.print(
                    Panel(hot_text, title="🔥 HOT FILES (Last 7 Days)", border_style="red")
                )

            # Entry Points
            entry_points = enriched.get("entry_points", [])
            if entry_points:
                entry_text = "\n".join(f"  📍 {ep}" for ep in entry_points)
                self.console.print(Panel(entry_text, title="🎯 ENTRY POINTS", border_style="green"))

            # Workflows
            workflows = enriched.get("workflows", {})
            if workflows:
                workflow_text = "\n".join(
                    f"  [bold]{name}:[/bold] [cyan]{cmd}[/cyan]" for name, cmd in workflows.items()
                )
                self.console.print(
                    Panel(workflow_text, title="⚙️  COMMON WORKFLOWS", border_style="green")
                )

            # Working Tree State
            working_tree = enriched.get("working_tree", {})
            if working_tree:
                wt_text = ""
                if "branch" in working_tree:
                    wt_text += f"[bold]Branch:[/bold] {working_tree['branch']}\n"
                if "modified" in working_tree:
                    wt_text += f"[bold]Modified Files:[/bold]\n"
                    for f in working_tree["modified"][:5]:
                        wt_text += f"  • {f}\n"
                if "staged" in working_tree:
                    wt_text += f"\n[bold]Staged:[/bold] {working_tree['staged']}"

                if wt_text:
                    self.console.print(
                        Panel(wt_text.strip(), title="📝 WORKING TREE STATE", border_style="yellow")
                    )

            # External Integrations
            integrations = enriched.get("external_integrations", [])
            if integrations:
                integrations_text = "\n".join(f"  🌐 {integration}" for integration in integrations)
                self.console.print(
                    Panel(
                        integrations_text, title="🔌 EXTERNAL INTEGRATIONS", border_style="magenta"
                    )
                )

            # File Relationships
            relationships = enriched.get("file_relationships", [])
            if relationships:
                rel_text = "\n".join(f"  🔗 {rel}" for rel in relationships)
                self.console.print(
                    Panel(rel_text, title="🔗 FILE RELATIONSHIPS", border_style="cyan")
                )

            # Known Issues
            known_issues = enriched.get("known_issues", [])
            if known_issues:
                issues_text = "\n".join(f"  ⚠️  {issue}" for issue in known_issues[:5])
                self.console.print(Panel(issues_text, title="🐛 KNOWN ISSUES", border_style="red"))

            # Health Metrics
            health = enriched.get("health_metrics", [])
            if health:
                health_text = "\n".join(f"  ✓ {metric}" for metric in health)
                self.console.print(
                    Panel(health_text, title="📊 PROJECT HEALTH", border_style="green")
                )

            # Recent Activity
            activity = enriched.get("recent_activity", {})
            if activity.get("commits") or activity.get("sessions"):
                activity_text = (
                    f"[bold]Sessions:[/bold] {activity.get('sessions', 0)} in last 7 days\n"
                )
                activity_text += (
                    f"[bold]Commits:[/bold] {len(activity.get('commits', []))} in last 7 days\n"
                )

                if activity.get("key_changes"):
                    activity_text += "\n[bold]Key Changes:[/bold]\n"
                    for change in activity.get("key_changes", [])[:3]:
                        activity_text += f"  • {change}\n"

                self.console.print(
                    Panel(activity_text, title="📈 RECENT ACTIVITY", border_style="yellow")
                )

            # Current Focus
            focus = enriched.get("current_focus", {})
            if focus.get("working_on") or focus.get("next_steps"):
                focus_text = ""
                if focus.get("working_on"):
                    focus_text += f"[bold]Working On:[/bold] {focus['working_on']}\n"

                if focus.get("blockers"):
                    focus_text += f"\n[bold red]Blockers:[/bold red]\n"
                    for blocker in focus["blockers"]:
                        focus_text += f"  ⚠️  {blocker}\n"

                if focus.get("next_steps"):
                    focus_text += f"\n[bold]Next Steps:[/bold]\n"
                    for i, step in enumerate(focus["next_steps"][:5], 1):
                        focus_text += f"  {i}. {step}\n"

                if focus_text:
                    self.console.print(
                        Panel(focus_text, title="🎯 CURRENT FOCUS", border_style="magenta")
                    )

            # TODOs and Issues
            todos = enriched.get("todos_and_issues", {})
            if todos.get("total", 0) > 0:
                todo_text = f"[bold]Total:[/bold] {todos['total']} items found\n"

                if todos.get("fixme"):
                    todo_text += f"\n[bold red]FIXME ({len(todos['fixme'])}):[/bold red]\n"
                    for item in todos["fixme"][:3]:
                        todo_text += f"  🐛 {item['file']}:{item['line']} - {item['text'][:60]}\n"

                if todos.get("todo"):
                    todo_text += f"\n[bold yellow]TODO ({len(todos['todo'])}):[/bold yellow]\n"
                    for item in todos["todo"][:5]:
                        todo_text += f"  📝 {item['file']}:{item['line']} - {item['text'][:60]}\n"

                if todos.get("hack"):
                    todo_text += f"\n[bold orange]HACK ({len(todos['hack'])}):[/bold orange]\n"
                    for item in todos["hack"][:2]:
                        todo_text += f"  ⚡️ {item['file']}:{item['line']} - {item['text'][:60]}\n"

                self.console.print(
                    Panel(todo_text, title="📝 TODO & ISSUES", border_style="yellow")
                )

            # Important Decisions
            if "decisions" in context and context["decisions"]:
                decisions_text = ""
                for key, value in list(context["decisions"].items())[:5]:
                    decisions_text += (
                        f"[bold]• {key.replace('_', ' ').title()}:[/bold]\n  {value}\n\n"
                    )

                if decisions_text:
                    self.console.print(
                        Panel(
                            decisions_text.strip(),
                            title="⚠️  IMPORTANT DECISIONS",
                            border_style="red",
                        )
                    )

            # Key Files
            key_files = enriched.get("key_files", [])
            if key_files:
                files_text = ""
                for file_info in key_files[:5]:
                    files_text += f"  📄 {file_info['path']} ({file_info['last_modified']}) - {file_info['modifications']} changes\n"

                if files_text:
                    self.console.print(
                        Panel(
                            files_text,
                            title="📁 KEY FILES (Recently Modified)",
                            border_style="cyan",
                        )
                    )

            # Quick Commands
            commands = enriched.get("quick_commands", {})
            if commands:
                cmd_text = ""
                for cmd_type, cmd in commands.items():
                    cmd_text += f"[bold]{cmd_type.title()}:[/bold] {cmd}\n"

                if cmd_text:
                    self.console.print(
                        Panel(cmd_text, title="🔧 QUICK COMMANDS", border_style="green")
                    )

            # Warnings
            warnings = enriched.get("warnings", [])
            if warnings:
                warnings_text = "\n".join(warnings)
                self.console.print(Panel(warnings_text, title="⚠️  WARNINGS", border_style="red"))

            # Suggestions
            suggestions = enriched.get("suggestions", [])
            if suggestions:
                sugg_text = "\n".join(suggestions)
                self.console.print(Panel(sugg_text, title="💡 SUGGESTIONS", border_style="blue"))

            # Recent Sessions
            if sessions:
                sessions_text = ""
                for session in sessions[:3]:
                    sessions_text += f"[bold]{session['created_at'][:19]}[/bold]\n"
                    if session.get("summary"):
                        sessions_text += f"  Summary: {session['summary']}\n"
                    if session.get("accomplishments"):
                        acc = session["accomplishments"]
                        if isinstance(acc, list):
                            for item in acc[:2]:
                                sessions_text += f"  ✓ {item}\n"
                        else:
                            sessions_text += f"  ✓ {acc[:100]}\n"
                    sessions_text += "\n"

                if sessions_text:
                    self.console.print(
                        Panel(
                            sessions_text.strip(), title="📊 RECENT SESSIONS", border_style="cyan"
                        )
                    )

            # Claude Instructions
            claude_instructions = """[bold]Before beginning development, please:[/bold]

1. 📖 [cyan]Review the README file[/cyan] to understand the project's purpose and setup
2. 📝 [cyan]Examine the last 2-3 git commits[/cyan] to understand recent changes
3. 🔍 [cyan]Do a quick review of the codebase structure[/cyan] and key files listed above
4. ✅ [cyan]Confirm your understanding[/cyan] by either:
   • Stating "I understand the project and am ready for development"
   • OR asking clarifying questions if anything is unclear

[bold yellow]Please review these items now and respond accordingly.[/bold yellow]"""

            self.console.print(
                Panel(
                    claude_instructions,
                    title="🤖 INSTRUCTIONS FOR CLAUDE",
                    border_style="bright_magenta",
                    box=box.DOUBLE,
                )
            )

            self.console.print(f"\n[bold cyan]{'='*80}[/bold cyan]\n")

        else:
            # Fallback text output
            print(f"\n{'='*80}")
            print(f"📦 PROJECT: {project_name.upper()}")
            print(f"{'='*80}\n")

            # Current State
            state = enriched.get("current_state", {})
            print("📍 CURRENT STATE")
            print(f"  Status: {state.get('status', 'Unknown')}")
            print(f"  Last Active: {state.get('last_active', 'Unknown')}")
            print(
                f"  Health: {state.get('health_emoji', '⚪')} {state.get('health', 'Unknown').replace('_', ' ').title()}"
            )
            if project.get("directory"):
                print(f"  Directory: {project['directory']}")
            print()

            # Architecture
            if "architecture" in context and context["architecture"]:
                print("🏗️  ARCHITECTURE")
                for key, value in context["architecture"].items():
                    print(f"  {key.replace('_', ' ').title()}: {value}")
                print()

            # Recent Activity
            activity = enriched.get("recent_activity", {})
            if activity.get("commits") or activity.get("sessions"):
                print("📈 RECENT ACTIVITY")
                print(f"  Sessions: {activity.get('sessions', 0)} in last 7 days")
                print(f"  Commits: {len(activity.get('commits', []))} in last 7 days")
                if activity.get("key_changes"):
                    print("  Key Changes:")
                    for change in activity.get("key_changes", [])[:3]:
                        print(f"    • {change}")
                print()

            # Continue with other sections in text format...

            # Claude Instructions (text fallback)
            print("=" * 80)
            print("🤖 INSTRUCTIONS FOR CLAUDE")
            print("=" * 80)
            print("\nBefore beginning development, please:\n")
            print("1. 📖 Review the README file to understand the project's purpose and setup")
            print("2. 📝 Examine the last 2-3 git commits to understand recent changes")
            print("3. 🔍 Do a quick review of the codebase structure and key files listed above")
            print("4. ✅ Confirm your understanding by either:")
            print("   • Stating 'I understand the project and am ready for development'")
            print("   • OR asking clarifying questions if anything is unclear")
            print("\nPlease review these items now and respond accordingly.")
            print("=" * 80)

            print(f"\n{'='*80}\n")


# Global instance
rich_output = RichOutput()
