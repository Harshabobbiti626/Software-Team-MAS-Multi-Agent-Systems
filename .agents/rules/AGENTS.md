# PROJECT-LEVEL AGENTS CONSTITUTION

This project inherits the Universal Cognitive Operating System (AGY-OS) from `~/.gemini/GEMINI.md`. All contributions must adhere to the following project-specific execution standards.

---

## 1. PROJECT STATE MACHINE & CONTEXT CONTINUITY
- At the start of any complex feature or refactor, read `.agents/STATE.md` if present to reload current architecture, active decisions, and progress.
- Update `.agents/STATE.md` upon completing major milestones, recording newly introduced patterns, environment variables, or schema migrations.

---

## 2. SURGICAL EXECUTION PRINCIPLES
- **No Half-Baked Code**: Never produce placeholder implementations (`// TODO: add later`). Write the complete, production-ready implementation, including error handling and edge cases.
- **Defensive Type Safety**: Strict TypeScript/typed Python/Go/Rust. No `any` escapes without explicit architectural rationale.
- **Fail Fast, Fail Loudly**: Validate inputs at boundary entrypoints (APIs, CLI flags, database adapters). Do not allow malformed state to propagate.
- **Zero Regressions**: Before finalizing edits, ensure existing unit and integration tests pass. If modifying an interface, update all downstream consumers.

---

## 3. REAL-TIME REQUIREMENTS SCOPING & STORIES
- If given a broad task or design document:
  1. Auto-catchup domain context from `.agents/knowledge/domain-model.md` and `.agents/STATE.md`.
  2. Ingest document into `.agents/knowledge/design-docs/`.
  3. Structure the Scope Boundary Matrix (**Strictly In-Scope P0** vs. **Explicitly Out-of-Scope Non-Goals**) and INVEST User Stories with Gherkin BDD.
  4. **MANDATORY APPROVAL GATE**: Halt and present the execution plan to the developer for review and approval.
  5. Only start writing production code after the developer approves the plan.

---

## 4. HUMAN-CENTRIC CODE & DOCUMENTATION
- Write code that reads like well-authored literature: clear domain nouns, explicit verbs, zero cryptic abbreviations.
- For architectural pivots or non-obvious design choices, create or update an ADR in `docs/adr/`.

---

## 5. MANDATORY USER STORY DEFINITION OF DONE (DoD)
When implementing any User Story or feature, verify all 10 production pillars before declaring completion:
1. **Defensive Validation**: Ingress schema verification (Zod/Pydantic) before business logic.
2. **Authorization & IDOR**: Session-derived tenant/user checks on every object read/write.
3. **Atomic Data & Indexes**: Explicit ACID transaction on multi-table writes; composite B-Tree indexes on query filter columns.
4. **Concurrency & Idempotency**: `Idempotency-Key` headers for mutations; optimistic/pessimistic locking.
5. **RFC 7807 Errors**: Structured `{ type, title, status, detail, instance }` payloads (zero blank 500s).
6. **Timeouts & Cancellation**: Explicit HTTP/RPC timeouts; `ctx.Done()` / `AbortController` propagation.
7. **Frontend 4-State UI**: Loading skeleton (fixed aspect ratio), Empty state (with CTA), Error state (with retry), Populated state.
8. **Accessibility & Core Web Vitals**: WCAG 2.1 AA/AAA keyboard navigation, ARIA labels, zero layout shifts (CLS < 0.1).
9. **Deterministic Tests**: Boundary unit tests (null, empty, negative, max limits) + real DB integration tests.
10. **Telemetry & State Sync**: Structured JSON logs with trace correlation; update `.agents/STATE.md`.
