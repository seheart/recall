#!/usr/bin/env python3
"""
Claude Code Integration - Automatically inject recall context into Claude sessions
"""
import os
import sys
import tempfile
from pathlib import Path
from .project_memory import ProjectMemory
from .status_reporter import StatusReporter


def generate_context_file(project_name: str, include_readiness: bool = True) -> str:
    """Generate a context file for Claude Code to load"""
    memory = ProjectMemory()

    if not memory.project_exists(project_name):
        print(f"❌ Project '{project_name}' not found")
        return None

    # Get formatted context
    formatted = memory.format_for_claude(project_name)

    # Add readiness report if requested
    if include_readiness:
        reporter = StatusReporter(project_name, memory)
        readiness = reporter.generate_report()
        formatted += "\n\n" + readiness

    # Write to temp file
    context_file = tempfile.NamedTemporaryFile(
        mode='w',
        delete=False,
        suffix='.txt',
        prefix=f'recall_{project_name}_'
    )

    context_file.write(formatted)
    context_file.close()

    return context_file.name


def launch_claude_with_context(project_name: str):
    """Launch Claude Code with recall context pre-loaded"""
    # Generate context file
    context_file = generate_context_file(project_name)

    if not context_file:
        return 1

    print(f"\n🎯 Launching Claude Code with {project_name} context...")
    print(f"📄 Context file: {context_file}")

    # Launch Claude Code with the context file as initial message
    # This simulates the user pasting the context
    import subprocess

    # Read the context
    with open(context_file, 'r') as f:
        context = f.read()

    # Create a startup message file
    startup_file = Path.home() / '.claude' / f'recall_{project_name}_startup.txt'
    startup_file.parent.mkdir(parents=True, exist_ok=True)

    with open(startup_file, 'w') as f:
        f.write(context)

    print(f"\n✅ Context saved to: {startup_file}")
    print(f"\n{'='*70}")
    print("🚀 NEXT STEPS:")
    print("="*70)
    print(f"1. Run: cdev")
    print(f"2. Paste the following to load {project_name} context:\n")
    print(f"   cat ~/.claude/recall_{project_name}_startup.txt\n")
    print("="*70)

    # Clean up temp file
    os.unlink(context_file)

    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: recall_integration.py <project-name>")
        sys.exit(1)

    project_name = sys.argv[1]
    sys.exit(launch_claude_with_context(project_name))
