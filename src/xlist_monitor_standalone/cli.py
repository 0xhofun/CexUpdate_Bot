from __future__ import annotations

import argparse
from pathlib import Path

from xlist_monitor_standalone.config import load_config
from xlist_monitor_standalone.runner import Runner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Standalone X list monitor")
    parser.add_argument("command", choices=["run"], nargs="?", default="run")
    parser.add_argument("--config", default="/app/config/config.json")
    return parser



def main() -> None:
    args = build_parser().parse_args()
    cfg_path = Path(args.config)
    if not cfg_path.exists():
        raise SystemExit(f"Config not found: {cfg_path}")

    config = load_config(cfg_path)
    summary = Runner(config).run_once()

    print(f"Scraped tweets: {summary.scraped}")
    print(f"Inserted tweets: {summary.inserted}")
    print(f"Raw dump: {summary.raw_dump_path}")
    print(f"Digest: {summary.digest_path}")


if __name__ == "__main__":
    main()
