import json

import pytest

from jobwatch.state import load_seen, save_seen


def test_missing_or_empty_is_first_run(tmp_path):
    assert load_seen(tmp_path / "nope.json") == {}
    (tmp_path / "e.json").write_text("  \n")
    assert load_seen(tmp_path / "e.json") == {}


def test_roundtrip_sorted(tmp_path):
    path = tmp_path / "seen.json"
    save_seen(path, {"b:1": "2026-11-16", "a:1": "2026-11-15"})
    assert load_seen(path) == {"a:1": "2026-11-15", "b:1": "2026-11-16"}
    assert list(json.loads(path.read_text())) == ["a:1", "b:1"]
    assert not (tmp_path / "seen.json.tmp").exists()


def test_rejects_non_object(tmp_path):
    path = tmp_path / "seen.json"
    path.write_text("[]")
    with pytest.raises(ValueError):
        load_seen(path)
