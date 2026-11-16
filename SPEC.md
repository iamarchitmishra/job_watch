# job-watch: Spec (v1)

## Goal
Every morning, tell me which new software engineering roles opened in the last day at my target companies, filtered to my profile and locations. Nothing else.

## Non-goals (v1)
- No LLM, no AI scoring
- No scraping of HTML pages, LinkedIn, or Naukri
- No web UI, no database server
- No auto-apply

## Architecture
```
config.yaml -> adapters (one per ATS platform) -> normalize to Job
            -> filter (rules) -> diff against seen.json
            -> digest (GitHub Issue) -> update seen.json -> commit
```

### Job (normalized record)
| field      | notes                                                 |
|------------|-------------------------------------------------------|
| key        | `"{company}:{platform_job_id}"`, the dedupe key       |
| company    | display name from config                              |
| title      | as posted                                             |
| location   | raw location text as posted                           |
| url        | public link to the posting                            |
| posted_at  | datetime or None (not every platform exposes it)      |

### Adapter interface
`fetch(company_cfg) -> list[Job]`. One module per platform. An adapter only fetches and normalizes. It does no filtering beyond optional server-side narrowing (e.g. country = India) to cut request volume.

## v1 platforms
1. **Greenhouse**: `GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs`
2. **Workday**: `POST https://{host}/wday/cxs/{tenant}/{site}/jobs` with a JSON body (`limit` max 20, paginate with `offset`). Large tenants have thousands of jobs, so use the "Country" facet the response exposes to narrow to India before paginating (search text is not used; the country facet alone is enough). Multi-location postings show only "N Locations"; use the primary location from the job URL path instead (per-job detail requests trip Workday's rate limit).
3. **SmartRecruiters**: `GET https://api.smartrecruiters.com/v1/companies/{id}/postings` (paginate; supports country filtering)

Endpoint details above are my best understanding. **Verify each against a real response before writing the adapter**, and record which field (if any) gives a posting date. Workday returns relative strings like "Posted 3 Days Ago"; parse what is reliable, otherwise set `posted_at = None`.

## Filtering (all rules live in config.yaml, none hardcoded)
A job passes only if:
1. Title matches at least one `include` pattern (case-insensitive), and
2. Title matches no `exclude` pattern, and
3. Location matches at least one allowed location alias. "Remote" passes only if India is also mentioned. "Remote - US" must fail.

Matching is case-insensitive and whole-word (`intern` does not match "Internal"). A company may adjust the global title lists with its own `filters` block: `title_include_add`, `title_exclude_add`, `title_exclude_remove`.

## State
- `seen.json` in the repo root: `{ "<key>": "<first_seen ISO date>" }`
- Only jobs that **passed the filter** are stored (keeps the file small).
- The workflow commits `seen.json` back after each run. The daily commit also keeps the scheduled workflow from being auto-disabled for inactivity.
- Reposted roles with a new platform ID will show up as new. That is acceptable for v1.

## First run (seen.json missing or empty)
1. Fetch and filter as normal.
2. Keep only jobs with `posted_at` within the last 7 days. Jobs with unknown `posted_at` are seeded silently.
3. If more than 100 remain, seed everything silently and post a single issue saying "Baseline seeded: N roles tracked".
4. Otherwise post them as a normal digest and seed the rest.

## Digest
- One GitHub Issue per run titled `New roles: YYYY-MM-DD (N)`, created with `gh issue create` using the workflow's `GITHUB_TOKEN`.
- Body is grouped by company: title, location, link.
- If there are no new roles and no errors, do not create an issue.
- A **Health** section lists any company that errored or returned 0 jobs before filtering. Zero raw jobs almost always means the adapter broke, not that hiring stopped.

## Failure handling
- Each company is fetched independently. One failure never stops the others.
- Timeouts on every request, with 2 retries and backoff on network errors or 5xx.
- `seen.json` is written only after the digest is successfully created, so a failed run never silently swallows jobs.

## Running
- `python -m jobwatch --dry-run` prints the digest to stdout and writes nothing (for local testing).
- GitHub Actions: daily cron at 03:30 UTC (9:00 AM IST) plus `workflow_dispatch` for manual runs. Permissions: `contents: write`, `issues: write`. No other secrets are needed in v1.

## Tech constraints
- Python 3.12; dependencies limited to `requests`, `PyYAML`, `pytest`
- Plain functions and dataclasses; no frameworks, no ORM, no async
- Tests use saved real API responses in `tests/fixtures/` (one per platform), not live calls

## Definition of done (v1)
1. `--dry-run` works locally against every company in config.yaml
2. Tests pass for all three adapters, the filter, the diff, and the first-run logic
3. The workflow ran unattended for 3 days and created at least one real digest issue

## v2 (not now)
Ashby (Confluent), Rippling's own ATS, then a pluggable `Scorer` (rule-based default, optional local Ollama model).
