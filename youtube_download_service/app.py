import os
import uuid
import time
import tempfile
import logging
from datetime import datetime
from urllib.parse import quote

from flask import Flask, request, jsonify
import yt_dlp
import boto3
from botocore.client import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# S3/MinIO Configuration from environment variables
S3_ENDPOINT_URL = os.environ.get('S3_ENDPOINT_URL', 'http://host.docker.internal:9000')
S3_ACCESS_KEY = os.environ.get('S3_ACCESS_KEY')
S3_SECRET_KEY = os.environ.get('S3_SECRET_KEY')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'nca-toolkit')

# Build number (can be incremented in production)
BUILD_NUMBER = 1


def get_s3_client():
    """Create and return S3 client for MinIO."""
    return boto3.client(
        's3',
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        config=Config(signature_version='s3v4'),
        region_name='us-east-1'  # MinIO doesn't care but boto3 needs it
    )


def sanitize_filename(title):
    """Sanitize title for use as filename."""
    # Remove or replace problematic characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        title = title.replace(char, '')
    return title.strip()


def download_and_upload(url):
    """Download YouTube video and upload to MinIO."""
    start_time = time.time()
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Common options to avoid 403 errors - spoof browser behavior
        common_opts = {
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate',
            },
            'referer': 'https://www.youtube.com/',
            'nocheckcertificate': True,
            'ignoreerrors': False,
            'no_warnings': False,
            'quiet': False,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        }
        
        # yt-dlp options - download best quality with audio merged
        ydl_opts = {
            **common_opts,
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best',
            'outtmpl': os.path.join(temp_dir, '%(title)s.%(ext)s'),
            'merge_output_format': 'mp4',
            'extract_flat': False,
        }
        
        # First, extract info without downloading
        with yt_dlp.YoutubeDL({**common_opts, 'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
        
        # Now download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Find the downloaded file
        downloaded_files = [f for f in os.listdir(temp_dir) if f.endswith('.mp4')]
        if not downloaded_files:
            # Try other extensions
            downloaded_files = os.listdir(temp_dir)
        
        if not downloaded_files:
            raise Exception("No file was downloaded")
        
        local_file = os.path.join(temp_dir, downloaded_files[0])
        file_ext = os.path.splitext(downloaded_files[0])[1]
        
        # Get file size
        file_size = os.path.getsize(local_file)
        
        # Prepare S3 key
        sanitized_title = sanitize_filename(info.get('title', 'video'))
        s3_key = f"{sanitized_title}{file_ext}"
        
        # Upload to MinIO
        s3_client = get_s3_client()
        
        logger.info(f"Uploading {local_file} to s3://{S3_BUCKET_NAME}/{s3_key}")
        s3_client.upload_file(
            local_file, 
            S3_BUCKET_NAME, 
            s3_key,
            ExtraArgs={'ContentType': 'video/mp4'}
        )
        
        # Construct the accessible URL
        encoded_key = quote(s3_key, safe='')
        media_url = f"{S3_ENDPOINT_URL}/{S3_BUCKET_NAME}/{encoded_key}"
        
        end_time = time.time()
        run_time = round(end_time - start_time, 2)
        
        # Extract video metadata
        # Get format info
        formats = info.get('formats', [])
        selected_format = None
        for fmt in formats:
            if fmt.get('ext') == 'mp4' and fmt.get('vcodec') != 'none':
                selected_format = fmt
                break
        
        if not selected_format:
            selected_format = formats[-1] if formats else {}
        
        # Build response matching user's expected format
        response_data = {
            "build_number": BUILD_NUMBER,
            "code": 200,
            "endpoint": "/download",
            "id": datetime.now().isoformat(),
            "job_id": str(uuid.uuid4()),
            "message": "success",
            "pid": os.getpid(),
            "queue_id": id(request),
            "queue_length": 0,
            "queue_time": 0,
            "response": {
                "media": {
                    "audio_codec": info.get('acodec', selected_format.get('acodec', 'unknown')),
                    "description": info.get('description', '')[:500] if info.get('description') else '',
                    "duration": info.get('duration', 0),
                    "ext": file_ext.replace('.', ''),
                    "filesize": file_size,
                    "format_id": info.get('format_id', selected_format.get('format_id', '')),
                    "fps": info.get('fps', selected_format.get('fps', 30)),
                    "height": info.get('height', selected_format.get('height', 0)),
                    "media_url": media_url,
                    "resolution": f"{info.get('width', 0)}x{info.get('height', 0)}",
                    "title": sanitized_title,
                    "upload_date": info.get('upload_date', ''),
                    "uploader": info.get('uploader', ''),
                    "uploader_id": info.get('uploader_id', ''),
                    "video_codec": info.get('vcodec', selected_format.get('vcodec', 'unknown')),
                    "view_count": info.get('view_count', 0),
                    "width": info.get('width', selected_format.get('width', 0))
                }
            },
            "run_time": run_time,
            "total_time": run_time
        }
        
        return response_data
        
    finally:
        # Cleanup temp files
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.error(f"Failed to cleanup temp dir: {e}")


@app.route('/download', methods=['POST'])
def download_video():
    """
    Download YouTube video and upload to MinIO.
    
    Expects JSON body:
    {
        "url": "https://youtu.be/WNSZ6xouNv4"
    }
    """
    try:
        if not request.is_json:
            return jsonify({
                "code": 400,
                "message": "Request must be JSON",
                "error": "Content-Type must be application/json"
            }), 400
        
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({
                "code": 400,
                "message": "Missing required field: url",
                "error": "URL is required"
            }), 400
        
        logger.info(f"Processing download request for: {url}")
        
        result = download_and_upload(url)
        
        return jsonify([result])  # Return as array to match expected format
        
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({
            "code": 500,
            "message": "error",
            "error": str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "service": "youtube-download-service"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
