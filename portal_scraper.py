"""
Scrapers for the large employers that never appear on Greenhouse or Lever.

Three public JSON endpoints are covered:
  * Workday   - every tenant exposes /wday/cxs/{tenant}/{site}/jobs
  * Amazon    - amazon.jobs search.json
  * Microsoft - the apply.careers.microsoft.com public search API

Each posting still passes through the shared internship and geography gates, so
only Indian roles and fully remote roles outside India are returned.
"""

from classifier import classify_domain, classify_location, is_valid_internship
from http_client import build_session, polite_request, sleep_between_requests

WORKDAY_PAGE_SIZE = 20

def _build_row(company_name, title, location_text, location_type, apply_url, source):
    opportunity_type = 'Fellowship' if 'fellow' in title.lower() else 'Internship'
    return {
        'company_name': company_name,
        'role_title': title,
        'opportunity_type': opportunity_type,
        'domain': classify_domain(title, company_name),
        'status': 'CURRENT',
        'application_deadline': None,
        'program_start_date': None,
        'location': location_text,
        'location_type': location_type,
        'source': source,
        'apply_url': apply_url,
    }

def _india_location_facets(session, endpoint):
    """
    Workday exposes each tenant's own location facet ids. This reads them once
    and returns (facet_parameter, [ids]) for every value that the geography
    gate recognises as Indian, so the job feed can be filtered server side.
    Facet parameter names differ per tenant, hence the discovery step.
    """
    response = polite_request(session, 'POST', endpoint,
                              json={"appliedFacets": {}, "limit": 1, "offset": 0})
    if response is None or response.status_code != 200:
        return {}

    try:
        facets = response.json().get('facets', [])
    except ValueError:
        return {}

    discovered = {}

    def walk(nodes):
        for node in nodes:
            parameter = node.get('facetParameter')
            for value in node.get('values') or []:
                if value.get('values'):
                    walk([value])
                    continue
                if parameter and classify_location(value.get('descriptor') or '') == 'India':
                    discovered.setdefault(parameter, []).append(value['id'])

    walk(facets)
    return discovered

def fetch_workday_jobs(company_name: str, tenant: str, site: str, wd_host: str = 'wd5',
                       search_text: str = 'intern India', max_pages: int = 5, session=None):
    """
    Reads one Workday tenant's public job feed. Workday's location facets are
    named inconsistently between tenants (several return HTTP 400 for the
    standard country facet), so India is targeted through the relevance ranked
    free-text search and every posting is then filtered with the shared
    geography gate.
    """
    session = session or build_session({"Accept": "application/json",
                                        "Content-Type": "application/json"})
    endpoint = f"https://{tenant}.{wd_host}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
    results = []
    seen_urls = set()

    # Prefer a server side India filter. 'locations' is the most common facet
    # name; anything else the tenant offers is used as a fallback.
    facets = _india_location_facets(session, endpoint)
    ordered_parameters = sorted(facets, key=lambda name: (name != 'locations', name))
    applied_facets = {}
    for parameter in ordered_parameters:
        probe = polite_request(session, 'POST', endpoint,
                               json={"appliedFacets": {parameter: facets[parameter]},
                                     "limit": 1, "offset": 0})
        if probe is not None and probe.status_code == 200:
            try:
                if probe.json().get('total', 0) > 0:
                    applied_facets = {parameter: facets[parameter]}
                    break
            except ValueError:
                continue

    # Without a usable facet, fall back to the relevance ranked text search and
    # let the shared geography gate do the filtering.
    page_limit = max_pages if applied_facets else max(max_pages, 5)

    for page in range(page_limit):
        payload = {
            "appliedFacets": applied_facets,
            "limit": WORKDAY_PAGE_SIZE,
            "offset": page * WORKDAY_PAGE_SIZE,
            "searchText": "" if applied_facets else search_text,
        }
        response = polite_request(session, 'POST', endpoint, json=payload)
        if response is None or response.status_code != 200:
            break

        try:
            data = response.json()
        except ValueError:
            break

        postings = data.get('jobPostings', [])
        if not postings:
            break

        for posting in postings:
            title = (posting.get('title') or '').strip()
            if not is_valid_internship(title):
                continue

            location_text = (posting.get('locationsText') or '').strip()
            location_type = classify_location(location_text)
            if location_type is None:
                continue

            external_path = posting.get('externalPath') or ''
            if not external_path:
                continue
            apply_url = f"https://{tenant}.{wd_host}.myworkdayjobs.com/en-US/{site}{external_path}"
            if apply_url in seen_urls:
                continue
            seen_urls.add(apply_url)

            results.append(_build_row(company_name, title, location_text, location_type, apply_url,
                                      f'Workday ({company_name})'))

        if (page + 1) * WORKDAY_PAGE_SIZE >= data.get('total', 0):
            break

        sleep_between_requests()

    return results

