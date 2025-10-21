#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Utility Module for Python Socket Server
---------------------------------------
Contains helper functions and classes used throughout the server:
- FileCache: For caching frequently accessed files
- Logging setup functions
- MIME type detection
- Path security validation
- Request/response parsing helpers
"""

import os
import time
import logging
import mimetypes
from logging.handlers import RotatingFileHandler
from collections import OrderedDict
import socket
import re

# Try to import colorama for colored logging
try:
    import colorama
    from colorama import Fore, Style
    colorama.init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False


class FileCache:
    """
    Cache for frequently requested files to improve performance.
    
    Uses an OrderedDict to maintain LRU (Least Recently Used) order
    and supports maximum size and age limits.
    """
    
    def __init__(self, max_size=100, max_age=3600):
        """
        Initialize the file cache.
        
        Args:
            max_size: Maximum number of files to cache
            max_age: Maximum age of cached files in seconds
        """
        self.max_size = max_size
        self.max_age = max_age
        self.cache = OrderedDict()
        self.logger = logging.getLogger('FileCache')
        self.hits = 0
        self.misses = 0
        self.total_requests = 0
        
    def get(self, filepath):
        """
        Get a file from the cache.
        
        Args:
            filepath: Path to the file
            
        Returns:
            Tuple of (content, last_modified) or None if not in cache
        """
        self.total_requests += 1
        
        if filepath in self.cache:
            entry = self.cache[filepath]
            
            # Check if the entry is still valid
            current_time = time.time()
            if current_time - entry['timestamp'] <= self.max_age:
                # Move to end to mark as most recently used
                self.cache.move_to_end(filepath)
                self.hits += 1
                self.logger.debug(f"Cache hit: {filepath}")
                return entry['content'], entry['last_modified']
            
            # Entry expired
            self.logger.debug(f"Cache expired: {filepath}")
            del self.cache[filepath]
            
        self.misses += 1
        return None, None
        
    def set(self, filepath, content, last_modified):
        """
        Add a file to the cache.
        
        Args:
            filepath: Path to the file
            content: File content
            last_modified: Last modified time of the file
        """
        # Skip if cache is disabled (max_size=0)
        if self.max_size <= 0:
            return
            
        # Check if we need to remove the oldest item
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)  # Remove oldest item
            
        self.cache[filepath] = {
            'content': content,
            'last_modified': last_modified,
            'timestamp': time.time()
        }
        self.logger.debug(f"Added to cache: {filepath}")
        
    def clear(self):
        """Clear the cache."""
        self.cache.clear()
        self.logger.info("Cache cleared")
        
    def stats(self):
        """
        Return cache statistics.
        
        Returns:
            dict: Cache statistics
        """
        hit_ratio = self.hits / self.total_requests if self.total_requests > 0 else 0
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'max_age': self.max_age,
            'hits': self.hits,
            'misses': self.misses,
            'total_requests': self.total_requests,
            'hit_ratio': hit_ratio,
            'memory_usage_estimate': sum(len(item['content']) for item in self.cache.values())
        }


def setup_logging(log_level='INFO', log_file=None, max_size=10485760, backup_count=5, use_colored_logging=True):
    """
    Set up logging configuration.
    
    Args:
        log_level: Logging level (default: INFO)
        log_file: Log file path (default: None, console only)
        max_size: Maximum log file size in bytes (default: 10MB)
        backup_count: Number of backup logs to keep (default: 5)
        use_colored_logging: Whether to use colored logging in console (default: True)
    
    Returns:
        logging.Logger: Root logger instance
    """
    # Convert log level string to constant
    log_level_value = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure basic logging format
    logging.basicConfig(
        level=log_level_value,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    root_logger = logging.getLogger()
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set up file handler if log_file is specified
    if log_file:
        try:
            file_handler = RotatingFileHandler(
                log_file, 
                maxBytes=max_size, 
                backupCount=backup_count
            )
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            root_logger.addHandler(file_handler)
        except Exception as e:
            print(f"Error setting up log file: {e}")
    
    # Set up console handler with colored output if available and enabled
    console_handler = logging.StreamHandler()
    
    if COLORAMA_AVAILABLE and use_colored_logging:
        class ColoredFormatter(logging.Formatter):
            """Custom formatter for colored log output."""
            
            FORMATS = {
                logging.DEBUG: Fore.CYAN + '%(asctime)s - %(name)s - %(levelname)s - %(message)s' + Style.RESET_ALL,
                logging.INFO: Fore.GREEN + '%(asctime)s - %(name)s - %(levelname)s - %(message)s' + Style.RESET_ALL,
                logging.WARNING: Fore.YELLOW + '%(asctime)s - %(name)s - %(levelname)s - %(message)s' + Style.RESET_ALL,
                logging.ERROR: Fore.RED + '%(asctime)s - %(name)s - %(levelname)s - %(message)s' + Style.RESET_ALL,
                logging.CRITICAL: Fore.RED + Style.BRIGHT + '%(asctime)s - %(name)s - %(levelname)s - %(message)s' + Style.RESET_ALL
            }
            
            def format(self, record):
                log_fmt = self.FORMATS.get(record.levelno, self.FORMATS[logging.INFO])
                formatter = logging.Formatter(log_fmt, datefmt='%Y-%m-%d %H:%M:%S')
                return formatter.format(record)
                
        console_handler.setFormatter(ColoredFormatter())
    else:
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
    
    root_logger.addHandler(console_handler)
    return root_logger


def is_path_safe(base_path, target_path):
    """
    Check if a path is safe (doesn't escape the base directory).
    
    Args:
        base_path: Base directory path
        target_path: Target path to check
        
    Returns:
        bool: True if path is safe, False otherwise
    """
    # Normalize both paths
    base_path = os.path.normpath(os.path.abspath(base_path))
    target_path = os.path.normpath(os.path.abspath(target_path))
    
    # Check if target_path starts with base_path
    return target_path.startswith(base_path)


def is_allowed_file_type(filepath, allowed_types=None):
    """
    Check if a file type is allowed.
    
    Args:
        filepath: Path to the file
        allowed_types: List of allowed MIME types or None to allow all
        
    Returns:
        bool: True if file type is allowed, False otherwise
    """
    if allowed_types is None:
        return True
        
    mime_type, _ = get_mime_type(filepath)
    
    if mime_type is None:
        return False
        
    # Check main type and subtype
    main_type = mime_type.split('/')[0]
    
    # Check if exact mime type or main type is in allowed types
    return mime_type in allowed_types or f"{main_type}/*" in allowed_types


def get_mime_type(filepath):
    """
    Get MIME type for a file.
    
    Args:
        filepath: Path to the file
        
    Returns:
        tuple: (mime_type, encoding)
    """
    mime_type, encoding = mimetypes.guess_type(filepath)
    
    # Ensure some common types are properly mapped
    if mime_type is None:
        ext = os.path.splitext(filepath)[1].lower()
        if ext == '.js':
            return 'text/javascript', 'utf-8'
        elif ext == '.css':
            return 'text/css', 'utf-8'
        elif ext == '.json':
            return 'application/json', 'utf-8'
        elif ext == '.svg':
            return 'image/svg+xml', None
        return 'application/octet-stream', None
        
    return mime_type, encoding


def human_readable_size(size):
    """
    Convert size in bytes to human readable format.
    
    Args:
        size: Size in bytes
        
    Returns:
        str: Human readable size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024 or unit == 'TB':
            return f"{size:.1f} {unit}" if size % 1 else f"{int(size)} {unit}"
        size /= 1024


def parse_multipart_form_data(body, boundary):
    """
    Parse multipart/form-data request body.
    
    Args:
        body: Request body as bytes
        boundary: Form boundary string
        
    Returns:
        tuple: (form_data, files)
    """
    form_data = {}
    files = {}
    
    # Add boundary markers
    boundary = f"--{boundary}".encode('utf-8')
    end_boundary = f"--{boundary}--".encode('utf-8')
    
    # Split the body into parts
    parts = body.split(boundary)
    
    # Process each part
    for part in parts:
        if not part or part.strip() == b'' or part.strip() == end_boundary:
            continue
            
        # Split headers and content
        try:
            headers_end = part.find(b'\r\n\r\n')
            if headers_end == -1:
                continue
                
            headers_data = part[:headers_end].decode('utf-8', 'replace')
            content = part[headers_end + 4:].rstrip(b'\r\n')
            
            # Parse content disposition
            content_disposition = None
            content_type = None
            
            for header in headers_data.split('\r\n'):
                if header.lower().startswith('content-disposition:'):
                    content_disposition = header[header.find(':') + 1:].strip()
                elif header.lower().startswith('content-type:'):
                    content_type = header[header.find(':') + 1:].strip()
                    
            if not content_disposition:
                continue
                
            # Parse field name and filename if present
            field_name = None
            file_name = None
            
            for param in content_disposition.split(';'):
                param = param.strip()
                if param.startswith('name='):
                    field_name = param[5:].strip('"\'')
                elif param.startswith('filename='):
                    file_name = param[9:].strip('"\'')
                    
            if not field_name:
                continue
                
            # Handle file upload
            if file_name:
                files[field_name] = {
                    'filename': file_name,
                    'content-type': content_type,
                    'content': content
                }
            else:
                # Regular form field
                field_value = content.decode('utf-8', 'replace')
                if field_name in form_data:
                    form_data[field_name].append(field_value)
                else:
                    form_data[field_name] = [field_value]
        except Exception as e:
            logging.error(f"Error processing multipart part: {e}")
            
    return form_data, files


def generate_status_page(server_stats):
    """
    Generate HTML status page with server statistics.
    
    Args:
        server_stats: Dictionary with server statistics
        
    Returns:
        str: HTML status page
    """
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Python Socket Server Status</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #3498db;
            margin-top: 20px;
        }}
        .stat-group {{
            margin-bottom: 30px;
        }}
        .stat-row {{
            display: flex;
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
        }}
        .stat-label {{
            flex: 1;
            font-weight: 500;
        }}
        .stat-value {{
            flex: 2;
        }}
        .good {{
            color: #27ae60;
        }}
        .warning {{
            color: #f39c12;
        }}
        .error {{
            color: #e74c3c;
        }}
        .stat-chart {{
            background-color: #f9f9f9;
            border: 1px solid #eee;
            border-radius: 4px;
            padding: 10px;
            margin-top: 5px;
        }}
        .refresh-button {{
            background-color: #3498db;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            margin-top: 20px;
        }}
        .refresh-button:hover {{
            background-color: #2980b9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Python Socket Server Status</h1>
        <p>Server status and statistics as of {server_stats.get('current_time', 'Unknown')}</p>
        
        <div class="stat-group">
            <h2>Server Information</h2>
            <div class="stat-row">
                <div class="stat-label">Uptime</div>
                <div class="stat-value">{server_stats.get('uptime', 'Unknown')}</div>
            </div>
            <div class="stat-row">
                <div class="stat-label">Version</div>
                <div class="stat-value">{server_stats.get('version', 'Unknown')}</div>
            </div>
            <div class="stat-row">
                <div class="stat-label">Host:Port</div>
                <div class="stat-value">{server_stats.get('host', '0.0.0.0')}:{server_stats.get('port', 8000)}</div>
            </div>
            <div class="stat-row">
                <div class="stat-label">Root Directory</div>
                <div class="stat-value">{server_stats.get('root_directory', 'Unknown')}</div>
            </div>
        </div>
        
        <div class="stat-group">
            <h2>Performance</h2>
            <div class="stat-row">
                <div class="stat-label">Active Connections</div>
                <div class="stat-value">{server_stats.get('active_connections', 0)}</div>
            </div>
            <div class="stat-row">
                <div class="stat-label">Total Requests</div>
                <div class="stat-value">{server_stats.get('total_requests', 0)}</div>
            </div>
            <div class="stat-row">
                <div class="stat-label">Requests Per Second</div>
                <div class="stat-value">{server_stats.get('requests_per_second', 0)}</div>
            </div>
            <div class="stat-row">
                <div class="stat-label">Average Response Time</div>
                <div class="stat-value">{server_stats.get('avg_response_time', 0)} ms</div>
            </div>
        </div>
        
        <div class="stat-group">
            <h2>Cache Status</h2>
            <div class="stat-row">
                <div class="stat-label">Cache Enabled</div>
                <div class="stat-value">{server_stats.get('cache_enabled', False)}</div>
            </div>
            <div class="stat-row">
                <div class="stat-label">Cache Size</div>
                <div class="stat-value">{server_stats.get('cache_size', 0)} / {server_stats.get('cache_max_size', 0)} items</div>
            </div>
            <div class="stat-row">
                <div class="stat-label">Cache Hit Ratio</div>
                <div class="stat-value">{server_stats.get('cache_hit_ratio', 0):.2%}</div>
            </div>
            <div class="stat-row">
                <div class="stat-label">Memory Usage</div>
                <div class="stat-value">{server_stats.get('memory_usage', 'Unknown')}</div>
            </div>
        </div>
        
        <div class="stat-group">
            <h2>Status Codes</h2>
            <div class="stat-row">
                <div class="stat-label">2xx Responses</div>
                <div class="stat-value">{server_stats.get('status_2xx', 0)}</div>
            </div>
            <div class="stat-row">
                <div class="stat-label">3xx Responses</div>
                <div class="stat-value">{server_stats.get('status_3xx', 0)}</div>
            </div>
            <div class="stat-row">
                <div class="stat-label">4xx Responses</div>
                <div class="stat-value">{server_stats.get('status_4xx', 0)}</div>
            </div>
            <div class="stat-row">
                <div class="stat-label">5xx Responses</div>
                <div class="stat-value">{server_stats.get('status_5xx', 0)}</div>
            </div>
        </div>
        
        <button class="refresh-button" onclick="location.reload()">Refresh Statistics</button>
    </div>
</body>
</html>"""
    return html


def check_hostname_availability(host, port):
    """
    Check if a hostname and port are available.
    
    Args:
        host: Host address
        port: Port number
        
    Returns:
        bool: True if available, False otherwise
    """
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            result = s.connect_ex((host, port))
            return result != 0
    except:
        return False


def parse_http_date(date_string):
    """
    Parse an HTTP date string.
    
    Args:
        date_string: HTTP date string
        
    Returns:
        float: UNIX timestamp or None if parsing failed
    """
    # Common HTTP date formats
    formats = [
        '%a, %d %b %Y %H:%M:%S GMT',  # RFC 7231 (e.g., "Sun, 06 Nov 1994 08:49:37 GMT")
        '%A, %d-%b-%y %H:%M:%S GMT',  # RFC 850 (e.g., "Sunday, 06-Nov-94 08:49:37 GMT")
        '%a %b %d %H:%M:%S %Y'        # ANSI C's asctime() (e.g., "Sun Nov  6 08:49:37 1994")
    ]
    
    for fmt in formats:
        try:
            time_struct = time.strptime(date_string, fmt)
            return time.mktime(time_struct)
        except ValueError:
            continue
    
    return None


def format_http_date(timestamp=None):
    """
    Format a timestamp as an HTTP date string.
    
    Args:
        timestamp: UNIX timestamp (default: current time)
        
    Returns:
        str: HTTP date string in RFC 7231 format
    """
    if timestamp is None:
        timestamp = time.time()
    return time.strftime('%a, %d %b %Y %H:%M:%S GMT', time.gmtime(timestamp))


# Initialize mimetypes module
mimetypes.init()

# Add common MIME types that might be missing
mimetypes.add_type('text/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('image/x-icon', '.ico')
mimetypes.add_type('image/svg+xml', '.svg')
mimetypes.add_type('application/json', '.json')