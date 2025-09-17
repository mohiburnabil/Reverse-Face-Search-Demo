import os
import time
import torch
import logging
from PIL import Image, ImageFilter
from huggingface_hub import hf_hub_download
from ultralytics import YOLO
from typing import List
import Esrgan_function_3 as image_upscaling

# import image_upscaling  # Assuming this exists

# Set up logging
logging.basicConfig(
    filename='face_detection.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def calculate_dynamic_padding(bboxes, image_width, image_height, step_size=0.1, max_padding=30):
    dynamic_padding_values = []

    for i, (x_min, y_min, x_max, y_max) in enumerate(bboxes):
        padding = 0
        while padding <= max_padding:
            overlap_found = False
            padded_bbox = (
                max(0, x_min - padding),
                max(0, y_min - padding),
                min(image_width, x_max + padding),
                min(image_height, y_max + padding)
            )

            for j, other_bbox in enumerate(bboxes):
                if i == j:
                    continue
                ox_min, oy_min, ox_max, oy_max = other_bbox
                if not (padded_bbox[2] < ox_min or padded_bbox[0] > ox_max or padded_bbox[3] < oy_min or padded_bbox[1] > oy_max):
                    overlap_found = True
                    break

            if overlap_found:
                break
            padding += step_size

        padding = padding - step_size if padding >= 10 else 10
        dynamic_padding_values.append(padding)

    return dynamic_padding_values


def filter_faces(face_bboxes, confidence_scores, dynamic_padding, confidence_threshold=0.5):
    good_faces = []
    for bbox, score, padding in zip(face_bboxes, confidence_scores, dynamic_padding):
        if score < confidence_threshold:
            continue

        x_min, y_min, x_max, y_max = bbox
        if x_max - x_min >= 60 and y_max - y_min >= 60:
            good_faces.append((
                int(max(0, x_min - padding)),
                int(max(0, y_min - padding)),
                int(x_max + padding),
                int(y_max + padding)
            ))
        else:
            good_faces.append((int(x_min), int(y_min), int(x_max), int(y_max)))
    return good_faces


def sharpen_image(face_image):
    return face_image.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3))


def face_detection(image: Image.Image, model) -> List[Image.Image]:
    """
    Detects faces using the provided YOLO model instance.
    """
    try:
        results = model(image)[0]
        bboxes = results.boxes.xyxy.cpu()
        scores = results.boxes.conf.cpu()

        logging.info("Inference done. Total predictions: %d", len(bboxes))

        dynamic_paddings = calculate_dynamic_padding(bboxes, image.width, image.height)
        filtered_faces = filter_faces(bboxes, scores, dynamic_paddings)

        face_images = []
        for i, bbox in enumerate(filtered_faces):
            x_min, y_min, x_max, y_max = [int(b.item()) if isinstance(b, torch.Tensor) else int(b) for b in bbox]
            cropped = image.crop((x_min, y_min, x_max, y_max))
            sharpened = sharpen_image(cropped)
            if sharpened.mode == 'RGBA':
                sharpened = sharpened.convert('RGB')
            width, height = sharpened.size  # Get the image dimensions
            if width < 1000 or height < 1000:
                logging.info("Upscaling image due to small dimensions: %dx%d", width, height)
                upscaled_face = image_upscaling.upscale_image(sharpened)
                face_images.append(upscaled_face)
            else:
                face_images.append(sharpened)


        return face_images

    except Exception as e:
        logging.error("Face detection error: %s", str(e), exc_info=True)
        return []
    

    


def convert_to_jpg(input_path: str, output_path: str):
    try:
        with Image.open(input_path) as img:
            if not output_path.lower().endswith(".jpg"):
                output_path += ".jpg"
            img.convert("RGB").save(output_path, "JPEG")
            logging.info("Image converted and saved to %s", output_path)
    except Exception as e:
        logging.error("Failed to convert image to JPG: %s", str(e))
