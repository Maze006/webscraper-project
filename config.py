# Configuration for ATS Endpoints grouped by platform and domain

# --- GREENHOUSE BOARDS ---
# Endpoint: https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true

QUANT_GREENHOUSE_TOKENS = [
    "janestreet",
    "optiver",
    "akunacapital",
    "jumptrading",
    "point72",
    "worldquant",   # has Mumbai / Bengaluru / New Delhi offices
    "imc",          # has a Mumbai office
    "flowtraders",
]

# Verified 2026-08-24 as having no public Greenhouse/Lever JSON board: these
# firms run their own careers portals or Workday, so an ATS scraper cannot see
# them. Left here so nobody re-adds them expecting results.
#   Greenhouse 404: twosigma, citadel, hrt, deshaw, susquehanna, blackrock, plaid
#   Lever 404:      kpmg-us, yelp, twitch
#   No public board at all: google, microsoft, amazon, meta, apple, netflix,
#                           goldmansachs, jpmorgan, morganstanley, de shaw india

FINANCE_GREENHOUSE_TOKENS = [
    "stripe",
    "robinhood",
    "coinbase",
    "brex",
    "chime",
    "affirm",
]

TECH_GREENHOUSE_TOKENS = [
    "canonical",
    "figma",
    "cloudflare",
    "databricks",
    "discord",
    "airbnb",
    "duolingo",
    "lyft",
]

# --- INDIA-FOCUSED BOARDS ---
# Employers that hire in India. The geography gate in classifier.py still
# filters every posting, so non-Indian roles on these boards are only kept
# when they are fully remote.

INDIA_GREENHOUSE_TOKENS = [
    "postman",
    "druva",
    "zetaglobal",
    "phonepe",
    "groww",
    "turing",
    "slice",
    "highradius",
    "sigmoid",
    "mongodb",
    "samsara",
    "mixpanel",
    "amplitude",
    "branch",
    "elastic",
    "asana",
]

# Remote-first employers: their non-Indian postings only survive the gate when
# the role itself is fully remote.
REMOTE_FIRST_GREENHOUSE_TOKENS = [
    "gitlab",
    "twilio",
    "dropbox",
]

# Combined Greenhouse list for easy iteration
ALL_GREENHOUSE_TARGETS = (
    QUANT_GREENHOUSE_TOKENS
    + FINANCE_GREENHOUSE_TOKENS
    + TECH_GREENHOUSE_TOKENS
    + INDIA_GREENHOUSE_TOKENS
    + REMOTE_FIRST_GREENHOUSE_TOKENS
)

INDIA_LEVER_TOKENS = [
    "cred",
    "zeta",
    "meesho",
    "mindtickle",
    "paytm",
    "porter",
]

# --- LEVER BOARDS ---
# Endpoint: https://api.lever.co/v0/postings/{token}?mode=json

LEVER_TOKENS = [
    "palantir",
] + INDIA_LEVER_TOKENS

# --- INDIA-FIRST JOB BOARDS (non-ATS) ---
# Internshala and Unstop are India-only student platforms and are by far the
# highest yield sources for this project.
#
# Internshala: only the server rendered category listing pages are read. Its
# robots.txt disallows /api/, /internship/search/ and any query-string URL, so
# none of those are touched. Category slugs below all return HTTP 200.

INTERNSHALA_CATEGORIES = [
    "computer-science-internship",
    "software-development-internship",
    "data-science-internship",
    "machine-learning-internship",
    "analytics-internship",
    "finance-internship",
    "web-development-internship",
    "product-management-internship",
]

INTERNSHALA_MAX_PAGES = 3      # 50 listings per page, per category

# Unstop's robots.txt explicitly allows /api/public/*, which is the endpoint used.
UNSTOP_MAX_PAGES = 8           # 30 listings per page

# --- WORKDAY TENANTS ---
# The large employers that never appear on Greenhouse or Lever. Each entry is
# (display name, tenant, site, workday host). Verified live on 2026-08-24.
# India location facets are discovered per tenant at runtime.

WORKDAY_TARGETS = [
    ("NVIDIA",     "nvidia",     "NVIDIAExternalCareerSite", "wd5"),
    ("Adobe",      "adobe",      "external_experienced",     "wd5"),
    ("HPE",        "hpe",        "Jobsathpe",                "wd5"),
    ("Micron",     "micron",     "External",                 "wd1"),
    ("Citi",       "citi",       "2",                        "wd5"),
    ("Mastercard", "mastercard", "CorporateCareers",         "wd1"),
    ("Autodesk",   "autodesk",   "Ext",                      "wd1"),
    ("Salesforce", "salesforce", "External_Career_Site",     "wd12"),
]

# Pages of 20 postings to read per tenant once the India facet is applied.
WORKDAY_MAX_PAGES = 25

# Amazon and Microsoft run their own portals rather than Workday.
ENABLE_AMAZON = True
ENABLE_MICROSOFT = True
