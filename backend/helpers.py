import requests
from bs4 import BeautifulSoup
import uuid
from urllib.parse import unquote
import logging
from datetime import datetime
import re
import os
from collections import Counter
from fuzzywuzzy import fuzz
from urllib.parse import urlparse
import re
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

key = os.getenv("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = key
def open_ai_api(message="sample message", use_model="gpt-3.5-turbo"):

    client = OpenAI()
    completion = client.chat.completions.create(
        model=use_model,
        temperature=0.0,
        store=False,
        messages=[{"role": "user", "content": message}],
    )
    # print(completion.choices[0].message.content)
   

    return completion.choices[0].message.content

async def open_ai_scraping_api(message="sample message", use_model="gpt-3.5-turbo"):
    client = OpenAI()
    response = client.responses.create(
    model=use_model,
    tools=[{"type": "web_search_preview"}],
    input= message)
    return response.output_text

def html_download(url):
    html_name = f"selected_{uuid.uuid4().hex}.html"
    try:
        response = requests.get(url,timeout=10)
        response.raise_for_status()
        html_content = response.text
        with open(html_name, "w", encoding="utf-8") as file:
            file.write(html_content)
        print("HTML content downloaded successfully.")

    except requests.exceptions.RequestException as e:
        logging.info(f'can not download {url} due to {e}')
        html_name = None
      
    return html_name

def extract_text_from_html(html_name):
    with open(html_name, "r", encoding="utf-8") as file:
        html_content = file.read()

    soup = BeautifulSoup(html_content, "html.parser")
    text_content = soup.get_text()
    lines = text_content.splitlines()

    text = ""
    for line in lines:
        cleaned_line = line.strip()
        if cleaned_line:
            text += " " + cleaned_line
    return text

async def extract_linkedin_usernames(urls):
      
        linkedin_pattern = re.compile(r'https?://(www\.)?linkedin\.com/in/([\w%\-]+)')
        seen = set()
        usernames = []
        valid_linkedin_urls = []
        for score,url in urls:
            if (match := linkedin_pattern.match(url)):
                username = match.group(2)
                username = unquote(username)

                if username not in seen:
                    valid_linkedin_urls.append(url)
                    seen.add(username)
                    usernames.append(username)
                    logging.info(f'username: {username} score:{score}, url: {url}')
                    print(f'username: {username} score:{score}, url: {url}')
        print(f'usernames: {usernames}')
        return usernames,valid_linkedin_urls
async def parse_profile(data):
    try:
        first_name = data.get('firstName', 'N/A')
        last_name = data.get('lastName', 'N/A')
        location = data.get('locationName', 'N/A')
        industry = data.get('industryName', 'N/A')
        headline = data.get('headline', 'N/A')
        summary = data.get('summary', 'N/A')
        
        experience = data.get('experience', [])
        experience_text = ""
        for exp in experience:
            company = exp.get('companyName', 'N/A')
            title = exp.get('title', 'N/A')
            time_period = exp.get('timePeriod', {}).get('startDate', {})
            start_month = time_period.get('month', 'N/A')
            start_year = time_period.get('year', 'N/A')
            experience_text += f"{title} at {company} ({start_month} {start_year})\n"
        
        skills = data.get('skills', [])
        skills_text = ", ".join([skill.get('name', 'N/A') for skill in skills])
        
        # Create the paragraph format
        paragraph = f"{first_name} {last_name} is a {industry} professional located in {location}. "
        paragraph += f"Currently, {first_name} {last_name} work as a {headline}.\n"
        paragraph += "Experience:\n" + experience_text if experience else "No experience listed.\n"
        paragraph += f"Skills: {skills_text}" if skills_text else "No skills listed."
        
        return paragraph
    except Exception as e:
        return f"An error occurred: {str(e)}"
    

async def linkedin_summary(profile,profile_info):
  
    linked_in_description = profile.get('summary', None)
    
    if linked_in_description:
        return f"{profile_info}\n LinkedIn About:\n{linked_in_description}"
    else:
        prompt = f'''{profile_info}\n\nFrom the above information. Can You make a summary of the person. His/Her name, 
            occupation(spcially his current job), net worth, descriptiion, skills and others. Try to make the summary in 4 parts: 
                Name
                Title
                Occupation(current with location if available)
                Summary:within 200 words'''
        return open_ai_api(prompt,'gpt-4o')
    





def clean_name(name):
    """Cleans and normalizes names (removes middle initials, extra spaces, etc.)."""
    return re.sub(r"\b[A-Z]\.\s?", "", name).strip().lower()  # Removes initials like "M."

def get_name_from_url(url):
    """Extracts a possible name from a URL."""
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.split("/")
    
    possible_names = [part.replace("-", " ").title() for part in path_parts if part.isalpha() and len(part) > 2]
    
    return possible_names[0] if possible_names else parsed_url.netloc.split(".")[0].capitalize()


def clean_name(name):
    """Cleans and normalizes names (removes middle initials, extra spaces, etc.)."""
    return re.sub(r"\b[A-Z]\.\s?", "", name).strip().lower()  # Removes initials like "M."

def get_name_from_url(url):
    """Extracts a possible name from a URL."""
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.split("/")
    
    possible_names = [part.replace("-", " ").title() for part in path_parts if part.isalpha() and len(part) > 2]
    
    return possible_names[0] if possible_names else None

def get_most_prominent_name(data_list):
    """Finds the most prominent name using fuzzy matching and URL fallback."""
    name_counts = Counter()
    url_names = []

    # Step 1: Count occurrences of names and normalize variations
    for entry in data_list:
        names = entry.get("names", [])
        url = entry.get("url", "")

        if names:
            for name in names:
                cleaned_name = clean_name(name)
                matched = False
                
                # Try merging similar names using fuzzy matching
                for existing_name in name_counts:
                    if fuzz.ratio(cleaned_name, existing_name) > 70:  # Soft matching threshold
                        name_counts[existing_name] += 1
                        matched = True
                        break
                
                if not matched:
                    name_counts[cleaned_name] += 1

        # Step 2: Extract name from URL if possible
        if url:
            url_name = get_name_from_url(url)
            if url_name:
                url_names.append(url_name)

    # Step 3: Prioritize names that appear in both the names list and URL
    for url_name in url_names:
        for name in name_counts:
            if fuzz.ratio(url_name.lower(), name.lower()) > 85:  # Soft match
                return name.title()  # Prioritize a match with the URL

    # Step 4: If no URL match, return the most frequent name
    if name_counts:
        most_prominent_name = max(name_counts, key=name_counts.get)  # Get most frequent name
        return most_prominent_name.title()

    # Step 5: If no names were found, return the most common URL-derived name
    if url_names:
        return max(set(url_names), key=url_names.count)  # Most common extracted name

    return "Unknown"


 
import requests

def google_search(search_query, num_results=5):
    GOOGLE_SEARCH_API_KEY = os.getenv("GOOGLE_SEARCH_API_KEY")

    API_KEY =GOOGLE_SEARCH_API_KEY  # Replace with your API key
    SEARCH_ENGINE_ID = "a42052c32ac90420b"  # Replace with your search engine ID
    url = "https://www.googleapis.com/customsearch/v1"

    params = {
        "q": search_query,
        "key": API_KEY,
        "cx": SEARCH_ENGINE_ID,
        "num": num_results,  # Number of results to return
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()  # Raise an error for bad responses
        results = response.json().get("items", [])

        return [result["link"] for result in results[:num_results]]  # Return top N links

    except requests.RequestException as e:
        print(f"API request error: {e}")
        logging.info(f'google search api error {e}')
    except KeyError:
        print("Unexpected Google SeachAPI response format.")  
    
    return []
