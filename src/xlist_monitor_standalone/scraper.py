from __future__ import annotations

import re
import time
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from xlist_monitor_standalone.config import MonitorConfig
from xlist_monitor_standalone.models import TweetRecord, utc_now_iso

STATUS_RE = re.compile(r"/status/(\d+)")
REPOST_HINTS = (" reposted", "转发了", "转推了")
DEFAULT_NAVIGATION_TIMEOUT_MS = 90_000
DEFAULT_ACTION_TIMEOUT_MS = 30_000


class Scraper:
    def __init__(self, config: MonitorConfig) -> None:
        self.config = config

    def scrape(self) -> list[TweetRecord]:
        collected: dict[str, TweetRecord] = {}
        scraped_at_iso = utc_now_iso()
        deadline = time.monotonic() + self.config.scrape_timeout_seconds

        with sync_playwright() as p:
            with self._open_page(p) as page:
                page.set_default_timeout(DEFAULT_ACTION_TIMEOUT_MS)
                for url in self.config.monitor_urls():
                    nav_timeout = min(
                        DEFAULT_NAVIGATION_TIMEOUT_MS,
                        self._remaining_timeout_ms(deadline),
                    )
                    if nav_timeout <= 0:
                        print("scrape timeout reached before navigation")
                        break

                    page.goto(url, wait_until="domcontentloaded", timeout=nav_timeout)
                    if not self._wait_with_deadline(page, 1500, deadline):
                        break

                    for _ in range(self.config.max_scrolls):
                        if self._remaining_timeout_ms(deadline) <= 0:
                            print("scrape timeout reached during scrolling")
                            break
                        for tweet in self._extract_visible_tweets(page, scraped_at_iso):
                            collected.setdefault(tweet.tweet_id, tweet)
                        page.mouse.wheel(0, 2600)
                        if not self._wait_with_deadline(
                            page, int(self.config.sleep_seconds * 1000), deadline
                        ):
                            break

        tweets = sorted(collected.values(), key=lambda item: item.posted_at_iso, reverse=True)
        return tweets

    def _extract_visible_tweets(self, page, scraped_at_iso: str) -> list[TweetRecord]:
        records: list[TweetRecord] = []
        for article in page.locator("article[data-testid='tweet']").all():
            try:
                if self.config.exclude_reposts and _is_repost(article):
                    continue
                record = _extract_tweet(article, scraped_at_iso)
            except PlaywrightError:
                continue
            if record is not None:
                records.append(record)
        return records

    @contextmanager
    def _open_page(self, playwright):
        if self.config.cdp_url:
            browser = playwright.chromium.connect_over_cdp(
                self.config.cdp_url,
                timeout=DEFAULT_ACTION_TIMEOUT_MS,
            )
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.new_page()
            try:
                yield page
            finally:
                try:
                    page.close()
                except PlaywrightError:
                    pass
                try:
                    browser.close()
                except PlaywrightError:
                    pass
            return

        Path(self.config.user_data_dir).mkdir(parents=True, exist_ok=True)
        browser_args = ["--disable-dev-shm-usage"]
        if self.config.allow_insecure_no_sandbox:
            browser_args.append("--no-sandbox")

        context = playwright.chromium.launch_persistent_context(
            user_data_dir=self.config.user_data_dir,
            headless=self.config.headless,
            args=browser_args,
        )
        page = context.new_page()
        try:
            yield page
        finally:
            try:
                page.close()
            except PlaywrightError:
                pass
            try:
                context.close()
            except PlaywrightError:
                pass

    def _remaining_timeout_ms(self, deadline: float) -> int:
        return max(int((deadline - time.monotonic()) * 1000), 0)

    def _wait_with_deadline(self, page, wait_ms: int, deadline: float) -> bool:
        remaining_ms = self._remaining_timeout_ms(deadline)
        if remaining_ms <= 0:
            return False
        page.wait_for_timeout(min(wait_ms, remaining_ms))
        return self._remaining_timeout_ms(deadline) > 0


def _extract_tweet(article, scraped_at_iso: str) -> TweetRecord | None:
    hrefs = article.locator("a[href*='/status/']").evaluate_all(
        "nodes => nodes.map(n => n.getAttribute('href')).filter(Boolean)"
    )
    if not hrefs:
        return None

    href = hrefs[0]
    match = STATUS_RE.search(href)
    if not match:
        return None

    tweet_id = match.group(1)
    tweet_url = href if href.startswith("http") else f"https://x.com{href}"
    author_handle = _extract_handle_from_url(tweet_url)

    text = "\n".join(article.locator("div[data-testid='tweetText']").all_inner_texts()).strip()

    try:
        posted = article.locator("time").first.get_attribute("datetime") or ""
    except PlaywrightError:
        posted = ""
    posted_at_iso = posted or scraped_at_iso

    return TweetRecord(
        tweet_id=tweet_id,
        tweet_url=tweet_url,
        author_handle=author_handle,
        posted_at_iso=posted_at_iso,
        text=text,
        scraped_at_iso=scraped_at_iso,
    )


def _extract_handle_from_url(url: str) -> str:
    try:
        body = url.replace("https://x.com/", "", 1)
        return body.split("/", 1)[0] or "unknown"
    except Exception:
        return "unknown"


def _is_repost(article) -> bool:
    contexts = article.locator("div[data-testid='socialContext']").all_inner_texts()
    if not contexts:
        return False
    text = " ".join(contexts).lower()
    return any(hint in text for hint in REPOST_HINTS)
