FROM python:3.10-slim-bookworm

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
RUN pip install --no-cache-dir \
    flask \
    gunicorn \
    "mediapipe==0.10.8" \
    opencv-python \
    numpy \
    requests

COPY app.py .

# Expose the port (using 5001 to avoid conflict with alignment service)
EXPOSE 5001

# Run with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--timeout", "60", "app:app"]
