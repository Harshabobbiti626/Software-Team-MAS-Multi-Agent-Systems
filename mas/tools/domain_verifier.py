"""
Domain Invariant Verifier & SME Rule Engine.
Validates artifacts and source code against domain axioms specified in config/domain_rules.yaml.
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


class InvariantViolation(BaseModel):
    invariant_id: str
    name: str
    severity: str
    description: str
    violating_content: str
    file_path: Optional[str] = None


class RuleValidationResult(BaseModel):
    is_valid: bool
    violations: List[InvariantViolation] = Field(default_factory=list)
    checked_invariants_count: int = 0


class DomainVerifier:
    def __init__(self, rules_path: Optional[str] = None):
        self.rules_path = Path(rules_path or "config/domain_rules.yaml")
        self.rules: Dict[str, Any] = {}
        self._load_rules()

    def _load_rules(self) -> None:
        if self.rules_path.exists():
            with open(self.rules_path, "r", encoding="utf-8") as f:
                raw_rules = yaml.safe_load(f)
                self.rules = raw_rules if isinstance(raw_rules, dict) else {}

    def verify_content(self, content: str, file_path: Optional[str] = None) -> RuleValidationResult:
        violations: List[InvariantViolation] = []
        invariants = self.rules.get("invariants", [])

        for inv in invariants:
            inv_id = inv.get("id", "UNKNOWN")
            name = inv.get("name", "")
            severity = inv.get("severity", "MEDIUM")
            desc = inv.get("description", "")
            rule_type = inv.get("rule_type", "")

            if rule_type == "regex_forbidden":
                for pattern in inv.get("patterns", []):
                    matches = re.findall(pattern, content)
                    if matches:
                        violations.append(InvariantViolation(
                            invariant_id=inv_id,
                            name=name,
                            severity=severity,
                            description=desc,
                            violating_content=f"Matched forbidden pattern '{pattern}' on: {matches[:3]}",
                            file_path=file_path
                        ))

            elif rule_type == "provenance_header":
                # Check for provenance metadata in patch or code
                if "CodePatch" in content or "diff --git" in content:
                    if "task_id" not in content.lower() and "provenance" not in content.lower():
                        violations.append(InvariantViolation(
                            invariant_id=inv_id,
                            name=name,
                            severity=severity,
                            description=desc,
                            violating_content="Code patch is missing required traceability provenance header.",
                            file_path=file_path
                        ))

        return RuleValidationResult(
            is_valid=(len(violations) == 0),
            violations=violations,
            checked_invariants_count=len(invariants)
        )

    def verify_prd(self, prd_content: str) -> RuleValidationResult:
        """Checks if PRD contains all required sections from ubiquitous language rules."""
        violations: List[InvariantViolation] = []
        required = ["executive_summary", "user_stories", "acceptance_criteria", "non_functional_requirements"]
        lower_content = prd_content.lower()

        for sec in required:
            # Check either snake_case or title case
            sec_title = sec.replace("_", " ")
            if sec not in lower_content and sec_title not in lower_content:
                violations.append(InvariantViolation(
                    invariant_id="INV_PRD_SCHEMA",
                    name="Missing PRD Section",
                    severity="HIGH",
                    description=f"PRD is missing required section: '{sec_title}'",
                    violating_content=f"Section '{sec_title}' not found in document.",
                    file_path="artifacts/prd/PRD.md"
                ))

        return RuleValidationResult(
            is_valid=(len(violations) == 0),
            violations=violations,
            checked_invariants_count=len(required)
        )
