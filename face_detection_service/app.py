import cv2
import mediapipe as mp
import numpy as np
import requests
import tempfile
import os
import logging
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize MediaPipe Face Mesh
mp_face_mesh = mp.solutions.face_mesh
# refine_landmarks=True gives us iris landmarks (468-477)
face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=10,
    refine_landmarks=True,
    min_detection_confidence=0.5
)

# Landmark Mapping (approximate indices for Google Vision compatibility)
LANDMARK_MAP = {
    "LEFT_EYE": 468,   # Left Iris Center
    "RIGHT_EYE": 473,  # Right Iris Center
    "LEFT_OF_LEFT_EYEBROW": 63,
    "RIGHT_OF_LEFT_EYEBROW": 105,
    "LEFT_OF_RIGHT_EYEBROW": 336,
    "RIGHT_OF_RIGHT_EYEBROW": 296,
    "MIDPOINT_BETWEEN_EYES": 168,
    "NOSE_TIP": 1,
    "UPPER_LIP": 0,   # Changed from 13 to 0 (Outer Upper Lip) per user snippet
    "LOWER_LIP": 17,  # Changed from 14 to 17 (Outer Lower Lip) per user snippet
    "MOUTH_LEFT": 61,
    "MOUTH_RIGHT": 291
}

def get_landmarks_dict(face_landmarks, width, height):
    """Convert MediaPipe landmarks to Google Vision JSON format."""
    landmarks_list = []
    
    # Standard mapped landmarks
    for name, idx in LANDMARK_MAP.items():
        if idx < len(face_landmarks.landmark):
            lm = face_landmarks.landmark[idx]
            landmarks_list.append({
                "type": name,
                "position": {
                    "x": lm.x * width,
                    "y": lm.y * height,
                    "z": lm.z * width 
                }
            })
            
    # Calculated MOUTH_CENTER (midpoint of upper and lower lip)
    try:
        # User snippet: Upper lip (0), Lower lip (17)
        upper = face_landmarks.landmark[0]
        lower = face_landmarks.landmark[17]
        landmarks_list.append({
            "type": "MOUTH_CENTER",
            "position": {
                "x": ((upper.x + lower.x) / 2) * width,
                "y": ((upper.y + lower.y) / 2) * height,
                "z": ((upper.z + lower.z) / 2) * width
            }
        })
    except IndexError:
        pass
            
    return landmarks_list

def get_bounding_box(face_landmarks, width, height):
    """Calculate bounding box from mesh points."""
    x_coords = [lm.x for lm in face_landmarks.landmark]
    y_coords = [lm.y for lm in face_landmarks.landmark]
    
    xmin = min(x_coords)
    ymin = min(y_coords)
    xmax = max(x_coords)
    ymax = max(y_coords)
    
    return {
        "xmin": xmin * width,
        "ymin": ymin * height,
        "xmax": xmax * width,
        "ymax": ymax * height,
        "width": (xmax - xmin) * width,
        "height": (ymax - ymin) * height
    }

def process_image(image):
    """Process a single image frame and return faces if found."""
    height, width, _ = image.shape
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(image_rgb)
    
    faces = []
    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            faces.append({
                "bbox": get_bounding_box(face_landmarks, width, height),
                "landmarks": get_landmarks_dict(face_landmarks, width, height),
                # FaceMesh doesn't strictly give a 'score' like FaceDetection, 
                # but we assume detection is confident if returned.
                "score": 0.95 
            })
    return faces

@app.route('/detect', methods=['POST'])
def detect_face():
    files_to_cleanup = []
    
    try:
        source_path = None
        is_video = False
        
        # 1. HANDLE INPUT SOURCE
        # Case A: JSON body with imageUri (Google Vision style)
        if request.is_json:
            try:
                data = request.get_json()
                if 'requests' in data and len(data['requests']) > 0:
                    req_item = data['requests'][0]
                    if 'image' in req_item and 'source' in req_item['image'] and 'imageUri' in req_item['image']['source']:
                        image_uri = req_item['image']['source']['imageUri']
                        
                        # Download to temp file
                        logger.info(f"Downloading from {image_uri}")
                        suffix = '.tmp'
                        # Generic try to preserve extension if possible for cv2 hints
                        if '.mp4' in image_uri.lower(): suffix = '.mp4'
                        if '.jpg' in image_uri.lower(): suffix = '.jpg'
                        
                        tf = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
                        files_to_cleanup.append(tf.name)
                        
                        with requests.get(image_uri, stream=True, headers={'User-Agent': 'Mozilla/5.0'}) as r:
                            r.raise_for_status()
                            for chunk in r.iter_content(chunk_size=8192):
                                tf.write(chunk)
                        tf.close()
                        source_path = tf.name
            except Exception as e:
                return jsonify({"error": f"JSON processing error: {str(e)}"}), 400

        # Case B: Direct file upload
        elif 'image' in request.files:
            file = request.files['image']
            tf = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') # Assume image/video
            files_to_cleanup.append(tf.name)
            file.save(tf.name)
            tf.close()
            source_path = tf.name
            
        if not source_path:
             return jsonify({"error": "No valid input provided"}), 400

        # 2. SMART SCANNING STRATEGY
        # Strategy: 
        # - Try scanning as video at checkpoints [0, 0.5, 1.0, 1.5, 2.0] seconds.
        # - If any checkpoint yields faces, return them immediately.
        
        checkpoints = [0, 0.5, 1.0, 1.5, 2.0, 3.0]
        detected_faces = []
        image_dim = {"width": 0, "height": 0}
        
        cap = cv2.VideoCapture(source_path)
        
        if not cap.isOpened():
            # Might be atomic image file that cv2.VideoCapture can't handle? 
            # Fallback to simple imread
            img = cv2.imread(source_path)
            if img is not None:
                image_dim = {"width": img.shape[1], "height": img.shape[0]}
                detected_faces = process_image(img)
            else:
                return jsonify({"error": "Could not open file as image or video"}), 400
        else:
            # It is a video (or image readable by VideoCapture)
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0: fps = 25 # Fallback
            
            for time_pos in checkpoints:
                # Seek
                frame_idx = int(time_pos * fps)
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                
                ret, frame = cap.read()
                if not ret:
                    break # End of stream
                
                image_dim = {"width": frame.shape[1], "height": frame.shape[0]}
                
                faces = process_image(frame)
                if faces:
                    detected_faces = faces
                    logger.info(f"Faces found at {time_pos}s")
                    break # FOUND!
            
            cap.release()

        # 3. RESPONSE
        if not detected_faces:
            return jsonify({
                "faces": [], 
                "message": "No faces detected after scanning video/image",
                "image_dim": image_dim
            })
        
        return jsonify({
            "faces": detected_faces, 
            "primary_face": detected_faces[0],
            "image_dim": image_dim
        })

    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({"error": str(e)}), 500
        
    finally:
        # Cleanup temp files
        for f in files_to_cleanup:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception as e:
                logger.error(f"Failed to cleanup {f}: {e}")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
