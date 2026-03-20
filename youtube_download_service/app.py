import os
import re
import uuid
import time
import shutil
import tempfile
import logging
import subprocess
from datetime import datetime, timezone
from urllib.parse import quote, urlparse

from flask import Flask, request, jsonify
from flask_cors import CORS
import yt_dlp
import boto3
from botocore.client import Config

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SERVICE_VERSION = "1.0.0"

S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "http://host.docker.internal:9000")
S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY")
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "yt-downloads")

MAX_CONTENT_LENGTH = 1 * 1024 * 1024  # 1 MB request body limit

ALLOWED_YOUTUBE_PATTERNS = [
    r"(https?://)?(www\.)?youtube\.com/watch\?v=[\w-]+",
    r"(https?://)?(www\.)?youtube\.com/shorts/[\w-]+",
    r"(https?://)?youtu\.be/[\w-]+",
    r"(https?://)?(www\.)?youtube\.com/playlist\?list=[\w-]+",
    r"(https?://)?(www\.)?youtube\.com/live/[\w-]+",
    r"(https?://)?music\.youtube\.com/watch\?v=[\w-]+",
]

QUALITY_FORMATS = {
    "best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best",
    "1080p": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360p": "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=360]+bestaudio/best[height<=360]",
    "audio_only": "bestaudio[ext=m4a]/bestaudio/best",
}

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("yt-download-service")

# ---------------------------------------------------------------------------
# Flask App
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
CORS(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def validate_youtube_url(url: str) -> bool:
    """Return True only if *url* looks like a valid YouTube URL."""
    return any(re.match(p, url) for p in ALLOWED_YOUTUBE_PATTERNS)


def get_s3_client():
    """Create and return an S3-compatible client (works with MinIO & AWS)."""
    return boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )


def sanitize_filename(title: str) -> str:
    """Strip characters that are invalid in filenames."""
    for ch in '<>:"/\\|?*':
        title = title.replace(ch, "")
    return title.strip()


