import os
import yaml
import json
from pathlib import Path

class Config:
    """Manage configuration for AlgoSystem."""
    
    def __init__(self, config_path=None):
        """
        Initialize configuration manager.
        
        Parameters:
        -----------
        config_path : str, optional
            Path to configuration file. If None, uses default locations.
        """
        # Default configuration paths to check
        self.default_paths = [
            os.path.join(os.getcwd(), 'algosystem.yaml'),
            os.path.join(os.getcwd(), 'algosystem.yml'),
            os.path.join(os.getcwd(), 'algosystem.json'),
            os.path.expanduser('~/.algosystem/config.yaml'),
            os.path.expanduser('~/.algosystem/config.yml'),
            os.path.expanduser('~/.algosystem/config.json')
        ]
        
        # Configuration values
        self.config = {}
        
        # Load configuration
        if config_path:
            self.load(config_path)
        else:
            self._load_default_config()
    
    def _load_default_config(self):
        """Load configuration from default paths."""
        for path in self.default_paths:
            if os.path.exists(path):
                self.load(path)
                return
        
        # If no config file found, use default configuration
        self.config = self._default_config()
    
    def _default_config(self):
        """Return default configuration values."""
        return {
            'data': {
                'directory': os.path.expanduser('~/algosystem_data'),
                'default_source': 'local'
            },
            'database': {
                'connection_string': None  # Use default SQLite
            },
            'backtesting': {
                'default_commission': 0.001,
                'default_slippage': 0.0005
            },
            'logging': {
                'level': 'INFO',
                'file': os.path.expanduser('~/.algosystem/logs/algosystem.log')
            }
        }
    
    def load(self, path):
        """
        Load configuration from file.
        
        Parameters:
        -----------
        path : str
            Path to configuration file (YAML or JSON)
        """
        try:
            with open(path, 'r') as f:
                if path.endswith(('.yaml', '.yml')):
                    loaded_config = yaml.safe_load(f)
                elif path.endswith('.json'):
                    loaded_config = json.load(f)
                else:
                    raise ValueError(f"Unsupported configuration file format: {path}")
            
            # Merge with default config (ensuring all required keys exist)
            default = self._default_config()
            
            # Recursive dictionary update
            def update_dict(d, u):
                for k, v in u.items():
                    if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                        d[k] = update_dict(d[k], v)
                    else:
                        d[k] = v
                return d
            
            self.config = update_dict(default, loaded_config)
            
            return True
            
        except Exception as e:
            print(f"Error loading configuration from {path}: {str(e)}")
            return False
    
    def save(self, path=None):
        """
        Save configuration to file.
        
        Parameters:
        -----------
        path : str, optional
            Path to save configuration. If None, uses the first default path.
        """
        if path is None:
            # Use the first YAML path by default
            path = self.default_paths[0]
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        try:
            with open(path, 'w') as f:
                if path.endswith(('.yaml', '.yml')):
                    yaml.dump(self.config, f, default_flow_style=False)
                elif path.endswith('.json'):
                    json.dump(self.config, f, indent=2)
                else:
                    raise ValueError(f"Unsupported configuration file format: {path}")
            
            return True
            
        except Exception as e:
            print(f"Error saving configuration to {path}: {str(e)}")
            return False
    
    def get(self, key, default=None):
        """
        Get configuration value.
        
        Parameters:
        -----------
        key : str
            Configuration key, can use dot notation for nested keys
        default : any, optional
            Default value if key not found
            
        Returns:
        --------
        value : any
            Configuration value
        """
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key, value):
        """
        Set configuration value.
        
        Parameters:
        -----------
        key : str
            Configuration key, can use dot notation for nested keys
        value : any
            Configuration value
        """
        keys = key.split('.')
        config = self.config
        
        # Navigate to the last parent
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value

# Global configuration instance
_config = None

def get_config(config_path=None):
    """
    Get the global configuration instance.
    
    Parameters:
    -----------
    config_path : str, optional
        Path to configuration file
        
    Returns:
    --------
    config : Config
        Configuration instance
    """
    global _config
    
    if _config is None:
        _config = Config(config_path)
    elif config_path:
        _config.load(config_path)
    
    return _config