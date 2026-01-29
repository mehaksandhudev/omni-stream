# Face Detection Service - Docker Instructions

This guide provides steps to start the **Face Detection Service** using Docker.

## Prerequisites

- **Docker** and **Docker Compose** must be installed on your system.

## Docker Compose Configuration

Ensure your `docker-compose.yml` file contains the following configuration:

```yaml
version: '3.8'

services:
  alignment-service:
    build: ./alignment_service
    container_name: alignment-service
    ports:
      - "5000:5000"
    environment:
      - WHISPER_MODEL=base
    restart: always

  face-detection-service:
    build: ./face_detection_service
    container_name: face-detection-service
    ports:
      - "5001:5001"
    restart: always

# Network configuration
# If you want these to be on the same network as your existing n8n/minio, 
# you might need to use 'external: true' or define standard bridge.
# By default, n8n on host can access these via http://host.docker.internal:5000 and 5001
```

## Starting the Service

The easiest way to start the service is using the existing `docker-compose.yml` file in the root directory.

### 1. Build and Start via Docker Compose

Open your terminal in the root directory (where `docker-compose.yml` is located) and run:

```bash
docker-compose up -d --build face-detection-service
```

- `-d`: Runs the container in the background (detached mode).
- `--build`: Forces a rebuild of the image (useful if you've made code changes).
- `face-detection-service`: Specifies that we only want to start this specific service.

If you want to view the logs to ensure everything is running correctly:

```bash
docker-compose logs -f face-detection-service
```

### 2. Verify the Service is Running

The service is configured to run on port **5001**. You can verify it's active by sending a test request.

**PowerShell Example:**
```powershell
Invoke-RestMethod -Uri "http://localhost:5001/detect" -Method Post -ContentType "application/json" -Body '{"imageUri": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/85/Elon_Musk_Royal_Society_%28crop1%29.jpg/220px-Elon_Musk_Royal_Society_%28crop1%29.jpg"}'
```

**Curl Example:**
```bash
curl -X POST http://localhost:5001/detect \
     -H "Content-Type: application/json" \
     -d '{"imageUri": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/85/Elon_Musk_Royal_Society_%28crop1%29.jpg/220px-Elon_Musk_Royal_Society_%28crop1%29.jpg"}'
```

## Stopping the Service

To stop the service, run:

```bash
docker-compose stop face-detection-service
```

To stop and remove the container:

```bash
docker-compose down
```
