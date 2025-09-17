import requests
from bs4 import BeautifulSoup
import spacy
import re
import sys
import spacy.cli
#spacy.cli.download("en_core_web_sm")
# Load spaCy NLP model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Spacy model not found. Please install it with: python -m spacy download en_core_web_sm")
    sys.exit(1)

# Define keywords for extracting professional and educational information
job_keywords = ["CEO", "founder", "scientist", "professor", "researcher", "engineer", "developer", "director", "manager"]
education_keywords = ["university", "college", "bachelor", "master", "PhD", "degree", "school"]
location_keywords = ["city", "state", "country", "born in", "living in", "resides in"]
religion_keywords = ["Christian", "Muslim", "Hindu", "Buddhist", "Jewish", "Atheist", "Catholic", "Protestant"]

# Function to extract text from a webpage
def extract_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, timeout=15, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        # Remove scripts and styles
        for script in soup(["script", "style"]):
            script.extract()

        return soup.get_text(separator=" ", strip=True)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

# Function to check if the full name is present in the text
def check_full_name_present(text, person_name):
    # Clean and normalize the name
    clean_name = re.sub(r'[^\w\s]', '', person_name).lower().strip()
    clean_text = re.sub(r'[^\w\s]', '', text).lower()
    
    # Check if full name is present
    name_parts = clean_name.split()
    
    if len(name_parts) > 1:
        # For multi-word names, check if all parts appear close to each other
        # This is a more strict check for multi-word names
        name_pattern = r'\b' + r'(?:\s+\w+){0,3}\s+'.join(re.escape(part) for part in name_parts) + r'\b'
        if re.search(name_pattern, clean_text):
            return True
            
    # Check if individual name parts appear
    # For very short names or when the full name pattern isn't found
    # we need to be careful about false positives
    part_count = 0
    for part in name_parts:
        if len(part) >= 4:  # Only count meaningful name parts (avoid short words like Dr, Mr)
            if re.search(r'\b' + re.escape(part) + r'\b', clean_text):
                part_count += 1
    
    # Return True if we found at least 2 meaningful parts of the name
    # or if the name has only one part and we found it
    return part_count >= 2 or (len(name_parts) == 1 and part_count == 1)

# Function to extract biographical details 
def extract_bio_details(text, person_name):
    # First verify the name is present before proceeding
    if not check_full_name_present(text, person_name):
        return {
            "names": [],
            "organizations": [],
            "job_titles": [],
            "locations": [],
            "education": [],
            "religion": []
        }
    
    doc = nlp(text)
    names, organizations, job_titles, locations, education, religion = set(), set(), set(), set(), set(), set()

    # Create a pattern to match variations of the person's name
    name_parts = person_name.lower().split()
    
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            ent_text_lower = ent.text.lower()
            if any(part in ent_text_lower for part in name_parts):
                names.add(ent.text)
        elif ent.label_ == "ORG":
            organizations.add(ent.text)
        elif ent.label_ in ["GPE", "LOC"]:
            locations.add(ent.text)
        elif ent.label_ in ["TITLE", "WORK_OF_ART"]:
            job_titles.add(ent.text)

    # Extract additional details using keyword matching
    for sentence in text.split("."):
        sentence_lower = sentence.lower()
        
        # Only process sentences potentially related to the person
        if any(part in sentence_lower for part in name_parts):
            # Education check
            if any(word in sentence_lower for word in education_keywords):
                education.add(sentence.strip())

            # Work check
            if any(word.lower() in sentence_lower for word in job_keywords):
                job_titles.add(sentence.strip())

            # Location check
            if any(word in sentence_lower for word in location_keywords):
                locations.add(sentence.strip())

            # Religion check
            if any(word in sentence_lower for word in religion_keywords):
                religion.add(sentence.strip())

    return {
        "names": list(names),
        "organizations": list(organizations),
        "job_titles": list(job_titles),
        "locations": list(locations),
        "education": list(education),
        "religion": list(religion)
    }

