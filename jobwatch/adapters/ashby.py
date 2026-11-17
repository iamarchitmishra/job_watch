"""Ashby public job board API. One call returns every listed posting.

Posting date: `publishedAt`.
"""
from datetime import datetime, timezone

from jobwatch.http import get_json
from jobwatch.models import Job, clean

URL = "https://api.ashbyhq.com/posting-api/job-board/{board}"


def fetch(company_cfg):
    payload = get_json(URL.format(board=company_cfg["board"]), params={"includeCompensation": "false"})
    return parse(company_cfg["name"], payload)


def parse(company, payload):
    return [
        Job(
            key=f"{company}:{p['id']}",
            company=company,
            title=clean(p["title"]),
            location=_location(p),
            url=p["jobUrl"],
            posted_at=_parse_dt(p.get("publishedAt")),
        )
        for p in payload.get("jobs") or []
        if p.get("isListed", True)
    ]


def _location(posting):
    names = [posting.get("location")]
    names += [s.get("location") for s in posting.get("secondaryLocations") or []]
    text = "; ".join(clean(n) for n in names if n)
    country = (((posting.get("address") or {}).get("postalAddress")) or {}).get("addressCountry")
    if country and country.lower() not in text.lower():
        text = f"{text}, {country}" if text else country
    remote = posting.get("isRemote") or (posting.get("workplaceType") or "").lower() == "remote"
    if remote and "remote" not in text.lower():
        text = f"{text} (Remote)" if text else "Remote"
    return text


def _parse_dt(value):
    if not value:
        return None
    return datetime.fromisoformat(value).astimezone(timezone.utc)
