import argparse
import sys
from datetime import datetime, timezone

from jobwatch import github, state
from jobwatch.adapters import ADAPTERS
from jobwatch.config import load_config
from jobwatch.digest import build_issue, plan_run
from jobwatch.filter import filter_jobs


def fetch_all(companies, adapters=ADAPTERS):
    """Fetch each company independently. Returns (results, health) where
    results is [(company_cfg, jobs)] and health is a list of problem lines."""
    results, health = [], []
    for company in companies:
        name, platform = company["name"], company["platform"]
        fetch = adapters.get(platform)
        if fetch is None:
            health.append(f"{name}: no adapter for platform '{platform}'")
            continue
        try:
            jobs = fetch(company)
        except Exception as e:
            health.append(f"{name}: error: {type(e).__name__}: {e}")
            continue
        if not jobs:
            health.append(f"{name}: 0 jobs before filtering (adapter may be broken)")
        results.append((company, jobs))
    return results, health


def run(cfg, seen_path, dry_run, adapters=ADAPTERS, create_issue=github.create_issue, now=None):
    now = now or datetime.now(timezone.utc)
    seen = state.load_seen(seen_path)
    results, health = fetch_all(cfg["companies"], adapters)

    passed, stats = [], []
    for company, jobs in results:
        kept = filter_jobs(jobs, cfg["filters"], company)
        passed.extend(kept)
        stats.append(f"{company['name']}: {len(jobs)} fetched, {len(kept)} passed")

    plan = plan_run(passed, seen, now, cfg.get("first_run") or {})
    issue = build_issue(plan, health, now.date(), [c["name"] for c in cfg["companies"]])

    if dry_run:
        print("Stats")
        print("\n".join(f"  {line}" for line in stats))
        print(f"  first run: {not seen}; would add {len(plan.seed)} keys to {seen_path}\n")
        if issue:
            print(f"Issue title: {issue[0]}\n\n{issue[1]}")
        else:
            print("No new roles and no errors: no issue would be created.")
        return 0

    if issue:
        print(f"Created issue: {create_issue(*issue)}")
    else:
        print("No new roles and no errors: no issue created.")
    # Only reached if the issue was created (or none was needed).
    if plan.seed:
        today = now.date().isoformat()
        seen.update({job.key: today for job in plan.seed})
        state.save_seen(seen_path, seen)
    print(f"{len(plan.post)} posted, {len(plan.seed)} added to {seen_path}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="jobwatch")
    parser.add_argument("--dry-run", action="store_true", help="print the digest, write nothing")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--seen", default="seen.json")
    args = parser.parse_args(argv)
    return run(load_config(args.config), args.seen, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
