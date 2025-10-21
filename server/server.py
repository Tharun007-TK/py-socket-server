#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Python Socket Server Main Module
-------------------------------
A modular, production-ready HTTP server implemented using Python socket library.
"""

import socket
import threading
import time
import logging
import ssl
import os
import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from .config import ServerConfig
from .handler import RequestHandler
from .utils import FileCache, setup_logging, check_hostname_availability

class WebServer:
    """
    Web server class that handles incoming connections and routes them
    to the appropriate handler.
    """
    
    def __init__(self, config_file=None, **kwargs):
        """
        Initialize the web server.
        
        Args:
            config_file: Path to the configuration file
            **kwargs: Additional configuration parameters that override config file
        """
        # Initialize configuration
        self.config = ServerConfig(config_file, **kwargs)
        
        # Initialize logging
        self.logger = setup_logging(
            log_level=self.config.log_level,
            log_file=self.config.log_file,
            use_colored_logging=self.config.colored_logging
        )
        self.logger = logging.getLogger('WebServer')
        
        # Initialize file cache if enabled
        if self.config.enable_cache:
            self.file_cache = FileCache(
                max_size=self.config.cache_max_size,
                max_age=self.config.cache_max_age
            )
            self.logger.info(f"File cache initialized with max_size={self.config.cache_max_size}, max_age={self.config.cache_max_age}s")
        else:
            self.file_cache = None
            self.logger.info("File cache disabled")
            
        # Initialize request handler
        self.request_handler = RequestHandler(self.config, self.file_cache)
        
        # Server state
        self.server_socket = None
        self.is_running = False
        self.start_time = time.time()
        self.config.start_time = self.start_time
        
        # Thread pool for handling connections
        self.thread_pool = ThreadPoolExecutor(
            max_workers=self.config.max_threads,
            thread_name_prefix="WebServerWorker"
        )
        
        # Active connections tracking
        self.active_connections = 0
        self.active_connections_lock = threading.Lock()
        
        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # Set configuration start time
        self.config.start_time = self.start_time
        
    def _signal_handler(self, sig, frame):
        """
        Handle termination signals gracefully.
        
        Args:
            sig: Signal number
            frame: Current stack frame
        """
        self.logger.info(f"Received signal {sig}, shutting down...")
        self.shutdown()
        sys.exit(0)
        
    def start(self):
        """
        Start the web server.
        """
        if self.is_running:
            self.logger.warning("Server is already running")
            return
            
        try:
            # Check if host:port is available
            if not check_hostname_availability(self.config.host, self.config.port):
                self.logger.error(f"Address {self.config.host}:{self.config.port} is already in use")
                return False
                
            # Create server socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Set socket options
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind socket
            self.server_socket.bind((self.config.host, self.config.port))
            
            # Start listening
            self.server_socket.listen(self.config.connection_queue)
            
            # Set up SSL if enabled
            if self.config.enable_ssl:
                if not os.path.isfile(self.config.ssl_cert) or not os.path.isfile(self.config.ssl_key):
                    self.logger.error(f"SSL certificate or key file not found. Disabling SSL.")
                    self.config.enable_ssl = False
                else:
                    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                    try:
                        context.load_cert_chain(
                            certfile=self.config.ssl_cert, 
                            keyfile=self.config.ssl_key,
                            password=self.config.ssl_password
                        )
                        self.server_socket = context.wrap_socket(
                            self.server_socket, 
                            server_side=True
                        )
                        self.logger.info("SSL enabled")
                    except Exception as e:
                        self.logger.error(f"Error setting up SSL: {e}")
                        self.logger.warning("Starting server without SSL")
                        self.config.enable_ssl = False
                        
                        # Create new socket without SSL
                        self.server_socket.close()
                        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                        self.server_socket.bind((self.config.host, self.config.port))
                        self.server_socket.listen(self.config.connection_queue)
                        
            # Set flag and start accept loop
            self.is_running = True
            protocol = "https" if self.config.enable_ssl else "http"
            
            # Determine access URLs
            bind_url = f"{protocol}://{self.config.host}:{self.config.port}"
            
            # Get local IP addresses for accessing the server
            localhost_url = f"{protocol}://localhost:{self.config.port}"
            loopback_url = f"{protocol}://127.0.0.1:{self.config.port}"
            
            # Log server start with access information
            self.logger.info(f"Server started and bound to {bind_url}")
            self.logger.info(f"Access the server locally at: {localhost_url} or {loopback_url}")
            
            # Try to get the machine's network IP address
            try:
                hostname = socket.gethostname()
                ip_address = socket.gethostbyname(hostname)
                if ip_address != "127.0.0.1":
                    network_url = f"{protocol}://{ip_address}:{self.config.port}"
                    self.logger.info(f"Access from other devices on your network: {network_url}")
            except Exception:
                pass  # Silently ignore if we can't get the network IP
                
            self.logger.info(f"Serving files from {self.config.document_root}")
            
            # Start acceptance loop in a separate thread
            threading.Thread(target=self._accept_connections, daemon=True).start()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting server: {e}")
            if self.server_socket:
                self.server_socket.close()
                self.server_socket = None
            self.is_running = False
            return False
            
    def shutdown(self):
        """
        Shut down the web server gracefully.
        """
        if not self.is_running:
            return
            
        self.logger.info("Shutting down server...")
        self.is_running = False
        
        # Close server socket
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
            
        # Shutdown thread pool
        self.logger.debug("Shutting down thread pool...")
        self.thread_pool.shutdown(wait=True)
        
        # Cleanup cache if enabled
        if self.file_cache:
            self.file_cache.clear()
            
        self.logger.info("Server shutdown complete")
        
    def _accept_connections(self):
        """
        Accept incoming connections.
        """
        try:
            while self.is_running:
                try:
                    # Accept new connection
                    client_socket, client_address = self.server_socket.accept()
                    
                    # Set socket options
                    client_socket.settimeout(self.config.request_timeout)
                    
                    # Increment active connections counter
                    with self.active_connections_lock:
                        self.active_connections += 1
                        self.config.active_connections = self.active_connections
                        
                    # Submit to thread pool
                    self.thread_pool.submit(
                        self._handle_client,
                        client_socket,
                        client_address
                    )
                    
                except (socket.timeout, ConnectionError):
                    # Non-fatal errors, continue accepting connections
                    continue
                except Exception as e:
                    if self.is_running:
                        self.logger.error(f"Error accepting connection: {e}")
                        # Sleep a bit to prevent CPU spinning on repeated errors
                        time.sleep(0.1)
                        
        except Exception as e:
            if self.is_running:
                self.logger.error(f"Fatal error in connection acceptance loop: {e}")
                self.is_running = False
                
    def _handle_client(self, client_socket, client_address):
        """
        Handle client connection.
        
        Args:
            client_socket: Client socket object
            client_address: Client address tuple (ip, port)
        """
        try:
            # Handle the request
            self.request_handler.handle_request(client_socket, client_address)
        except Exception as e:
            self.logger.error(f"Error handling client {client_address}: {e}")
        finally:
            # Close the socket if it's not already closed
            try:
                client_socket.close()
            except:
                pass
                
            # Decrement active connections counter
            with self.active_connections_lock:
                self.active_connections -= 1
                self.config.active_connections = self.active_connections
                
    def wait_for_shutdown(self):
        """
        Wait for server shutdown (can be called after start() to keep the main thread alive).
        """
        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt, shutting down...")
            self.shutdown()
            
    def restart(self):
        """
        Restart the server.
        """
        self.logger.info("Restarting server...")
        self.shutdown()
        return self.start()
        
    @property
    def stats(self):
        """
        Get server statistics.
        
        Returns:
            dict: Server statistics
        """
        uptime = time.time() - self.start_time
        
        stats = {
            'uptime': uptime,
            'uptime_formatted': self._format_uptime(uptime),
            'active_connections': self.active_connections,
            'total_requests': self.request_handler.stats['total_requests'],
            'requests_per_second': self.request_handler.stats['total_requests'] / max(1, uptime),
            'status_2xx': self.request_handler.stats['status_2xx'],
            'status_3xx': self.request_handler.stats['status_3xx'],
            'status_4xx': self.request_handler.stats['status_4xx'],
            'status_5xx': self.request_handler.stats['status_5xx']
        }
        
        # Add cache stats if enabled
        if self.file_cache:
            cache_stats = self.file_cache.stats()
            stats.update({
                'cache_enabled': True,
                'cache_size': cache_stats['size'],
                'cache_max_size': cache_stats['max_size'],
                'cache_hit_ratio': cache_stats['hit_ratio'],
                'cache_hits': cache_stats['hits'],
                'cache_misses': cache_stats['misses']
            })
        else:
            stats['cache_enabled'] = False
            
        return stats
        
    def _format_uptime(self, seconds):
        """
        Format uptime in seconds to human readable format.
        
        Args:
            seconds: Uptime in seconds
            
        Returns:
            str: Formatted uptime
        """
        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{int(days)}d")
        if hours > 0 or days > 0:
            parts.append(f"{int(hours)}h")
        if minutes > 0 or hours > 0 or days > 0:
            parts.append(f"{int(minutes)}m")
        parts.append(f"{int(seconds)}s")
        
        return " ".join(parts)