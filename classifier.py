import re
from datetime import date

# ---------------------------------------------------------------------------
# Geographic gate: keep roles in India, or fully remote roles based outside it.
# ---------------------------------------------------------------------------

# Country / state / city terms that identify an Indian posting.
INDIA_TERMS = [
    "india", "bharat", "ind",
    # States and union territories
    "karnataka", "maharashtra", "tamil nadu", "telangana", "kerala",
    "gujarat", "rajasthan", "haryana", "punjab", "west bengal",
    "uttar pradesh", "madhya pradesh", "andhra pradesh", "odisha", "assam",
    "goa", "bihar", "jharkhand", "chhattisgarh", "uttarakhand",
    # Cities, tech parks and campuses that appear in ATS location strings
    "bengaluru", "bangalore", "whitefield", "electronic city", "koramangala",
    "mumbai", "navi mumbai", "thane", "andheri", "powai",
    "delhi", "new delhi", "ncr", "gurgaon", "gurugram", "noida", "faridabad",
    "ghaziabad", "manesar",
    "hyderabad", "secunderabad", "gachibowli", "hitech city",
    "chennai", "pune", "hinjewadi", "kolkata", "ahmedabad", "gandhinagar",
    "jaipur", "chandigarh", "mohali", "kochi", "cochin", "trivandrum",
    "thiruvananthapuram", "coimbatore", "madurai", "indore", "bhopal",
    "nagpur", "nashik", "vadodara", "surat", "lucknow", "kanpur", "varanasi",
    "patna", "ranchi", "raipur", "bhubaneswar", "visakhapatnam", "vizag",
    "mysore", "mysuru", "mangalore", "mangaluru", "udaipur", "dehradun",
    "guwahati", "jodhpur", "kharagpur", "roorkee",
]

REMOTE_TERMS = [
    "remote", "work from home", "work-from-home", "wfh", "anywhere",
    "telecommute", "virtual", "home based", "home-based", "distributed",
]

# A hybrid or on-site posting outside India still requires showing up abroad,
# so it does not count as remote.
NON_REMOTE_TERMS = [
    "hybrid", "on-site", "onsite", "in-office", "in office", "non-remote",
    "not remote",
]

def _compile_terms(terms):
    return re.compile(r"\b(" + "|".join(re.escape(t) for t in terms) + r")\b", re.IGNORECASE)

INDIA_RE = _compile_terms(INDIA_TERMS)
REMOTE_RE = _compile_terms(REMOTE_TERMS)
NON_REMOTE_RE = _compile_terms(NON_REMOTE_TERMS)

# Postings with no usable location string are dropped by default: they cannot
# be proven to be in India or remote. Flip to True to keep them for triage.
ALLOW_UNKNOWN_LOCATION = False

def classify_location(location_text: str):
    """
    Returns 'India' for any role located in India (on-site, hybrid or remote),
    'Remote' for a fully remote role outside India, and None for everything
    else, i.e. roles that must be discarded.
    """
    if not location_text:
        return None

    text = str(location_text).strip()
    if not text or text.lower() in ("none", "null", "n/a", "-"):
        return None

    # India wins outright: an Indian role is in scope whatever its work mode.
    if INDIA_RE.search(text):
        return "India"

    # Outside India, only genuinely remote postings survive.
    if REMOTE_RE.search(text) and not NON_REMOTE_RE.search(text):
        return "Remote"

    return None

def is_allowed_location(location_text: str) -> bool:
    """Strict geographic gate applied by every scraper before a role is kept."""
    if classify_location(location_text) is not None:
        return True
    return ALLOW_UNKNOWN_LOCATION and not location_text


def classify_horizon(application_deadline: date, status: str) -> str:
    """
    Classifies the application deadline horizon into specific buckets based on the current date.
    """
    if application_deadline is None:
        return status
        
    today = date.today()
    
    if application_deadline < today:
        return 'EXPIRED'
        
    if status == 'CURRENT':
        return 'CURRENT'
        
    delta_days = (application_deadline - today).days
    
    if 0 <= delta_days <= 30:
        return '1_MONTH'
    elif 31 <= delta_days <= 90:
        return '3_MONTHS'
    elif 91 <= delta_days <= 180:
        return '6_MONTHS'
    else:
        return '1_YEAR'

# Senior / full-time employee exclusions
SENIORITY_EXCLUSIONS = [
    "senior", "lead", "staff", "principal", "manager", "director",
    "vice president", "vp", "head of", "recruiter", "talent", "hr",
    "sourcer", "recruiting", "recruitment", "full-time engineer",
    "full-time analyst",
]

