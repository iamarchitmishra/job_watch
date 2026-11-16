import pytest
import requests

from jobwatch import http


class FakeResp:
    def __init__(self, status, data=None, headers=None):
        self.status_code, self._data, self.headers = status, data, headers or {}

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


SLEEPS = []


@pytest.fixture
def no_sleep(monkeypatch):
    SLEEPS.clear()
    monkeypatch.setattr(http.time, "sleep", SLEEPS.append)


def _script(monkeypatch, outcomes):
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append(kwargs["timeout"])
        outcome = outcomes[len(calls) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    monkeypatch.setattr(http.requests, "request", fake_request)
    return calls


def test_retries_5xx_then_succeeds(monkeypatch, no_sleep):
    calls = _script(monkeypatch, [FakeResp(503), requests.ConnectionError(), FakeResp(200, {"ok": 1})])
    assert http.get_json("u") == {"ok": 1}
    assert len(calls) == 3
    assert all(t == http.TIMEOUT for t in calls)


def test_gives_up_after_two_retries(monkeypatch, no_sleep):
    calls = _script(monkeypatch, [FakeResp(500)] * 3)
    with pytest.raises(requests.HTTPError):
        http.get_json("u")
    assert len(calls) == 3


def test_4xx_is_not_retried(monkeypatch, no_sleep):
    calls = _script(monkeypatch, [FakeResp(404)])
    with pytest.raises(requests.HTTPError):
        http.post_json("u", {})
    assert len(calls) == 1


def test_429_is_retried_honouring_retry_after(monkeypatch, no_sleep):
    calls = _script(monkeypatch, [FakeResp(429, headers={"Retry-After": "7"}),
                                  FakeResp(429), FakeResp(200, {"ok": 1})])
    assert http.post_json("u", {}) == {"ok": 1}
    assert len(calls) == 3
    assert SLEEPS == [7, http.RATE_LIMIT_BACKOFF * 2]


def test_backoff_doubles_on_5xx(monkeypatch, no_sleep):
    _script(monkeypatch, [FakeResp(502), FakeResp(502), FakeResp(200, {})])
    http.get_json("u")
    assert SLEEPS == [http.BACKOFF, http.BACKOFF * 2]
