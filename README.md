# job-watch

Every morning, opens one GitHub Issue listing the software engineering roles that
newly opened at a list of target companies, filtered to your titles and to India.
No scraping, no LLM, no server: it reads the public job APIs that company career
pages already use, and runs on GitHub Actions for free.

`SPEC.md` is the source of truth for behaviour. Setting it up for yourself:
see [ONBOARDING.md](ONBOARDING.md).

## How it works

```
config.yaml ─▶ adapters (Greenhouse / Workday / SmartRecruiters / Lever / Ashby) ─▶ Job records
           ─▶ filter (title + location rules) ─▶ diff against seen.json
           ─▶ GitHub Issue "New roles: YYYY-MM-DD (N)" ─▶ update + commit seen.json
```

1. **Fetch.** Each company in `config.yaml` is fetched on its own. If one fails, the
   rest still run and the failure shows up in the issue's **Health** section.
2. **Filter.** A job is kept if its title matches an `include` phrase, matches no
   `exclude` phrase, and its location mentions India or an Indian city. Matching is
   case-insensitive and whole-word (`intern` does not match "Internal"; words are
   letters and digits, so `lead` does match "Java Lead_ VP").
3. **Diff.** `seen.json` remembers every job that ever passed the filter. Anything
   not in it is new.
4. **Report.** New jobs go into one issue, grouped by company. No new jobs and no
   errors means no issue.
5. **Remember.** `seen.json` is updated only after the issue is created, so a failed
   run never silently loses jobs.

### First run, and newly added companies

A company with nothing in `seen.json` yet (first run, or a company you just added)
would otherwise dump every open role, some months old. Instead, for that company
only jobs posted in the last 7 days are shown; older ones are remembered silently.
If that is still more than 100, all of them are remembered silently and the issue
just says "Baseline seeded". Both numbers are in `config.yaml` under `first_run`.

### Posting dates by platform

| Platform | Date field | Notes |
|---|---|---|
| Greenhouse | `first_published` | exact |
| SmartRecruiters | `releasedDate` | exact |
| Lever | `createdAt` | when the posting was created (usually = published) |
| Ashby | `publishedAt` | exact |
| Workday | `postedOn` ("Posted 3 Days Ago") | day-level; "30+ Days Ago" is treated as unknown |

## Running locally

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt   # once

.venv/bin/python -m pytest -q                                  # tests (offline, uses tests/fixtures)
.venv/bin/python -m jobwatch --dry-run                         # full preview, writes nothing (~1 min)
.venv/bin/python -m jobwatch --dry-run --only PhonePe          # one company (repeat --only for more)
.venv/bin/python -m jobwatch --dry-run | sed -n '/^Stats/,/^$/p'   # just the per-company counts
```

`--dry-run` prints per-company stats (fetched / passed) and the issue it would
create. It never creates issues or writes `seen.json`. Without a local
`seen.json` it shows what a first run would post.

## Adding a company

1. **Find the platform.** Open any job on their careers site and click Apply:

   | Apply URL looks like | `platform` | Config fields |
   |---|---|---|
   | `job-boards.greenhouse.io/rubrik/...` | `greenhouse` | `token: rubrik` |
   | `akamai.wd1.myworkdayjobs.com/en-US/Akamai_Careers/...` | `workday` | `host: akamai.wd1.myworkdayjobs.com`, `tenant: akamai`, `site: Akamai_Careers`, `country: India` |
   | `jobs.smartrecruiters.com/PhonePeLimited/...` | `smartrecruiters` | `company_id: PhonePeLimited`, `country: in` |
   | `jobs.lever.co/meesho/...` | `lever` | `slug: meesho` (add `region: eu` for `jobs.eu.lever.co`) |
   | `jobs.ashbyhq.com/snowflake/...` | `ashby` | `board: snowflake` |
   | a custom portal (Flipkart, Amazon, Google...) | not supported | no public job API |

   For Workday the tenant is usually the first part of the host; the site is the
   path segment after the optional `en-US/`. Guessing the site name usually fails
   (HTTP 422); copy it from a real Apply URL. `country: India` works whether the
   tenant has a country facet or only a "Locations" facet (like Intel).

2. **Check it responds** (you should see JSON with jobs):

   ```bash
   curl -s https://boards-api.greenhouse.io/v1/boards/TOKEN/jobs | head -c 300
   curl -s "https://api.smartrecruiters.com/v1/companies/ID/postings?limit=1&country=in" | head -c 300
   curl -s "https://api.lever.co/v0/postings/SLUG?mode=json" | head -c 300
   curl -s "https://api.ashbyhq.com/posting-api/job-board/BOARD" | head -c 300
   curl -s -X POST -H 'Content-Type: application/json' \
     -d '{"appliedFacets":{},"limit":1,"offset":0,"searchText":""}' \
     https://HOST/wday/cxs/TENANT/SITE/jobs | head -c 300
   ```

3. **Add it to `config.yaml`:**

   ```yaml
   - name: Akamai              # pick once; it prefixes every key in seen.json
     platform: workday
     host: akamai.wd1.myworkdayjobs.com
     tenant: akamai
     site: Akamai_Careers
     country: India
     filters:                  # optional: only if their titles are unusual
       title_include_add: [mts]
   ```

4. **Dry-run just that company:** `.venv/bin/python -m jobwatch --dry-run --only Akamai`.
   Check that "fetched" looks plausible and that the right titles pass. If not,
   adjust its `filters` block (see below).

5. **Commit and push `config.yaml`.** The next scheduled run picks it up, using
   the first-run rules above for that company.

Renaming a company later counts as a new company (its keys in `seen.json` change).

## Filters

Global rules live under `filters:` in `config.yaml`. A company can adjust them
with its own `filters:` block, because titles mean different things at
different companies:

```yaml
filters:
  title_include_add: [smts]       # Salesforce: "SMTS" is a mid-level engineer
  title_exclude_add: [pmts]       # ...and "PMTS" is principal
  title_exclude_remove: [staff]   # "Member of Technical Staff" is an IC title there
