import uvicorn
from fastapi import FastAPI, File, UploadFile,Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import utils
import logging
import aiohttp
# import similarity_score_tuple_dynamicPath_without_face_detection_12 as faceverify_filter
import numpy as np
import io
from PIL import Image
import json
import aiofiles
import aiohttp
import uuid
import torch
import time
import requests
import json
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

logging.basicConfig(
filename='facecheck.log',
level=logging.INFO,
format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# @app.on_event("startup")
# async def startup_event():

#     """Ensure the face model is initialized before handling requests."""
#     await faceverify_filter.init_face_app()


@app.get("/process-image-telegram/")
async def process_image(request: Request):
    start_time = time.time()
    try:
        data = await request.json()
        response_text = data.get("response")
        image_path = data.get("image_path")
        bot_version = data.get("bot_version")
    except Exception as e:
        logging.error(f"Error parsing request data: {str(e)}")
        return JSONResponse(content={"result": f"Error parsing request data: {str(e)}"})
    
    logging.info("Starting image processing for FaceCheck")
    face_verification_threshold=0.45
    try:
        
        if "error" in response_text:
            error_message = response_text["error"]
            logging.error(f"FaceCheck failed: {error_message}")
            return JSONResponse(content={"result": error_message})

        response = response_text.get("face_check_response", {})

        # Process best URLs
        try:
           
            image_rgb = await utils.load_and_convert_image(image_path)
            try:
              
                face_verify_url = "http://localhost:8111/face-verification/"
                payload = {
                    # 'face_check_json': response_text_str,
                    'score_threshold': 80,
                    'similarity_threshold': face_verification_threshold
                }
              
                files = {
                     'face_check_json': ('data.json', json.dumps(response_text), 'application/json'),
                     'query_image': open(image_path, 'rb')
                }

                try:
                    face_verify_response = requests.post(face_verify_url, data=payload, files=files)
                    print("Status Code:", face_verify_response.status_code)
                    print("Response:", face_verify_response.json())
                    returned_list = face_verify_response.json()
                except Exception as e:
                    print("Test failed:", str(e))




                logging.info(f"face verify filter returned list: {returned_list}")
            
                face_check_urls = [(x[0], x[1]) for x in returned_list]
                end_time = time.time()
                logging.info(f"Face verification took {end_time - start_time} seconds")
            except Exception as e:
                end_time = time.time()
                logging.exception(f"Error in face verify filter pipeline: {str(e)}")  # Logs the full stack trace
            # face_check_urls = []
            if not face_check_urls:
                logging.info('face verification did not returned anything....')
                face_check_urls = await utils.get_best_urls(response)

            # best_urls = await utils.urls_filer(face_check_urls)
            best_urls = face_check_urls
            linked_in_api_start = time.time()
            linked_in_summary = None
            # linked_in_summary = await utils.get_linked_in_summary(image_rgb,face_check_urls,face_verification_threshold)
            linked_in_summary = await utils.get_linked_in_summary(open(image_path, 'rb'),face_check_urls,face_verification_threshold)

            linked_in_api_end = time.time()
            logging.info(f"Linkedin API took {linked_in_api_end - linked_in_api_start} seconds")
            
            logging.info(f"FaceCheck URLs: {face_check_urls}")
            logging.info(f"Best URLs: {best_urls}")

        except Exception as e:
            logging.exception("Error processing URLs")  # Logs the full stack trace
            return JSONResponse(content={"result": f"Error processing URLs: {str(e)}"})

        # Generate summary
        try:
            if bot_version == 'v2.0':
                logging.info("Using new scraping and summarization method")
                summary = await utils.generate_gpt_scrapping_summary(best_urls) if not linked_in_summary else "" # new scraping and summarization
            else:
                logging.info("Using old scraping and summarization method")
                summary = await utils.generate_summary(best_urls) if not linked_in_summary else "" # old scraping and summarization
            
            logging.info(f"Generated Summary: {summary}")

            # Limit to top 5 URLs
            top_urls = face_check_urls[:5] if len(face_check_urls) > 5 else face_check_urls

            # Add LinkedIn URL if available
            if linked_in_summary:
                linkedin_link = next((link for link in face_check_urls if "linkedin" in link[1].lower()), None)
                if linkedin_link and linkedin_link not in top_urls:
                    top_urls.append(linkedin_link)

            urls_text = "\n\n".join(url[1] for url in top_urls)
            summary = (
                f"LinkedIn Score:{linkedin_link[0]}\n\n{linked_in_summary}\n\nTop {len(top_urls)}/{len(face_check_urls)} links:\n\n{urls_text}"
                if linked_in_summary else f"{summary}\n\nTop {len(top_urls)}/{len(face_check_urls)} links:\n\n{urls_text}"
            )

            logging.info(f"Generated Summary: {summary}")
            return JSONResponse(content={"result": summary})

        except Exception as e:
            logging.exception("Error generating summary")  # Logs full stack trace
            return JSONResponse(content={"result": f"Error generating summary: {str(e)}"})

    except Exception as e:
        logging.exception("Unexpected error in processing")  # Logs full stack trace
        return JSONResponse(content={"result": f"Unexpected error: {str(e)}"})

    finally:
        logging.info("Image processing completed")    
        try:
            directory = os.getcwd() 
            logging.info(f'Cleaning up HTML files in directory: {directory}')
            for f in os.listdir(directory):
                if f.startswith('selected_') and f.endswith('.html'):
                    os.remove(os.path.join(directory, f))
        except Exception as e:
            logging.exception(f'Error while removing HTML files')  # Logs full stack trace






if __name__ == "__main__":
    uvicorn.run('main:app', host="0.0.0.0", port=8000,workers=10)