def _common_ydl_opts() -> dict:
    """Options shared across all yt-dlp calls (anti-bot headers etc.)."""
    return {
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-us,en;q=0.5",
            "Sec-Fetch-Mode": "navigate",
        },
        "referer": "https://www.youtube.com/",
        "nocheckcertificate": True,
        "ignoreerrors": False,
        "no_warnings": False,
        "quiet": False,
        "extractor_args": {"youtube": {"player_client": ["android", "web"]}},
    }


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------
def download_and_upload(url: str, quality: str = "best",
                        bucket: str | None = None,
                        path_prefix: str = "") -> dict:
    """Download a YouTube video, upload to S3/MinIO, and return metadata."""
    start_time = time.time()
    temp_dir = tempfile.mkdtemp()
    target_bucket = bucket or S3_BUCKET_NAME
    is_audio = quality == "audio_only"

    try:
        fmt = QUALITY_FORMATS.get(quality, QUALITY_FORMATS["best"])
        common = _common_ydl_opts()

        ydl_opts = {
            **common,
            "format": fmt,
            "outtmpl": os.path.join(temp_dir, "%(title)s.%(ext)s"),
            "extract_flat": False,
        }
        if is_audio:
            ydl_opts["postprocessors"] = [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }]
        else:
            ydl_opts["merge_output_format"] = "mp4"

        # 1) Extract metadata
        with yt_dlp.YoutubeDL({**common, "quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)

        # 2) Download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # 3) Find downloaded file
        target_ext = ".mp3" if is_audio else ".mp4"
        downloaded = [f for f in os.listdir(temp_dir) if f.endswith(target_ext)]
        if not downloaded:
            downloaded = os.listdir(temp_dir)
        if not downloaded:
            raise FileNotFoundError("No file was downloaded")

        local_file = os.path.join(temp_dir, downloaded[0])
        file_ext = os.path.splitext(downloaded[0])[1]
        file_size = os.path.getsize(local_file)

        # 4) Upload to S3/MinIO
        sanitized = sanitize_filename(info.get("title", "video"))
        s3_key = f"{path_prefix}{sanitized}{file_ext}" if not path_prefix else f"{path_prefix.strip('/')}/{sanitized}{file_ext}"
        if not path_prefix:
            s3_key = f"{sanitized}{file_ext}"

        content_type = "audio/mpeg" if is_audio else "video/mp4"
        s3 = get_s3_client()
        logger.info("Uploading %s → s3://%s/%s", local_file, target_bucket, s3_key)
        s3.upload_file(local_file, target_bucket, s3_key,
                       ExtraArgs={"ContentType": content_type})

        media_url = f"{S3_ENDPOINT_URL}/{target_bucket}/{quote(s3_key, safe='/')}"

        run_time = round(time.time() - start_time, 2)

        # 5) Pick best format metadata
        formats = info.get("formats", [])
        sel = next((f for f in formats if f.get("ext") == "mp4" and f.get("vcodec") != "none"), None)
        if sel is None:
            sel = formats[-1] if formats else {}

        return {
            "code": 200,
            "endpoint": "/download",
            "id": datetime.now(timezone.utc).isoformat(),
            "job_id": str(uuid.uuid4()),
            "message": "success",
            "response": {
                "media": {
                    "audio_codec": info.get("acodec", sel.get("acodec", "unknown")),
                    "description": (info.get("description") or "")[:500],
                    "duration": info.get("duration", 0),
                    "ext": file_ext.lstrip("."),
                    "filesize": file_size,
                    "fps": info.get("fps", sel.get("fps", 0)),
                    "height": info.get("height", sel.get("height", 0)),
                    "media_url": media_url,
                    "quality": quality,
                    "resolution": f"{info.get('width', 0)}x{info.get('height', 0)}",
                    "s3_bucket": target_bucket,
                    "s3_key": s3_key,
                    "title": sanitized,
                    "upload_date": info.get("upload_date", ""),
                    "uploader": info.get("uploader", ""),
                    "video_codec": info.get("vcodec", sel.get("vcodec", "unknown")),
                    "view_count": info.get("view_count", 0),
                    "width": info.get("width", sel.get("width", 0)),
                }
            },
            "run_time": run_time,
            "version": SERVICE_VERSION,
        }
    finally:
        try:
            shutil.rmtree(temp_dir)
        except Exception as exc:
            logger.error("Failed to cleanup temp dir: %s", exc)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/download", methods=["POST"])
def download_video():
    """
    Download a YouTube video and upload to MinIO/S3.

    JSON body:
        url          (required)  YouTube video URL
        quality      (optional)  best | 1080p | 720p | 480p | 360p | audio_only
        bucket       (optional)  Override default S3 bucket
        path_prefix  (optional)  S3 key prefix / folder path
    """
    try:
        if not request.is_json:
            return jsonify({"code": 400, "message": "Content-Type must be application/json"}), 400

        data = request.get_json()
        url = data.get("url")
        quality = data.get("quality", "best")
        bucket = data.get("bucket")
        path_prefix = data.get("path_prefix", "")

        if not url:
            return jsonify({"code": 400, "message": "Missing required field: url"}), 400

        if not validate_youtube_url(url):
            return jsonify({
                "code": 400,
                "message": "Invalid YouTube URL",
                "error": "Only youtube.com, youtu.be, and music.youtube.com URLs are accepted",
            }), 400

        if quality not in QUALITY_FORMATS:
            return jsonify({
                "code": 400,
                "message": f"Invalid quality. Choose from: {', '.join(QUALITY_FORMATS.keys())}",
            }), 400

        logger.info("Download request — url=%s quality=%s bucket=%s", url, quality, bucket or S3_BUCKET_NAME)
        result = download_and_upload(url, quality=quality, bucket=bucket, path_prefix=path_prefix)
        return jsonify([result])

    except Exception as exc:
        logger.exception("Error processing download request")
        return jsonify({"code": 500, "message": "error", "error": str(exc)}), 500


@app.route("/info", methods=["GET"])
def video_info():
    """
    Return video metadata without downloading.

    Query params:
        url  (required)  YouTube video URL
    """
    url = request.args.get("url")
    if not url:
        return jsonify({"code": 400, "message": "Missing required query parameter: url"}), 400

    if not validate_youtube_url(url):
        return jsonify({"code": 400, "message": "Invalid YouTube URL"}), 400

    try:
        with yt_dlp.YoutubeDL({**_common_ydl_opts(), "quiet": True}) as ydl:
            info = ydl.extract_info(url, download=False)

        return jsonify({
            "code": 200,
            "message": "success",
            "response": {
                "title": info.get("title"),
                "description": (info.get("description") or "")[:1000],
                "duration": info.get("duration", 0),
                "uploader": info.get("uploader", ""),
                "upload_date": info.get("upload_date", ""),
                "view_count": info.get("view_count", 0),
                "like_count": info.get("like_count", 0),
                "thumbnail": info.get("thumbnail", ""),
                "width": info.get("width", 0),
                "height": info.get("height", 0),
                "fps": info.get("fps", 0),
                "available_qualities": list(QUALITY_FORMATS.keys()),
            },
        })
    except Exception as exc:
        logger.exception("Error fetching video info")
        return jsonify({"code": 500, "message": "error", "error": str(exc)}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "youtube-download-service",
        "version": SERVICE_VERSION,
    })


@app.route("/version", methods=["GET"])
def version():
    """Return service and dependency versions."""
    try:
        ytdlp_ver = subprocess.check_output(["yt-dlp", "--version"], text=True).strip()
    except Exception:
        ytdlp_ver = "unknown"

    return jsonify({
        "service_version": SERVICE_VERSION,
        "yt_dlp_version": ytdlp_ver,
        "python_version": os.popen("python --version").read().strip(),
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5002)
