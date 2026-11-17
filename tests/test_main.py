import json
from datetime import datetime, timedelta, timezone

import pytest

from jobwatch.__main__ import fetch_all, run
from tests.helpers import job

NOW = datetime(2026, 11, 16, 3, 30, tzinfo=timezone.utc)
CFG = {
    "companies": [{"name": "A", "platform": "ok"}, {"name": "Bad", "platform": "bad"}],
    "filters": {"title_include": ["software engineer"], "title_exclude": ["intern"],
                "locations": {"india": ["india", "hyderabad"]}},
    "first_run": {"lookback_days": 7, "max_digest_size": 100},
}


def _boom(cfg):
    raise RuntimeError("down")


def _adapters(jobs):
    return {"ok": lambda cfg: jobs, "bad": _boom}


JOBS = [job("A:1", posted_at=NOW - timedelta(days=1)),
        job("A:2", posted_at=None),
        job("A:3", title="Software Engineer Intern"),
        job("A:4", location="London")]


def test_one_failure_does_not_stop_others():
    adapters = {"ok": lambda cfg: [job()], "bad": _boom, "empty": lambda cfg: []}
    companies = [{"name": "Bad", "platform": "bad"}, {"name": "A", "platform": "ok"},
                 {"name": "E", "platform": "empty"}, {"name": "U", "platform": "nope"}]
    results, health = fetch_all(companies, adapters)
    assert [c["name"] for c, _ in results] == ["A", "E"]
    assert health == [
        "Bad: error: RuntimeError: down",
        "E: 0 jobs before filtering (adapter may be broken)",
        "U: no adapter for platform 'nope'",
    ]


def test_first_run_end_to_end(tmp_path):
    seen_path = tmp_path / "seen.json"
    issues = []
    run(CFG, seen_path, dry_run=False, adapters=_adapters(JOBS),
        create_issue=lambda t, b: issues.append((t, b)) or "url", now=NOW)

    (title, body), = issues
    assert title == "New roles: 2026-11-16 (1)"
    assert "https://x/A:1" in body and "https://x/A:2" not in body
    assert "Bad: error: RuntimeError: down" in body
    # Only filter-passing jobs are stored; the undated one is seeded silently.
    assert json.loads(seen_path.read_text()) == {"A:1": "2026-11-16", "A:2": "2026-11-16"}


def test_second_run_posts_only_new(tmp_path):
    seen_path = tmp_path / "seen.json"
    seen_path.write_text(json.dumps({"A:1": "2026-11-15"}))
    issues = []
    run(CFG, seen_path, dry_run=False, adapters=_adapters(JOBS),
        create_issue=lambda t, b: issues.append(t) or "url", now=NOW)
    assert issues == ["New roles: 2026-11-16 (1)"]
    assert json.loads(seen_path.read_text()) == {"A:1": "2026-11-15", "A:2": "2026-11-16"}


def test_no_issue_when_nothing_new_and_healthy(tmp_path):
    seen_path = tmp_path / "seen.json"
    seen_path.write_text(json.dumps({"A:1": "x", "A:2": "x"}))
    cfg = {**CFG, "companies": CFG["companies"][:1]}
    issues = []
    run(cfg, seen_path, dry_run=False, adapters=_adapters(JOBS),
        create_issue=lambda t, b: issues.append(t), now=NOW)
    assert issues == []


def test_failed_issue_does_not_write_seen(tmp_path):
    seen_path = tmp_path / "seen.json"

    def fail(title, body):
        raise RuntimeError("gh failed")

    with pytest.raises(RuntimeError):
        run(CFG, seen_path, dry_run=False, adapters=_adapters(JOBS), create_issue=fail, now=NOW)
    assert not seen_path.exists()


def test_dry_run_writes_nothing(tmp_path, capsys):
    seen_path = tmp_path / "seen.json"

    def never(title, body):
        raise AssertionError("dry run must not create issues")

    run(CFG, seen_path, dry_run=True, adapters=_adapters(JOBS), create_issue=never, now=NOW)
    out = capsys.readouterr().out
    assert "A: 4 fetched, 2 passed" in out
    assert "Issue title: New roles: 2026-11-16 (1)" in out
    assert not seen_path.exists()


def test_only_requires_dry_run(capsys):
    from jobwatch.__main__ import main
    with pytest.raises(SystemExit):
        main(["--only", "Arcesium"])
    assert "needs --dry-run" in capsys.readouterr().err


def test_only_unknown_company(capsys):
    from jobwatch.__main__ import main
    with pytest.raises(SystemExit):
        main(["--dry-run", "--only", "Nope"])
    assert "no company" in capsys.readouterr().err
