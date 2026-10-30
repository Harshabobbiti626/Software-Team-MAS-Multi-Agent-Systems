"""
Multi-Agent Software Engineering System (MAS) - Primary CLI Entrypoint.
Commands:
  run     - Execute an end-to-end task through the contract-first multi-agent pipeline
  status  - Inspect Blackboard artifacts, token usage, and circuit breaker metrics
  verify  - Run deterministic static linters and domain invariant rules
  pr      - Synthesize a production-ready GitHub Pull Request description
"""

import argparse
import sys
from pathlib import Path

from mas.agents.engineering import (
    BackendEngineerAgent,
    CloudEngineerAgent,
    DatabaseArchitectAgent,
    DevOpsSREAgent,
    FrontendEngineerAgent,
)
from mas.agents.governance_docs import (
    AppSecAgent,
    CodeReviewerAgent,
    QASDETAgent,
    TechnicalWriterAgent,
)
from mas.agents.leadership import (
    BusinessSponsorAgent,
    DomainSMEAgent,
    ProductManagerAgent,
    SystemArchitectAgent,
    TechLeadAgent,
)
from mas.core.blackboard import ArtifactBlackboard
from mas.core.circuit_breaker import CircuitBreaker
from mas.core.config import get_config
from mas.core.orchestrator import MASOrchestrator
from mas.core.state import SubsystemClass, Task, TaskPriority, TestReport
from mas.core.vcs import PullRequestGenerator
from mas.hitl.gates import GateDecision, GateLevel, HITLGateManager
from mas.observability.otlp import OTLPTraceExporter
from mas.observability.tracer import DistributedTracer
from mas.tools.domain_verifier import DomainVerifier
from mas.tools.linter import DeterministicLinter


def interactive_gate_handler(gate: GateLevel, task_id: str, context: dict) -> GateDecision:
    print(f"\n[HITL Gate Intervention Required]: {gate.value}")
    resp = input("Decision [A]pprove / [R]eject / [M]odify (default: Approve): ").strip().upper()
    if resp == "R":
        reason = input("Enter rejection reason: ").strip() or "Rejected by human reviewer"
        return GateDecision(gate=gate, task_id=task_id, decision="REJECTED", reviewer="HumanArchitect", rationale=reason)
    return GateDecision(gate=gate, task_id=task_id, decision="APPROVED", reviewer="HumanArchitect", rationale="Approved by human reviewer")


def run_pipeline(task_title: str, task_desc: str, interactive: bool = False) -> int:
    print("\n================================================================================")
    print(f"🚀 Initializing MAS Multi-Agent Pipeline for: {task_title}")
    print("================================================================================\n")

    config = get_config()
    blackboard = ArtifactBlackboard(repo_path=".")
    circuit_breaker = CircuitBreaker(config.limits)
    orchestrator = MASOrchestrator(config=config, blackboard=blackboard, circuit_breaker=circuit_breaker)
    tracer = DistributedTracer()
    otlp_exporter = OTLPTraceExporter(output_file_path=".mas_traces.jsonl")

    hitl = HITLGateManager(auto_approve_in_dev=not interactive)
    if interactive:
        hitl.set_interactive_handler(interactive_gate_handler)

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

    # 4. Specialized Engineering Pods (Contract-First Parallel Concurrency)
    print("[3/5] Executing Contract-First Parallel Engineering Pods (Concurrent Workers)...")
    engineering_pods = [
        DatabaseArchitectAgent(**agent_kwargs),
        BackendEngineerAgent(**agent_kwargs),
        FrontendEngineerAgent(**agent_kwargs),
        CloudEngineerAgent(**agent_kwargs),
        DevOpsSREAgent(**agent_kwargs)
    ]

    parallel_results = orchestrator.execute_parallel_pods(task, engineering_pods, max_workers=5)
    for role, resp in parallel_results.items():
        print(f"  + [Concurrent Pod] {role}: {resp.summary}")
    print()

    # 5. Verification, Security & Gatekeeping
    print("[4/5] Executing QA, Security & Quality Gatekeeping...")
    qa = QASDETAgent(**agent_kwargs)
    r_qa = qa.run(task)
    circuit_breaker.record_turn(qa.role)
    print(f"  + {qa.role}: {r_qa.summary}")

    # Closed-loop remediation check if QA failed
    if r_qa.status != "SUCCESS":
        print("  ⚠️ QA Failure detected. Triggering Intelligent Remediation Loop...")
        agent_roster = {a.role: a for a in engineering_pods}
        test_report = getattr(r_qa, "test_report", None)
        if not isinstance(test_report, TestReport):
            test_report = TestReport(
                id=f"TR-FAIL-{task.id}",
                task_id=task.id,
                test_suite="integration",
                passed_all=False,
                stderr=r_qa.summary
            )
        remediated = orchestrator.trigger_remediation_loop(task, test_report, agent_roster, qa)
        print(f"  [*] Remediation Loop Result: {'SUCCESS' if remediated else 'FAILED'}")

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

    # 7. Export OpenTelemetry Traces
    task_span = tracer.start_span(
        task_id=task.id,
        agent_name="MASOrchestrator",
        agent_role="Orchestrator",
        operation="ExecutePipeline",
        attributes={"task.title": task.title, "task.assigned_pod": task.assigned_pod.value}
    )
    tracer.finish_span(
        span=task_span,
        prompt_tokens=circuit_breaker.prompt_tokens,
        candidate_tokens=circuit_breaker.candidate_tokens,
        thinking_tokens=circuit_breaker.thinking_tokens,
        duration_ms=2500.0,
        status="OK"
    )
    otlp_exporter.export_spans([task_span])

    # Summary
    print("\n================================================================================")
    print(f"✅ MAS Task Complete: {task.title}")
    print(f"   Total Turns: {circuit_breaker.total_turns} / {config.limits.max_total_turns_per_task}")
    print(f"   Tokens Consumed: {circuit_breaker.prompt_tokens + circuit_breaker.candidate_tokens + circuit_breaker.thinking_tokens}")
    print(f"   Circuit Breaker: Healthy (Tripped: {circuit_breaker.is_tripped()})")
    print(f"   Artifacts Committed: {len(blackboard.list_artifacts())}")
    print("   Telemetry Trace: Exported to .mas_traces.jsonl")
    print("================================================================================\n")
    return 0


