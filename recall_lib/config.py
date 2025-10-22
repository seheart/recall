#!/usr/bin/env python3
"""
Configuration management for Recall - supports global and per-project configs
"""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from .logger import get_logger

logger = get_logger(__name__)


class RecallConfig:
    """Manages configuration from YAML files with defaults and override support"""

    DEFAULT_CONFIG = {
        'database': {
            'path': None,  # Will use default if None
            'pool_size': 5,
            'cache_ttl': 300,  # 5 minutes
        },
        'defaults': {
            'auto_analyze': True,
            'git_hooks': True,
            'max_sessions_display': 3,
        },
        'output': {
            'theme': 'tokyo-night',  # 'tokyo-night', 'gruvbox', 'plain'
            'color': True,
            'verbose': False,
        },
        'analysis': {
            'show_progress': True,
            'incremental': False,  # Future feature
        },
        'integrations': {
            'github': {
                'enabled': False,
                'token': None,  # Can use ${GITHUB_TOKEN} for env var
            },
            'notion': {
                'enabled': False,
                'token': None,
            },
        },
        'plugins': [],  # List of enabled plugins
    }

    def __init__(self, project_dir: Optional[str] = None):
        """
        Initialize configuration system

        Args:
            project_dir: Optional project directory for per-project config
        """
        self.project_dir = project_dir
        self.config = self._load_config()

    def _get_global_config_path(self) -> Path:
        """Get path to global configuration file"""
        config_dir = Path.home() / '.config' / 'recall'
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / 'config.yaml'

    def _get_project_config_path(self) -> Optional[Path]:
        """Get path to project-specific configuration file"""
        if not self.project_dir:
            return None

        project_config = Path(self.project_dir) / '.recall' / 'config.yaml'
        return project_config if project_config.exists() else None

    def _expand_env_vars(self, value: Any) -> Any:
        """
        Expand environment variables in config values

        Supports ${VAR_NAME} syntax

        Args:
            value: Config value (can be dict, list, string, etc.)

        Returns:
            Value with environment variables expanded
        """
        if isinstance(value, str):
            # Replace ${VAR_NAME} with environment variable value
            import re
            def replace_env(match):
                var_name = match.group(1)
                return os.environ.get(var_name, match.group(0))

            return re.sub(r'\$\{([A-Za-z0-9_]+)\}', replace_env, value)

        elif isinstance(value, dict):
            return {k: self._expand_env_vars(v) for k, v in value.items()}

        elif isinstance(value, list):
            return [self._expand_env_vars(item) for item in value]

        else:
            return value

    def _load_yaml(self, path: Path) -> Dict:
        """
        Load YAML config file

        Args:
            path: Path to YAML file

        Returns:
            Parsed YAML as dict
        """
        try:
            with open(path, 'r') as f:
                content = yaml.safe_load(f)
                return content if content else {}
        except FileNotFoundError:
            return {}
        except yaml.YAMLError as e:
            logger.warning(f"Failed to parse config file {path}: {e}")
            return {}

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """
        Deep merge two dictionaries (override takes precedence)

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def _load_config(self) -> Dict:
        """
        Load configuration with precedence: DEFAULT < global < project

        Returns:
            Final merged configuration
        """
        # Start with defaults
        config = self.DEFAULT_CONFIG.copy()

        # Load global config
        global_config_path = self._get_global_config_path()
        if global_config_path.exists():
            global_config = self._load_yaml(global_config_path)
            config = self._deep_merge(config, global_config)

        # Load project-specific config
        project_config_path = self._get_project_config_path()
        if project_config_path:
            project_config = self._load_yaml(project_config_path)
            config = self._deep_merge(config, project_config)

        # Expand environment variables
        config = self._expand_env_vars(config)

        return config

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated key path

        Args:
            key_path: Dot-separated key path (e.g., 'database.pool_size')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value

    def set(self, key_path: str, value: Any, persist: bool = False) -> None:
        """
        Set configuration value

        Args:
            key_path: Dot-separated key path (e.g., 'database.pool_size')
            value: Value to set
            persist: If True, save to global config file
        """
        keys = key_path.split('.')
        target = self.config

        # Navigate to parent dict
        for key in keys[:-1]:
            if key not in target:
                target[key] = {}
            target = target[key]

        # Set value
        target[keys[-1]] = value

        # Persist if requested
        if persist:
            self.save_global()

    def save_global(self) -> None:
        """Save current configuration to global config file"""
        config_path = self._get_global_config_path()

        try:
            with open(config_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
            logger.info(f"✅ Configuration saved to {config_path}")
        except Exception as e:
            logger.error(f"❌ Failed to save configuration: {e}")

    def create_default_config(self) -> None:
        """Create default global configuration file"""
        config_path = self._get_global_config_path()

        if config_path.exists():
            logger.warning(f"⚠️  Configuration file already exists: {config_path}")
            return

        try:
            with open(config_path, 'w') as f:
                f.write("""# Recall Configuration
# Global configuration for the Recall project memory system

database:
  # Database file path (null = use default: ~/.local/share/recall/projects.db)
  path: null
  # Connection pool size
  pool_size: 5
  # Cache TTL in seconds
  cache_ttl: 300

defaults:
  # Auto-analyze projects on creation
  auto_analyze: true
  # Install git hooks by default
  git_hooks: true
  # Maximum number of recent sessions to display
  max_sessions_display: 3

output:
  # Theme: 'tokyo-night', 'gruvbox', 'plain'
  theme: 'tokyo-night'
  # Enable colored output
  color: true
  # Verbose output
  verbose: false

analysis:
  # Show progress indicators during analysis
  show_progress: true
  # Use incremental analysis (only scan changed files)
  incremental: false

integrations:
  github:
    enabled: false
    # Use ${GITHUB_TOKEN} to read from environment variable
    token: null

  notion:
    enabled: false
    token: null

# List of enabled plugins
plugins: []
""")
            logger.info(f"✅ Created default configuration: {config_path}")
        except Exception as e:
            logger.error(f"❌ Failed to create configuration file: {e}")

    def show(self) -> None:
        """Display current configuration"""
        logger.info("📋 Current Recall Configuration:\n")
        logger.info(yaml.dump(self.config, default_flow_style=False, sort_keys=False))


# Global config instance
_global_config: Optional[RecallConfig] = None


def get_config(project_dir: Optional[str] = None, reload: bool = False) -> RecallConfig:
    """
    Get global configuration instance (singleton)

    Args:
        project_dir: Optional project directory for project-specific config
        reload: Force reload configuration from files

    Returns:
        RecallConfig instance
    """
    global _global_config

    if _global_config is None or reload or project_dir:
        _global_config = RecallConfig(project_dir=project_dir)

    return _global_config


if __name__ == "__main__":
    # Test the configuration system
    logger.info("🧪 Testing RecallConfig...")

    config = RecallConfig()

    # Test getting values
    logger.info(f"Database pool size: {config.get('database.pool_size')}")
    logger.info(f"Theme: {config.get('output.theme')}")
    logger.info(f"Non-existent key: {config.get('foo.bar', 'default_value')}")

    # Test setting values
    config.set('output.theme', 'gruvbox')
    logger.info(f"Updated theme: {config.get('output.theme')}")

    # Show full config
    config.show()

    logger.info("\n✅ Configuration test complete!")
