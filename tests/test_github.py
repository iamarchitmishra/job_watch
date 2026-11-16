import subprocess

import pytest

from jobwatch import github


def test_create_issue_passes_body_on_stdin(monkeypatch):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"], seen["input"] = cmd, kwargs["input"]
        return subprocess.CompletedProcess(cmd, 0, stdout="https://github.com/o/r/issues/1\n", stderr="")

    monkeypatch.setattr(github.subprocess, "run", fake_run)
    assert github.create_issue("T", "body") == "https://github.com/o/r/issues/1"
    assert seen["cmd"] == ["gh", "issue", "create", "--title", "T", "--body-file", "-"]
    assert seen["input"] == "body"


def test_create_issue_raises_on_failure(monkeypatch):
    monkeypatch.setattr(github.subprocess, "run", lambda cmd, **kw:
                        subprocess.CompletedProcess(cmd, 1, stdout="", stderr="HTTP 403"))
    with pytest.raises(RuntimeError, match="403"):
        github.create_issue("T", "b")
