"""Title + location rules from config.yaml. Case-insensitive, whole-word.

A "word" is letters and digits only, so "Lead_ Vice President" still
matches `lead` (underscores and punctuation are boundaries).
"""
import re

EDGE_BEFORE = r"(?<![^\W_])"  # previous char is not a letter/digit
EDGE_AFTER = r"(?![^\W_])"    # next char is not a letter/digit


def compile_phrases(phrases):
    patterns = []
    for phrase in phrases or []:
        words = str(phrase).split()
        if words:
            body = r"\s+".join(re.escape(w) for w in words)
            patterns.append(re.compile(EDGE_BEFORE + body + EDGE_AFTER, re.IGNORECASE))
    return patterns


def matches_any(text, patterns):
    return any(p.search(text or "") for p in patterns)


def title_rules(filters, company):
    """Global title lists adjusted by the company's optional `filters` block."""
    own = company.get("filters") or {}
    include = list(filters.get("title_include") or []) + list(own.get("title_include_add") or [])
    remove = {str(p).lower() for p in own.get("title_exclude_remove") or []}
    exclude = [p for p in filters.get("title_exclude") or [] if str(p).lower() not in remove]
    exclude += list(own.get("title_exclude_add") or [])
    return include, exclude


def location_aliases(filters):
    return [alias for aliases in (filters.get("locations") or {}).values() for alias in aliases]


def filter_jobs(jobs, filters, company):
    include, exclude = title_rules(filters, company)
    include, exclude = compile_phrases(include), compile_phrases(exclude)
    locations = compile_phrases(location_aliases(filters))
    return [
        job for job in jobs
        if matches_any(job.title, include)
        and not matches_any(job.title, exclude)
        and matches_any(job.location, locations)
    ]
