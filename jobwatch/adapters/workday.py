"""Workday CXS job search API.

- POST {base}/jobs, `limit` max 20, paginate with `offset`.
- `total` is only reliable on the first page (later pages return 0).
- Server-side narrowing: each tenant exposes a facet whose descriptor is
  "Country" (the facetParameter name differs per tenant, and it may be nested
  under locationMainGroup). We look it up from the first response.
- Multi-location postings list `locationsText` as e.g. "2 Locations". We use
  the primary location from the URL path instead, e.g. "India - Hyderabad
  (+1 more)". (Fetching each job's detail gave the full list but tripped the
  rate limit; see below.)

Posting date: only the relative `postedOn` string ("Posted Today",
"Posted Yesterday", "Posted 3 Days Ago"). "Posted 30+ Days Ago" is not precise,
so it maps to None. Dates are day-granular (midnight UTC).

Workday rate-limits bursts (429 after ~4 quick requests), so requests are
spaced out by REQUEST_GAP seconds; jobwatch.http retries 429s.
"""
import re
import time as clock
from datetime import datetime, time, timedelta, timezone

from jobwatch import http
from jobwatch.models import Job, clean

PAGE_SIZE = 20
REQUEST_GAP = 1.0  # seconds between requests to one tenant
MAX_PAGES = 50
MULTI_LOCATION = re.compile(r"^(\d+) Locations$")
DAYS_AGO = re.compile(r"^Posted (\d+) Days? Ago$")


def fetch(company_cfg, today=None):
    host, tenant, site = company_cfg["host"], company_cfg["tenant"], company_cfg["site"]
    base = f"https://{host}/wday/cxs/{tenant}/{site}"
    today = today or datetime.now(timezone.utc).date()

    first = post_json(f"{base}/jobs", _body({}, 0))
    applied = {}
    country = company_cfg.get("country")
    if country:
        facet = find_facet_value(first.get("facets") or [], "Country", country)
        if facet is None:
            raise LookupError(f"no '{country}' value in a 'Country' facet")
        param, value_id = facet
        applied = {param: [value_id]}
        first = post_json(f"{base}/jobs", _body(applied, 0))

    total = first.get("total", 0)
    postings = list(first.get("jobPostings") or [])
    offset = PAGE_SIZE
    for _ in range(MAX_PAGES):
        if offset >= total:
            break
        page = post_json(f"{base}/jobs", _body(applied, offset)).get("jobPostings") or []
        if not page:
            break
        postings.extend(page)
        offset += PAGE_SIZE

    jobs, seen = [], set()
    for posting in postings:
        job = parse_posting(company_cfg["name"], host, site, posting, today)
        if job.key not in seen:  # listings can shift between pages
            seen.add(job.key)
            jobs.append(job)
    return jobs


def post_json(url, body):
    clock.sleep(REQUEST_GAP)
    return http.post_json(url, body)


def find_facet_value(facets, facet_descriptor, value_descriptor):
    """Return (facetParameter, value id) for the first facet named
    `facet_descriptor` holding a value named `value_descriptor`. Searches
    nested facet groups. Case-insensitive."""
    for facet in facets:
        values = facet.get("values") or []
        if (facet.get("descriptor") or "").lower() == facet_descriptor.lower():
            for v in values:
                if (v.get("descriptor") or "").lower() == value_descriptor.lower():
                    return facet["facetParameter"], v["id"]
        nested = [v for v in values if "facetParameter" in v]
        found = find_facet_value(nested, facet_descriptor, value_descriptor)
        if found:
            return found
    return None


def parse_posting(company, host, site, posting, today):
    path = posting["externalPath"]
    location = posting.get("locationsText") or ""
    multi = MULTI_LOCATION.match(location)
    if multi:
        location = f"{path_location(path)} (+{int(multi.group(1)) - 1} more)"
    return Job(
        key=f"{company}:{path.rsplit('_', 1)[-1]}",
        company=company,
        title=clean(posting["title"]),
        location=clean(location),
        url=f"https://{host}/{site}{path}",
        posted_at=parse_posted_on(posting.get("postedOn"), today),
    )


def path_location(path):
    """Primary location from an externalPath like
    "/job/India---Hyderabad/Some-Title_JR1" -> "India - Hyderabad"."""
    parts = path.strip("/").split("/")
    segment = parts[1] if len(parts) > 2 and parts[0] == "job" else ""
    return " - ".join(p.replace("-", " ").strip() for p in segment.split("---"))


def parse_posted_on(text, today):
    text = (text or "").strip()
    if text == "Posted Today":
        days = 0
    elif text == "Posted Yesterday":
        days = 1
    elif m := DAYS_AGO.match(text):
        days = int(m.group(1))
    else:  # "Posted 30+ Days Ago", missing, or unknown format
        return None
    return datetime.combine(today - timedelta(days=days), time(), tzinfo=timezone.utc)


def _body(applied, offset):
    return {"appliedFacets": applied, "limit": PAGE_SIZE, "offset": offset, "searchText": ""}
