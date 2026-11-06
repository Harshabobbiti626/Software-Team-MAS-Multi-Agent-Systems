# Multi-stage hardened Dockerfile for Cost Tracking Test Mission
# Service: cost-tracking-test-mission
# Production non-root container with security context and health check

FROM python:3.13-slim AS builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt* pyproject.toml* ./
RUN pip install --no-cache-dir --upgrade pip \
 && if [ -f requirements.txt ]; then pip install --no-cache-dir --user -r requirements.txt; fi

FROM python:3.13-slim AS runtime
WORKDIR /app
RUN useradd -u 10001 -m appuser
USER appuser
COPY --from=builder /root/.local /home/appuser/.local
COPY --chown=appuser:appuser . .
ENV PATH=/home/appuser/.local/bin:$PATH
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1
CMD ["python", "main.py"]
