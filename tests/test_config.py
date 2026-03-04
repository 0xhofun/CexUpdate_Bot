from __future__ import annotations

import json

import pytest

from xlist_monitor_standalone.config import load_config


def _write_config(tmp_path, payload: dict) -> str:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return str(path)


def test_load_config_requires_list_url(tmp_path) -> None:
    _write_config(tmp_path, {"headless": True})
    with pytest.raises(ValueError):
        load_config(tmp_path / "config.json")


def test_load_config_appends_browserless_token(tmp_path, monkeypatch) -> None:
    payload = {"list_url": "https://x.com/i/lists/123", "cdp_url": "ws://browser:3000"}
    _write_config(tmp_path, payload)
    monkeypatch.setenv("BROWSERLESS_TOKEN", "abc123")

    cfg = load_config(tmp_path / "config.json")
    assert cfg.cdp_url == "ws://browser:3000?token=abc123"


def test_load_config_does_not_duplicate_token(tmp_path, monkeypatch) -> None:
    payload = {"list_url": "https://x.com/i/lists/123", "cdp_url": "ws://browser:3000?token=old"}
    _write_config(tmp_path, payload)
    monkeypatch.setenv("BROWSERLESS_TOKEN", "abc123")

    cfg = load_config(tmp_path / "config.json")
    assert cfg.cdp_url == "ws://browser:3000?token=old"


def test_load_config_env_override_no_sandbox(tmp_path, monkeypatch) -> None:
    payload = {"list_url": "https://x.com/i/lists/123", "allow_insecure_no_sandbox": False}
    _write_config(tmp_path, payload)
    monkeypatch.setenv("XLM_ALLOW_INSECURE_NO_SANDBOX", "true")

    cfg = load_config(tmp_path / "config.json")
    assert cfg.allow_insecure_no_sandbox is True
