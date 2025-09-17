import os
import json
import cv2
import base64
from io import BytesIO
from PIL import Image
from sklearn.metrics.pairwise import cosine_similarity
from insightface.app import FaceAnalysis
import uuid
import asyncio
base_dir = os.getcwd()
face_app = None  


async def init_face_app():
    
    """Initialize FaceAnalysis once and prevent multiple initializations."""
    global face_app
    if face_app is None:  # Prevent re-initialization CPUExecutionProvider CUDAExecutionProvider
        temp_app = FaceAnalysis(name="buffalo_l", providers=["CUDAExecutionProvider"])
        await asyncio.to_thread(temp_app.prepare, ctx_id=0, det_size=(320, 320))
        face_app = temp_app  # Assign after initialization to prevent multiple creations

 
async def load_facecheck_json(json_path):
    """Loads the FaceCheck ID response JSON file."""
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

async def load_and_convert_image(image_path):

    img = cv2.imread(image_path)
    if img is None:
        print(f"Error loading image: {image_path}")
        return None
    
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

async def filter_json_by_score(json_data, threshold=80):
    """Filters JSON data and keeps only entries with a score >= threshold, stopping after 8 entries."""
    filtered_entries = []
    for entry in json_data["face_check_response"]:
        if entry["score"] >= threshold:
            filtered_entries.append(entry)
        if len(filtered_entries) >= 8:
            break
    
    filtered_data = {
        "face_check_response": filtered_entries
    }
    return filtered_data

async def save_filtered_json(json_data, original_json_path):
    """Saves the filtered JSON data to a new file."""
    base_name = os.path.splitext(os.path.basename(original_json_path))[0]
    filtered_json_path = f"{base_name}_filtered.json"
    
    with open(filtered_json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4)

    return filtered_json_path

async def extract_and_save_images(json_data, output_dir):
    """Extracts images from Base64 & URLs in JSON and saves them to a directory."""
    os.makedirs(output_dir, exist_ok=True)
    image_mapping = {}

    for i, entry in enumerate(json_data["face_check_response"]):
        url = entry.get("url", None)
        score = entry.get("score", 0)  # Get the score from JSON

        # Extract images from Base64
        if "base64" in entry:
         
            try:
                b64_data = entry["base64"].split(",")[-1]
                image_data = base64.b64decode(b64_data)
                img = Image.open(BytesIO(image_data))

                image_filename = f"image_{i+1}.jpg"
                image_path = os.path.join(output_dir, image_filename)
                img.save(image_path)

                if url not in image_mapping:
                    image_mapping[url] = []
                image_mapping[url].append({"image": image_path, "score": score})
            except Exception as e:
                print(f"Failed to decode Base64 image: {e}")

    
    return image_mapping

async def get_embedding(img_rgb):
    print(f'image rgb type: {type(img_rgb)}')
    """Extracts face embedding directly using ArcFace (without face detection)."""

    if face_app is None:
        raise RuntimeError("FaceAnalysis model is not initialized. Call init_face_app() first.")
    faces = await asyncio.to_thread(face_app.get, img_rgb)
    
    if len(faces) == 0:
        print(f"No face detected by ArcFace")
        return None

    return faces[0].embedding



async def compute_similarity(query_image, extracted_images):
    """Computes cosine similarity scores between query image and extracted images."""
    query_embedding = await get_embedding(query_image)
    if query_embedding is None:
        raise ValueError("No face found in the query image.")

    results = {}

    # Function to process each image and compute similarity
    async def process_image(img_data):
        face_check_img = await load_and_convert_image(img_data["image"])
        embedding = await get_embedding(face_check_img)
        if embedding is None:
            return None  

        similarity = cosine_similarity([query_embedding], [embedding])[0][0]
        img_data["similarity_score"] = float(similarity)
        return img_data

    for url, images in extracted_images.items():
        # Run all image processing tasks concurrently using asyncio.gather
        tasks = [process_image(img_data) for img_data in images]
        processed_images = await asyncio.gather(*tasks)

        # Filter out None results (where embedding was None)
        results[url] = [img_data for img_data in processed_images if img_data is not None]

    return results


    
async def compute_similarity_linkedin(query_image, extracted_images):
    """
    Computes cosine similarity scores between query image and extracted images.

    Args:
        query_image: The image object for the query.
        extracted_images: A list of tuples (url, image_object), where image_object is already loaded.

    Returns:
        A list of tuples (similarity_score, url) for each successfully processed image.
    """
    query_embedding = await get_embedding(query_image)
    if query_embedding is None:
        raise ValueError("No face found in the query image.")

    async def process_image(url, image):
        if image is None:
            return None  # Skip entries with no image object

        embedding = await get_embedding(image)
        if embedding is None:
            return None  # Skip images with no detected face

        similarity = cosine_similarity([query_embedding], [embedding])[0][0]
        return (float(similarity), url)

    tasks = [process_image(url, image) for url, image in extracted_images]
    processed_results = await asyncio.gather(*tasks)

    # Filter out None results
    results = [res for res in processed_results if res is not None]

    return results


async def filter_results_by_threshold(results, threshold):
    """Filters results and returns a list of tuples (Score, URL, Similarity Score)."""
    filtered_tuples = []
    for url, images in results.items():
        for img_data in images:
            if img_data["similarity_score"] >= threshold:
                filtered_tuples.append((img_data["score"], url, img_data["similarity_score"]))

    return filtered_tuples

async def Face_verification(json_data, query_image, score_threshold=80, similarity_threshold=0.6):

    """Full pipeline to process FaceCheck ID response and return filtered tuples."""
    

    filtered_json_data =await filter_json_by_score(json_data, score_threshold)

    
    os.makedirs('face_check_images', exist_ok=True)

    query_image_name = uuid.uuid4().hex  
    extracted_images_dir = os.path.join(base_dir, f"face_check_images/extracted_images_{query_image_name}_test")  
    
    extracted_images =await extract_and_save_images(filtered_json_data, extracted_images_dir)

    similarity_results =await compute_similarity(query_image, extracted_images)
    filtered_tuples =await filter_results_by_threshold(similarity_results, similarity_threshold)

    return filtered_tuples

  