# Function to score webpages based on information completeness
def score_page(bio_details, text, person_name):
    # If the bio_details is empty (name not found), return 0 score
    if not bio_details["names"] and not bio_details["organizations"] and not bio_details["job_titles"] and not bio_details["locations"] and not bio_details["education"] and not bio_details["religion"]:
        return 0
        
    # Double-check that the name is actually present
    if not check_full_name_present(text, person_name):
        return 0
        
    score = 0

    # Assign scores based on the presence of key information
    if bio_details["names"]: score += 10
    if bio_details["organizations"]: score += 10
    if bio_details["job_titles"]: score += 15
    if bio_details["locations"]: score += 10
    if bio_details["education"]: score += 10
    if bio_details["religion"]: score += 5

    # Count variations of the name to determine relevance
    name_parts = person_name.lower().split()
    name_count = 0
    
    # Count full name occurrences
    full_name_pattern = r'\b' + r'\s+'.join(re.escape(part) for part in name_parts) + r'\b'
    full_name_count = len(re.findall(full_name_pattern, text.lower()))
    name_count += full_name_count * 2  # Weight full name matches more heavily
    
    # Count individual name part occurrences for longer name parts (to avoid common words)
    for part in name_parts:
        if len(part) >= 4:  # Only count significant name parts
            part_count = len(re.findall(r'\b' + re.escape(part) + r'\b', text.lower()))
            name_count += part_count

    # Bonus Score: If the person's name appears multiple times, it's more relevant.
    score += min(10, name_count)

    return score

# Function to rank webpages based on the extracted information
def rank_webpages(person_name, urls):
    results = []
    for url in urls:
        print(f"Processing: {url}")
        text = extract_text(url)
        if text:
            # First check if the full name is present
            if check_full_name_present(text, person_name):
                bio_details = extract_bio_details(text, person_name)
                score = score_page(bio_details, text, person_name)
                results.append({"url": url, "score": score, "bio_details": bio_details})
            else:
                # Name not found, score zero
                results.append({"url": url, "score": 0, "bio_details": {
                    "names": [], "organizations": [], "job_titles": [],
                    "locations": [], "education": [], "religion": []
                }})
        else:
            # Failed to fetch URL, score zero
            results.append({"url": url, "score": 0, "bio_details": {
                "names": [], "organizations": [], "job_titles": [],
                "locations": [], "education": [], "religion": []
            }})

    # Sort results by score (descending), keeping ALL links
    results.sort(key=lambda x: x["score"], reverse=True)
    return results

# Function to display ranked results
def display_results(ranked_results):
    # Display ranked results (excluding scores of zero)
    print("\n=== Ranked Results (All Links) ===")
    for i, res in enumerate(ranked_results, 1):
        if res["score"] > 0:  # Only print results with score greater than 0
            print(f"{i}. {res['url']} (Score: {res['score']})")


    # Display URLs with Zero Scores
    print("\n=== URLs with Zero Score ===")
    for i, res in enumerate([r for r in ranked_results if r["score"] == 0], 1):
        print(f"{i}. {res['url']} (Score: {res['score']})")


def rank_webpages_from_html(most_prominent_name, html_text_list):
    results = []
    for item in html_text_list:
        text = item['html_text']
        url = item.get('url', '')
        # text = extract_text(item)
        print(f"Scoring: {url}")
        if check_full_name_present(text, most_prominent_name):
            bio_details = extract_bio_details(text, most_prominent_name)
            score = score_page(bio_details, text, most_prominent_name)
            results.append({"text": text, "score": score})
        else:
            results.append({"text": text, "score": 0})
    if all(result["score"] == 0 for result in results):
        return None
    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    final_text = ""
    for result in results:
        text = result["text"]
        if len(text)>5000:
            text = text[:5000]
        final_text+=text
    return final_text


if __name__ == "__main__":
    person_name = "Joseph M. Acaba"
    test_urls = [
     " https://linkedin.com/in/adam-ades-5387b7a",

"https://linkedin.com/in/perrieperilly",

"https://linkedin.com/in/andreea-caratas-2b17986b",

"https://mishpacha.com/category/travel/page/2/",

"https://theabrahamicbusinesscircle.com/moshe-shapoff-3/"
        
        ]

    # # Rank the webpages based on the person name and URLs provided
    # ranked_results = rank_webpages(person_name, test_urls)
    # print(ranked_results)
    # # Display the results
    # display_results(ranked_results)
    print(rank_webpages_from_html(person_name,test_urls))
