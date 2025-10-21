#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Advanced Python Web Server
--------------------------
A web server built from scratch using only the socket library.
This server supports multiple clients, HTTP GET and POST requests,
and serves static files with proper MIME types.

Author: GitHub Copilot
Date: October 21, 2025
"""

import socket
import threading
import os
import sys
import time
import datetime
import json
import mimetypes
import logging
import re
import urllib.parse
from collections import OrderedDict

# Optional: For colored logging
try:
    import colorama
    from colorama import Fore, Style
    colorama.init(autoreset=True)
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False

# Global constants
DEFAULT_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "root_directory": "htdocs",
    "enable_directory_listing": True,
    "enable_caching": True,
    "cache_max_size": 100,
    "cache_max_age": 3600,
    "log_level": "INFO",
    "use_colored_logging": True
}

# HTTP status codes and messages
HTTP_STATUS = {
    200: 'OK',
    301: 'Moved Permanently',
    302: 'Found',
    304: 'Not Modified',
    400: 'Bad Request',
    401: 'Unauthorized',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    500: 'Internal Server Error'
}


class FileCache:
    """Cache for frequently requested files to improve performance."""
    
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
        
    def get(self, filepath):
        """
        Get a file from the cache.
        
        Args:
            filepath: Path to the file
            
        Returns:
            Tuple of (content, last_modified) or None if not in cache
        """
        if filepath in self.cache:
            entry = self.cache[filepath]
            
            # Check if the entry is still valid
            current_time = time.time()
            if current_time - entry['timestamp'] <= self.max_age:
                # Move to end to mark as most recently used
                self.cache.move_to_end(filepath)
                self.logger.debug(f"Cache hit: {filepath}")
                return entry['content'], entry['last_modified']
            
            # Entry expired
            self.logger.debug(f"Cache expired: {filepath}")
            del self.cache[filepath]
            
        return None, None
        
    def set(self, filepath, content, last_modified):
        """
        Add a file to the cache.
        
        Args:
            filepath: Path to the file
            content: File content
            last_modified: Last modified time of the file
        """
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
        """Return cache statistics."""
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'max_age': self.max_age
        }


class RequestHandler:
    """Handles HTTP requests and generates responses."""
    
    def __init__(self, server, client_sock, client_address):
        """
        Initialize the request handler.
        
        Args:
            server: Reference to the WebServer instance
            client_sock: Client socket object
            client_address: Client address tuple (ip, port)
        """
        self.server = server
        self.client_sock = client_sock
        self.client_address = client_address
        self.logger = logging.getLogger('RequestHandler')
        self.request_data = b''
        
        # Request parsing results
        self.method = None
        self.path = None
        self.http_version = None
        self.headers = {}
        self.body = None
        
        # Response data
        self.response_status = 200
        self.response_headers = {}
        self.response_content = b''
        
    def handle(self):
        """Handle the client request."""
        try:
            self._receive_data()
            self._parse_request()
            self._process_request()
        except Exception as e:
            self.logger.error(f"Error handling request: {e}", exc_info=True)
            self.send_error(500)
        finally:
            self._close_connection()
            
    def _receive_data(self):
        """Receive data from client socket."""
        buffer_size = 1024
        while True:
            try:
                chunk = self.client_sock.recv(buffer_size)
                if not chunk:
                    break
                    
                self.request_data += chunk
                
                # Check if we've received the complete request
                if b'\r\n\r\n' in self.request_data:
                    # If it's a POST request, check if we've received the full body
                    header_end = self.request_data.find(b'\r\n\r\n') + 4
                    headers = self.request_data[:header_end].decode('utf-8', 'replace')
                    
                    if 'POST' in headers.split('\r\n')[0]:
                        # Check for Content-Length header
                        match = re.search(r'Content-Length:\s*(\d+)', headers, re.IGNORECASE)
                        if match:
                            content_length = int(match.group(1))
                            body_received = len(self.request_data) - header_end
                            
                            if body_received >= content_length:
                                break
                    else:
                        # For non-POST requests, we can stop after headers
                        break
                        
            except socket.timeout:
                self.logger.warning(f"Socket timeout from {self.client_address[0]}")
                break
            except socket.error as e:
                self.logger.error(f"Socket error: {e}")
                break
                
    def _parse_request(self):
        """Parse the HTTP request."""
        # Split the request data into header and body parts
        try:
            header_end = self.request_data.find(b'\r\n\r\n')
            if header_end == -1:
                self.logger.error("Invalid request format: no header-body separator found")
                raise ValueError("Invalid request format")
                
            header_data = self.request_data[:header_end].decode('utf-8', 'replace')
            self.body = self.request_data[header_end + 4:]  # +4 to skip the '\r\n\r\n'
            
            # Parse the request line
            request_lines = header_data.split('\r\n')
            request_line = request_lines[0]
            request_parts = request_line.split(' ')
            
            if len(request_parts) != 3:
                self.logger.error(f"Invalid request line: {request_line}")
                raise ValueError(f"Invalid request line: {request_line}")
                
            self.method, self.path, self.http_version = request_parts
            
            # Parse headers
            for header_line in request_lines[1:]:
                if not header_line:
                    continue
                    
                if ':' not in header_line:
                    continue
                    
                key, value = header_line.split(':', 1)
                self.headers[key.strip().lower()] = value.strip()
                
            # URL-decode the path
            self.path = urllib.parse.unquote(self.path)
                
            self.logger.debug(f"Parsed request: {self.method} {self.path} {self.http_version}")
        except Exception as e:
            self.logger.error(f"Error parsing request: {e}")
            raise
            
    def _process_request(self):
        """Process the request based on the HTTP method."""
        self.logger.info(f"{self.client_address[0]} - {self.method} {self.path}")
        
        # Add common headers
        self.response_headers['Server'] = 'PythonCustomServer/1.0'
        self.response_headers['Date'] = datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        self.response_headers['Connection'] = 'close'
        
        # Handle different HTTP methods
        if self.method == 'GET':
            self._handle_get()
        elif self.method == 'POST':
            self._handle_post()
        elif self.method == 'HEAD':
            self._handle_head()
        else:
            self.send_error(405, f"Method {self.method} not allowed")
            
    def _handle_get(self):
        """Handle GET requests."""
        # Serve file or directory listing
        self._serve_file()
            
    def _handle_head(self):
        """Handle HEAD requests (like GET but without body)."""
        self._serve_file(send_body=False)
            
    def _handle_post(self):
        """Handle POST requests."""
        if self.path == '/submit':
            content_type = self.headers.get('content-type', '')
            self.logger.debug(f"Handling POST request with Content-Type: {content_type}")
            
            # Initialize form data dictionary
            form_data = {}
            files = {}
            
            # Parse the form data based on content type
            if 'application/x-www-form-urlencoded' in content_type:
                # Standard form data
                form_data = urllib.parse.parse_qs(self.body.decode('utf-8', 'replace'))
                
            elif 'application/json' in content_type:
                # JSON data
                try:
                    json_data = json.loads(self.body.decode('utf-8', 'replace'))
                    # Convert JSON to form data format (values as lists)
                    for key, value in json_data.items():
                        if isinstance(value, list):
                            form_data[key] = value
                        else:
                            form_data[key] = [value]
                except json.JSONDecodeError as e:
                    self.logger.error(f"Invalid JSON in request: {e}")
                    self.send_error(400, "Invalid JSON format")
                    return
            
            elif 'multipart/form-data' in content_type:
                # Multipart form data (including file uploads)
                try:
                    # Get boundary from content type
                    boundary = content_type.split('boundary=')[1].strip()
                    if boundary.startswith('"') and boundary.endswith('"'):
                        boundary = boundary[1:-1]
                    
                    # Parse multipart form data
                    form_data, files = self._parse_multipart(boundary)
                except Exception as e:
                    self.logger.error(f"Error parsing multipart form: {e}")
                    self.send_error(400, "Invalid multipart form data")
                    return
            else:
                self.send_error(400, "Unsupported Content-Type")
                return
                
            # Store form submission in submissions.json
            self._store_submission(form_data)
                
            # Handle file uploads if any
            for file_field, file_data in files.items():
                self._save_uploaded_file(file_data)
            
            # Redirect to a success page if it exists
            success_page_path = os.path.join(self.server.root_directory, 'submit_success.html')
            if os.path.exists(success_page_path):
                # Use a redirect to the success page
                self.response_status = 302
                self.response_headers['Location'] = '/submit_success.html'
                self._send_response()
                return
            
            # If no success page exists, generate HTML response
            # Create a styled HTML response with the submitted data
            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Form Submission</title>
    <link rel="stylesheet" href="/styles.css">
    <style>
        .submission-container {{
            background-color: #f5f5f5;
            border-radius: 5px;
            padding: 20px;
            margin: 20px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .submission-item {{
            margin: 10px 0;
            padding: 10px;
            border-bottom: 1px solid #eee;
        }}
        .submission-key {{
            font-weight: bold;
            color: #333;
        }}
        .submission-value {{
            background-color: #fff;
            padding: 5px 10px;
            border-radius: 3px;
            margin-top: 5px;
        }}
        .back-button {{
            display: inline-block;
            background-color: #4CAF50;
            color: white;
            padding: 10px 15px;
            text-decoration: none;
            border-radius: 4px;
            margin-top: 20px;
        }}
        .back-button:hover {{
            background-color: #45a049;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Form Submission Received</h1>
        <p>Your form data has been successfully submitted and processed.</p>
        
        <div class="submission-container">
            <h2>Submitted Data:</h2>"""
            
            # Add form data to HTML
            for key, values in form_data.items():
                html_content += f'<div class="submission-item"><span class="submission-key">{key}:</span>'
                for value in values:
                    html_content += f'<div class="submission-value">{value}</div>'
                html_content += '</div>'
                
            # Add file information if any
            if files:
                html_content += '<h2>Uploaded Files:</h2>'
                for field_name, file_info in files.items():
                    file_name = file_info.get('filename', 'unknown')
                    file_size = len(file_info.get('content', b''))
                    html_content += f'<div class="submission-item"><span class="submission-key">{field_name}:</span>'
                    html_content += f'<div class="submission-value">File: {file_name} ({self._human_readable_size(file_size)})</div></div>'
            
            # Close HTML tags
            html_content += """
        </div>
        
        <a href="/" class="back-button">Return to Homepage</a>
    </div>
</body>
</html>"""
            
            self.response_content = html_content.encode('utf-8')
            self.response_headers['Content-Type'] = 'text/html; charset=utf-8'
            self.response_headers['Content-Length'] = str(len(self.response_content))
            self._send_response()
        else:
            self.send_error(404)
    
    def _parse_multipart(self, boundary):
        """Parse multipart form data including file uploads."""
        form_data = {}
        files = {}
        
        # Add boundary markers
        boundary = f"--{boundary}".encode('utf-8')
        end_boundary = f"--{boundary}--".encode('utf-8')
        
        # Split the body into parts
        parts = self.body.split(boundary)
        
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
                self.logger.error(f"Error processing multipart part: {e}")
                
        return form_data, files
        
    def _store_submission(self, form_data):
        """Store form submission in a JSON file."""
        try:
            submissions_path = os.path.join(self.server.root_directory, '..', 'submissions.json')
            
            # Convert form_data values from lists to single values when possible
            simplified_data = {}
            for key, values in form_data.items():
                simplified_data[key] = values[0] if len(values) == 1 else values
                
            # Add timestamp and IP
            submission = {
                'timestamp': datetime.datetime.now().isoformat(),
                'ip': self.client_address[0],
                'data': simplified_data
            }
            
            # Load existing submissions or create new array
            if os.path.exists(submissions_path):
                try:
                    with open(submissions_path, 'r') as f:
                        submissions = json.load(f)
                except json.JSONDecodeError:
                    submissions = []
            else:
                submissions = []
                
            # Add new submission
            submissions.append(submission)
            
            # Write back to file
            with open(submissions_path, 'w') as f:
                json.dump(submissions, f, indent=2)
                
            self.logger.info(f"Form submission stored: {submission['timestamp']}")
            
        except Exception as e:
            self.logger.error(f"Error storing form submission: {e}")
            
    def _save_uploaded_file(self, file_info):
        """Save uploaded file to the uploads directory."""
        try:
            uploads_dir = os.path.join(self.server.root_directory, 'uploads')
            
            # Create uploads directory if it doesn't exist
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
                
            # Create safe filename
            filename = file_info.get('filename', 'unnamed_file')
            safe_filename = os.path.basename(filename)
            
            # Ensure filename is unique
            file_path = os.path.join(uploads_dir, safe_filename)
            counter = 1
            while os.path.exists(file_path):
                name_parts = os.path.splitext(safe_filename)
                safe_filename = f"{name_parts[0]}_{counter}{name_parts[1]}"
                file_path = os.path.join(uploads_dir, safe_filename)
                counter += 1
                
            # Write file content
            with open(file_path, 'wb') as f:
                f.write(file_info.get('content', b''))
                
            self.logger.info(f"File uploaded: {safe_filename}")
            return safe_filename
            
        except Exception as e:
            self.logger.error(f"Error saving uploaded file: {e}")
            return None
            
    def _serve_file(self, send_body=True):
        """
        Serve a file or directory listing.
        
        Args:
            send_body: Whether to send the file content (for GET) or just headers (for HEAD)
        """
        # Convert URL path to file system path
        if self.path == '/':
            file_path = os.path.join(self.server.root_directory, 'index.html')
        else:
            # Remove the leading slash and any query parameters
            path = self.path.lstrip('/')
            path = path.split('?')[0]
            file_path = os.path.join(self.server.root_directory, path)
            
        # Normalize the path to prevent directory traversal attacks
        file_path = os.path.normpath(file_path)
        if not file_path.startswith(self.server.root_directory):
            self.send_error(403, "Forbidden")
            return
            
        # Check if it's a directory
        if os.path.isdir(file_path):
            # Look for index.html in the directory
            index_path = os.path.join(file_path, 'index.html')
            if os.path.exists(index_path):
                file_path = index_path
            elif self.server.config.get('enable_directory_listing', True):
                self._serve_directory_listing(file_path)
                return
            else:
                self.send_error(403, "Directory listing not allowed")
                return
                
        # Check if file exists
        if not os.path.exists(file_path):
            self.send_error(404)
            return
            
        # Check if file is accessible
        if not os.access(file_path, os.R_OK):
            self.send_error(403, "Access denied")
            return
            
        try:
            # Check if we have a cached version
            if self.server.config.get('enable_caching', True):
                last_modified = datetime.datetime.fromtimestamp(
                    os.path.getmtime(file_path)
                ).strftime('%a, %d %b %Y %H:%M:%S GMT')
                
                # Check if client has a cached version (If-Modified-Since header)
                if_modified_since = self.headers.get('if-modified-since')
                if if_modified_since and if_modified_since == last_modified:
                    # File not modified
                    self.response_status = 304
                    self.response_headers['Last-Modified'] = last_modified
                    self._send_response()
                    return
                    
                # Try to get file from cache
                content, cache_last_modified = self.server.file_cache.get(file_path)
                
                if content and cache_last_modified == last_modified:
                    # Cache hit
                    self.response_content = content
                else:
                    # Cache miss, read file
                    with open(file_path, 'rb') as f:
                        self.response_content = f.read()
                    
                    # Update cache
                    self.server.file_cache.set(file_path, self.response_content, last_modified)
                    
                # Set Last-Modified header
                self.response_headers['Last-Modified'] = last_modified
            else:
                # No caching, read the file
                with open(file_path, 'rb') as f:
                    self.response_content = f.read()
                    
            # Determine content type
            content_type, encoding = mimetypes.guess_type(file_path)
            if content_type:
                if encoding:
                    self.response_headers['Content-Type'] = f"{content_type}; charset={encoding}"
                else:
                    self.response_headers['Content-Type'] = content_type
            else:
                self.response_headers['Content-Type'] = 'application/octet-stream'
                
            # Set content length
            self.response_headers['Content-Length'] = str(len(self.response_content))
            
            # Send the response
            self._send_response(send_body=send_body)
            
        except Exception as e:
            self.logger.error(f"Error serving file {file_path}: {e}", exc_info=True)
            self.send_error(500)
            
    def _serve_directory_listing(self, directory):
        """Generate and serve a directory listing."""
        try:
            # Get relative path for display
            rel_path = os.path.relpath(directory, self.server.root_directory)
            if rel_path == '.':
                rel_path = '/'
            else:
                rel_path = '/' + rel_path.replace('\\', '/')
                
            items = os.listdir(directory)
            
            # Build HTML content
            html = '<!DOCTYPE html>\n'
            html += '<html>\n<head>\n'
            html += f'<title>Directory listing for {rel_path}</title>\n'
            html += '<style>\n'
            html += 'body { font-family: Arial, sans-serif; padding: 20px; }\n'
            html += 'h1 { border-bottom: 1px solid #ddd; padding-bottom: 10px; }\n'
            html += 'ul { list-style-type: none; padding: 0; }\n'
            html += 'li { margin: 5px 0; }\n'
            html += 'a { text-decoration: none; color: #0366d6; }\n'
            html += 'a:hover { text-decoration: underline; }\n'
            html += '</style>\n'
            html += '</head>\n<body>\n'
            html += f'<h1>Directory listing for {rel_path}</h1>\n<ul>\n'
            
            # Add parent directory link if not in root
            if rel_path != '/':
                parent_path = os.path.dirname(rel_path.rstrip('/'))
                if not parent_path:
                    parent_path = '/'
                html += f'<li><a href="{parent_path}">../</a> (Parent Directory)</li>\n'
                
            # Add items
            for item in sorted(items):
                item_path = os.path.join(directory, item)
                link_path = os.path.join(rel_path, item).replace('\\', '/')
                
                if os.path.isdir(item_path):
                    html += f'<li><a href="{link_path}/">{item}/</a></li>\n'
                else:
                    # Add file size
                    size = os.path.getsize(item_path)
                    size_str = self._human_readable_size(size)
                    html += f'<li><a href="{link_path}">{item}</a> ({size_str})</li>\n'
                    
            html += '</ul>\n</body>\n</html>'
            
            # Send the response
            self.response_content = html.encode('utf-8')
            self.response_headers['Content-Type'] = 'text/html; charset=utf-8'
            self.response_headers['Content-Length'] = str(len(self.response_content))
            self._send_response()
            
        except Exception as e:
            self.logger.error(f"Error generating directory listing: {e}", exc_info=True)
            self.send_error(500)
            
    def _human_readable_size(self, size):
        """Convert size in bytes to human readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024 or unit == 'TB':
                return f"{size:.1f} {unit}" if size % 1 else f"{int(size)} {unit}"
            size /= 1024
            
    def send_error(self, status_code, message=None):
        """
        Send an error response.
        
        Args:
            status_code: HTTP status code
            message: Optional error message
        """
        self.response_status = status_code
        status_message = HTTP_STATUS.get(status_code, 'Unknown')
        
        # Check for custom error page
        error_page_path = os.path.join(self.server.root_directory, f"{status_code}.html")
        
        if os.path.exists(error_page_path):
            try:
                with open(error_page_path, 'rb') as f:
                    self.response_content = f.read()
                self.response_headers['Content-Type'] = 'text/html; charset=utf-8'
            except Exception as e:
                self.logger.error(f"Error reading custom error page: {e}")
                # Fall back to default error page
                self._generate_default_error_page(status_code, status_message, message)
        else:
            # Generate default error page
            self._generate_default_error_page(status_code, status_message, message)
            
        self.response_headers['Content-Length'] = str(len(self.response_content))
        self._send_response()
        
    def _generate_default_error_page(self, status_code, status_message, message=None):
        """Generate a default error page."""
        if not message:
            message = status_message
            
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>{status_code} {status_message}</title>
    <style>
        body {{ font-family: Arial, sans-serif; padding: 20px; text-align: center; }}
        .error-container {{ margin: 0 auto; max-width: 600px; }}
        .error-code {{ font-size: 72px; color: #e74c3c; margin: 0; }}
        .error-message {{ font-size: 24px; margin: 10px 0 30px; }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1 class="error-code">{status_code}</h1>
        <p class="error-message">{status_message}</p>
        <p>{message}</p>
        <p><a href="/">Return to Homepage</a></p>
    </div>
</body>
</html>"""
        self.response_content = html.encode('utf-8')
        self.response_headers['Content-Type'] = 'text/html; charset=utf-8'
        
    def _send_response(self, send_body=True):
        """
        Send the HTTP response.
        
        Args:
            send_body: Whether to send the response body (False for HEAD requests)
        """
        try:
            # Build the response header
            status_line = f"HTTP/1.1 {self.response_status} {HTTP_STATUS.get(self.response_status, 'Unknown')}"
            header_lines = [status_line]
            
            for key, value in self.response_headers.items():
                header_lines.append(f"{key}: {value}")
                
            # Add blank line to separate headers from body
            header_lines.append("")
            header_lines.append("")
            
            # Encode and send headers
            header_data = "\r\n".join(header_lines).encode('utf-8')
            self.client_sock.sendall(header_data)
            
            # Send body if needed
            if send_body and self.response_content and self.response_status not in (204, 304):
                self.client_sock.sendall(self.response_content)
                
            # Log the response
            log_msg = f"{self.client_address[0]} - {self.method} {self.path} {self.response_status}"
            if self.response_status >= 400:
                self.logger.warning(log_msg)
            else:
                self.logger.info(log_msg)
                
        except socket.error as e:
            self.logger.error(f"Error sending response: {e}")
            
    def _close_connection(self):
        """Close the client connection."""
        try:
            self.client_sock.close()
        except socket.error:
            pass


