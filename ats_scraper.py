import requests
from datetime import date, timedelta
from classifier import is_valid_internship, classify_domain, classify_location

def _greenhouse_location(job: dict) -> str:
    """
    Builds a single location string for a Greenhouse posting by merging the
    primary location with every office name attached to the job.
    """
    parts = []

    location = job.get('location') or {}
    if isinstance(location, dict) and location.get('name'):
        parts.append(location['name'])

    for office in job.get('offices') or []:
        if isinstance(office, dict):
            for key in ('name', 'location'):
                value = office.get(key)
                if value and value not in parts:
                    parts.append(value)

    return ' | '.join(parts)

def _lever_location(job: dict) -> str:
    """
    Builds a single location string for a Lever posting from the category
    location, any additional locations, the country and the workplace type.
    """
    parts = []

    categories = job.get('categories') or {}
    if categories.get('location'):
        parts.append(categories['location'])

    for extra in categories.get('allLocations') or []:
        if extra and extra not in parts:
            parts.append(extra)

    if job.get('country'):
        parts.append(job['country'])

    # Lever exposes 'remote' / 'hybrid' / 'on-site' separately from the city.
    if job.get('workplaceType'):
        parts.append(job['workplaceType'])

    return ' | '.join(parts)

def fetch_greenhouse_jobs(board_token: str):
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs?content=true"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    jobs = data.get('jobs', [])
    results = []
    seen_roles = set()
    
    for job in jobs:
        title = job.get('title', '')
        
        # Strict internship gate — discard full-time / senior / HR roles
        if not is_valid_internship(title):
            continue

        # Geography gate — keep India, or fully remote roles outside India
        location_text = _greenhouse_location(job)
        location_type = classify_location(location_text)
        if location_type is None:
            continue

        company_name = board_token.replace('-', ' ').title()
        
        apply_url = job.get('absolute_url')
        if not apply_url:
            continue
            
        # Deduplication filter
        dedup_key = (company_name.lower(), title.lower())
        if dedup_key in seen_roles:
            continue
        seen_roles.add(dedup_key)
            
        opportunity_type = 'Fellowship' if 'fellow' in title.lower() else 'Internship'
        classified_domain = classify_domain(title, company_name)
            
        results.append({
            'company_name': company_name,
            'role_title': title,
            'opportunity_type': opportunity_type,
            'domain': classified_domain,
            'status': 'CURRENT',
            'application_deadline': None,
            'program_start_date': None,
            'location': location_text,
            'location_type': location_type,
            'source': 'Greenhouse',
            'apply_url': apply_url
        })
        
    return results

def fetch_lever_jobs(company_token: str):
    url = f"https://api.lever.co/v0/postings/{company_token}?mode=json"
    response = requests.get(url)
    response.raise_for_status()
    jobs = response.json()
    
    results = []
    seen_roles = set()
    
    for job in jobs:
        title = job.get('text', '')
        
        # Strict internship gate — discard full-time / senior / HR roles
        if not is_valid_internship(title):
            continue

        # Geography gate — keep India, or fully remote roles outside India
        location_text = _lever_location(job)
        location_type = classify_location(location_text)
        if location_type is None:
            continue

        company_name = company_token.replace('-', ' ').title()
        
        apply_url = job.get('applyUrl', job.get('hostedUrl', ''))
        if not apply_url:
            continue
            
        # Deduplication filter
        dedup_key = (company_name.lower(), title.lower())
        if dedup_key in seen_roles:
            continue
        seen_roles.add(dedup_key)
            
        opportunity_type = 'Fellowship' if 'fellow' in title.lower() else 'Internship'
        classified_domain = classify_domain(title, company_name)
            
        results.append({
            'company_name': company_name,
            'role_title': title,
            'opportunity_type': opportunity_type,
            'domain': classified_domain,
            'status': 'CURRENT',
            'application_deadline': None,
            'program_start_date': None,
            'location': location_text,
            'location_type': location_type,
            'source': 'Lever',
            'apply_url': apply_url
        })
        
    return results
