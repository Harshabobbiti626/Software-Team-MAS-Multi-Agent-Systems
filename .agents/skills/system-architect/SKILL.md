---
name: system-architect
description: >-
  Provides principal-level system architecture, high-level and low-level design (HLD/LLD),
  database modeling, API contract definition, scaling analysis, and living Architecture
  Decision Records (ADRs). Use when designing a new service, database schema, API, or
  refactoring existing architectures for scale and reliability.
  Do NOT use for PRD requirements breakdown into user stories (use prd-to-stories),
  searching libraries/codebase (use deep-search-and-execute), or auditing completed code (use production-code-reviewer).
---

# Principal System Architecture Engine

This skill guides Antigravity in delivering enterprise-grade system designs that balance delivery speed with long-term evolvability, resilience, and operational simplicity.

---

## MODULAR REFERENCE PLAYBOOKS (READ ON-DEMAND)
To optimize token consumption, consult these deep-dive reference playbooks only when designing that specific tier:
- [Cross-Tier Full-Stack Cohesion](../../references/interlinked-fullstack-workflow.md): Type SSOT, mutation lifecycle, trace propagation, zero-downtime migrations.
- [Database & Storage Standards](../../references/database-storage-standards.md): 3NF schema, UUIDv7, B-tree/GIN/BRIN indexing, Redis cache stampede defense.
- [Backend & API Standards](../../references/backend-api-standards.md): Hexagonal architecture, RFC 7807 problem details, idempotency, cursor pagination.
- [Cloud & DevOps Standards](../../references/cloud-devops-standards.md): Minimal Distroless Docker, K8s probes/limits, Terraform least-privilege IAM.
- [AI/ML & GenAI Standards](../../references/ai-ml-genai-standards.md): Hybrid RAG (dense + BM25 + rerank), agent recursion guardrails.

---

## ARCHITECTURAL WORKFLOW

### Phase 1: Requirements & Quantitative Bounds
Calculate back-of-the-envelope numbers before proposing any architecture:
- **Throughput**: Peak requests per second (RPS), read-to-write ratio.
- **Data Volume**: Storage growth per day/month/year.
- **Latency SLOs**: p95 and p99 response times (e.g., < 100ms).
- **Availability Target**: 99.9% vs. 99.99% (acceptable downtime per year).
- **Consistency Model**: Strict ACID vs. Eventual Consistency (CAP theorem trade-offs).

### Phase 2: Structural Architecture (C4 Model)
1. **Context Level**: External actors, third-party systems, user touchpoints (Mermaid diagram).
2. **Container Level**: Web apps, mobile clients, API gateways, microservices, databases, queues, caches.
3. **Component Level**: Internal services, repositories, domain handlers.
4. **Data Flow**: Sequence diagrams representing critical user paths.

### Phase 3: Data Tier & Contract Specification
- **Engine Selection**: Relational (PostgreSQL) vs. Analytical (ClickHouse/BigQuery) vs. Cache (Redis).
- **Schema & Indexes**: Tables, primary keys (UUIDv7), foreign keys, composite indexes.
- **API Contracts**: REST (RFC 7807) / gRPC / WebSockets with idempotency keys.

### Phase 4: Architecture Decision Record (ADR)
Document every major decision using standard ADR structure (Context, Drivers, Considered Options, Outcome, Pros/Cons, Mitigation).
See [ADR Template](../../../templates/ADR_TEMPLATE.md).