# Student / internship inclusion keywords. Matched on word boundaries so that
# titles like "Internal Audit Analyst" or "Internal Systems" are not mistaken
# for internships.
STUDENT_KEYWORDS = [
    "intern", "interns", "internship", "internships", "fellow", "fellowship",
    "summer analyst", "co-op", "coop", "trainee", "undergraduate", "reu",
    "visiting student",
]

SENIORITY_RE = _compile_terms(SENIORITY_EXCLUSIONS)
STUDENT_RE = _compile_terms(STUDENT_KEYWORDS)

# ---------------------------------------------------------------------------
# Link safety
# ---------------------------------------------------------------------------

# Job listings are written by third parties (anyone can post on Internshala,
# Unstop or a Greenhouse board), so an apply link is untrusted input. Only
# ordinary web URLs are ever stored or rendered: a "javascript:" or "data:"
# URL reaching the Apply button would execute in the visitor's browser.
SAFE_URL_SCHEMES = ("http://", "https://")

def is_safe_url(url) -> bool:
    """True only for a plain http(s) URL."""
    if not url or not isinstance(url, str):
        return False
    return url.strip().lower().startswith(SAFE_URL_SCHEMES)

def is_senior_role(job_title: str) -> bool:
    """
    True when a title is a senior / full-time / recruiting role. Internship-only
    sources (Internshala, Unstop) guarantee the internship part themselves, so
    they screen on this alone rather than on the full is_valid_internship gate.
    """
    return bool(job_title) and bool(SENIORITY_RE.search(job_title))

def is_valid_internship(job_title: str) -> bool:
    """
    Strict gate: returns True only if the title is a student/internship role
    and NOT a senior/full-time employee position.
    """
    if not job_title:
        return False

    if SENIORITY_RE.search(job_title):
        return False

    return bool(STUDENT_RE.search(job_title))

def classify_domain(job_title: str, company_name: str = "") -> str:
    """
    4-Tier priority domain segregation matrix.
    Deterministically classifies a job title into a specific domain.
    """
    title = job_title.lower()
    
    # Priority 1: Quant
    quant_keywords = [
        "quant", "quantitative", "trading", "trader", "algo", "algorithmic",
        "derivatives", "fixed income", "alpha", "mathematical", "systematic"
    ]
    if any(kw in title for kw in quant_keywords):
        return "Quant"
        
    # Priority 2: Research Lab
    research_keywords = [
        "research scientist", "r&d", "laboratory", "reu", "phd intern",
        "research intern", "postdoc", "fellowship"
    ]
    research_exclusions = ["ux", "user experience", "market", "design"]
    
    if any(kw in title for kw in research_keywords):
        if not any(kw in title for kw in research_exclusions):
            return "Research Lab"
            
    # Priority 3: Finance
    finance_keywords = [
        "accounting", "finance", "financial", "audit", "tax", "treasury",
        "fp&a", "investment banking", "ibd", "wealth management",
        "capital markets", "summer analyst", "equity", "macro", "credit"
    ]
    finance_exclusions = ["software", "engineer", "developer", "data engineer", "systems"]
    
    if any(kw in title for kw in finance_keywords):
        if not any(kw in title for kw in finance_exclusions):
            return "Finance"
            
    # Priority 4: Fallback
    return "Tech"

