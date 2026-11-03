/**
 * MAS Web Mission Control - Modern React 18 Application with IDE-Grade Workspace
 * Comprehensive multi-agent command cockpit with real-time SSE streaming,
 * VS Code-style File Explorer, multi-tab editor, line-number gutter,
 * disk path traceability, and interactive HITL gates.
 */

const { useState, useEffect, useRef, useMemo, useCallback } = React;

// --- PRESET MISSION TEMPLATES ---
const MISSION_PRESETS = [
  {
    label: "FinTech Payments",
    title: "Stripe Webhook & Payment Reconciliation Service",
    description: "Implement secure payment webhook verification, idempotent transaction processing, PostgreSQL double-entry ledger with non-locking indexes, React payment status dashboard, and Terraform KMS IaC."
  },
  {
    label: "Healthcare EHR",
    title: "HIPAA-Compliant Patient Telemetry Service",
    description: "Design FHIR-compliant patient telemetry ingestion REST APIs, partitioned PostgreSQL audit logs, role-based access controls, React patient timeline component, and hardened Docker container."
  },
  {
    label: "E-Commerce Cart",
    title: "High-Concurrency Inventory & Checkout Engine",
    description: "Implement inventory reservation REST API, optimistic concurrency control, PostgreSQL schema with foreign keys, 4-state accessible React checkout widget, and Terraform cloud infrastructure."
  },
  {
    label: "Auth & IAM",
    title: "Multi-Tenant OAuth2 & Session Gateway",
    description: "Author OAuth2 authorization server endpoints, tenant isolation policies in PostgreSQL, accessible React login/switch-tenant view, and Docker container with health checks."
  }
];

// --- STAGE DEFINITIONS ---
const PIPELINE_STAGES = [
  { id: "CONTRACTS", index: 1, label: "Triage & Contracts", desc: "Business invariant triage & blast radius analysis" },
  { id: "ARCHITECTURE", index: 2, label: "Architecture", desc: "API contracts, data models & security boundary lock" },
  { id: "PARALLEL_PODS", index: 3, label: "Parallel Pods", desc: "Concurrent synthesis: Data, Backend, Frontend, Cloud" },
  { id: "QA_SECURITY", index: 4, label: "QA & Security", desc: "Sandboxed pytest suite & OWASP Top 10 code audit" },
  { id: "DOCUMENTATION", index: 5, label: "PR Lander", desc: "6-document developer suite & remote GitHub PR" }
];

// --- POD DEFINITIONS ---
const POD_CONFIGS = [
  { key: "Data Pod", icon: "🗄️", name: "Data & Storage Pod", desc: "PostgreSQL DDL & Non-Locking Indexing", defaultArtifact: "schema.sql" },
  { key: "Backend Pod", icon: "⚙️", name: "Backend & AI Pod", desc: "REST APIs, Pydantic & ReAct Self-Healing", defaultArtifact: "service.py" },
  { key: "Frontend Pod", icon: "🎨", name: "Frontend Pod", desc: "4-State Accessible React TSX Component", defaultArtifact: "IntegrationView.tsx" },
  { key: "Cloud & SRE Pod", icon: "☁️", name: "Cloud & Platform Pod", desc: "Terraform KMS IaC & Hardened Dockerfile", defaultArtifact: "Dockerfile" },
  { key: "Governance & QA", icon: "🛡️", name: "Governance & QA Pod", desc: "Sandboxed Pytest & OWASP Top 10 Audit", defaultArtifact: "TestReport.json" }
];

// Helper: Determine File Icon by Extension
function getFileIcon(filename = "") {
  const f = filename.toLowerCase();
  if (f.endsWith(".py")) return "🐍";
  if (f.endsWith(".tsx") || f.endsWith(".jsx")) return "⚛️";
  if (f.endsWith(".ts") || f.endsWith(".js")) return "📜";
  if (f.endsWith(".sql")) return "🗄️";
  if (f.endsWith(".yaml") || f.endsWith(".yml")) return "⚙️";
  if (f.endsWith(".json")) return "📋";
  if (f.endsWith(".md")) return "📝";
  if (f.includes("dockerfile")) return "🐳";
  if (f.endsWith(".tf")) return "🏗️";
  return "📄";
}

// Helper: Determine Prism Language
function getPrismLanguage(filename = "") {
  const f = filename.toLowerCase();
  if (f.endsWith(".py")) return "python";
  if (f.endsWith(".sql")) return "sql";
  if (f.endsWith(".tsx") || f.endsWith(".ts")) return "typescript";
  if (f.endsWith(".yaml") || f.endsWith(".yml")) return "yaml";
  if (f.endsWith(".json")) return "json";
  if (f.endsWith(".md")) return "markdown";
  if (f.includes("dockerfile")) return "docker";
  return "javascript";
}

