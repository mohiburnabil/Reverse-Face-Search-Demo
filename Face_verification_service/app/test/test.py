import requests

# Replace with your FastAPI server's URL
url = "http://localhost:8000/face-verification/"

# Sample face_check_json and image file
face_check_json = '{"id": "user123", "images": ["image1.jpg", "image2.jpg"]}'
image_path = "sample_query.jpg"  # Replace with your actual test image file

# Form data
payload = {
    'face_check_json': face_check_json,
    'score_threshold': 80,
    'similarity_threshold': 0.6
}

# File to upload
files = {
    'query_image': open(image_path, 'rb')
}

try:
    response = requests.post(url, data=payload, files=files)
    print("Status Code:", response.status_code)
    print("Response:", response.json())
except Exception as e:
    print("Test failed:", str(e))
