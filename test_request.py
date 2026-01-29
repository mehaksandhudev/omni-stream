import requests
import json

url = "http://localhost:5001/detect"
payload = {
  "requests": [
    {
      "image": {
        "source": {
          "imageUri": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/Aurora_as_seen_from_ISS-42.jpg/640px-Aurora_as_seen_from_ISS-42.jpg"
        }
      },
      "features": [
        {
          "type": "FACE_DETECTION",
          "maxResults": 10
        }
      ]
    }
  ]
}

# Start with a reliable static image to test landmarks
payload['requests'][0]['image']['source']['imageUri'] = "https://raw.githubusercontent.com/opencv/opencv/master/samples/data/lena.jpg"


try:
    response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
