# 🎬 YouTube Media Ingestion Service

[![Docker Hub](https://img.shields.io/docker/pulls/mehakxsandhu/youtube-download-api?style=flat-square&logo=docker)](https://hub.docker.com/r/mehakxsandhu/youtube-download-api)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/mehaksandhudev/youtube-download-api/docker-publish.yml?style=flat-square&logo=github)](https://github.com/mehaksandhudev/youtube-download-api/actions)

A scalable, containerized REST API that enhances the capabilities of `yt-dlp` by providing a dynamic interface to download YouTube media and securely stream the output directly to MinIO/AWS S3. It ensures you always have the latest features and bug fixes by **automatically updating `yt-dlp` on every container start**, offering a truly robust backend for your data pipelines.

## 📖 Table of Contents
- [✨ Features](#-features)
- [🚀 Quick Start](#-quick-start)
- [📡 API Reference](#-api-reference)
  - [`POST /download`](#post-download)
  - [`GET /info?url=...`](#get-infourl)
  - [`GET /health`](#get-health)
  - [`GET /version`](#get-version)
- [⚙️ Environment Variables](#️-environment-variables)
- [🔗 n8n Integration](#-n8n-integration)
- [🐳 Docker Hub](#-docker-hub)
- [🛠️ Development](#️-development)
- [📄 License](#-license)

## ✨ Features

- **Download & Upload** — Downloads YouTube videos and uploads directly to MinIO/S3
- **Quality Selection** — Choose from `best`, `1080p`, `720p`, `480p`, `360p`
- **Audio-Only Mode** — Extract audio as MP3 (`audio_only`)
- **Custom Bucket** — Override the default S3 bucket per request
- **Path Prefix** — Organize uploads into S3 folders
- **Video Metadata** — Fetch video info without downloading (`/info`)
- **YouTube URL Validation** — Rejects non-YouTube URLs for security
- **CORS Enabled** — Works with frontend apps and n8n
- **Health Checks** — Built-in Docker `HEALTHCHECK` + `/health` endpoint
- **Non-Root Container** — Runs as unprivileged user for security
- **Auto-Updates yt-dlp** — Updates yt-dlp on every container start

---

## 🚀 Quick Start

### Option 1: Docker Run (Fastest)

```bash
docker run -d \
  --name youtube-download-api \
  -p 5002:5002 \
  -e S3_ENDPOINT_URL=http://host.docker.internal:9000 \
  -e S3_ACCESS_KEY=your-access-key \
  -e S3_SECRET_KEY=your-secret-key \
  -e S3_BUCKET_NAME=your-bucket-name \
  mehakxsandhu/youtube-download-api:latest
```

### Option 2: Docker Compose

1. Clone the repo:
   ```bash
   git clone https://github.com/mehaksandhudev/youtube-download-api.git
   cd youtube-download-api
   ```

2. Create your `.env` file:
   ```bash
   cp .env.example .env
   # Edit .env with your MinIO/S3 credentials
   ```

3. Start the service:
   ```bash
   docker-compose up -d --build
   ```

4. Verify it's running:
   ```bash
   curl http://localhost:5002/health
   ```

---

## 📡 API Reference

### `POST /download`

Download a YouTube video and upload to S3/MinIO.

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `url` | string | ✅ | — | YouTube video URL |
| `quality` | string | ❌ | `best` | `best`, `1080p`, `720p`, `480p`, `360p`, `audio_only` |
| `bucket` | string | ❌ | env var | Override S3 bucket name |
| `path_prefix` | string | ❌ | `""` | S3 key prefix (folder path) |

**Example:**
```bash
curl -X POST http://localhost:5002/download \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://youtu.be/V8o6ItwYJkE",
       "quality": "720p",
       "path_prefix": "podcasts/"
     }'
```

**Response:**
```json
[{
  "code": 200,
  "job_id": "uuid-here",
  "message": "success",
  "response": {
    "media": {
      "title": "Video Title",
      "media_url": "http://...:9000/bucket/podcasts/Video%20Title.mp4",
      "duration": 120,
      "resolution": "1280x720",
      "filesize": 12345678,
      "quality": "720p",
      "s3_bucket": "your-bucket",
      "s3_key": "podcasts/Video Title.mp4"
    }
  },
  "run_time": 45.23
}]
```

---

### `GET /info?url=...`

Get video metadata without downloading.

```bash
curl "http://localhost:5002/info?url=https://youtu.be/V8o6ItwYJkE"
```

**Response:**
```json
{
  "code": 200,
  "response": {
    "title": "Video Title",
    "duration": 120,
    "uploader": "Channel Name",
    "view_count": 1000000,
    "thumbnail": "https://...",
    "available_qualities": ["best", "1080p", "720p", "480p", "360p", "audio_only"]
  }
}
```

---

### `GET /health`

Health check endpoint.

```bash
curl http://localhost:5002/health
# {"status": "healthy", "service": "youtube-download-service", "version": "1.0.0"}
```

### `GET /version`

Service and dependency versions.

```bash
curl http://localhost:5002/version
# {"service_version": "1.0.0", "yt_dlp_version": "2024.12.23", "python_version": "Python 3.10.x"}
```

---

## ⚙️ Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `S3_ENDPOINT_URL` | ❌ | `http://host.docker.internal:9000` | MinIO/S3 endpoint |
| `S3_ACCESS_KEY` | ✅ | — | S3 access key |
| `S3_SECRET_KEY` | ✅ | — | S3 secret key |
| `S3_BUCKET_NAME` | ❌ | `yt-downloads` | Default bucket name |
| `GUNICORN_WORKERS` | ❌ | `2` | Number of Gunicorn workers |

---

## 🔗 n8n Integration

When calling from **n8n** running in Docker, use `http://host.docker.internal:5002` as the base URL.

| Setting | Value |
|---------|-------|
| Method | `POST` |
| URL | `http://host.docker.internal:5002/download` |
| Body Content Type | JSON |
| **Timeout** | `600000` (10 min — important for long videos!) |

### Dynamic Body Example

Unlike a basic `yt-dlp` script, this service allows dynamic configuration per request. You can map n8n variables to the payload:

```json
{
  "url": "={{ $('On form submission').first().json['What is the video URL?'] }}",
  "quality": "1080p",
  "bucket": "client-uploads",
  "path_prefix": "={{ $('On form submission').first().json['submittedAt'] }}/"
}
```

**Why this is better for automation:**
- **Dynamic Routing**: Save videos to different S3 buckets/folders based on the submitter (using `bucket` and `path_prefix`).
- **Format Control**: Dynamically request `audio_only` for podcasts or specific resolutions.
- **Always Available**: Returns a direct accessible `media_url` immediately after uploading so the next n8n node can use the file.

---

## 🐳 Docker Hub

```bash
# Pull the latest image
docker pull mehakxsandhu/youtube-download-api:latest

# Or pull a specific version
docker pull mehakxsandhu/youtube-download-api:1.0.0
```

**Supported platforms:** `linux/amd64`, `linux/arm64`

---

## 🛠️ Development

```bash
cd youtube_download_service
pip install -r requirements.txt
python app.py
```

The server starts on `http://localhost:5002`.

---

## 📄 License

[MIT](LICENSE) © [mehaksandhudev](https://github.com/mehaksandhudev)
