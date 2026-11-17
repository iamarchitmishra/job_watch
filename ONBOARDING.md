# Onboarding: run job-watch for yourself

About 20 minutes. You end up with a daily GitHub Issue listing new engineering
roles at the companies you choose, matched to your level and locations.

You need: a GitHub account, Python 3.12, and `git`. The `gh` CLI is only needed
inside GitHub Actions (already installed there).

## 1. Get your own copy

Use **"Use this template"** or create a new repo and push a copy of this code.
A plain fork works too, but forks start with Issues and scheduled workflows
turned off (see step 6).

Then **delete `seen.json`** if it exists. It is the previous owner's memory of
which jobs they already saw. Without it, your first run starts fresh.

```bash
git rm --cached seen.json 2>/dev/null; rm -f seen.json
```

## 2. Set up locally

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest -q          # should all pass
```

## 3. Make the config yours

Everything is in `config.yaml`; nothing is hardcoded.

**Companies.** Delete the ones you don't care about. To add one, follow
"Adding a company" in the README (find the platform from the Apply URL, check it
with `curl`, add a block, dry-run it).

**Titles for your level.** The defaults target an engineer with about 4 years of
experience: `software engineer`, `sde`, `backend`, `mts`, ML/AI engineer are in;
`intern`, `staff`, `principal`, `lead`, `manager`, `architect`, frontend/mobile/QA
are out. Change `filters.title_include` and `title_exclude` to fit you.

Company ladders differ, so check a few companies' real titles and use their
per-company `filters` block where needed. Examples already in the config:

- Salesforce: MTS < SMTS < LMTS < PMTS, and "Member of Technical Staff" is an IC
  title, so `staff` is removed from the excludes there.
- ServiceNow: Staff is IC4 (~8+ years), so it stays excluded.
- Adobe: "Computer Scientist 1/2" are engineering roles.

If you are more senior, you probably want to remove `staff` and `lead` from the
global excludes instead.

**Locations.** `filters.locations` is a list of words, any of which must appear
in the job's location. The default is India plus major Indian cities (some
boards list only the city). For a different country, replace the list, and change
`country:` on Workday (`India` → the facet's name, e.g. `Germany`) and
SmartRecruiters (`in` → ISO code, e.g. `de`) companies.

## 4. Preview

```bash
.venv/bin/python -m jobwatch --dry-run                    # everything (~1 min)
.venv/bin/python -m jobwatch --dry-run --only Databricks  # one company
```

Read the **Stats** block: every company should show a non-zero "fetched".
Then read the issue preview and tune titles until it looks right. Dry-run never
writes anything, so iterate freely.

## 5. Push

```bash
git add -A && git commit -m "My job-watch config" && git push
```

`seen.json` will be created by the first real run in Actions. Never commit
tokens or `.env` files; none are needed.

## 6. Turn it on in GitHub

1. **Settings → General → Features:** make sure **Issues** is ticked.
2. **Actions tab:** if it says workflows are disabled (forks), enable them.
3. **Settings → Actions → General → Workflow permissions:** "Read and write
   permissions" (the workflow also declares the two permissions it needs).
4. **Actions → job-watch → Run workflow** to do the first run now instead of
   waiting for 09:00 IST.

After about two minutes you should see:

- an issue titled `New roles: YYYY-MM-DD (N)` (or `Baseline seeded: N roles tracked`
  if more than 100 recent matches), and
- a commit from `github-actions[bot]`: `Update seen.json (...)`.

## 7. Get notified

Click **Watch → All Activity** (or Custom → Issues) on the repo. GitHub then
emails you each new issue, and the GitHub mobile app pushes it.

## Day to day

- A new issue appears on mornings when something new matched. No issue means
  nothing new and nothing broken.
- Check the **Health** section: an error or "0 jobs before filtering" for a
  company means its config needs a look (the README has a table of causes).
- Change your mind about titles or companies: edit `config.yaml`, dry-run,
  push. Newly added companies get the first-run treatment, so they don't flood
  the digest with old roles.
- Want a run now: Actions → job-watch → Run workflow.

## Costs and limits

- Free on public repos. Private repos: about 2 minutes per run against 2,000
  free minutes a month.
- Workday sites rate-limit bursts. Requests are spaced out and retried, but if
  you run the dry-run many times in an hour, Workday companies may show 429 in
  Health for a while. That clears by itself.
- GitHub pauses scheduled workflows after 60 days without repo activity. A
  `seen.json` commit counts, so this only bites after two months with zero
  new matches. Re-enable it from the Actions tab if it happens.
