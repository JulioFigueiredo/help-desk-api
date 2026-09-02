# Stage 1: Base image with Python 3.12 slim
FROM python:3.12-slim AS base

# Install uv from official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Configure environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

# Copy dependency definition files first (layer caching optimization)
COPY pyproject.toml uv.lock README.md ./

# Install dependencies into virtual environment without development dependencies
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source code and migrations
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

# Install the application itself
RUN uv sync --frozen --no-dev

# Create non-privileged user for security
RUN groupadd -r appgroup && useradd -r -g appgroup -u 10001 appuser && \
    chown -R appuser:appgroup /app

USER appuser

# Expose API port
EXPOSE 8000

# Health check using standard python urllib (avoids extra curl installation)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Default command to run the API
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
