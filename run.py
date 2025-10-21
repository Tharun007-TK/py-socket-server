#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Python Socket-Based HTTP Server
------------------------------
A production-ready HTTP server implemented from scratch using Python's socket library.
This is the main entry point for the server.
"""

import os
import sys
import argparse

# Add parent directory to path so we can import the server package
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from server.server import WebServer


def main():
    """
    Main entry point for the server.
    """
    parser = argparse.ArgumentParser(description='Python Socket HTTP Server')
    
    # Basic server options
    parser.add_argument('-H', '--host', type=str, help='Host address to bind to')
    parser.add_argument('-p', '--port', type=int, help='Port to listen on')
    parser.add_argument('-d', '--document-root', type=str, help='Document root directory')
    parser.add_argument('-c', '--config', type=str, help='Path to configuration file')
    
    # Logging options
    parser.add_argument('--log-level', type=str, choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                        help='Logging level')
    parser.add_argument('--log-file', type=str, help='Path to log file')
    parser.add_argument('--no-color', action='store_true', help='Disable colored logging')
    
    # Server behavior options
    parser.add_argument('--directory-listing', action='store_true', help='Enable directory listing')
    parser.add_argument('--enable-cache', action='store_true', help='Enable file caching')
    parser.add_argument('--max-threads', type=int, help='Maximum number of worker threads')
    
    # SSL options
    parser.add_argument('--ssl', action='store_true', help='Enable SSL/HTTPS')
    parser.add_argument('--ssl-cert', type=str, help='Path to SSL certificate file')
    parser.add_argument('--ssl-key', type=str, help='Path to SSL key file')
    
    # Performance options
    parser.add_argument('--request-timeout', type=int, help='Request timeout in seconds')
    parser.add_argument('--connection-queue', type=int, help='Connection queue size')
    
    args = parser.parse_args()
    
    # Convert arguments to dictionary, excluding None values
    config_args = {k: v for k, v in vars(args).items() if v is not None}
    
    # Special handling for boolean flags
    if 'no_color' in config_args:
        config_args['colored_logging'] = not config_args.pop('no_color')
    
    # Create and start server
    server = WebServer(config_file=args.config, **config_args)
    
    if server.start():
        try:
            # Keep the main thread alive until interrupted
            server.wait_for_shutdown()
        except KeyboardInterrupt:
            print("\nShutting down gracefully...")
        finally:
            server.shutdown()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())