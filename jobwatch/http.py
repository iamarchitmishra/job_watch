"""Tiny JSON-over-HTTP helpers: timeout on every request, 2 retries with
backoff on network errors, 5xx, or 429 (rate limited; honours Retry-After).
Other 4xx fail immediately."""
import time

import requests

TIMEOUT = 20  # seconds
RETRIES = 2
BACKOFF = 2  # seconds; doubles each retry
RATE_LIMIT_BACKOFF = 10  # seconds for 429 without Retry-After; doubles each retry
MAX_RETRY_AFTER = 60
HEADERS = {"Accept": "application/json", "User-Agent": "job-watch/0.1"}


def get_json(url, params=None):
    return _request("GET", url, params=params)


def post_json(url, body):
    return _request("POST", url, json=body)


def _request(method, url, **kwargs):
    for attempt in range(RETRIES + 1):
        last = attempt == RETRIES
        try:
            resp = requests.request(method, url, headers=HEADERS, timeout=TIMEOUT, **kwargs)
        except (requests.ConnectionError, requests.Timeout):
            if last:
                raise
            wait = BACKOFF * 2**attempt
        else:
            retryable = resp.status_code >= 500 or resp.status_code == 429
            if not retryable or last:
                resp.raise_for_status()
                return resp.json()
            wait = _wait_for(resp, attempt)
        time.sleep(wait)


def _wait_for(resp, attempt):
    if resp.status_code == 429:
        retry_after = (resp.headers or {}).get("Retry-After", "")
        if retry_after.isdigit():
            return min(int(retry_after), MAX_RETRY_AFTER)
        return RATE_LIMIT_BACKOFF * 2**attempt
    return BACKOFF * 2**attempt
