from datetime import date, datetime, timedelta, timezone

from jobwatch.digest import MAX_BODY, Plan, build_issue, plan_run
from tests.helpers import job

NOW = datetime(2026, 11, 16, 3, 30, tzinfo=timezone.utc)
FIRST_RUN = {"lookback_days": 7, "max_digest_size": 3}


def days_ago(n):
    return NOW - timedelta(days=n)


def test_normal_run_posts_only_unseen():
    jobs = [job("A:1"), job("A:2"), job("A:2")]
    plan = plan_run(jobs, {"A:1": "2026-11-01"}, NOW, FIRST_RUN)
    assert [j.key for j in plan.post] == ["A:2"]
    assert [j.key for j in plan.seed] == ["A:2"]
    assert not plan.baseline


def test_normal_run_posts_new_jobs_regardless_of_age():
    plan = plan_run([job("A:1", posted_at=None), job("A:2", posted_at=days_ago(90))],
                    {"A:0": "2026-11-01"}, NOW, FIRST_RUN)
    assert [j.key for j in plan.post] == ["A:1", "A:2"]


def test_first_run_posts_recent_and_seeds_rest_silently():
    jobs = [job("A:1", posted_at=days_ago(1)), job("A:2", posted_at=days_ago(30)),
            job("A:3", posted_at=None), job("A:4", posted_at=days_ago(7))]
    plan = plan_run(jobs, {}, NOW, FIRST_RUN)
    assert [j.key for j in plan.post] == ["A:1", "A:4"]
    assert [j.key for j in plan.seed] == ["A:1", "A:2", "A:3", "A:4"]
    assert not plan.baseline


def test_first_run_too_many_recent_seeds_baseline():
    jobs = [job(f"A:{i}", posted_at=days_ago(1)) for i in range(4)] + [job("A:old")]
    plan = plan_run(jobs, {}, NOW, FIRST_RUN)
    assert plan.baseline == ["A"] and plan.post == [] and len(plan.seed) == 5

    title, body = build_issue(plan, [], NOW.date(), ["A"])
    assert title == "Baseline seeded: 5 roles tracked"


def test_new_company_gets_first_run_treatment():
    seen = {"A:1": "2026-11-01"}
    jobs = [job("A:2", posted_at=days_ago(60)),                    # known company: always posted
            job("B:1", company="B", posted_at=days_ago(2)),        # new company, recent: posted
            job("B:2", company="B", posted_at=days_ago(60)),       # new company, old: silent
            job("B:3", company="B", posted_at=None)]               # new company, undated: silent
    plan = plan_run(jobs, seen, NOW, FIRST_RUN)
    assert [j.key for j in plan.post] == ["A:2", "B:1"]
    assert [j.key for j in plan.seed] == ["A:2", "B:1", "B:2", "B:3"]
    assert plan.baseline == []


def test_new_company_with_too_many_recent_is_baselined_alongside_normal_digest():
    jobs = [job("A:2")] + [job(f"B:{i}", company="B", posted_at=days_ago(1)) for i in range(4)]
    plan = plan_run(jobs, {"A:1": "x"}, NOW, FIRST_RUN)
    assert [j.key for j in plan.post] == ["A:2"]
    assert len(plan.seed) == 5 and plan.baseline == ["B"] and plan.baseline_count == 4

    title, body = build_issue(plan, [], NOW.date(), ["A", "B"])
    assert title == "New roles: 2026-11-16 (1)"
    assert "## Baseline\nStarted tracking B: 4 matching roles recorded silently" in body


def test_no_issue_when_nothing_new_and_healthy():
    assert build_issue(Plan(), [], NOW.date(), []) is None


def test_health_only_issue():
    title, body = build_issue(Plan(), ["Stripe: error: Timeout"], NOW.date(), [])
    assert title == "New roles: 2026-11-16 (0)"
    assert "## Health\n- Stripe: error: Timeout" in body


def test_digest_grouped_by_company_in_config_order():
    jobs = [job("B:1", title="Zeta Engineer", company="B", location="Pune", posted_at=days_ago(1)),
            job("A:1", title="Backend [Go]", company="A"),
            job("B:2", title="Alpha Engineer", company="B", location="Delhi")]
    title, body = build_issue(Plan(post=jobs, seed=jobs), [], date(2026, 11, 16), ["A", "B"])
    assert title == "New roles: 2026-11-16 (3)"
    assert body == (
        "## A\n"
        "- [Backend \\[Go\\]](https://x/A:1) · Hyderabad\n\n"
        "## B\n"
        "- [Alpha Engineer](https://x/B:2) · Delhi\n"
        "- [Zeta Engineer](https://x/B:1) · Pune · posted 2026-11-15"
    )


def test_body_is_truncated():
    jobs = [job(f"A:{i}", title="x" * 500) for i in range(200)]
    _, body = build_issue(Plan(post=jobs, seed=jobs), [], NOW.date(), ["A"])
    assert len(body) <= MAX_BODY + 50 and body.endswith("(truncated)")
