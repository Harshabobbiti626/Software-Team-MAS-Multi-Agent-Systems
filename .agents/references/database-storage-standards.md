# DATABASE & STORAGE STANDARDS PLAYBOOK
## Production Guidelines for PostgreSQL, MySQL, Redis, NoSQL & Data Modeling

---

## 1. RELATIONAL SCHEMA DESIGN (POSTGRESQL & MYSQL)
- **Normalization**: Enforce 3rd Normal Form (3NF) to eliminate update anomalies.
- **Primary Keys**:
  - Default to **UUIDv7** or **ULID** (time-ordered, index-friendly, secure against ID enumeration).
  - Use `BIGINT GENERATED ALWAYS AS IDENTITY` for high-write internal append-only event logs.
- **Data Integrity**:
  - Explicit foreign keys with deliberate `ON DELETE RESTRICT` (prevent accidental orphan deletion) or `ON DELETE CASCADE`.
  - Check constraints for domain ranges: `CHECK (price_cents >= 0)`, `CHECK (status IN ('PENDING', 'PAID', 'CANCELLED'))`.
  - Always store monetary values as integers (cents/micros) to prevent IEEE 754 floating-point rounding errors.

---

## 2. INDEXING STRATEGY & QUERY OPTIMIZATION
- **Leftmost Prefix Rule**: For composite indexes `CREATE INDEX idx_user_status ON orders(user_id, status)`, queries filtering only by `status` cannot use the index. Align index column order with query frequency and cardinality.
- **Partial Indexes**: Save disk and write I/O on large tables:
  ```sql
  CREATE INDEX idx_active_tasks ON tasks(assignee_id) WHERE status != 'COMPLETED';
  ```
- **GIN Indexes**: Required for fast searching inside PostgreSQL `JSONB` columns or full-text search.
- **BRIN Indexes**: Ideal for multi-gigabyte append-only time-series tables where data is sorted by `created_at`.
- **Query Profiling**: Run `EXPLAIN (ANALYZE, BUFFERS)` on slow queries. Look for `Seq Scan` on tables with > 1,000 rows.

---

## 3. CACHING & REDIS BEST PRACTICES
- **Cache-Aside Pattern**: Read from cache $\rightarrow$ if miss, read DB and set cache $\rightarrow$ write directly to DB and invalidate cache key.
- **Cache Stampede (Thundering Herd) Defense**:
  - Enforce randomized TTL jitter (e.g. `base_ttl + random(0, 60) seconds`) so all keys don't expire simultaneously.
  - Use distributed mutex locks (`SET lock:resource NX PX 5000`) when recalculating expensive aggregations.
- **Eviction Policies**: Always configure `maxmemory` and an eviction policy (e.g. `volatile-lru` or `allkeys-lru`) to prevent OOM crashes.
