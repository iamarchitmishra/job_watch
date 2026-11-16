from datetime import datetime, timezone

from jobwatch.adapters import smartrecruiters

FIXTURE = "smartrecruiters_servicenow_india.json"


def test_parse_servicenow(load_fixture):
    postings = load_fixture(FIXTURE)["content"]
    jobs = smartrecruiters.parse("ServiceNow", "ServiceNow", postings)
    assert len(jobs) == 80
    assert all("India" in j.location for j in jobs)

    job = next(j for j in jobs if j.key == "ServiceNow:744000161370789")
    assert job.title == "Staff Software Engineer, AI Native Engineering, Integrations"
    assert job.location == "Hyderabad, India"  # "Hyderabad, , India" cleaned
    assert job.url == "https://jobs.smartrecruiters.com/ServiceNow/744000161370789"
    assert job.posted_at == datetime(2026, 11, 12, 19, 24, 59, 688000, tzinfo=timezone.utc)


def test_remote_flag_is_shown():
    loc = {"fullLocation": "Pune, , India", "remote": True}
    assert smartrecruiters._location(loc) == "Pune, India (Remote)"


def test_fetch_paginates_and_sends_country(monkeypatch, load_fixture):
    content = load_fixture(FIXTURE)["content"]
    calls = []

    def fake_get_json(url, params=None):
        calls.append(dict(params))
        start = params["offset"]
        return {"totalFound": len(content), "content": content[start:start + params["limit"]]}

    monkeypatch.setattr(smartrecruiters, "PAGE_SIZE", 30)
    monkeypatch.setattr(smartrecruiters, "get_json", fake_get_json)
    jobs = smartrecruiters.fetch({"name": "ServiceNow", "company_id": "ServiceNow", "country": "in"})
    assert len(jobs) == 80
    assert [c["offset"] for c in calls] == [0, 30, 60]
    assert all(c["country"] == "in" for c in calls)
