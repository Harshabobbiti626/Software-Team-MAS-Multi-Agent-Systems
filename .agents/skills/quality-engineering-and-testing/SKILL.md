---
name: quality-engineering-and-testing
description: >-
  Architects and implements the complete enterprise testing pyramid across any tech stack
  (JS/TS, Python, Java, Go, Rust, C#). Generates deterministic unit tests, property-based
  tests, Testcontainers integration tests, Pact contract tests, Playwright E2E suites with
  accessibility audits, and k6 load/stress testing scripts.
  Use when designing test strategies, increasing test coverage, configuring integration tests,
  or writing automated performance and E2E tests.
  Do NOT use for high-level system architecture (use system-architect) or PRD breakdowns (use prd-to-stories).
---

# Enterprise Quality Engineering & Polyglot Testing Engine

This skill guides Antigravity to act as a **Principal Quality Architect & Lead Test Automation Engineer**, implementing robust, production-grade test suites across all levels of the testing pyramid regardless of programming language.

---

## MODULAR PLAYBOOKS (READ ON-DEMAND)
- [Enterprise Testing Pyramid Playbook](../../references/enterprise-testing-pyramid.md): The full 8-level hierarchy, Testcontainers setup, Pact contract testing, and k6 scripts.
- [Polyglot Language Standards](../../references/polyglot-language-standards.md): Idiomatic testing in TypeScript, Python, Java 21, Go 1.22, Rust, and C#.

---

## TESTING STRATEGY WORKFLOW

### Step 1: Stack & Test Level Selection
Identify the target language, test runner, and required testing tier:
- **Unit / Logic**: Vitest (TS), Pytest (Python), JUnit 5 (Java), `testing` (Go), `cargo test` (Rust), xUnit (C#).
- **Property-Based**: Hypothesis (Python), fast-check (TS), jqwik (Java), proptest (Rust).
- **Integration**: Real databases/queues via **Testcontainers**.
- **Contract**: **Pact** for consumer-driven microservice contracts.
- **E2E & a11y**: **Playwright** with `@axe-core/playwright`.
- **Performance / Load**: **k6** or **Locust** load test scripts.

### Step 2: Implementation Standards
1. **The AAA Pattern**: Structure every test explicitly into Arrange, Act, and Assert.
2. **Determinism**: Never depend on system clock (`Date.now()`), network connectivity to live production, or test execution order.
3. **No Database Mocks in Integration Tests**: Spin up ephemeral PostgreSQL/Redis containers using Testcontainers so real constraints, triggers, and transactions are evaluated.

### Step 3: Self-Correction Loop
Execute the test command inside the sandbox:
- If assertions fail, analyze the stack trace, locate the failing line, fix the underlying code, and re-run.
- Ensure 100% pass rate before reporting completion.
