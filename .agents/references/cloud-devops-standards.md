# CLOUD, DEVOPS & INFRASTRUCTURE STANDARDS PLAYBOOK
## Production Guidelines for Containers, Kubernetes, Terraform & CI/CD

---

## 1. CONTAINER SECURITY & MULTI-STAGE BUILDS
Never ship developer tools, package managers, or source compilers into production images:

```dockerfile
# Stage 1: Build & Compile
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json pnpm-lock.yaml ./
RUN npm install -g pnpm && pnpm install --frozen-lockfile
COPY . .
RUN pnpm build && pnpm prune --prod

# Stage 2: Distroless / Minimal Runtime
FROM gcr.io/distroless/nodejs22-debian12:nonroot
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json
USER nonroot
EXPOSE 3000
CMD ["dist/server.js"]
```

- **Non-Root User**: Always execute containers under an unprivileged user (`nonroot` or `USER 10001`).
- **Read-Only Root Filesystem**: Configure container runtimes to prevent writing to disk (`readOnlyRootFilesystem: true`).

---

## 2. KUBERNETES RESILIENCE BENCHMARKS
- **Explicit Resource Boundaries**:
  Always set `resources.requests` (for scheduling) and `resources.limits` (for OOM prevention).
- **Probes**:
  - `startupProbe`: Allows slow application warm-ups (loading caches/models) without triggering restart loops.
  - `readinessProbe`: Removes pod from Service routing if downstream DB connection drops.
  - `livenessProbe`: Restarts deadlocked processes.
- **Graceful Termination**: Listen for `SIGTERM`, wait for active HTTP connections to complete (drain period), then close DB connection pools.

---

## 3. INFRASTRUCTURE AS CODE & IAM (TERRAFORM)
- **Least-Privilege RBAC**:
  Never use wildcard permissions (`"Action": "*"`). Grant only the exact verbs needed for the target resource.
- **Workload Identity Federation (OIDC)**:
  Authenticate GitHub Actions CI/CD to AWS/GCP via short-lived OIDC tokens. Never store permanent cloud access keys in GitHub Secrets.
