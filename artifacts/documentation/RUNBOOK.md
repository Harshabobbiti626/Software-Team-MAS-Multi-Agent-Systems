# Operations Runbook: Cost Tracking Test Mission

## Deployment & Rollout
1. Run database migrations:
   ```bash
   psql -f artifacts/schema_sql/schema.sql
   ```
2. Start service container:
   ```bash
   docker run -p 8080:8080 mas-service:latest
   ```

## Incident Recovery Playbook
- **High Latency (> 150ms)**: Inspect Postgres active queries for lock contention on `idx_resources_category_status`.
- **Health Check Failure**: Verify process health via `/health` endpoint and review memory metrics.