class WebServer:
    """Main web server class."""
    
    def __init__(self, config_path='config.json'):
        """
        Initialize the web server.
        
        Args:
            config_path: Path to the configuration file
        """
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Setup logging
        self._setup_logging()
        
        # Initialize server properties
        self.host = self.config.get('host', '0.0.0.0')
        self.port = self.config.get('port', 8000)
        self.root_directory = os.path.abspath(self.config.get('root_directory', 'htdocs'))
        
        # Create root directory if it doesn't exist
        if not os.path.exists(self.root_directory):
            try:
                os.makedirs(self.root_directory)
                self.logger.info(f"Created root directory: {self.root_directory}")
            except Exception as e:
                self.logger.error(f"Failed to create root directory: {e}")
                sys.exit(1)
                
        # Initialize file cache if enabled
        if self.config.get('enable_caching', True):
            max_size = self.config.get('cache_max_size', 100)
            max_age = self.config.get('cache_max_age', 3600)
            self.file_cache = FileCache(max_size, max_age)
            self.logger.info(f"File cache enabled (max_size={max_size}, max_age={max_age}s)")
        else:
            self.file_cache = FileCache(0, 0)  # Disabled cache
            self.logger.info("File cache disabled")
            
        # Initialize server socket
        self.server_socket = None
        self.is_running = False
        
        # Initialize mimetypes
        mimetypes.init()
        
        # Set common MIME types that might be missing
        mimetypes.add_type('text/javascript', '.js')
        mimetypes.add_type('text/css', '.css')
        mimetypes.add_type('image/x-icon', '.ico')
        mimetypes.add_type('image/svg+xml', '.svg')
        mimetypes.add_type('application/json', '.json')
        
    def _load_config(self, config_path):
        """
        Load server configuration from a JSON file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            dict: Configuration dictionary
        """
        config = DEFAULT_CONFIG.copy()
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    file_config = json.load(f)
                    config.update(file_config)
                print(f"Loaded configuration from {config_path}")
            else:
                print(f"Configuration file {config_path} not found. Using default configuration.")
                # Save default config
                with open(config_path, 'w') as f:
                    json.dump(DEFAULT_CONFIG, f, indent=4)
                print(f"Created default configuration file: {config_path}")
        except Exception as e:
            print(f"Error loading configuration: {e}")
            print("Using default configuration.")
            
        return config
        
    def _setup_logging(self):
        """Set up logging configuration."""
        log_level_name = self.config.get('log_level', 'INFO')
        log_level = getattr(logging, log_level_name.upper(), logging.INFO)
        
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        self.logger = logging.getLogger('WebServer')
        
        # Set up colored logging if available and enabled
        if COLORAMA_AVAILABLE and self.config.get('use_colored_logging', True):
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
                    
            handler = logging.StreamHandler()
            handler.setFormatter(ColoredFormatter())
            logging.root.handlers = [handler]
            
    def start(self):
        """Start the web server."""
        try:
            # Create server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.is_running = True
            
            self.logger.info(f"Server started at http://{self.host if self.host != '0.0.0.0' else 'localhost'}:{self.port}")
            self.logger.info(f"Serving files from: {self.root_directory}")
            self.logger.info("Press Ctrl+C to stop the server")
            
            # Accept client connections
            while self.is_running:
                try:
                    client_sock, client_address = self.server_socket.accept()
                    client_sock.settimeout(30)  # Set timeout
                    
                    # Start a new thread to handle the client request
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_sock, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.logger.error(f"Error accepting client connection: {e}")
                    
        except Exception as e:
            self.logger.error(f"Error starting server: {e}", exc_info=True)
        finally:
            self.stop()
            
    def _handle_client(self, client_sock, client_address):
        """
        Handle a client connection.
        
        Args:
            client_sock: Client socket object
            client_address: Client address tuple (ip, port)
        """
        handler = RequestHandler(self, client_sock, client_address)
        handler.handle()
        
    def stop(self):
        """Stop the web server."""
        self.is_running = False
        
        if self.server_socket:
            try:
                self.server_socket.close()
                self.logger.info("Server stopped")
            except Exception as e:
                self.logger.error(f"Error closing server socket: {e}")
                

if __name__ == '__main__':
    # Parse command line arguments
    import argparse
    
    parser = argparse.ArgumentParser(description='Python Custom Web Server')
    parser.add_argument('-c', '--config', default='config.json', help='Path to configuration file')
    parser.add_argument('-p', '--port', type=int, help='Server port (overrides config file)')
    parser.add_argument('-d', '--directory', help='Root directory (overrides config file)')
    
    args = parser.parse_args()
    
    # Create and start the server
    server = WebServer(args.config)
    
    # Override configuration with command line arguments
    if args.port:
        server.port = args.port
    if args.directory:
        server.root_directory = os.path.abspath(args.directory)
        
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.stop()