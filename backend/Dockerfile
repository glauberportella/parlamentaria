##############################################################################
# Stage 1 — Builder: install dependencies
##############################################################################
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
# Install production dependencies only
RUN pip install --no-cache-dir --prefix=/install .


##############################################################################
# Stage 2 — Runtime: lean production image
##############################################################################
FROM python:3.12-slim AS runtime

LABEL maintainer="Parlamentaria <contato@parlamentaria.app>"
LABEL org.opencontainers.image.description="Parlamentaria API — plataforma agêntica legislativa"

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Security: run as non-root user
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Install Playwright Chromium browser and system dependencies
RUN pip install --no-cache-dir playwright \
    && playwright install --with-deps chromium

WORKDIR /app

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Copy Alembic configuration and migrations
COPY alembic.ini ./alembic.ini
COPY alembic/ ./alembic/

# Copy application code
COPY app/ ./app/

# Create directory for social media generated images
RUN mkdir -p /app/data/social_images && chown appuser:appuser /app/data/social_images

# Non-root user
USER appuser

EXPOSE 8000

# Gunicorn + Uvicorn workers for production
# Workers = 2 * CPU cores + 1 (set via WEB_CONCURRENCY env var)
ENV WEB_CONCURRENCY=2
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f -H "Host: parlamentaria.app" http://localhost:8000/health || exit 1

CMD ["python", "-m", "gunicorn", "app.main:app", \
     "-w", "${WEB_CONCURRENCY}", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
