"""
Unstop scraper.

Unstop (formerly Dare2Compete) is an India-first student opportunity platform.
Its robots.txt explicitly allows /api/public/*, which is the documented public
search endpoint used here, so no HTML scraping or private endpoint is involved.
"""

from datetime import datetime

from classifier import classify_domain, classify_location, is_senior_role
from http_client import build_session, polite_request, sleep_between_requests

SEARCH_URL = "https://unstop.com/api/public/opportunity/search-result"
SITE_URL = "https://unstop.com"

def _parse_deadline(raw_value):
    """Converts Unstop's ISO timestamp (e.g. 2026-09-06T00:00:00+05:30) to a date."""
    if not raw_value:
        return None
    try:
        return datetime.fromisoformat(str(raw_value)).date().isoformat()
    except ValueError:
        return None

def _resolve_location(item: dict):
    """
    Unstop only hosts Indian opportunities, so a work-from-home listing is an
    India based remote role rather than a foreign one.
    """
    job_detail = item.get('jobDetail') or {}
    cities = [c for c in (job_detail.get('locations') or []) if c]

    if cities:
        location_text = ", ".join(cities)
        if classify_location(location_text) == 'India':
            return location_text, 'India'
        # An Indian platform listing an unrecognised city is still Indian.
        return f"{location_text}, India", 'India'

    if job_detail.get('type') == 'wfh' or item.get('region') == 'online':
        return "Work from home, India", 'India'

    return None, None

def fetch_unstop_internships(max_pages: int = 5, per_page: int = 30, session=None):
    """
    Pages through Unstop's open internship listings and returns rows matching
    the database schema.
    """
    session = session or build_session({"Accept": "application/json"})
    collected = []
    seen_urls = set()

    for page in range(1, max_pages + 1):
        params = {
            'opportunity': 'internships',
            'page': page,
            'per_page': per_page,
            'oppstatus': 'open',
        }
        response = polite_request(session, 'GET', SEARCH_URL, params=params)
        if response is None or response.status_code != 200:
            break

        try:
            payload = response.json().get('data', {})
        except ValueError:
            break

        items = payload.get('data', [])
        if not items:
            break

        for item in items:
            title = (item.get('title') or '').strip()
            if not title or is_senior_role(title):
                continue

            organisation = (item.get('organisation') or {}).get('name', '').strip()
            if not organisation:
                continue

            location_text, location_type = _resolve_location(item)
            if not location_type:
                continue

            apply_url = item.get('seo_url') or item.get('public_url')
            if not apply_url:
                continue
            if not apply_url.startswith('http'):
                apply_url = f"{SITE_URL}/{apply_url.lstrip('/')}"
            if apply_url in seen_urls:
                continue
            seen_urls.add(apply_url)

            role_title = title if 'intern' in title.lower() else f"{title} Internship"
            opportunity_type = 'Fellowship' if 'fellow' in title.lower() else 'Internship'

            collected.append({
                'company_name': organisation,
                'role_title': role_title,
                'opportunity_type': opportunity_type,
                'domain': classify_domain(role_title, organisation),
                'status': 'CURRENT',
                'application_deadline': _parse_deadline(item.get('end_date')),
                'program_start_date': None,
                'location': location_text,
                'location_type': location_type,
                'source': 'Unstop',
                'apply_url': apply_url,
            })

        # Stop early once the API says the last page has been reached.
        if payload.get('current_page') and payload.get('last_page'):
            if payload['current_page'] >= payload['last_page']:
                break

        sleep_between_requests()

    return collected

if __name__ == '__main__':
    roles = fetch_unstop_internships(max_pages=2)
    print(f"Fetched {len(roles)} internships from Unstop (2 pages).")
    for role in roles[:8]:
        print(f" - {role['role_title'][:42]:42} | {role['company_name'][:22]:22} | "
              f"{role['location'][:24]:24} | closes {role['application_deadline']}")
