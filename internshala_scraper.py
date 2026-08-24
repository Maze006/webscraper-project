"""
Internshala scraper.

Internshala is an India-only internship marketplace, so it is the single
highest yield source for this project. Only the server rendered category
listing pages are used (for example /internships/computer-science-internship/
and its /page-N/ variants). Internshala's robots.txt disallows /api/,
/internship/search/ and any URL carrying a query string, so none of those are
touched here.
"""

from bs4 import BeautifulSoup

from classifier import classify_domain, classify_location, is_senior_role
from http_client import build_session, polite_request, sleep_between_requests

BASE_URL = "https://internshala.com"

# Phrases Internshala uses for a work-from-home listing. These are still Indian
# opportunities, so they are tagged as India rather than as foreign remote.
WFH_MARKERS = ("work from home", "work-from-home", "wfh", "remote")

def _card_location(card) -> str:
    node = card.select_one('.row-1-item.locations') or card.select_one('.locations')
    if not node:
        return ""
    return " ".join(node.get_text(" ", strip=True).split())

def _resolve_location(raw_location: str):
    """
    Maps an Internshala location string onto (location_text, location_type).
    Work-from-home listings on an India-only board are India based, so they are
    labelled accordingly instead of being treated as foreign remote roles.
    """
    if not raw_location:
        return None, None

    location_type = classify_location(raw_location)
    if location_type == 'India':
        return raw_location, 'India'

    if any(marker in raw_location.lower() for marker in WFH_MARKERS):
        return f"{raw_location}, India", 'India'

    # Anything else is a genuinely foreign posting: let the shared gate decide.
    return (raw_location, location_type) if location_type else (None, None)

def parse_listing_page(html: str):
    """Extracts every internship card from one Internshala listing page."""
    soup = BeautifulSoup(html, 'html.parser')
    results = []

    for card in soup.select('div.individual_internship'):
        title_node = card.select_one('a.job-title-href') or card.select_one('h2.job-internship-name a')
        company_node = card.select_one('p.company-name')
        if not title_node or not company_node:
            continue

        title = title_node.get_text(strip=True)
        company_name = company_node.get_text(strip=True)

        # The board only lists internships, so the title itself rarely contains
        # the word "intern". Screening on seniority is the meaningful check.
        if is_senior_role(title):
            continue

        location_text, location_type = _resolve_location(_card_location(card))
        if not location_type:
            continue

        href = card.get('data-href') or title_node.get('href')
        if not href:
            continue
        apply_url = href if href.startswith('http') else BASE_URL + href

        stipend_node = card.select_one('span.stipend')
        stipend = stipend_node.get_text(strip=True) if stipend_node else ''
        role_title = f"{title} Internship" if 'intern' not in title.lower() else title

        results.append({
            'company_name': company_name,
            'role_title': role_title,
            'opportunity_type': 'Internship',
            'domain': classify_domain(role_title, company_name),
            'status': 'CURRENT',
            'application_deadline': None,   # Internshala listings are rolling
            'program_start_date': None,
            'location': location_text,
            'location_type': location_type,
            'source': 'Internshala',
            'apply_url': apply_url,
            'stipend': stipend,
        })

    return results

def fetch_internshala_internships(category: str, max_pages: int = 3, session=None):
    """
    Scrapes one Internshala category, following /page-N/ pagination.
    `category` is a slug such as 'computer-science-internship'.
    """
    session = session or build_session()
    collected = []
    seen_urls = set()

    for page in range(1, max_pages + 1):
        path = f"/internships/{category}/" if page == 1 else f"/internships/{category}/page-{page}/"
        response = polite_request(session, 'GET', BASE_URL + path)

        if response is None or response.status_code != 200:
            break

        page_results = parse_listing_page(response.text)
        if not page_results:
            break

        new_on_page = 0
        for item in page_results:
            if item['apply_url'] in seen_urls:
                continue
            seen_urls.add(item['apply_url'])
            collected.append(item)
            new_on_page += 1

        # A page that repeats the previous one means pagination has run out.
        if new_on_page == 0:
            break

        sleep_between_requests()

    return collected

if __name__ == '__main__':
    roles = fetch_internshala_internships('computer-science-internship', max_pages=1)
    print(f"Fetched {len(roles)} internships from Internshala (1 page).")
    for role in roles[:8]:
        print(f" - {role['role_title'][:45]:45} | {role['company_name'][:22]:22} | "
              f"{role['location'][:28]:28} | {role['domain']}")
