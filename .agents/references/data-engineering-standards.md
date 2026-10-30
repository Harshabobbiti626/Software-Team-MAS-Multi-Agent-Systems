# DATA ENGINEERING STANDARDS PLAYBOOK
## Production Guidelines for dbt, Apache Airflow, Spark/PySpark & BigQuery

---

## 1. MODERN ELT ARCHITECTURE
- **Load First, Transform In Warehouse**:
  Extract and load raw data into Cloud Storage (GCS/S3) or raw landing tables in BigQuery/Snowflake without brittle in-flight transformations.
- **Strict Layer Separation (dbt Medallion Architecture)**:
  - `staging/` (Bronze): 1:1 view with source data, cast datatypes, rename columns to domain conventions.
  - `intermediate/` (Silver): Cleanse data, apply business logic, join entities, deduplicate records.
  - `marts/` (Gold): Star schema fact (`fct_`) and dimension (`dim_`) tables optimized for analytics and BI dashboards.

---

## 2. IDEMPOTENT PIPELINE EXECUTION
- **The Golden Rule**: Re-running a pipeline on a historical partition date `ds = 2026-10-29` must produce the exact same table state and never create duplicate rows.
- **Partition Overwrites**: Use partition replacement (`MERGE INTO` or atomic partition swap) instead of naive `INSERT INTO`.

---

## 3. SPARK & DISTRIBUTED COMPUTE PERFORMANCE
- **Avoid Wide Shuffles**:
  Minimize expensive `groupByKey` operations; prefer `reduceByKey` or map-side aggregations.
- **Broadcast Small Lookup Tables**:
  If joining a large event table with a small dimension table (< 100MB), use Broadcast Hash Join (`broadcast(dim_table)`) to avoid cross-network data shuffling.
- **Data Skew Defense**:
  Identify high-cardinality keys that cause single worker bottlenecks; apply salting (appending a random suffix 0-N) to distribute processing evenly across executors.

---

## 4. DATA QUALITY & DATA CONTRACTS
- **Automated Assertions**: Run automated freshness, uniqueness, and non-null tests before downstream consumption:
  ```yaml
  models:
    - name: fct_orders
      columns:
        - name: order_id
          tests:
            - unique
            - not_null
  ```
- **Quarantine / Dead-Letter Queue**: Divert malformed incoming records to a dead-letter table with timestamp and error message rather than silently dropping or crashing the pipeline.
