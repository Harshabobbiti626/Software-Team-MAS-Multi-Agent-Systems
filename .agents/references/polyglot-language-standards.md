# POLYGLOT LANGUAGE STANDARDS PLAYBOOK
## Production Standards for TypeScript, Python, Java, Go, Rust & C#

---

## 1. TYPESCRIPT & MODERN JAVASCRIPT
- **Compiler Options**: `strict: true`, `noImplicitAny: true`, `strictNullChecks: true`, `verbatimModuleSyntax: true`.
- **Package Management**: Prefer `pnpm` or `bun` with locked lockfiles (`pnpm-lock.yaml`).
- **Idioms**:
  - Discriminated unions for multi-state domain logic (`type State = { status: 'idle' } | { status: 'loading' } | ...`).
  - Runtime validation at all I/O boundaries with Zod or Valibot. Zero unvalidated `as Type` casting.
  - Native ESM (`"type": "module"`), top-level await where supported.
- **Testing & Tooling**: Vitest for blazing fast unit tests, Biome or ESLint (flat config) + Prettier.

---

## 2. PYTHON 3.11+ / MODERN PYTHON
- **Toolchain**: Prefer `uv` for lightning-fast package management and virtual environment resolution.
- **Project Structure**: Standard `pyproject.toml` using `hatchling` or `flit_core`.
- **Type Safety**:
  - Mypy or Pyright in strict mode (`strict = true`).
  - Runtime validation with Pydantic v2 (`BaseModel`, `Field(frozen=True)`).
- **Asynchronous Execution**:
  - Pure non-blocking `asyncio`. Never call blocking sync I/O (e.g. `requests.get` or `time.sleep`) inside an async event loop (use `httpx.AsyncClient` and `asyncio.sleep`).
- **Testing & Tooling**: `pytest` with `pytest-asyncio`, `ruff` for ultra-fast linting and formatting.

---

## 3. GO (GOLANG 1.22+)
- **Dependency Management**: Standard `go.mod` and `go.sum` with vendoring where specified.
- **Concurrency & Goroutines**:
  - Always pass `ctx context.Context` as the first argument in functions making network or DB calls.
  - Prevent goroutine leaks: Every spawned goroutine must have an explicit exit trigger governed by `ctx.Done()`.
- **Error Handling**:
  - Explicit error inspection (`if err != nil`). Wrap errors with context: `fmt.Errorf("fetching user %s: %w", id, err)`.
- **Testing**: Table-driven tests with `t.Parallel()` and `testify/assert` or standard library checks.

---

## 4. RUST (EDITION 2021/2024)
- **Toolchain**: `cargo`, `rustup`, `rustc`.
- **Safety & Idioms**:
  - Zero `unsafe` blocks unless strictly justified with formal memory safety proofs.
  - Zero unhandled `.unwrap()` or `.expect()` in production paths. Always propagate errors using `?` with `thiserror` (for libraries) or `anyhow` (for applications).
  - Explicit ownership, lifetimes, and borrowed references (`&str` instead of `&String`).
- **Async Runtime**: Tokio runtime with `tokio::select!` for cooperative cancellation.
- **Tooling**: `cargo clippy -- -D warnings`, `cargo audit` for vulnerability scanning, `cargo fmt`.

---

## 5. JAVA 21+ / KOTLIN
- **Toolchain**: Gradle (Kotlin DSL `build.gradle.kts`) or Maven (`pom.xml`).
- **Java 21 Modern Capabilities**:
  - Virtual Threads (`Thread.ofVirtual().start(...)` / Spring Boot Loom integration) for high-throughput I/O without reactive callback hell.
  - Domain modeling with `record` (immutable data carriers) and sealed interfaces with pattern matching.
- **Testing**: JUnit 5, AssertJ, Mockito, Testcontainers for real DB testing, and ArchUnit to assert package boundary rules.

---

## 6. C# / .NET 8/9
- **Architecture**: Minimal APIs or Clean Architecture with ASP.NET Core.
- **Type Safety**: Nullable reference types enabled (`<Nullable>enable</Nullable>`).
- **Idioms**:
  - Immutable records (`public record UserDto(...)`), pattern matching with switch expressions.
  - Asynchronous first: `async Task<IResult>` with `CancellationToken` propagation.
- **Testing**: xUnit, FluentAssertions, Moq/NSubstitute, and Testcontainers.NET.
