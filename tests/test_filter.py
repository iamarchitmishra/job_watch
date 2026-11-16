import pytest

from jobwatch.filter import compile_phrases, filter_jobs, matches_any, title_rules
from tests.helpers import job

FILTERS = {
    "title_include": ["software engineer", "mts", "ml engineer"],
    "title_exclude": ["intern", "staff", "lead"],
    "locations": {"india": ["india", "bengaluru", "hyderabad", "delhi"]},
}


def m(text, *phrases):
    return matches_any(text, compile_phrases(phrases))


@pytest.mark.parametrize("text, phrase, expected", [
    ("Software Engineer Intern", "intern", True),
    ("Software Engineer, Internal Tools", "intern", False),
    ("International Payments", "intern", False),
    ("SMTS/LMTS", "smts", True),
    ("Developer SMTS / LMTS", "lmts", True),
    ("SMTS", "mts", False),
    ("software  engineer", "software engineer", True),
    ("Software Engineer", "software engineer", True),
    ("Software Engineering", "software engineer", False),
    ("Indiana - Indianapolis", "india", False),
    ("New Delhi, India", "delhi", True),
])
def test_whole_word_matching(text, phrase, expected):
    assert m(text, phrase) is expected


@pytest.mark.parametrize("title, location, passes", [
    ("Software Engineer", "Bengaluru; Gurugram; Hyderabad", True),
    ("Senior Software Engineer", "Remote, India", True),
    ("Software Engineer", "Remote - US", False),
    ("Software Engineer", "Remote", False),
    ("Software Engineer", "Indiana - Indianapolis", False),
    ("Software Engineer Intern", "Hyderabad", False),
    ("Staff Software Engineer", "Hyderabad", False),       # exclude beats include
    ("Product Manager", "Hyderabad", False),
    ("Software Engineer, Internal Tools", "Hyderabad", True),
])
def test_filter_global_rules(title, location, passes):
    kept = filter_jobs([job(title=title, location=location)], FILTERS, {"name": "A"})
    assert bool(kept) is passes


def test_company_filters_adjust_global_lists():
    company = {"name": "Salesforce", "filters": {
        "title_include_add": ["smts"], "title_exclude_add": ["pmts"],
        "title_exclude_remove": ["staff"]}}
    include, exclude = title_rules(FILTERS, company)
    assert include == ["software engineer", "mts", "ml engineer", "smts"]
    assert exclude == ["intern", "lead", "pmts"]

    titles = ["Data Engineering SMTS/LMTS", "Senior Member of Technical Staff MTS",
              "Software Engineering PMTS", "LMTS Agentic AP/Invoicing", "LMTS - Lead ML Engineer"]
    kept = filter_jobs([job(key=f"S:{i}", title=t) for i, t in enumerate(titles)], FILTERS, company)
    assert [j.title for j in kept] == titles[:2]


def test_company_filters_do_not_leak_to_other_companies():
    salesforce = {"name": "S", "filters": {"title_exclude_remove": ["staff"]}}
    staff = [job(title="Staff Software Engineer")]
    assert filter_jobs(staff, FILTERS, salesforce)
    assert not filter_jobs(staff, FILTERS, {"name": "Other"})


def test_repo_config_with_real_titles(load_fixture):
    """The real config against real fixture titles."""
    from jobwatch.adapters import greenhouse, smartrecruiters
    from jobwatch.config import load_config

    cfg = load_config("config.yaml")
    by_name = {c["name"]: c for c in cfg["companies"]}

    arcesium = greenhouse.parse("Arcesium", load_fixture("greenhouse_arcesiumllc.json"))
    kept = filter_jobs(arcesium, cfg["filters"], by_name["Arcesium"])
    assert [j.title for j in kept] == ["Software Engineer III - Linux & AWS"]

    snow = smartrecruiters.parse("ServiceNow", "ServiceNow",
                                 load_fixture("smartrecruiters_servicenow_india.json")["content"])
    titles = {j.title for j in filter_jobs(snow, cfg["filters"], by_name["ServiceNow"])}
    assert "Applications Dev Engineer" in titles        # title has a non-breaking space upstream
    assert "Sr Software Engineer" in titles
    assert not any("Staff" in t for t in titles)