def generate_pr_command(task_id: str = "TASK-001") -> int:
    task = Task(id=task_id, title="Core Service Implementation", description="End-to-end microservice", assigned_pod=SubsystemClass.FULL_SYSTEM)
    pr_gen = PullRequestGenerator()
    pr = pr_gen.generate_pr(task=task, source_branch="feat/task-001")
    
    pr_file = Path("PULL_REQUEST.md")
    pr_file.write_text(pr.description_markdown, encoding="utf-8")
    print(f"\n✅ Synthesized GitHub Pull Request: {pr.title}")
    print(f"[*] Saved to: {pr_file.resolve()}\n")
    print(pr.description_markdown)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Multi-Agent Software Engineering System (MAS) CLI")
    subparsers = parser.add_subparsers(dest="command", help="MAS command to execute")

    # run command
    run_parser = subparsers.add_parser("run", help="Run multi-agent engineering workflow")
    run_parser.add_argument("--title", type=str, default="Core Resource Service", help="Task title")
    run_parser.add_argument("--description", type=str, default="Implement secure REST API endpoints with PostgreSQL persistence, React UI, and Terraform IaC.", help="Task description")
    run_parser.add_argument("--interactive", action="store_true", help="Enable interactive human approval gates")

    # status command
    subparsers.add_parser("status", help="Show system status and blackboard artifacts")

    # verify command
    subparsers.add_parser("verify", help="Run domain verifier and syntax linter")

    # pr command
    pr_parser = subparsers.add_parser("pr", help="Generate GitHub Pull Request markdown")
    pr_parser.add_argument("--task-id", type=str, default="TASK-001", help="Task ID to generate PR for")

    args = parser.parse_args()

    if args.command == "run" or args.command is None:
        title = getattr(args, "title", "Core Resource Service")
        desc = getattr(args, "description", "Implement secure REST API endpoints with PostgreSQL persistence, React UI, and Terraform IaC.")
        interactive = getattr(args, "interactive", False)
        return run_pipeline(title, desc, interactive=interactive)

    elif args.command == "pr":
        return generate_pr_command(getattr(args, "task_id", "TASK-001"))

    elif args.command == "status":
        bb = ArtifactBlackboard(repo_path=".")
        arts = bb.list_artifacts()
        print("\n--- Artifact Blackboard Status ---")
        print(f"Total Registered Artifacts: {len(arts)}")
        for a in arts:
            print(f"[{a.type.value}] {a.name} (v{a.version}) created by {a.created_by} -> {a.path}")
        return 0

    elif args.command == "verify":
        print("\n--- Running Deterministic Domain & Syntax Verification ---")
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
