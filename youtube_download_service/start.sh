#!/bin/bash
set -e

echo "=== Updating yt-dlp to latest version ==="
pip install --user --upgrade --quiet yt-dlp
export PATH="$HOME/.local/bin:$PATH"

echo "=== yt-dlp version: $(yt-dlp --version) ==="
echo "=== Starting YouTube Download Service v1.0.0 ==="

exec gunicorn \
    --bind 0.0.0.0:5002 \
    --timeout 600 \
    --workers "${GUNICORN_WORKERS:-2}" \
    --access-logfile - \
    --error-logfile - \
    app:app
