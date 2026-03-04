FROM mcr.microsoft.com/playwright/python:v1.51.0-noble

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY scripts /app/scripts
COPY config /app/config

RUN pip install --upgrade pip \
    && pip install -e . \
    && playwright install chromium \
    && chmod +x /app/scripts/entrypoint.sh /app/scripts/healthcheck.sh \
    && mkdir -p /app/data /app/output /app/runtime \
    && chown -R pwuser:pwuser /app

USER pwuser

CMD ["/app/scripts/entrypoint.sh"]
