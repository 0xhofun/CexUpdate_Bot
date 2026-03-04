from __future__ import annotations

import json
from pathlib import Path

from xlist_monitor_standalone.config import MonitorConfig
from xlist_monitor_standalone.models import RunSummary, TweetRecord, utc_now_iso
from xlist_monitor_standalone.scraper import Scraper
from xlist_monitor_standalone.storage import Storage
from xlist_monitor_standalone.telegram import send_tweets


class Runner:
    def __init__(self, config: MonitorConfig) -> None:
        self.config = config
        self.storage = Storage(config.db_path)

    def run_once(self) -> RunSummary:
        self.storage.init_db()

        tweets = Scraper(self.config).scrape()
        raw_dump_path = self._write_raw_dump(tweets)

        inserted = 0
        for item in tweets:
            if self.storage.save_tweet(item):
                inserted += 1

        digest_tweets = self.storage.latest_for_digest(limit=20)
        digest_path = self._write_digest(digest_tweets)

        if self.config.telegram.enabled:
            bot_token = self.config.telegram.bot_token
            chat_id = self.config.telegram.chat_id
            if not bot_token or not chat_id:
                raise RuntimeError(
                    "Telegram enabled but missing bot token/chat id. "
                    "Use config or TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID env."
                )

            unpushed = self.storage.filter_unpushed(digest_tweets)
            if unpushed:
                send_tweets(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    tweets=unpushed,
                    max_posts_per_round=self.config.telegram.max_posts_per_round,
                )
                self.storage.mark_pushed(unpushed, utc_now_iso())

        return RunSummary(
            scraped=len(tweets),
            inserted=inserted,
            raw_dump_path=str(raw_dump_path),
            digest_path=str(digest_path),
        )

    def _write_raw_dump(self, tweets: list[TweetRecord]) -> Path:
        dump_dir = Path(self.config.raw_dump_dir)
        dump_dir.mkdir(parents=True, exist_ok=True)
        stamp = utc_now_iso().replace(":", "").replace("-", "")
        path = dump_dir / f"scrape_{stamp}.json"
        path.write_text(
            json.dumps([item.to_dict() for item in tweets], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def _write_digest(self, tweets: list[TweetRecord]) -> Path:
        out_dir = Path(self.config.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = utc_now_iso().replace(":", "").replace("-", "")
        path = out_dir / f"digest_{stamp}.md"

        lines: list[str] = ["# X Monitor Digest", ""]
        if not tweets:
            lines.append("No tweets captured.")
        else:
            for item in tweets:
                lines.append(f"- @{item.author_handle} | {item.posted_at_iso}")
                lines.append(f"  - {item.tweet_url}")
                text = (item.text or "").strip().replace("\n", " ")
                lines.append(f"  - {text[:280]}")

        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return path
