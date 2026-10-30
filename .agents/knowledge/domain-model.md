# PROJECT DOMAIN MODEL & BUSINESS INVARIANTS

> This file documents the core business rules, domain entities, and regulatory compliance constraints. AI assistants read this automatically to ground technical code in business reality.

---

## 1. Domain Identity & Ubiquitous Language

- **Industry / Vertical**: [e.g. Fintech, Healthcare, E-Commerce, Logistics, SaaS, Gaming]
- **Core Business Mission**: [What problem does this company or application solve?]

### Ubiquitous Language Glossary
| Domain Term | Business Definition | Technical Representation |
| :--- | :--- | :--- |
| **Customer** | Verified person who holds an active account. | `UserEntity` with `role = 'CUSTOMER'` |
| **Order** | A confirmed commercial commitment with line items. | `OrderEntity` with state machine |
| **Settlement** | Final transfer of funds between merchant and buyer. | `PaymentTransaction` |

---

## 2. Core Business Invariants (Non-Negotiable Rules)

1. **State Transition Rules**:
   - An Order can only transition: `DRAFT` $\rightarrow$ `PENDING` $\rightarrow$ `PAID` $\rightarrow$ `SHIPPED` $\rightarrow$ `DELIVERED`.
   - An Order cannot be cancelled once in `SHIPPED` state.
2. **Financial / Transactional Rules**:
   - All monetary calculations must use integer cents (never floating-point).
   - Double-entry bookkeeping: every debit must have an equal and corresponding credit.
3. **Temporal Rules**:
   - Magic links expire strictly after 15 minutes.
   - Idempotency tokens remain valid for 24 hours.

---

## 3. Regulatory, Privacy & Security Invariants

- **Compliance Scope**: [e.g. GDPR, HIPAA, SOC 2 Type II, PCI-DSS Level 1]
- **Data Protection Rules**:
  - PII (Personally Identifiable Information) must be encrypted at rest with AES-256-GCM.
  - User deletion requests (GDPR Right to Be Forgotten) must soft-delete within 24 hours and purge backups within 30 days.
  - No customer secrets, credit card numbers, or passwords may ever be logged.
