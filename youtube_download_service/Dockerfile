FROM python:3.10-slim-bookworm

LABEL maintainer="mehaksandhudev@gmail.com"
LABEL org.opencontainers.image.source="https://github.com/mehaksandhudev/yt-download-service"
LABEL org.opencontainers.image.description="YouTube video downloader microservice with S3/MinIO upload"
LABEL org.opencontainers.image.licenses="MIT"

# Install system dependencies (ffmpeg for yt-dlp merging & audio conversion)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app.py .
COPY start.sh .
RUN chmod +x start.sh

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5002

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:5002/health || exit 1

CMD ["./start.sh"]
