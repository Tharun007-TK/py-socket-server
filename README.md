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

### 🧵 Multi-threading

Handles multiple client connections concurrently using threading

### 🌐 HTTP Support

Full HTTP/1.1 implementation with support for GET and POST requests

### 📂 Static File Serving

Serves various file types with proper MIME type detection

### ⚠️ Custom Error Pages

Includes custom 404 and 500 error pages with fallback generation

### 🗂️ Directory Listing

Option to browse directories when index.html is not found

### ⚡ Caching System

Basic file caching for improved performance with configurable settings

### 📝 Comprehensive Logging

Records all requests with IP, method, path, status, and timestamps

### ⚙️ JSON Configuration

Easily customizable server settings through config.json

### 🎨 Colored Console Output

Enhanced terminal logging with colorama (optional)

### 🏗️ Object-oriented Design

Clean architecture with WebServer and RequestHandler classes

## 🏛️ Architecture

The server follows a clean object-oriented design with three main components:

| Component          | Description                                                                            |
| ------------------ | -------------------------------------------------------------------------------------- |
| **WebServer**      | The core server class that manages the socket, accepts connections, and spawns threads |
| **RequestHandler** | Processes individual client requests and generates responses                           |
| **FileCache**      | An optional caching system for frequently accessed files                               |

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
python server.py
```

For specific configurations:

```bash
python server.py --port 8080 --directory /path/to/content
```

### ⌨️ Command Line Options

| Option            | Description                                       |
| ----------------- | ------------------------------------------------- |
| `-c, --config`    | Path to configuration file (default: config.json) |
| `-p, --port`      | Server port (overrides config file)               |
| `-d, --directory` | Root directory (overrides config file)            |

## ⚙️ Configuration

The server can be configured through a `config.json` file with the following options:

```json
{
  "host": "0.0.0.0",
  "port": 8000,
  "root_directory": "htdocs",
  "enable_directory_listing": true,
  "enable_caching": true,
  "cache_max_size": 100,
  "cache_max_age": 3600,
  "log_level": "INFO",
  "use_colored_logging": true
}
```

## 📁 Project Structure

```text
https-server/
├── server.py          # Main server implementation
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
| **HTTPS/TLS**          | Add secure connections with SSL/TLS                   |
| **Advanced Routing**   | Create a more sophisticated routing system            |
| **Template Engine**    | Integrate template rendering capabilities             |
| **REST API Framework** | Add features to easily build REST APIs                |

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
python server.py

# Access in browser
# http://localhost:8000/
```

### Using Custom Port and Directory

```bash
# Start server on port 9000 serving files from "public" directory
python server.py --port 9000 --directory public
```

### Handling POST Requests

The server can process form submissions:

```html
<form action="/submit" method="post">
  <input type="text" name="username" />
  <input type="submit" value="Submit" />
</form>
```

### Directory Listing

When a directory is accessed without an index.html file, the server generates a directory listing (if enabled in config):

```bash
# Access http://localhost:8000/images/
# Shows list of files in the /htdocs/images/ directory
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
