from datetime import date, datetime, timezone

import pytest

from jobwatch.adapters import workday

TODAY = date(2026, 11, 15)
SF = {"name": "Salesforce", "host": "salesforce.wd12.myworkdayjobs.com",
      "tenant": "salesforce", "site": "External_Career_Site", "country": "India"}
SF_COUNTRY_PARAM = "CF_-_REC_-_LRV_-_Job_Posting_Anchor_-_Country_from_Job_Posting_Location_Extended"
INDIA_ID = "c4f78be1a8f14da0ab49ce1162348a5e"


@pytest.fixture(autouse=True)
def no_pacing(monkeypatch):
    monkeypatch.setattr(workday, "REQUEST_GAP", 0)


@pytest.mark.parametrize("text, expected", [
    ("Posted Today", date(2026, 11, 15)),
    ("Posted Yesterday", date(2026, 11, 14)),
    ("Posted 1 Day Ago", date(2026, 11, 14)),
    ("Posted 3 Days Ago", date(2026, 11, 12)),
    ("Posted 30+ Days Ago", None),
    ("", None),
    (None, None),
    ("Something new", None),
])
def test_parse_posted_on(text, expected):
    got = workday.parse_posted_on(text, TODAY)
    assert (got.date() if got else None) == expected
    if got:
        assert got.tzinfo == timezone.utc


def test_country_facet_top_level_salesforce(load_fixture):
    facets = load_fixture("workday_salesforce_unfiltered.json")["facets"]
    assert workday.find_facet_value(facets, "Country", "India") == (SF_COUNTRY_PARAM, INDIA_ID)


def test_country_facet_nested_adobe(load_fixture):
    facets = load_fixture("workday_adobe_unfiltered.json")["facets"]
    assert workday.find_facet_value(facets, "Country", "india") == ("locationCountry", INDIA_ID)


def test_country_facet_missing(load_fixture):
    facets = load_fixture("workday_adobe_unfiltered.json")["facets"]
    assert workday.find_facet_value(facets, "Country", "Atlantis") is None


def test_parse_posting(load_fixture):
    posting = load_fixture("workday_salesforce_india_p0.json")["jobPostings"][0]
    job = workday.parse_posting("Salesforce", SF["host"], SF["site"], posting, TODAY)
    assert job.key == "Salesforce:JR368325"
    assert job.title == "Business Development Representative"
    assert job.location == "India - Bangalore"
    assert job.url.startswith("https://salesforce.wd12.myworkdayjobs.com/External_Career_Site/job/")
    assert job.posted_at == datetime(2026, 11, 14, tzinfo=timezone.utc)



def test_multi_location_uses_path():
    posting = {"title": "T", "externalPath": "/job/India---Hyderabad/Success-Architect_JR352696",
               "locationsText": "3 Locations", "postedOn": "Posted Today"}
    job = workday.parse_posting("Salesforce", SF["host"], SF["site"], posting, TODAY)
    assert job.location == "India - Hyderabad (+2 more)"


@pytest.mark.parametrize("path, expected", [
    ("/job/India---Hyderabad/X_JR1", "India - Hyderabad"),
    ("/job/California---San-Francisco/X_JR1", "California - San Francisco"),
    ("/job/Bangalore/X_R1", "Bangalore"),
    ("/weird", ""),
])
def test_path_location(path, expected):
    assert workday.path_location(path) == expected



def test_repost_suffix_kept_in_key():
    posting = {"title": "T", "externalPath": "/job/X/Escalation-Manager_JR368011-1",
               "locationsText": "India - Bangalore", "postedOn": "Posted Today"}
    job = workday.parse_posting("Salesforce", SF["host"], SF["site"], posting, TODAY)
    assert job.key == "Salesforce:JR368011-1"


def test_fetch_applies_country_facet_and_paginates(monkeypatch, load_fixture):
    unfiltered = load_fixture("workday_salesforce_unfiltered.json")
    pages = [load_fixture("workday_salesforce_india_p0.json"),
             load_fixture("workday_salesforce_india_p1.json")]
    pages[0]["total"] = 40  # pretend there are exactly two pages
    bodies = []

    def fake_post_json(url, body):
        bodies.append(body)
        if not body["appliedFacets"]:
            return unfiltered
        return pages[body["offset"] // workday.PAGE_SIZE]

    monkeypatch.setattr(workday, "post_json", fake_post_json)
    jobs = workday.fetch(SF, today=TODAY)

    assert len(jobs) == 40
    assert bodies[1]["appliedFacets"] == {SF_COUNTRY_PARAM: [INDIA_ID]}
    assert [b["offset"] for b in bodies] == [0, 0, 20]
    assert not any(j.location.endswith("Locations") for j in jobs)
    assert all(j.location.startswith("India") for j in jobs)


def test_fetch_errors_when_country_not_offered(monkeypatch, load_fixture):
    unfiltered = load_fixture("workday_adobe_unfiltered.json")
    monkeypatch.setattr(workday, "post_json", lambda url, body: unfiltered)
    with pytest.raises(LookupError, match="Atlantis"):
        workday.fetch({**SF, "country": "Atlantis"}, today=TODAY)
