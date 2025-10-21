#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
HTTP Request Handler Module for Python Socket Server
---------------------------------------------------
Handles parsing and processing HTTP requests and generating responses.
"""

import os
import time
import json
import logging
import socket
import traceback
import urllib.parse
from datetime import datetime
from .utils import (
    get_mime_type, 
    is_path_safe, 
    is_allowed_file_type,
    parse_multipart_form_data, 
    format_http_date,
    parse_http_date,
    human_readable_size
)

# HTTP status codes with descriptions
HTTP_STATUS = {
    200: 'OK',
    201: 'Created',
    204: 'No Content',
    301: 'Moved Permanently',
    302: 'Found',
    304: 'Not Modified',
    400: 'Bad Request',
    401: 'Unauthorized',
    403: 'Forbidden',
    404: 'Not Found',
    405: 'Method Not Allowed',
    413: 'Payload Too Large',
    500: 'Internal Server Error',
    501: 'Not Implemented',
    503: 'Service Unavailable'
}

# Default error page template
ERROR_PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{code} {status}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }}
        .container {{
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
            max-width: 500px;
            width: 100%;
        }}
        h1 {{
            margin-top: 0;
            color: #e74c3c;
            font-size: 36px;
        }}
        .status {{
            font-weight: normal;
            color: #777;
            margin-bottom: 20px;
        }}
        .message {{
            margin-bottom: 25px;
            line-height: 1.5;
        }}
        .server-info {{
            font-size: 12px;
            color: #999;
            margin-top: 30px;
            text-align: right;
        }}
        .back-link {{
            display: inline-block;
            margin-top: 20px;
            color: #3498db;
            text-decoration: none;
        }}
        .back-link:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{code} <span class="status">{status}</span></h1>
        <div class="message">{message}</div>
        <a href="/" class="back-link">← Go to Homepage</a>
        <div class="server-info">Python Socket Server | {date}</div>
    </div>
</body>
</html>"""


