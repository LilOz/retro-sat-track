FROM python:3.14-slim AS base
WORKDIR /app

FROM base AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.0 /uv /usr/local/bin/uv
COPY pyproject.toml uv.lock README.md ./
COPY backend/app ./backend/app
RUN uv sync --locked --no-dev --no-editable --no-managed-python --no-cache

FROM base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SAT_TRACK_DATA_DIR=/data

COPY --from=build /app/.venv /app/.venv
RUN mkdir /data && chown 10001:10001 /data
USER 10001:10001

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/status', timeout=3).close()"]
CMD ["/app/.venv/bin/uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
