"""Lever postings API. One call returns every published posting.

Posting date: `createdAt` (epoch milliseconds). Lever has no separate publish
date in this API, so this is when the posting was created.
Some boards live on the EU instance; set `region: eu` in config for those.
"""
from datetime import datetime, timezone

from jobwatch.http import get_json
from jobwatch.models import Job, clean

URLS = {
    "global": "https://api.lever.co/v0/postings/{slug}",
    "eu": "https://api.eu.lever.co/v0/postings/{slug}",
}


def fetch(company_cfg):
    url = URLS[company_cfg.get("region", "global")].format(slug=company_cfg["slug"])
    return parse(company_cfg["name"], get_json(url, params={"mode": "json"}))


def parse(company, postings):
    return [
        Job(
            key=f"{company}:{p['id']}",
            company=company,
            title=clean(p["text"]),
            location=_location(p),
            url=p["hostedUrl"],
            posted_at=_parse_ms(p.get("createdAt")),
        )
        for p in postings
    ]


def _location(posting):
    categories = posting.get("categories") or {}
    locations = categories.get("allLocations") or [categories.get("location")]
    text = "; ".join(clean(loc) for loc in locations if loc)
    if posting.get("workplaceType") == "remote" and "remote" not in text.lower():
        text = f"{text} (Remote)" if text else "Remote"
    return text


def _parse_ms(value):
    if not value:
        return None
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
