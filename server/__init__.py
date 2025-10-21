#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Python Socket HTTP Server
------------------------
A modular, production-ready HTTP server implementation using only Python's socket library.

This package provides a complete HTTP server implementation with features such as:
- Static file serving
- Directory listing
- Form handling
- File caching
- Multithreading
- SSL/HTTPS support
- Configuration options
- And more
"""

__version__ = '1.0.0'
__author__ = 'GitHub Copilot'

from .server import WebServer
from .config import ServerConfig
from .handler import RequestHandler
from .utils import FileCache, setup_logging

# Make these classes available at the package level
__all__ = ['WebServer', 'ServerConfig', 'RequestHandler', 'FileCache', 'setup_logging']