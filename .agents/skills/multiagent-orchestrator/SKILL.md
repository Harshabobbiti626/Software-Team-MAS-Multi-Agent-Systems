---
name: multiagent-orchestrator
description: >-
  Orchestrates, decomposes, and coordinates multi-agent workflows across subagents,
  parallel threads, and background tasks. Use when a complex task benefits from
  specialized worker division (e.g. concurrent research, multi-service refactoring,
  independent frontend/backend parallel tracks, or multi-perspective code review).
  Do NOT use for simple single-file edits or direct questions that can be answered in a single turn.
---

# Multi-Agent Orchestration & Subagent Delegation Engine

This skill guides Antigravity to operate as a **Principal Orchestrator (Supervisor Agent)**, decomposing complex, high-consequence programming tasks across specialized subagents, background threads, and validation pipelines.

---

## REFERENCE PLAYBOOK (READ ON-DEMAND)
- [Multi-Agent Systems (MAS) Playbook](../../references/multiagent-systems.md): Coordination topologies, memory tiers, A2A message envelopes, loop detection, and self-healing.
- [Cross-Tier Cohesion Playbook](../../references/interlinked-fullstack-workflow.md): Cross-boundary type safety and trace propagation.

---

## ORCHESTRATION WORKFLOW

### Phase 1: Task Decomposition (DAG Generation)
Break down the user's objective into a Directed Acyclic Graph (DAG) of independent subtasks:
1. Identify parallel workstreams (e.g. Subtask A: Database migration, Subtask B: Frontend view components).
2. Identify sequential dependency bottlenecks (e.g. Subtask C: API route depends on Subtask A).
3. Assign each subtask to an appropriate subagent persona.

### Phase 2: Subagent Selection & Dispatch
Antigravity supports built-in and dynamically defined subagents via `invoke_subagent`:
- **`research`**: For deep read-only codebase surveys, documentation fetching, and web searches (keeps main context clean).
- **`self`**: For autonomous implementation tasks in isolated branch workspaces (`Workspace: 'branch'`).
- **Specialist Subagents**: Define specialized personas using `define_subagent` if the domain requires strict boundaries (e.g. `SecurityAuditor`, `SchemaMigrationSpecialist`).

### Phase 3: Structured Task Envelopes
When launching or messaging a subagent via `invoke_subagent` or `send_message`, provide a self-contained, unambiguous task description:
- **Objective**: Exact deliverable required.
- **Context & Constraints**: File paths, interface definitions, strict types, coding standards.
- **Verification Rule**: What command or test the subagent must execute before reporting completion.

### Phase 4: Reactive Synthesis & Review
Antigravity wakes up reactively when a subagent finishes (no polling loops):
1. Ingest subagent results and inspect changed files.
2. Run an integration test suite across the combined changes.
3. If an error is detected, deliver targeted feedback via `send_message` or remediate directly.
4. Update `.agents/STATE.md` with completed milestones.
