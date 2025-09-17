import logging
from typing import List
from PIL import Image
import base64
import io
import helpers

logging.basicConfig(
    filename='face_detection.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_detected_faces(image: Image.Image,model) -> List[str]:
    """
    Detects faces and returns them as base64-encoded strings.
    Args:
        image: Input PIL image.
        model: Preloaded YOLO model instance.
    Returns:
        List of base64-encoded face image strings.
    """
    try:
        logging.info("Detecting faces...")
        faces = helpers.face_detection(image, model)

        base64_faces = []
        for face in faces:
            buffered = io.BytesIO()
            face.save(buffered, format="JPEG")
            encoded_string = base64.b64encode(buffered.getvalue()).decode("utf-8")
            base64_faces.append(encoded_string)

        logging.info("Detected %d faces", len(base64_faces))
        return base64_faces

    except Exception as e:
        logging.error("Face detection failed: %s",str(e), exc_info=True)
        return []
