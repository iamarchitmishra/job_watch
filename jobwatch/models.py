from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Job:
    key: str  # "{company}:{platform_job_id}", the dedupe key
    company: str
    title: str
    location: str
    url: str
    posted_at: datetime | None  # timezone-aware UTC, or None if the platform doesn't say


def clean(text):
    """Collapse all whitespace (including non-breaking spaces) to single spaces."""
    return " ".join((text or "").split())
