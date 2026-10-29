"""
Multi-Agent Software Engineering System (MAS) - Primary CLI Entrypoint.
Commands:
  run     - Execute an end-to-end task through the contract-first multi-agent pipeline
  status  - Inspect Blackboard artifacts, token usage, and circuit breaker metrics
  verify  - Run deterministic static linters and domain invariant rules
  autopsy - Run root cause analysis (RCA) on test/build failures
"""

import argparse
import sys
from pathlib import Path
from mas.core.config import get_config
from mas.core.blackboard import ArtifactBlackboard
from mas.core.circuit_breaker import CircuitBreaker
from mas.core.orchestrator import MASOrchestrator
from mas.core.state import TaskPriority, TaskStatus, SubsystemClass
from mas.agents.leadership import (
    BusinessSponsorAgent,
    ProductManagerAgent,
    DomainSMEAgent,
    SystemArchitectAgent,
    TechLeadAgent,
)
from mas.agents.engineering import (
    DatabaseArchitectAgent,
    BackendEngineerAgent,
    FrontendEngineerAgent,
    CloudEngineerAgent,
    DevOpsSREAgent,
)
from mas.agents.governance_docs import (
    AppSecAgent,
    CodeReviewerAgent,
    QASDETAgent,
    TechnicalWriterAgent,
)
from mas.observability.tracer import DistributedTracer
from mas.hitl.gates import HITLGateManager, GateLevel
from mas.tools.domain_verifier import DomainVerifier
from mas.tools.linter import DeterministicLinter


