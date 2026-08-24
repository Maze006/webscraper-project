"""
Shared, deliberately polite HTTP helpers for the non-ATS scrapers.

Every source here is a public listing page or a documented public JSON API.
Requests are rate limited, identified by a real User-Agent and retried a couple
of times on transient failures so a single flaky response cannot kill a run.
"""

import time
import requests

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# Seconds to wait between consecutive requests to the same source.
REQUEST_DELAY = 1.5
REQUEST_TIMEOUT = 25
MAX_RETRIES = 3

def build_session(extra_headers: dict = None) -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept-Language": "en-US,en;q=0.9",
    })
    if extra_headers:
        session.headers.update(extra_headers)
    return session

def polite_request(session: requests.Session, method: str, url: str, **kwargs):
    """
    Performs a rate limited request with a small retry budget. Returns the
    response, or None when every attempt failed.
    """
    kwargs.setdefault('timeout', REQUEST_TIMEOUT)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = session.request(method, url, **kwargs)
        except requests.exceptions.RequestException as exc:
            if attempt == MAX_RETRIES:
                print(f"    [HTTP] {url} failed after {attempt} attempts: {exc}")
                return None
            time.sleep(REQUEST_DELAY * attempt)
            continue

        # Back off and retry on rate limiting or a transient server error.
        if response.status_code in (429, 500, 502, 503, 504):
            if attempt == MAX_RETRIES:
                print(f"    [HTTP] {url} returned {response.status_code}, giving up.")
                return None
            time.sleep(REQUEST_DELAY * attempt * 2)
            continue

        return response

    return None

def sleep_between_requests():
    time.sleep(REQUEST_DELAY)
