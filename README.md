# OmniStream: Containerized YouTube Media Ingestion Service

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-%E2%98%95-FFDD00?style=flat-square&logo=buymeacoffee&logoColor=black)](https://buymeacoffee.com/mehaksandhudev)


[![Docker Hub](https://img.shields.io/docker/pulls/mehakxsandhu/youtube-download-api?style=flat-square&logo=docker)](https://hub.docker.com/r/mehakxsandhu/youtube-download-api)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![GitHub Actions](https://img.shields.io/github/actions/workflow/status/mehaksandhudev/youtube-download-api/docker-publish.yml?style=flat-square&logo=github)](https://github.com/mehaksandhudev/youtube-download-api/actions)

A scalable, containerized REST API that enhances the capabilities of `yt-dlp` by providing a dynamic interface to download YouTube media and securely stream the output directly to MinIO/AWS S3. It ensures you always have the latest features and bug fixes by **automatically updating `yt-dlp` on every container start**, offering a truly robust backend for your data pipelines.

---

## 📑 Table of Contents
- [✨ Features](#-features)
- [📦 Disk Space](#-disk-space)
- [🚀 Quick Start](#-quick-start)
- [🔌 API Endpoints](#-api-endpoints)
- [📥 Downloading Media](#-downloading-media)
- [ℹ️ Fetching Metadata](#️-fetching-metadata)
- [📊 Sample Response](#-sample-response)
- [🖥️ System Requirements](#️-system-requirements)
- [🔧 Configuration](#-configuration)
- [🚀 Deploy to Production](#-deploy-to-production)
- [🔄 Integration with Other Services](#-integration-with-other-services)
- [🔗 n8n Integration](#-n8n-integration)
- [📁 Project Structure](#-project-structure)
- [🤝 Contributing & Support](#-contributing--support)
- [🛠️ Troubleshooting & FAQ](#️-troubleshooting--faq)
- [📄 License](#-license)

---

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

## 📦 Disk Space
| Component | Size |
|---|---|
| Docker image (total) | **~350 MB** |
| Python 3.10 slim base | ~150 MB |
| ffmpeg + yt-dlp + deps | ~199 MB |
| Application code | < 1 MB |

---

## 🚀 Quick Start

**Option A: Pull from Docker Hub (Recommended)**
```bash
docker pull mehakxsandhu/youtube-download-api:latest
docker run -d \
  --name youtube-download-api \
  -p 5002:5002 \
  -e S3_ENDPOINT_URL=http://host.docker.internal:9000 \
  -e S3_ACCESS_KEY=your-access-key \
  -e S3_SECRET_KEY=your-secret-key \
  -e S3_BUCKET_NAME=your-bucket-name \
  mehakxsandhu/youtube-download-api:latest
```

**Option B: Build from source**
```bash
git clone https://github.com/mehaksandhudev/youtube-download-api.git
cd youtube-download-api
docker-compose up -d --build
```

**Verify the container is running smoothly:**
```bash
curl http://localhost:5002/health
```

---

## 🔌 API Endpoints
| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `GET` | `/version` | Service and dependency versions |
| `GET` | `/info` | Get video metadata without downloading |
| `POST` | `/download` | Download a video and upload to S3/MinIO |

---

## 📥 Downloading Media

Download a YouTube video and push it straight to MinIO/S3 by hitting `POST /download`.

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

---

## ℹ️ Fetching Metadata

Get a video's details without downloading anything.

```bash
curl "http://localhost:5002/info?url=https://youtu.be/V8o6ItwYJkE"
```

---

## 📊 Sample Response

All payload endpoints return a standardized JSON structure. Here is the response for a successful download:

```json
[{
  "code": 200,
  "job_id": "uuid-here",
  "message": "success",
  "response": {
    "media": {
      "title": "Video Title",
      "media_url": "http://...:9000/your-bucket-name/podcasts/Video%20Title.mp4",
      "duration": 120,
      "resolution": "1280x720",
      "filesize": 12345678,
      "quality": "720p",
      "s3_bucket": "your-bucket-name",
      "s3_key": "podcasts/Video Title.mp4"
    }
  },
  "run_time": 45.23
}]
```

---

## 🖥️ System Requirements
- **Docker Desktop** (Windows, macOS, or Linux)
- **CPU**: Any modern x86_64 or ARM64
- **RAM**: 1 GB available 
- **Storage**: Sufficient MinIO/S3 storage for downloaded videos!
- **Network**: Internet access to `youtube.com`

---

## 🔧 Configuration

**Environment Variables:**
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `S3_ENDPOINT_URL` | ❌ | `http://host.docker.internal:9000` | MinIO/S3 endpoint |
| `S3_ACCESS_KEY` | ✅ | — | S3 access key |
| `S3_SECRET_KEY` | ✅ | — | S3 secret key |
| `S3_BUCKET_NAME` | ❌ | `yt-downloads` | Default bucket name |
| `GUNICORN_WORKERS` | ❌ | `2` | Number of Gunicorn workers |

---

## 🚀 Deploy to Production

### Option 1: Docker Hub (CI/CD Automated)
This repository includes a GitHub Actions workflow that automatically builds and securely pushes to Docker Hub on every push to the `main` branch.

**Setup Instructions:**
1. Go to your GitHub repo → Settings → Secrets and variables → Actions
2. Add these repository secrets:
   - `DOCKERHUB_USERNAME` 
   - `DOCKERHUB_TOKEN` ([Create a Personal Access Token here](https://hub.docker.com/settings/security))
3. Push new code to `main` and watch GitHub Actions do the rest!

### Option 2: Manual Terminal Push
```bash
docker build -t mehakxsandhu/youtube-download-api:latest .
docker push mehakxsandhu/youtube-download-api:latest
```

---

## 🔄 Integration with Other Services

Add this snippet to your root `docker-compose.yml` to seamlessly connect the API to your existing stack:

```yaml
services:
  youtube-download-api:
    image: mehakxsandhu/youtube-download-api:latest
    container_name: youtube-download-api
    ports:
      - "5002:5002"
    env_file:
      - .env
    restart: unless-stopped
```
*Note: Make sure your `S3_ENDPOINT_URL` correctly reaches your storage backend. If using a `minio` service on the same docker network, you should set `S3_ENDPOINT_URL=http://minio:9000`.*

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

---

## 📁 Project Structure
```text
youtube-download-api/
├── .github/workflows/         # CI/CD pipelines
│   └── docker-publish.yml
├── youtube_download_service/  # Source code folder
│   ├── app.py                 # Core Flask API (yt-dlp + boto3 integration)
│   ├── Dockerfile             # Python 3.10 slim + ffmpeg
│   ├── requirements.txt       # Pinned production dependencies
│   └── start.sh               # Auto-updates yt-dlp and boots gunicorn
├── docker-compose.yml         # Container orchestration
├── .env.example               # Template for S3 credentials
├── LICENSE                    # MIT License
├── .gitignore
└── .dockerignore
```

---

## 🤝 Contributing & Support

If you encounter a bug, have a feature request, or need help integrating the API:
1. Please check the existing Issues page on GitHub.
2. If your problem isn't listed, open a new issue containing your Docker logs, the API request body, and expected output.
3. Pull requests are always welcome!

**Contact Me:**
- 📧 **Email:** `mehaksandhudev@gmail.com`
- 🌐 **Portfolio:** [www.mehak-sandhu.in](https://www.mehak-sandhu.in)

---

## 🛠️ Troubleshooting & FAQ

**1. "Could not connect to the endpoint URL" / MinIO Connection Refused** 
If the API fails to upload your video with a `500` error, it cannot reach your S3 backend. Make sure your MinIO container is actually running! If you are using Windows Docker Desktop, `host.docker.internal:9000` perfectly maps to your host machine's `localhost`. If you are on Linux, you may need to add `extra_hosts: - "host.docker.internal:host-gateway"` to your `docker-compose.yml` or use the direct IP of your host.

**2. Video Downloads Timeout in n8n**
Heavy videos take time to process and upload. Make sure your HTTP request node in n8n has the **Timeout** setting increased to at least `600000` ms (10 minutes) so it doesn't drop the connection while yt-dlp is working.

**3. Port 5002 is already in use** 
You can map it to any available port by modifying your Docker run command. For example, to run the service on port `8080`: 
```bash
docker run -d -p 8080:5002 mehakxsandhu/youtube-download-api:latest
```

**4. Container Crashes on Massive Videos (4K/8K)**
When downloading huge videos (e.g., 5GB+), the container temporarily stores the video file locally before uploading it to MinIO. If your Docker instance runs out of internal storage space during the download, the container will crash. To prevent this, simply map a high-capacity local directory to the container's temporary folder in your run command:
```bash
docker run -d -p 5002:5002 -v /mnt/my_huge_drive:/tmp mehakxsandhu/youtube-download-api:latest
```

---

## 📄 License
MIT License — see [LICENSE](LICENSE) for details.