class RequestHandler:
    """
    Handles HTTP requests by parsing the request, routing to the appropriate
    handler based on method and path, and generating HTTP responses.
    """
    
    def __init__(self, server_config, file_cache=None):
        """
        Initialize the request handler.
        
        Args:
            server_config: Server configuration object
            file_cache: Optional FileCache instance for serving cached files
        """
        self.config = server_config
        self.logger = logging.getLogger('RequestHandler')
        self.file_cache = file_cache
        self.request_count = 0
        
        # Request statistics
        self.stats = {
            'status_2xx': 0,
            'status_3xx': 0,
            'status_4xx': 0,
            'status_5xx': 0,
            'total_requests': 0,
            'response_times': []
        }
    
    def handle_request(self, client_socket, client_address):
        """
        Handle an incoming HTTP request.
        
        Args:
            client_socket: Client socket object
            client_address: Client address tuple (ip, port)
            
        Returns:
            None
        """
        self.request_count += 1
        self.stats['total_requests'] += 1
        start_time = time.time()
        
        try:
            # Set socket timeout
            client_socket.settimeout(self.config.request_timeout)
            
            # Parse request
            request = self._parse_request(client_socket)
            
            if not request:
                self.logger.warning(f"Invalid request from {client_address[0]}:{client_address[1]}")
                self._send_error_response(client_socket, 400, "Bad Request")
                return
                
            method = request.get('method', '')
            path = request.get('path', '')
            headers = request.get('headers', {})
            
            # Log the request
            self.logger.info(f"{client_address[0]}:{client_address[1]} - {method} {path}")
            
            # Route request to appropriate handler
            if method == 'GET':
                self._handle_get(client_socket, request)
            elif method == 'HEAD':
                self._handle_head(client_socket, request)
            elif method == 'POST':
                self._handle_post(client_socket, request)
            elif method == 'OPTIONS':
                self._handle_options(client_socket, request)
            else:
                self._send_error_response(client_socket, 501, f"Method {method} not implemented")
                
        except ConnectionError as e:
            self.logger.warning(f"Connection error: {e}")
        except socket.timeout:
            self.logger.warning(f"Request from {client_address[0]}:{client_address[1]} timed out")
        except Exception as e:
            self.logger.error(f"Error handling request: {e}")
            self.logger.debug(traceback.format_exc())
            try:
                self._send_error_response(client_socket, 500, "Internal Server Error")
            except:
                pass
        finally:
            # Close the connection
            try:
                client_socket.close()
            except:
                pass
                
            # Update response time statistics
            elapsed = time.time() - start_time
            self.stats['response_times'].append(elapsed)
            
            # Trim response times list if it gets too large
            if len(self.stats['response_times']) > 1000:
                self.stats['response_times'] = self.stats['response_times'][-1000:]
                
    def _parse_request(self, client_socket):
        """
        Parse an HTTP request from the client socket.
        
        Args:
            client_socket: Client socket object
            
        Returns:
            dict: Parsed request or None if parsing failed
        """
        # Read and parse the request line and headers
        try:
            # Initialize an empty request object
            request = {'headers': {}, 'body': b''}
            
            # Read the request line
            request_line = client_socket.recv(1024).decode('utf-8', 'replace')
            
            if not request_line:
                return None
                
            # Split the request into headers and potential partial body
            header_end = request_line.find('\r\n\r\n')
            
            if header_end != -1:
                headers_text = request_line[:header_end]
                partial_body = request_line[header_end + 4:].encode('utf-8', 'replace')
            else:
                # If we haven't received the full headers yet, keep reading
                headers_text = request_line
                while '\r\n\r\n' not in headers_text:
                    chunk = client_socket.recv(1024).decode('utf-8', 'replace')
                    if not chunk:
                        return None
                    headers_text += chunk
                    
                    header_end = headers_text.find('\r\n\r\n')
                    if header_end != -1:
                        partial_body = headers_text[header_end + 4:].encode('utf-8', 'replace')
                        headers_text = headers_text[:header_end]
                        break
                        
            # Split headers into lines
            header_lines = headers_text.split('\r\n')
            
            # Parse request line
            if not header_lines or len(header_lines[0].split()) < 3:
                return None
                
            request_parts = header_lines[0].split()
            request['method'] = request_parts[0]
            request['path'] = urllib.parse.unquote(request_parts[1])
            request['http_version'] = request_parts[2]
            
            # Parse query parameters if present
            if '?' in request['path']:
                path, query_string = request['path'].split('?', 1)
                request['path'] = path
                request['query_params'] = urllib.parse.parse_qs(query_string)
            else:
                request['query_params'] = {}
                
            # Parse headers
            for header in header_lines[1:]:
                if not header:
                    continue
                    
                if ':' not in header:
                    continue
                    
                key, value = header.split(':', 1)
                request['headers'][key.strip().lower()] = value.strip()
                
            # Check if we need to read the body
            if request['method'] in ['POST', 'PUT'] and 'content-length' in request['headers']:
                content_length = int(request['headers']['content-length'])
                body = partial_body
                
                # Read the rest of the body
                bytes_remaining = content_length - len(body)
                while bytes_remaining > 0:
                    chunk = client_socket.recv(min(bytes_remaining, 4096))
                    if not chunk:
                        break
                    body += chunk
                    bytes_remaining -= len(chunk)
                    
                request['body'] = body
                
                # Parse body based on content type
                content_type = request['headers'].get('content-type', '')
                
                if 'application/x-www-form-urlencoded' in content_type:
                    # Parse form data
                    form_data = urllib.parse.parse_qs(body.decode('utf-8', 'replace'))
                    request['form'] = form_data
                elif 'multipart/form-data' in content_type:
                    # Get boundary
                    boundary = None
                    for part in content_type.split(';'):
                        part = part.strip()
                        if part.startswith('boundary='):
                            boundary = part[9:].strip('"\'')
                            break
                            
                    if boundary:
                        form_data, files = parse_multipart_form_data(body, boundary)
                        request['form'] = form_data
                        request['files'] = files
                elif 'application/json' in content_type:
                    # Parse JSON data
                    try:
                        json_data = json.loads(body.decode('utf-8', 'replace'))
                        request['json'] = json_data
                    except json.JSONDecodeError:
                        self.logger.warning("Invalid JSON in request body")
            
            return request
            
        except Exception as e:
            self.logger.error(f"Error parsing request: {e}")
            self.logger.debug(traceback.format_exc())
            return None
            
    def _handle_get(self, client_socket, request):
        """
        Handle a GET request.
        
        Args:
            client_socket: Client socket object
            request: Parsed request dictionary
        """
        path = request['path']
        headers = request['headers']
        
        # Check for server-status endpoint
        if path == '/server-status' and self.config.enable_server_status:
            self._send_server_status(client_socket, request)
            return
            
        # Sanitize the path and build the full file path
        if path == '/':
            path = '/index.html'
        elif path.endswith('/'):
            path = path + 'index.html'
            
        file_path = os.path.join(self.config.document_root, path.lstrip('/'))
        
        # Convert to absolute path for safety checks
        file_path = os.path.abspath(file_path)
        
        # Security check - make sure the path is within the document root
        if not is_path_safe(self.config.document_root, file_path):
            self._send_error_response(client_socket, 403, "Forbidden")
            return
            
        # Check if path is a directory
        if os.path.isdir(file_path) and self.config.directory_listing:
            self._send_directory_listing(client_socket, file_path, path)
            return
        elif os.path.isdir(file_path):
            self._send_error_response(client_socket, 403, "Directory listing not allowed")
            return
            
        # Check if file exists
        if not os.path.isfile(file_path):
            self._send_error_response(client_socket, 404, "File not found")
            return
            
        # Check if file type is allowed
        if not is_allowed_file_type(file_path, self.config.allowed_file_types):
            self._send_error_response(client_socket, 403, "File type not allowed")
            return
            
        # Try to get file from cache
        use_cache = self.file_cache is not None and self.config.enable_cache
        file_content = None
        last_modified = None
        
        if use_cache:
            file_content, last_modified = self.file_cache.get(file_path)
            
        # Check file modification time for caching
        try:
            file_mtime = os.path.getmtime(file_path)
            
            # Check if client has a cached version (If-Modified-Since)
            if 'if-modified-since' in headers:
                if_modified_since = parse_http_date(headers['if-modified-since'])
                
                if if_modified_since and file_mtime <= if_modified_since:
                    self._send_response(client_socket, 304, {
                        'Date': format_http_date(),
                        'Server': self.config.server_name,
                        'Last-Modified': format_http_date(file_mtime)
                    })
                    self.stats['status_3xx'] += 1
                    return
        except:
            pass
            
        # Read file if not in cache or cache is disabled
        if file_content is None:
            try:
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                    
                last_modified = os.path.getmtime(file_path)
                
                # Add to cache if caching is enabled
                if use_cache:
                    self.file_cache.set(file_path, file_content, last_modified)
            except Exception as e:
                self.logger.error(f"Error reading file {file_path}: {e}")
                self._send_error_response(client_socket, 500, "Internal Server Error")
                return
                
        # Get content type
        content_type, encoding = get_mime_type(file_path)
        headers = {
            'Content-Type': content_type,
            'Content-Length': str(len(file_content)),
            'Date': format_http_date(),
            'Server': self.config.server_name,
            'Last-Modified': format_http_date(last_modified)
        }
        
        # Set caching headers if enabled
        if self.config.enable_browser_caching:
            cache_time = self.config.browser_cache_time
            headers['Cache-Control'] = f'public, max-age={cache_time}'
            headers['Expires'] = format_http_date(time.time() + cache_time)
            
        # Set security headers if enabled
        if self.config.enable_security_headers:
            headers.update(self._get_security_headers())
            
        # Send the response
        self._send_response(client_socket, 200, headers, file_content)
        self.stats['status_2xx'] += 1
        
    def _handle_head(self, client_socket, request):
        """
        Handle a HEAD request (same as GET but without body).
        
        Args:
            client_socket: Client socket object
            request: Parsed request dictionary
        """
        path = request['path']
        headers = request['headers']
        
        # Sanitize the path and build the full file path
        if path == '/':
            path = '/index.html'
        elif path.endswith('/'):
            path = path + 'index.html'
            
        file_path = os.path.join(self.config.document_root, path.lstrip('/'))
        
        # Convert to absolute path for safety checks
        file_path = os.path.abspath(file_path)
        
        # Security check
        if not is_path_safe(self.config.document_root, file_path):
            self._send_error_response(client_socket, 403, "Forbidden", send_body=False)
            return
            
        # Check if file exists
        if not os.path.isfile(file_path):
            self._send_error_response(client_socket, 404, "File not found", send_body=False)
            return
            
        # Get file metadata
        try:
            file_size = os.path.getsize(file_path)
            last_modified = os.path.getmtime(file_path)
            
            # Check if client has a cached version (If-Modified-Since)
            if 'if-modified-since' in headers:
                if_modified_since = parse_http_date(headers['if-modified-since'])
                
                if if_modified_since and last_modified <= if_modified_since:
                    self._send_response(client_socket, 304, {
                        'Date': format_http_date(),
                        'Server': self.config.server_name,
                        'Last-Modified': format_http_date(last_modified)
                    })
                    self.stats['status_3xx'] += 1
                    return
        except Exception as e:
            self.logger.error(f"Error getting file metadata {file_path}: {e}")
            self._send_error_response(client_socket, 500, "Internal Server Error", send_body=False)
            return
            
        # Get content type
        content_type, encoding = get_mime_type(file_path)
        headers = {
            'Content-Type': content_type,
            'Content-Length': str(file_size),
            'Date': format_http_date(),
            'Server': self.config.server_name,
            'Last-Modified': format_http_date(last_modified)
        }
        
        # Set caching headers if enabled
        if self.config.enable_browser_caching:
            cache_time = self.config.browser_cache_time
            headers['Cache-Control'] = f'public, max-age={cache_time}'
            headers['Expires'] = format_http_date(time.time() + cache_time)
            
        # Set security headers if enabled
        if self.config.enable_security_headers:
            headers.update(self._get_security_headers())
            
        # Send the response (HEAD has no body)
        self._send_response(client_socket, 200, headers)
        self.stats['status_2xx'] += 1
        
    def _handle_post(self, client_socket, request):
        """
        Handle a POST request.
        
        Args:
            client_socket: Client socket object
            request: Parsed request dictionary
        """
        path = request['path']
        
        # Check if we're handling form submission
        if path == '/submit':
            self._handle_form_submission(client_socket, request)
        else:
            # For any other path, return 404
            self._send_error_response(client_socket, 404, "File not found")
            
    def _handle_options(self, client_socket, request):
        """
        Handle an OPTIONS request.
        
        Args:
            client_socket: Client socket object
            request: Parsed request dictionary
        """
        headers = {
            'Allow': 'GET, HEAD, POST, OPTIONS',
            'Date': format_http_date(),
            'Server': self.config.server_name,
            'Content-Length': '0'
        }
        
        # Set CORS headers if enabled
        if self.config.enable_cors:
            headers.update(self._get_cors_headers())
            
        # Set security headers if enabled
        if self.config.enable_security_headers:
            headers.update(self._get_security_headers())
            
        # Send the response
        self._send_response(client_socket, 200, headers)
        self.stats['status_2xx'] += 1
        
    def _handle_form_submission(self, client_socket, request):
        """
        Handle form submission.
        
        Args:
            client_socket: Client socket object
            request: Parsed request dictionary
        """
        # Check if form data is present
        form_data = request.get('form', {})
        form_files = request.get('files', {})
        json_data = request.get('json', None)
        
        if not form_data and not form_files and not json_data:
            self._send_error_response(client_socket, 400, "No form data found")
            return
            
        # Process the form submission
        try:
            # Example: Save uploaded files
            if form_files and self.config.enable_file_uploads:
                uploads_dir = os.path.join(self.config.document_root, 'uploads')
                
                # Create uploads directory if it doesn't exist
                if not os.path.exists(uploads_dir):
                    os.makedirs(uploads_dir)
                    
                # Save each uploaded file
                for field_name, file_info in form_files.items():
                    # Sanitize filename to prevent directory traversal
                    filename = os.path.basename(file_info['filename'])
                    
                    # Generate unique filename to prevent overwrites
                    timestamp = int(time.time())
                    unique_filename = f"{timestamp}_{filename}"
                    
                    # Save the file
                    with open(os.path.join(uploads_dir, unique_filename), 'wb') as f:
                        f.write(file_info['content'])
                        
            # Redirect to success page
            headers = {
                'Location': '/submit_success.html',
                'Date': format_http_date(),
                'Server': self.config.server_name,
                'Content-Length': '0'
            }
            
            # Send redirect response
            self._send_response(client_socket, 302, headers)
            self.stats['status_3xx'] += 1
            
        except Exception as e:
            self.logger.error(f"Error processing form submission: {e}")
            self.logger.debug(traceback.format_exc())
            self._send_error_response(client_socket, 500, "Internal Server Error")
            
    def _send_directory_listing(self, client_socket, dir_path, request_path):
        """
        Send directory listing.
        
        Args:
            client_socket: Client socket object
            dir_path: Directory path on the server
            request_path: Path in the request
        """
        try:
            # Get directory contents
            entries = os.listdir(dir_path)
            entries.sort()
            
            # Build HTML for directory listing
            html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Directory: {request_path}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background-color: white;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        th {{
            background-color: #f8f9fa;
            font-weight: 600;
        }}
        tr:hover {{
            background-color: #f8f9fa;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .icon {{
            margin-right: 6px;
            color: #7f8c8d;
        }}
        .parent {{
            font-weight: bold;
            margin-bottom: 20px;
            display: inline-block;
        }}
    </style>