if __name__ == '__main__':
    import datetime
    today = date.today()
    
    # --- Horizon Tests ---
    print(f"Testing horizons with today = {today}")
    assert classify_horizon(today - datetime.timedelta(days=1), 'CURRENT') == 'EXPIRED'
    assert classify_horizon(today + datetime.timedelta(days=15), 'CURRENT') == 'CURRENT'
    assert classify_horizon(today + datetime.timedelta(days=15), 'UPCOMING') == '1_MONTH'
    assert classify_horizon(None, 'CURRENT') == 'CURRENT'
    print("[PASS] Horizon tests passed.")
    
    # --- Internship Gate Tests ---
    print("\nTesting is_valid_internship()...")
    
    assert is_valid_internship("Software Engineer Intern") == True
    assert is_valid_internship("Summer Analyst - IBD") == True
    assert is_valid_internship("Research Fellow - AI") == True
    assert is_valid_internship("Software Engineer Intern (Open to Full-Time)") == True
    assert is_valid_internship("Undergraduate Research Intern") == True
    assert is_valid_internship("Co-op Engineer") == True
    assert is_valid_internship("REU Student") == True
    
    assert is_valid_internship("Senior Software Engineer") == False
    assert is_valid_internship("Lead Data Scientist") == False
    assert is_valid_internship("VP of Engineering") == False
    assert is_valid_internship("Campus Recruiter, ML Research") == False
    assert is_valid_internship("Director of Product") == False
    assert is_valid_internship("Full-Time Engineer") == False
    assert is_valid_internship("Staff Machine Learning Engineer") == False
    assert is_valid_internship("Internal Audit Analyst") == False
    assert is_valid_internship("Software Engineer, Internal Systems") == False
    assert is_valid_internship("International Trade Analyst") == False
    assert is_valid_internship("Data Science Interns - Summer 2027") == True
    assert is_senior_role("Senior Data Analyst") == True
    assert is_senior_role("Campus Recruiter") == True
    assert is_senior_role("Android App Development") == False

    print("\nTesting is_safe_url()...")
    assert is_safe_url("https://internshala.com/internship/detail/x") == True
    assert is_safe_url("http://example.com/job") == True
    assert is_safe_url("javascript:alert(1)") == False
    assert is_safe_url("JavaScript:alert(1)") == False
    assert is_safe_url("data:text/html,<script>alert(1)</script>") == False
    assert is_safe_url("  javascript:alert(1)") == False
    assert is_safe_url("") == False
    assert is_safe_url(None) == False
    print("[PASS] Link safety tests passed.")
    
    print("[PASS] Internship gate tests passed.")

    # --- Location Gate Tests ---
    print("\nTesting classify_location()...")

    # Inside India every work mode is allowed
    assert classify_location("Bengaluru, India") == "India"
    assert classify_location("Gurugram") == "India"
    assert classify_location("Hybrid - Hyderabad") == "India"
    assert classify_location("Remote (India)") == "India"
    assert classify_location("Mumbai, Maharashtra") == "India"
    assert classify_location("Noida / Pune") == "India"
    assert classify_location("Chennai, Tamil Nadu, IN") == "India"

    # Outside India only fully remote roles survive
    assert classify_location("Remote") == "Remote"
    assert classify_location("Remote - EMEA") == "Remote"
    assert classify_location("Work From Home") == "Remote"
    assert classify_location("Anywhere") == "Remote"

    # Outside India and not remote: rejected
    assert classify_location("New York, NY") is None
    assert classify_location("London, United Kingdom") is None
    assert classify_location("Hybrid - Amsterdam") is None
    assert classify_location("Remote / Hybrid - Berlin") is None
    assert classify_location("Indianapolis, Indiana") is None
    assert classify_location("Singapore") is None
    assert classify_location("") is None
    assert classify_location(None) is None

    assert is_allowed_location("Bengaluru, India") == True
    assert is_allowed_location("Remote - Global") == True
    assert is_allowed_location("San Francisco, CA") == False
    assert is_allowed_location(None) == ALLOW_UNKNOWN_LOCATION

    print("[PASS] Location gate tests passed.")
    
    # --- Domain Classification Tests ---
    print("\nTesting classify_domain()...")
    
    r1 = classify_domain("Accounting Intern", "Cloudflare")
    print(f"  Accounting Intern -> {r1}")
    assert r1 == "Finance"
    
    r2 = classify_domain("Quantitative Researcher", "Citadel")
    print(f"  Quantitative Researcher -> {r2}")
    assert r2 == "Quant"
    
    r3 = classify_domain("UX Researcher", "Airbnb")
    print(f"  UX Researcher -> {r3}")
    assert r3 == "Tech"
    
    r4 = classify_domain("AI Research Fellowship", "Microsoft")
    print(f"  AI Research Fellowship -> {r4}")
    assert r4 == "Research Lab"
    
    r5 = classify_domain("Financial Software Engineer", "")
    print(f"  Financial Software Engineer -> {r5}")
    assert r5 == "Tech"
    
    r6 = classify_domain("Systematic Trading Intern", "Jump Trading")
    print(f"  Systematic Trading Intern -> {r6}")
    assert r6 == "Quant"
    
    r7 = classify_domain("Summer Analyst - Equity Research", "Goldman Sachs")
    print(f"  Summer Analyst - Equity Research -> {r7}")
    assert r7 == "Finance"
    
    r8 = classify_domain("Credit Risk Intern", "BlackRock")
    print(f"  Credit Risk Intern -> {r8}")
    assert r8 == "Finance"
    
    print("[PASS] Domain classification tests passed.")
    
    print("\nAll tests passed successfully.")
