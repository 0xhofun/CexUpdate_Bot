from __future__ import annotations

import requests

from xlist_monitor_standalone.models import TweetRecord
from xlist_monitor_standalone.telegram import (
    MAX_TELEGRAM_MESSAGE_LENGTH,
    _render_tweet_message,
    send_tweets,
)


class DummyResponse:
    def __init__(self, status_code: int, body: dict, headers: dict | None = None):
        self.status_code = status_code
        self._body = body
        self.headers = headers or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"http {self.status_code}")

    def json(self) -> dict:
        return self._body


def _tweet(text: str) -> TweetRecord:
    return TweetRecord(
        tweet_id="1",
        tweet_url="https://x.com/a/status/1",
        author_handle="a",
        posted_at_iso="2026-03-04T00:00:00Z",
        text=text,
        scraped_at_iso="2026-03-04T00:00:00Z",
    )


def test_render_tweet_message_respects_telegram_max_length() -> None:
    message = _render_tweet_message(_tweet("a" * 20_000))
    assert len(message) <= MAX_TELEGRAM_MESSAGE_LENGTH


def test_send_tweets_retries_429_then_succeeds(monkeypatch) -> None:
    calls = {"count": 0}
    responses = [
        DummyResponse(
            429,
            {"ok": False, "error_code": 429, "parameters": {"retry_after": 1}},
            headers={"Retry-After": "1"},
        ),
        DummyResponse(200, {"ok": True}),
    ]

    def fake_post(*args, **kwargs):
        calls["count"] += 1
        return responses.pop(0)

    monkeypatch.setattr("xlist_monitor_standalone.telegram.requests.post", fake_post)
    monkeypatch.setattr("xlist_monitor_standalone.telegram.time.sleep", lambda *_: None)

    sent = send_tweets("token", "chat", [_tweet("hello")], max_posts_per_round=1)
    assert sent == 1
    assert calls["count"] == 2