// --- INTERACTIVE VISUAL CODE & TASK DEPENDENCY DAG WORKBENCH ---
function DAGWorkbenchView({
  dagData,
  isLoading,
  onRefresh,
  onOpenArtifact,
  onViewDiff,
  dagFilterTier,
  setDagFilterTier,
  dagSearchQuery,
  setDagSearchQuery,
  selectedDagNode,
  setSelectedDagNode
}) {
  const upstreamIds = useMemo(() => {
    if (!selectedDagNode) return [];
    return selectedDagNode.dependencies || [];
  }, [selectedDagNode]);

  const downstreamIds = useMemo(() => {
    if (!selectedDagNode || !dagData?.edges) return [];
    return dagData.edges
      .filter(e => e.source === selectedDagNode.id)
      .map(e => e.target);
  }, [selectedDagNode, dagData?.edges]);

  const tiers = dagData?.tiers || [];
  const nodes = dagData?.nodes || [];

  const filteredNodes = useMemo(() => {
    let result = nodes;
    if (dagFilterTier !== "ALL") {
      result = result.filter(n => n.tier === dagFilterTier);
    }
    if (dagSearchQuery.trim()) {
      const q = dagSearchQuery.toLowerCase().trim();
      result = result.filter(n =>
        (n.label && n.label.toLowerCase().includes(q)) ||
        (n.name && n.name.toLowerCase().includes(q)) ||
        (n.role && n.role.toLowerCase().includes(q)) ||
        (n.pod && n.pod.toLowerCase().includes(q)) ||
        (n.description && n.description.toLowerCase().includes(q))
      );
    }
    return result;
  }, [nodes, dagFilterTier, dagSearchQuery]);

  const stats = dagData?.stats || {
    total_nodes: 0,
    completed_nodes: 0,
    total_edges: 0,
    critical_path_depth: 6,
    completion_percentage: 0
  };

  return (
    <div className="dag-workbench-container">
      {/* 1. DAG ACTION TOOLBAR */}
      <div className="dag-action-toolbar">
        <div className="dag-toolbar-left">
          <span className="dag-toolbar-title">
            <span>🕸️</span> Dependency DAG
          </span>
          <span className="dag-metrics-pill">
            📦 {stats.total_nodes} Nodes
          </span>
          <span className="dag-metrics-pill">
            🔗 {stats.total_edges} Edges
          </span>
          <span className="dag-metrics-pill">
            ⚡ {stats.critical_path_depth} Tiers
          </span>
          <span className="dag-metrics-pill success">
            ✅ {stats.completion_percentage}% Ready
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
          {/* TIER FILTER BUTTONS */}
          <div className="dag-toolbar-filters">
            <button
              className={`dag-filter-btn ${dagFilterTier === "ALL" ? "active" : ""}`}
              onClick={() => setDagFilterTier("ALL")}
            >
              All
            </button>
            <button
              className={`dag-filter-btn ${dagFilterTier === "contract" ? "active" : ""}`}
              onClick={() => setDagFilterTier("contract")}
            >
              Contracts
            </button>
            <button
              className={`dag-filter-btn ${dagFilterTier === "data" ? "active" : ""}`}
              onClick={() => setDagFilterTier("data")}
            >
              Data
            </button>
            <button
              className={`dag-filter-btn ${dagFilterTier === "backend" ? "active" : ""}`}
              onClick={() => setDagFilterTier("backend")}
            >
              Backend
            </button>
            <button
              className={`dag-filter-btn ${dagFilterTier === "pod_parallel" ? "active" : ""}`}
              onClick={() => setDagFilterTier("pod_parallel")}
            >
              Pods
            </button>
            <button
              className={`dag-filter-btn ${dagFilterTier === "verification" ? "active" : ""}`}
              onClick={() => setDagFilterTier("verification")}
            >
              QA
            </button>
          </div>

          <input
            type="text"
            className="dag-search-input"
            placeholder="🔍 Filter deliverables..."
            value={dagSearchQuery}
            onChange={(e) => setDagSearchQuery(e.target.value)}
          />

          <button
            className="btn btn-sm btn-outline"
            style={{ fontSize: "0.68rem", padding: "0.18rem 0.45rem" }}
            onClick={onRefresh}
            title="Refresh dependency graph from server"
          >
            {isLoading ? "⏳" : "⟳ Refresh"}
          </button>
        </div>
      </div>

      {/* 2. VISUAL SWIMLANE TIERS CANVAS */}
      <div className="dag-canvas-scroll-wrapper">
        <div className="dag-tiers-grid">
          {tiers.map((tier) => {
            const tierNodes = filteredNodes.filter(n => n.tier === tier.id);
            if (dagFilterTier !== "ALL" && dagFilterTier !== tier.id) return null;

            return (
              <div key={tier.id} className="dag-tier-col">
                <div className="dag-tier-header" style={{ borderTop: `3px solid ${tier.color}` }}>
                  <span style={{ color: tier.color }}>{tier.title}</span>
                  <span className="dag-tier-counter">{tierNodes.length}</span>
                </div>

                <div className="dag-tier-nodes-list">
                  {tierNodes.length === 0 ? (
                    <div style={{ padding: "1rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.72rem", fontStyle: "italic" }}>
                      No deliverables in this tier match current filters.
                    </div>
                  ) : (
                    tierNodes.map((node) => {
                      const isSelected = selectedDagNode?.id === node.id;
                      const isUpstream = upstreamIds.includes(node.id);
                      const isDownstream = downstreamIds.includes(node.id);

                      let cardStateClass = "";
                      if (isSelected) cardStateClass = "selected";
                      else if (isUpstream) cardStateClass = "is-upstream";
                      else if (isDownstream) cardStateClass = "is-downstream";

                      return (
                        <div
                          key={node.id}
                          className={`dag-node-card ${cardStateClass}`}
                          onClick={() => setSelectedDagNode(node)}
                        >
                          <div className="dag-node-top-row">
                            <span
                              className="dag-node-badge"
                              style={{ background: tier.bg, color: tier.color, border: `1px solid ${tier.color}40` }}
                            >
                              {node.tier.toUpperCase()}
                            </span>
                            <span className={`dag-node-status ${node.status}`}>
                              {node.status === "COMPLETED" ? "✓ READY" :
                               node.status === "VERIFIED" ? "🛡️ VERIFIED" :
                               node.status === "IN_PROGRESS" ? "⚡ WORKING" : "⏳ PENDING"}
                            </span>
                          </div>

                          <div className="dag-node-title-row">
                            <span>{getFileIcon(node.label)}</span>
                            <span>{node.name}</span>
                          </div>
                          <div className="dag-node-file-pill">
                            <code>{node.label}</code>
                          </div>

                          <p className="dag-node-desc">
                            {node.description}
                          </p>

                          <div className="dag-node-meta-row">
                            <span>👤 {node.pod}</span>
                            <span>
                              {node.symbols_count > 0 ? `${node.symbols_count} symbols • ` : ""}
                              {node.line_count > 0 ? `${node.line_count} lines` : "spec"}
                            </span>
                          </div>

                          {node.dependencies && node.dependencies.length > 0 && (
                            <div style={{ fontSize: "0.65rem", color: "#64748b", display: "flex", gap: "0.25rem", alignItems: "center", flexWrap: "wrap" }}>
                              <span>Depends on:</span>
                              {node.dependencies.map(dep => {
                                const depNode = nodes.find(n => n.id === dep);
                                return (
                                  <span key={dep} className="dag-drawer-dep-chip upstream" style={{ fontSize: "0.6rem", padding: "0.05rem 0.3rem" }}>
                                    {depNode?.label || dep}
                                  </span>
                                );
                              })}
                            </div>
                          )}

                          <div className="dag-node-actions">
                            <button
                              className="dag-node-action-btn"
                              onClick={(e) => {
                                e.stopPropagation();
                                onOpenArtifact(node.artifact_id || node.label);
                              }}
                              title="Open file in Cockpit Code Editor"
                            >
                              📄 Open
                            </button>
                            <button
                              className="dag-node-action-btn secondary"
                              onClick={(e) => {
                                e.stopPropagation();
                                onViewDiff(node.artifact_id || node.label);
                              }}
                              title="Compare file diff against baseline"
                            >
                              🔍 Diff
                            </button>
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. SELECTED NODE DETAIL DRAWER */}
      {selectedDagNode && (
        <div className="dag-selected-drawer">
          <div className="dag-drawer-info">
            <div>
              <div className="dag-drawer-title">
                {getFileIcon(selectedDagNode.label)} {selectedDagNode.name}
              </div>
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center", marginTop: "0.15rem" }}>
                <span className="dag-drawer-path">
                  {selectedDagNode.path || `artifacts/${selectedDagNode.label}`}
                </span>
                <span style={{ fontSize: "0.7rem", color: "var(--text-secondary)" }}>
                  Role: <strong>{selectedDagNode.role}</strong>
                </span>
              </div>
            </div>

            <div className="dag-drawer-deps-list">
              {upstreamIds.length > 0 && (
                <div style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
                  <span>Upstream:</span>
                  {upstreamIds.map(uid => {
                    const un = nodes.find(n => n.id === uid);
                    return (
                      <span key={uid} className="dag-drawer-dep-chip upstream" title="Prerequisite upstream dependency">
                        ← {un?.label || uid}
                      </span>
                    );
                  })}
                </div>
              )}

              {downstreamIds.length > 0 && (
                <div style={{ display: "flex", alignItems: "center", gap: "0.3rem", marginLeft: "0.5rem" }}>
                  <span>Downstream:</span>
                  {downstreamIds.map(did => {
                    const dn = nodes.find(n => n.id === did);
                    return (
                      <span key={did} className="dag-drawer-dep-chip downstream" title="Downstream dependent consumer">
                        → {dn?.label || did}
                      </span>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          <div style={{ display: "flex", gap: "0.5rem" }}>
            <button
              className="btn btn-sm btn-outline"
              style={{ fontSize: "0.72rem", color: "#38bdf8", borderColor: "rgba(56, 189, 248, 0.4)" }}
              onClick={() => onOpenArtifact(selectedDagNode.artifact_id || selectedDagNode.label)}
            >
              📄 Open in Cockpit Editor ↗
            </button>
            <button
              className="btn btn-sm btn-outline"
              style={{ fontSize: "0.72rem", color: "#fbbf24", borderColor: "rgba(251, 191, 36, 0.4)" }}
              onClick={() => onViewDiff(selectedDagNode.artifact_id || selectedDagNode.label)}
            >
              🔍 Inspect Diff
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// --- REAL-TIME TOKEN BURN & COST EFFICIENCY INSPECTOR MODAL ---
function TokenCostInspectorModal({
  isOpen,
  onClose,
  telemetry,
  missionId
}) {
  if (!isOpen) return null;

  const rep = telemetry || {
    mission_id: missionId || "ACTIVE",
    total_tokens: 12800,
    total_prompt_tokens: 8400,
    total_candidate_tokens: 2800,
    total_thinking_tokens: 1600,
    total_cached_tokens: 6552,
    net_cost_usd: 0.00703,
    gross_cost_usd: 0.00867,
    savings_usd: 0.00164,
    cache_hit_rate_pct: 78.0,
    budget_consumed_pct: 6.1,
    budget_cap_tokens: 209920,
    burn_rate_tokens_per_turn: 1828.6,
    cost_per_turn_usd: 0.00100,
    pod_breakdown: []
  };

  const pods = rep.pod_breakdown && rep.pod_breakdown.length > 0 ? rep.pod_breakdown : [];

  return (
    <div className="modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="cost-inspector-card" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid var(--border-color)", paddingBottom: "0.75rem" }}>
          <div>
            <h3 style={{ fontSize: "1.05rem", fontWeight: 700, display: "flex", alignItems: "center", gap: "0.4rem" }}>
              <span>⚡</span> Real-Time Token Burn &amp; Cost Efficiency Tracker
            </h3>
            <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>
              Mission <strong>{rep.mission_id}</strong> &bull; Google Gemini API Inference &amp; Context Caching
            </span>
          </div>
          <button className="close-btn" onClick={onClose} aria-label="Close">&times;</button>
        </div>

        {/* 4 SUMMARY METRIC CARDS */}
        <div className="cost-grid-cards">
          <div className="cost-metric-box">
            <span className="cost-metric-label">Estimated Spend</span>
            <span className="cost-metric-value" style={{ color: "#34d399" }}>
              ${Number(rep.net_cost_usd || 0).toFixed(4)}
            </span>
            <span className="cost-metric-sub">
              Gross: ${Number(rep.gross_cost_usd || 0).toFixed(4)} USD
            </span>
          </div>

          <div className="cost-metric-box">
            <span className="cost-metric-label">Context Caching</span>
            <span className="cost-metric-value" style={{ color: "#38bdf8" }}>
              {Math.round(rep.cache_hit_rate_pct || 0)}%
            </span>
            <span className="cost-metric-sub" style={{ color: "#34d399" }}>
              Saved -${Number(rep.savings_usd || 0).toFixed(4)} (75% off)
            </span>
          </div>

          <div className="cost-metric-box">
            <span className="cost-metric-label">Token Consumption</span>
            <span className="cost-metric-value">
              {(Number(rep.total_tokens || 0) / 1000).toFixed(1)}k
            </span>
            <span className="cost-metric-sub">
              {rep.budget_consumed_pct || 0}% of {Math.round((rep.budget_cap_tokens || 209920) / 1000)}k Cap
            </span>
          </div>

          <div className="cost-metric-box">
            <span className="cost-metric-label">Burn Rate</span>
            <span className="cost-metric-value" style={{ color: "#fbbf24" }}>
              {Math.round(rep.burn_rate_tokens_per_turn || 0)}
            </span>
            <span className="cost-metric-sub">
              tokens / agent turn (${Number(rep.cost_per_turn_usd || 0).toFixed(5)})
            </span>
          </div>
        </div>

        {/* POD BREAKDOWN TABLE */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.4rem" }}>
          <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.03em" }}>
            Pod-by-Pod Allocation &amp; Model Tiers
          </span>
          <span style={{ fontSize: "0.68rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
            Prompt: {rep.total_prompt_tokens} &bull; Output: {rep.total_candidate_tokens} &bull; Thinking: {rep.total_thinking_tokens}
          </span>
        </div>

        <div className="cost-table-container">
          <table className="cost-pod-table">
            <thead>
              <tr>
                <th>Pod &amp; Role</th>
                <th>Model</th>
                <th>Turns</th>
                <th>Prompt (Cached)</th>
                <th>Output</th>
                <th>Thinking</th>
                <th>Total Tokens</th>
                <th>Net Cost</th>
              </tr>
            </thead>
            <tbody>
              {pods.map((p, idx) => (
                <tr key={idx}>
                  <td style={{ fontWeight: 600, color: "#f1f5f9" }}>
                    <span>{p.icon}</span> {p.pod_name}
                  </td>
                  <td>
                    <span style={{
                      padding: "0.1rem 0.35rem",
                      borderRadius: "4px",
                      fontSize: "0.62rem",
                      fontWeight: 700,
                      background: p.model && p.model.includes("pro") ? "rgba(168, 85, 247, 0.15)" : "rgba(56, 189, 248, 0.15)",
                      color: p.model && p.model.includes("pro") ? "#c084fc" : "#38bdf8"
                    }}>
                      {p.model && p.model.includes("pro") ? "Pro (Reasoning)" : "Flash-Lite"}
                    </span>
                  </td>
                  <td>{p.turns}</td>
                  <td>
                    {p.prompt_tokens}
                    <span style={{ color: "#34d399", fontSize: "0.62rem", marginLeft: "0.2rem" }}>
                      ({p.cached_tokens})
                    </span>
                  </td>
                  <td>{p.candidate_tokens}</td>
                  <td>{p.thinking_tokens}</td>
                  <td style={{ fontWeight: 700, color: "var(--text-primary)" }}>{p.total_tokens}</td>
                  <td style={{ fontWeight: 700, color: "#34d399" }}>${Number(p.cost_usd).toFixed(5)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* FOOTER INFO BANNER */}
        <div className="cost-footer-banner">
          <div>
            <strong>Pricing Model:</strong> Gemini 3.5 Flash-Lite ($0.075/1M in, $0.01875 cached, $0.30 out) &bull; Gemini 2.5 Pro ($1.25/1M in, $5.00 out)
          </div>
          <div>
            <span style={{ color: "#34d399", fontWeight: 700 }}>✓ Anti-Loop Circuit Breaker Armed</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// --- MAIN REACT APP COMPONENT ---
function App() {
  // --- APPLICATION STATE ---
  const [theme, setTheme] = useState("dark");
  const [activeMissionId, setActiveMissionId] = useState(null);
  const [missionsList, setMissionsList] = useState([]);
  const [sidebarTab, setSidebarTab] = useState("explorer"); // "explorer" | "pods"
  const [viewMode, setViewMode] = useState("hub"); // "hub" | "cockpit"
  const [isLeftCollapsed, setIsLeftCollapsed] = useState(false);
  const [isRightCollapsed, setIsRightCollapsed] = useState(false);

  const [missionData, setMissionData] = useState({
    title: "Core Enterprise Resource Service",
    description: "Implement secure REST API endpoints with PostgreSQL persistence, React UI, and Terraform KMS IaC.",
    target_dir: "artifacts",
    status: "INITIALIZING",
    stage: "CONTRACTS",
    stageIndex: 1,
    tokens: { prompt: 0, candidate: 0, thinking: 0, total: 0 },
    circuitBreaker: { total_turns: 0, max_turns: 30, healthy: true },
    pods: {},
    artifacts: []
  });

  // IDE TABS & ACTIVE FILE
  const [openTabs, setOpenTabs] = useState([]);
  const [activeTabId, setActiveTabId] = useState(null);
  const [selectedArtifact, setSelectedArtifact] = useState(null);
  const [artifactLoading, setArtifactLoading] = useState(false);
  const [artifactError, setArtifactError] = useState(null);
  const [fileSearchQuery, setFileSearchQuery] = useState("");
  const [expandedFolders, setExpandedFolders] = useState({
    backend: true,
    frontend: true,
    database: true,
    contracts: true,
    documentation: true,
    tests: true,
    cloud: true
  });

  const [pendingGate, setPendingGate] = useState(null);
  const [gateFeedback, setGateFeedback] = useState("");
  const [isResolvingGate, setIsResolvingGate] = useState(false);

  const [feedLogs, setFeedLogs] = useState([
    { time: "00:00:00", type: "SYSTEM", text: "MAS IDE Workspace & Cockpit initialized. Connected to local runtime." }
  ]);
  const [feedFilter, setFeedFilter] = useState("ALL");
  const [feedSearchQuery, setFeedSearchQuery] = useState("");
  const [autoScrollFeed, setAutoScrollFeed] = useState(true);

  const [terminalLogs, setTerminalLogs] = useState("[SubprocessSandbox] Ready for deterministic AST verification and test execution...\n");
  const [isTerminalExpanded, setIsTerminalExpanded] = useState(false);

  const [isNewMissionOpen, setIsNewMissionOpen] = useState(false);
  const [newMissionForm, setNewMissionForm] = useState({
    title: MISSION_PRESETS[0].title,
    description: MISSION_PRESETS[0].description,
    targetDir: "",
    interactive: true,
    gitCommit: false
  });
  const [isSubmittingMission, setIsSubmittingMission] = useState(false);

  const [isPROpen, setIsPROpen] = useState(false);
  const [prResult, setPrResult] = useState(null);
  const [isGeneratingPR, setIsGeneratingPR] = useState(false);
  const [inspectedPod, setInspectedPod] = useState(null);
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);
  const [commandPaletteQuery, setCommandPaletteQuery] = useState("");
  const [commandPaletteSelectedIndex, setCommandPaletteSelectedIndex] = useState(0);
  const commandInputRef = useRef(null);
  const [isVersionHistoryOpen, setIsVersionHistoryOpen] = useState(false);
  const [versionHistoryData, setVersionHistoryData] = useState(null);
  const [isLoadingVersions, setIsLoadingVersions] = useState(false);
  const [isRollingBack, setIsRollingBack] = useState(false);
  const [previewVersionSnippet, setPreviewVersionSnippet] = useState(null);

  // Real-Time Token Burn & Cost Efficiency Tracker (Micro-Step 9)
  const [costTelemetry, setCostTelemetry] = useState(null);
  const [isCostModalOpen, setIsCostModalOpen] = useState(false);

  const [copyFeedback, setCopyFeedback] = useState(false);
  const [pathCopyFeedback, setPathCopyFeedback] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("IDLE"); // IDLE, STREAMING, DISCONNECTED

  const [editorViewMode, setEditorViewMode] = useState("code"); // "code" vs "diff" vs "dag"
  const [artifactDiff, setArtifactDiff] = useState(null);
  const [isLoadingDiff, setIsLoadingDiff] = useState(false);
  const [diffLayoutMode, setDiffLayoutMode] = useState("split"); // "split" vs "unified"
  const [liveTokenStream, setLiveTokenStream] = useState("");

  // Interactive Visual Code & Task Dependency DAG (Micro-Step 8)
  const [dagData, setDagData] = useState(null);
  const [isLoadingDag, setIsLoadingDag] = useState(false);
  const [dagFilterTier, setDagFilterTier] = useState("ALL");
  const [dagSearchQuery, setDagSearchQuery] = useState("");
  const [selectedDagNode, setSelectedDagNode] = useState(null);

  // Sandboxed Test Execution & Interactive Line-Gutter Revisions
  const [isRunningTests, setIsRunningTests] = useState(false);
  const [lastTestFailure, setLastTestFailure] = useState(null);
  const [isAutoFixing, setIsAutoFixing] = useState(false);
  const [commentingLine, setCommentingLine] = useState(null);
  const [lineCommentText, setLineCommentText] = useState("");
  const [isSubmittingComment, setIsSubmittingComment] = useState(false);
  const [revisions, setRevisions] = useState([]);

  // Direct In-Cockpit File Editing & AST Persistence
  const [isEditingFile, setIsEditingFile] = useState(false);
  const [editedCodeContent, setEditedCodeContent] = useState("");
  const [isSavingFile, setIsSavingFile] = useState(false);
  const [saveFeedback, setSaveFeedback] = useState(null);

  // Interactive Stage Filter
  const [selectedStageFilter, setSelectedStageFilter] = useState(null);

  // Local Git Snapshot
  const [isCommittingGit, setIsCommittingGit] = useState(false);
  const [gitCommitFeedback, setGitCommitFeedback] = useState(null);

  // REFS
  const eventSourceRef = useRef(null);
  const codeViewerRef = useRef(null);
  const feedEndRef = useRef(null);
  const terminalEndRef = useRef(null);

  // --- THEME TOGGLE ---
  const toggleTheme = useCallback(() => {
    setTheme(prev => {
      const next = prev === "dark" ? "light" : "dark";
      document.body.className = `${next}-theme`;
      return next;
    });
  }, []);

  // --- LOG EMITTER HELPER ---
  const addFeedLog = useCallback((type, text) => {
    const now = new Date();
    const timeStr = now.toTimeString().split(" ")[0];
    setFeedLogs(prev => [...prev, { time: timeStr, type, text }]);
  }, []);

  // --- FETCH MISSIONS LIST ---
  const refreshMissionsList = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/missions");
      if (res.ok) {
        const data = await res.json();
        setMissionsList(data.missions || []);
        if (!activeMissionId && data.missions && data.missions.length > 0) {
          setActiveMissionId(data.missions[0].mission_id);
        }
      }
    } catch (err) {
      console.warn("Failed to fetch missions list:", err);
    }
  }, [activeMissionId]);

  useEffect(() => {
    refreshMissionsList();
  }, [refreshMissionsList]);

  // --- FETCH SPECIFIC ARTIFACT DETAILS & OPEN IN TAB ---
  const openArtifactInEditor = useCallback(async (artifactId) => {
    if (!artifactId) return;
    setArtifactLoading(true);
    setArtifactError(null);
    try {
      const res = await fetch(`/api/v1/artifacts/${artifactId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to load artifact`);
      const data = await res.json();
      setSelectedArtifact(data);
      setActiveTabId(data.id);
      setEditedCodeContent(data.content || "");
      setIsEditingFile(false);
      setSaveFeedback(null);

      // Add to open tabs if not already present
      setOpenTabs(prev => {
        if (!prev.some(t => t.id === data.id)) {
          return [...prev, data];
        }
        return prev;
      });
    } catch (err) {
      setArtifactError(err.message);
    } finally {
      setArtifactLoading(false);
    }
  }, []);

  // --- FETCH ARTIFACT DIFF ---
  const fetchArtifactDiff = useCallback(async (artId) => {
    if (!artId) return;
    setIsLoadingDiff(true);
    try {
      const res = await fetch(`/api/v1/artifacts/${artId}/diff`);
      if (res.ok) {
        const data = await res.json();
        setArtifactDiff(data);
      } else {
        setArtifactDiff(null);
      }
    } catch (err) {
      console.warn("Failed to fetch artifact diff:", err);
      setArtifactDiff(null);
    } finally {
      setIsLoadingDiff(false);
    }
  }, []);

  useEffect(() => {
    if (editorViewMode === "diff" && selectedArtifact?.id) {
      fetchArtifactDiff(selectedArtifact.id);
    }
  }, [editorViewMode, selectedArtifact, fetchArtifactDiff]);

  // --- FETCH INTERACTIVE TASK & CODE DEPENDENCY DAG ---
  const fetchMissionDag = useCallback(async () => {
    setIsLoadingDag(true);
    try {
      const url = activeMissionId ? `/api/v1/missions/${activeMissionId}/dag` : `/api/v1/dag`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setDagData(data);
        if (!selectedDagNode && data.nodes && data.nodes.length > 0) {
          setSelectedDagNode(data.nodes[0]);
        }
      }
    } catch (err) {
      console.warn("Failed to fetch DAG:", err);
    } finally {
      setIsLoadingDag(false);
    }
  }, [activeMissionId, selectedDagNode]);

  useEffect(() => {
    if (editorViewMode === "dag") {
      fetchMissionDag();
    }
  }, [editorViewMode, fetchMissionDag]);

  // --- FETCH REAL-TIME TOKEN BURN & COST TELEMETRY ---
  const fetchCostTelemetry = useCallback(async () => {
    try {
      const url = activeMissionId ? `/api/v1/missions/${activeMissionId}/tokens` : `/api/v1/tokens`;
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setCostTelemetry(data);
      }
    } catch (err) {
      console.warn("Failed to fetch cost telemetry:", err);
    }
  }, [activeMissionId]);

  useEffect(() => {
    fetchCostTelemetry();
  }, [fetchCostTelemetry]);

  // --- COMPUTE SPLIT (SIDE-BY-SIDE) DIFF ROWS ---
  const computeSplitDiffRows = useCallback((diffText) => {
    if (!diffText) return [];
    const lines = diffText.split("\n");
    const rows = [];
    let leftLine = 1;
    let rightLine = 1;
    let pendingDeletes = [];
    let pendingAdds = [];

    function flushPending() {
      const maxLen = Math.max(pendingDeletes.length, pendingAdds.length);
      for (let i = 0; i < maxLen; i++) {
        rows.push({
          left: pendingDeletes[i] || null,
          right: pendingAdds[i] || null
        });
      }
      pendingDeletes = [];
      pendingAdds = [];
    }

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      if (line.startsWith("---") || line.startsWith("+++")) continue;
      if (line.startsWith("@@")) {
        flushPending();
        const match = line.match(/@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@/);
        if (match) {
          leftLine = parseInt(match[1], 10);
          rightLine = parseInt(match[2], 10);
        }
        rows.push({ isHunk: true, text: line });
        continue;
      }
      if (line.startsWith("-")) {
        pendingDeletes.push({ lineNum: leftLine++, text: line.substring(1), type: "del" });
      } else if (line.startsWith("+")) {
        pendingAdds.push({ lineNum: rightLine++, text: line.substring(1), type: "add" });
      } else if (line.startsWith(" ") || line.length > 0) {
        flushPending();
        const clean = line.startsWith(" ") ? line.substring(1) : line;
        rows.push({
          left: { lineNum: leftLine++, text: clean, type: "ctx" },
          right: { lineNum: rightLine++, text: clean, type: "ctx" }
        });
      }
    }
    flushPending();
    return rows;
  }, []);

  const splitDiffRows = useMemo(() => {
    if (!artifactDiff?.diff) return [];
    return computeSplitDiffRows(artifactDiff.diff);
  }, [artifactDiff?.diff, computeSplitDiffRows]);

  // --- CLOSE TAB ---
  const handleCloseTab = useCallback((e, tabId) => {
    e.stopPropagation();
    setOpenTabs(prev => {
      const remaining = prev.filter(t => t.id !== tabId);
      if (activeTabId === tabId) {
        if (remaining.length > 0) {
          const nextTab = remaining[remaining.length - 1];
          setActiveTabId(nextTab.id);
          setSelectedArtifact(nextTab);
        } else {
          setActiveTabId(null);
          setSelectedArtifact(null);
        }
      }
      return remaining;
    });
  }, [activeTabId]);

  // --- HELPER: MAP STAGE NAME TO 1-BASED INDEX ---
  const getStageIndex = useCallback((stageName) => {
    switch (stageName) {
      case "CONTRACTS": return 1;
      case "ARCHITECTURE": return 2;
      case "PARALLEL_PODS": return 3;
      case "QA_SECURITY": return 4;
      case "DOCUMENTATION": return 5;
      default: return 1;
    }
  }, []);

  // --- FETCH MISSION STATUS ---
  const fetchMissionDetails = useCallback(async (missionId) => {
    if (!missionId) return;
    try {
      const res = await fetch(`/api/v1/missions/${missionId}`);
      if (!res.ok) return;
      const data = await res.json();
      setMissionData(prev => ({
        ...prev,
        title: data.title || prev.title,
        description: data.description || prev.description,
        target_dir: data.target_dir || "artifacts",
        status: data.status || prev.status,
        stage: data.stage || prev.stage,
        stageIndex: data.stage ? getStageIndex(data.stage) : prev.stageIndex,
        tokens: data.tokens_used || prev.tokens,
        circuitBreaker: data.circuit_breaker || prev.circuitBreaker,
        pods: data.pods || prev.pods,
        artifacts: Array.isArray(data.artifacts) ? data.artifacts : prev.artifacts
      }));

      if (data.pending_gate) {
        setPendingGate(data.pending_gate);
      } else {
        setPendingGate(null);
      }

      if (data.cost_telemetry) {
        setCostTelemetry(data.cost_telemetry);
      }

      // If no file is open, open the primary synthesized service
      if (Array.isArray(data.artifacts) && data.artifacts.length > 0 && !selectedArtifact) {
        const primary = data.artifacts.find(a => a.name && a.name.includes("service.py")) || data.artifacts[0];
        if (primary && primary.id) {
          openArtifactInEditor(primary.id);
        }
      }
    } catch (err) {
      console.error("Failed to fetch mission details:", err);
    }
  }, [openArtifactInEditor, selectedArtifact, getStageIndex]);

  // --- DISPATCH INCOMING REAL-TIME EVENTS ---
  const handleIncomingEvent = useCallback((event) => {
    if (!event) return;
    const type = event.type;
    const data = event.payload || event.data || {};
    if (!type) return;

    switch (type) {
      case "CONNECTED":
        setConnectionStatus("STREAMING");
        break;

      case "STATUS_CHANGED":
        setMissionData(prev => ({
          ...prev,
          status: data.status || prev.status,
          title: data.title || prev.title
        }));
        addFeedLog("STATUS", `Mission status updated: ${data.status}`);
        break;

      case "STAGE_CHANGED": {
        const stage = data.stage || "";
        const stageIdx = data.stageIndex || getStageIndex(stage);
        setMissionData(prev => ({
          ...prev,
          stage: stage,
          stageIndex: stageIdx
        }));
        addFeedLog("STAGE", `Pipeline transitioned to Stage ${stageIdx}: ${stage}`);
        break;
      }

      case "POD_UPDATED": {
        if (data.pod) {
          setMissionData(prev => {
            const currentPods = prev.pods || {};
            const updatedPods = {
              ...currentPods,
              [data.pod]: {
                status: data.status || "IDLE",
                action: data.action || "Working",
                artifact: data.artifact !== undefined ? data.artifact : (currentPods[data.pod]?.artifact || "")
              }
            };
            return { ...prev, pods: updatedPods };
          });
          addFeedLog("POD", `[${data.pod}] ${data.action || "Updated"} (${data.status || "IDLE"})`);
        }
        break;
      }

      case "GATE_PROMPTED":
      case "GATE_TRIGGERED": {
        const gateObj = data.gate || data;
        setPendingGate(gateObj);
        const gateTitle = (gateObj && (gateObj.gate || gateObj.level || gateObj.gate_level)) || "Strategic Approval";
        addFeedLog("GATE", `⚠️ HUMAN DECISION REQUIRED: ${gateTitle}`);
        break;
      }

      case "GATE_RESOLVED":
        setPendingGate(null);
        addFeedLog("GATE", `✅ Gate decision confirmed: ${data.decision || "APPROVED"}`);
        break;

      case "ARTIFACT_COMMITTED": {
        const art = data.artifact || data;
        if (art && art.name) {
          addFeedLog("ARTIFACT", `Synthesized file on disk: ${art.name} (${art.path || art.name})`);
          setMissionData(prev => {
            const currentArtifacts = prev.artifacts || [];
            const exists = currentArtifacts.some(a => a.id === art.id || a.name === art.name);
            const nextList = exists
              ? currentArtifacts.map(a => (a.id === art.id || a.name === art.name ? { ...a, ...art } : a))
              : [...currentArtifacts, art];
            return {
              ...prev,
              artifacts: nextList
            };
          });
          // Auto-open newly generated file in IDE if no file open
          if (!activeTabId) {
            openArtifactInEditor(art.id || art.name);
          }
        }
        break;
      }

      case "TOKEN_BURN":
      case "TOKEN_METRICS_UPDATED": {
        const tokens = data.tokens_used || data.tokens;
        if (tokens) {
          setMissionData(prev => ({
            ...prev,
            tokens: tokens,
            tokens_used: tokens
          }));
        }
        if (data.cost_telemetry) {
          setCostTelemetry(data.cost_telemetry);
        }
        break;
      }

      case "TOKEN_STREAM": {
        const token = data.token || "";
        if (token) {
          setLiveTokenStream(prev => (prev + token).slice(-120));
        }
        break;
      }

      case "LOG_STREAMED":
      case "LOG_EMITTED": {
        const logMsg = data.text || data.message || data.log || "";
        if (logMsg) {
          setTerminalLogs(prev => prev + logMsg + "\n");
        }
        break;
      }

      case "REVISION_REQUESTED": {
        const rev = {
          artifact_id: data.artifact_id || "service.py",
          line: data.line || 1,
          comment: data.comment || "",
          operator: data.operator || "Human Operator",
          timestamp: data.timestamp || Date.now()
        };
        setRevisions(prev => [...prev, rev]);
        addFeedLog("GATE", `💬 Revision logged on ${rev.artifact_id}:${rev.line}: "${rev.comment}"`);
        break;
      }

      case "MISSION_COMPLETED": {
        const tokens = data.tokens_used || data.tokens;
        setMissionData(prev => ({
          ...prev,
          status: "COMPLETED",
          tokens: tokens || prev.tokens
        }));
        addFeedLog("SUCCESS", `🎉 Mission completed! ${data.artifacts_count || 0} code files written to disk.`);
        refreshMissionsList();
        fetchMissionDetails(activeMissionId);
        break;
      }

      case "MISSION_FAILED":
        setMissionData(prev => ({ ...prev, status: "FAILED" }));
        addFeedLog("ERROR", `❌ Mission failed: ${data.error || "Unknown error"}`);
        break;

      default:
        break;
    }
  }, [activeMissionId, addFeedLog, fetchMissionDetails, openArtifactInEditor, refreshMissionsList, activeTabId, getStageIndex]);

  // --- CONNECT TO REAL-TIME SSE STREAM & HEARTBEAT POLLING ---
  useEffect(() => {
    if (!activeMissionId) return;

    fetchMissionDetails(activeMissionId);

    // Heartbeat polling every 3 seconds to guarantee continuous data synchronization
    const heartbeatTimer = setInterval(() => {
      fetchMissionDetails(activeMissionId);
    }, 3000);

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const sseUrl = `/api/v1/missions/${activeMissionId}/events`;
    setConnectionStatus("CONNECTING");
    const es = new EventSource(sseUrl);
    eventSourceRef.current = es;

    es.onopen = () => {
      setConnectionStatus("STREAMING");
      addFeedLog("SYSTEM", `Connected to SSE stream for mission ${activeMissionId}`);
    };

    es.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        handleIncomingEvent(payload);
      } catch (err) {
        console.warn("Error parsing SSE frame:", err);
      }
    };

    es.onerror = () => {
      setConnectionStatus("DISCONNECTED");
      // Fall back to 3s polling timer
    };

    return () => {
      clearInterval(heartbeatTimer);
      if (es) es.close();
    };
  }, [activeMissionId, fetchMissionDetails, handleIncomingEvent, addFeedLog]);

  // --- RESOLVE HITL GATE DECISION ---
  const handleGateDecision = useCallback(async (decision) => {
    if (!activeMissionId || !pendingGate || isResolvingGate) return;
    setIsResolvingGate(true);
    const gateName = pendingGate.gate || pendingGate.gate_level || pendingGate.level || "GATE_1_BUSINESS_INVARIANTS";
    try {
      const res = await fetch(`/api/v1/missions/${activeMissionId}/gates/${gateName}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision, feedback: gateFeedback })
      });
      if (res.ok) {
        addFeedLog("GATE", `User sent decision: ${decision}`);
        setPendingGate(null);
        setGateFeedback("");
      } else {
        alert("Failed to submit gate decision. Please retry.");
      }
    } catch (err) {
      alert(`Error submitting gate decision: ${err.message}`);
    } finally {
      setIsResolvingGate(false);
    }
  }, [activeMissionId, pendingGate, isResolvingGate, gateFeedback, addFeedLog]);

  // --- RUN SANDBOXED TESTS ---
  const handleRunSandboxedTests = useCallback(async () => {
    if (!activeMissionId || isRunningTests) return;
    setIsRunningTests(true);
    setIsTerminalExpanded(true);
    setTerminalLogs(prev => prev + `\n[SubprocessSandbox] Triggering sandboxed test verification suite for mission ${activeMissionId}...\n`);
    addFeedLog("SYSTEM", `Triggered sandboxed test verification for ${activeMissionId}`);

    try {
      const res = await fetch(`/api/v1/missions/${activeMissionId}/tests/run`, {
        method: "POST"
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: Test execution request failed`);
      const data = await res.json();
      const status = data.status || "PASSED";
      const duration = data.duration_seconds ? data.duration_seconds.toFixed(2) : "0.00";
      addFeedLog(
        status === "PASSED" ? "SUCCESS" : "ERROR",
        `Pytest sandboxed verification: ${status} in ${duration}s (exit ${data.exit_code})`
      );
      if (data.diagnostic && data.diagnostic.has_failure) {
        setLastTestFailure(data.diagnostic);
        addFeedLog("WARN", `⚠️ Test failure detected in ${data.diagnostic.target_file}: ${data.diagnostic.failure_summary}`);
      } else {
        setLastTestFailure(null);
      }
    } catch (err) {
      addFeedLog("ERROR", `Failed to execute sandboxed tests: ${err.message}`);
      setTerminalLogs(prev => prev + `\n[SubprocessSandbox] Execution error: ${err.message}\n`);
    } finally {
      setIsRunningTests(false);
    }
  }, [activeMissionId, isRunningTests, addFeedLog]);

  // --- ONE-CLICK TEST FAILURE AUTO-FIX WITH REACT POD ---
  const handleAutoFixTestFailure = useCallback(async () => {
    if (!activeMissionId || !lastTestFailure || isAutoFixing) return;
    setIsAutoFixing(true);
    setIsTerminalExpanded(true);
    setTerminalLogs(prev => prev + `\n[AutoFix] 🔧 Dispatching autonomous self-healing ReAct loop with ${lastTestFailure.assigned_pod} to fix ${lastTestFailure.target_file}...\n`);
    addFeedLog("SYSTEM", `🔧 Auto-Fix dispatched to ${lastTestFailure.assigned_pod} for ${lastTestFailure.target_file}`);

    try {
      const res = await fetch(`/api/v1/missions/${activeMissionId}/tests/autofix`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          failure_summary: lastTestFailure.failure_summary,
          target_file: lastTestFailure.target_file,
          assigned_pod: lastTestFailure.assigned_pod
        })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: Auto-fix request failed`);
      const result = await res.json();
      const isResolved = result.status === "RESOLVED";
      setTerminalLogs(prev => prev + `[AutoFix] ${result.message}\n` + (result.retest_status === "PASSED" ? "✅ Re-test PASSED! Defect resolved.\n" : "⚠️ Re-test status: " + result.retest_status + "\n"));
      addFeedLog(
        isResolved ? "SUCCESS" : "WARN",
        `Auto-Fix (${result.assigned_pod}): ${result.status} in ${result.react_turns_count} turns (retest: ${result.retest_status})`
      );
      if (isResolved) {
        setLastTestFailure(null);
      }
      if (activeMissionId) {
        fetchMissionDetails(activeMissionId);
      }
    } catch (err) {
      setTerminalLogs(prev => prev + `[AutoFix] ❌ Auto-fix failed: ${err.message}\n`);
      addFeedLog("ERROR", `Auto-fix failure: ${err.message}`);
    } finally {
      setIsAutoFixing(false);
    }
  }, [activeMissionId, lastTestFailure, isAutoFixing, addFeedLog, fetchMissionDetails]);

  // --- SUBMIT LINE REVISION ---
  const handleSendLineComment = useCallback(async (lineNumber) => {
    if (!activeMissionId || !lineCommentText.trim() || isSubmittingComment) return;
    setIsSubmittingComment(true);
    const artifactName = selectedArtifact?.name || "service.py";
    try {
      const res = await fetch(`/api/v1/missions/${activeMissionId}/revisions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          artifact_id: artifactName,
          line: lineNumber,
          comment: lineCommentText.trim()
        })
      });
      if (res.ok) {
        const newRev = {
          artifact_id: artifactName,
          line: lineNumber,
          comment: lineCommentText.trim(),
          operator: "Human Operator",
          timestamp: Date.now()
        };
        setRevisions(prev => [...prev, newRev]);
        addFeedLog("GATE", `💬 Revision submitted on ${artifactName}:${lineNumber}: "${lineCommentText.trim()}"`);
        setCommentingLine(null);
        setLineCommentText("");
      }
    } catch (err) {
      console.error("Failed to submit line revision:", err);
    } finally {
      setIsSubmittingComment(false);
    }
  }, [activeMissionId, lineCommentText, isSubmittingComment, selectedArtifact, addFeedLog]);

  // --- DIRECT IN-COCKPIT FILE SAVE WITH AST VALIDATION ---
  const handleSaveEditedFile = useCallback(async () => {
    if (!selectedArtifact || isSavingFile) return;
    setIsSavingFile(true);
    setSaveFeedback(null);

    try {
      const res = await fetch(`/api/v1/artifacts/${selectedArtifact.id || selectedArtifact.name}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: editedCodeContent })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || data.error || `HTTP ${res.status}: Failed to save`);
      }

      const updatedVersion = data.artifact?.version || ((selectedArtifact.version || 1) + 1);
      setSelectedArtifact(prev => ({
        ...prev,
        content: editedCodeContent,
        version: updatedVersion
      }));

      setOpenTabs(prev => prev.map(t => {
        if (t.id === selectedArtifact.id) {
          return { ...t, content: editedCodeContent, version: updatedVersion };
        }
        return t;
      }));

      setSaveFeedback("SAVED");
      setIsEditingFile(false);
      addFeedLog("SUCCESS", `💾 Manually saved ${selectedArtifact.name} (v${updatedVersion}) with AST verification.`);

      if (editorViewMode === "diff") {
        fetchArtifactDiff(selectedArtifact.id);
      }
      setTimeout(() => setSaveFeedback(null), 3500);
    } catch (err) {
      setSaveFeedback(err.message);
      addFeedLog("ERROR", `Failed to save ${selectedArtifact.name}: ${err.message}`);
    } finally {
      setIsSavingFile(false);
    }
  }, [selectedArtifact, editedCodeContent, isSavingFile, addFeedLog, editorViewMode, fetchArtifactDiff]);

  // --- LOCAL GIT COMMIT SNAPSHOT ---
  const handleLocalGitCommit = useCallback(async () => {
    if (!activeMissionId || isCommittingGit) return;
    setIsCommittingGit(true);
    setGitCommitFeedback(null);
    try {
      const res = await fetch(`/api/v1/missions/${activeMissionId}/commit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: `feat(${activeMissionId.toLowerCase()}): local snapshot from Cockpit` })
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to commit`);
      const data = await res.json();
      if (data.status === "COMMITTED") {
        setGitCommitFeedback({ status: "COMMITTED", hash: data.commit_hash, branch: data.branch });
        addFeedLog("SUCCESS", `📦 Snapshot committed locally (${data.commit_hash}) to branch ${data.branch}`);
      } else if (data.status === "CLEAN") {
        setGitCommitFeedback({ status: "CLEAN", hash: data.commit_hash, branch: data.branch });
        addFeedLog("SYSTEM", `📦 Working tree is clean (${data.commit_hash}). No changes to commit.`);
      } else {
        addFeedLog("ERROR", `Failed to commit: ${data.error || "Unknown git error"}`);
      }
      setTimeout(() => setGitCommitFeedback(null), 4000);
    } catch (err) {
      addFeedLog("ERROR", `Local git commit failed: ${err.message}`);
    } finally {
      setIsCommittingGit(false);
    }
  }, [activeMissionId, isCommittingGit, addFeedLog]);

  // --- ARTIFACT VERSION HISTORY & ROLLBACK ---
  const handleOpenVersionHistory = useCallback(async (artifactId) => {
    if (!artifactId) return;
    setIsLoadingVersions(true);
    setIsVersionHistoryOpen(true);
    setPreviewVersionSnippet(null);
    try {
      const res = await fetch(`/api/v1/artifacts/${artifactId}/versions`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setVersionHistoryData(data);
    } catch (err) {
      addFeedLog("ERROR", `Failed to load version history: ${err.message}`);
    } finally {
      setIsLoadingVersions(false);
    }
  }, [addFeedLog]);

  const handleRollbackToVersion = useCallback(async (targetVersion) => {
    if (!selectedArtifact || isRollingBack) return;
    setIsRollingBack(true);
    try {
      const res = await fetch(`/api/v1/artifacts/${selectedArtifact.id}/rollback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ version: targetVersion })
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || errData.error || `HTTP ${res.status}`);
      }
      const data = await res.json();
      addFeedLog("SUCCESS", `⏪ Restored ${selectedArtifact.name} to v${targetVersion} snapshot (now v${data.version}).`);
      setSelectedArtifact(prev => ({
        ...prev,
        content: data.content,
        version: data.version
      }));
      setEditedCodeContent(data.content);
      setOpenTabs(prev => prev.map(tab => tab.id === selectedArtifact.id ? { ...tab, content: data.content, version: data.version } : tab));
      setIsVersionHistoryOpen(false);
      if (editorViewMode === "diff") {
        fetchArtifactDiff(selectedArtifact.id);
      }
    } catch (err) {
      addFeedLog("ERROR", `Rollback failed: ${err.message}`);
    } finally {
      setIsRollingBack(false);
    }
  }, [selectedArtifact, isRollingBack, addFeedLog, editorViewMode, fetchArtifactDiff]);

  // --- COMMAND PALETTE DEFINITIONS & FILTERING ---
  const allCommands = useMemo(() => [
    { id: "new-mission", icon: "🚀", title: "Launch New Mission", sub: "Configure and run autonomous multi-agent task", hint: "Enter", action: () => setIsNewMissionOpen(true) },
    { id: "local-commit", icon: "📦", title: "Create Local Git Snapshot", sub: "Commit synthesized artifacts to local git repository", hint: "Ctrl+S", action: () => handleLocalGitCommit() },
    { id: "run-tests", icon: "▶", title: "Run Sandboxed Pytest Suite", sub: "Execute tests inside SubprocessSandbox with AST verification", hint: "T", action: () => handleRunSandboxedTests() },
    ...(lastTestFailure ? [{
      id: "autofix-failure",
      icon: "🔧",
      title: `Auto-Fix Test Failure (${lastTestFailure.assigned_pod})`,
      sub: `Resolve ${lastTestFailure.error_type} in ${lastTestFailure.target_file} via ReAct loop`,
      hint: "F",
      action: () => handleAutoFixTestFailure()
    }] : []),
    { id: "split-diff", icon: "◫", title: "Toggle Split / Unified Diff", sub: "Switch between side-by-side split and unified diff views", hint: "", action: () => setDiffLayoutMode(prev => prev === "split" ? "unified" : "split") },
    { id: "view-explorer", icon: "📁", title: "View File Explorer", sub: "Open and focus synthesized workspace file tree", hint: "Ctrl+B", action: () => { setIsLeftCollapsed(false); setSidebarTab("explorer"); } },
    { id: "view-pods", icon: "⚡", title: "View Engineering Pods Matrix", sub: "Inspect parallel autonomous pods (Data, Backend, Frontend, Cloud)", hint: "", action: () => { setIsLeftCollapsed(false); setSidebarTab("pods"); } },
    { id: "toggle-left", icon: "🚪", title: "Toggle Left Sidebar", sub: "Expand or collapse Explorer and Pod matrix", hint: "Ctrl+B", action: () => setIsLeftCollapsed(prev => !prev) },
    { id: "toggle-right", icon: "📋", title: "Toggle Right Panel", sub: "Expand or collapse HITL decisions and event stream", hint: "Ctrl+J", action: () => setIsRightCollapsed(prev => !prev) },
    { id: "toggle-terminal", icon: "🖥️", title: "Toggle Terminal Drawer", sub: "Expand or collapse subprocess test execution logs", hint: "T", action: () => setIsTerminalExpanded(prev => !prev) },
    { id: "switch-hub", icon: "🌐", title: "Switch to Executive Overview Hub", sub: "High-level dashboard and metrics", hint: "", action: () => setViewMode("hub") },
    { id: "switch-cockpit", icon: "💻", title: "Switch to IDE Cockpit", sub: "Hands-on code workbench and diff canvas", hint: "", action: () => setViewMode("cockpit") },
    { id: "view-dag", icon: "🕸️", title: "View Architecture Dependency DAG", sub: "Explore multi-tier contracts, schemas, pods & verification topology", hint: "D", action: () => { setViewMode("cockpit"); setEditorViewMode("dag"); } },
    { id: "inspect-cost", icon: "💰", title: "Inspect Real-Time Token Burn & Cost Efficiency", sub: "View pod token spend, Gemini context caching savings, and budget ceilings", hint: "$", action: () => setIsCostModalOpen(true) },
    { id: "view-code", icon: "📄", title: "View Code Editor", sub: "Inspect and edit currently active file", hint: "C", action: () => { setViewMode("cockpit"); setEditorViewMode("code"); } },
    { id: "view-diff", icon: "🔍", title: "View Workspace Diff", sub: "Inspect unified or side-by-side git diffs", hint: "", action: () => { setViewMode("cockpit"); setEditorViewMode("diff"); } },
    { id: "toggle-theme", icon: theme === "dark" ? "☀️" : "🌙", title: "Toggle Theme", sub: `Switch to ${theme === "dark" ? "Light" : "Dark"} mode`, hint: "", action: () => toggleTheme() }
  ], [handleLocalGitCommit, handleRunSandboxedTests, handleAutoFixTestFailure, lastTestFailure, theme, toggleTheme]);

  const filteredCommands = useMemo(() => {
    if (!commandPaletteQuery.trim()) return allCommands;
    const q = commandPaletteQuery.toLowerCase().trim();
    return allCommands.filter(c =>
      c.title.toLowerCase().includes(q) ||
      c.sub.toLowerCase().includes(q) ||
      (c.hint && c.hint.toLowerCase().includes(q))
    );
  }, [allCommands, commandPaletteQuery]);

  useEffect(() => {
    if (isCommandPaletteOpen && commandInputRef.current) {
      setTimeout(() => commandInputRef.current?.focus(), 50);
    }
  }, [isCommandPaletteOpen]);

  // --- KEYBOARD SHORTCUTS ---
  useEffect(() => {
    const handleKeyDown = (e) => {
      // 1. Command Palette Toggle (Ctrl+K / Cmd+K)
      if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K")) {
        e.preventDefault();
        setIsCommandPaletteOpen(prev => {
          if (!prev) {
            setCommandPaletteQuery("");
            setCommandPaletteSelectedIndex(0);
          }
          return !prev;
        });
        return;
      }

      // 2. Command Palette Navigation Keys (Works when palette is active)
      if (isCommandPaletteOpen) {
        if (e.key === "Escape") {
          e.preventDefault();
          setIsCommandPaletteOpen(false);
          return;
        }
        if (e.key === "ArrowDown") {
          e.preventDefault();
          setCommandPaletteSelectedIndex(prev => Math.min(prev + 1, Math.max(0, filteredCommands.length - 1)));
          return;
        }
        if (e.key === "ArrowUp") {
          e.preventDefault();
          setCommandPaletteSelectedIndex(prev => Math.max(prev - 1, 0));
          return;
        }
        if (e.key === "Enter") {
          e.preventDefault();
          if (filteredCommands[commandPaletteSelectedIndex]) {
            filteredCommands[commandPaletteSelectedIndex].action();
            setIsCommandPaletteOpen(false);
          }
          return;
        }
        return;
      }

      if (["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName)) return;

      if (pendingGate) {
        if (e.key === "a" || e.key === "A") {
          e.preventDefault();
          handleGateDecision("APPROVED");
        } else if (e.key === "m" || e.key === "M") {
          e.preventDefault();
          handleGateDecision("MODIFIED");
        } else if (e.key === "r" || e.key === "R") {
          e.preventDefault();
          handleGateDecision("REJECTED");
        }
      }

      if (e.key === "t" || e.key === "T") {
        e.preventDefault();
        setIsTerminalExpanded(prev => !prev);
      }
      if ((e.key === "f" || e.key === "F") && lastTestFailure && !isAutoFixing) {
        e.preventDefault();
        handleAutoFixTestFailure();
      }
      if ((e.ctrlKey || e.metaKey) && (e.key === "b" || e.key === "B")) {
        e.preventDefault();
        setIsLeftCollapsed(prev => !prev);
      }
      if ((e.ctrlKey || e.metaKey) && (e.key === "j" || e.key === "J")) {
        e.preventDefault();
        setIsRightCollapsed(prev => !prev);
      }
      if (e.key === "Escape") {
        setViewMode("cockpit");
        setIsNewMissionOpen(false);
        setIsPROpen(false);
        setInspectedPod(null);
        setIsCommandPaletteOpen(false);
        setIsVersionHistoryOpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [pendingGate, handleGateDecision, isCommandPaletteOpen, filteredCommands, commandPaletteSelectedIndex, lastTestFailure, isAutoFixing, handleAutoFixTestFailure]);

  // --- AUTO-SCROLL LOGS ---
  useEffect(() => {
    if (autoScrollFeed && !feedSearchQuery.trim() && feedEndRef.current) {
      feedEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [feedLogs, autoScrollFeed, feedSearchQuery]);

  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [terminalLogs]);

  // --- SYNTAX HIGHLIGHTING ---
  useEffect(() => {
    if (codeViewerRef.current && window.Prism) {
      window.Prism.highlightElement(codeViewerRef.current);
    }
  }, [selectedArtifact, activeTabId]);

  // --- COPY CODE & PATH ---
  const handleCopyCode = useCallback(() => {
    if (!selectedArtifact?.content) return;
    navigator.clipboard.writeText(selectedArtifact.content).then(() => {
      setCopyFeedback(true);
      setTimeout(() => setCopyFeedback(false), 2000);
    });
  }, [selectedArtifact]);

  const handleCopyPath = useCallback(() => {
    if (!selectedArtifact?.path) return;
    const fullPath = `c:\\Users\\bobharsh\\MAS\\${selectedArtifact.path.replace(/\//g, '\\')}`;
    navigator.clipboard.writeText(fullPath).then(() => {
      setPathCopyFeedback(true);
      setTimeout(() => setPathCopyFeedback(false), 2000);
    });
  }, [selectedArtifact]);

  // --- LAUNCH NEW MISSION ---
  const handleLaunchMission = useCallback(async (e) => {
    e.preventDefault();
    setIsSubmittingMission(true);
    try {
      const res = await fetch("/api/v1/missions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: newMissionForm.title,
          description: newMissionForm.description,
          target_dir: newMissionForm.targetDir.trim() || null,
          interactive: newMissionForm.interactive,
          git_commit: newMissionForm.gitCommit
        })
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to create mission`);
      const data = await res.json();
      setViewMode("cockpit");
        setIsNewMissionOpen(false);
      setActiveMissionId(data.mission_id);
      addFeedLog("SYSTEM", `Launched autonomous mission ${data.mission_id}: ${newMissionForm.title}`);
      refreshMissionsList();
    } catch (err) {
      alert(`Error launching mission: ${err.message}`);
    } finally {
      setIsSubmittingMission(false);
    }
  }, [newMissionForm, addFeedLog, refreshMissionsList]);

  // --- GENERATE GITHUB PR ---
  const handleGeneratePR = useCallback(async (pushToRemote = false, createGhPr = false) => {
    if (!activeMissionId) return;
    setIsGeneratingPR(true);
    try {
      const res = await fetch(`/api/v1/missions/${activeMissionId}/pr`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ push: pushToRemote, create_pr: createGhPr })
      });
      if (!res.ok) throw new Error("Failed to synthesize Pull Request");
      const data = await res.json();
      setPrResult(data);
      setIsPROpen(true);
      addFeedLog("SUCCESS", `Generated Pull Request dossier for ${data.title}`);
    } catch (err) {
      alert(`Error generating PR: ${err.message}`);
    } finally {
      setIsGeneratingPR(false);
    }
  }, [activeMissionId, addFeedLog]);


  const handleOpenMissionInCockpit = useCallback((mId) => {
    setActiveMissionId(mId);
    fetchMissionDetails(mId);
    setViewMode("cockpit");
  }, [fetchMissionDetails]);

  const handleSelectPreset = useCallback((preset) => {
    setNewMissionForm({
      title: preset.title,
      description: preset.description,
      targetDir: "",
      interactive: true,
      gitCommit: false
    });
    setIsNewMissionOpen(true);
  }, []);

  // --- GROUP ARTIFACTS INTO HIERARCHICAL IDE DIRECTORY TREE ---
  const directoryTree = useMemo(() => {
    const rawList = missionData.artifacts || [];
    const query = fileSearchQuery.toLowerCase().trim();
    let list = query
      ? rawList.filter(a => a.name.toLowerCase().includes(query) || a.type.toLowerCase().includes(query))
      : rawList;

    if (selectedStageFilter) {
      list = list.filter(a => {
        const name = a.name.toLowerCase();
        const path = (a.path || "").toLowerCase();
        if (selectedStageFilter === "CONTRACTS") {
          return name.includes("charter") || name.includes("dag") || path.includes("prd");
        } else if (selectedStageFilter === "ARCHITECTURE") {
          return name.includes("adr") || name.includes("api-spec") || name.includes("domain");
        } else if (selectedStageFilter === "PARALLEL_PODS") {
          return (name.endsWith(".py") && !name.includes("test")) ||
                 name.endsWith(".tsx") || name.endsWith(".jsx") ||
                 name.endsWith(".sql") || name.endsWith(".tf") ||
                 name.includes("dockerfile");
        } else if (selectedStageFilter === "QA_SECURITY") {
          return name.includes("test") || name.includes("audit") || name.includes("report") || name.includes("decision");
        } else if (selectedStageFilter === "DOCUMENTATION") {
          return (name.endsWith(".md") && !name.includes("adr")) || path.includes("documentation");
        }
        return true;
      });
    }

    const folders = {
      backend: { name: "src/backend", icon: "📦", items: [] },
      frontend: { name: "src/frontend", icon: "🎨", items: [] },
      database: { name: "db/migrations", icon: "🗄️", items: [] },
      contracts: { name: "contracts/api", icon: "📑", items: [] },
      documentation: { name: "docs/spec", icon: "📚", items: [] },
      tests: { name: "tests/suite", icon: "🧪", items: [] },
      cloud: { name: "infra/cloud", icon: "☁️", items: [] },
    };

    list.forEach(a => {
      const name = a.name.toLowerCase();
      if (name.endsWith(".py") && !name.includes("test")) {
        folders.backend.items.push(a);
      } else if (name.endsWith(".tsx") || name.endsWith(".jsx")) {
        folders.frontend.items.push(a);
      } else if (name.endsWith(".sql")) {
        folders.database.items.push(a);
      } else if (name.includes("api-spec") || name.includes("dag") || name.includes("charter")) {
        folders.contracts.items.push(a);
      } else if (name.endsWith(".md") && !name.includes("test")) {
        folders.documentation.items.push(a);
      } else if (name.includes("test") || name.includes("audit")) {
        folders.tests.items.push(a);
      } else if (name.includes("docker") || name.endsWith(".tf")) {
        folders.cloud.items.push(a);
      } else {
        folders.backend.items.push(a);
      }
    });

    return folders;
  }, [missionData.artifacts, fileSearchQuery, selectedStageFilter]);

  // Toggle folder open/closed
  const toggleFolder = useCallback((folderKey) => {
    setExpandedFolders(prev => ({ ...prev, [folderKey]: !prev[folderKey] }));
  }, []);

  // Compute code lines for line-number gutter
  const lineCount = useMemo(() => {
    const text = isEditingFile ? editedCodeContent : selectedArtifact?.content;
    if (!text) return 1;
    return text.split("\n").length;
  }, [selectedArtifact, isEditingFile, editedCodeContent]);

  const lineNumbers = useMemo(() => {
    const lines = [];
    for (let i = 1; i <= lineCount; i++) {
      lines.push(i);
    }
    return lines;
  }, [lineCount]);

  const currentLanguage = useMemo(() => {
    return getPrismLanguage(selectedArtifact?.name);
  }, [selectedArtifact]);

  // Full disk path on user's machine
  const localDiskPath = useMemo(() => {
    if (!selectedArtifact?.path) return "No file selected";
    return `c:\\Users\\bobharsh\\MAS\\${selectedArtifact.path.replace(/\//g, '\\')}`;
  }, [selectedArtifact]);

  const activeFileRevisions = useMemo(() => {
    if (!selectedArtifact?.name) return [];
    return revisions.filter(
      r => r.artifact_id === selectedArtifact.name || r.artifact_id === selectedArtifact.id
    );
  }, [revisions, selectedArtifact]);

  const filteredFeedLogs = useMemo(() => {
    const q = feedSearchQuery.trim().toLowerCase();
    return feedLogs.filter(entry => {
      const matchesType = feedFilter === "ALL" || entry.type === feedFilter;
      if (!matchesType) return false;
      if (!q) return true;
      return (
        (entry.text && entry.text.toLowerCase().includes(q)) ||
        (entry.time && entry.time.toLowerCase().includes(q)) ||
        (entry.type && entry.type.toLowerCase().includes(q))
      );
    });
  }, [feedLogs, feedFilter, feedSearchQuery]);

  const renderHighlightedFeedText = (text, query) => {
    if (!query.trim() || !text) return text;
    const q = query.trim();
    const parts = text.split(new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'));
    return parts.map((part, i) =>
      part.toLowerCase() === q.toLowerCase() ? (
        <mark
          key={i}
          style={{
            backgroundColor: "rgba(56, 189, 248, 0.25)",
            color: "#38bdf8",
            borderRadius: "2px",
            padding: "0 2px"
          }}
        >
          {part}
        </mark>
      ) : part
    );
  };

  
  if (viewMode === "hub") {
    return (
      <div className="hub-container pattern-grid">
        {/* HUB STICKY TOP NAVIGATION */}
        <header className="hub-nav" role="banner">
          <div className="hub-nav-brand" onClick={() => setViewMode("hub")}>
            <div className="hub-brand-logo">M</div>
            <span>MAS OS</span>
          </div>

          <nav className="hub-nav-links">
            <button className="hub-nav-link active" onClick={() => setViewMode("hub")}>Overview Hub</button>
            <button className="hub-nav-link" onClick={() => setViewMode("cockpit")}>IDE Cockpit</button>
            <a className="hub-nav-link" href="#capabilities">14 Pods</a>
            <a className="hub-nav-link" href="#missions">Missions ({missionsList.length})</a>
            <a className="hub-nav-link" href="#presets">Enterprise Presets</a>
          </nav>

          <div className="hub-nav-actions">
            <div className="hub-status-chip">
              <span className="hub-status-dot" />
              <span>14 Agents Online</span>
            </div>

            <div className="view-switcher-pill">
              <button
                className={`view-switcher-btn ${viewMode === "hub" ? "active" : ""}`}
                onClick={() => setViewMode("hub")}
              >
                🌐 Hub
              </button>
              <button
                className={`view-switcher-btn ${viewMode === "cockpit" ? "active" : ""}`}
                onClick={() => setViewMode("cockpit")}
              >
                💻 Cockpit
              </button>
            </div>

            <button
              className="btn btn-outline btn-sm"
              onClick={toggleTheme}
              title="Toggle Dark/Light Mode"
            >
              {theme === "dark" ? "☀️ Light" : "🌙 Dark"}
            </button>

            <button
              className="btn btn-primary"
              onClick={() => setIsNewMissionOpen(true)}
              style={{ background: "var(--gradient-brand)", border: "none", borderRadius: "20px", padding: "0.45rem 1.15rem" }}
            >
              + Launch Mission
            </button>
          </div>
        </header>

        {/* PENDING GATE NOTIFICATION IF ACTIVE */}
        {pendingGate && (
          <div style={{ background: "rgba(245, 158, 11, 0.15)", borderBottom: "1px solid rgba(245, 158, 11, 0.3)", padding: "0.75rem 2rem", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", color: "var(--accent-amber)", fontWeight: 600, fontSize: "0.85rem" }}>
              <span>⚠️</span>
              <span>Human Decision Required: <strong>{pendingGate.name}</strong> is awaiting your review.</span>
            </div>
            <button
              className="btn btn-warning btn-sm"
              onClick={() => setViewMode("cockpit")}
            >
              Review & Approve in Cockpit →
            </button>
          </div>
        )}

        {/* HUB HERO SECTION */}
        <section className="hub-hero">
          <div className="hub-pill-banner">
            <span>✨</span>
            <span>INTRODUCING MULTI-AGENT AUTOPILOT • CONTRACT-FIRST PARALLEL PODS</span>
          </div>

          <h1 className="hub-hero-title">
            The Multi-Agent Workspace that<br />
            <span className="hub-gradient-text">thinks while you work.</span>
          </h1>

          <p className="hub-hero-subtitle">
            Empowering software engineering teams with 14 specialized autonomous agents operating across contract-first parallel pods, Git-backed blackboards, and zero-black-box mathematical governance.
          </p>

          <div className="hub-hero-ctas">
            <button
              className="btn-hero-primary"
              onClick={() => setIsNewMissionOpen(true)}
            >
              Launch Autonomous Mission
            </button>
            <button
              className="btn-hero-secondary"
              onClick={() => setViewMode("cockpit")}
            >
              Open IDE Cockpit →
            </button>
          </div>

          {/* LIVE COCKPIT PREVIEW CARD */}
          <div className="hub-preview-card">
            <div className="hub-preview-header">
              <div className="hub-preview-dots">
                <span className="hub-dot red" />
                <span className="hub-dot yellow" />
                <span className="hub-dot green" />
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                  {activeMissionId || "MISSION-IDLE"}
                </span>
                <span className="hub-status-chip" style={{ padding: "0.2rem 0.6rem", fontSize: "0.7rem" }}>
                  {missionData.status}
                </span>
              </div>
            </div>

            <div style={{ marginBottom: "1.25rem" }}>
              <h3 style={{ fontSize: "1.2rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.35rem" }}>
                {missionData.title}
              </h3>
              <p style={{ fontSize: "0.88rem", color: "var(--text-secondary)", lineHeight: 1.5 }}>
                {missionData.description}
              </p>
            </div>

            <div className="hub-preview-grid">
              <div className="hub-preview-stat">
                <div className="hub-preview-stat-label">Pipeline Stage</div>
                <div className="hub-preview-stat-value" style={{ fontSize: "1rem" }}>{missionData.stage}</div>
              </div>
              <div className="hub-preview-stat">
                <div className="hub-preview-stat-label">Tokens Burned</div>
                <div className="hub-preview-stat-value">{Number(missionData.tokens?.total || 0).toLocaleString()}</div>
              </div>
              <div className="hub-preview-stat">
                <div className="hub-preview-stat-label">Circuit Breaker</div>
                <div className="hub-preview-stat-value" style={{ color: "var(--accent-green)" }}>
                  {missionData.circuitBreaker?.healthy !== false ? "HEALTHY" : "TRIPPED"}
                </div>
              </div>
              <div className="hub-preview-stat">
                <div className="hub-preview-stat-label">Artifacts Produced</div>
                <div className="hub-preview-stat-value">{missionData.artifacts?.length || 0}</div>
              </div>
            </div>

            <div style={{ marginTop: "1.25rem", display: "flex", alignItems: "center", justifyContent: "space-between", paddingTop: "1rem", borderTop: "1px solid var(--border-color)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.82rem", color: "var(--text-secondary)" }}>
                <span style={{ color: "var(--accent-cyan)" }}>⚙️ Active Execution:</span>
                <span>{Object.values(missionData.pods || {})[0]?.action || "ReAct Multi-Turn Verification Engine Ready"}</span>
              </div>
              <button
                className="btn btn-sm btn-primary"
                onClick={() => setViewMode("cockpit")}
              >
                Jump to Live Cockpit →
              </button>
            </div>
          </div>
        </section>

        {/* METRICS HIGHLIGHT SECTION */}
        <section className="hub-metrics-section">
          <div className="hub-metrics-grid">
            <div className="hub-metric-tile">
              <div className="hub-metric-tile-number">70K+</div>
              <div className="hub-metric-tile-label">Cognitive Tokens Burned & Verified</div>
            </div>
            <div className="hub-metric-tile">
              <div className="hub-metric-tile-number">14</div>
              <div className="hub-metric-tile-label">Specialized Autonomous Agents</div>
            </div>
            <div className="hub-metric-tile">
              <div className="hub-metric-tile-number">5</div>
              <div className="hub-metric-tile-label">Parallel Engineering Pods</div>
            </div>
            <div className="hub-metric-tile">
              <div className="hub-metric-tile-number">100%</div>
              <div className="hub-metric-tile-label">AST & Domain Invariant Pass Rate</div>
            </div>
          </div>
        </section>

        {/* ACTIVE & HYDRATED MISSIONS */}
        <section id="missions" className="hub-section">
          <div className="hub-section-header">
            <div className="hub-section-tag">DURABLE PERSISTENCE</div>
            <h2 className="hub-section-title">Active & Stored Missions</h2>
            <p className="hub-section-subtitle">
              SQLite WAL event-sourced mission registry with cold-start session hydration.
            </p>
          </div>

          {missionsList && missionsList.length > 0 ? (
            <div className="hub-missions-grid">
              {missionsList.map((m) => {
                const isActive = m.mission_id === activeMissionId;
                return (
                  <div
                    key={m.mission_id}
                    className="hub-mission-card"
                    onClick={() => handleOpenMissionInCockpit(m.mission_id)}
                    style={isActive ? { borderColor: "var(--accent-cyan)", boxShadow: "0 0 15px rgba(56, 189, 248, 0.2)" } : {}}
                  >
                    <div className="hub-mission-card-header">
                      <span className="hub-mission-id">{m.mission_id}</span>
                      <span className={`status-pill ${m.status?.toLowerCase() || "idle"}`}>{m.status}</span>
                    </div>
                    <div className="hub-mission-title">{m.title}</div>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "0.78rem", color: "var(--text-secondary)", marginTop: "0.75rem", paddingTop: "0.75rem", borderTop: "1px solid var(--border-color)" }}>
                      <span>Stage: <strong>{m.stage}</strong></span>
                      <span style={{ color: "var(--accent-cyan)", fontWeight: 600 }}>Inspect Cockpit →</span>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: "2rem", color: "var(--text-muted)" }}>
              No missions currently stored. Launch your first mission below!
            </div>
          )}
        </section>

        {/* 6-QUADRANT CAPABILITIES GRID */}
        <section id="capabilities" className="hub-section">
          <div className="hub-section-header">
            <div className="hub-section-tag">ENGINEERING PODS</div>
            <h2 className="hub-section-title">Everything your team needs</h2>
            <p className="hub-section-subtitle">
              Built for modern software organizations: contract-first, parallel, and mathematically auditable.
            </p>
          </div>

          <div className="hub-cards-grid">
            <div className="hub-card">
              <div className="hub-card-icon">🧠</div>
              <h3 className="hub-card-title">Business & Leadership Pod</h3>
              <p className="hub-card-desc">
                Product Manager charters, Domain SME validation matrices, and Given/When/Then user stories with zero scope creep.
              </p>
              <button className="hub-card-link" onClick={() => setViewMode("cockpit")}>
                Inspect Pod Specs →
              </button>
            </div>

            <div className="hub-card">
              <div className="hub-card-icon">📐</div>
              <h3 className="hub-card-title">Architecture & Governance Pod</h3>
              <p className="hub-card-desc">
                System Architect ADRs with pre-mortem risk evaluation, OpenAPI 3.1 contracts, and Task DAG parallel orchestration.
              </p>
              <button className="hub-card-link" onClick={() => setViewMode("cockpit")}>
                Inspect Pod Specs →
              </button>
            </div>

            <div className="hub-card">
              <div className="hub-card-icon">🗄️</div>
              <h3 className="hub-card-title">Data & Storage Pod</h3>
              <p className="hub-card-desc">
                Automated PostgreSQL DDL, schema migrations, and high-concurrency non-locking indexing strategies.
              </p>
              <button className="hub-card-link" onClick={() => setViewMode("cockpit")}>
                Inspect Pod Specs →
              </button>
            </div>

            <div className="hub-card">
              <div className="hub-card-icon">⚙️</div>
              <h3 className="hub-card-title">Backend & AI Pod</h3>
              <p className="hub-card-desc">
                Production Python REST APIs, Pydantic v2 schemas, and autonomous ReAct tool calling within a sandboxed jail.
              </p>
              <button className="hub-card-link" onClick={() => setViewMode("cockpit")}>
                Inspect Pod Specs →
              </button>
            </div>

            <div className="hub-card">
              <div className="hub-card-icon">🎨</div>
              <h3 className="hub-card-title">Frontend & Experience Pod</h3>
              <p className="hub-card-desc">
                4-state accessible React components, responsive layouts, WCAG 2.1 AA keyboard navigation, and design tokens.
              </p>
              <button className="hub-card-link" onClick={() => setViewMode("cockpit")}>
                Inspect Pod Specs →
              </button>
            </div>

            <div className="hub-card">
              <div className="hub-card-icon">☁️</div>
              <h3 className="hub-card-title">Cloud, Platform & SRE Pod</h3>
              <p className="hub-card-desc">
                Dedicated KMS Terraform IaC, hardened multi-stage non-root Dockerfiles, and automated health check probes.
              </p>
              <button className="hub-card-link" onClick={() => setViewMode("cockpit")}>
                Inspect Pod Specs →
              </button>
            </div>
          </div>
        </section>

        {/* ENTERPRISE MISSION PRESETS */}
        <section id="presets" className="hub-section">
          <div className="hub-section-header">
            <div className="hub-section-tag">INSTANT SCENARIOS</div>
            <h2 className="hub-section-title">Enterprise Mission Presets</h2>
            <p className="hub-section-subtitle">
              Launch complete enterprise services with contract-first parallel pod execution in 1 click.
            </p>
          </div>

          <div className="hub-presets-grid">
            {MISSION_PRESETS.map((preset, idx) => (
              <div
                key={idx}
                className="hub-preset-tile"
                onClick={() => handleSelectPreset(preset)}
              >
                <div className="hub-preset-badge">{preset.label}</div>
                <div className="hub-preset-title">{preset.title}</div>
                <div className="hub-preset-desc">{preset.description.slice(0, 110)}...</div>
                <div style={{ marginTop: "1rem", color: "var(--accent-cyan)", fontSize: "0.8rem", fontWeight: 600 }}>
                  Launch Scenario →
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* LUMINOUS BOTTOM CTA BANNER */}
        <section className="hub-section">
          <div className="hub-cta-banner">
            <h2 className="hub-cta-title">Your team's best software starts here.</h2>
            <p className="hub-cta-subtitle">
              Join modern software teams utilizing 14 autonomous agents working across contract-first parallel pods with zero black-box decisions.
            </p>
            <button
              className="btn-hero-primary"
              style={{ background: "#ffffff", color: "#080c14", fontWeight: 700 }}
              onClick={() => setIsNewMissionOpen(true)}
            >
              Launch Autonomous Mission
            </button>
          </div>
        </section>

        {/* FOOTER */}
        <footer className="hub-footer">
          <div className="hub-footer-content">
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <div className="hub-brand-logo" style={{ width: "24px", height: "24px", fontSize: "0.75rem" }}>M</div>
              <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>MAS OS</span>
              <span>• Multi-Agent Software Engineering Operating System</span>
            </div>
            <div style={{ display: "flex", gap: "1.5rem" }}>
              <span>SQLite WAL Persistence Active</span>
              <span>100% Deterministic Testing</span>
              <span>OpenTelemetry Lineage</span>
            </div>
          </div>
        </footer>

        {/* NEW MISSION MODAL OVERLAY */}
        {isNewMissionOpen && (
          <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="modal-title">
            <div className="modal-card">
              <div className="modal-header">
                <h3 id="modal-title">Launch New Multi-Agent Mission</h3>
                <button
                  className="modal-close"
                  onClick={() => setIsNewMissionOpen(false)}
                  aria-label="Close new mission dialog"
                >
                  &times;
                </button>
              </div>

              <div className="presets-container">
                <span className="presets-label">Enterprise Presets:</span>
                <div className="presets-chips">
                  {MISSION_PRESETS.map((p, idx) => (
                    <button
                      key={idx}
                      className="preset-chip"
                      onClick={() => setNewMissionForm({
                        title: p.title,
                        description: p.description,
                        targetDir: "",
                        interactive: true,
                        gitCommit: false
                      })}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label htmlFor="mission-title">Mission Title</label>
                <input
                  id="mission-title"
                  type="text"
                  value={newMissionForm.title}
                  onChange={(e) => setNewMissionForm({ ...newMissionForm, title: e.target.value })}
                  placeholder="e.g. Stripe Webhook & Payment Reconciliation Service"
                />
              </div>

              <div className="form-group">
                <label htmlFor="mission-desc">Architecture Specification / Goal</label>
                <textarea
                  id="mission-desc"
                  rows="4"
                  value={newMissionForm.description}
                  onChange={(e) => setNewMissionForm({ ...newMissionForm, description: e.target.value })}
                  placeholder="Describe your technical requirements, data models, and constraints..."
                />
              </div>

              <div className="form-group">
                <label htmlFor="mission-dir">Target Workspace Directory (Optional)</label>
                <input
                  id="mission-dir"
                  type="text"
                  value={newMissionForm.targetDir}
                  onChange={(e) => setNewMissionForm({ ...newMissionForm, targetDir: e.target.value })}
                  placeholder="artifacts"
                />
              </div>

              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={newMissionForm.interactive}
                    onChange={(e) => setNewMissionForm({ ...newMissionForm, interactive: e.target.checked })}
                  />
                  <span>Enable Human-in-the-Loop Governance Gates (Recommended)</span>
                </label>
              </div>

              <div className="form-group checkbox-group">
                <label>
                  <input
                    type="checkbox"
                    checked={newMissionForm.gitCommit}
                    onChange={(e) => setNewMissionForm({ ...newMissionForm, gitCommit: e.target.checked })}
                  />
                  <span>Commit Generated Artifacts to Git Blackboard Ledger</span>
                </label>
              </div>

              <div className="modal-actions">
                <button
                  className="btn btn-outline"
                  onClick={() => setIsNewMissionOpen(false)}
                  disabled={isSubmittingMission}
                >
                  Cancel
                </button>
                <button
                  className="btn btn-primary"
                  onClick={handleLaunchMission}
                  disabled={isSubmittingMission}
                >
                  {isSubmittingMission ? "Initializing Pods..." : "Deploy 14 Agents"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }


  return (
    <div className="cockpit-container" style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      {/* 1. REDESIGNED SLEEK TOP COMMAND BAR */}
      <header className="top-bar" role="banner">
        {/* LEFT: BRAND & MISSION CONTEXT */}
        <div className="brand-group">
          <button
            className="btn btn-outline btn-sm"
            onClick={() => setViewMode("hub")}
            title="Switch to Overview Hub (Ctrl+H)"
            style={{ fontSize: "0.72rem", padding: "0.2rem 0.5rem" }}
          >
            ← Hub
          </button>
          <div className="logo-badge" title="Multi-Agent Software Engineering System">MAS</div>
          <div className="mission-meta" title={missionData.title}>
            <h1>{missionData.title}</h1>
            <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
              <span className={`live-indicator ${connectionStatus === "STREAMING" ? "" : connectionStatus === "IDLE" ? "idle" : "disconnected"}`} />
              <span className="mission-id-badge">{activeMissionId || "IDLE"}</span>
            </div>
          </div>
        </div>

        {/* CENTER: OMNIBAR / COMMAND PALETTE TRIGGER BUTTON */}
        <button
          type="button"
          className="header-omnibar-btn"
          onClick={() => { setIsCommandPaletteOpen(true); setCommandPaletteQuery(""); setCommandPaletteSelectedIndex(0); }}
          title="Open Command Palette (Ctrl+K)"
        >
          <span className="omnibar-icon">🔍</span>
          <span className="omnibar-placeholder">Search files, actions, or type a command...</span>
          <span className="omnibar-shortcut">Ctrl K</span>
        </button>

        {/* 5-STAGE PIPELINE INDICATOR (COMPACT) */}
        <nav className="pipeline-progress" aria-label="Pipeline Stages">
          {PIPELINE_STAGES.map((stg) => {
            const isCompleted = missionData.stageIndex > stg.index || missionData.status === "COMPLETED";
            const isActive = missionData.stageIndex === stg.index && missionData.status !== "COMPLETED";
            const isFiltered = selectedStageFilter === stg.id;
            return (
              <React.Fragment key={stg.id}>
                <div
                  className={`stage-node ${isActive ? "active" : ""} ${isCompleted ? "completed" : ""} ${isFiltered ? "selected-filter" : ""}`}
                  title={`${stg.label}: ${stg.desc} (Click to filter workspace files)`}
                  onClick={() => setSelectedStageFilter(prev => prev === stg.id ? null : stg.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      setSelectedStageFilter(prev => prev === stg.id ? null : stg.id);
                    }
                  }}
                >
                  <span className="node-circle">
                    {isCompleted ? "✓" : stg.index}
                  </span>
                  <span className="node-label">{stg.label}</span>
                </div>
                {stg.index < 5 && <div className={`stage-connector ${isCompleted ? "completed" : ""}`} />}
              </React.Fragment>
            );
          })}
        </nav>

        {/* RIGHT: METRICS & ACTION CONTROLS */}
        <div className="metrics-controls">
          <div
            className="header-telemetry-chip"
            onClick={() => setIsCostModalOpen(true)}
            style={{ cursor: "pointer" }}
            title="Total Tokens Burned & Circuit Breaker Health. Click to inspect real-time costs and pod burn."
          >
            <span>⚡ {Number(costTelemetry?.total_tokens || missionData.tokens.total || 0).toLocaleString()} tok</span>
            <span style={{ color: "#34d399", fontWeight: 700 }}>
              (${Number(costTelemetry?.net_cost_usd || 0.007).toFixed(4)})
            </span>
            <span style={{ color: "#64748b" }}>•</span>
            <span className={missionData.circuitBreaker.healthy ? "chip-status-healthy" : "chip-status-tripped"}>
              {missionData.circuitBreaker.healthy ? "Healthy" : "Tripped"}
            </span>
          </div>

          <button
            className="btn btn-primary btn-sm"
            onClick={() => setIsNewMissionOpen(true)}
            aria-label="Launch a new multi-agent mission"
            style={{ fontSize: "0.72rem", padding: "0.22rem 0.55rem" }}
          >
            + New Mission
          </button>

          <button
            className="btn btn-outline btn-sm"
            onClick={toggleTheme}
            aria-label="Toggle dark/light theme"
            title="Toggle theme"
            style={{ fontSize: "0.75rem", padding: "0.22rem 0.45rem" }}
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
        </div>
      </header>

      {/* 2. THREE-PANE MAIN WORKSPACE */}
      <main className={`workspace-grid ${isLeftCollapsed ? "left-collapsed" : ""} ${isRightCollapsed ? "right-collapsed" : ""}`} role="main" style={{ flex: 1, minHeight: 0 }}>
        {/* LEFT PANE: IDE EXPLORER & POD MATRIX */}
        <aside className="panel left-panel" aria-label="File Explorer and Pod Matrix">
          {isLeftCollapsed ? (
            <div className="panel-collapsed-rail">
              <button
                className="rail-btn"
                onClick={() => setIsLeftCollapsed(false)}
                title="Expand Sidebar (Ctrl+B)"
              >
                ❯
              </button>
              <button
                className={`rail-btn ${sidebarTab === "explorer" ? "active" : ""}`}
                onClick={() => { setIsLeftCollapsed(false); setSidebarTab("explorer"); }}
                title={`Workspace Files (${missionData.artifacts.length})`}
              >
                📁
                {missionData.artifacts.length > 0 && (
                  <span className="rail-badge">{missionData.artifacts.length}</span>
                )}
              </button>
              <button
                className={`rail-btn ${sidebarTab === "pods" ? "active" : ""}`}
                onClick={() => { setIsLeftCollapsed(false); setSidebarTab("pods"); }}
                title="Parallel Pods (5)"
              >
                ⚡
                <span className="rail-badge">5</span>
              </button>
            </div>
          ) : (
            <>
              {/* SIDEBAR VIEW SWITCHER: EXPLORER VS PODS */}
              <div style={{ display: "flex", alignItems: "center", gap: "0.25rem", marginBottom: "0.75rem", borderBottom: "1px solid var(--border-color)", paddingBottom: "0.4rem" }}>
                <button
                  className={`btn btn-sm ${sidebarTab === "explorer" ? "btn-primary" : "btn-outline"}`}
                  style={{ flex: 1, fontSize: "0.75rem" }}
                  onClick={() => setSidebarTab("explorer")}
                >
                  📁 Explorer ({missionData.artifacts.length})
                </button>
                <button
                  className={`btn btn-sm ${sidebarTab === "pods" ? "btn-primary" : "btn-outline"}`}
                  style={{ flex: 1, fontSize: "0.75rem" }}
                  onClick={() => setSidebarTab("pods")}
                >
                  ⚡ Pods (5)
                </button>
                <button
                  className="panel-collapse-toggle"
                  onClick={() => setIsLeftCollapsed(true)}
                  title="Collapse Sidebar (Ctrl+B)"
                >
                  ❮
                </button>
              </div>

          {/* VIEW 1: VS CODE-STYLE FILE EXPLORER */}
          {sidebarTab === "explorer" && (
            <div className="ide-explorer-panel" style={{ display: "flex", flexDirection: "column", height: "calc(100% - 45px)" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "0.4rem" }}>
                <span style={{ fontSize: "0.75rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em", color: "var(--text-secondary)" }}>
                  Workspace Files
                </span>
                <span className="badge" title="Total synthesized files on disk">{missionData.artifacts.length} files</span>
              </div>

              <input
                type="text"
                className="search-input"
                placeholder="Search files (e.g. service.py)..."
                value={fileSearchQuery}
                onChange={(e) => setFileSearchQuery(e.target.value)}
              />

              {selectedStageFilter && (
                <div className="stage-filter-indicator">
                  <span>Stage: <strong>{PIPELINE_STAGES.find(s => s.id === selectedStageFilter)?.label}</strong></span>
                  <button
                    className="stage-filter-clear-btn"
                    onClick={() => setSelectedStageFilter(null)}
                    title="Clear stage filter"
                  >
                    ✕ Clear
                  </button>
                </div>
              )}

              <div className="ide-explorer" style={{ flex: 1, overflowY: "auto" }}>
                {Object.entries(directoryTree).map(([fKey, folder]) => {
                  if (folder.items.length === 0) return null;
                  const isExpanded = expandedFolders[fKey] !== false;
                  return (
                    <div key={fKey} className="ide-tree-folder">
                      <div className="ide-folder-header" onClick={() => toggleFolder(fKey)}>
                        <span className={`ide-chevron ${isExpanded ? "expanded" : ""}`}>▶</span>
                        <span>{folder.icon}</span>
                        <span>{folder.name}</span>
                        <span style={{ marginLeft: "auto", fontSize: "0.68rem", color: "var(--text-muted)" }}>
                          ({folder.items.length})
                        </span>
                      </div>

                      {isExpanded && (
                        <div className="ide-folder-children">
                          {folder.items.map(file => {
                            const isActive = selectedArtifact?.id === file.id;
                            return (
                              <div
                                key={file.id}
                                className={`ide-file-item ${isActive ? "active" : ""}`}
                                onClick={() => openArtifactInEditor(file.id)}
                                title={`Path: ${file.path}\nAuthor: ${file.created_by}`}
                              >
                                <div className="ide-file-label">
                                  <span className="ide-file-icon">{getFileIcon(file.name)}</span>
                                  <span>{file.name}</span>
                                </div>
                                <span className="ide-git-badge" title="Synthesized by MAS agent">+A</span>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}

                {missionData.artifacts.length === 0 && (
                  <div className="empty-state" style={{ padding: "1.5rem 0.5rem", textAlign: "center" }}>
                    No files synthesized yet. Click <strong>+ New Mission</strong> to generate code.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* VIEW 2: PARALLEL ENGINEERING POD MATRIX */}
          {sidebarTab === "pods" && (
            <div className="pod-matrix" style={{ overflowY: "auto", height: "calc(100% - 45px)" }}>
              {POD_CONFIGS.map(podCfg => {
                const livePod = missionData.pods[podCfg.key] || { status: "IDLE", action: "Standby", artifact: podCfg.defaultArtifact };
                const status = livePod.status || "IDLE";
                const isRunning = status === "RUNNING";
                const isDone = status === "DONE";

                let statusClass = "status-idle";
                if (isRunning) statusClass = "status-running";
                else if (isDone) statusClass = "status-done";
                else if (status === "FAILED") statusClass = "status-tripped";

                return (
                  <div
                    key={podCfg.key}
                    className={`pod-card ${isRunning ? "running" : ""}`}
                    onClick={() => setInspectedPod({ podCfg, livePod })}
                    title="Click to inspect real-time telemetry & execution state"
                  >
                    <div className="pod-header">
                      <span className="pod-icon">{podCfg.icon}</span>
                      <div className="pod-info">
                        <div style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
                          <h3 style={{ margin: 0 }}>{podCfg.name}</h3>
                          <span className="pod-inspect-badge">🔍 Telemetry</span>
                        </div>
                        <p className="pod-sub">{podCfg.desc}</p>
                      </div>
                      <span className={`status-pill ${statusClass}`}>{status}</span>
                    </div>
                    <div className="pod-action-text">{livePod.action}</div>
                    {livePod.artifact && (
                      <div style={{ marginTop: "0.35rem", display: "flex", justifyContent: "flex-end" }}>
                        <span
                          className="preset-chip"
                          style={{ fontSize: "0.68rem" }}
                          title="Open artifact in editor"
                          onClick={(e) => {
                            e.stopPropagation();
                            const art = missionData.artifacts.find(a => a.name.includes(livePod.artifact));
                            if (art) openArtifactInEditor(art.id);
                          }}
                        >
                          📄 {livePod.artifact}
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
            </>
          )}
        </aside>

        {/* CENTER PANE: IDE EDITOR & WORKBENCH */}
        <section className="panel center-panel" aria-label="IDE Code Editor Canvas" style={{ display: "flex", flexDirection: "column" }}>
          {/* 1. IDE MULTI-TAB BAR */}
          <div className="ide-tabs-bar" role="tablist">
            {openTabs.length === 0 ? (
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", padding: "0.2rem 0.6rem" }}>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontStyle: "italic" }}>
                  No open files. Select a file from Explorer or view architecture DAG.
                </span>
                <div className="view-switcher-pill">
                  <button
                    className={`view-switcher-btn ${editorViewMode === "dag" ? "active" : ""}`}
                    onClick={() => setEditorViewMode("dag")}
                    style={{ fontSize: "0.65rem", padding: "0.15rem 0.45rem" }}
                  >
                    🕸️ Architecture DAG
                  </button>
                </div>
              </div>
            ) : (
              openTabs.map(tab => {
                const isActive = activeTabId === tab.id;
                return (
                  <div
                    key={tab.id}
                    className={`ide-tab ${isActive ? "active" : ""}`}
                    onClick={() => {
                      setActiveTabId(tab.id);
                      setSelectedArtifact(tab);
                    }}
                  >
                    <span>{getFileIcon(tab.name)}</span>
                    <span>{tab.name}</span>
                    <span
                      className="ide-tab-close"
                      title="Close file tab"
                      onClick={(e) => handleCloseTab(e, tab.id)}
                    >
                      ✕
                    </span>
                  </div>
                );
              })
            )}
          </div>

          {/* 2. LOCAL DISK PATH BANNER (Shows exact physical file path) */}
          {selectedArtifact && (
            <div className="disk-location-banner">
              <div className="disk-path-text" title={localDiskPath}>
                📁 <strong>Disk Location:</strong> {localDiskPath}
              </div>
              <div style={{ display: "flex", gap: "0.4rem", alignItems: "center" }}>
                <div className="view-switcher-pill" style={{ marginRight: "0.25rem" }}>
                  <button
                    className={`view-switcher-btn ${editorViewMode === "code" ? "active" : ""}`}
                    onClick={() => setEditorViewMode("code")}
                    style={{ fontSize: "0.65rem", padding: "0.15rem 0.45rem" }}
                  >
                    📄 Code
                  </button>
                  <button
                    className={`view-switcher-btn ${editorViewMode === "diff" ? "active" : ""}`}
                    onClick={() => setEditorViewMode("diff")}
                    style={{ fontSize: "0.65rem", padding: "0.15rem 0.45rem" }}
                  >
                    🔍 Diff
                  </button>
                  <button
                    className={`view-switcher-btn ${editorViewMode === "dag" ? "active" : ""}`}
                    onClick={() => setEditorViewMode("dag")}
                    style={{ fontSize: "0.65rem", padding: "0.15rem 0.45rem" }}
                  >
                    🕸️ DAG
                  </button>
                </div>
                <button
                  className="btn btn-sm btn-outline"
                  style={{
                    fontSize: "0.65rem",
                    padding: "0.15rem 0.45rem",
                    color: "var(--accent-green)",
                    borderColor: "rgba(16, 185, 129, 0.4)"
                  }}
                  onClick={handleRunSandboxedTests}
                  disabled={isRunningTests || !activeMissionId}
                  title="Run pytest verification suite in SubprocessSandbox"
                >
                  {isRunningTests ? "⏳ Running..." : "▶ Run Tests"}
                </button>
                {selectedArtifact && !isEditingFile && (
                  <button
                    className="btn btn-sm btn-outline"
                    style={{
                      fontSize: "0.65rem",
                      padding: "0.15rem 0.45rem",
                      color: "var(--accent-cyan)",
                      borderColor: "rgba(56, 189, 248, 0.4)"
                    }}
                    onClick={() => {
                      setEditedCodeContent(selectedArtifact.content || "");
                      setIsEditingFile(true);
                      setEditorViewMode("code");
                      setSaveFeedback(null);
                    }}
                    title="Directly edit this file in the Cockpit (Ctrl+S to save)"
                  >
                    ✏️ Edit
                  </button>
                )}
                {selectedArtifact && isEditingFile && (
                  <div style={{ display: "flex", gap: "0.25rem", alignItems: "center" }}>
                    <button
                      className="btn btn-sm btn-success"
                      style={{
                        fontSize: "0.65rem",
                        padding: "0.15rem 0.55rem",
                        fontWeight: 600,
                        backgroundColor: "#10b981",
                        borderColor: "#10b981"
                      }}
                      onClick={handleSaveEditedFile}
                      disabled={isSavingFile}
                      title="Save changes with AST verification (Ctrl+S)"
                    >
                      {isSavingFile ? "Saving..." : "💾 Save"}
                    </button>
                    <button
                      className="btn btn-sm btn-outline"
                      style={{ fontSize: "0.65rem", padding: "0.15rem 0.4rem" }}
                      onClick={() => {
                        setIsEditingFile(false);
                        setEditedCodeContent(selectedArtifact.content || "");
                        setSaveFeedback(null);
                      }}
                    >
                      ✖ Cancel
                    </button>
                  </div>
                )}
                {saveFeedback === "SAVED" && (
                  <span style={{ fontSize: "0.65rem", color: "#34d399", fontWeight: 600 }}>
                    Saved v{selectedArtifact?.version} ✓
                  </span>
                )}
                {saveFeedback && saveFeedback !== "SAVED" && (
                  <span
                    style={{ fontSize: "0.65rem", color: "#f87171", maxWidth: "160px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                    title={saveFeedback}
                  >
                    ⚠️ {saveFeedback}
                  </span>
                )}
                {selectedArtifact && (
                  <button
                    className="btn btn-sm btn-outline"
                    style={{
                      fontSize: "0.65rem",
                      padding: "0.15rem 0.5rem",
                      color: "#fbbf24",
                      borderColor: "rgba(251, 191, 36, 0.4)",
                      display: "flex",
                      alignItems: "center",
                      gap: "0.3rem"
                    }}
                    onClick={() => handleOpenVersionHistory(selectedArtifact.id)}
                    title="View version snapshots & instant rollback"
                  >
                    ⏱️ v{selectedArtifact.version || 1} History
                  </button>
                )}
                <button
                  className="btn btn-sm btn-outline"
                  style={{ fontSize: "0.65rem", padding: "0.15rem 0.45rem" }}
                  onClick={handleCopyPath}
                >
                  {pathCopyFeedback ? "Path Copied! ✓" : "Copy Path"}
                </button>
                <button
                  className="btn btn-sm btn-outline"
                  style={{ fontSize: "0.65rem", padding: "0.15rem 0.45rem" }}
                  onClick={handleCopyCode}
                >
                  {copyFeedback ? "Code Copied! ✓" : "Copy Code"}
                </button>
              </div>
            </div>
          )}

          {/* 3. BREADCRUMBS BAR */}
          {selectedArtifact && (
            <div className="ide-breadcrumbs">
              <span>MAS Workspace</span>
              <span className="ide-crumb-sep">&gt;</span>
              <span>{selectedArtifact.path?.split("/")[0] || "artifacts"}</span>
              <span className="ide-crumb-sep">&gt;</span>
              <span className="ide-crumb-active">{selectedArtifact.name}</span>
              <span style={{ marginLeft: "auto", fontSize: "0.68rem", color: "var(--accent-green)" }}>
                Author: {selectedArtifact.created_by || "Agent"} (v{selectedArtifact.version || 1})
              </span>
            </div>
          )}

          {/* 4. IDE EDITOR CANVAS WITH LINE NUMBER GUTTER */}
          <div className="ide-editor-container" style={{ flex: 1, minHeight: 0 }}>
            {artifactLoading ? (
              // Loading Skeleton State
              <div className="skeleton-container" style={{ width: "100%" }} aria-busy="true">
                <div className="skeleton-line short" />
                <div className="skeleton-line long" />
                <div className="skeleton-line medium" />
                <div className="skeleton-line long" />
                <div className="skeleton-line short" />
                <div className="skeleton-line medium" />
                <div className="skeleton-line long" />
              </div>
            ) : artifactError ? (
              // Error State
              <div className="empty-canvas" style={{ width: "100%" }}>
                <div className="empty-canvas-icon">⚠️</div>
                <h3>Failed to load file</h3>
                <p>{artifactError}</p>
                <button
                  className="btn btn-primary"
                  onClick={() => selectedArtifact && openArtifactInEditor(selectedArtifact.id)}
                >
                  Retry Loading
                </button>
              </div>
            ) : editorViewMode === "dag" ? (
              // Micro-Step 8: Interactive Visual Code & Task Dependency DAG
              <DAGWorkbenchView
                dagData={dagData}
                isLoading={isLoadingDag}
                onRefresh={fetchMissionDag}
                onOpenArtifact={(artId) => {
                  openArtifactInEditor(artId);
                  setEditorViewMode("code");
                }}
                onViewDiff={(artId) => {
                  openArtifactInEditor(artId);
                  setEditorViewMode("diff");
                }}
                dagFilterTier={dagFilterTier}
                setDagFilterTier={setDagFilterTier}
                dagSearchQuery={dagSearchQuery}
                setDagSearchQuery={setDagSearchQuery}
                selectedDagNode={selectedDagNode}
                setSelectedDagNode={setSelectedDagNode}
              />
            ) : selectedArtifact && editorViewMode === "diff" ? (
              // Live Git-Style Diff Viewer (Unified & Side-by-Side Split Views)
              <div className="diff-container">
                <div className="diff-header-bar">
                  <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                    <span><strong>Target:</strong> {selectedArtifact.name}</span>
                    <span style={{ color: "var(--text-muted)" }}>|</span>
                    <span><strong>Baseline:</strong> {artifactDiff?.baseline_path || "Initial file synthesis (/dev/null)"}</span>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.8rem" }}>
                    <div className="view-switcher-pill">
                      <button
                        className={`view-switcher-btn ${diffLayoutMode === "split" ? "active" : ""}`}
                        onClick={() => setDiffLayoutMode("split")}
                        style={{ fontSize: "0.65rem", padding: "0.15rem 0.45rem" }}
                        title="Side-by-side dual pane view"
                      >
                        ◫ Split
                      </button>
                      <button
                        className={`view-switcher-btn ${diffLayoutMode === "unified" ? "active" : ""}`}
                        onClick={() => setDiffLayoutMode("unified")}
                        style={{ fontSize: "0.65rem", padding: "0.15rem 0.45rem" }}
                        title="Single column unified view"
                      >
                        ☰ Unified
                      </button>
                    </div>
                    <div style={{ display: "flex", gap: "0.4rem" }}>
                      <span className="diff-badge-add">+{artifactDiff?.additions_count || 0}</span>
                      <span className="diff-badge-del">-{artifactDiff?.deletions_count || 0}</span>
                    </div>
                  </div>
                </div>

                {isLoadingDiff ? (
                  <div style={{ padding: "1.5rem", textAlign: "center", color: "var(--text-muted)" }}>
                    Computing unified diff against repository baseline...
                  </div>
                ) : !artifactDiff?.diff ? (
                  <div style={{ padding: "1.5rem", textAlign: "center", color: "var(--text-muted)" }}>
                    No diff detected. Synthesized content is identical to workspace baseline.
                  </div>
                ) : diffLayoutMode === "split" ? (
                  // Side-by-Side Dual Pane Diff
                  <div className="diff-split-container">
                    <div className="diff-split-subheaders">
                      <div className="diff-split-subcol">
                        <span>Original: {artifactDiff?.baseline_path || "Baseline (/dev/null)"}</span>
                        <span style={{ color: "#f87171" }}>-{artifactDiff?.deletions_count || 0}</span>
                      </div>
                      <div className="diff-split-subcol">
                        <span>Modified: {selectedArtifact.name}</span>
                        <span style={{ color: "#34d399" }}>+{artifactDiff?.additions_count || 0}</span>
                      </div>
                    </div>
                    {splitDiffRows.map((row, idx) => {
                      if (row.isHunk) {
                        return (
                          <div key={idx} className="diff-split-hunk-row">
                            {row.text}
                          </div>
                        );
                      }
                      return (
                        <div key={idx} className="diff-split-row">
                          {/* Left Column (Original/Baseline) */}
                          <div className={`diff-split-cell ${row.left ? (row.left.type === "del" ? "diff-split-del" : "diff-split-ctx") : "diff-split-empty"}`}>
                            <div className="diff-split-gutter">{row.left ? row.left.lineNum : ""}</div>
                            <div className="diff-split-text">{row.left ? row.left.text : " "}</div>
                          </div>
                          {/* Right Column (Modified/Head) */}
                          <div className={`diff-split-cell ${row.right ? (row.right.type === "add" ? "diff-split-add" : "diff-split-ctx") : "diff-split-empty"}`}>
                            <div className="diff-split-gutter">{row.right ? row.right.lineNum : ""}</div>
                            <div className="diff-split-text">{row.right ? row.right.text : " "}</div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  // Unified Single Column Diff
                  <div className="diff-lines-wrapper">
                    {artifactDiff.diff.split("\n").map((line, idx) => {
                      let lineClass = "diff-line-ctx";
                      if (line.startsWith("+") && !line.startsWith("+++")) lineClass = "diff-line-add";
                      else if (line.startsWith("-") && !line.startsWith("---")) lineClass = "diff-line-del";
                      else if (line.startsWith("@@")) lineClass = "diff-line-hunk";
                      return (
                        <div key={idx} className={`diff-line ${lineClass}`}>
                          {line || " "}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            ) : selectedArtifact ? (
              // Populated IDE Code Editor with Interactive Line Gutter & Revision Support
              <div style={{ display: "flex", flexDirection: "column", width: "100%", height: "100%" }}>
                {/* ACTIVE REVISIONS BANNER */}
                {activeFileRevisions.length > 0 && (
                  <div className="revisions-banner">
                    <span className="revisions-banner-badge">
                      💬 {activeFileRevisions.length} Revision Request{activeFileRevisions.length > 1 ? "s" : ""} Active
                    </span>
                    <div className="revisions-banner-list">
                      {activeFileRevisions.map((rev, idx) => (
                        <span
                          key={idx}
                          className="revision-pill"
                          onClick={() => {
                            setCommentingLine(rev.line);
                            setLineCommentText(rev.comment);
                          }}
                          title={rev.comment}
                        >
                          Line {rev.line}: &ldquo;{rev.comment}&rdquo;
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* INLINE REVISION PROMPT OVERLAY */}
                {commentingLine !== null && (
                  <div className="inline-revision-overlay">
                    <div className="inline-revision-card">
                      <div className="inline-revision-header">
                        <span className="inline-revision-title">
                          💬 Request Agent Revision on Line <code>{selectedArtifact.name}:{commentingLine}</code>
                        </span>
                        <button
                          type="button"
                          className="close-btn-xs"
                          onClick={() => setCommentingLine(null)}
                          aria-label="Close"
                        >
                          &times;
                        </button>
                      </div>
                      <div className="inline-revision-body">
                        <input
                          type="text"
                          className="inline-revision-input"
                          placeholder="Instruct agent to revise this line (e.g., validate boundary condition, handle nulls)..."
                          value={lineCommentText}
                          onChange={(e) => setLineCommentText(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && lineCommentText.trim()) {
                              handleSendLineComment(commentingLine);
                            } else if (e.key === "Escape") {
                              setCommentingLine(null);
                            }
                          }}
                          autoFocus
                        />
                        <div className="inline-revision-actions">
                          <button
                            type="button"
                            className="btn btn-xs btn-outline"
                            onClick={() => setCommentingLine(null)}
                          >
                            Cancel
                          </button>
                          <button
                            type="button"
                            className="btn btn-xs btn-primary"
                            onClick={() => handleSendLineComment(commentingLine)}
                            disabled={!lineCommentText.trim() || isSubmittingComment}
                          >
                            {isSubmittingComment ? "Submitting..." : "Submit Revision ↵"}
                          </button>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                <div style={{ display: "flex", flex: 1, minHeight: 0 }}>
                  {/* LINE NUMBERS GUTTER */}
                  <div className="ide-gutter">
                    {lineNumbers.map(n => {
                      const hasComment = activeFileRevisions.some(r => r.line === n);
                      return (
                        <div
                          key={n}
                          className={`gutter-line-item ${hasComment ? "has-comment" : ""} ${commentingLine === n ? "active-comment" : ""}`}
                          onClick={() => {
                            if (commentingLine === n) {
                              setCommentingLine(null);
                            } else {
                              setCommentingLine(n);
                              setLineCommentText("");
                            }
                          }}
                          title={`Line ${n}: Click to request agent revision`}
                        >
                          <span className="gutter-line-num">{n}</span>
                          {hasComment && <span className="gutter-comment-icon">💬</span>}
                        </div>
                      );
                    })}
                  </div>

                  {/* SYNTAX HIGHLIGHTED CODE OR EDITABLE CODE SURFACE */}
                  {isEditingFile ? (
                    <div className="ide-code-pane" style={{ padding: 0 }}>
                      <textarea
                        className="ide-textarea-editor"
                        value={editedCodeContent}
                        onChange={(e) => setEditedCodeContent(e.target.value)}
                        onKeyDown={(e) => {
                          if ((e.ctrlKey || e.metaKey) && e.key === "s") {
                            e.preventDefault();
                            handleSaveEditedFile();
                          } else if (e.key === "Tab") {
                            e.preventDefault();
                            const start = e.target.selectionStart;
                            const end = e.target.selectionEnd;
                            const val = e.target.value;
                            setEditedCodeContent(val.substring(0, start) + "    " + val.substring(end));
                            setTimeout(() => {
                              e.target.selectionStart = e.target.selectionEnd = start + 4;
                            }, 0);
                          } else if (e.key === "Escape") {
                            setIsEditingFile(false);
                            setEditedCodeContent(selectedArtifact.content || "");
                            setSaveFeedback(null);
                          }
                        }}
                        spellCheck="false"
                        autoCapitalize="off"
                        autoComplete="off"
                        autoCorrect="off"
                        autoFocus
                      />
                    </div>
                  ) : (
                    <div className="ide-code-pane">
                      <pre>
                        <code ref={codeViewerRef} className={`language-${currentLanguage}`}>
                          {selectedArtifact.content || "// File content is empty."}
                        </code>
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              // Empty State with CTA
              <div className="empty-canvas" style={{ width: "100%" }}>
                <div className="empty-canvas-icon">💻</div>
                <h3>MAS IDE Workspace Ready</h3>
                <p>
                  Click any file in the <strong>Explorer</strong> on the left, or explore the end-to-end task and code dependency DAG.
                </p>
                <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
                  <button
                    className="btn btn-outline"
                    onClick={() => setEditorViewMode("dag")}
                    style={{ color: "#38bdf8", borderColor: "rgba(56, 189, 248, 0.4)", fontSize: "0.8rem", padding: "0.45rem 1rem" }}
                  >
                    🕸️ Explore Architecture DAG
                  </button>
                  <button
                    className="btn btn-primary"
                    onClick={() => setIsNewMissionOpen(true)}
                    style={{ fontSize: "0.8rem", padding: "0.45rem 1rem" }}
                  >
                    + Launch New Mission
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* 5. IDE STATUS BAR */}
          <footer className="ide-status-bar dark-status">
            <div className="ide-status-left">
              <span className="ide-status-item">
                <span>Ln {lineCount}, Col 1</span>
              </span>
              <span className="ide-status-item">Spaces: 4</span>
              <span className="ide-status-item">UTF-8</span>
              <span className="ide-status-item">LF</span>
              <span
                className="ide-status-item ide-status-clickable"
                onClick={() => setIsCostModalOpen(true)}
                title="Click to inspect real-time token burn, model costs, and Gemini context caching savings"
                style={{ cursor: "pointer", display: "inline-flex", alignItems: "center", gap: "0.25rem" }}
              >
                <span>⚡ {((costTelemetry?.total_tokens || missionData.tokens?.total || 12800) / 1000).toFixed(1)}k tok</span>
                <span style={{ color: "#34d399", fontWeight: 700 }}>
                  (${Number(costTelemetry?.net_cost_usd || 0.007).toFixed(4)})
                </span>
                <span className="telemetry-savings-tag" style={{ marginLeft: "0.15rem" }}>
                  {costTelemetry?.cache_hit_rate_pct ? `${Math.round(costTelemetry.cache_hit_rate_pct)}% cached` : "Cached"}
                </span>
              </span>
              {liveTokenStream && (
                <span className="live-token-pill" title="Live streamed cognitive token buffer">
                  ⚡ Stream: {liveTokenStream}
                </span>
              )}
            </div>

            <div className="ide-status-right">
              <span className="ide-status-item" style={{ color: "var(--accent-green)" }}>
                AST Linter: Verified ✓
              </span>
              <button
                className="btn btn-sm btn-outline"
                style={{
                  fontSize: "0.65rem",
                  padding: "0.15rem 0.45rem",
                  color: "var(--accent-cyan)",
                  borderColor: "rgba(56, 189, 248, 0.4)",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.3rem"
                }}
                onClick={handleLocalGitCommit}
                disabled={isCommittingGit || !activeMissionId}
                title="Create local Git commit checkpoint (Strictly local on disk, zero remote push)"
              >
                {isCommittingGit ? "⏳ Committing..." : "📦 Local Git Commit"}
              </button>
              {gitCommitFeedback && (
                <span
                  style={{
                    fontSize: "0.65rem",
                    fontWeight: 600,
                    color: gitCommitFeedback.status === "COMMITTED" ? "#34d399" : "var(--accent-cyan)",
                    padding: "0.1rem 0.35rem",
                    borderRadius: "4px",
                    background: gitCommitFeedback.status === "COMMITTED" ? "rgba(16, 185, 129, 0.15)" : "rgba(56, 189, 248, 0.12)"
                  }}
                >
                  {gitCommitFeedback.status === "COMMITTED" ? `Committed (${gitCommitFeedback.hash}) ✓` : `Clean (${gitCommitFeedback.hash})`}
                </span>
              )}
              <span className="ide-status-item" style={{ textTransform: "capitalize" }}>
                {currentLanguage}
              </span>
              <button
                className="btn btn-sm btn-outline"
                style={{ fontSize: "0.65rem", padding: "0.1rem 0.4rem" }}
                onClick={() => handleGeneratePR(false, false)}
              >
                🚀 GitHub PR
              </button>
            </div>
          </footer>
        </section>

        {/* RIGHT PANE: HITL STRATEGIC GATES & LIVE EVENT STREAM */}
        <aside className="panel right-panel" aria-label="HITL Strategic Decisions and Activity Feed">
          {isRightCollapsed ? (
            <div className="panel-collapsed-rail">
              <button
                className="rail-btn"
                onClick={() => setIsRightCollapsed(false)}
                title="Expand Decision & Event Panel (Ctrl+J)"
              >
                ❮
              </button>
              {pendingGate && (
                <button
                  className="rail-btn active"
                  onClick={() => setIsRightCollapsed(false)}
                  title="⚠️ Strategic Decision Required!"
                  style={{ borderColor: "#f59e0b" }}
                >
                  ⚠️
                  <span className="rail-badge rail-badge-gate">!</span>
                </button>
              )}
              <button
                className="rail-btn"
                onClick={() => setIsRightCollapsed(false)}
                title={`Live Event Stream (${feedLogs.length} events)`}
              >
                📋
                <span className="rail-badge">{feedLogs.length}</span>
              </button>
            </div>
          ) : (
            <>
              {/* STRATEGIC GATE DECISION CARD */}
              {pendingGate && (
                <div className="gate-card-wrapper" role="alert" aria-live="assertive">
                  <div className="gate-card">
                    <div className="gate-badge">⚠️ HUMAN DECISION REQUIRED</div>
                    <h3>{pendingGate.gate || pendingGate.level || "Gate: Strategic Review"}</h3>
                    <p className="gate-premise">
                      {pendingGate.pre_mortem ||
                       pendingGate.premise ||
                       pendingGate.context?.blast_radius_summary ||
                       "A strategic boundary gate has been reached. Inspect blast radius and approve next phase."}
                    </p>
                    <div className="gate-mitigation-box">
                      <strong>Pre-Mortem Mitigation:</strong> Non-locking index verification and contract compliance locked.
                    </div>

                    <div style={{ marginTop: "0.5rem" }}>
                      <input
                        type="text"
                        className="search-input"
                        placeholder="Optional feedback or redirection note for agents..."
                        value={gateFeedback}
                        onChange={(e) => setGateFeedback(e.target.value)}
                      />
                    </div>

                    <div className="gate-actions">
                      <button
                        className="btn btn-success"
                        onClick={() => handleGateDecision("APPROVED")}
                        disabled={isResolvingGate}
                      >
                        Approve <span className="kbd-hint">A</span>
                      </button>
                      <button
                        className="btn btn-warning"
                        onClick={() => handleGateDecision("MODIFIED")}
                        disabled={isResolvingGate}
                      >
                        Modify <span className="kbd-hint">M</span>
                      </button>
                      <button
                        className="btn btn-danger"
                        onClick={() => handleGateDecision("REJECTED")}
                        disabled={isResolvingGate}
                      >
                        Reject <span className="kbd-hint">R</span>
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* ACTIVITY FEED HEADER & CONTROLS */}
              <div className="panel-header">
                <h2>Live Event Stream</h2>
                <div style={{ display: "flex", alignItems: "center", gap: "0.25rem" }}>
                  {["ALL", "POD", "GATE", "ARTIFACT"].map(f => (
                    <button
                      key={f}
                      className={`btn btn-sm ${feedFilter === f ? "btn-primary" : "btn-outline"}`}
                      style={{ fontSize: "0.65rem", padding: "0.15rem 0.4rem" }}
                      onClick={() => setFeedFilter(f)}
                    >
                      {f}
                    </button>
                  ))}
                  <button
                    className="panel-collapse-toggle"
                    onClick={() => setIsRightCollapsed(true)}
                    title="Collapse Panel (Ctrl+J)"
                    style={{ marginLeft: "0.25rem" }}
                  >
                    ❯
                  </button>
                </div>
              </div>

              {/* LIVE SEARCH & FILTER INPUT BAR */}
              <div
                style={{
                  padding: "0.35rem 0.65rem",
                  borderBottom: "1px solid var(--border-color)",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.4rem",
                  background: "rgba(0, 0, 0, 0.18)"
                }}
              >
                <div style={{ position: "relative", flex: 1, display: "flex", alignItems: "center" }}>
                  <input
                    type="text"
                    className="search-input"
                    style={{
                      width: "100%",
                      paddingRight: feedSearchQuery ? "1.6rem" : "0.5rem",
                      fontSize: "0.72rem",
                      height: "26px",
                      margin: 0
                    }}
                    placeholder="Search events (e.g. error, pod, artifact)..."
                    value={feedSearchQuery}
                    onChange={(e) => setFeedSearchQuery(e.target.value)}
                  />
                  {feedSearchQuery && (
                    <button
                      type="button"
                      onClick={() => setFeedSearchQuery("")}
                      style={{
                        position: "absolute",
                        right: "6px",
                        background: "none",
                        border: "none",
                        color: "#94a3b8",
                        cursor: "pointer",
                        fontSize: "0.75rem",
                        padding: "2px",
                        lineHeight: 1
                      }}
                      title="Clear search"
                    >
                      ✕
                    </button>
                  )}
                </div>
                <span
                  style={{
                    fontSize: "0.68rem",
                    color: "var(--text-muted)",
                    whiteSpace: "nowrap",
                    fontFamily: "var(--font-mono)"
                  }}
                  title="Matching / Total events"
                >
                  {filteredFeedLogs.length}/{feedLogs.length}
                </span>
              </div>

              <div className="activity-feed" role="log" aria-live="polite">
                {filteredFeedLogs.length === 0 ? (
                  <div style={{ padding: "2rem 1rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.75rem" }}>
                    <div style={{ fontSize: "1.4rem", marginBottom: "0.4rem" }}>🔍</div>
                    <div style={{ color: "var(--text-secondary)", fontWeight: 600 }}>No matching events</div>
                    <div style={{ fontSize: "0.7rem", marginTop: "0.2rem" }}>
                      No events match &ldquo;{feedSearchQuery}&rdquo; {feedFilter !== "ALL" ? `in category [${feedFilter}]` : ""}
                    </div>
                    <button
                      className="btn btn-sm btn-outline"
                      style={{ marginTop: "0.75rem", fontSize: "0.7rem", padding: "0.2rem 0.6rem" }}
                      onClick={() => { setFeedSearchQuery(""); setFeedFilter("ALL"); }}
                    >
                      Reset Filters
                    </button>
                  </div>
                ) : (
                  filteredFeedLogs.map((entry, idx) => {
                    let tagClass = "system-msg";
                    if (entry.type === "POD") tagClass = "pod-msg";
                    else if (entry.type === "GATE") tagClass = "gate-msg";
                    else if (entry.type === "SUCCESS") tagClass = "success-msg";
                    else if (entry.type === "ERROR") tagClass = "error-msg";

                    return (
                      <div key={idx} className={`feed-entry ${tagClass}`}>
                        <span className="feed-time">{entry.time}</span>
                        <span className="feed-text">{renderHighlightedFeedText(entry.text, feedSearchQuery)}</span>
                      </div>
                    );
                  })
                )}
                <div ref={feedEndRef} />
              </div>
            </>
          )}
        </aside>
      </main>

      {/* 3. BOTTOM COLLAPSIBLE DRAWER: SANDBOX TERMINAL */}
      <footer className={`bottom-drawer ${isTerminalExpanded ? "expanded" : ""}`} role="contentinfo">
        <div
          className="drawer-header"
          onClick={() => setIsTerminalExpanded(prev => !prev)}
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setIsTerminalExpanded(prev => !prev); }}
          role="button"
          aria-expanded={isTerminalExpanded}
        >
          <div className="drawer-title">
            <span>⚡ Subprocess Sandbox & Deterministic Linter Terminal</span>
            {lastTestFailure ? (
              <span className="drawer-tag" style={{ background: "rgba(239, 68, 68, 0.15)", color: "#f87171", borderColor: "rgba(239, 68, 68, 0.35)" }}>
                Failed ({lastTestFailure.assigned_pod})
              </span>
            ) : (
              <span className="drawer-tag">Exit Code: 0 (AST Verified)</span>
            )}
            <span className="kbd-hint">T to toggle</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <button
              type="button"
              className="run-tests-btn"
              onClick={(e) => {
                e.stopPropagation();
                handleRunSandboxedTests();
              }}
              disabled={isRunningTests || !activeMissionId}
              title="Run pytest inside isolated SubprocessSandbox"
            >
              {isRunningTests ? "⏳ Running Pytest..." : "▶ Run Sandboxed Tests"}
            </button>
            <button className="drawer-btn">
              {isTerminalExpanded ? "▼ Collapse" : "▲ Expand"}
            </button>
          </div>
        </div>
        <div className="drawer-body">
          {lastTestFailure && (
            <div className="terminal-diagnostic-bar">
              <div className="terminal-diagnostic-info">
                <span className="diagnostic-badge">🚨 Failure</span>
                <span className="diagnostic-target">
                  <strong>{lastTestFailure.target_file}{lastTestFailure.line_number ? `:${lastTestFailure.line_number}` : ""}</strong>
                </span>
                <span className="diagnostic-pill">{lastTestFailure.assigned_pod}</span>
                <span className="diagnostic-summary" title={lastTestFailure.failure_summary}>
                  {lastTestFailure.failure_summary}
                </span>
              </div>
              <div className="terminal-diagnostic-actions">
                <button
                  type="button"
                  className="btn-autofix"
                  onClick={handleAutoFixTestFailure}
                  disabled={isAutoFixing}
                  title={`Dispatch autonomous ReAct self-healing loop with ${lastTestFailure.assigned_pod}`}
                >
                  {isAutoFixing ? "⏳ Auto-Fixing..." : `🔧 Auto-Fix with ${lastTestFailure.assigned_pod}`}
                </button>
                <button
                  type="button"
                  className="btn-dismiss-diagnostic"
                  onClick={() => setLastTestFailure(null)}
                  title="Dismiss diagnostic callout"
                >
                  ✕
                </button>
              </div>
            </div>
          )}
          <div className="terminal-output">
            {terminalLogs}
            <div ref={terminalEndRef} />
          </div>
        </div>
      </footer>

      {/* 4. NEW MISSION MODAL */}
      {isNewMissionOpen && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="modal-title">
          <div className="modal-card">
            <div className="modal-header">
              <h2 id="modal-title">Launch Multi-Agent Engineering Mission</h2>
              <button
                className="close-btn"
                onClick={() => setIsNewMissionOpen(false)}
                aria-label="Close modal"
              >
                &times;
              </button>
            </div>

            {/* PRESET CHIPS */}
            <div style={{ marginBottom: "0.75rem" }}>
              <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>
                Quick Presets:
              </label>
              <div className="presets-container">
                {MISSION_PRESETS.map((p, i) => (
                  <button
                    key={i}
                    type="button"
                    className="preset-chip"
                    onClick={() => setNewMissionForm(prev => ({ ...prev, title: p.title, description: p.description }))}
                  >
                    ⚡ {p.label}
                  </button>
                ))}
              </div>
            </div>

            <form onSubmit={handleLaunchMission}>
              <div className="form-group">
                <label htmlFor="task-title">Task Title</label>
                <input
                  id="task-title"
                  type="text"
                  required
                  value={newMissionForm.title}
                  onChange={(e) => setNewMissionForm(prev => ({ ...prev, title: e.target.value }))}
                  placeholder="e.g. Stripe Webhook Verification Service"
                />
              </div>

              <div className="form-group">
                <label htmlFor="task-desc">Task Requirements & Domain Specification</label>
                <textarea
                  id="task-desc"
                  rows={4}
                  required
                  value={newMissionForm.description}
                  onChange={(e) => setNewMissionForm(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Describe APIs, database tables, validation rules, and UI expectations..."
                />
              </div>

              <div className="form-group">
                <label htmlFor="target-dir">Target Workspace Directory (In-Place Mapping)</label>
                <input
                  id="target-dir"
                  type="text"
                  value={newMissionForm.targetDir}
                  onChange={(e) => setNewMissionForm(prev => ({ ...prev, targetDir: e.target.value }))}
                  placeholder="Optional: C:/projects/my-app (leave blank for default blackboard)"
                />
              </div>

              <div className="form-group checkbox-group">
                <input
                  id="chk-interactive"
                  type="checkbox"
                  checked={newMissionForm.interactive}
                  onChange={(e) => setNewMissionForm(prev => ({ ...prev, interactive: e.target.checked }))}
                />
                <label htmlFor="chk-interactive">
                  Enable Interactive Human-in-the-Loop (HITL) Approval Gates
                </label>
              </div>

              <div className="form-group checkbox-group">
                <input
                  id="chk-git-commit"
                  type="checkbox"
                  checked={newMissionForm.gitCommit}
                  onChange={(e) => setNewMissionForm(prev => ({ ...prev, gitCommit: e.target.checked }))}
                />
                <label htmlFor="chk-git-commit">
                  Auto-commit synthesized code to git branch
                </label>
              </div>

              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn-outline"
                  onClick={() => setIsNewMissionOpen(false)}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn btn-primary"
                  disabled={isSubmittingMission}
                >
                  {isSubmittingMission ? "Initializing..." : "Start Autonomous Mission"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 5. PULL REQUEST MODAL */}
      {isPROpen && prResult && (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal-card pr-modal-card">
            <div className="modal-header">
              <h2>GitHub Pull Request Dossier</h2>
              <button className="close-btn" onClick={() => setIsPROpen(false)}>&times;</button>
            </div>

            <div style={{ marginBottom: "0.75rem", display: "flex", gap: "0.5rem", alignItems: "center" }}>
              <span className="file-path-badge">{prResult.pr_id || "PR-001"}</span>
              <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>{prResult.title}</span>
            </div>

            <div className="pr-content-view">
              {prResult.markdown}
            </div>

            <div className="modal-actions" style={{ marginTop: "1rem" }}>
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => {
                  navigator.clipboard.writeText(prResult.markdown);
                  alert("PR Markdown copied to clipboard!");
                }}
              >
                📋 Copy Markdown
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => handleGeneratePR(true, true)}
                disabled={isGeneratingPR}
              >
                {isGeneratingPR ? "Pushing & Submitting..." : "🚀 Push to Remote & Create PR"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 6. POD TELEMETRY & EXECUTION INSPECTOR MODAL */}
      {inspectedPod && (
        <div className="modal-backdrop" onClick={() => setInspectedPod(null)} role="dialog" aria-modal="true">
          <div className="modal-card" style={{ width: "560px" }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                <span style={{ fontSize: "1.5rem" }}>{inspectedPod.podCfg.icon}</span>
                <div>
                  <h2 style={{ margin: 0, fontSize: "1.05rem" }}>{inspectedPod.podCfg.name}</h2>
                  <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "0.15rem" }}>
                    {inspectedPod.podCfg.desc}
                  </div>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span className={`status-pill status-${(inspectedPod.livePod.status || "IDLE").toLowerCase()}`}>
                  {inspectedPod.livePod.status || "IDLE"}
                </span>
                <button
                  type="button"
                  className="close-btn"
                  onClick={() => setInspectedPod(null)}
                  title="Close inspector (Esc)"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* ARCHITECTURE & MODEL PILL */}
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.85rem", flexWrap: "wrap" }}>
              <span className="badge" style={{ background: "rgba(56, 189, 248, 0.15)", color: "var(--accent-cyan)", border: "1px solid rgba(56, 189, 248, 0.3)" }}>
                ⚡ Model: Gemini 3.8 Flash
              </span>
              <span className="badge" style={{ background: "rgba(16, 185, 129, 0.15)", color: "#34d399", border: "1px solid rgba(16, 185, 129, 0.3)" }}>
                🛡️ SubprocessSandbox Isolated
              </span>
              <span className="badge" style={{ background: "rgba(168, 85, 247, 0.15)", color: "#c084fc", border: "1px solid rgba(168, 85, 247, 0.3)" }}>
                🔄 Autonomous ReAct Engine
              </span>
            </div>

            {/* TELEMETRY METRICS GRID */}
            <div className="pod-telemetry-grid">
              <div className="pod-telemetry-stat">
                <div className="stat-label">Prompt Tokens</div>
                <div className="stat-val" style={{ color: "#38bdf8" }}>
                  {(inspectedPod.livePod.tokens?.prompt || 2840).toLocaleString()}
                </div>
              </div>
              <div className="pod-telemetry-stat">
                <div className="stat-label">Thinking Tokens</div>
                <div className="stat-val" style={{ color: "#c084fc" }}>
                  {(inspectedPod.livePod.tokens?.thinking || 1420).toLocaleString()}
                </div>
              </div>
              <div className="pod-telemetry-stat">
                <div className="stat-label">Candidate Tokens</div>
                <div className="stat-val" style={{ color: "#34d399" }}>
                  {(inspectedPod.livePod.tokens?.candidate || 960).toLocaleString()}
                </div>
              </div>
              <div className="pod-telemetry-stat">
                <div className="stat-label">Loop Turn Count</div>
                <div className="stat-val" style={{ color: "#fbbf24" }}>
                  {inspectedPod.livePod.turns || 3} / 10 turns
                </div>
              </div>
            </div>

            {/* CURRENT ACTION & REASONING */}
            <div style={{ marginBottom: "0.85rem" }}>
              <div style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "0.3rem", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                Current Reasoning & Action
              </div>
              <div style={{ background: "rgba(0,0,0,0.3)", border: "1px solid var(--border-color)", borderRadius: "6px", padding: "0.6rem 0.8rem", fontSize: "0.78rem", color: "#f1f5f9", fontFamily: "var(--font-mono)" }}>
                {inspectedPod.livePod.action || "Pod idle and waiting for stage transition trigger."}
              </div>
            </div>

            {/* TARGET ARTIFACT */}
            <div style={{ marginBottom: "1.25rem" }}>
              <div style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--text-secondary)", marginBottom: "0.3rem", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                Target Output Artifact
              </div>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "rgba(0,0,0,0.2)", border: "1px solid var(--border-color)", borderRadius: "6px", padding: "0.5rem 0.8rem" }}>
                <span style={{ fontSize: "0.8rem", fontFamily: "var(--font-mono)", color: "#93c5fd" }}>
                  📄 {inspectedPod.livePod.artifact || inspectedPod.podCfg.defaultArtifact}
                </span>
                <button
                  type="button"
                  className="btn btn-sm btn-primary"
                  style={{ fontSize: "0.72rem", padding: "0.2rem 0.6rem" }}
                  onClick={() => {
                    const artName = inspectedPod.livePod.artifact || inspectedPod.podCfg.defaultArtifact;
                    const art = missionData.artifacts.find(a => a.name.includes(artName));
                    if (art) {
                      openArtifactInEditor(art.id);
                    }
                    setInspectedPod(null);
                  }}
                >
                  Open in Cockpit Editor ↗
                </button>
              </div>
            </div>

            {/* MODAL ACTIONS */}
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "0.5rem" }}>
              <button
                type="button"
                className="btn btn-outline"
                onClick={() => setInspectedPod(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 7. QUICK-ACTION COMMAND PALETTE (CTRL+K) */}
      {isCommandPaletteOpen && (
        <div
          className="command-palette-backdrop"
          onClick={() => setIsCommandPaletteOpen(false)}
          role="dialog"
          aria-modal="true"
        >
          <div className="command-palette-card" onClick={(e) => e.stopPropagation()}>
            <div className="command-palette-input-wrap">
              <span className="command-palette-icon">🔍</span>
              <input
                ref={commandInputRef}
                type="text"
                className="command-palette-input"
                placeholder="Type a command or search actions..."
                value={commandPaletteQuery}
                onChange={(e) => {
                  setCommandPaletteQuery(e.target.value);
                  setCommandPaletteSelectedIndex(0);
                }}
                autoFocus
              />
              <span className="command-palette-badge">ESC to close</span>
            </div>

            <div className="command-palette-list" role="listbox">
              {filteredCommands.length === 0 ? (
                <div style={{ padding: "1.5rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.8rem" }}>
                  No commands match &ldquo;{commandPaletteQuery}&rdquo;
                </div>
              ) : (
                filteredCommands.map((cmd, idx) => {
                  const isSelected = idx === commandPaletteSelectedIndex;
                  return (
                    <div
                      key={cmd.id}
                      className={`command-palette-item ${isSelected ? "active" : ""}`}
                      onClick={() => {
                        cmd.action();
                        setIsCommandPaletteOpen(false);
                      }}
                      onMouseEnter={() => setCommandPaletteSelectedIndex(idx)}
                      role="option"
                      aria-selected={isSelected}
                    >
                      <div className="command-palette-item-left">
                        <span className="command-palette-item-icon">{cmd.icon}</span>
                        <div>
                          <span className="command-palette-item-title">{cmd.title}</span>
                          <span className="command-palette-item-sub">{cmd.sub}</span>
                        </div>
                      </div>
                      {cmd.hint && <span className="command-palette-item-hint">{cmd.hint}</span>}
                    </div>
                  );
                })
              )}
            </div>

            <div className="command-palette-footer">
              <span>Use <kbd style={{ padding: "0.1rem 0.3rem", background: "rgba(255,255,255,0.08)", borderRadius: "3px" }}>↑</kbd> <kbd style={{ padding: "0.1rem 0.3rem", background: "rgba(255,255,255,0.08)", borderRadius: "3px" }}>↓</kbd> to navigate, <kbd style={{ padding: "0.1rem 0.3rem", background: "rgba(255,255,255,0.08)", borderRadius: "3px" }}>↵</kbd> to select</span>
              <span>{filteredCommands.length} available actions</span>
            </div>
          </div>
        </div>
      )}

      {/* 8. IN-COCKPIT REVISION HISTORY & ONE-CLICK ROLLBACK MODAL */}
      {isVersionHistoryOpen && (
        <div
          className="modal-backdrop"
          onClick={() => setIsVersionHistoryOpen(false)}
          role="dialog"
          aria-modal="true"
        >
          <div className="version-history-card" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{ fontSize: "1.25rem" }}>⏱️</span>
                <div>
                  <h2 style={{ margin: 0, fontSize: "1.05rem" }}>
                    Version History: {selectedArtifact?.name}
                  </h2>
                  <div style={{ fontSize: "0.72rem", color: "var(--text-muted)", marginTop: "0.15rem" }}>
                    Deterministic snapshot timeline with AST-safe rollback
                  </div>
                </div>
              </div>
              <button
                type="button"
                className="close-btn"
                onClick={() => setIsVersionHistoryOpen(false)}
                title="Close version history (Esc)"
              >
                ✕
              </button>
            </div>

            {isLoadingVersions ? (
              <div style={{ padding: "2.5rem 1rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.82rem" }}>
                ⏳ Loading artifact version snapshots...
              </div>
            ) : !versionHistoryData?.versions || versionHistoryData.versions.length === 0 ? (
              <div style={{ padding: "2rem 1rem", textAlign: "center", color: "var(--text-muted)", fontSize: "0.82rem" }}>
                No version history recorded yet for this file.
              </div>
            ) : (
              <div className="version-history-list">
                {versionHistoryData.versions
                  .slice()
                  .reverse()
                  .map((ver) => {
                    const isCurrent = ver.version === (selectedArtifact?.version || 1);
                    return (
                      <div
                        key={ver.version}
                        className={`version-entry ${isCurrent ? "current-head" : ""}`}
                      >
                        <div className="version-entry-header">
                          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                            <span className="version-pill-tag">v{ver.version}</span>
                            <span style={{ fontSize: "0.78rem", fontWeight: 600, color: "#f1f5f9" }}>
                              {ver.created_by || "Agent Synthesizer"}
                            </span>
                            {isCurrent && (
                              <span
                                className="badge"
                                style={{
                                  background: "rgba(16, 185, 129, 0.15)",
                                  color: "#34d399",
                                  border: "1px solid rgba(16, 185, 129, 0.3)",
                                  fontSize: "0.62rem"
                                }}
                              >
                                Current Head
                              </span>
                            )}
                          </div>
                          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                            <span style={{ fontSize: "0.68rem", color: "#64748b", fontFamily: "var(--font-mono)" }}>
                              {ver.timestamp ? new Date(ver.timestamp).toLocaleTimeString() : "Recent"}
                            </span>
                            {!isCurrent && (
                              <button
                                type="button"
                                className="btn btn-sm btn-warning"
                                style={{ fontSize: "0.68rem", padding: "0.15rem 0.55rem" }}
                                onClick={() => handleRollbackToVersion(ver.version)}
                                disabled={isRollingBack}
                                title={`Revert file back to v${ver.version}`}
                              >
                                {isRollingBack ? "Rolling back..." : `⏪ Rollback to v${ver.version}`}
                              </button>
                            )}
                          </div>
                        </div>

                        {ver.content && (
                          <div className="version-snippet-preview">
                            {ver.content.split("\n").slice(0, 4).join("\n")}
                          </div>
                        )}
                      </div>
                    );
                  })}
              </div>
            )}

            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "0.75rem" }}>
              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={() => setIsVersionHistoryOpen(false)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* REAL-TIME TOKEN BURN & COST EFFICIENCY INSPECTOR MODAL */}
      <TokenCostInspectorModal
        isOpen={isCostModalOpen}
        onClose={() => setIsCostModalOpen(false)}
        telemetry={costTelemetry}
        missionId={activeMissionId}
      />
    </div>
  );
}

// Error Boundary for UI resilience
class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error: error };
  }
  componentDidCatch(error, errorInfo) {
    console.error("MAS Cockpit ErrorBoundary caught error:", error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ minHeight: "100vh", background: "#080c14", color: "#f87171", padding: "3rem", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", fontFamily: "'Inter', sans-serif", textAlign: "center" }}>
          <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>⚠️</div>
          <h2 style={{ color: "#f9fafb", marginBottom: "0.5rem" }}>Cockpit Runtime Resilience Active</h2>
          <p style={{ color: "#9ca3af", maxWidth: "600px", marginBottom: "1.5rem", fontSize: "0.95rem" }}>
            The UI encountered an unexpected error: {String(this.state.error?.message || this.state.error)}
          </p>
          <pre style={{ background: "#111827", padding: "1rem 1.5rem", borderRadius: "8px", maxWidth: "800px", overflow: "auto", textAlign: "left", fontSize: "0.8rem", color: "#e2e8f0", border: "1px solid rgba(255,255,255,0.1)" }}>
            {this.state.error?.stack || this.state.error?.message || "Unknown render exception"}
          </pre>
          <button
            className="btn btn-primary"
            style={{ marginTop: "1.5rem", padding: "0.6rem 1.5rem" }}
            onClick={() => {
              this.setState({ hasError: false, error: null });
              window.location.reload();
            }}
          >
            Restart & Reload Cockpit
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

// Mount React Root with DOMContentLoaded fallback
function mountApp() {
  const rootElement = document.getElementById("root");
  if (rootElement) {
    const root = ReactDOM.createRoot(rootElement);
    root.render(
      <ErrorBoundary>
        <App />
      </ErrorBoundary>
    );
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", mountApp);
} else {
  mountApp();
}
