# THE MASTER ENTERPRISE ENGINEERING CHECKLIST (360° TOTAL COVERAGE)
## Exhaustive Technical Verification Matrix Across All 12 Software Engineering Disciplines

This document codifies the non-negotiable architectural, engineering, operational, and security standards enforced by Principal and Staff Engineers across top-tier software organizations globally.

---

## 1. FRONTEND ENGINEERING (WEB & SPA)

### State Architecture & Data Flow
- [ ] **State Hierarchy Separation**:
  - **URL State**: Query parameters (`?tab=orders&page=2&filter=active`) shareable and bookmarkable via URL.
  - **Server State**: Managed via TanStack Query / SWR / Apollo (stale-while-revalidate, optimistic updates, cache invalidation tags).
  - **Global Client State**: Lightweight store (Zustand) strictly for session, theme, and ephemeral shopping cart.
  - **Local State**: `useState` / `useReducer` kept strictly inside leaf components.
- [ ] **Prop Drilling Elimination**: Use component composition (`children` slots) or hoisted context/Zustand rather than passing props deeper than 2 layers.
- [ ] **Form Handling**: Use uncontrolled forms with `useForm` (React Hook Form) + Zod schema validation to eliminate re-renders on every keystroke.

### Rendering Performance & DOM Optimization
- [ ] **DOM & Reconciliation**: Unique, stable `key` attributes on lists (using UUIDs/IDs; never array indices on mutable lists).
- [ ] **List Virtualization**: Implement `@tanstack/react-virtual` for lists $> 100$ items to prevent DOM bloat and memory leaks.
- [ ] **Memoization Hygiene**:
  - `useMemo` for expensive array transformations ($O(N \log N)$ sorting/filtering).
  - `useCallback` for stable function references passed to memoized children (`React.memo`).
- [ ] **Debouncing & Throttling**:
  - **Debounce** search input events (300ms) to eliminate network request storms.
  - **Throttle** scroll, resize, and mousemove listeners (16ms / 60fps) to eliminate layout thrashing.
- [ ] **Memory Leak Defense**: Explicitly dispose of all `setTimeout`, `setInterval`, `addEventListener`, WebSocket channels, and `AbortController` in component unmount effects (`return () => cleanup()`).

### Core Web Vitals (CWV) & Hydration
- [ ] **LCP (< 2.5s)**: Preload hero images (`priority` / `fetchpriority="high"`), SSR above-the-fold content.
- [ ] **INP (< 200ms)**: Defer heavy computations using `useTransition` / `startTransition` to keep input boxes responsive.
- [ ] **CLS (< 0.1)**: Explicit `width`/`height` or CSS `aspect-ratio` on images, ads, embeds, and skeleton placeholders.
- [ ] **Hydration Error Defense**: Guard browser-only APIs (`window`, `localStorage`) behind `useEffect` or client-only boundaries.
- [ ] **Dynamic Code Splitting**: Lazy-load heavy third-party bundles (charts, rich-text editors, markdown parsers) using `React.lazy` / `next/dynamic`.

### UI Resilience & Accessibility (a11y)
- [ ] **4-State UI Completeness**: Every view component must handle:
  1. *Loading Skeleton* (fixed aspect ratio matching content)
  2. *Populated State* (clean domain rendering with optimistic feedback)
  3. *Empty State* (informative illustration + primary actionable CTA)
  4. *Error State* (user-friendly message + retry button)
- [ ] **Keyboard & Focus Management**: Logical `tabindex`, visible focus indicators (`focus-visible:ring-2`), and focus trapping inside modals.
- [ ] **Screen Reader Support**: `aria-label` on icon buttons, `aria-expanded` on dropdowns, and `aria-live="polite"` for asynchronous notifications.

---

## 2. MOBILE ENGINEERING (REACT NATIVE, FLUTTER, iOS, ANDROID)

### App Lifecycle & Resource Management
- [ ] **Lifecycle State Handling**: Respond cleanly to `active`, `background`, and `inactive` lifecycle events. Suspend expensive timers, animations, and camera streams on backgrounding.
- [ ] **Low Memory Warnings**: Listen for system memory pressure warnings (`didReceiveMemoryWarning` on iOS, `onTrimMemory` on Android) and purge in-memory image caches.
- [ ] **Battery & Network Conservation**: Batch network syncs; use exponential backoff on radio reconnects; defer heavy uploads to Wi-Fi + charging states via WorkManager / BackgroundTasks.

