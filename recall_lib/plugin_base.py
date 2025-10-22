#!/usr/bin/env python3
"""
Plugin Base - Abstract base class for Recall plugins
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from pathlib import Path


class PluginHookPoints:
    """
    Enumeration of available hook points in Recall

    Plugins can subscribe to these hooks to extend functionality
    """

    # Session lifecycle hooks
    SESSION_PRE_CREATE = "session_pre_create"
    SESSION_POST_CREATE = "session_post_create"
    SESSION_PRE_UPDATE = "session_pre_update"
    SESSION_POST_UPDATE = "session_post_update"

    # Context lifecycle hooks
    CONTEXT_PRE_SET = "context_pre_set"
    CONTEXT_POST_SET = "context_post_set"
    CONTEXT_PRE_DELETE = "context_pre_delete"
    CONTEXT_POST_DELETE = "context_post_delete"

    # Project lifecycle hooks
    PROJECT_PRE_CREATE = "project_pre_create"
    PROJECT_POST_CREATE = "project_post_create"
    PROJECT_PRE_ANALYZE = "project_pre_analyze"
    PROJECT_POST_ANALYZE = "project_post_analyze"

    # Git integration hooks
    GIT_PRE_LOG = "git_pre_log"
    GIT_POST_LOG = "git_post_log"
    GIT_COMMIT_ANALYZED = "git_commit_analyzed"

    # Export hooks
    EXPORT_PRE = "export_pre"
    EXPORT_POST = "export_post"

    # Query hooks
    QUERY_PRE = "query_pre"
    QUERY_POST = "query_post"


class RecallPlugin(ABC):
    """
    Abstract base class for Recall plugins

    All plugins must inherit from this class and implement the required methods.
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the plugin

        Args:
            config: Plugin-specific configuration dict
        """
        self.config = config or {}
        self._hooks = {}
        self._enabled = True

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name (unique identifier)"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version (semver format)"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Short description of plugin functionality"""
        pass

    @property
    def author(self) -> str:
        """Plugin author (optional)"""
        return "Unknown"

    @property
    def enabled(self) -> bool:
        """Whether the plugin is currently enabled"""
        return self._enabled

    def enable(self):
        """Enable the plugin"""
        self._enabled = True

    def disable(self):
        """Disable the plugin"""
        self._enabled = False

    @abstractmethod
    def initialize(self) -> bool:
        """
        Initialize the plugin (called once on load)

        Returns:
            True if initialization successful, False otherwise
        """
        pass

    def shutdown(self):
        """
        Shutdown the plugin (called on cleanup)

        Override this method to perform cleanup operations.
        """
        pass

    def register_hooks(self) -> Dict[str, callable]:
        """
        Register hook handlers

        Returns:
            Dict mapping hook names to handler functions

        Example:
            {
                'session_post_create': self.on_session_created,
                'git_commit_analyzed': self.on_commit_analyzed,
            }
        """
        return {}

    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get configuration schema for this plugin

        Returns:
            Dict describing expected configuration parameters

        Example:
            {
                'api_token': {'type': 'string', 'required': True},
                'sync_interval': {'type': 'int', 'default': 300},
            }
        """
        return {}

    def validate_config(self) -> bool:
        """
        Validate plugin configuration

        Returns:
            True if configuration is valid, False otherwise
        """
        schema = self.get_config_schema()

        for key, spec in schema.items():
            if spec.get("required", False) and key not in self.config:
                return False

        return True

    def get_commands(self) -> Dict[str, callable]:
        """
        Register custom CLI commands

        Returns:
            Dict mapping command names to handler functions

        Example:
            {
                'github-sync': self.sync_github,
                'github-issues': self.list_issues,
            }
        """
        return {}

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get plugin metadata

        Returns:
            Dict with plugin metadata
        """
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "enabled": self.enabled,
            "config_schema": self.get_config_schema(),
        }


class PluginContext:
    """
    Context object passed to plugin hooks

    Provides access to Recall internals and allows plugins to modify behavior
    """

    def __init__(self, memory=None, project=None, data=None):
        """
        Initialize plugin context

        Args:
            memory: ProjectMemory instance
            project: Current project dict
            data: Hook-specific data
        """
        self.memory = memory
        self.project = project
        self.data = data or {}
        self._abort = False
        self._modified = {}

    def abort(self):
        """Signal that the operation should be aborted"""
        self._abort = True

    def is_aborted(self) -> bool:
        """Check if operation was aborted by a plugin"""
        return self._abort

    def set_data(self, key: str, value: Any):
        """Set data to pass to next plugin or back to caller"""
        self._modified[key] = value

    def get_data(self, key: str, default=None) -> Any:
        """Get data (checks modified data first, then original)"""
        if key in self._modified:
            return self._modified[key]
        return self.data.get(key, default)

    def get_modified_data(self) -> Dict[str, Any]:
        """Get all modified data"""
        return self._modified.copy()


class PluginError(Exception):
    """Exception raised by plugin operations"""

    pass


class PluginLoadError(PluginError):
    """Exception raised when plugin fails to load"""

    pass


class PluginConfigError(PluginError):
    """Exception raised when plugin configuration is invalid"""

    pass
