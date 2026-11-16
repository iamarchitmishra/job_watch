"""seen.json: { "<key>": "<first_seen ISO date>" } for jobs that passed the filter."""
import json
import os


def load_seen(path):
    try:
        with open(path) as f:
            text = f.read()
    except FileNotFoundError:
        return {}
    if not text.strip():
        return {}
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return data


def save_seen(path, seen):
    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        json.dump(seen, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)