### UI & Performance
- [ ] **60 / 120 FPS Rendering**: Zero heavy computation on the UI/Main thread (offload JSON parsing, crypto, and image filtering to Web Workers / Isolates).
- [ ] **List Virtualization**: `FlatList` / `ListView.builder` configured with `initialNumToRender`, `maxToRenderPerBatch`, and `windowSize`.
- [ ] **Image Optimization**: Local disk caching (FastImage / CachedNetworkImage) with downscaled decoding dimensions matching target pixel density.

### Offline-First & Storage
- [ ] **Local Embedded Database**: SQLite / Room / CoreData / WatermelonDB storing local state with versioned, reversible migrations.
- [ ] **Bi-Directional Conflict Resolution**: Optimistic client mutations queued locally; sync engine resolves conflicts using Last-Write-Wins (LWW) or operational transformation.

---

## 3. BACKEND & API ENGINEERING

### Architecture & Layer Boundaries
- [ ] **Hexagonal / Clean Architecture**: Controllers (Transport) $\rightarrow$ Services (Domain business rules) $\rightarrow$ Repositories (Data access). Zero SQL queries in controllers.
- [ ] **Dependency Inversion**: Services depend on abstract repository interfaces, allowing painless unit testing with fakes.

### Ingress Validation & Defensive Coding
- [ ] **Strict Boundary Validation**: Ingress runtime schema parsing (Zod, Pydantic, class-validator). Strip unknown fields, enforce min/max ranges, string regex.
- [ ] **Fail Fast**: Terminate invalid requests immediately before allocating DB connections or executing expensive computations.

### API Contracts & Transport
- [ ] **RFC 7807 Problem Details**: Structured error responses (`{ type, title, status, detail, instance, invalid_params }`). Zero blank 500s or 200 OK error responses.
- [ ] **HTTP Status Semantics**: Correct usage of 200, 201 (with `Location`), 204, 400, 401, 403, 404, 409, 422, 429, 500.
- [ ] **Idempotency Keys**: Redis-backed `Idempotency-Key` headers on `POST`, `PUT`, `PATCH` to prevent double-charges and duplicated rows.
- [ ] **Cursor-Based Pagination**: Reject offset pagination (`OFFSET 10000`); use time-ordered keys (`WHERE id > :cursor ORDER BY id ASC LIMIT :limit`).
- [ ] **Backpressure & Streaming**: Stream large responses (file downloads, large datasets) instead of buffering entire payloads in memory.

### Resilience & Distributed Safety
- [ ] **Network Timeouts**: Explicit timeouts on all external HTTP/gRPC requests (e.g. 3000ms).
- [ ] **Cancellation Propagation**: Listen for client abort signals (`ctx.Done()`, `AbortController`) and cancel downstream database queries.
- [ ] **Circuit Breakers**: Wrap external dependencies in circuit breakers with fallbacks.
- [ ] **Rate Limiting**: Distributed token-bucket or leaky-bucket rate limiting per IP / User ID using Redis.

---

## 4. DATABASE & STORAGE ENGINEERING (SQL, NOSQL, CACHE, VECTOR)

### Schema Design & Normalization
- [ ] **Third Normal Form (3NF)**: Clean relational schema eliminating update anomalies.
- [ ] **Primary Key Strategy**: Time-ordered UUIDv7 or ULID (combining collision resistance with B-Tree index locality).
- [ ] **Data Integrity Constraints**:
  - `NOT NULL` on mandatory columns.
  - Foreign keys with deliberate `ON DELETE RESTRICT` or `CASCADE`.
  - Check constraints for domain validation (`CHECK (price_cents >= 0)`).
  - Store monetary values as integers (cents/micros) to eliminate floating-point rounding bugs.
  - Timestamps with timezone (`TIMESTAMPTZ NOT NULL DEFAULT now()`).

### Query Performance & Indexing
- [ ] **Index Coverage**:
  - Composite indexes aligned with frequent query filters adhering to the Leftmost Prefix Rule.
  - Partial indexes for high-frequency subsets (`WHERE status = 'ACTIVE'`).
  - GIN indexes for PostgreSQL `JSONB` columns or full-text search.
  - BRIN indexes for large append-only time-series tables.
  - HNSW / IVFFlat indexes for high-dimensional vector embeddings (pgvector).
- [ ] **N+1 Query Elimination**: Eager loading / batch fetching (`IN (...)`) / DataLoaders.
- [ ] **Query Profiling**: Run `EXPLAIN (ANALYZE, BUFFERS)`. Verify zero sequential scans on tables > 1,000 rows.

