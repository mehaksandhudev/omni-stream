#!/bin/bash

echo "=== Updating yt-dlp to latest version ==="
pip install --upgrade yt-dlp

echo "=== yt-dlp version: ==="
yt-dlp --version

echo "=== Starting YouTube Download Service ==="
exec gunicorn --bind 0.0.0.0:5002 --timeout 600 --workers 2 app:app
