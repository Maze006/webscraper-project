"""
Single place that knows how to collect opportunities from every source.

Both the one-shot ingestion script and the scheduler call collect_all(), so the
source list never drifts between them. Every scraper applies the internship and
geography gates internally; collect_all only aggregates and reports.
"""

import os

from classifier import is_safe_url
from config import (
    ALL_GREENHOUSE_TARGETS, LEVER_TOKENS,
    INTERNSHALA_CATEGORIES, INTERNSHALA_MAX_PAGES,
    UNSTOP_MAX_PAGES, WORKDAY_TARGETS, WORKDAY_MAX_PAGES,
    ENABLE_AMAZON, ENABLE_MICROSOFT,
)
from ats_scraper import fetch_greenhouse_jobs, fetch_lever_jobs
from internshala_scraper import fetch_internshala_internships
from unstop_scraper import fetch_unstop_internships
from portal_scraper import fetch_workday_jobs, fetch_amazon_jobs, fetch_microsoft_jobs

LAB_TARGETS = [
    ("https://www.nsf.gov/funding/opportunities", "National Science Foundation", "Research Lab"),
]

def _run(label, fetcher, collected, verbose=True):
    """Runs one scraper, logs its yield and never lets a failure abort the run."""
    try:
        roles = fetcher() or []
    except Exception as exc:
        if verbose:
            print(f"  {label}: failed ({type(exc).__name__}: {exc})")
        return 0

    collected.extend(roles)
    if verbose:
        print(f"  {label}: {len(roles)} roles")
    return len(roles)

def collect_all(verbose=True, include_labs=True):
    """Aggregates every source into a single list of opportunity dicts."""
    collected = []

    if verbose:
        print("\n--- India-first boards (Internshala, Unstop) ---")
    for category in INTERNSHALA_CATEGORIES:
        _run(f"Internshala/{category}",
             lambda c=category: fetch_internshala_internships(c, max_pages=INTERNSHALA_MAX_PAGES),
             collected, verbose)
    _run("Unstop", lambda: fetch_unstop_internships(max_pages=UNSTOP_MAX_PAGES), collected, verbose)

    if verbose:
        print("\n--- Big-company portals (Workday, Amazon, Microsoft) ---")
    for company, tenant, site, host in WORKDAY_TARGETS:
        _run(f"Workday/{company}",
             lambda c=company, t=tenant, s=site, h=host: fetch_workday_jobs(
                 c, t, s, h, max_pages=WORKDAY_MAX_PAGES),
             collected, verbose)
    if ENABLE_AMAZON:
        _run("Amazon", fetch_amazon_jobs, collected, verbose)
    if ENABLE_MICROSOFT:
        _run("Microsoft", fetch_microsoft_jobs, collected, verbose)

    if verbose:
        print("\n--- ATS boards (Greenhouse, Lever) ---")
    for token in ALL_GREENHOUSE_TARGETS:
        _run(f"Greenhouse/{token}", lambda t=token: fetch_greenhouse_jobs(t), collected, verbose)
    for token in LEVER_TOKENS:
        _run(f"Lever/{token}", lambda t=token: fetch_lever_jobs(t), collected, verbose)

    if include_labs:
        if 'GEMINI_API_KEY' in os.environ:
            if verbose:
                print("\n--- Research labs ---")
            from lab_scraper import parse_lab_page
            for url, name, domain in LAB_TARGETS:
                def fetch_lab(u=url, n=name, d=domain):
                    parsed = parse_lab_page(u, n, d)
                    return [parsed] if parsed else []
                _run(f"Lab/{name}", fetch_lab, collected, verbose)
        elif verbose:
            print("\n--- Research labs skipped (GEMINI_API_KEY not set) ---")

    # Apply links come from third-party listings. Anything that is not a plain
    # http(s) URL is dropped here so it can never reach the database or the
    # Apply button in the UI.
    unsafe = [r for r in collected if not is_safe_url(r.get('apply_url'))]
    if unsafe:
        if verbose:
            print(f"\n[SECURITY] Dropped {len(unsafe)} listings with a non-http(s) apply link.")
        collected = [r for r in collected if is_safe_url(r.get('apply_url'))]

    return collected

def summarise(roles):
    """Returns (by_source, by_location_type, by_domain) counts for reporting."""
    by_source, by_location, by_domain = {}, {}, {}
    for role in roles:
        source = role.get('source', 'Unknown')
        by_source[source] = by_source.get(source, 0) + 1
        by_location[role['location_type']] = by_location.get(role['location_type'], 0) + 1
        by_domain[role['domain']] = by_domain.get(role['domain'], 0) + 1
    return by_source, by_location, by_domain

if __name__ == '__main__':
    roles = collect_all()
    by_source, by_location, by_domain = summarise(roles)
    print(f"\nCollected {len(roles)} roles")
    print("By source:", by_source)
    print("By location:", by_location)
    print("By domain:", by_domain)
