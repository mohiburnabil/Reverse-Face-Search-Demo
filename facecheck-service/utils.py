import logging
import asyncio
from helpers import search_by_face

async def get_face_check_results(face_image_path: str, api_key: str):
    # Assume search_by_face is a blocking synchronous function
    loop = asyncio.get_event_loop()
    face_check_api_error, face_check_results = await loop.run_in_executor(None, search_by_face, face_image_path, api_key)

    if face_check_api_error:
        print(f"face check api error: {face_check_api_error} for api key {api_key} face check Response: {face_check_results}")
        
        if 'Your image was not recognized as a valid face.' in face_check_api_error:
            return 'invalid_face'
        return None
    return face_check_results


