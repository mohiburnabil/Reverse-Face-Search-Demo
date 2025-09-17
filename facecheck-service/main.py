import uvicorn
from fastapi import FastAPI,UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import utils
import os
import keyManager
import uuid
import traceback
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SAVE_DIR = "query_face_images"
os.makedirs(SAVE_DIR, exist_ok=True)

api_keys_string = os.getenv("FACECHECK_API_KEY")
api_keys = [key.strip() for key in api_keys_string.split(",")]

key_manager =keyManager.KeyManager(api_keys)


@app.post("/process-face-check/")
async def face_check_route(file: UploadFile = File(...)):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{timestamp}_{unique_id}.jpg"
    image_path = os.path.join(SAVE_DIR, filename)
    with open(image_path, "wb") as buffer:
        buffer.write(await file.read())
    api_key = None
    tried_keys = set()
    try:
        while len(tried_keys) < len(api_keys):
            api_key = await key_manager.get_next_key()
            if api_key in tried_keys:
                continue
            tried_keys.add(api_key)
            print(f"Using API key: {api_key[:5]}...")

            # Await the async function call
            face_check_response = await utils.get_face_check_results(image_path, api_key)
            try:
                if face_check_response.strip() == 'invalid_face':
                    print("Invalid face detected......")
                    await key_manager.release_key(api_key)
                    api_key = None
                    break
            except:
                pass

            if face_check_response:
                print("Face check done.")
                return JSONResponse(content={"face_check_response": face_check_response})
            else:
                print("Face check failed with current key. Trying next key...")
                await key_manager.release_key(api_key)
                api_key = None

        return JSONResponse(content={"error": "All API keys exhausted without success. Please buy credits."})

    except Exception as e:
        print(f"Error in face check: {e}")
        traceback.print_exc()
        return JSONResponse(content={"error": "An unexpected error occurred running the face check service.."})
    finally:
        if api_key:
            await key_manager.release_key(api_key)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8888,workers=10)


