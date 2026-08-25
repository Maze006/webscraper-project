# Internship Discovery Platform

An internship and fellowship aggregator with a hard geographic rule:

> **Only roles based in India, or roles outside India that are fully remote.**

Everything else — on-site or hybrid postings in New York, London, Singapore, Amsterdam — is discarded at scrape time, again before it is written to the database, and once more when the UI reads it back.

Listings are pulled from India-first student boards, big-company career portals and public ATS feeds, classified into four domains (Tech, Finance, Quant, Research Lab), stored in SQLite and browsed through a Streamlit app.

---

## Quick start

```bash
pip install requests beautifulsoup4 streamlit apscheduler pydantic google-genai
```

```bash
python run_real_ingestion.py
```

```bash
streamlit run streamlit_app.py
```

A full ingestion run takes roughly 6-8 minutes, most of it deliberate rate limiting and Workday pagination.

---

## The geography gate

Implemented in `classifier.py` as `classify_location()`, which returns one of three values:

| Result | Meaning | Examples |
| --- | --- | --- |
| `India` | Anywhere in India, any work mode | `Bengaluru, India`, `Gurugram`, `Hybrid - Hyderabad`, `Remote (India)` |
| `Remote` | Fully remote, based outside India | `Remote`, `Remote - EMEA`, `Work From Home` |
| `None` | Discarded | `New York, NY`, `London, United Kingdom`, `Hybrid - Amsterdam` |

Matching is word-boundary regex across the country name, states and around 70 hiring cities, so `Indianapolis, Indiana` is correctly rejected. A hybrid or on-site role outside India still requires showing up abroad, so it does not count as remote. Postings with no usable location string are dropped by default (`ALLOW_UNKNOWN_LOCATION = False`).

The database enforces the same rule with a `CHECK` constraint on `location_type`, and `query_engine.get_opportunities()` filters on it again on every read.

---

## Sources

| Source | Module | How it is read |
| --- | --- | --- |
| **Internshala** | `internshala_scraper.py` | Server-rendered category listing pages |
| **Unstop** | `unstop_scraper.py` | Public search API under `/api/public/` |
| **Workday tenants** | `portal_scraper.py` | `/wday/cxs/{tenant}/{site}/jobs` with per-tenant India facets |
| **Amazon** | `portal_scraper.py` | `amazon.jobs/en/search.json` |
| **Microsoft** | `portal_scraper.py` | `apply.careers.microsoft.com/api/pcsx/search` |
| **Greenhouse / Lever** | `ats_scraper.py` | Public board JSON APIs |
| **Research labs** | `lab_scraper.py` | Page text extracted with Gemini (needs `GEMINI_API_KEY`) |

Internshala and Unstop dominate the results because they are India-only platforms. Both guarantee that every listing is an internship, so they screen on `is_senior_role()` — rejecting senior, full-time and recruiting titles — rather than on the internship-keyword gate that ATS boards need. Work-from-home listings on those two boards are labelled **India**, not foreign-remote, because that is what they are.

### Polite scraping

`http_client.py` centralises this: a real User-Agent, a 1.5 second delay between requests, a 25 second timeout, and three retries with backoff on 429 and 5xx responses.

Both HTML sources are read within their robots.txt rules. Internshala disallows `/api/`, `/internship/search/` and every query-string URL, so only the plain category paths are requested. Unstop explicitly allows `/api/public/`, which is the endpoint used.

### Employers with no public feed

Google, Meta, Apple, Netflix, Goldman Sachs, JPMorgan and Morgan Stanley have no public Greenhouse or Lever board and no reachable JSON API, so they cannot be scraped. Citadel, HRT, Two Sigma, D. E. Shaw and Susquehanna return 404 on Greenhouse. These are recorded as comments in `config.py` so nobody re-adds them expecting results.

---

## Project layout

