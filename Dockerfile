# Production Multi-Stage Container for MAS (Multi-Agent Software Engineering System)
FROM python:3.13-slim AS base

# System dependencies: git for worktrees/versioning, curl for container healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged system user
RUN groupadd -g 10001 mas && \
    useradd -u 10001 -g mas -s /bin/bash -m mas

WORKDIR /app

# Copy dependency specifications first for optimal Docker layer caching
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY --chown=mas:mas . .

# Set permissions for unprivileged user
RUN chown -R mas:mas /app

USER mas

# Environment configuration
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    HOST=0.0.0.0

EXPOSE 8000

# Container healthcheck asserting /api/v1/health returns 200 OK
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

ENTRYPOINT ["python", "main.py", "web", "--host", "0.0.0.0", "--port", "8000"]

