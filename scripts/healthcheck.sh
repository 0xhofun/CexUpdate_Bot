#!/usr/bin/env bash
set -euo pipefail

HEALTH_FILE="${XLM_HEALTH_FILE:-/app/runtime/last_success_epoch}"
MAX_AGE_SECONDS="${XLM_HEALTH_MAX_AGE_SECONDS:-21600}"

if ! [[ "${MAX_AGE_SECONDS}" =~ ^[0-9]+$ ]] || [[ "${MAX_AGE_SECONDS}" -le 0 ]]; then
  echo "invalid XLM_HEALTH_MAX_AGE_SECONDS"
  exit 1
fi

if [[ ! -f "${HEALTH_FILE}" ]]; then
  echo "health file missing: ${HEALTH_FILE}"
  exit 1
fi

last_epoch="$(cat "${HEALTH_FILE}" 2>/dev/null || true)"
if ! [[ "${last_epoch}" =~ ^[0-9]+$ ]]; then
  echo "invalid health timestamp"
  exit 1
fi

now_epoch="$(date +%s)"
age_seconds=$((now_epoch - last_epoch))
if [[ "${age_seconds}" -gt "${MAX_AGE_SECONDS}" ]]; then
  echo "health timestamp stale: ${age_seconds}s"
  exit 1
fi
