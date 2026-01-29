# Clippy Video Services - Complete Setup Guide

This guide covers everything needed to deploy the **YouTube Download Service** and **Face Detection Service** on a new computer.

## Prerequisites

### Required Software

| Software | Version | Download Link |
|----------|---------|---------------|
| **Docker Desktop** | 4.0+ | [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) |
| **Git** | 2.0+ | [git-scm.com/downloads](https://git-scm.com/downloads) |

### System Requirements
- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: 10GB free space for Docker images + video downloads
- **OS**: Windows 10/11, macOS, or Linux

---

## Quick Start Commands

```bash
# 1. Clone the repository
git clone <your-repo-url> clippy
cd clippy

# 2. Build and start all services
docker-compose up -d --build

# 3. Verify services are running
docker-compose ps
```

---

## MinIO S3 Storage (Required for YouTube Service)

The YouTube download service uploads videos to MinIO. If you don't have MinIO running, add this to your `docker-compose.yml`:

```yaml
  minio:
    image: minio/minio
    container_name: minio
    ports:
      - "9000:9000"
      - "9001:9001"  # Console
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - minio_data:/data
    command: server /data --console-address ":9001"
    restart: always

volumes:
  minio_data:
```

### MinIO Setup Steps
1. Start MinIO: `docker-compose up -d minio`
2. Open console: http://localhost:9001
3. Login: `minioadmin` / `minioadmin`
4. Create bucket: `nca-toolkit`
5. Generate Access Keys (Access Keys → Create)
6. Update `docker-compose.yml` with your new keys

---

## Environment Variables

Update these in `docker-compose.yml` for the youtube-download-service:

| Variable | Description | Example |
|----------|-------------|---------|
| `S3_ENDPOINT_URL` | MinIO server URL | `http://host.docker.internal:9000` |
| `S3_ACCESS_KEY` | MinIO access key | `YoSGcgLbihsWi2JrgHOt` |
| `S3_SECRET_KEY` | MinIO secret key | `3GkWozKbN...` |
| `S3_BUCKET_NAME` | Target bucket | `nca-toolkit` |

---

## Service Ports

| Service | Port | Health Check |
|---------|------|--------------|
| Face Detection | 5001 | `http://localhost:5001/health` |
| YouTube Download | 5002 | `http://localhost:5002/health` |

---

## Common Commands

```bash
# Build and start all services
docker-compose up -d --build

# Start a specific service
docker-compose up -d --build youtube-download-service

# View logs
docker-compose logs -f youtube-download-service

# Restart a service
docker-compose restart youtube-download-service

# Stop all services
docker-compose down

# Check running containers
docker-compose ps
```

---

## n8n Integration

When calling from n8n's HTTP Request node:

| Setting | Value |
|---------|-------|
| URL | `http://host.docker.internal:5002/download` |
| Method | POST |
| Body Type | JSON |
| **Timeout** | `600000` (10 minutes) |

### Example Request Body
```json
{
  "url": "https://youtu.be/WNSZ6xouNv4"
}
```

---

## Troubleshooting

### YouTube 403 Forbidden Error
The service auto-updates yt-dlp at startup. If you still get 403 errors:
```bash
# Rebuild and restart
docker-compose up -d --build youtube-download-service
```

### Container Won't Start
```bash
# Check logs for errors
docker logs youtube-download-service
```

### Port Already in Use
```bash
# Find what's using the port
netstat -ano | findstr :5002

# Kill the process or change the port in docker-compose.yml
```
