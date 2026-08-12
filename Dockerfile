FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_LINK_MODE=copy

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    git \
    ca-certificates \
    && groupadd --system monitor \
    && useradd --system --gid monitor --home-dir /app --shell /usr/sbin/nologin monitor \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md alembic.ini ./
COPY migrations ./migrations
COPY src ./src

RUN uv sync --no-dev && uv cache clean
RUN uv run playwright install --with-deps chromium

RUN mkdir -p /app/snapshots /app/data \
    && chown -R monitor:monitor /app

USER monitor

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "monitor_comunitario.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
