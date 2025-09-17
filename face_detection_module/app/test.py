
import requests
import base64
from PIL import Image
from io import BytesIO

def send_image_to_api(image_path: str, api_url="http://localhost:8080/detect-faces/"):
    with open(image_path, "rb") as f:
        files = {"file": (image_path, f, "image/jpeg")}
        response = requests.post(api_url, files=files)

    if response.status_code == 200:
        face_count = response.json().get("face_count", -1)
        faces = response.json().get("faces", [])
        print(f"Detected {face_count} face(s).")

        # # Optionally display or save each face
        # for idx, face_b64 in enumerate(faces):
        #     image_data = base64.b64decode(face_b64)
        #     image = Image.open(BytesIO(image_data))
        #     # image.save(f"face_{idx+1}.jpg")  # Or save it locally
    else:
        print(f"Request failed: {response.status_code} - {response.text}")

# Example usage
send_image_to_api("../IMG_4551.JPG")
