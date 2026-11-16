# Working rules for this repo

- SPEC.md is the source of truth. If something in it is wrong or ambiguous, stop and ask; do not silently deviate.
- Before writing code for any step, show a short plan and wait for approval.
- Build in vertical slices: one adapter end to end (fetch, normalize, print) before starting the next.
- Before writing an adapter, call the real endpoint for one company from config.yaml, save the raw response to tests/fixtures/, and show me the fields you plan to use (especially the posting date field).
- Only the dependencies listed in SPEC.md. Ask before adding anything else.
- Keep it boring: plain functions and dataclasses, no frameworks, no async, no premature abstraction.
- Never commit secrets, tokens, or .env files.
- After each slice: run the tests, run `python -m jobwatch --dry-run`, and summarize what changed in a few lines.
- Stop when a slice is done. Do not start the next slice without my go-ahead.
