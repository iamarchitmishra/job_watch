"""SmartRecruiters public postings API. Paginated; supports `country` (ISO
alpha-2) filtering server-side.

Posting date: `releasedDate`.
"""
from datetime import datetime, timezone

from jobwatch.http import get_json
from jobwatch.models import Job, clean

URL = "https://api.smartrecruiters.com/v1/companies/{company_id}/postings"
PUBLIC_URL = "https://jobs.smartrecruiters.com/{company_id}/{id}"
PAGE_SIZE = 100
MAX_PAGES = 50


def fetch(company_cfg):
    company_id = company_cfg["company_id"]
    params = {"limit": PAGE_SIZE, "offset": 0}
    if company_cfg.get("country"):
        params["country"] = company_cfg["country"]

    postings = []
    for _ in range(MAX_PAGES):
        page = get_json(URL.format(company_id=company_id), params=params)
        content = page.get("content") or []
        postings.extend(content)
        params["offset"] += PAGE_SIZE
        if not content or params["offset"] >= page.get("totalFound", 0):
            break
    return parse(company_cfg["name"], company_id, postings)


def parse(company, company_id, postings):
    return [
        Job(
            key=f"{company}:{p['id']}",
            company=company,
            title=clean(p["name"]),
            location=_location(p.get("location") or {}),
            url=PUBLIC_URL.format(company_id=company_id, id=p["id"]),
            posted_at=_parse_dt(p.get("releasedDate")),
        )
        for p in postings
    ]


def _location(loc):
    # fullLocation looks like "Hyderabad, , India"; drop the empty parts.
    parts = [clean(part) for part in (loc.get("fullLocation") or "").split(",")]
    text = ", ".join(part for part in parts if part)
    if loc.get("remote") and "remote" not in text.lower():
        text = f"{text} (Remote)" if text else "Remote"
    return text


def _parse_dt(value):
    if not value:
        return None
    return datetime.fromisoformat(value).astimezone(timezone.utc)
