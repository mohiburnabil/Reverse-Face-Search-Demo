from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
import utils
import traceback
import json
from PIL import Image
import numpy as np
import io
import os
from typing import List
from pydantic import BaseModel
from PIL import Image
import io
import asyncio
import realtimeLinkedinScraper

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

logging.basicConfig(
    filename='face_verification.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="Face Verification API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():

    """Ensure the face model is initialized before handling requests."""
    await utils.init_face_app()


# ---------------------------- Endpoint ----------------------------
@app.post("/face-verification/")
async def face_verification_endpoint(
    face_check_json: UploadFile = File(...),
    query_image: UploadFile = File(...),
    score_threshold: float = Form(80),
    similarity_threshold: float = Form(0.6)
):
    try:
        logging.info(f"Received request: face_check_json={face_check_json.filename}, file={query_image.filename}, "
                     f"score_threshold={score_threshold}, similarity_threshold={similarity_threshold}")
        json_bytes = await face_check_json.read()
        data = json.loads(json_bytes.decode('utf-8'))

        
         # Convert to PIL Image
        try:
            print(f"Opening image: {query_image}")
            image_bytes = await query_image.read()
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            image_np = np.array(image) 

        except Exception as e:
            print(f"Error opening image: {e}")

        result = await utils.Face_verification(
        data,
        image_np,
        score_threshold,
        similarity_threshold
    )

        logging.info(f"Response: {result}")
        return JSONResponse(content=result)

    except Exception as e:
        logging.error("Error during face verification: " + str(e))
        logging.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal Server Error")


class LinkedInRequest(BaseModel):
    linkedin_urls: List[str]


@app.post("/compare-linkedin")
async def compare_linkedin_faces(
    file: UploadFile = File(...),
   linkedin_urls: List[str] = Form(...)
):
    try:
        # Load the query image
        print(f"Opening image: {file.filename}")
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_np = np.array(image) 

        print(f"Fetching profile pictures for URLs: {linkedin_urls} type: {type(linkedin_urls)}")

        extracted_images = realtimeLinkedinScraper.get_profile_pic_link_and_image(linkedin_urls)

        # Compute similarity
        results = await utils.compute_similarity_linkedin(image_np, extracted_images)

        return {"results": results}

    except Exception as e:
        import traceback
        logging.error(f"Error in compare_linkedin_faces: {str(e)}")
        tb = traceback.format_exc()
        logging.info(tb)
        print(tb)
        return JSONResponse(status_code=500, content={"error": str(e)})


# ---------------------------- Run Server ----------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8111, workers=5)
    
