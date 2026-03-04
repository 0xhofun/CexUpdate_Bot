from __future__ import annotations

import json
import os
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class TelegramConfig(BaseModel):
    enabled: bool = False
    bot_token: str | None = None
    chat_id: str | None = None
    max_posts_per_round: int = Field(default=10, ge=1, le=50)


class MonitorConfig(BaseModel):
    list_url: str | None = None
    cdp_url: str | None = None
    user_data_dir: str = "/app/runtime/chrome-data"
    headless: bool = True
    max_scrolls: int = Field(default=20, ge=1, le=500)
    sleep_seconds: float = Field(default=1.2, gt=0, le=30)
    scrape_timeout_seconds: int = Field(default=240, ge=30, le=3600)
    exclude_reposts: bool = True
    allow_insecure_no_sandbox: bool = False

    db_path: str = "/app/data/x_list_monitor.db"
    raw_dump_dir: str = "/app/data/raw"
    output_dir: str = "/app/output"

    telegram: TelegramConfig = Field(default_factory=TelegramConfig)

    @model_validator(mode="after")
    def validate_targets(self) -> "MonitorConfig":
        if self.list_url and self.list_url.strip():
            return self
        raise ValueError("list_url is required")

    def monitor_urls(self) -> list[str]:
        return [self.list_url] if self.list_url else []



def load_config(path: Path) -> MonitorConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    cfg = MonitorConfig.model_validate(raw)

    # Environment overrides for deployment.
    env_cdp = os.getenv("XLM_CDP_URL", "").strip()
    if env_cdp:
        cfg.cdp_url = env_cdp

    env_browserless_token = os.getenv("BROWSERLESS_TOKEN", "").strip()
    if cfg.cdp_url and env_browserless_token and "token=" not in cfg.cdp_url:
        sep = "&" if "?" in cfg.cdp_url else "?"
        cfg.cdp_url = f"{cfg.cdp_url}{sep}token={env_browserless_token}"

    env_allow_no_sandbox = os.getenv("XLM_ALLOW_INSECURE_NO_SANDBOX", "").strip().lower()
    if env_allow_no_sandbox in {"1", "true", "yes", "on"}:
        cfg.allow_insecure_no_sandbox = True

    if cfg.telegram.enabled:
        cfg.telegram.bot_token = cfg.telegram.bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        cfg.telegram.chat_id = cfg.telegram.chat_id or os.getenv("TELEGRAM_CHAT_ID")

    return cfg
