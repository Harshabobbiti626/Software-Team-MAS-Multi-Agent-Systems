# BACKEND & API STANDARDS PLAYBOOK
## Production Guidelines for Node.js, Go, Python, Java & Distributed Systems

---

## 1. CLEAN / HEXAGONAL ARCHITECTURE
Enforce strict separation between external protocols and core domain logic:

```text
[HTTP Controllers / CLI / gRPC Handlers]
                   │
                   ▼  (DTOs / Ingress Schemas)
[Domain Services / Use Cases / Business Rules]
                   │
                   ▼  (Repository Interfaces)
[Postgres Adapter / Redis Cache / Kafka Producer / Stripe API]
```

- **Domain Invariants**: Business logic must not depend on HTTP requests (`req, res`), express middleware, or database ORMs.
- **Dependency Inversion**: Services depend on abstract repositories (`IOrderRepository`); database adapters implement them.

---

## 2. API CONTRACTS & ERROR SEMANTICS
- **RFC 7807 Problem Details**:
  Standardize all error responses to `{ type, title, status, detail, instance, invalid_params }`.
  Never return a 200 OK with `{ success: false, error: "..." }`.
- **Deterministic HTTP Status Codes**:
  - `200 OK`: Successful read or sync update.
  - `201 Created`: Resource successfully created (with `Location` header).
  - `204 No Content`: Successful deletion or action with empty response.
  - `400 Bad Request`: Syntactically invalid JSON or malformed headers.
  - `401 Unauthorized`: Missing or invalid authentication token.
  - `403 Forbidden`: Authenticated, but lacking permissions for this resource.
  - `404 Not Found`: Target resource does not exist.
  - `409 Conflict`: Resource state conflict (e.g. duplicate key, concurrent lock).
  - `422 Unprocessable Entity`: Semantic validation failure (e.g. Zod schema errors).
  - `429 Too Many Requests`: Rate limit exceeded (with `Retry-After` header).
  - `500 Internal Server Error`: Unhandled server exception (logged with trace ID).

---

## 3. RESILIENCE & DISTRIBUTED SAFETY
- **Idempotency Keys**: All non-idempotent endpoints (`POST`, `PUT`, `PATCH`) must support an `Idempotency-Key` header stored in Redis with a 24-hour TTL.
- **Cursor-Based Pagination**: For high-volume collections, reject offset pagination (`OFFSET 10000` is $O(N)$ table scan). Use cursor-based pagination based on time-ordered keys (`WHERE id > :cursor ORDER BY id ASC LIMIT :limit`).
- **Circuit Breakers**: Wrap external network calls (Stripe, Twilio, 3rd-party APIs) in circuit breakers with configurable failure thresholds and fallbacks.
