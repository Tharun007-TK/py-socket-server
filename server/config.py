#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuration Module for Python Socket Server
--------------------------------------------
Handles loading and managing server configuration from various sources:
- Default configuration
- Configuration file (JSON)
- Command-line arguments

This module centralizes all configuration-related functionality.
"""

import os
import json
import logging
import argparse


class ServerConfig:
    """
    Server configuration manager.
    
    Loads and provides access to server configuration settings from various sources,
    with the following precedence (highest to lowest):
    1. Command-line arguments
    2. Configuration file
    3. Default values
    """
    
    # Default configuration settings
    DEFAULT_CONFIG = {
        "host": "0.0.0.0",
        "port": 8000,
        "document_root": "htdocs",
        "root_directory": "htdocs",  # Alias for backward compatibility
        "directory_listing": True,
        "enable_directory_listing": True,  # Alias for backward compatibility
        "enable_cache": True,
        "enable_caching": True,  # Alias for backward compatibility
        "cache_max_size": 100,
        "cache_max_age": 3600,
        "log_level": "INFO",
        "log_file": "server.log",
        "log_max_size": 10485760,  # 10 MB
        "log_backup_count": 5,
        "colored_logging": True,
        "use_colored_logging": True,  # Alias for backward compatibility
        "max_threads": 20,
        "thread_pool_size": 20,  # Alias for backward compatibility
        "request_timeout": 30,
        "socket_timeout": 30,  # Alias for backward compatibility
        "enable_keep_alive": True,
        "keep_alive_timeout": 5,
        "max_request_size": 10485760,  # 10 MB
        "allowed_file_types": None,  # None means all file types are allowed
        "enable_ssl": False,
        "ssl_cert": "cert.pem",
        "ssl_key": "key.pem",
        "ssl_cert_file": "cert.pem",  # Alias for backward compatibility
        "ssl_key_file": "key.pem",  # Alias for backward compatibility
        "ssl_password": None,
        "enable_server_status": True,
        "status_endpoint": True,  # Alias for backward compatibility
        "connection_queue": 10,
        "enable_browser_caching": True,
        "browser_cache_time": 86400,
        "enable_security_headers": True,
        "enable_cors": True,
        "cors_allow_origin": "*",
        "enable_file_uploads": True,
        "max_upload_size": 10485760,  # 10 MB
        "show_hidden_files": False
    }
    
    def __init__(self, config_file=None, **kwargs):
        """
        Initialize the configuration with values from file and kwargs.
        
        Args:
            config_file: Path to the configuration file
            **kwargs: Additional configuration parameters that override file values
        """
        self._config = self.DEFAULT_CONFIG.copy()
        self.logger = logging.getLogger(__name__)
        
        # Load from file if specified
        if config_file:
            self.load_from_file(config_file)
            
        # Override with kwargs
        for key, value in kwargs.items():
            self._config[key] = value
    
    def load_from_file(self, config_path="config.json"):
        """
        Load configuration from a JSON file.
        
        Args:
            config_path: Path to the configuration file (default: config.json)
            
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                    self._config.update(file_config)
                    self.logger.info(f"Loaded configuration from {config_path}")
                return True
            else:
                self.logger.warning(f"Configuration file {config_path} not found. Using defaults.")
                return False
        except Exception as e:
            self.logger.error(f"Error loading configuration: {e}")
            return False
    
    def save_to_file(self, config_path="config.json"):
        """
        Save current configuration to a JSON file.
        
        Args:
            config_path: Path to save the configuration file (default: config.json)
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            with open(config_path, 'w') as f:
                json.dump(self._config, f, indent=4)
            self.logger.info(f"Configuration saved to {config_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
    
    def load_from_args(self, args=None):
        """
        Parse command line arguments and update configuration.
        
        Args:
            args: Command line arguments to parse (default: None, uses sys.argv)
            
        Returns:
            argparse.Namespace: Parsed arguments
        """
        parser = argparse.ArgumentParser(description='Python Socket Web Server')
        parser.add_argument('-c', '--config', default='config.json', 
                            help='Path to configuration file')
        parser.add_argument('-p', '--port', type=int, 
                            help='Server port (overrides config file)')
        parser.add_argument('-d', '--directory', 
                            help='Root directory (overrides config file)')
        parser.add_argument('-l', '--log-level', 
                            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                            help='Logging level')
        parser.add_argument('--host', 
                            help='Host address to bind (overrides config file)')
        parser.add_argument('--enable-ssl', action='store_true',
                            help='Enable SSL/HTTPS')
        parser.add_argument('--ssl-cert', 
                            help='Path to SSL certificate file')
        parser.add_argument('--ssl-key', 
                            help='Path to SSL key file')
        parser.add_argument('--auto-reload', action='store_true',
                            help='Enable auto-reload for development')
        
        parsed_args = parser.parse_args(args)
        
        # First load from config file if specified
        if parsed_args.config != 'config.json':
            self.load_from_file(parsed_args.config)
        
        # Override with command line arguments
        if parsed_args.port:
            self._config['port'] = parsed_args.port
        if parsed_args.directory:
            self._config['root_directory'] = os.path.abspath(parsed_args.directory)
        if parsed_args.log_level:
            self._config['log_level'] = parsed_args.log_level
        if parsed_args.host:
            self._config['host'] = parsed_args.host
        if parsed_args.enable_ssl:
            self._config['enable_ssl'] = True
        if parsed_args.ssl_cert:
            self._config['ssl_cert_file'] = parsed_args.ssl_cert
        if parsed_args.ssl_key:
            self._config['ssl_key_file'] = parsed_args.ssl_key
        if parsed_args.auto_reload:
            self._config['auto_reload'] = True
        
        return parsed_args
    
    def get(self, key, default=None):
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key is not found
            
        Returns:
            Value for the key or default if not found
        """
        return self._config.get(key, default)
    
    def set(self, key, value):
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Value to set
        """
        self._config[key] = value
    
    def get_all(self):
        """
        Get all configuration values.
        
        Returns:
            dict: All configuration values
        """
        return self._config.copy()
    
    # Property accessors for common configuration values
    @property
    def host(self):
        return self.get('host')
    
    @property
    def port(self):
        return self.get('port')
    
    @property
    def document_root(self):
        return self.get('document_root')
    
    @property
    def directory_listing(self):
        return self.get('directory_listing')
    
    @property
    def enable_cache(self):
        return self.get('enable_cache')
    
    @property
    def cache_max_size(self):
        return self.get('cache_max_size')
    
    @property
    def cache_max_age(self):
        return self.get('cache_max_age')
    
    @property
    def log_level(self):
        return self.get('log_level')
    
    @property
    def log_file(self):
        return self.get('log_file')
    
    @property
    def colored_logging(self):
        return self.get('colored_logging')
    
    @property
    def max_threads(self):
        return self.get('max_threads')
    
    @property
    def request_timeout(self):
        return self.get('request_timeout')
    
    @property
    def connection_queue(self):
        return self.get('connection_queue')
    
    @property
    def enable_ssl(self):
        return self.get('enable_ssl')
    
    @property
    def ssl_cert(self):
        return self.get('ssl_cert')
    
    @property
    def ssl_key(self):
        return self.get('ssl_key')
    
    @property
    def ssl_password(self):
        return self.get('ssl_password')
    
    @property
    def server_name(self):
        return self.get('server_name', 'Python Socket Server/1.0')
    
    @property
    def server_version(self):
        return self.get('server_version', '1.0.0')
    
    @property
    def enable_server_status(self):
        return self.get('enable_server_status', True)
    
    @property
    def allowed_file_types(self):
        return self.get('allowed_file_types')
    
    @property
    def enable_security_headers(self):
        return self.get('enable_security_headers', True)
    
    @property
    def enable_cors(self):
        return self.get('enable_cors', True)
    
    @property
    def cors_allow_origin(self):
        return self.get('cors_allow_origin', '*')
    
    @property
    def enable_browser_caching(self):
        return self.get('enable_browser_caching', True)
    
    @property
    def browser_cache_time(self):
        return self.get('browser_cache_time', 86400)
    
    @property
    def show_hidden_files(self):
        return self.get('show_hidden_files', False)
    
    @property
    def max_request_size(self):
        return self.get('max_request_size', 10485760)
    
    @property
    def enable_keep_alive(self):
        return self.get('enable_keep_alive', True)
    
    @property
    def keep_alive_timeout(self):
        return self.get('keep_alive_timeout', 5)
    
    @property
    def active_connections(self):
        return self.get('active_connections', 0)
    
    @active_connections.setter
    def active_connections(self, value):
        self.set('active_connections', value)
    
    @property
    def start_time(self):
        return self.get('start_time', 0)
    
    @start_time.setter
    def start_time(self, value):
        self.set('start_time', value)


# Global configuration instance
config = ServerConfig()


def init_config(config_file="config.json", args=None):
    """
    Initialize configuration from file and command line arguments.
    
    Args:
        config_file: Path to configuration file
        args: Command line arguments
        
    Returns:
        ServerConfig: Configuration instance
    """
    # Load from file first
    config.load_from_file(config_file)
    
    # Then override with command line arguments
    config.load_from_args(args)
    
    return config


if __name__ == "__main__":
    # Test configuration loading
    conf = init_config()
    print(json.dumps(conf.get_all(), indent=2))