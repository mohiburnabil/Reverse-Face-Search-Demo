import os
import random
import time
import helpers
import os
from datetime import datetime
import os
import logging
from requests.cookies import RequestsCookieJar
import uuid
import io
from PIL import Image
from linkedin_api import Linkedin
import aiofiles
import aiohttp
import json
import cv2
import json
import ast
import requests

import page_ranking
from fuzzywuzzy import fuzz
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
logging.basicConfig(
    filename="facecheck.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    )


async def get_facecheckResult(file, session: aiohttp.ClientSession):
    print("inside process_face")

    url = "http://127.0.0.1:8888/process-face-check/"
    
    try:
        file_uuid = str(uuid.uuid4())
        image_save_path = "face-images"
        os.makedirs(image_save_path, exist_ok=True)
        image_file_path = os.path.join(image_save_path, f"{file_uuid}.jpg")
        
        async with aiofiles.open(image_file_path, "wb") as img_f:
            await img_f.write(await file.read())
        
        # Prepare form data for the request
        form_data = aiohttp.FormData()
        form_data.add_field("file", open(image_file_path, "rb"), filename=file.filename, content_type=file.content_type)

        async with session.get(url, data=form_data) as response:
            if response.status != 200:
                logging.error(f"Face check service returned status {response.status}")
                return None,{"error": f"Face check service returned status {response.status}"}

            face_check_response = await response.json()
            
            if "error" in face_check_response:
                logging.error("Cannot process the image by face check.")
                return None,{"error": "Cannot process the image by face check."}

            # Save face check response
            face_check_response_path = "face_check_response"
            os.makedirs(face_check_response_path, exist_ok=True)

            output_file = os.path.join(face_check_response_path, f"{file_uuid}.json")
            
            try:
                async with aiofiles.open(output_file, "w") as f:
                    await f.write(json.dumps(face_check_response, indent=4))
            except Exception as e:
                logging.error(f"Error saving face check response: {e}")
                return None,{"error": f"Error saving face check response: {e}"}

            return image_file_path,face_check_response

    except Exception as e:
        logging.error(f"HTTP request failed: {e}")
        return None,{"error": "Request failed due to an unexpected error"}



async def save_image_with_unique_name(image_bytes, directory="./saved_images"):
    os.makedirs(directory, exist_ok=True)

    # Generate a unique filename
    unique_filename = f"{uuid.uuid4().hex}.png"  # Use .png or the relevant format
    unique_path = f"{directory}/{unique_filename}"
    
    # Load and save the image
    image = Image.open(io.BytesIO(image_bytes))
    image.save(unique_path)
    return unique_path

async def get_best_urls(face_check_results):
       
        best_urls_list = []
        print(f"total urls found: {len(face_check_results)}")
        # Step 1: First try to collect links with scores >= 80, up to 5
        count = 0
        for link in face_check_results:
            if link["score"] >= 80:
                best_urls_list.append((link["score"], link["url"]))
                count += 1
                if len(best_urls_list) >= 8:
                    break
               
        if len(best_urls_list) == 0:
            print("NO  urls found")
        print(f"selected urls number: {len(best_urls_list)}")
        
        return best_urls_list
   


async def generate_gpt_scrapping_summary(best_urls_list):
    best_urls_list = [link for score,link in best_urls_list]
    links_str = "\n".join(best_urls_list)
    prompt = f"""
        You are given the following links:

        {links_str}
        Your task is to analyze the content across all the links to infer information about a single individual.

        Important Instructions:
            1. There may be references to multiple people across the links. Use critical analysis to determine the most likely central individual discussed.
            2. If multiple profiles are mentioned, use majority evidence across the links to consolidate findings into only one profile.
            3. Do not assume or fabricate any information that is not directly supported by the content.
            4. If you find only the name of the individual, and no other details, then output the name and set all other fields to None.

        Output Format (Mandatory):
            Name: <name>
            Job Experience: <details or None>
            Summary: <details or None>
            
        Additional Constraints:
            1. Summarize only one person.
            2. Do not mix information from multiple individuals.
            3. Be concise and factual.mary:
    """
    Summary =await helpers.open_ai_scraping_api(message=prompt, use_model="gpt-4.1")
    return Summary
    
  




async def generate_summary(best_urls_list) -> str:
    print("inside generate_summary")
    html_text = ""
    rank_text = ""
    score_value = 0
    html_text_list = []
    link_download_time = time.time()
    for score,url in best_urls_list:
        score_value = score
        print(url)
        html_name = helpers.html_download(url)
       
        if html_name:
            print('getting html text')
            if os.path.exists(html_name):
                scrapped_text = helpers.extract_text_from_html(html_name)
                if len(str(scrapped_text))>5000:
                    scrapped_text = scrapped_text[:5000]
                print(f"url: {url} \nscrapped text: {scrapped_text}")
                html_text += f"{scrapped_text}\n"
                html_text_list.append({'url':url,'html_text':scrapped_text})
            else:
                print('the html was not found. skipping.....')
    link_download_end_time = time.time()
    logging.info(f"Link download time: {link_download_end_time - link_download_time:.2f} seconds")
    
    try:
       name_module_time = time.time()

       names =  get_names(html_text_list)
       most_prominent_name = helpers.get_most_prominent_name(names)
       logging.info(f'Most prominent name: {most_prominent_name}')

       name_module_end_time = time.time()
       logging.info(f"Name module time: {name_module_end_time - name_module_time:.2f} seconds")

       #page ranking
       page_ranking_time = time.time()
       rank_text = page_ranking.rank_webpages_from_html(most_prominent_name,html_text_list)
       logging.info(f'Ranked Text:\n{rank_text}')

       page_ranking_end_time = time.time()
       logging.info(f"Page ranking time: {page_ranking_end_time - page_ranking_time:.2f} seconds")
       if rank_text:
         html_text = rank_text
       else:
            logging.info(f"got no ranking for name: {most_prominent_name} and links: {best_urls_list}")
       
    #    if most_prominent_name!= "Unknown":
    #        google_serach_restult = helpers.google_search(f'{most_prominent_name} linkedin')
    #        logging.info(f'google serach result for name {most_prominent_name}:\n {google_serach_restult}')
    #    html_text_name_pruned = ''
    #    if len(html_text_list)>  1:
    #         links = find_matching_links(names)
         
    #         logging.info(f'links after name pruning: {links}')
    #         logging.info(f'names: {names} and len: {len(names)}')
            
    #         html_text_list.sort(key=lambda entry: len(entry.get("html_text", "")))
    #         for entry in html_text_list:
    #             if entry['url'] in links:
    #                 html_text_name_pruned+=entry['html_text']
    #                 print('link matched....')
    #                 logging.info(f"link matched: {entry['url']}")
    except Exception as e:
        print(f'names not found: {e}')


    # if html_text_name_pruned != '':
    #     html_text = html_text_name_pruned
    open_ai_time = time.time()
    if len(html_text) >= 10000:
        html_text = html_text[:10000]
    prompt = '''
        The following includes the information provided along with details from different sources about a person.

        If there is mixed information from multiple people, try to identify content relevant to the main person. If no relevant information about a person is found, return: 'can not summarize about a person from the texts' without giving any additional reason.

        Provide a summary in the following format:

        Title: [Example: Elon Musk, Famous Serial Technology Entrepreneur, owner of Tesla, SpaceX, Neuralink]  

        Field of expertise: [Example: technology, space research, AI, biotech, electric automobiles]

        Net Worth: [Net worth if available]

        Summary:(new line) 
        [A summary within 200 words]
    '''
    message = f"{html_text}\n{prompt}"

    score_details = f"Confidence Score: {score_value}\n\n"
    if score_value !=0:
        summary = score_details + helpers.open_ai_api(message, use_model="gpt-4o")
    else:
        summary = 'Could not find the person.'
    open_ai_end_time = time.time()
    logging.info(f"Open AI time: {open_ai_end_time - open_ai_time:.2f} seconds")
    return summary


async def urls_filer(best_urls_list):
    filtered_urls = []  # Use a new list to avoid modifying the list while iterating
    for link in best_urls_list:
        if not any(keyword in link[1].lower() for keyword in ['linkedin']): # ["facebook", "twitter", "instagram", "youtube",'linkedin']
            filtered_urls.append(link)  # Only add links that do not match the keywords
    return filtered_urls

async def get_linked_in_summary(query_image,best_urls_list,face_verification_threshold):
    print("inside get_linked_in_summary")
    logging.info("inside get_linked_in_summary")

    li_at = 'AQEDAViSp-MCJP6kAAABlYZrCpAAAAGVqneOkFYAzQqX_E_DKKuX_jKEmhW4174DolTgTL4KNTRWuoda4IEZsh1_VE3G3hZNXcS3Z7zp6LD2Q7_r6O2hHV8wS6uO8biCnwPFskpqjHUIAYmTgOu14x7s'
    jsessionid = "ajax:0929358765196351330"
    cookie_jar = RequestsCookieJar()
    cookie_jar.set("li_at", li_at)
    cookie_jar.set("JSESSIONID", jsessionid)

    linkedin_usernames,valid_linkedin_links = await helpers.extract_linkedin_usernames(best_urls_list)
    if len(linkedin_usernames) == 0:
        return None
    else:
        try:
            logging.info(linkedin_usernames)
            logging.info(valid_linkedin_links)
            try:
               
               
                url = "http://localhost:8111/compare-linkedin"

                # Convert list to string format for form field
                linkedin_data = {"linkedin_urls": valid_linkedin_links}
                files = {"file": query_image}
                response = requests.post(url, files=files, data=linkedin_data)
                print(f'linkedin response: {response.json()}')
                linkedin_face_verification_results = response.json().get('results', [])


                logging.info(f'linkedin profiles usernames: {linkedin_usernames}')
                logging.info(f'after face verfication in linkedin pics: {linkedin_face_verification_results}\nfor usernames: {linkedin_usernames}')
                filtered_results = [(score,url) for score,url  in linkedin_face_verification_results if score >= face_verification_threshold]
                logging.info(f'after using {face_verification_threshold} threshold linkedin links: {filtered_results}')
                # Select the link with the maximum score if there are multiple candidates
                if filtered_results:
                    best_linked_in =  [max(filtered_results, key=lambda x: x[0])]
                    logging.info(f'final linkedin link: {best_linked_in}')
                    best_linkedin_usernames,best_valid_linkedin_links = await helpers.extract_linkedin_usernames(best_linked_in)
                    logging.info(f'best linkedin user name : {best_linkedin_usernames}')
                    # Initialize LinkedIn API with cookies
                    api = Linkedin('', '', cookies=cookie_jar)
                    profile = api.get_profile(best_linkedin_usernames[0])
                    profile_info = await helpers.parse_profile(profile)
                    return await helpers.linkedin_summary(profile,profile_info)

                else:
                    return None    
            except Exception as e:
                logging.info(f'error in get_profile_pic_link_and_path: {e} for usernames: {linkedin_usernames}')

 
        except Exception as e:
            logging.error(f'error in linkedin_summary. Cookie is expired {e}')
            return None
        

async def load_and_convert_image(image_path):
    """
    Loads an image from the given path and converts it to RGB format.
    
    Args:
        image_path (str): Path to the image file.
    
    Returns:
        numpy.ndarray: RGB image if successful, None otherwise.
    """
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error loading image: {image_path}")
        return None
    
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)




