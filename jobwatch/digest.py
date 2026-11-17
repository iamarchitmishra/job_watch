"""Decide what is new, and render the GitHub issue."""
from dataclasses import dataclass, field
from datetime import timedelta

MAX_BODY = 60_000  # GitHub caps issue bodies at 65,536 characters


@dataclass
class Plan:
    post: list = field(default_factory=list)       # jobs to show in the digest
    seed: list = field(default_factory=list)       # jobs to add to seen.json (includes `post`)
    baseline: list = field(default_factory=list)   # newly tracked companies seeded silently
    baseline_count: int = 0                        # how many jobs those companies had


def plan_run(passed, seen, now, first_run_cfg):
    """Pick the jobs to post and the jobs to remember.

    A company with no keys in seen.json yet (the very first run, a company just
    added to config, or a renamed one) gets first-run treatment: only jobs
    posted in the last `lookback_days` are shown, the rest are remembered
    silently. If those recent jobs exceed `max_digest_size`, they are all
    remembered silently and the digest just says the baseline was seeded.
    """
    unique = {}
    for job in passed:
        unique.setdefault(job.key, job)
    new = [job for key, job in unique.items() if key not in seen]

    tracked = {key.split(":", 1)[0] for key in seen}
    known = [job for job in new if job.company in tracked]
    first_seen = [job for job in new if job.company not in tracked]

    cutoff = now - timedelta(days=first_run_cfg.get("lookback_days", 7))
    recent = [job for job in first_seen if job.posted_at and job.posted_at >= cutoff]
    if len(recent) > first_run_cfg.get("max_digest_size", 100):
        companies = sorted({job.company for job in first_seen})
        return Plan(post=known, seed=new, baseline=companies, baseline_count=len(first_seen))
    return Plan(post=known + recent, seed=new)


def build_issue(plan, health, today, company_order):
    """Return (title, body), or None when there is nothing to report."""
    if not plan.post and not plan.baseline and not health:
        return None

    sections = []
    if plan.baseline and not plan.post:
        title = f"Baseline seeded: {plan.baseline_count} roles tracked"
    else:
        title = f"New roles: {today.isoformat()} ({len(plan.post)})"
        sections.append(_jobs_markdown(plan.post, company_order) if plan.post else "No new roles.")
    if plan.baseline:
        sections.append(
            f"## Baseline\nStarted tracking {', '.join(plan.baseline)}: "
            f"{plan.baseline_count} matching roles recorded silently (too many recent ones "
            f"to list). From the next run, only new roles show up here.")
    if health:
        sections.append("## Health\n" + "\n".join(f"- {line}" for line in health))

    body = "\n\n".join(sections)
    if len(body) > MAX_BODY:
        body = body[:MAX_BODY] + "\n\n…(truncated)"
    return title, body


def _jobs_markdown(jobs, company_order):
    rank = {name: i for i, name in enumerate(company_order)}
    by_company = {}
    for job in jobs:
        by_company.setdefault(job.company, []).append(job)

    parts = []
    for company in sorted(by_company, key=lambda c: rank.get(c, len(rank))):
        lines = [f"## {company}"]
        for job in sorted(by_company[company], key=lambda j: j.title.lower()):
            posted = f" · posted {job.posted_at.date().isoformat()}" if job.posted_at else ""
            lines.append(f"- [{_escape(job.title)}]({job.url}) · {job.location}{posted}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def _escape(text):
    return text.replace("[", "\\[").replace("]", "\\]")
