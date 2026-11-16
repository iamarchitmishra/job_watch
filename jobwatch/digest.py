"""Decide what is new, and render the GitHub issue."""
from dataclasses import dataclass, field
from datetime import timedelta

MAX_BODY = 60_000  # GitHub caps issue bodies at 65,536 characters


@dataclass
class Plan:
    post: list = field(default_factory=list)  # jobs to show in the digest
    seed: list = field(default_factory=list)  # jobs to add to seen.json (includes `post`)
    baseline: bool = False                    # first run with too many recent jobs


def plan_run(passed, seen, now, first_run_cfg):
    unique = {}
    for job in passed:
        unique.setdefault(job.key, job)
    new = [job for key, job in unique.items() if key not in seen]
    if seen:
        return Plan(post=new, seed=new)

    # First run: only recent jobs are worth showing; everything else is seeded silently.
    cutoff = now - timedelta(days=first_run_cfg.get("lookback_days", 7))
    recent = [job for job in new if job.posted_at and job.posted_at >= cutoff]
    if len(recent) > first_run_cfg.get("max_digest_size", 100):
        return Plan(post=[], seed=new, baseline=True)
    return Plan(post=recent, seed=new)


def build_issue(plan, health, today, company_order):
    """Return (title, body), or None when there is nothing to report."""
    if not plan.post and not plan.baseline and not health:
        return None

    if plan.baseline:
        title = f"Baseline seeded: {len(plan.seed)} roles tracked"
        sections = [f"{title}. First run: too many recent matches to list, so all were "
                    f"recorded silently. From tomorrow, only new roles show up here."]
    else:
        title = f"New roles: {today.isoformat()} ({len(plan.post)})"
        sections = [_jobs_markdown(plan.post, company_order)] if plan.post else ["No new roles."]

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
