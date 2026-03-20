# YouTube Download Service — Docker Guide

Detailed instructions for running the YouTube Download Service in Docker.

## Prerequisites

- **Docker** and **Docker Compose** installed
- **MinIO** or any S3-compatible storage running and accessible

## Setup

### 1. Environment Configuration

Create a `.env` file in the project root (or copy from `.env.example`):

```env
S3_ENDPOINT_URL=http://host.docker.internal:9000
S3_ACCESS_KEY=your-access-key-here
S3_SECRET_KEY=your-secret-key-here
S3_BUCKET_NAME=your-bucket-name
```

> ⚠️ **Never commit your `.env` file to version control!** It is already in `.gitignore`.

### 2. Docker Compose

```yaml
services:
  youtube-download-service:
    build: ./youtube_download_service
    container_name: youtube-download-service
    ports:
      - "5002:5002"
    env_file:
      - .env
    restart: unless-stopped
```

### 3. Build & Start

```bash
docker-compose up -d --build
```

View logs:
```bash
docker-compose logs -f youtube-download-service
```

### 4. Verify

```bash
curl http://localhost:5002/health
# {"status": "healthy", "service": "youtube-download-service", "version": "1.0.0"}
```

## API Usage

### Download a Video (default best quality)

```bash
curl -X POST http://localhost:5002/download \
     -H "Content-Type: application/json" \
     -d '{"url": "https://youtu.be/VIDEO_ID"}'
```

### Download at 720p

```bash
curl -X POST http://localhost:5002/download \
     -H "Content-Type: application/json" \
     -d '{"url": "https://youtu.be/VIDEO_ID", "quality": "720p"}'
```

### Download Audio Only (MP3)

```bash
curl -X POST http://localhost:5002/download \
     -H "Content-Type: application/json" \
     -d '{"url": "https://youtu.be/VIDEO_ID", "quality": "audio_only"}'
```

### Download to Custom Bucket & Folder

```bash
curl -X POST http://localhost:5002/download \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://youtu.be/VIDEO_ID",
       "bucket": "my-podcasts",
       "path_prefix": "episodes/season1/"
     }'
```

### Get Video Info (No Download)

```bash
curl "http://localhost:5002/info?url=https://youtu.be/VIDEO_ID"
```

### PowerShell Examples

```powershell
# Health check
Invoke-RestMethod -Uri "http://localhost:5002/health" -Method GET

# Download video
$body = @{
    url = "https://youtu.be/VIDEO_ID"
    quality = "720p"
} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:5002/download" -Method POST -ContentType "application/json" -Body $body
```

## n8n Integration

| Setting | Value |
|---------|-------|
| Method | POST |
| URL | `http://host.docker.internal:5002/download` |
| Body Content Type | JSON |
| **Timeout** | `600000` (10 min — important for long videos!) |

## Stopping the Service

```bash
docker-compose stop youtube-download-service   # stop
docker-compose down                             # stop & remove
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `403 Forbidden` from YouTube | Container auto-updates yt-dlp on start; restart to get latest |
| Connection refused to MinIO | Check `S3_ENDPOINT_URL`; use `host.docker.internal` from Docker |
| Timeout error | Increase Gunicorn timeout (default 600s) or check network |
| "Invalid YouTube URL" | Only `youtube.com`, `youtu.be`, `music.youtube.com` URLs accepted |
