---
name: universal-state-tracker
description: >-
  Maintains and updates the project state ledger (.agents/STATE.md). Acts as a
  persistent memory and state machine across conversations, tracking tech stack,
  architectural decisions, active milestones, open user stories, and known technical debt.
  Use when initializing a new project, picking up work from a previous session,
  or recording completed milestones.
  Do NOT use for writing functional code, designing architectures, or reviewing pull requests;
  strictly for reading, synchronizing, and maintaining project state and memory.
---

# Universal Project State Tracker & Memory Machine

This skill ensures Antigravity maintains **situational awareness and continuity** across sessions, context compactions, and long development cycles.

---

## WORKFLOW

### 1. Initialization
When entering a project or when asked to initialize tracking:
- Check if `.agents/STATE.md` exists.
- If missing, inspect the repository (dependencies, directory layout, Dockerfiles, README) and generate a new `.agents/STATE.md` using the [State Ledger Template](../../../templates/STATE_TEMPLATE.md).
- If it exists, read it at the start of any complex engineering session.

### 2. Continuous State Synchronization
Whenever an architectural choice is finalized, a user story completed, or a new dependency introduced:
- Update `.agents/STATE.md` with surgical precision.
- Ensure open tickets, completed features, and technical debt items are accurately reflected.

---

## CORE STATE FIELDS MAINTAINED
1. **System Identity & Mission**: Name, current development phase, last updated timestamp.
2. **Tech Stack & Infrastructure Matrix**: Runtimes, frontend, backend, databases, cloud, APIs.
3. **Active Architecture & Core Invariants**: Architectural patterns, auth model, non-negotiables.
4. **Current Milestone & Story Backlog**: Completed stories vs. in-progress vs. next up.
5. **Technical Debt & Open Questions**: Unresolved trade-offs, performance hotspots, refactor tickets.
