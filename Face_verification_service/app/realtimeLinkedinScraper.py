import http.client
import urllib.parse
import json
import requests
from io import BytesIO
from PIL import Image
import os
from dotenv import load_dotenv
load_dotenv()
import numpy as np
import traceback
x_rapidapi_key = os.getenv('x-rapidapi-key')
x_rapidapi_host = os.getenv('x-rapidapi-host')

def get_profile_picture_image(linkedin_url):
    # URL encode the LinkedIn URL
    encoded_url = urllib.parse.quote(linkedin_url)

    conn = http.client.HTTPSConnection("linkedin-api8.p.rapidapi.com")

    headers = {
    'x-rapidapi-key': x_rapidapi_key,
    'x-rapidapi-host': x_rapidapi_host
    }

    try:
        # Make the request with the encoded URL
        conn.request("GET", f"/get-profile-data-by-url?url={encoded_url}", headers=headers)

        # Get the response
        res = conn.getresponse()
        data = res.read()

        profile_data = json.loads(data.decode("utf-8"))
        profile_pic_url = profile_data.get('profilePicture')
        print(f'profile link: {profile_pic_url}')
        if 'profilePicture' in profile_data:
            picture_url = profile_data['profilePicture']
            print('got the profile picture')
            # Download the image
            img_response = requests.get(picture_url)
            img = Image.open(BytesIO(img_response.content))
            
            return img
        else:
            return None  # No profile picture found
    

    except Exception as e:
        tb = traceback.format_exc()
        print(f"An error occurred: {str(e)}\n{tb}")
        return f"Error: {str(e)}"


def save_profile_picture(linkedin_url, save_dir="profile_pictures"):
    # Create a directory if it doesn't exist
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # Fetch the profile picture
    image = get_profile_picture_image(linkedin_url)

    if image:
        # Define the file path and save the image
        filename = linkedin_url.split("/")[-1]  # Use part of the URL as the filename
        file_path = os.path.join(save_dir, f"{filename}.jpg")

        # Save the image
        image.save(file_path)

        print(f"Profile picture saved as {file_path}")
        return file_path  # Return the file path for confirmation
    else:
        print("No profile picture found.")
        return None


from PIL import Image

def get_profile_pic_link_and_image(linkedin_urls):
    """
    Fetches profile pictures from LinkedIn URLs and returns them with the URLs.

    Returns:
        List of tuples (url, image_object), where image_object is a PIL Image or None if not found.
    """
    profile_pic_link_and_image = []
    
    for url in linkedin_urls:
        print(f"Processing LinkedIn profile: {url}")
        saved_path = save_profile_picture(url)

        if saved_path:
            try:

                image = Image.open(saved_path).convert("RGB")
                image_np = np.array(image) 
                print(f"Profile picture loaded from: {saved_path}\n")
                profile_pic_link_and_image.append((url, image_np))
            except Exception as e:
                print(f"Failed to load image from {saved_path}: {e}\n")
                profile_pic_link_and_image.append((url, None))
        else:
            print(f"No profile picture found for {url}\n")
            profile_pic_link_and_image.append((url, None))
    
    return profile_pic_link_and_image



if __name__ == "__main__":
    linkedin_urls = ['https://linkedin.com/in/andreea-caratas-2b17986b', 'https://linkedin.com/in/joanne-baron-42781060', 'https://linkedin.com/in/rina-rhine-594558284', 'https://linkedin.com/in/adam-ades-5387b7a']
    get_profile_pic_link_and_path(linkedin_urls)