</head>
<body>
    <h1>Directory Listing: {request_path}</h1>
"""
            # Add parent directory link if not at root
            if request_path != '/':
                parent_path = '/'.join(request_path.rstrip('/').split('/')[:-1]) or '/'
                html += f'    <a href="{parent_path}" class="parent">↩ Parent Directory</a>\n'
                
            html += """    <table>
        <thead>
            <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Size</th>
                <th>Last Modified</th>
            </tr>
        </thead>
        <tbody>
"""
            
            # Add entries
            for entry in entries:
                entry_path = os.path.join(dir_path, entry)
                full_path = os.path.join(request_path, entry)
                
                # Skip hidden files
                if entry.startswith('.') and not self.config.show_hidden_files:
                    continue
                    
                # Get file information
                is_dir = os.path.isdir(entry_path)
                if is_dir:
                    entry_type = "Directory"
                    size = "-"
                    entry += "/"
                else:
                    entry_type = get_mime_type(entry_path)[0] or "Unknown"
                    size = human_readable_size(os.path.getsize(entry_path))
                    
                # Format last modified time
                mtime = os.path.getmtime(entry_path)
                last_modified = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                
                # Build the HTML row
                icon = "📁" if is_dir else "📄"
                html += f"""        <tr>
            <td><a href="{full_path}"><span class="icon">{icon}</span> {entry}</a></td>
            <td>{entry_type}</td>
            <td>{size}</td>
            <td>{last_modified}</td>
        </tr>
