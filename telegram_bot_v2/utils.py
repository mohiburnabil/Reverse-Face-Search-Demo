import os
import helpers
from typing import List
import logging
import base64
import uuid
import requests
from io import BytesIO
from PIL import Image
from dotenv import load_dotenv

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

load_dotenv()
FACE_DETECTION_API = os.getenv("FACE_DETECTION_API")

def face_detection_api(image_file, chat_id) -> list:
    """
    image_file: A file-like object (e.g., open(..., 'rb') or UploadFile.file)
    chat_id: Identifier for saving face images under detected_faces/{chat_id}
    """
    print(f'Inside face_detection_api with chat_id: {chat_id}')
    image_bytes = helpers.pil_to_bytes(image_file)  # Ensure the image is in bytes format
    files = {"file": ("uploaded.jpg", image_bytes, "image/jpeg")}
    response = requests.post(FACE_DETECTION_API, files=files)

    saved_paths = []

    if response.status_code == 200:
        data = response.json()
        face_count = data.get("face_count", -1)
        faces = data.get("faces", [])
        print(f"Detected {face_count} face(s).")

        save_dir = os.path.join("detected_faces", str(chat_id))
        os.makedirs(save_dir, exist_ok=True)

        for face_b64 in faces:
            image_data = base64.b64decode(face_b64)
            image = Image.open(BytesIO(image_data))

            filename = f"{uuid.uuid4().hex}.jpg"
            save_path = os.path.join(save_dir, filename)
            image.save(save_path)
            saved_paths.append(save_path)

        return saved_paths
    else:
        print(f"Request failed: {response.status_code} - {response.text}")
        return []



async def get_best_urls(face_check_results):
    return await helpers.get_best_urls(face_check_results)

async def get_best_urls_summary(best_urls):
    print("Generating summary from best URLs...")
   

    if not best_urls:
        return "Sorry, we could not find any URLs with high confidence."

    link_string = (
        "I guess we found the person. Using the following URLs to generate a summary of the person:\n\n"
    )
    for i, (score, url) in enumerate(best_urls):
        link_string += f"{i+1}. Confidence: {score}. URL: {url}\n"

    link_string += "\nPlease wait while I generate a summary of the person."

    return link_string

   
