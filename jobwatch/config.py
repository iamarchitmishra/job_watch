import yaml

COMPANY_FILTER_KEYS = {"title_include_add", "title_exclude_add", "title_exclude_remove"}


def load_config(path):
    with open(path) as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict) or not cfg.get("companies"):
        raise ValueError(f"{path}: 'companies' must be a non-empty list")
    filters = cfg.get("filters") or {}
    for key in ("title_include", "locations"):
        if not filters.get(key):
            raise ValueError(f"{path}: 'filters.{key}' must not be empty")
    global_exclude = {str(p).lower() for p in filters.get("title_exclude") or []}

    for i, company in enumerate(cfg["companies"]):
        for field in ("name", "platform"):
            if not company.get(field):
                raise ValueError(f"{path}: companies[{i}] is missing '{field}'")
        own = company.get("filters") or {}
        unknown = set(own) - COMPANY_FILTER_KEYS
        if unknown:
            raise ValueError(f"{path}: {company['name']}: unknown filters keys {sorted(unknown)}")
        for phrase in own.get("title_exclude_remove") or []:
            if str(phrase).lower() not in global_exclude:
                raise ValueError(f"{path}: {company['name']}: title_exclude_remove "
                                 f"'{phrase}' is not in filters.title_exclude")
    return cfg
