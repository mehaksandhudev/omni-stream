# YouTube Download Service - Docker Instructions

This guide provides steps to start the **YouTube Download Service** using Docker.

## Prerequisites

- **Docker** and **Docker Compose** must be installed on your system.
- **MinIO** must be running and accessible at `http://host.docker.internal:9000`

## Docker Compose Configuration

Ensure your `docker-compose.yml` file contains the following configuration:

```yaml
youtube-download-service:
  build: ./youtube_download_service
  container_name: youtube-download-service
  ports:
    - "5002:5002"
  environment:
    - S3_ENDPOINT_URL=http://host.docker.internal:9000
    - S3_ACCESS_KEY=YoSGcgLbihsWi2JrgHOt
    - S3_SECRET_KEY=3GkWozKbNGwZ8BnFdBUXrpIk1WmS381YQzD2DpUK
    - S3_BUCKET_NAME=nca-toolkit
  restart: always
```

## Starting the Service

### 1. Build and Start via Docker Compose

Open your terminal in the root directory (where `docker-compose.yml` is located) and run:

```bash
docker-compose up -d --build youtube-download-service
```

- `-d`: Runs the container in the background (detached mode).
- `--build`: Forces a rebuild of the image (useful if you've made code changes).
- `youtube-download-service`: Specifies that we only want to start this specific service.

If you want to view the logs to ensure everything is running correctly:

```bash
docker-compose logs -f youtube-download-service
```

### 2. Verify the Service is Running

The service is configured to run on port **5002**. You can verify it's active by sending a health check request.

**PowerShell Example:**
```powershell
Invoke-RestMethod -Uri "http://localhost:5002/health" -Method GET
```

## Using the Service

### API Endpoint

| Method | URL | Content-Type |
|--------|-----|--------------|
| POST | `http://localhost:5002/download` | `application/json` |

### Request Body

```json
{
  "url": "https://youtu.be/WNSZ6xouNv4?si=ZEt-IsfGIL7-PUZ3"
}
```

### Example Request

**PowerShell:**
```powershell
$body = @{ url = "https://youtu.be/WNSZ6xouNv4?si=ZEt-IsfGIL7-PUZ3" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:5002/download" -Method POST -ContentType "application/json" -Body $body
```

**Curl:**
```bash
curl -X POST http://localhost:5002/download \
     -H "Content-Type: application/json" \
     -d '{"url": "https://youtu.be/WNSZ6xouNv4?si=ZEt-IsfGIL7-PUZ3"}'
```

### Response Format

```json
[
  {
    "build_number": 1,
    "code": 200,
    "endpoint": "/download",
    "id": "2026-01-24T00:12:00.123+05:30",
    "job_id": "uuid-here",
    "message": "success",
    "response": {
      "media": {
        "audio_codec": "mp4a.40.2",
        "duration": 120,
        "ext": "mp4",
        "filesize": 12345678,
        "fps": 30,
        "height": 1080,
        "media_url": "http://host.docker.internal:9000/nca-toolkit/Video%20Title.mp4",
        "resolution": "1920x1080",
        "title": "Video Title",
        "width": 1920
      }
    },
    "run_time": 45.23,
    "total_time": 45.23
  }
]
```

## n8n Integration

When using this service from n8n's HTTP Request node:

| Setting | Value |
|---------|-------|
| Method | POST |
| URL | `http://host.docker.internal:5002/download` |
| Body Content Type | JSON |
| **Timeout** | `600000` (10 minutes - important for long videos!) |

> **Note:** The service has a 600-second Gunicorn timeout to handle long video downloads without timing out.

## Stopping the Service

To stop the service, run:

```bash
docker-compose stop youtube-download-service
```

To stop and remove the container:

```bash
docker-compose down
```
