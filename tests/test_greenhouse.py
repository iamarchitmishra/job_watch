from datetime import datetime, timezone

from jobwatch.adapters import greenhouse


def test_parse_arcesium(load_fixture):
    jobs = greenhouse.parse("Arcesium", load_fixture("greenhouse_arcesiumllc.json"))
    assert len(jobs) == 40
    assert len({j.key for j in jobs}) == 40

    job = next(j for j in jobs if j.key == "Arcesium:5257251007")
    assert job.company == "Arcesium"
    assert job.title == "AI Transformation Intern"
    assert job.location == "New York"
    assert job.url == "https://job-boards.greenhouse.io/arcesiumllc/jobs/5257251007"
    # first_published "2026-11-11T13:13:22-05:00", converted to UTC
    assert job.posted_at == datetime(2026, 11, 11, 18, 13, 22, tzinfo=timezone.utc)


def test_titles_are_stripped(load_fixture):
    jobs = greenhouse.parse("Arcesium", load_fixture("greenhouse_arcesiumllc.json"))
    assert all(j.title == j.title.strip() for j in jobs)


def test_missing_first_published_gives_none():
    payload = {"jobs": [{"id": 1, "title": "T", "location": {"name": "X"},
                         "absolute_url": "u", "first_published": None}]}
    assert greenhouse.parse("C", payload)[0].posted_at is None
