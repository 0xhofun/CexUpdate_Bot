#!/usr/bin/env bash
set -euo pipefail

CONFIG_PATH="${XLM_CONFIG_PATH:-/app/config/config.json}"
RUN_MODE="${XLM_RUN_MODE:-loop}"
RUN_INTERVAL_SECONDS="${XLM_RUN_INTERVAL_SECONDS:-14400}"
MAX_CONSECUTIVE_FAILURES="${XLM_MAX_CONSECUTIVE_FAILURES:-3}"
FAILURE_BACKOFF_SECONDS="${XLM_FAILURE_BACKOFF_SECONDS:-60}"
HEALTH_FILE="${XLM_HEALTH_FILE:-/app/runtime/last_success_epoch}"

if [[ ! -f "${CONFIG_PATH}" ]]; then
  echo "xlist-standalone: config not found at ${CONFIG_PATH}"
  echo "Create it from /app/config/config.example.json"
  exit 1
fi

if ! [[ "${RUN_INTERVAL_SECONDS}" =~ ^[0-9]+$ ]] || [[ "${RUN_INTERVAL_SECONDS}" -le 0 ]]; then
  echo "xlist-standalone: XLM_RUN_INTERVAL_SECONDS must be a positive integer"
  exit 1
fi

if ! [[ "${MAX_CONSECUTIVE_FAILURES}" =~ ^[0-9]+$ ]]; then
  echo "xlist-standalone: XLM_MAX_CONSECUTIVE_FAILURES must be an integer"
  exit 1
fi

if ! [[ "${FAILURE_BACKOFF_SECONDS}" =~ ^[0-9]+$ ]] || [[ "${FAILURE_BACKOFF_SECONDS}" -le 0 ]]; then
  echo "xlist-standalone: XLM_FAILURE_BACKOFF_SECONDS must be a positive integer"
  exit 1
fi

mkdir -p "$(dirname "${HEALTH_FILE}")"

run_once() {
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] run start"
  xlist-standalone run --config "${CONFIG_PATH}"
  date +%s > "${HEALTH_FILE}"
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] run done"
}

if [[ "${RUN_MODE}" == "once" ]]; then
  run_once
  exit 0
fi

consecutive_failures=0
while true; do
  if run_once; then
    consecutive_failures=0
    sleep "${RUN_INTERVAL_SECONDS}"
    continue
  fi

  consecutive_failures=$((consecutive_failures + 1))
  echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] run failed (${consecutive_failures}/${MAX_CONSECUTIVE_FAILURES})"

  if [[ "${MAX_CONSECUTIVE_FAILURES}" -gt 0 ]] && [[ "${consecutive_failures}" -ge "${MAX_CONSECUTIVE_FAILURES}" ]]; then
    echo "[$(date -u +"%Y-%m-%dT%H:%M:%SZ")] max consecutive failures reached, exiting"
    exit 1
  fi

  sleep "${FAILURE_BACKOFF_SECONDS}"
done