def get_names(text_list):
    results = []
    for text in text_list:
        prompt = (
            "Extract all unique names of persons from the following text "
            "and return them strictly as a valid JSON array (e.g., [name1,name2,name3]). "
            f"\\n{text['html_text']}\\n If no names are found, return []. Do not include any additional text or explanations."
        )

        response = helpers.open_ai_api(message=prompt)

        try:
            print(f"Raw API response: {response}") 
            if not response.strip():  # Handle empty response
                results.append({'url':text['url'],'names':[]})
                continue

            names = ast.literal_eval(response)  # Convert response to list
            if isinstance(names, list):
                results.append({'url':text['url'],'names':names})
            else:
                results.append({'url':text['url'],'names':[]})
        except Exception as e:
            print(f"Parsing error: {e}")
            results.append({'url':text['url'],'names':[]})

    return results



def find_matching_links(data_list):
    matching_urls = set()  # To store unique URLs
    
    # Convert the data into a list of (url, names) tuples
    url_name_pairs = [(entry['url'], entry['names']) for entry in data_list]

    # Compare each list of names with others
    for i, (url1, names1) in enumerate(url_name_pairs):
        for j, (url2, names2) in enumerate(url_name_pairs):
            if i != j:  # Avoid self-comparison
                for name1 in names1:
                    for name2 in names2:
                        # Soft matching using fuzzy string matching
                        match_score = fuzz.partial_ratio(name1.lower(), name2.lower())
                        if match_score > 60:  
                            matching_urls.add(url1)  # Add the matched URL
                            matching_urls.add(url2)
                            break  # Break inner loop if a match is found
    
    return list(matching_urls)  # Convert set to list before returning