```

Effective lists: global include + `title_include_add`; global exclude −
`title_exclude_remove` + `title_exclude_add`. Exclude always wins over include.
Config loading fails loudly on unknown keys or on removing a phrase that is not
in the global exclude list.

## GitHub Actions

`.github/workflows/jobwatch.yml` runs daily at 03:30 UTC (09:00 IST) and on the
"Run workflow" button (Actions tab). Each run gets a fresh Linux machine:

1. check out the repo (including `config.yaml` and `seen.json`)
2. install Python 3.12 and `requirements.txt`
3. run the tests (a failure stops the run before anything is posted)
4. `python -m jobwatch`: fetch, filter, diff, create the issue with `gh`
5. commit `seen.json` back if it changed

The machine is thrown away after each run; `seen.json` committed to the repo is
the only memory between days. The workflow has just `contents: write` (push
`seen.json`) and `issues: write`, via the temporary `GITHUB_TOKEN`. No secrets.

Note: GitHub disables scheduled workflows after 60 days with no repo activity.
Any new matching role (a `seen.json` commit) resets that clock.

## Reading the Health section

| Health line | Usually means |
|---|---|
| `X: error: HTTPError: 404` | wrong token / company_id / site, or the company moved platform |
| `X: error: HTTPError: 429` | rate limited (Workday). Retried with backoff; usually fine the next day |
| `X: error: LookupError: no 'India' value in a 'Country' facet` | Workday tenant names its country filter differently, or has no India jobs |
| `X: 0 jobs before filtering` | the adapter is probably broken; check the board manually |

## Companies

Tracked: see `config.yaml`. The bottom of `config.yaml` lists companies that
were checked but can't be tracked yet: own portals with no public job API
(Flipkart, Amazon, Google, Microsoft, Atlassian, Myntra, Zomato/Blinkit, ...),
Workday tenants whose site name isn't known yet (NVIDIA, Walmart, Qualcomm, ...),
and boards with no India roles right now.

Ranks in titles differ per company, so some have their own `filters`:
Salesforce (MTS/SMTS), Adobe (Computer Scientist), ServiceNow (Staff = IC4),
Target ("Engineer" / "Sr Engineer"), Morgan Stanley (bank ranks: VP and above excluded).

## Layout

```
jobwatch/
  __main__.py        CLI, fetch loop, run()
  adapters/          greenhouse, workday, smartrecruiters, lever, ashby  (fetch + normalize to Job)
  filter.py          title/location rules
  digest.py          what's new (incl. first-run rules) + issue markdown
  state.py           seen.json load/save
  github.py          gh issue create
  http.py            timeouts + retries (network errors, 5xx, 429)
tests/               pytest; fixtures/ are saved real API responses
```