```
classifier.py            Geography gate, internship gate, domain classifier (run it for tests)
config.py                Board tokens, Workday tenants, category slugs, page limits
http_client.py           Shared rate-limited HTTP session
sources.py               collect_all(): runs every scraper, aggregates, reports

ats_scraper.py           Greenhouse + Lever
internshala_scraper.py   Internshala
unstop_scraper.py        Unstop
portal_scraper.py        Workday + Amazon + Microsoft
lab_scraper.py           Research lab pages via Gemini

database.py              Schema, connection, migrations
query_engine.py          Filtered reads, time-horizon bucketing
run_real_ingestion.py    Full rebuild
scheduler.py             Incremental refresh, every 12 hours
seed_db.py               Mock data for UI work

streamlit_app.py         App entry point, sidebar filters
pages_ui/                Currently Open + Future Pipeline pages
ui_components.py         Cards, pagination, countdown formatting
theme.py                 Glassmorphism theme
```

---

## Usage

Full rebuild from scratch — wipes the table, rebuilds the schema, scrapes everything:

```bash
python run_real_ingestion.py
```

Incremental refresh that keeps existing rows:

```bash
python scheduler.py --run-now
```

Run continuously, refreshing every 12 hours:

```bash
python scheduler.py
```

Scrape only, printing a source / domain / geography breakdown without touching the database:

```bash
python sources.py
```

Run the classifier test suite:

```bash
python classifier.py
```

Replace real data with mock rows for UI work:

```bash
python seed_db.py
```

Launch the UI:

```bash
streamlit run streamlit_app.py
```

The UI has sidebar filters for opportunity type, domain, location (India vs remote-outside-India) and source, with results paginated 24 cards per page.

---

## Database schema

`opportunities.db`, one table:

| Column | Notes |
| --- | --- |
| `company_name`, `role_title` | |
| `opportunity_type` | `Internship` or `Fellowship` |
| `domain` | `Tech`, `Finance`, `Quant`, `Research Lab` |
| `status` | `CURRENT` or `UPCOMING` |
| `application_deadline` | Only Unstop supplies real deadlines; the rest are rolling |
| `program_start_date` | Usually null outside lab listings |
| `location` | Raw location string from the source |
| `location_type` | `India` or `Remote`, enforced by a CHECK constraint |
| `source` | `Internshala`, `Unstop`, `Amazon`, `Microsoft`, `Workday (…)`, `Greenhouse`, `Lever` |
| `apply_url` | Unique; the upsert key |

`database.init_db()` migrates older databases by adding missing columns and deleting rows that predate the geography gate.

---

## Tuning

All in `config.py`:

- `INTERNSHALA_CATEGORIES`, `INTERNSHALA_MAX_PAGES` — 50 listings per page, per category
- `UNSTOP_MAX_PAGES` — 30 listings per page
- `WORKDAY_TARGETS`, `WORKDAY_MAX_PAGES` — display name, tenant, site and host per employer
- `ENABLE_AMAZON`, `ENABLE_MICROSOFT`
- Greenhouse and Lever token lists, grouped by domain

Results skew towards smaller companies because that is what Internshala mostly lists. To weight the mix towards larger employers, raise `UNSTOP_MAX_PAGES` and trim `INTERNSHALA_CATEGORIES`.

---

## Known limits

- **Quant internships in India are close to nonexistent.** Every quant internship found across Jump Trading, Akuna, Point72, WorldQuant, IMC and Flow Traders sits in Chicago, New York, London, Singapore, Amsterdam or Hong Kong, so the gate drops them. Those firms do post India full-time roles; they simply do not post India internships on public boards.
- **Large employers hire interns seasonally.** Citi exposes 834 India jobs with zero internships; Micron 281 with zero. That layer starts paying off around January to March, when summer programmes open.
- **Geo-locked remote roles pass the gate.** `Remote - USA` counts as remote even though it is not practically open to a candidate in India.
- HTML scraping breaks when a site redesigns; the ATS and portal JSON feeds are more stable.
- `GEMINI_API_KEY` is only needed for the research-lab scraper. Without it that source is skipped and everything else runs.
