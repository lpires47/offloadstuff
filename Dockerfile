# The test app plus a real Chromium for searching and listing as the user.
FROM mcr.microsoft.com/playwright/python:v1.55.0-noble
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[web]" pillow-heif   # Playwright + Chromium come with the base image
COPY data ./data
ENV PORT=8000 OFFLOAD_SESSIONS_DIR=/data/sessions OFFLOAD_ROUTER_STATS=/data/router_stats.json
CMD ["sh", "-c", "mkdir -p /data/sessions && uvicorn offload.web.app:app --host 0.0.0.0 --port ${PORT}"]
