# Recall Plugin System

The Recall plugin system allows you to extend Recall's functionality with custom features, integrations, and behaviors.

## Plugin Basics

A Recall plugin is a Python module that:
1. Inherits from `RecallPlugin` base class
2. Implements required properties and methods
3. Registers hooks to respond to Recall events
4. Optionally provides custom CLI commands

## Quick Start

### 1. Create a Plugin

```python
from recall_lib.plugin_base import RecallPlugin, PluginContext

class MyPlugin(RecallPlugin):
    @property
    def name(self) -> str:
        return "my-plugin"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "My awesome plugin"

    def initialize(self) -> bool:
        # Setup code here
        return True

    def register_hooks(self):
        return {
            'session_post_create': self.on_session_created,
        }

    def on_session_created(self, context: PluginContext):
        print(f"Session created: {context.get_data('summary')}")
```

### 2. Install the Plugin

Save your plugin to:
- `./plugins/my_plugin.py` (project-local)
- `~/.config/recall/plugins/my_plugin.py` (user-global)

### 3. Configure the Plugin

Add to `~/.config/recall/config.yaml`:

```yaml
plugin_dir: /path/to/your/plugins

plugins:
  my-plugin:
    enabled: true
    # plugin-specific config here
```

### 4. Use the Plugin

```bash
# List loaded plugins
recall --plugins

# Execute plugin command
recall --plugin-command my-plugin:my-command
```

## Plugin API

### Required Properties

```python
@property
def name(self) -> str:
    """Unique plugin identifier"""
    return "my-plugin"

@property
def version(self) -> str:
    """Semantic version (e.g., '1.2.3')"""
    return "1.0.0"

@property
def description(self) -> str:
    """Short description of functionality"""
    return "Does something cool"
```

### Required Methods

```python
def initialize(self) -> bool:
    """
    Called once when plugin is loaded

    Returns:
        True if initialization successful, False otherwise
    """
    # Setup code here
    return True
```

### Optional Methods

```python
def shutdown(self):
    """Called when plugin is unloaded (cleanup)"""
    pass

def get_config_schema(self) -> dict:
    """Define expected configuration parameters"""
    return {
        'api_token': {
            'type': 'string',
            'required': True,
            'description': 'API token for service'
        },
        'sync_interval': {
            'type': 'int',
            'default': 300,
            'description': 'Sync interval in seconds'
        }
    }

def register_hooks(self) -> dict:
    """Register event handlers"""
    return {
        'session_post_create': self.on_session_created,
        'git_commit_analyzed': self.on_commit_analyzed,
    }

def get_commands(self) -> dict:
    """Register custom CLI commands"""
    return {
        'sync': self.sync_command,
        'status': self.status_command,
    }
```

## Available Hooks

### Session Lifecycle
- `session_pre_create` - Before session is created
- `session_post_create` - After session is created
- `session_pre_update` - Before session is updated
- `session_post_update` - After session is updated

### Context Lifecycle
- `context_pre_set` - Before context is set
- `context_post_set` - After context is set
- `context_pre_delete` - Before context is deleted
- `context_post_delete` - After context is deleted

### Project Lifecycle
- `project_pre_create` - Before project is created
- `project_post_create` - After project is created
- `project_pre_analyze` - Before project is analyzed
- `project_post_analyze` - After project is analyzed

### Git Integration
- `git_pre_log` - Before git commits are logged
- `git_post_log` - After git commits are logged
- `git_commit_analyzed` - When a commit is analyzed

### Export/Import
- `export_pre` - Before data export
- `export_post` - After data export

### Query
- `query_pre` - Before query execution
- `query_post` - After query execution

## Plugin Context

Hook handlers receive a `PluginContext` object with:

```python
def on_session_created(self, context: PluginContext):
    # Access project memory
    memory = context.memory

    # Access current project
    project = context.project

    # Get hook-specific data
    summary = context.get_data('summary')

    # Set data for other plugins or caller
    context.set_data('custom_field', 'value')

    # Abort the operation
    context.abort()
```

## Custom Commands

Plugins can register custom CLI commands:

```python
def get_commands(self) -> dict:
    return {
        'sync': self.sync_github,
        'issues': self.list_issues,
    }

def sync_github(self, *args, **kwargs):
    # Command implementation
    return {"status": "success"}

# Usage:
# recall --plugin-command github:sync
# recall --plugin-command github:issues
```

## Configuration

Plugins can access configuration via `self.config`:

```python
def initialize(self) -> bool:
    api_token = self.config.get('api_token')
    if not api_token:
        logger.error("API token not configured")
        return False
    return True
```

## Example: Slack Notification Plugin

```python
from recall_lib.plugin_base import RecallPlugin, PluginContext
import requests

class SlackPlugin(RecallPlugin):
    @property
    def name(self) -> str:
        return "slack"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Send Slack notifications on important events"

    def get_config_schema(self):
        return {
            'webhook_url': {
                'type': 'string',
                'required': True,
                'description': 'Slack webhook URL'
            },
            'notify_on_session': {
                'type': 'bool',
                'default': True
            }
        }

    def initialize(self) -> bool:
        self.webhook_url = self.config.get('webhook_url')
        return bool(self.webhook_url)

    def register_hooks(self):
        return {
            'session_post_create': self.on_session_created,
        }

    def on_session_created(self, context: PluginContext):
        if not self.config.get('notify_on_session', True):
            return

        project = context.project['name']
        summary = context.get_data('summary', 'No summary')

        self._send_slack({
            'text': f"📝 New session logged for *{project}*: {summary}"
        })

    def _send_slack(self, payload: dict):
        try:
            requests.post(self.webhook_url, json=payload)
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
```

## Best Practices

1. **Error Handling**: Always wrap external API calls in try/except
2. **Configuration Validation**: Validate required config in `initialize()`
3. **Logging**: Use `logger` from `recall_lib.logger` for consistent logging
4. **Performance**: Keep hook handlers fast - avoid blocking operations
5. **Documentation**: Document your plugin's config schema and commands
6. **Testing**: Test your plugin standalone before loading into Recall

## Plugin Discovery

Recall searches for plugins in:
1. Current directory: `./plugins/`
2. Global config directory: `~/.config/recall/plugins/`
3. Custom directory specified in config: `plugin_dir` setting

Plugins can be:
- Single Python files: `my_plugin.py`
- Python packages: `my_plugin/__init__.py`

## Debugging Plugins

```bash
# Test plugin standalone
python3 plugins/my_plugin.py

# Check loaded plugins
recall --plugins

# Test plugin commands
recall --plugin-command my-plugin:test

# Check logs
tail -f ~/.local/share/recall/recall.log
```

## Example Plugins

See `example_plugin.py` for a complete working example demonstrating:
- Hook registration
- Custom commands
- Configuration schema
- Context access
- File logging

## Contributing Plugins

To share your plugin with the community:
1. Create a GitHub repository for your plugin
2. Document the plugin in README.md
3. Include config schema and examples
4. Submit to the Recall Plugin Directory (coming soon)

## Advanced: Plugin Packages

For complex plugins, use a package structure:

```
plugins/
  my_plugin/
    __init__.py      # Plugin class here
    api.py           # API integration
    models.py        # Data models
    config.yaml      # Default config
    README.md        # Plugin documentation
```

## Support

- Issues: https://github.com/anthropics/recall/issues
- Documentation: https://docs.recall.dev/plugins
- Examples: https://github.com/anthropics/recall-plugins