### Concurrency, Caching & Migrations
- [ ] **Transaction Boundaries**: Multi-table writes wrapped in ACID transactions with appropriate isolation (`READ COMMITTED` or `REPEATABLE READ`).
- [ ] **Race Condition Defense**: Optimistic locking (`version` column) or pessimistic locking (`SELECT ... FOR UPDATE`).
- [ ] **Cache Stampede Defense**: Cache-aside with randomized TTL jitter and distributed mutex locks (`SET lock NX PX`).
- [ ] **Zero-Downtime Migrations**: Expand and Contract pattern (Expand schema $\rightarrow$ Backfill $\rightarrow$ Switch Reads $\rightarrow$ Contract/Drop old column).

---

## 5. DISTRIBUTED SYSTEMS & MICROSERVICES

- [ ] **Strategic DDD Bounded Contexts**: Strict domain boundaries. Database-per-Service mandatory (no shared databases).
- [ ] **Synchronous gRPC / Protobuf**: High-performance HTTP/2 multiplexing, connection pooling, backward-compatible field numbering.
- [ ] **Asynchronous Event-Driven Architecture**: Kafka / RabbitMQ / NATS with partitioned topic keys preserving in-order processing.
- [ ] **Transactional Outbox Pattern**: Atomic local DB commit with an `outbox` table, published via CDC (Debezium) to prevent dual-write loss.
- [ ] **Idempotent Consumers (Inbox Pattern)**: Deduplication table verifying `event_id` before executing business logic.
- [ ] **Orchestrated Saga Pattern**: Central saga state machine managing multi-service workflows with automated compensating rollback actions.
- [ ] **Exponential Backoff with Full Jitter**: Retries using $\text{sleep} = \text{random}(0, \min(M, B \times 2^{\text{attempt}}))$.
- [ ] **Distributed Tracing**: W3C `traceparent` and Baggage propagation across HTTP, gRPC, and Kafka into OpenTelemetry.

---

## 6. MULTI-AGENT SYSTEMS & GENAI

- [ ] **Agent Topology**: Appropriate coordination pattern (Hierarchical Supervisor, Sequential Pipeline, Multi-Agent Debate, or Blackboard).
- [ ] **Structured Outputs Only**: Enforce strict schema constraints (Zod/Pydantic/JSON Schema). Zero loose string parsing.
- [ ] **Hybrid RAG Pipeline**:
  - Structure-aware chunking with 15-20% overlap.
  - Hybrid search (Dense vector + Sparse BM25 via Reciprocal Rank Fusion).
  - Cross-encoder re-ranking top candidates.
  - Isolated context delimiters (`<context>...</context>`) with source citations.
- [ ] **Execution Ceilings & Loop Detection**: Hard limits on tool loop iterations (`max_turns = 10`), cost/token budgets, and tool call hashing to break loops.
- [ ] **Sandboxed Execution**: Shell tools and code execution isolated in sandboxes with least-privilege permissions.
- [ ] **Test-Driven Self-Correction (Reflexion)**: Agent runs tests in sandbox; captures `stderr` and self-heals failing code before presenting results.
- [ ] **Human-in-the-Loop (HITL)**: Mandatory confirmation gates for high-consequence mutations (DB drops, cloud deletions, external payments).

---

## 7. DATA ENGINEERING & PIPELINES (ELT & STREAMING)

- [ ] **Idempotent ELT**: Re-running pipelines on partition dates (`ds = YYYY-MM-DD`) must produce identical results without duplicate rows.
- [ ] **dbt Medallion Layers**: Strict separation: `staging/` (1:1 with source), `intermediate/` (business logic joins), and `marts/` (star schema facts & dims).
- [ ] **Distributed Compute (Spark / BigQuery)**:
  - Broadcast small dimension tables (< 100MB) to eliminate network shuffles.
  - Minimize wide transformations (`groupBy`, `distinct`).
  - Key salting to prevent data skew bottlenecks.
- [ ] **Data Quality & Contracts**: Automated freshness, uniqueness, non-null, and referential integrity assertions. Quarantine bad rows into dead-letter tables.
- [ ] **Streaming Watermarks**: Flink / Spark Structured Streaming configured with late-arriving event handling and watermarks.

---

## 8. CLOUD, DEVOPS & INFRASTRUCTURE AS CODE (IaC)

- [ ] **Container Security**:
  - Multi-stage Docker builds separating build tools from runtime.
  - Minimal Distroless / Alpine base images with zero critical CVEs.
  - Non-root execution (`USER 10001:10001`), read-only root filesystems where possible.
- [ ] **Kubernetes Hardening**:
  - Explicit `resources.requests` and `resources.limits`.
  - Startup, Liveness, and Readiness probes configured with realistic grace periods.
  - Graceful `SIGTERM` draining of HTTP connections and DB pools.
  - PodDisruptionBudgets (PDB) and HorizontalPodAutoscalers (HPA).
