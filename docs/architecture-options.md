# Architecture Options

## Option A: Single Container

- Compose file: `docker-compose.yml`
- One service runs scrape + persistence + notification
- Lowest complexity and fastest delivery

## Option B: CDP Sidecar

- Compose file: `docker-compose.cdp-sidecar.yml`
- Browser process is isolated in `browser` service
- Better separation for browser tuning and restarts

## Option C: API-first Hybrid

- Not implemented in this repository
- Intended direction for higher SLA and compliance
- Browser automation retained only as fallback path