"""
                
            html += """    </tbody>
    </table>
    <div style="margin-top: 20px; font-size: 12px; color: #777;">
        Generated by Python Socket Server on {0}
    </div>
</body>
</html>""".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            
            # Send the directory listing
            headers = {
                'Content-Type': 'text/html; charset=utf-8',
                'Content-Length': str(len(html)),
                'Date': format_http_date(),
                'Server': self.config.server_name
            }
            
            # Set security headers if enabled
            if self.config.enable_security_headers:
                headers.update(self._get_security_headers())
                
            # Send the response
            self._send_response(client_socket, 200, headers, html.encode('utf-8'))
            self.stats['status_2xx'] += 1
            
        except Exception as e:
            self.logger.error(f"Error generating directory listing: {e}")
            self.logger.debug(traceback.format_exc())
            self._send_error_response(client_socket, 500, "Internal Server Error")
            
    def _send_server_status(self, client_socket, request):
        """
        Send server status page.
        
        Args:
            client_socket: Client socket object
            request: Parsed request dictionary
        """
        from .utils import generate_status_page
        
        # Gather server statistics
        if self.file_cache:
            cache_stats = self.file_cache.stats()
            cache_enabled = True
            cache_size = cache_stats.get('size', 0)
            cache_max_size = cache_stats.get('max_size', 0)
            cache_hit_ratio = cache_stats.get('hit_ratio', 0)
            memory_usage = human_readable_size(cache_stats.get('memory_usage_estimate', 0))
        else:
            cache_enabled = False
            cache_size = 0
            cache_max_size = 0
            cache_hit_ratio = 0
            memory_usage = "0 B"
            
        # Calculate average response time
        if self.stats['response_times']:
            avg_response_time = sum(self.stats['response_times']) / len(self.stats['response_times']) * 1000
        else:
            avg_response_time = 0
            
        # Get uptime
        uptime_seconds = time.time() - self.config.start_time
        days, remainder = divmod(uptime_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime = f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"
        
        # Build server stats dict
        server_stats = {
            'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'uptime': uptime,
            'version': self.config.server_version,
            'host': self.config.host,
            'port': self.config.port,
            'root_directory': self.config.document_root,
            'active_connections': self.config.active_connections,
            'total_requests': self.stats['total_requests'],
            'requests_per_second': round(self.stats['total_requests'] / max(1, uptime_seconds), 2),
            'avg_response_time': round(avg_response_time, 2),
            'cache_enabled': cache_enabled,
            'cache_size': cache_size,
            'cache_max_size': cache_max_size,
            'cache_hit_ratio': cache_hit_ratio,
            'memory_usage': memory_usage,
            'status_2xx': self.stats['status_2xx'],
            'status_3xx': self.stats['status_3xx'],
            'status_4xx': self.stats['status_4xx'],
            'status_5xx': self.stats['status_5xx']
        }
        
        # Generate HTML status page
        html = generate_status_page(server_stats)
        
        # Send the response
        headers = {
            'Content-Type': 'text/html; charset=utf-8',
            'Content-Length': str(len(html)),
            'Date': format_http_date(),
            'Server': self.config.server_name,
            'Cache-Control': 'no-store, no-cache, must-revalidate'
        }
        
        # Send the response
        self._send_response(client_socket, 200, headers, html.encode('utf-8'))
        self.stats['status_2xx'] += 1
        
    def _send_response(self, client_socket, status_code, headers, body=None):
        """
        Send HTTP response.
        
        Args:
            client_socket: Client socket object
            status_code: HTTP status code
            headers: Response headers dict
            body: Response body (bytes or str)
        """
        try:
            # Get status message
            status_message = HTTP_STATUS.get(status_code, 'Unknown')
            
            # Build response line
            response_line = f"HTTP/1.1 {status_code} {status_message}\r\n"
            
            # Add Date and Server headers if not present
            if 'Date' not in headers:
                headers['Date'] = format_http_date()
                
            if 'Server' not in headers:
                headers['Server'] = self.config.server_name
                
            # Add CORS headers if enabled
            if self.config.enable_cors:
                headers.update(self._get_cors_headers())
                
            # Build headers string
            header_lines = [f"{key}: {value}" for key, value in headers.items()]
            headers_str = "\r\n".join(header_lines) + "\r\n\r\n"
            
            # Encode body if it's a string
            if body is not None and isinstance(body, str):
                body = body.encode('utf-8')
                
            # Send response line and headers
            client_socket.sendall(response_line.encode('utf-8'))
            client_socket.sendall(headers_str.encode('utf-8'))
            
            # Send body if present and not a HEAD request
            if body is not None:
                client_socket.sendall(body)
                
        except Exception as e:
            self.logger.error(f"Error sending response: {e}")
            
    def _send_error_response(self, client_socket, status_code, message, send_body=True):
        """
        Send error response.
        
        Args:
            client_socket: Client socket object
            status_code: HTTP status code
            message: Error message
            send_body: Whether to send the body or not (for HEAD requests)
        """
        # Update error statistics based on status code
        if 400 <= status_code < 500:
            self.stats['status_4xx'] += 1
        elif 500 <= status_code < 600:
            self.stats['status_5xx'] += 1
            
        # Get status message
        status_message = HTTP_STATUS.get(status_code, 'Unknown')
        
        # Check for custom error page
        error_page_path = os.path.join(self.config.document_root, f"{status_code}.html")
        custom_error_page = None
        
        if os.path.isfile(error_page_path):
            try:
                with open(error_page_path, 'rb') as f:
                    custom_error_page = f.read()
            except:
                pass
                
        # Use custom error page or generate default
        if custom_error_page and send_body:
            body = custom_error_page
            content_type = 'text/html; charset=utf-8'
        elif send_body:
            # Generate error page using template
            html = ERROR_PAGE_TEMPLATE.format(
                code=status_code,
                status=status_message,
                message=message,
                date=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
            body = html.encode('utf-8')
            content_type = 'text/html; charset=utf-8'
        else:
            body = None
            content_type = 'text/plain'
            
        # Prepare headers
        headers = {
            'Content-Type': content_type,
            'Date': format_http_date(),
            'Server': self.config.server_name,
            'Connection': 'close'
        }
        
        if body:
            headers['Content-Length'] = str(len(body))
            
        # Set security headers if enabled
        if self.config.enable_security_headers:
            headers.update(self._get_security_headers())
            
        # Send response
        self._send_response(client_socket, status_code, headers, body)
        
    def _get_security_headers(self):
        """
        Get security headers.
        
        Returns:
            dict: Security headers
        """
        return {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'SAMEORIGIN',
            'X-XSS-Protection': '1; mode=block',
            'Content-Security-Policy': "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'",
            'Referrer-Policy': 'strict-origin-when-cross-origin'
        }
        
    def _get_cors_headers(self):
        """
        Get CORS headers.
        
        Returns:
            dict: CORS headers
        """
        return {
            'Access-Control-Allow-Origin': self.config.cors_allow_origin,
            'Access-Control-Allow-Methods': 'GET, POST, HEAD, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Accept, X-Requested-With',
            'Access-Control-Max-Age': '86400'  # 24 hours
        }