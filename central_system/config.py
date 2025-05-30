"""
Central configuration management for ConsultEase.
Provides a unified interface for accessing configuration settings from various sources.
"""
import os
import json
import logging
import pathlib
import time

logger = logging.getLogger(__name__)


class Config:
    """Central configuration management for ConsultEase."""

    # Default configuration
    DEFAULT_CONFIG = {
        "database": {
            "type": "sqlite",
            "host": "localhost",
            "port": 5432,
            "name": "consultease.db",
            "user": "",
            "password": "",
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 1800,
            "debug": False  # Add option to control SQL debugging
        },
        "mqtt": {
            "broker_host": "localhost",
            "broker_port": 1883,
            "client_id": "consultease_central",
            "username": "",
            "password": "",
            "use_tls": False,
            "tls_ca_certs": None,
            "tls_certfile": None,
            "tls_keyfile": None,
            "tls_insecure": False,
            # Options: "TLSv1.2", "TLSv1.3", "CLIENT_DEFAULT" (for auto-negotiate)
            "tls_version": "CLIENT_DEFAULT",
            "tls_cert_reqs": "CERT_REQUIRED"  # Options: "CERT_REQUIRED", "CERT_OPTIONAL", "CERT_NONE"
        },
        "rfid": {
            "device_path": None,
            "simulation_mode": False,
            "target_vid": "ffff",
            "target_pid": "0035"
        },
        "ui": {
            "fullscreen": True,
            "transition_type": "fade",
            "transition_duration": 300,
            "theme": "light"
        },
        "keyboard": {
            "type": "squeekboard",
            "fallback": "onboard"
        },
        "security": {
            "min_password_length": 8,
            "password_lockout_threshold": 5,
            "password_lockout_duration": 900,  # 15 minutes in seconds
            "session_timeout": 1800,  # 30 minutes in seconds
            "default_admin_password": None,  # Force explicit setting in config or code
            "bcrypt_rounds": 12,  # Control password hashing strength
            "enforce_password_complexity": True  # Require mixed case, numbers, etc.
        },
        "logging": {
            "level": "INFO",
            "file": "consultease.log",
            "max_size": 10485760,  # 10MB
            "backup_count": 5,
            "rfid_level": "INFO"
        },
        "system": {
            "auto_start": True,
            "faculty_image_dir": "images/faculty",
            "ensure_test_faculty_available": False
        }
    }

    # Singleton instance
    _instance = None
    _config = None

    @classmethod
    def instance(cls):
        """Get the singleton instance of the configuration manager."""
        if cls._instance is None:
            cls._instance = Config()
        return cls._instance

    def __init__(self):
        """Initialize the configuration manager."""
        # Prevent multiple initialization of the singleton
        if Config._instance is not None:
            return

        # Load configuration
        self.load_config()

    def load_config(self):
        """Load configuration from file or environment."""
        config_data = self.DEFAULT_CONFIG.copy()

        # Try to load from config file
        config_paths = [
            os.environ.get('CONSULTEASE_CONFIG'),
            'config.json',
            os.path.join(os.path.dirname(__file__), 'config.json'),
            str(pathlib.Path(__file__).resolve().parent.parent / 'config.json')
        ]

        loaded_path = None
        for config_path in config_paths:
            if config_path and os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        file_config = json.load(f)
                        # Update config with file values
                        self._update_dict(config_data, file_config)
                    logger.info(f"Loaded configuration from {config_path}")
                    loaded_path = config_path
                    break
                except Exception as e:
                    logger.error(f"Failed to load configuration from {config_path}: {e}")

        if not loaded_path:
            logger.info(
                "No config.json found, using default configuration. Consider creating a config.json.")

        # Override with environment variables
        self._override_from_env(config_data)

        Config._config = config_data

    @staticmethod
    def _update_dict(target, source):
        """
        Recursively update a dictionary with values from another dictionary.

        Args:
            target (dict): Target dictionary to update
            source (dict): Source dictionary with new values
        """
        for key, value in source.items():
            if isinstance(target.get(key), dict) and isinstance(value, dict):
                Config._update_dict(target[key], value)
            else:
                target[key] = value

    @staticmethod
    def _override_from_env(config_data):
        """
        Override configuration values from environment variables.

        Args:
            config_data (dict): Configuration dictionary to update
        """
        # Database configuration
        config_data['database']['type'] = os.environ.get('DB_TYPE', config_data['database']['type'])
        config_data['database']['host'] = os.environ.get('DB_HOST', config_data['database']['host'])
        config_data['database']['port'] = int(
            os.environ.get('DB_PORT', config_data['database']['port']))
        config_data['database']['name'] = os.environ.get('DB_NAME', config_data['database']['name'])
        config_data['database']['user'] = os.environ.get('DB_USER', config_data['database']['user'])
        config_data['database']['password'] = os.environ.get(
            'DB_PASSWORD', config_data['database']['password'])

        # MQTT configuration
        config_data['mqtt']['broker_host'] = os.environ.get(
            'MQTT_BROKER_HOST', config_data['mqtt']['broker_host'])
        config_data['mqtt']['broker_port'] = int(os.environ.get(
            'MQTT_BROKER_PORT', config_data['mqtt']['broker_port']))
        config_data['mqtt']['username'] = os.environ.get(
            'MQTT_USERNAME', config_data['mqtt']['username'])
        config_data['mqtt']['password'] = os.environ.get(
            'MQTT_PASSWORD', config_data['mqtt']['password'])
        config_data['mqtt']['use_tls'] = os.environ.get(
            'MQTT_USE_TLS', str(
                config_data['mqtt']['use_tls'])).lower() in (
            'true', '1', 'yes')
        config_data['mqtt']['tls_ca_certs'] = os.environ.get(
            'MQTT_TLS_CA_CERTS', config_data['mqtt']['tls_ca_certs'])
        config_data['mqtt']['tls_certfile'] = os.environ.get(
            'MQTT_TLS_CERTFILE', config_data['mqtt']['tls_certfile'])
        config_data['mqtt']['tls_keyfile'] = os.environ.get(
            'MQTT_TLS_KEYFILE', config_data['mqtt']['tls_keyfile'])
        config_data['mqtt']['tls_insecure'] = os.environ.get(
            'MQTT_TLS_INSECURE', str(
                config_data['mqtt']['tls_insecure'])).lower() in (
            'true', '1', 'yes')
        config_data['mqtt']['tls_version'] = os.environ.get(
            'MQTT_TLS_VERSION', config_data['mqtt']['tls_version'])
        config_data['mqtt']['tls_cert_reqs'] = os.environ.get(
            'MQTT_TLS_CERT_REQS', config_data['mqtt']['tls_cert_reqs'])

        # RFID configuration
        config_data['rfid']['simulation_mode'] = os.environ.get(
            'RFID_SIMULATION_MODE', str(
                config_data['rfid']['simulation_mode'])).lower() in (
            'true', '1', 'yes')
        config_data['rfid']['device_path'] = os.environ.get(
            'RFID_DEVICE_PATH', config_data['rfid']['device_path'])

        # UI configuration
        config_data['ui']['fullscreen'] = os.environ.get(
            'CONSULTEASE_FULLSCREEN', str(
                config_data['ui']['fullscreen'])).lower() in (
            'true', '1', 'yes')
        config_data['ui']['theme'] = os.environ.get('CONSULTEASE_THEME', config_data['ui']['theme'])

        # Keyboard configuration
        config_data['keyboard']['type'] = os.environ.get(
            'CONSULTEASE_KEYBOARD', config_data['keyboard']['type'])

        # Logging configuration
        config_data['logging']['level'] = os.environ.get(
            'LOG_LEVEL', config_data['logging']['level'])
        config_data['logging']['rfid_level'] = os.environ.get(
            'LOG_RFID_LEVEL', config_data['logging']['rfid_level'])

    def get(self, key, default=None):
        """
        Get a configuration value by key.

        Args:
            key (str): Configuration key (dot notation for nested keys)
            default: Default value if key is not found

        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = Config._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        # Attempt type conversion for known numeric/boolean fields if value is string
        if isinstance(value, str):
            if value.lower() == 'true':
                return True
            if value.lower() == 'false':
                return False
            if value.isdigit():
                return int(value)
            try:
                return float(value)  # For ports or other numbers
            except ValueError:
                pass  # Not a float

        return value

    def set(self, key, value):
        """
        Set a configuration value by key.

        Args:
            key (str): Configuration key (dot notation for nested keys)
            value: Value to set
        """
        keys = key.split('.')
        config_data = Config._config

        # Navigate to the parent of the target key
        for k in keys[:-1]:
            config_data = config_data.setdefault(k, {})

        # Set the value
        config_data[keys[-1]] = value

    def save(self, config_path=None):
        """
        Save the configuration to a file.

        Args:
            config_path (str, optional): Path to save the configuration file

        Returns:
            bool: True if successful, False otherwise
        """
        if not config_path:
            # Prefer saving to config.json in the project root if it exists or can be created
            # This makes it user-editable easily.
            # Fallback to a location relative to this config file if others fail.
            possible_paths = [
                str(pathlib.Path(__file__).resolve().parent.parent / 'config.json'),
                'config.json',
                os.path.join(os.path.dirname(__file__), 'config.json')
            ]
            # Try to find an existing config.json to overwrite, or use the first preferred path.
            existing_path_to_save = next(
                (p for p in possible_paths if p and os.path.exists(p)),
                possible_paths[0])
            config_path = existing_path_to_save

        try:
            # Ensure directory exists if saving to a nested path (though preferred is project root)
            dir_to_save_to = os.path.dirname(os.path.abspath(config_path))
            if not os.path.exists(dir_to_save_to):
                os.makedirs(dir_to_save_to, exist_ok=True)
                logger.info(f"Created directory for config file: {dir_to_save_to}")

            with open(config_path, 'w') as f:
                json.dump(Config._config, f, indent=4, sort_keys=True)
            logger.info(f"Saved configuration to {config_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save configuration to {config_path}: {e}")
            return False

    def _load_config_from_file(self, config_path=None):
        """
        Load configuration from JSON file.

        Args:
            config_path (str, optional): Path to the config file

        Returns:
            dict: Loaded configuration or empty dict if failed
        """
        try:
            if not config_path:
                # Check standard locations
                config_paths = [
                    os.environ.get('CONSULTEASE_CONFIG'),
                    'config.json',
                    os.path.join(os.path.dirname(__file__), 'config.json'),
                    str(pathlib.Path(__file__).resolve().parent.parent / 'config.json')
                ]

                for path in config_paths:
                    if path and os.path.exists(path):
                        config_path = path
                        break

                if not config_path:
                    logger.warning("No config file found in standard locations")
                    return {}

            # If the config file exists, load it
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r') as f:
                        try:
                            file_config = json.load(f)
                            logger.info(f"Loaded configuration from {config_path}")
                            return file_config
                        except json.JSONDecodeError as e:
                            logger.error(f"Invalid JSON in config file {config_path}: {e}")
                            # Create a backup of the invalid config file
                            backup_file = f"{config_path}.bak.{int(time.time())}"
                            try:
                                import shutil
                                shutil.copy2(config_path, backup_file)
                                logger.info(
                                    f"Created backup of invalid config file at {backup_file}")
                            except Exception as backup_err:
                                logger.error(
                                    f"Failed to create backup of invalid config file: {backup_err}")
                except Exception as e:
                    logger.error(f"Error reading config file {config_path}: {e}")
            else:
                logger.warning(f"Config file {config_path} not found")

                # Create config directory if it doesn't exist
                config_dir = os.path.dirname(config_path)
                if config_dir and not os.path.exists(config_dir):
                    try:
                        os.makedirs(config_dir, exist_ok=True)
                        logger.info(f"Created config directory: {config_dir}")
                    except Exception as e:
                        logger.error(f"Error creating config directory {config_dir}: {e}")

                # Write default config to file if requested
                write_default = os.environ.get(
                    'CONSULTEASE_WRITE_DEFAULT_CONFIG', 'true').lower() in (
                    'true', '1', 'yes')
                if write_default:
                    try:
                        with open(config_path, 'w') as f:
                            json.dump(self.DEFAULT_CONFIG, f, indent=4)
                            logger.info(f"Created default config file at {config_path}")
                    except Exception as e:
                        logger.error(f"Error creating default config file: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in _load_config_from_file: {e}")

        # Return empty dict if we couldn't load the config
        return {}

# Convenience function to get the configuration instance


def get_config():
    """Get the configuration instance."""
    return Config.instance()
