from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class TweetRecord:
    tweet_id: str
    tweet_url: str
    author_handle: str
    posted_at_iso: str
    text: str
    scraped_at_iso: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class RunSummary:
    scraped: int
    inserted: int
    raw_dump_path: str
    digest_path: str


@dataclass(frozen=True)
class TelegramConfigValue:
    enabled: bool
    bot_token: str | None
    chat_id: str | None
    max_posts_per_round: int


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
