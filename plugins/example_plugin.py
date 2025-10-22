#!/usr/bin/env python3
"""
Example Plugin - Demonstrates Recall plugin capabilities

This plugin shows how to:
- Register hooks
- Define custom commands
- Use configuration
- Access project context
"""
import sys
from pathlib import Path

# Add parent directory to path to import recall_lib
sys.path.insert(0, str(Path(__file__).parent.parent))

from recall_lib.plugin_base import RecallPlugin, PluginContext, PluginHookPoints
from recall_lib.logger import get_logger

logger = get_logger(__name__)


class ExamplePlugin(RecallPlugin):
    """
    Example plugin demonstrating all plugin features
    """

    @property
    def name(self) -> str:
        return "example"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Example plugin demonstrating Recall plugin capabilities"

    @property
    def author(self) -> str:
        return "Recall Team"

    def initialize(self) -> bool:
        """Initialize the plugin"""
        logger.info(f"🔌 Initializing {self.name} plugin")

        # Perform any initialization here
        self.session_count = 0
        self.context_changes = 0

        return True

    def shutdown(self):
        """Shutdown the plugin"""
        logger.info(f"👋 Shutting down {self.name} plugin")
        logger.info(f"   Sessions created: {self.session_count}")
        logger.info(f"   Context changes: {self.context_changes}")

    def get_config_schema(self):
        """Define configuration schema"""
        return {
            'log_to_file': {
                'type': 'bool',
                'default': False,
                'description': 'Log plugin activity to file'
            },
            'output_file': {
                'type': 'string',
                'default': '/tmp/recall-example-plugin.log',
                'description': 'Path to log file'
            },
            'notify_on_session': {
                'type': 'bool',
                'default': True,
                'description': 'Show notification on session creation'
            }
        }

    def register_hooks(self):
        """Register hook handlers"""
        return {
            PluginHookPoints.SESSION_POST_CREATE: self.on_session_created,
            PluginHookPoints.CONTEXT_POST_SET: self.on_context_set,
            PluginHookPoints.PROJECT_POST_ANALYZE: self.on_project_analyzed,
            PluginHookPoints.GIT_POST_LOG: self.on_git_logged,
        }

    def get_commands(self):
        """Register custom commands"""
        return {
            'stats': self.show_stats,
            'reset': self.reset_stats,
            'test': self.test_command,
        }

    # Hook Handlers

    def on_session_created(self, context: PluginContext):
        """Called after a session is created"""
        self.session_count += 1

        if self.config.get('notify_on_session', True):
            summary = context.get_data('summary', 'N/A')
            logger.info(f"📝 Example plugin: New session created - {summary[:50]}")

        # Example: Add metadata to the session
        context.set_data('example_plugin_processed', True)

        # Example: Log to file if configured
        if self.config.get('log_to_file', False):
            self._log_to_file(f"Session created: {context.get_data('summary')}")

    def on_context_set(self, context: PluginContext):
        """Called after context is set"""
        self.context_changes += 1

        category = context.get_data('category')
        key = context.get_data('key')

        logger.debug(f"🔧 Example plugin: Context updated - {category}/{key}")

    def on_project_analyzed(self, context: PluginContext):
        """Called after project is analyzed"""
        project_name = context.project.get('name') if context.project else 'Unknown'
        analysis = context.get_data('analysis', {})

        logger.info(f"🔍 Example plugin: Project '{project_name}' analyzed")
        logger.info(f"   Analysis keys: {', '.join(analysis.keys())}")

        # Example: Could send analysis to external service here

    def on_git_logged(self, context: PluginContext):
        """Called after git commits are logged"""
        sessions_created = context.get_data('sessions_created', 0)
        logger.info(f"📦 Example plugin: Git logging complete - {sessions_created} sessions created")

    # Custom Commands

    def show_stats(self):
        """Show plugin statistics"""
        logger.info("📊 Example Plugin Statistics:")
        logger.info(f"   Sessions created: {self.session_count}")
        logger.info(f"   Context changes: {self.context_changes}")
        logger.info(f"   Enabled: {self.enabled}")
        logger.info(f"   Config: {self.config}")

    def reset_stats(self):
        """Reset plugin statistics"""
        self.session_count = 0
        self.context_changes = 0
        logger.info("🔄 Example plugin: Statistics reset")

    def test_command(self, *args):
        """Test command with arguments"""
        logger.info(f"🧪 Example plugin: Test command called")
        logger.info(f"   Arguments: {args}")
        return {"status": "success", "args": args}

    # Helper Methods

    def _log_to_file(self, message: str):
        """Log message to file"""
        output_file = self.config.get('output_file', '/tmp/recall-example-plugin.log')
        try:
            from datetime import datetime
            timestamp = datetime.now().isoformat()
            with open(output_file, 'a') as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            logger.error(f"Failed to write to log file: {e}")


# This allows the plugin to be tested standalone
if __name__ == "__main__":
    # Test the plugin
    config = {
        'log_to_file': False,
        'notify_on_session': True,
    }

    plugin = ExamplePlugin(config=config)
    print(f"Plugin: {plugin.name} v{plugin.version}")
    print(f"Description: {plugin.description}")
    print(f"Author: {plugin.author}")
    print(f"\nConfig Schema:")
    for key, spec in plugin.get_config_schema().items():
        print(f"  {key}: {spec}")

    print(f"\nInitializing...")
    if plugin.initialize():
        print("✅ Plugin initialized successfully")

        print(f"\nRegistered Hooks:")
        for hook in plugin.register_hooks().keys():
            print(f"  - {hook}")

        print(f"\nRegistered Commands:")
        for cmd in plugin.get_commands().keys():
            print(f"  - {cmd}")

        # Test commands
        print(f"\n--- Testing Commands ---")
        plugin.show_stats()
        plugin.test_command("arg1", "arg2")

        plugin.shutdown()
    else:
        print("❌ Plugin initialization failed")