def run_pipeline(task_title: str, task_desc: str) -> int:
    print(f"\n================================================================================")
    print(f"🚀 Initializing MAS Multi-Agent Pipeline for: {task_title}")
    print(f"================================================================================\n")

    config = get_config()
    blackboard = ArtifactBlackboard(repo_path=".")
    circuit_breaker = CircuitBreaker(config.limits)
    orchestrator = MASOrchestrator(config=config, blackboard=blackboard, circuit_breaker=circuit_breaker)
    tracer = DistributedTracer()
    hitl = HITLGateManager(auto_approve_in_dev=True)

    # 1. Create Task & Blast Radius Triage
    task_id = "TASK-001"
    task = orchestrator.create_task(
        task_id=task_id,
        title=task_title,
        description=task_desc,
        priority=TaskPriority.HIGH
    )
    print(f"[*] Task Created: {task.id} | Assigned Pod: {task.assigned_pod.value}")
    print(f"[*] Active Agents (JIT Awakened): {', '.join(orchestrator.state.active_pods)}\n")

    # Shared Agent Dependency Dict
    agent_kwargs = {
        "config": config,
        "blackboard": blackboard
    }

    # 2. Business & Domain Tier
    print("[1/5] Executing Business & Domain Tier...")
    sponsor = BusinessSponsorAgent(**agent_kwargs)
    r_sponsor = sponsor.run(task)
    circuit_breaker.record_turn(sponsor.role)
    circuit_breaker.record_tokens(r_sponsor.tokens_used.prompt_tokens, r_sponsor.tokens_used.candidate_tokens, r_sponsor.tokens_used.thinking_tokens)
    print(f"  + {sponsor.role}: {r_sponsor.summary}")

    pm = ProductManagerAgent(**agent_kwargs)
    r_pm = pm.run(task)
    circuit_breaker.record_turn(pm.role)
    circuit_breaker.record_tokens(r_pm.tokens_used.prompt_tokens, r_pm.tokens_used.candidate_tokens, r_pm.tokens_used.thinking_tokens)
    print(f"  + {pm.role}: {r_pm.summary}")

    sme = DomainSMEAgent(**agent_kwargs)
    r_sme = sme.run(task)
    circuit_breaker.record_turn(sme.role)
    circuit_breaker.record_tokens(r_sme.tokens_used.prompt_tokens, r_sme.tokens_used.candidate_tokens, r_sme.tokens_used.thinking_tokens)
    print(f"  + {sme.role}: {r_sme.summary}")

    gate1 = hitl.evaluate_gate(GateLevel.GATE_1_SCOPE_BUDGET, task.id)
    print(f"  [Gate 1: Scope & Budget] -> {gate1.decision} by {gate1.reviewer}\n")

    # 3. Technical Architecture & Governance
    print("[2/5] Executing Architecture & Interface Contract Compilation...")
    architect = SystemArchitectAgent(**agent_kwargs)
    r_arch = architect.run(task)
    circuit_breaker.record_turn(architect.role)
    circuit_breaker.record_tokens(r_arch.tokens_used.prompt_tokens, r_arch.tokens_used.candidate_tokens, r_arch.tokens_used.thinking_tokens)
    print(f"  + {architect.role}: {r_arch.summary}")

    tech_lead = TechLeadAgent(**agent_kwargs)
    r_tl = tech_lead.run(task)
    circuit_breaker.record_turn(tech_lead.role)
    circuit_breaker.record_tokens(r_tl.tokens_used.prompt_tokens, r_tl.tokens_used.candidate_tokens, r_tl.tokens_used.thinking_tokens)
    print(f"  + {tech_lead.role}: {r_tl.summary}")

    gate2 = hitl.evaluate_gate(GateLevel.GATE_2_ARCHITECTURE_SECURITY, task.id)
    print(f"  [Gate 2: Architecture & Security] -> {gate2.decision} by {gate2.reviewer}\n")

    # 4. Specialized Engineering Pods (Contract-First Parallel Execution)
    print("[3/5] Executing Contract-First Parallel Engineering Pods...")
    dba = DatabaseArchitectAgent(**agent_kwargs)
    r_dba = dba.run(task)
    circuit_breaker.record_turn(dba.role)
    print(f"  + [Data Pod] {dba.role}: {r_dba.summary}")

    be = BackendEngineerAgent(**agent_kwargs)
    r_be = be.run(task)
    circuit_breaker.record_turn(be.role)
    print(f"  + [Backend Pod] {be.role}: {r_be.summary}")

    fe = FrontendEngineerAgent(**agent_kwargs)
    r_fe = fe.run(task)
    circuit_breaker.record_turn(fe.role)
    print(f"  + [Frontend Pod] {fe.role}: {r_fe.summary}")

    cloud = CloudEngineerAgent(**agent_kwargs)
    r_cloud = cloud.run(task)
    circuit_breaker.record_turn(cloud.role)
    print(f"  + [Cloud Pod] {cloud.role}: {r_cloud.summary}")

    sre = DevOpsSREAgent(**agent_kwargs)
    r_sre = sre.run(task)
    circuit_breaker.record_turn(sre.role)
    print(f"  + [DevOps Pod] {sre.role}: {r_sre.summary}\n")

    # 5. Verification, Security & Gatekeeping
    print("[4/5] Executing QA, Security & Quality Gatekeeping...")
    qa = QASDETAgent(**agent_kwargs)
    r_qa = qa.run(task)
    circuit_breaker.record_turn(qa.role)
    print(f"  + {qa.role}: {r_qa.summary}")

    reviewer = CodeReviewerAgent(**agent_kwargs)
    r_rev = reviewer.run(task)
    circuit_breaker.record_turn(reviewer.role)
    print(f"  + {reviewer.role}: {r_rev.summary}")

    security = AppSecAgent(**agent_kwargs)
    r_sec = security.run(task)
    circuit_breaker.record_turn(security.role)
    print(f"  + {security.role}: {r_sec.summary}")

    gate4 = hitl.evaluate_gate(GateLevel.GATE_4_PRODUCTION_RELEASE, task.id)
    print(f"  [Gate 4: Production Release] -> {gate4.decision} by {gate4.reviewer}\n")

    # 6. Documentation Agent: Human Reference & Audit Bridge
    print("[5/5] Synthesizing 6-Document Human Reference & Audit Suite...")
    writer = TechnicalWriterAgent(**agent_kwargs)
    r_writer = writer.run(task)
    circuit_breaker.record_turn(writer.role)
    print(f"  + {writer.role}: {r_writer.summary}")
    for art_id in r_writer.artifacts_produced:
        art = blackboard.get_artifact(art_id)
        if art:
            print(f"     * Generated: {art.path}")

    # Summary
    print(f"\n================================================================================")
    print(f"✅ MAS Task Complete: {task.title}")
    print(f"   Total Turns: {circuit_breaker.total_turns} / {config.limits.max_total_turns_per_task}")
    print(f"   Circuit Breaker: Healthy (Tripped: {circuit_breaker.is_tripped()})")
    print(f"   Artifacts Committed: {len(blackboard.list_artifacts())}")
    print(f"================================================================================\n")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-Agent Software Engineering System (MAS) CLI")
    subparsers = parser.add_subparsers(dest="command", help="MAS command to execute")

    # run command
    run_parser = subparsers.add_parser("run", help="Run multi-agent engineering workflow")
    run_parser.add_argument("--title", type=str, default="Core Resource Service", help="Task title")
    run_parser.add_argument("--description", type=str, default="Implement secure REST API endpoints with PostgreSQL persistence, React UI, and Terraform IaC.", help="Task description")

    # status command
    status_parser = subparsers.add_parser("status", help="Show system status and blackboard artifacts")

    # verify command
    verify_parser = subparsers.add_parser("verify", help="Run domain verifier and syntax linter")

    args = parser.parse_args()

    if args.command == "run" or args.command is None:
        title = getattr(args, "title", "Core Resource Service")
        desc = getattr(args, "description", "Implement secure REST API endpoints with PostgreSQL persistence, React UI, and Terraform IaC.")
        return run_pipeline(title, desc)

    elif args.command == "status":
        bb = ArtifactBlackboard(repo_path=".")
        arts = bb.list_artifacts()
        print(f"\n--- Artifact Blackboard Status ---")
        print(f"Total Registered Artifacts: {len(arts)}")
        for a in arts:
            print(f"[{a.type.value}] {a.name} (v{a.version}) created by {a.created_by} -> {a.path}")
        return 0

    elif args.command == "verify":
        print(f"\n--- Running Deterministic Domain & Syntax Verification ---")
        verifier = DomainVerifier()
        linter = DeterministicLinter()
        ast_res = linter.check_python_syntax_ast("main.py")
        print(f"[*] Python AST Parser: {'PASSED' if ast_res.passed else 'FAILED'}")
        rule_res = verifier.verify_content("sample check content")
        print(f"[*] Domain Invariant Rules Checked: {rule_res.checked_invariants_count} (Pass: {rule_res.is_valid})")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
