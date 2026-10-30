---
name: production-code-reviewer
description: >-
  Audits codebases, pull requests, and implementations against elite industry
  standards for security (OWASP), concurrency, performance, error resilience,
  type integrity, and test completeness. Use when reviewing code, auditing pull
  requests, diagnosing architectural code smell, or preparing for production release.
  Do NOT use for designing new systems from scratch (use system-architect),
  breaking down PRDs (use prd-to-stories), or conducting initial exploratory searches (use deep-search-and-execute).
---

# Principal Engineer Production Code Reviewer

This skill guides Antigravity to conduct deep-tier code audits that surface latent bugs, race conditions, security vulnerabilities, and scalability bottlenecks before code hits staging or production.

---

## MODULAR AUDIT REFERENCES (READ ON-DEMAND)
Consult the relevant domain playbooks to verify compliance with production standards:
- [Cross-Tier Cohesion](../../references/interlinked-fullstack-workflow.md): Verify type-sharing and trace propagation.
- [Frontend Standards](../../references/frontend-standards.md): WCAG AA/AAA, Core Web Vitals, smart/dumb separation.
- [Backend Standards](../../references/backend-api-standards.md): RFC 7807 problem details, idempotency keys, rate limits.
- [Database Standards](../../references/database-storage-standards.md): Prevent N+1 queries, verify composite indexing.
- [Cloud & Security](../../references/cloud-devops-standards.md): Container security, non-root users, secret scanning.

---

## 7-PILLAR AUDIT RUBRIC

### 1. Security & Hygiene (OWASP Top 10)
- Parameterized SQL queries (zero string concatenation in queries).
- Broken Object-Level Authorization (BOLA/IDOR) checks on every endpoint.
- Sensitive fields (passwords, tokens, PII) stripped before serialization.

### 2. Concurrency & State Integrity
- Atomic transactions with proper isolation (`SELECT ... FOR UPDATE` or CAS checks).
- Lock hierarchy consistency (prevent deadlocks).
- Disposed timers, socket connections, and event listeners (prevent memory leaks).

### 3. Error Handling & Resilience
- Boundary schema validation on all inputs (Zod/Pydantic).
- Zero swallowed errors (`catch (e) {}` with no logging is an instant blocker).
- Graceful degradation when external dependencies fail.

### 4. Performance & Resource Utilization
- Eager loading / batching / DataLoaders to eliminate N+1 query patterns.
- $O(n)$ HashMap lookups instead of nested $O(n^2)$ array searches.
- Streamed I/O for large payloads to avoid memory spikes.

### 5. Type Safety & API Contracts
- Strict typing (zero `any`, exhaustive union handling).
- Non-nullable verification before dereferencing.

### 6. Test Integrity & Edge Coverage
- Explicit boundary tests (null, empty, negative, max integer).
- Deterministic tests (zero dependency on system clock or execution order).

### 7. Human Readability & Maintainability
- Ubiquitous business domain naming.
- Single Responsibility Principle (functions under 50 lines).

---

## AUDIT OUTPUT FORMAT
Categorize findings by severity:
- **Critical Blockers** (Must Fix Before Deploy): Security, concurrency, memory leaks.
- **Major Improvements**: Performance, N+1 queries, missing validation.
- **Minor Refactors**: Style alignments, comment corrections.
