"""Greenhouse job board API. One call returns every job on the board.

Posting date: `first_published`. (`updated_at` changes on any edit, including
bulk edits, so it is not a posting date.)
"""
from datetime import datetime, timezone

from jobwatch.http import get_json
from jobwatch.models import Job, clean

URL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"


def fetch(company_cfg):
    payload = get_json(URL.format(token=company_cfg["token"]))
    return parse(company_cfg["name"], payload)


def parse(company, payload):
    return [
        Job(
            key=f"{company}:{j['id']}",
            company=company,
            title=clean(j["title"]),
            location=clean((j.get("location") or {}).get("name")),
            url=j["absolute_url"],
            posted_at=_parse_dt(j.get("first_published")),
        )
        for j in payload["jobs"]
    ]


def _parse_dt(value):
    if not value:
        return None
    return datetime.fromisoformat(value).astimezone(timezone.utc)
