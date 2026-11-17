from datetime import datetime, timezone

from jobwatch.adapters import lever


def test_parse_cred(load_fixture):
    jobs = lever.parse("CRED", load_fixture("lever_cred.json"))
    assert len(jobs) == 15
    assert len({j.key for j in jobs}) == 15

    job = next(j for j in jobs if j.title == "threat detection engineer")
    assert job.key.startswith("CRED:")
    assert job.location == "bengaluru"
    assert job.url.startswith("https://jobs.lever.co/cred/")
    assert job.posted_at == datetime.fromtimestamp(1769676707323 / 1000, tz=timezone.utc)


def test_location_multiple_and_remote():
    p = {"workplaceType": "remote",
         "categories": {"location": "Bangalore", "allLocations": ["Bangalore", "Pune"]}}
    assert lever._location(p) == "Bangalore; Pune (Remote)"
    assert lever._location({"categories": {"location": "Gurugram"}}) == "Gurugram"
    assert lever._location({"workplaceType": "remote", "categories": {}}) == "Remote"


def test_fetch_uses_region_and_mode(monkeypatch):
    calls = []
    monkeypatch.setattr(lever, "get_json", lambda url, params=None: calls.append((url, params)) or [])
    lever.fetch({"name": "X", "slug": "acme", "region": "eu"})
    assert calls == [("https://api.eu.lever.co/v0/postings/acme", {"mode": "json"})]
