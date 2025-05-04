import yaml
import os
import logging
from pathlib import Path
import copy

class ConfigManager:
    """Configuration manager that handles loading and saving YAML config files."""
    
    def __init__(self, config_path="config/user_config.yaml", default_config_path="config/default_config.yaml"):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to user configuration file
            default_config_path: Path to default configuration file
        """
        self.config_path = config_path
        self.default_config_path = default_config_path
        self.config = {}
        
        # Load default configuration if it exists
        if os.path.exists(default_config_path):
            logging.debug(f"Loading default configuration from {default_config_path}")
            try:
                with open(default_config_path, 'r') as f:
                    self.config = yaml.safe_load(f) or {}
            except Exception as e:
                logging.error(f"Error loading default configuration: {e}")
        
        # Load user configuration and merge with defaults
        if os.path.exists(config_path):
            logging.debug(f"Loading user configuration from {config_path}")
            try:
                with open(config_path, 'r') as f:
                    user_config = yaml.safe_load(f) or {}
                    self._deep_update(self.config, user_config)
            except Exception as e:
                logging.error(f"Error loading user configuration: {e}")
        else:
            # Create user config directory if it doesn't exist
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            logging.info(f"User configuration not found, creating empty file at {config_path}")
            self.save()
    
    def get(self, key, default=None):
        """
        Get a configuration value.
        
        Args:
            key: Configuration key (can be nested using dot notation)
            default: Default value if key not found
        
        Returns:
            Configuration value or default
        """
        # Handle nested keys with dot notation
        if '.' in key:
            parts = key.split('.')
            value = self.config
            for part in parts:
                if isinstance(value, dict) and part in value:
                    value = value[part]
                else:
                    return default
            return value
        
        # Simple key lookup
        return self.config.get(key, default)
    
    def set(self, key, value):
        """
        Set a configuration value.
        
        Args:
            key: Configuration key (can be nested using dot notation)
            value: Value to set
        """
        # Handle nested keys with dot notation
        if '.' in key:
            parts = key.split('.')
            config = self.config
            for part in parts[:-1]:
                if part not in config:
                    config[part] = {}
                config = config[part]
            config[parts[-1]] = value
        else:
            # Simple key update
            self.config[key] = value
    
    def save(self, path=None):
        """
        Save configuration to file.
        
        Args:
            path: Optional path to save to (defaults to config_path)
        
        Returns:
            True if successful, False otherwise
        """
        save_path = path or self.config_path
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # Save configuration
            with open(save_path, 'w') as f:
                yaml.dump(self.config, f, default_flow_style=False)
            
            logging.debug(f"Configuration saved to {save_path}")
            return True
        except Exception as e:
            logging.error(f"Error saving configuration: {e}")
            return False
    
    def _deep_update(self, source, update):
        """
        Deep update a nested dictionary.
        
        Args:
            source: Source dictionary to update
            update: Dictionary with updates to apply
        """
        for key, value in update.items():
            if isinstance(value, dict) and key in source and isinstance(source[key], dict):
                # Recursive update for nested dictionaries
                self._deep_update(source[key], value)
            else:
                # Simple update for non-dictionary values
                source[key] = value
    
    def get_all(self):
        """
        Get the entire configuration.
        
        Returns:
            A deep copy of the configuration dictionary
        """
        return copy.deepcopy(self.config)
    
    def reset_to_defaults(self):
        """
        Reset configuration to defaults.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load default configuration
            if os.path.exists(self.default_config_path):
                with open(self.default_config_path, 'r') as f:
                    self.config = yaml.safe_load(f) or {}
                logging.info("Configuration reset to defaults")
                return True
            else:
                logging.error(f"Default configuration not found at {self.default_config_path}")
                return False
        except Exception as e:
            logging.error(f"Error resetting configuration: {e}")
            return False