---
name: prd-to-stories
description: >-
  Ingests design documents, PRDs, technical specs, or ambiguous user requirements
  and transforms them into a structured scope analysis (In-Scope vs. Out-of-Scope)
  and production-ready INVEST user stories with Gherkin BDD acceptance criteria.
  Use when the user asks to analyze a design doc, break down requirements, define
  user stories, or establish scope boundaries.
  Do NOT use for high-level system design or database modeling (use system-architect),
  codebase investigation (use deep-search-and-execute), or code audits (use production-code-reviewer).
---

# PRD & Requirements Deconstruction Engine

This skill equips Antigravity to act as a **Staff Technical Product Manager**, converting complex or vague specifications into crystal-clear development backlogs with zero scope creep.

---

## EXECUTION WORKFLOW

### Step 1: Context & Core Problem
Extract the core problem statement, target user personas, and primary success metrics (KPIs).

### Step 2: The Scope Boundary Matrix
Create an explicit, non-negotiable scope boundary table:

| Category | In-Scope (P0 / P1 - MVP) | Out-of-Scope (Non-Goals) | Phase 2 / Deferred |
| :--- | :--- | :--- | :--- |
| **Functional Features** | Specific user-facing actions | Explicit exclusions | Future enhancements |
| **Technical / Infra** | Architecture, DB schema, APIs | Complex microservices, premature optimizations | Advanced caching / read-replicas |
| **Security & Auth** | RBAC, session handling | Custom SSO providers | Biometrics / hardware tokens |

### Step 3: Cross-Tier Technical Mapping
Map entities, endpoints, and data lifecycle across tiers using the [Cross-Tier Full-Stack Cohesion Playbook](../../references/interlinked-fullstack-workflow.md).

### Step 4: INVEST User Story Generation
Deconstruct requirements into atomic stories meeting the **INVEST** criteria (Independent, Negotiable, Valuable, Estimable, Small, Testable):

```markdown
### US-[ID]: [Descriptive Action Title]

**User Narrative:**
As a [specific user persona], I want to [action], so that [outcome].

#### Acceptance Criteria (Gherkin BDD format):
Scenario: Happy Path - [Action description]
  Given [initial system state and authentication context]
  When [user triggers action with valid input]
  Then [expected primary state change and response]

Scenario: Edge Case / Validation Failure - [Action description]
  Given [user enters invalid input]
  When [action submitted]
  Then [system rejects with descriptive 4xx RFC 7807 error]

#### Technical Implementation Checklist:
- [ ] Backend: Schema validation (Zod/Pydantic), Service layer, DB query
- [ ] Frontend: UI component, responsive layout, loading/error states, a11y labels
- [ ] Testing: Unit tests for domain logic, integration tests for API route
```

See [User Story Template](../../../templates/USER_STORY_TEMPLATE.md) for full format.

### Step 5: Mandatory Developer Approval Gate (STOP & WAIT)
Halt execution and present the Scope Boundary Matrix, INVEST User Stories, and Execution Plan to the developer:
> *"Here is the Scope Matrix and Step-by-Step Implementation Plan based on your design document and domain model. Please review and approve. Once you confirm ('Proceed' / 'Approved'), I will begin full-stack execution."*

**Never begin writing production code until the developer explicitly approves the plan.**
