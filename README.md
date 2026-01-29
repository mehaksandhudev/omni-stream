# Clippy - Video Automation Services

Self-hosted Docker services for video processing automation, designed to work with **n8n** workflows.

## Services

| Service | Port | Description |
|---------|------|-------------|
| **YouTube Download** | 5002 | Download YouTube videos and upload to MinIO S3 |
| **Face Detection** | 5001 | Detect faces in images/video frames using MediaPipe |

## Quick Start

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/clippy.git
cd clippy

# Start all services
docker-compose up -d --build

# Verify services are running
docker-compose ps
```

## Prerequisites

- **Docker Desktop** 4.0+
- **MinIO** (for S3 storage) - can run in Docker

## Documentation

- [Setup Guide](./SETUP_GUIDE.md) - Complete installation instructions
- [YouTube Download Guide](./YOUTUBE_DOWNLOAD_DOCKER_GUIDE.md) - API usage
- [Face Detection Guide](./FACE_DETECTION_DOCKER_GUIDE.md) - Face detection API

## API Examples

### YouTube Download
```bash
curl -X POST http://localhost:5002/download \
     -H "Content-Type: application/json" \
     -d '{"url": "https://youtu.be/VIDEO_ID"}'
```

### Face Detection
```bash
curl -X POST http://localhost:5001/detect \
     -H "Content-Type: application/json" \
     -d '{"imageUri": "http://host.docker.internal:9000/bucket/image.jpg"}'
```

## n8n Integration

Use `http://host.docker.internal:500X` URLs when calling from n8n running in Docker.

## License

MIT
