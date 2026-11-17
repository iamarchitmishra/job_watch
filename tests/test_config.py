import pytest

from jobwatch.config import load_config


def test_loads_repo_config():
    cfg = load_config("config.yaml")
    assert {c["platform"] for c in cfg["companies"]} == {"greenhouse", "workday", "smartrecruiters", "lever", "ashby"}


BASE = """
filters:
  title_include: [software engineer]
  title_exclude: [staff]
  locations: {india: [india]}
companies:
"""


@pytest.mark.parametrize("company, error", [
    ("  - name: X\n", "platform"),
    ("  - {name: 'A:B', platform: p}\n", "must not contain"),
    ("  - {name: X, platform: p, filters: {title_include_ad: [a]}}\n", "unknown filters keys"),
    ("  - {name: X, platform: p, filters: {title_exclude_remove: [stuff]}}\n", "not in filters.title_exclude"),
])
def test_rejects_bad_company(tmp_path, company, error):
    path = tmp_path / "c.yaml"
    path.write_text(BASE + company)
    with pytest.raises(ValueError, match=error):
        load_config(path)