- [ ] **Infrastructure as Code (Terraform)**:
  - Remote encrypted state with state locking (S3/DynamoDB or GCS).
  - Least-privilege IAM roles (zero wildcards `*`).
- [ ] **Zero Hardcoded Secrets**: Use OIDC / Workload Identity Federation for cloud authentication. Secrets managed via AWS Secrets Manager / Vault / GCP Secret Manager.

---

## 9. CYBERSECURITY, APPSEC & OWASP TOP 10

- [ ] **Injection Defense**: 100% parameterized SQL / ORM queries. Sanitized shell command arguments.
- [ ] **Broken Object-Level Authorization (BOLA/IDOR)**: Mandatory tenant and ownership verification on every database read/write.
- [ ] **Cross-Site Scripting (XSS) & Content Security Policy (CSP)**:
  - Strict CSP headers (`default-src 'self'`).
  - Context-aware HTML escaping on all rendered user inputs.
- [ ] **CSRF & Session Security**:
  - `SameSite=Lax` or `SameSite=Strict` and `HttpOnly`, `Secure` flags on authentication cookies.
- [ ] **Server-Side Request Forgery (SSRF)**: Validate and whitelist target URLs on webhook dispatchers; block internal loopback/private ranges (`127.0.0.1`, `10.0.0.0/8`, `169.254.169.254`).
- [ ] **Cryptographic Standards**: Passwords hashed with Argon2id or bcrypt (work factor $\ge 12$). Symmetric encryption using AES-256-GCM.
- [ ] **Automated Security Scanning**: Semgrep SAST, Trivy container scanning, and TruffleHog secrets scanning in CI/CD.

---

## 10. ENTERPRISE TESTING PYRAMID & QUALITY ASSURANCE

- [ ] **Level 1 (Unit)**: Deterministic AAA unit tests covering happy paths, edge cases, negative limits, and null states.
- [ ] **Level 2 (Property-Based Fuzzing)**: Randomized testing with Hypothesis/fast-check/proptest asserting mathematical and business invariants.
- [ ] **Level 3 (Architecture Rules)**: ArchUnit / dependency-cruiser asserting package separation rules.
- [ ] **Level 4 (Testcontainers)**: Ephemeral, real PostgreSQL, Redis, or Kafka containers during integration tests (no DB mocks).
- [ ] **Level 5 (Contract Testing)**: Pact consumer/provider contracts preventing breaking API changes in CI/CD.
- [ ] **Level 6 (E2E & a11y)**: Playwright cross-browser automation with `@axe-core/playwright` asserting zero WCAG violations.
- [ ] **Level 7 (Load Testing)**: k6 scripts asserting $p_{95} < 150\text{ ms}$, $p_{99} < 300\text{ ms}$, and error rate $< 1\%$.
- [ ] **Level 8 (Security SAST)**: Static code analysis via Semgrep/SonarQube and dependency vulnerability audits (`npm audit`, `cargo audit`).

---

## 11. SITE RELIABILITY ENGINEERING (SRE) & OBSERVABILITY

- [ ] **The 3 Pillars of Observability**:
  - **Metrics**: RED Method (Rate, Errors, Duration) for services; USE Method (Utilization, Saturation, Errors) for resources.
  - **Structured JSON Logs**: Universal fields (`trace_id`, `span_id`, `user_id`, `environment`, `duration_ms`).
  - **Distributed Tracing**: OpenTelemetry trace spans correlated with database queries and external RPCs.
- [ ] **SLOs, SLIs & Error Budgets**:
  - Documented Service Level Objectives (e.g. 99.9% success rate, p95 latency < 200ms).
  - Automated alerting on Error Budget burn rates (multi-window multi-burn-rate alerts).
- [ ] **Incident Response & Blameless Post-Mortems**:
  - 5-Whys root cause analysis.
  - Permanent automated regression test preventing recurrence.

---

## 12. TECHNICAL PRODUCT MANAGEMENT & SCOPING

- [ ] **Boundary Matrix Enforcement**:
  - **Strictly In-Scope (P0 / Must-Have)**: Locked MVP deliverable.
  - **Explicitly Out-of-Scope (Non-Goals)**: Deliberate omissions preventing scope creep.
  - **Deferred / Phase 2**: Backlog items for subsequent sprints.
- [ ] **INVEST-Compliant User Stories**:
  - Independent, Negotiable, Valuable, Estimable, Small, Testable.
  - Executable Gherkin BDD scenarios (`Given ... When ... Then ...`).
- [ ] **Living Architecture Decision Records (ADRs)**: Documenting context, drivers, evaluated options, chosen outcome, pros/cons, and mitigation strategies.
