import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta
from pydantic import BaseModel
from google import genai
from google.genai import types
from classifier import classify_location

class LabOpportunity(BaseModel):
    role_title: str
    location: str
    opportunity_type: str
    status: str
    application_deadline: str
    program_start_date: str
    apply_url: str

def parse_lab_page(url: str, company_name: str, domain: str = 'Research Lab'):
    """
    Fetches a webpage, cleans the HTML, and uses Gemini Pro to extract structured 
    opportunity data matching the database schema.
    """
    try:
        # 1. Fetch the webpage content
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        # 2. Strip unnecessary HTML boilerplate
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove scripts, styles, headers, footers to reduce noise
        for element in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
            element.decompose()
            
        text = soup.get_text(separator='\n')
        
        # Clean up excessive whitespace
        lines = (line.strip() for line in text.splitlines())
        cleaned_text = '\n'.join(line for line in lines if line)
        
        # Truncate text just in case it's a massive page
        cleaned_text = cleaned_text[:30000] 
        
        # 3. Setup Gemini SDK client
        # Relies on GEMINI_API_KEY environment variable being set
        client = genai.Client()
        
        today_str = date.today().isoformat()
        fallback_date = (date.today() + timedelta(days=60)).isoformat()
        
        prompt = f"""
        Extract the fellowship or internship opportunity details from the following academic lab webpage text.
        
        Webpage URL: {url}
        Company/Lab Name: {company_name}
        Current Date: {today_str}
        
        Rules for extraction:
        - `role_title`: The specific name of the role or fellowship (e.g., "Student Summer Research Fellowship")
        - `opportunity_type`: Must be strictly 'Fellowship' or 'Internship'
        - `status`: Must be 'CURRENT' if applications are currently open or 'UPCOMING' if they open in the future
        - `application_deadline`: Must be YYYY-MM-DD. If ambiguous or missing, use {fallback_date}
        - `program_start_date`: Must be YYYY-MM-DD. If missing, estimate a reasonable date.
        - `location`: The city and country where the programme takes place, exactly as written on the page.
          If the programme is fully remote, return "Remote". If no location is stated, return "Unknown".
        - `apply_url`: The direct link to apply found in the text. If none is found, return the Webpage URL.
        
        Webpage Text:
        {cleaned_text}
        """
        
        # 4. Generate structured JSON output using Gemini Pro
        gen_response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=LabOpportunity,
                temperature=0.1,
            ),
        )
        
        # Parse the JSON response returned by the model
        extracted_data = json.loads(gen_response.text)
        
        # 5. Geography gate: keep India, or fully remote programmes outside India
        location_text = extracted_data.get('location', '')
        location_type = classify_location(location_text)
        if location_type is None:
            print(f"Skipping '{company_name}': location '{location_text}' is neither in India nor remote.")
            return None

        # 6. Format to match our DB schema
        result_dict = {
            'company_name': company_name,
            'role_title': extracted_data.get('role_title', 'Research Fellow'),
            'opportunity_type': extracted_data.get('opportunity_type', 'Fellowship'),
            'domain': domain,
            'status': extracted_data.get('status', 'CURRENT'),
            'application_deadline': extracted_data.get('application_deadline', fallback_date),
            'program_start_date': extracted_data.get('program_start_date', fallback_date),
            'location': location_text,
            'location_type': location_type,
            'source': 'Research Lab',
            'apply_url': extracted_data.get('apply_url', url)
        }
        
        return result_dict

    except requests.exceptions.RequestException as e:
        print(f"Network error fetching the lab page '{url}': {e}")
        return None
    except Exception as e:
        print(f"Error during Gemini parsing for '{url}': {e}")
        return None

if __name__ == '__main__':
    # Test CLI block (requires GEMINI_API_KEY environment variable)
    print("Testing Lab Scraper with Gemini Pro...\n")
    
    if 'GEMINI_API_KEY' not in os.environ:
        print("[WARNING] GEMINI_API_KEY environment variable is not set. The Gemini SDK call will fail.")
        print("Please set it before running this script in production.")
        print("Skipping live API test.")
    else:
        # Use a generic recognizable research lab fellowship page as a test
        test_url = "https://www.nsf.gov/funding/opportunities" # Sample URL, in reality would be a specific fellowship
        test_company = "National Science Foundation"
        
        print(f"Scraping '{test_company}' from {test_url}...")
        result = parse_lab_page(url=test_url, company_name=test_company)
        
        if result:
            print("\n[SUCCESS] Successfully parsed opportunity data:")
            for key, value in result.items():
                print(f" - {key}: {value}")
        else:
            print("\n[ERROR] Failed to parse lab page.")
