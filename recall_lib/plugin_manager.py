#!/usr/bin/env python3
"""
Plugin Manager - Discovery, loading, and hook execution for Recall plugins
"""
import sys
import importlib.util
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from .plugin_base import RecallPlugin, PluginContext, PluginLoadError, PluginConfigError
from .logger import get_logger

logger = get_logger(__name__)


class PluginManager:
    """
    Manages plugin discovery, loading, and hook execution
    """

    def __init__(self, plugin_dirs: List[str] = None, config: Dict = None):
        """
        Initialize plugin manager

        Args:
            plugin_dirs: List of directories to search for plugins
            config: Configuration dict with plugin settings
        """
        self.plugin_dirs = plugin_dirs or []
        self.config = config or {}
        self._plugins: Dict[str, RecallPlugin] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._enabled = True

    def discover_plugins(self) -> List[str]:
        """
        Discover available plugins in plugin directories

        Returns:
            List of discovered plugin file paths
        """
        discovered = []

        for plugin_dir in self.plugin_dirs:
            path = Path(plugin_dir)
            if not path.exists() or not path.is_dir():
                continue

            # Look for Python files (except __init__.py)
            for plugin_file in path.glob("*.py"):
                if plugin_file.name == "__init__.py":
                    continue
                discovered.append(str(plugin_file))

            # Look for plugin packages (directories with __init__.py)
            for plugin_package in path.iterdir():
                if plugin_package.is_dir() and (plugin_package / "__init__.py").exists():
                    discovered.append(str(plugin_package / "__init__.py"))

        return discovered

    def load_plugin_from_file(self, plugin_path: str) -> Optional[RecallPlugin]:
        """
        Load a plugin from a file

        Args:
            plugin_path: Path to plugin file

        Returns:
            Loaded plugin instance, or None if loading failed
        """
        path = Path(plugin_path)
        if not path.exists():
            logger.error(f"Plugin file not found: {plugin_path}")
            return None

        # Import the module
        module_name = path.stem
        spec = importlib.util.spec_from_file_location(module_name, plugin_path)
        if not spec or not spec.loader:
            logger.error(f"Failed to load plugin spec: {plugin_path}")
            return None

        try:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
        except Exception as e:
            logger.error(f"Failed to import plugin {plugin_path}: {e}")
            return None

        # Find RecallPlugin subclass
        plugin_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, RecallPlugin)
                and attr is not RecallPlugin
            ):
                plugin_class = attr
                break

        if not plugin_class:
            logger.error(f"No RecallPlugin subclass found in {plugin_path}")
            return None

        # Instantiate plugin with config
        try:
            plugin_config = self.config.get("plugins", {}).get(module_name, {})
            plugin = plugin_class(config=plugin_config)
        except Exception as e:
            logger.error(f"Failed to instantiate plugin {module_name}: {e}")
            return None

        return plugin

    def load_plugin(self, plugin: RecallPlugin) -> bool:
        """
        Load and initialize a plugin

        Args:
            plugin: Plugin instance to load

        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            # Validate configuration
            if not plugin.validate_config():
                raise PluginConfigError(f"Invalid configuration for plugin '{plugin.name}'")

            # Initialize plugin
            if not plugin.initialize():
                raise PluginLoadError(f"Plugin '{plugin.name}' initialization failed")

            # Register hooks
            hooks = plugin.register_hooks()
            for hook_name, handler in hooks.items():
                if hook_name not in self._hooks:
                    self._hooks[hook_name] = []
                self._hooks[hook_name].append((plugin.name, handler))

            # Store plugin
            self._plugins[plugin.name] = plugin

            logger.info(f"✅ Loaded plugin: {plugin.name} v{plugin.version}")
            return True

        except (PluginLoadError, PluginConfigError) as e:
            logger.error(f"❌ Failed to load plugin '{plugin.name}': {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error loading plugin '{plugin.name}': {e}")
            return False

    def load_all_plugins(self) -> int:
        """
        Discover and load all plugins

        Returns:
            Number of plugins successfully loaded
        """
        plugin_files = self.discover_plugins()
        loaded_count = 0

        for plugin_file in plugin_files:
            plugin = self.load_plugin_from_file(plugin_file)
            if plugin and self.load_plugin(plugin):
                loaded_count += 1

        if loaded_count > 0:
            logger.info(f"📦 Loaded {loaded_count} plugin(s)")

        return loaded_count

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin

        Args:
            plugin_name: Name of plugin to unload

        Returns:
            True if unloaded successfully, False otherwise
        """
        if plugin_name not in self._plugins:
            logger.error(f"Plugin '{plugin_name}' not loaded")
            return False

        plugin = self._plugins[plugin_name]

        # Call shutdown
        try:
            plugin.shutdown()
        except Exception as e:
            logger.warning(f"Error during plugin shutdown: {e}")

        # Remove hooks
        for hook_name, handlers in self._hooks.items():
            self._hooks[hook_name] = [
                (name, handler) for name, handler in handlers if name != plugin_name
            ]

        # Remove plugin
        del self._plugins[plugin_name]

        logger.info(f"🗑️ Unloaded plugin: {plugin_name}")
        return True

    def get_plugin(self, plugin_name: str) -> Optional[RecallPlugin]:
        """Get a loaded plugin by name"""
        return self._plugins.get(plugin_name)

    def list_plugins(self) -> List[Dict[str, Any]]:
        """
        List all loaded plugins

        Returns:
            List of plugin metadata dicts
        """
        return [plugin.get_metadata() for plugin in self._plugins.values()]

    def execute_hook(self, hook_name: str, context: PluginContext) -> PluginContext:
        """
        Execute all handlers registered for a hook

        Args:
            hook_name: Name of hook to execute
            context: Plugin context object

        Returns:
            Modified context object
        """
        if not self._enabled:
            return context

        if hook_name not in self._hooks:
            return context

        for plugin_name, handler in self._hooks[hook_name]:
            plugin = self._plugins.get(plugin_name)
            if not plugin or not plugin.enabled:
                continue

            try:
                handler(context)

                # Check if plugin aborted the operation
                if context.is_aborted():
                    logger.info(f"🛑 Operation aborted by plugin '{plugin_name}'")
                    break

            except Exception as e:
                logger.error(f"❌ Error in plugin '{plugin_name}' hook '{hook_name}': {e}")
                # Continue with other plugins

        return context

    def execute_command(self, command_name: str, *args, **kwargs) -> Any:
        """
        Execute a plugin command

        Args:
            command_name: Command name in format 'plugin-name:command'
            *args: Positional arguments for command
            **kwargs: Keyword arguments for command

        Returns:
            Command result
        """
        # Parse command
        if ":" not in command_name:
            raise ValueError(
                f"Invalid command format: '{command_name}' (expected 'plugin:command')"
            )

        plugin_name, cmd = command_name.split(":", 1)

        # Get plugin
        plugin = self.get_plugin(plugin_name)
        if not plugin:
            raise ValueError(f"Plugin '{plugin_name}' not loaded")

        if not plugin.enabled:
            raise ValueError(f"Plugin '{plugin_name}' is disabled")

        # Get command handler
        commands = plugin.get_commands()
        if cmd not in commands:
            raise ValueError(f"Command '{cmd}' not found in plugin '{plugin_name}'")

        handler = commands[cmd]

        # Execute command
        try:
            return handler(*args, **kwargs)
        except Exception as e:
            logger.error(f"❌ Error executing command '{command_name}': {e}")
            raise

    def enable(self):
        """Enable all plugin functionality"""
        self._enabled = True

    def disable(self):
        """Disable all plugin functionality (hooks won't execute)"""
        self._enabled = False

    def shutdown_all(self):
        """Shutdown all plugins"""
        for plugin_name in list(self._plugins.keys()):
            self.unload_plugin(plugin_name)


# Global plugin manager instance
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager(config: Dict = None) -> PluginManager:
    """
    Get the global plugin manager instance

    Args:
        config: Configuration dict (only used on first call)

    Returns:
        PluginManager instance
    """
    global _plugin_manager

    if _plugin_manager is None:
        # Get plugin directories from config
        plugin_dirs = []

        if config:
            # User plugin directory
            if "plugin_dir" in config:
                plugin_dirs.append(config["plugin_dir"])

            # Built-in plugins
            recall_dir = Path(__file__).parent.parent
            builtin_plugins = recall_dir / "plugins"
            if builtin_plugins.exists():
                plugin_dirs.append(str(builtin_plugins))

        _plugin_manager = PluginManager(plugin_dirs=plugin_dirs, config=config)

    return _plugin_manager


def initialize_plugins(config: Dict = None) -> int:
    """
    Initialize the plugin system and load all plugins

    Args:
        config: Configuration dict

    Returns:
        Number of plugins loaded
    """
    manager = get_plugin_manager(config)
    return manager.load_all_plugins()
