FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

WORKDIR /app

# Install dependencies first (cached layer — only invalidated when lock file changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy application source
COPY main.py cron_crawl.py web.py ./
COPY sfbot/ ./sfbot/
COPY templates/ ./templates/

# Directories — will be bind-mounted at runtime
RUN mkdir -p logs account_data

CMD ["uv", "run", "main.py"]