def fetch_amazon_jobs(search_query: str = 'intern', max_pages: int = 3, session=None):
    """Reads amazon.jobs' public search.json feed, restricted to India."""
    session = session or build_session({"Accept": "application/json"})
    results = []
    seen_urls = set()
    page_size = 100

    for page in range(max_pages):
        params = {
            'base_query': search_query,
            'loc_query': 'India',
            'country': 'IND',
            'result_limit': page_size,
            'offset': page * page_size,
            'sort': 'recent',
        }
        response = polite_request(session, 'GET', "https://www.amazon.jobs/en/search.json", params=params)
        if response is None or response.status_code != 200:
            break

        try:
            jobs = response.json().get('jobs', [])
        except ValueError:
            break
        if not jobs:
            break

        for job in jobs:
            title = (job.get('title') or '').strip()
            if not is_valid_internship(title):
                continue

            location_text = (job.get('location') or job.get('normalized_location') or '').strip()
            location_type = classify_location(location_text)
            if location_type is None:
                continue

            job_path = job.get('job_path') or ''
            if not job_path:
                continue
            apply_url = f"https://www.amazon.jobs{job_path}"
            if apply_url in seen_urls:
                continue
            seen_urls.add(apply_url)

            results.append(_build_row('Amazon', title, location_text, location_type, apply_url, 'Amazon'))

        if len(jobs) < page_size:
            break
        sleep_between_requests()

    return results

def fetch_microsoft_jobs(search_query: str = 'intern', location: str = 'India',
                         max_pages: int = 3, session=None):
    """Reads Microsoft's public careers search API (apply.careers.microsoft.com)."""
    session = session or build_session({"Accept": "application/json"})
    results = []
    seen_urls = set()
    page_size = 20

    for page in range(max_pages):
        params = {
            'domain': 'microsoft.com',
            'query': search_query,
            'location': location,
            'start': page * page_size,
            'num': page_size,
        }
        response = polite_request(session, 'GET',
                                  "https://apply.careers.microsoft.com/api/pcsx/search",
                                  params=params)
        if response is None or response.status_code != 200:
            break

        try:
            data = response.json().get('data', {})
        except ValueError:
            break

        positions = data.get('positions', [])
        if not positions:
            break

        for position in positions:
            title = (position.get('name') or '').strip()
            if not is_valid_internship(title):
                continue

            location_text = ", ".join(position.get('locations') or []) or ''
            location_type = classify_location(location_text)
            if location_type is None:
                continue

            apply_url = position.get('positionUrl') or ''
            if not apply_url:
                job_id = position.get('displayJobId') or position.get('id')
                if not job_id:
                    continue
                apply_url = f"https://jobs.careers.microsoft.com/global/en/job/{job_id}"
            if apply_url in seen_urls:
                continue
            seen_urls.add(apply_url)

            results.append(_build_row('Microsoft', title, location_text, location_type, apply_url, 'Microsoft'))

        if (page + 1) * page_size >= data.get('count', 0):
            break
        sleep_between_requests()

    return results

if __name__ == '__main__':
    print("Amazon:")
    for r in fetch_amazon_jobs(max_pages=1)[:5]:
        print(f"  - {r['role_title'][:48]:48} | {r['location']}")
    print("Microsoft:")
    for r in fetch_microsoft_jobs(max_pages=1)[:5]:
        print(f"  - {r['role_title'][:48]:48} | {r['location']}")
    print("Workday (NVIDIA):")
    for r in fetch_workday_jobs('Nvidia', 'nvidia', 'NVIDIAExternalCareerSite', 'wd5', max_pages=3)[:5]:
        print(f"  - {r['role_title'][:48]:48} | {r['location']}")
