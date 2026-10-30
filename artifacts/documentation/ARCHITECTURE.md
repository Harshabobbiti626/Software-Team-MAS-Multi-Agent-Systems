# System Architecture & Technical Rationale: Real-Time Payment Gateway

## C4 System Flow
```mermaid
flowchart LR
    Client["Client App"] --> API["/api/v1/resource"]
    API --> Service["ResourceService"]
    Service --> DB[("PostgreSQL DB")]
```

## Architectural Decisions
- Grounded in ADR-001 (Contract-First Interface Design).
- Concurrency and lock protection enforced via non-locking DDL migrations.
