# X List Monitor Standalone

A fully standalone container-first monitor for X list timelines.

This repository is independent from your existing `x-list-monitor` workflow.

## What it does

- Scrapes X list timeline with Playwright
- Stores deduplicated tweets in SQLite
- Writes raw JSON snapshots and Markdown digest files
- Optionally pushes new tweets to Telegram
- Runs once or in loop mode under Docker Compose

## Quick Start (Option A: single-container)

1. Prepare config and env:

```bash
cd CexUpdate_Bot
cp config/config.example.json config/config.json
cp .env.example .env
```

2. Edit `config/config.json` and set `list_url`

3. Run one round:

```bash
XLM_RUN_MODE=once docker compose up --build --abort-on-container-exit
```

4. Run as service:

```bash
docker compose up -d --build
docker compose logs -f monitor
```

If your host bind-mount permissions block writes (because the container now defaults to `pwuser`), set:

```bash
XLM_CONTAINER_USER=0:0 docker compose up -d --build
```

## Deployment Options Comparison

### Option A: Single-container browser automation (default)

- Stack: one `monitor` service in `docker-compose.yml`
- Pros: simplest deployment, fastest handoff
- Cons: browser runtime and business logic are coupled
- Best for: internal best-effort monitoring

### Option B: Dedicated browser sidecar (CDP)

- Stack: `monitor + browser` in `docker-compose.cdp-sidecar.yml`
- Pros: browser lifecycle isolation, easier browser-node tuning
- Cons: extra component and network path
- Best for: medium-scale workloads and cleaner operational boundaries

Run Option B:

```bash
cp config/config.cdp.example.json config/config.cdp.json
BROWSERLESS_TOKEN=replace_me docker compose -f docker-compose.cdp-sidecar.yml up -d --build
```

The browser sidecar is internal-only by default (no host port mapping). If you intentionally need host access, add a temporary `ports` mapping in `docker-compose.cdp-sidecar.yml`.

Use explicit CDP override only when needed:

```bash
XLM_CDP_URL=ws://browser:3000?token=replace_me docker compose -f docker-compose.cdp-sidecar.yml up -d --build
```

### Option C: API-first hybrid (recommended for production SLA)

- Stack: official X API as primary ingestion + browser fallback for edge cases
- Pros: best stability/compliance posture
- Cons: API approval, billing, dual-path complexity
- Best for: production-critical pipelines

## Session persistence (important)

- Browser login/session state is persisted at `user_data_dir` (default `/app/runtime/chrome-data`).
- Keep `./runtime:/app/runtime` mounted to avoid losing session between container restarts.
- `allow_insecure_no_sandbox` defaults to `false`; only set it `true` in trusted environments where sandbox cannot run.

## Data paths

- SQLite: `./data/x_list_monitor.db`
- Raw dumps: `./data/raw/*.json`
- Digests: `./output/digest_*.md`

## Runtime env vars

- `XLM_CONFIG_PATH` config path inside container
- `XLM_RUN_MODE` `once` or `loop`
- `XLM_RUN_INTERVAL_SECONDS` loop interval
- `XLM_MAX_CONSECUTIVE_FAILURES` loop failure threshold (`0` means never stop)
- `XLM_FAILURE_BACKOFF_SECONDS` wait time after each failed run
- `XLM_ALLOW_INSECURE_NO_SANDBOX` optional override (`true/false`)
- `XLM_CONTAINER_USER` container user (default `pwuser`)
- `XLM_HEALTH_MAX_AGE_SECONDS` max age of last successful run heartbeat
- `TELEGRAM_BOT_TOKEN` optional
- `TELEGRAM_CHAT_ID` optional
- `XLM_CDP_URL` optional override for CDP mode
- `BROWSERLESS_TOKEN` required for CDP sidecar mode

## Operational hardening

- Entrypoint now exits after repeated failures, so orchestrator restart policy can recover cleanly.
- Telegram push includes retry/backoff and message length clipping.
- Compose applies `no-new-privileges`, drops Linux capabilities, and adds a healthcheck.

## Notes

- This project is designed for server hosting, not desktop launchd.
- Browser automation against X still has anti-bot/session-risk; treat it as best-effort unless you move to API-first architecture.
- When policy/compliance is strict, prefer API-first and keep browser automation only as a fallback.
