# 🌐 Advanced Python Web Server from Scratch

![Python Version](https://img.shields.io/badge/python-3.6%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Dependencies](https://img.shields.io/badge/dependencies-socket-orange)
![Status](https://img.shields.io/badge/status-educational-brightgreen)

> A feature-rich, educational web server built from scratch using only Python's standard libraries

## 📋 Overview

This project implements a powerful, fully-featured web server built completely from scratch using only Python's standard socket library. It serves as both a functional web server and an educational tool for understanding HTTP protocol fundamentals.

Perfect for:

- Learning how web servers work behind the scenes
- Studying socket programming in Python
- Understanding HTTP protocol implementation
- Creating lightweight web servers for development

## ✨ Features

### 🐍 Pure Python

Built using only the standard library (primarily the socket module)

### 🔌 User-Friendly Connection Display

Clear connection information showing multiple access URLs:

- Local URLs for same-machine access (localhost/127.0.0.1)
- Network URL for accessing from other devices
- See [CONNECTION.md](docs/CONNECTION.md) for details

### 🧵 Advanced Threading

Thread pool implementation for efficient concurrent connection handling

### 🌐 Comprehensive HTTP Support

Full HTTP/1.1 implementation with support for GET, POST, HEAD, and OPTIONS methods

### 🔒 HTTPS Support

SSL/TLS encryption for secure connections with certificate management

### 📂 Advanced Static File Serving

Serves files with proper MIME type detection, caching headers, and conditional requests

### ⚠️ Custom Error Pages

Includes custom error pages with graceful fallback generation

### 🗂️ Directory Listing

Customizable directory browsing with file details and navigation

### ⚡ LRU Caching System

Sophisticated least-recently-used caching system with size and time limits

### 📝 Advanced Logging

Comprehensive logging with rotation, different output formats, and log levels

### ⚙️ Multi-source Configuration

Configuration from files, command line arguments, and environment variables

### 🎨 Colored Console Output

Enhanced terminal logging with colorama (automatically detected)

### 🔐 Security Features

Protection against directory traversal, content-type sniffing, and other vulnerabilities

### 📊 Status Dashboard

Built-in server statistics and monitoring dashboard

### 📤 Form Processing

Handle form submissions with file uploads and multipart data

### ⚓ CORS Support

Cross-Origin Resource Sharing headers for API usage

### 🏗️ Modular Design

Clean, maintainable architecture with proper separation of concerns

## 🏛️ Architecture

The server follows a clean, modular object-oriented design with these main components:

| Component          | Description                                                                       |
| ------------------ | --------------------------------------------------------------------------------- |
| **WebServer**      | Core server class that manages the socket and thread pool for connection handling |
| **ServerConfig**   | Centralized configuration management with multi-source support                    |
| **RequestHandler** | Processes HTTP requests and generates appropriate responses                       |
| **FileCache**      | LRU caching system for frequently accessed files to improve performance           |
| **Utils**          | Collection of utility functions for logging, MIME types, security, and more       |

### 🔄 Data Flow

![Data Flow](https://mermaid.ink/img/pako:eNp9kc9qwzAMxl_F6NTB8gI5DLbRjZVCGWPsEHywYq8xJHZwlNJR-u4zSbexy3YRks33_fgjncDaFqEEr_2ZGnsxj8bWCF-o1V0IYeABvYfGd0v6NKrXlV6NBUG3pPjKOzE2hGCM7tt4N9I3tYa_Wfx6Ir_QJ-rtK7U3bnlJPkqjdQnPKLiDoMBZCLjnNm34YCOsodfYYvbkzsnwgg1-YGuR_oDqvcdMTYDsouSkSgj9AuKBNRbXh-PpUC6CoOv7Ye9QU5bnKBcIJxtkSH7vg6lzrzs2dQmMIzjrTZO4sgCfItv9k7tUWewA_vbZzG5NSCcMduZSzc_Ps8t9BdvVXf8DtjOX8w)

1. **Client Connection**: The WebServer accepts a connection and passes it to a new RequestHandler thread
2. **Request Parsing**: The RequestHandler parses the HTTP request (method, path, headers, body)
3. **Request Processing**: Based on the method (GET/POST), the appropriate handler is called
4. **Response Generation**: The server generates HTTP headers and retrieves the requested content
5. **Response Delivery**: The complete HTTP response is sent back to the client
6. **Connection Cleanup**: The connection is closed (unless Keep-Alive is implemented)

## 🚀 Running the Server

Start the server with a single command:

```bash
python run.py
```

For specific configurations:

```bash
python run.py --host 0.0.0.0 --port 8080 --document-root /path/to/content
```

> **Note on Backwards Compatibility**: The server supports both the new parameter names and legacy names for compatibility with older configurations. For example, both `--document-root` and `--directory` will work, as will both `--directory-listing` and `--enable-directory-listing` in the config file.

### ⌨️ Command Line Options

| Option                | Description                                 |
| --------------------- | ------------------------------------------- |
| `-H, --host`          | Host address to bind to                     |
| `-p, --port`          | Port to listen on                           |
| `-d, --document-root` | Document root directory                     |
| `-c, --config`        | Path to configuration file                  |
| `--log-level`         | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `--log-file`          | Path to log file for output                 |
| `--no-color`          | Disable colored logging                     |
| `--directory-listing` | Enable directory listing                    |
| `--enable-cache`      | Enable file caching                         |
| `--max-threads`       | Maximum number of worker threads            |
| `--ssl`               | Enable SSL/HTTPS                            |
| `--ssl-cert`          | Path to SSL certificate file                |
| `--ssl-key`           | Path to SSL key file                        |
| `--request-timeout`   | Request timeout in seconds                  |
| `--connection-queue`  | Connection queue size                       |

## ⚙️ Configuration

The server can be configured through a `config.json` file with extensive options:

```json
{
  "host": "0.0.0.0",
  "port": 8000,
  "document_root": "htdocs",
  "server_name": "Python Socket Server/1.0",
  "server_version": "1.0.0",

  "log_level": "INFO",
  "log_file": "logs/server.log",
  "colored_logging": true,

  "max_threads": 20,
  "connection_queue": 10,
  "request_timeout": 30,

  "directory_listing": true,
  "show_hidden_files": false,

  "enable_cache": true,
  "cache_max_size": 100,
  "cache_max_age": 3600,

  "enable_browser_caching": true,
  "browser_cache_time": 86400,

  "enable_security_headers": true,
  "enable_cors": true,
  "cors_allow_origin": "*",

  "enable_file_uploads": true,
  "max_upload_size": 10485760,

  "enable_server_status": true,

  "enable_ssl": false,
  "ssl_cert": "cert.pem",
  "ssl_key": "key.pem",
  "ssl_password": null
}
```

## 📁 Project Structure

```text
https-server/
├── run.py             # Main entry point script
├── server/            # Server package
│   ├── __init__.py    # Package initialization
│   ├── server.py      # Core server implementation
│   ├── config.py      # Configuration management
│   ├── handler.py     # HTTP request handler
│   └── utils.py       # Utility functions and classes
├── config.json        # Server configuration
└── htdocs/            # Web root directory
    ├── index.html     # Sample homepage
    ├── styles.css     # CSS styles
    ├── script.js      # JavaScript file
    ├── 404.html       # Custom 404 error page
    └── 500.html       # Custom 500 error page
```

## 🛠️ Future Enhancements

| Feature                | Description                                           |
| ---------------------- | ----------------------------------------------------- |
| **HTTP/2 Support**     | Add support for the newer HTTP protocol version       |
| **WebSockets**         | Enable real-time bidirectional communication          |
| **Authentication**     | Implement basic auth and other authentication methods |
| **HTTP Compression**   | Add GZIP/Deflate compression for responses            |
| **Advanced Routing**   | Create a more sophisticated routing system            |
| **Template Engine**    | Integrate template rendering capabilities             |
| **REST API Framework** | Add features to easily build REST APIs                |
| **Rate Limiting**      | Implement request rate limiting for endpoints         |
| **Async Processing**   | Add support for asynchronous request handling         |
| **Load Balancing**     | Implement basic load balancing capabilities           |

## 📊 Performance

The server is designed for educational purposes but offers reasonable performance for development use:

- Can handle multiple concurrent connections through threading
- Implements basic file caching for frequently accessed resources
- Optimized for serving static content efficiently

## 🖥️ Usage Examples

### Serving Static Files

The server automatically serves static files from the `htdocs` directory:

```bash
# Start the server with default settings
python run.py

# Access in browser
# http://localhost:8000/
```

### Using Custom Port and Directory

```bash
# Start server on port 9000 serving files from "public" directory
python run.py --port 9000 --document-root public
```

### Enabling HTTPS

```bash
# Generate self-signed certificates (for development)
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes

# Start server with HTTPS enabled
python run.py --ssl --ssl-cert cert.pem --ssl-key key.pem
```

### Handling Form Uploads

The server can process form submissions with file uploads:

```html
<form action="/submit" method="post" enctype="multipart/form-data">
  <input type="text" name="username" />
  <input type="file" name="profile_picture" />
  <input type="submit" value="Submit" />
</form>
```

### Server Status Dashboard

Monitor server performance with the built-in dashboard:

```bash
# Access the server status page
http://localhost:8000/server-status
```

### Directory Listing

When a directory is accessed without an index.html file, the server generates a directory listing (if enabled):

```bash
# Access http://localhost:8000/images/
# Shows list of files in the /htdocs/images/ directory with details
```

### Thread Pool Configuration

Optimize for your hardware by adjusting thread pool size:

```bash
# For high-traffic servers on multi-core systems
python run.py --max-threads 50
```

## 🙏 Contributing

Contributions are welcome! Feel free to:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.
