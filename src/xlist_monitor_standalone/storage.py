from __future__ import annotations

import sqlite3
from pathlib import Path

from xlist_monitor_standalone.models import TweetRecord


class Storage:
    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)

    def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tweets (
                    tweet_id TEXT PRIMARY KEY,
                    tweet_url TEXT NOT NULL,
                    author_handle TEXT NOT NULL,
                    posted_at_iso TEXT NOT NULL,
                    text TEXT NOT NULL,
                    scraped_at_iso TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_push_history (
                    tweet_id TEXT PRIMARY KEY,
                    pushed_at_iso TEXT NOT NULL
                )
                """
            )

    def save_tweet(self, tweet: TweetRecord) -> bool:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO tweets (
                    tweet_id, tweet_url, author_handle, posted_at_iso, text, scraped_at_iso
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    tweet.tweet_id,
                    tweet.tweet_url,
                    tweet.author_handle,
                    tweet.posted_at_iso,
                    tweet.text,
                    tweet.scraped_at_iso,
                ),
            )
            return cur.rowcount > 0

    def latest_for_digest(self, limit: int = 20) -> list[TweetRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT tweet_id, tweet_url, author_handle, posted_at_iso, text, scraped_at_iso
                FROM tweets
                ORDER BY posted_at_iso DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [
            TweetRecord(
                tweet_id=row[0],
                tweet_url=row[1],
                author_handle=row[2],
                posted_at_iso=row[3],
                text=row[4],
                scraped_at_iso=row[5],
            )
            for row in rows
        ]

    def filter_unpushed(self, tweets: list[TweetRecord]) -> list[TweetRecord]:
        if not tweets:
            return []

        ids = [item.tweet_id for item in tweets]
        placeholders = ",".join(["?"] * len(ids))
        with self._connect() as conn:
            rows = conn.execute(
                f"SELECT tweet_id FROM telegram_push_history WHERE tweet_id IN ({placeholders})",
                ids,
            ).fetchall()

        pushed = {row[0] for row in rows}
        return [item for item in tweets if item.tweet_id not in pushed]

    def mark_pushed(self, tweets: list[TweetRecord], pushed_at_iso: str) -> None:
        if not tweets:
            return
        rows = [(item.tweet_id, pushed_at_iso) for item in tweets]
        with self._connect() as conn:
            conn.executemany(
                (
                    "INSERT OR IGNORE INTO telegram_push_history "
                    "(tweet_id, pushed_at_iso) VALUES (?, ?)"
                ),
                rows,
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)
