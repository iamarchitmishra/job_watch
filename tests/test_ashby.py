from datetime import datetime, timezone

from jobwatch.adapters import ashby


def test_parse_thoughtworks(load_fixture):
    jobs = ashby.parse("Thoughtworks", load_fixture("ashby_thoughtworks.json"))
    assert len(jobs) == 75
    assert len({j.key for j in jobs}) == 75

    job = next(j for j in jobs if j.key == "Thoughtworks:2513267d-9a13-4242-843f-6cb248f18c1a")
    assert job.title == "Lead FP&A Analyst"
    assert job.location == "Singapore"
    assert job.url == "https://jobs.ashbyhq.com/thoughtworks/2513267d-9a13-4242-843f-6cb248f18c1a"
    assert job.posted_at == datetime(2026, 10, 27, 8, 20, 52, 918000, tzinfo=timezone.utc)


def test_location_secondary_country_remote():
    p = {"location": "Pune", "secondaryLocations": [{"location": "Bangalore"}],
         "address": {"postalAddress": {"addressCountry": "India"}}, "isRemote": True}
    assert ashby._location(p) == "Pune; Bangalore, India (Remote)"
    assert ashby._location({"location": "Remote", "address": {"postalAddress": {"addressCountry": "India"}}}) == "Remote, India"
    assert ashby._location({"location": "Bangalore, India",
                            "address": {"postalAddress": {"addressCountry": "India"}}}) == "Bangalore, India"


def test_unlisted_postings_are_skipped():
    payload = {"jobs": [{"id": "1", "title": "T", "location": "Pune", "jobUrl": "u", "isListed": False}]}
    assert ashby.parse("X", payload) == []
