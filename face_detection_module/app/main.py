import uvicorn
from fastapi import FastAPI, UploadFile, File
from PIL import Image
import io
import torch
import logging
from ultralytics import YOLO
from huggingface_hub import hf_hub_download
import utils

app = FastAPI()

@app.on_event("startup")
async def load_model():
    model_path = hf_hub_download(repo_id="arnabdhar/YOLOv8-Face-Detection",filename="model.pt")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    app.state.model = YOLO(model_path).to(device)
    logging.info("YOLO model loaded on %s", device)

@app.post("/detect-faces/")
async def detect_faces(file: UploadFile = File(...)):
    image_data = await file.read()
    image = Image.open(io.BytesIO(image_data)).convert("RGB")
    faces_base64 = utils.get_detected_faces(image, model=app.state.model)
    return {"face_count":len(faces_base64),"faces": faces_base64}



if __name__ == "__main__":
    uvicorn.run('main:app', host="0.0.0.0", port=8080,workers=4)