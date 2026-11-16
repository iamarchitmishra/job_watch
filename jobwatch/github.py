import subprocess


def create_issue(title, body):
    """Create an issue in the current repo with the gh CLI (uses GH_TOKEN in CI)."""
    result = subprocess.run(
        ["gh", "issue", "create", "--title", title, "--body-file", "-"],
        input=body, text=True, capture_output=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh issue create failed: {result.stderr.strip()}")
    return result.stdout.strip()
