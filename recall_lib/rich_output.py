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

    def print_table(self, title: str, columns: List[str], rows: List[List[str]],
                    show_header: bool = True) -> None:
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

    def print_project_list(self, projects: List[Dict], tags_dict: Dict[str, List[str]] = None) -> None:
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
                name = project['name']
                tags = tags_dict.get(name, []) if tags_dict else []
                tags_str = ", ".join(tags) if tags else "-"
                desc = project.get('description', '-')
                if desc and len(desc) > 50:
                    desc = desc[:47] + "..."
                updated = project['updated_at'][:10]

                table.add_row(name, tags_str, desc, updated)

            self.console.print(table)
        else:
            # Fallback
            print(f"\n📚 Projects ({len(projects)}):\n")
            for project in projects:
                name = project['name']
                tags = tags_dict.get(name, []) if tags_dict else []
                tags_str = f" 🏷️  [{', '.join(tags)}]" if tags else ""
                print(f"• {name}{tags_str}")
                if project.get('description'):
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
                table.add_row(tag_info['tag'], str(tag_info['count']))

            self.console.print(table)
        else:
            print(f"\n🏷️  All Tags ({len(tags)}):\n")
            for tag_info in tags:
                print(f"  • {tag_info['tag']} ({tag_info['count']} project{'s' if tag_info['count'] > 1 else ''})")

    def print_templates_list(self, templates: List[Dict]) -> None:
        """Print available templates"""
        if self.enabled:
            table = Table(title=f"📋 Project Templates ({len(templates)})", box=box.ROUNDED)
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Name", style="green")
            table.add_column("Tags", style="magenta")
            table.add_column("Description", style="white")

            for tmpl in templates:
                tags_str = ", ".join(tmpl['tags']) if tmpl['tags'] else "-"
                table.add_row(tmpl['id'], tmpl['name'], tags_str, tmpl['description'])

            self.console.print(table)
            self.console.print("\n💡 [bold cyan]Use with:[/] recall my-project --create --template <template-id>")
        else:
            print(f"\n📋 Available Project Templates ({len(templates)}):\n")
            for tmpl in templates:
                tags_str = f" [{', '.join(tmpl['tags'])}]" if tmpl['tags'] else ""
                print(f"• {tmpl['id']:<15} - {tmpl['name']}{tags_str}")
                print(f"  └─ {tmpl['description']}")
                print()
            print("💡 Use with: recall my-project --create --template <template-id>")

    def print_project_status(self, project: Dict, context: Dict, sessions: List[Dict]) -> None:
        """Print detailed project status"""
        if self.enabled:
            # Project header panel
            header = f"[bold]{project['name']}[/bold]\n"
            if project.get('description'):
                header += f"{project['description']}\n"
            header += f"\n📁 {project.get('directory', 'Not specified')}"
            header += f"\n🕒 Updated: {project['updated_at'][:19]}"

            self.console.print(Panel(header, title="📊 Project Status", border_style="cyan"))

            # Architecture
            if 'architecture' in context:
                arch_text = "\n".join(f"• {k}: {v}" for k, v in context['architecture'].items())
                self.console.print(Panel(arch_text, title="🏗️  Architecture", border_style="blue"))

            # Current State
            if 'state' in context:
                state_text = "\n".join(f"• {k}: {v}" for k, v in context['state'].items())
                self.console.print(Panel(state_text, title="⚡ Current State", border_style="yellow"))

            # Recent Sessions
            if sessions:
                self.console.print(f"\n[bold cyan]📝 Recent Sessions ({len(sessions)}):[/bold cyan]")
                for session in sessions[:3]:
                    session_text = f"[bold]{session['created_at'][:19]}[/bold]\n"
                    if session['summary']:
                        session_text += f"• {session['summary']}\n"
                    if session['accomplishments']:
                        session_text += f"✓ {session['accomplishments'][:100]}"

                    self.console.print(Panel(session_text, border_style="green", box=box.SIMPLE))
        else:
            # Fallback to simple output
            print(f"\n📊 Status for project: {project['name']}")
            print("=" * 50)
            if project.get('description'):
                print(f"Description: {project['description']}")
            print(f"Directory: {project.get('directory', 'Not specified')}")
            print(f"Updated: {project['updated_at'][:19]}")

            if 'architecture' in context:
                print("\n🏗️  Architecture:")
                for k, v in context['architecture'].items():
                    print(f"  • {k}: {v}")

            if 'state' in context:
                print("\n⚡ Current State:")
                for k, v in context['state'].items():
                    print(f"  • {k}: {v}")

            if sessions:
                print(f"\n📝 Recent Sessions ({len(sessions)}):")
                for session in sessions[:3]:
                    print(f"\n  {session['created_at'][:19]}:")
                    if session['summary']:
                        print(f"    • {session['summary']}")


# Global instance
rich_output = RichOutput()
