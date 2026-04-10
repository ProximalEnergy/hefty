"""Configuration file management using YAML."""

from pathlib import Path
from typing import Any

import yaml


class ConfigManager:
    """Manages configuration persistence using YAML files."""

    DEFAULT_CONFIG_DIR = Path.home() / ".inspectui"
    DEFAULT_CONFIG_FILE = "config.yaml"

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize the config manager.

        Args:
            config_path: Optional custom config file path.
        """
        if config_path:
            self.config_path = config_path
        else:
            self.config_path = self.DEFAULT_CONFIG_DIR / self.DEFAULT_CONFIG_FILE

        self._config: dict[str, Any] = {}

    def load(self) -> dict[str, Any]:
        """Load configuration from file.

        Returns:
            The loaded configuration dictionary.
        """
        if self.config_path.exists():
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    self._config = yaml.safe_load(f) or {}
            except (OSError, UnicodeDecodeError, yaml.YAMLError):
                self._config = {}
        else:
            self._config = {}

        return self._config

    def save(self) -> None:
        """Save configuration to file."""
        # Ensure directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w") as f:
            yaml.dump(self._config, f, default_flow_style=False)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: The configuration key (supports dot notation for nested keys).
            default: Default value if key doesn't exist.

        Returns:
            The configuration value or default.
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            key: The configuration key (supports dot notation for nested keys).
            value: The value to set.
        """
        keys = key.split(".")
        config = self._config

        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    def delete(self, key: str) -> bool:
        """Delete a configuration value.

        Args:
            key: The configuration key (supports dot notation for nested keys).

        Returns:
            True if the key was deleted, False if it didn't exist.
        """
        keys = key.split(".")
        config = self._config

        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                return False
            config = config[k]

        if keys[-1] in config:
            del config[keys[-1]]
            return True
        return False

    @property
    def config(self) -> dict[str, Any]:
        """Get the full configuration dictionary."""
        return self._config.copy()
