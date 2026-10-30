# PROJECT KNOWLEDGE BASE (DOMAIN & SPECIFICATIONS)
## Central Repository for Domain Invariants, Design Documents & Living Architecture

This directory serves as the **persistent domain memory and specification archive** for both AI assistants and human engineers. It ensures the AI understands **business-specific domain rules** (e.g. healthcare, fintech, e-commerce, logistics) while aligning them with the technical stack.

---

## 📁 KNOWLEDGE BASE STRUCTURE

```text
.agents/knowledge/
├── README.md                           # This guide
├── domain-model.md                     # Ubiquitous language, business invariants & regulations
├── design-docs/                        # Ingested PRDs, RFCs, and feature specifications
│   └── .gitkeep
└── architecture-decisions/             # Living ADRs (001-decision-title.md)
    └── .gitkeep
```

---

## 🧠 HOW THE AI INTERACTS WITH THE KNOWLEDGE BASE

1. **Auto-Catchup (Zero Redundant Questions)**:
   - When you start a task, the AI automatically reads `domain-model.md` and `.agents/STATE.md`.
   - It already knows your core business rules (e.g. "Orders cannot be refunded after 30 days", "All PII must be encrypted with AES-256") without you having to re-explain them.
2. **Design Document Ingestion**:
   - When you share a new design doc or PRD, the AI archives it under `design-docs/YYYY-MM-DD-feature-name.md` for permanent reference.
3. **Living Architecture Decisions (ADRs)**:
   - When a major technical choice is agreed upon, it is recorded in `architecture-decisions/ADR-XXX-title.md` using the ADR template.
