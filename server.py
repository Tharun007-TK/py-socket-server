#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Advanced Python Web Server (Legacy Interface)
--------------------------------------------
This is a backward compatibility wrapper around the modular server implementation.
For new applications, use run.py instead.

This module will be deprecated in future versions.
"""

import os
import sys
import logging
import argparse
import warnings

# Show deprecation warning
warnings.warn(
    "This module is deprecated. Please use run.py instead.",
    DeprecationWarning,
    stacklevel=2
)

# Import from modular server package
try:
    from server.server import WebServer
except ImportError:
    print("Error: Cannot import the modular server package.")
    print("Make sure you have the 'server' directory in the same location as this script.")
    sys.exit(1)


def main():
    """
    Main entry point for legacy interface.
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Python Socket Web Server (Legacy Interface)')
    
    # Basic server options
    parser.add_argument('-p', '--port', type=int, help='Port to listen on')
    parser.add_argument('-d', '--directory', type=str, help='Document root directory')
    parser.add_argument('-c', '--config', type=str, help='Path to configuration file')
    
    args = parser.parse_args()
    
    # Convert arguments to the new format
    config_args = {}
    
    if args.port is not None:
        config_args['port'] = args.port
        
    if args.directory is not None:
        config_args['document_root'] = args.directory
        
    # Create and start server with the new interface
    print("Starting server using new modular implementation...")
    print("NOTE: This script is deprecated. Please use run.py instead.")
    
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