@echo off
REM Python Socket Server Launcher
REM Run this script to start the server with default settings

echo Starting Python Socket Server...
python run.py

REM If you want to customize server settings, edit config.json or use command-line options
REM Examples:
REM python run.py --port 9000
REM python run.py --ssl --ssl-cert cert.pem --ssl-key key.pem
REM python run.py --document-root /path/to/webfiles