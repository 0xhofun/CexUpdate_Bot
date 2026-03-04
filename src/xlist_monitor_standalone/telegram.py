from __future__ import annotations

import html
import time

import requests

from xlist_monitor_standalone.models import TweetRecord

MAX_TELEGRAM_MESSAGE_LENGTH = 4096
MAX_RETRIES = 3
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def send_tweets(
    bot_token: str,
    chat_id: str,
    tweets: list[TweetRecord],
    max_posts_per_round: int,
) -> int:
    sent = 0
    endpoint = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    for item in tweets[:max_posts_per_round]:
        text = _render_tweet_message(item)
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        _send_message_with_retry(endpoint=endpoint, payload=payload)
        sent += 1
    return sent


def _render_tweet_message(item: TweetRecord) -> str:
    url = html.escape(item.tweet_url, quote=True)
    author = html.escape(item.author_handle)
    posted = html.escape(item.posted_at_iso)

    prefix = f"<b>@{author}</b>\n<code>{posted}</code>\n\n"
    suffix = f"\n\n<a href=\"{url}\">Open Tweet</a>"
    text = item.text.strip() or "(no text)"
    fitted_text = _fit_escaped_text(raw_text=text, prefix=prefix, suffix=suffix)
    return f"{prefix}{fitted_text}{suffix}"


def _fit_escaped_text(raw_text: str, prefix: str, suffix: str) -> str:
    escaped_full = html.escape(raw_text)
    if len(prefix) + len(escaped_full) + len(suffix) <= MAX_TELEGRAM_MESSAGE_LENGTH:
        return escaped_full

    best = ""
    low, high = 0, len(raw_text)
    while low <= high:
        mid = (low + high) // 2
        candidate_raw = raw_text[:mid].rstrip()
        if mid < len(raw_text):
            candidate_raw = f"{candidate_raw}..."
        escaped_candidate = html.escape(candidate_raw)
        total = len(prefix) + len(escaped_candidate) + len(suffix)
        if total <= MAX_TELEGRAM_MESSAGE_LENGTH:
            best = escaped_candidate
            low = mid + 1
        else:
            high = mid - 1

    if best:
        return best

    fallback = html.escape("(truncated)")
    max_text_len = MAX_TELEGRAM_MESSAGE_LENGTH - len(prefix) - len(suffix)
    if max_text_len <= 0:
        return ""
    return fallback[:max_text_len]


def _send_message_with_retry(endpoint: str, payload: dict) -> None:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(endpoint, json=payload, timeout=30)
        except requests.RequestException:
            if attempt >= MAX_RETRIES:
                raise
            time.sleep(_retry_sleep_seconds(attempt))
            continue

        if response.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
            time.sleep(_retry_sleep_seconds(attempt, _parse_retry_after_header(response)))
            continue

        response.raise_for_status()
        body = _safe_json(response)
        if body.get("ok"):
            return

        error_code = body.get("error_code")
        retry_after = _parse_retry_after_body(body)
        if error_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
            time.sleep(_retry_sleep_seconds(attempt, retry_after))
            continue

        raise RuntimeError(f"telegram sendMessage failed: {body}")

    raise RuntimeError("telegram sendMessage failed after retries")


def _safe_json(response: requests.Response) -> dict:
    try:
        body = response.json()
    except ValueError as exc:
        raise RuntimeError("telegram returned non-JSON response") from exc
    if not isinstance(body, dict):
        raise RuntimeError(f"unexpected telegram response body type: {type(body)!r}")
    return body


def _parse_retry_after_header(response: requests.Response) -> int | None:
    value = response.headers.get("Retry-After")
    if not value:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _parse_retry_after_body(body: dict) -> int | None:
    params = body.get("parameters")
    if not isinstance(params, dict):
        return None
    raw = params.get("retry_after")
    if isinstance(raw, int) and raw > 0:
        return raw
    return None


def _retry_sleep_seconds(attempt: int, retry_after: int | None = None) -> float:
    if retry_after is not None:
        return min(float(retry_after), 60.0)
    return min(float(2 ** (attempt - 1)), 30.0)
