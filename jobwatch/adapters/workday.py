"""Workday CXS job search API.

- POST {base}/jobs, `limit` max 20, paginate with `offset`.
- `total` is only reliable on the first page (later pages return 0).
- Server-side narrowing: most tenants expose a country facet (named
  "Country", "Country / Territory", "Location Country"...; the facetParameter
  differs per tenant and may be nested under locationMainGroup). Tenants
  without one (e.g. Intel) have a "Locations" facet with values like
  "India, Bangalore"; then every location value naming the country is used.
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
        found = find_country_filter(first.get("facets") or [], country)
        if found is None:
            raise LookupError(f"no '{country}' value in a country or locations facet")
        param, value_ids = found
        applied = {param: value_ids}
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


def find_country_filter(facets, country):
    """Return (facetParameter, [value ids]) that narrows results to `country`,
    or None. Prefers a country facet with an exact value; falls back to a
    locations facet, selecting every value that names the country."""
    flat = list(_all_facets(facets))
    for facet in flat:
        if "country" in (facet.get("descriptor") or "").lower():
            for v in facet.get("values") or []:
                if (v.get("descriptor") or "").strip().lower() == country.lower():
                    return facet["facetParameter"], [v["id"]]
    word = re.compile(rf"(?<!\w){re.escape(country)}(?!\w)", re.IGNORECASE)
    for facet in flat:
        if "location" in (facet.get("descriptor") or facet.get("facetParameter") or "").lower():
            ids = [v["id"] for v in facet.get("values") or []
                   if "id" in v and word.search(v.get("descriptor") or "")]
            if ids:
                return facet["facetParameter"], ids
    return None


def _all_facets(facets):
    for facet in facets:
        yield facet
        nested = [v for v in facet.get("values") or [] if "facetParameter" in v]
        yield from _all_facets(nested)


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
