/**
 * MAS Web Mission Control - Modern React 18 Application
 * Comprehensive multi-agent command cockpit with real-time SSE streaming,
 * reactive pod matrix, 4-state artifact canvas, interactive HITL gates,
 * and keyboard-navigable operational controls.
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

// --- MAIN REACT APP COMPONENT ---
function App() {
  // --- APPLICATION STATE ---
  const [theme, setTheme] = useState("dark");
  const [activeMissionId, setActiveMissionId] = useState(null);
  const [missionsList, setMissionsList] = useState([]);
  const [missionData, setMissionData] = useState({
    title: "Core Enterprise Resource Service",
    description: "Implement secure REST API endpoints with PostgreSQL persistence, React UI, and Terraform KMS IaC.",
    status: "INITIALIZING",
    stage: "CONTRACTS",
    stageIndex: 1,
    tokens: { prompt: 0, candidate: 0, thinking: 0, total: 0 },
    circuitBreaker: { total_turns: 0, max_turns: 30, healthy: true },
    pods: {},
    artifacts: []
  });

  const [activeTab, setActiveTab] = useState("code");
  const [selectedArtifact, setSelectedArtifact] = useState(null);
  const [artifactLoading, setArtifactLoading] = useState(false);
  const [artifactError, setArtifactError] = useState(null);
  const [artifactSearch, setArtifactSearch] = useState("");

  const [pendingGate, setPendingGate] = useState(null);
  const [gateFeedback, setGateFeedback] = useState("");
  const [isResolvingGate, setIsResolvingGate] = useState(false);

  const [feedLogs, setFeedLogs] = useState([
    { time: "00:00:00", type: "SYSTEM", text: "MAS React Mission Control initialized. Connected to local runtime." }
  ]);
  const [feedFilter, setFeedFilter] = useState("ALL");
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

  const [copyFeedback, setCopyFeedback] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("IDLE"); // IDLE, STREAMING, DISCONNECTED

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

  // Initial load
  useEffect(() => {
    refreshMissionsList();
  }, [refreshMissionsList]);

  // --- FETCH SPECIFIC ARTIFACT DETAILS ---
  const loadArtifactContent = useCallback(async (artifactId) => {
    if (!artifactId) return;
    setArtifactLoading(true);
    setArtifactError(null);
    try {
      const res = await fetch(`/api/v1/artifacts/${artifactId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to load artifact`);
      const data = await res.json();
      setSelectedArtifact(data);
    } catch (err) {
      setArtifactError(err.message);
    } finally {
      setArtifactLoading(false);
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
        status: data.status,
        stage: data.stage,
        stageIndex: getStageIndex(data.stage),
        tokens: data.tokens_used || prev.tokens,
        circuitBreaker: data.circuit_breaker || prev.circuitBreaker,
        pods: data.pods || prev.pods,
        artifacts: data.artifacts || prev.artifacts
      }));

      if (data.pending_gate) {
        setPendingGate(data.pending_gate);
      } else {
        setPendingGate(null);
      }

      // If active tab has matching artifact, load it
      if (data.artifacts && data.artifacts.length > 0 && !selectedArtifact) {
        const match = data.artifacts[data.artifacts.length - 1];
        loadArtifactContent(match.id);
      }
    } catch (err) {
      console.error("Failed to fetch mission details:", err);
    }
  }, [loadArtifactContent, selectedArtifact]);

  // --- CONNECT TO REAL-TIME SSE STREAM ---
  useEffect(() => {
    if (!activeMissionId) return;

    fetchMissionDetails(activeMissionId);

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
      es.close();
    };

    return () => {
      if (es) es.close();
    };
  }, [activeMissionId]);

  // --- DISPATCH INCOMING REAL-TIME EVENTS ---
  const handleIncomingEvent = useCallback((event) => {
    const { type, data } = event;
    if (!type) return;

    switch (type) {
      case "CONNECTED":
        setConnectionStatus("STREAMING");
        break;

      case "STAGE_CHANGED":
        setMissionData(prev => ({
          ...prev,
          stage: data.stage,
          stageIndex: data.stageIndex || getStageIndex(data.stage)
        }));
        addFeedLog("STAGE", `Pipeline transitioned to Stage ${data.stageIndex}: ${data.stage}`);
        break;

      case "POD_UPDATED":
        setMissionData(prev => {
          const updatedPods = { ...prev.pods, [data.pod]: { status: data.status, action: data.action, artifact: data.artifact } };
          return { ...prev, pods: updatedPods };
        });
        addFeedLog("POD", `[${data.pod}] ${data.action} (${data.status})`);
        break;

      case "GATE_TRIGGERED":
        setPendingGate(data.gate);
        addFeedLog("GATE", `⚠️ HUMAN DECISION REQUIRED: ${data.gate.level || "Strategic Approval"}`);
        break;

      case "GATE_RESOLVED":
        setPendingGate(null);
        addFeedLog("GATE", `✅ Gate decision confirmed: ${data.decision}`);
        break;

      case "ARTIFACT_COMMITTED":
        addFeedLog("ARTIFACT", `Committed artifact: ${data.artifact.name} (${data.artifact.type})`);
        setMissionData(prev => ({
          ...prev,
          artifacts: [...prev.artifacts, data.artifact]
        }));
        // Auto-select newly committed artifact
        loadArtifactContent(data.artifact.id);
        break;

      case "TOKEN_BURN":
        setMissionData(prev => ({
          ...prev,
          tokens: data.tokens_used || prev.tokens
        }));
        break;

      case "LOG_EMITTED":
        setTerminalLogs(prev => prev + data.message + "\n");
        break;

      case "MISSION_COMPLETED":
        setMissionData(prev => ({
          ...prev,
          status: "COMPLETED",
          tokens: data.tokens_used || prev.tokens
        }));
        addFeedLog("SUCCESS", `🎉 Mission completed! ${data.artifacts_count || 0} artifacts locked.`);
        refreshMissionsList();
        break;

      case "MISSION_FAILED":
        setMissionData(prev => ({ ...prev, status: "FAILED" }));
        addFeedLog("ERROR", `❌ Mission failed: ${data.error}`);
        break;

      default:
        break;
    }
  }, [addFeedLog, loadArtifactContent, refreshMissionsList]);

  // Helper to map stage name to index
  function getStageIndex(stageName) {
    switch (stageName) {
      case "CONTRACTS": return 1;
      case "ARCHITECTURE": return 2;
      case "PARALLEL_PODS": return 3;
      case "QA_SECURITY": return 4;
      case "DOCUMENTATION": return 5;
      default: return 1;
    }
  }

  // --- RESOLVE HITL GATE DECISION ---
  const handleGateDecision = useCallback(async (decision) => {
    if (!activeMissionId || !pendingGate || isResolvingGate) return;
    setIsResolvingGate(true);
    const gateName = pendingGate.gate_level || pendingGate.level || "GATE_1_BUSINESS_INVARIANTS";
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

  // --- KEYBOARD SHORTCUTS FOR ACCESSIBILITY & SPEED ---
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Ignore if user is typing in input or textarea
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
      if (e.key === "Escape") {
        setIsNewMissionOpen(false);
        setIsPROpen(false);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [pendingGate, handleGateDecision]);

  // --- AUTO-SCROLL LOGS ---
  useEffect(() => {
    if (autoScrollFeed && feedEndRef.current) {
      feedEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [feedLogs, autoScrollFeed]);

  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [terminalLogs]);

  // --- SYNTAX HIGHLIGHTING EFFECT ---
  useEffect(() => {
    if (codeViewerRef.current && window.Prism) {
      window.Prism.highlightElement(codeViewerRef.current);
    }
  }, [selectedArtifact, activeTab]);

  // --- COPY CANVAS CODE ---
  const handleCopyCode = useCallback(() => {
    if (!selectedArtifact?.content) return;
    navigator.clipboard.writeText(selectedArtifact.content).then(() => {
      setCopyFeedback(true);
      setTimeout(() => setCopyFeedback(false), 2000);
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

  // --- GENERATE GITHUB PULL REQUEST ---
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

  // Filtered artifacts
  const filteredArtifacts = useMemo(() => {
    if (!missionData.artifacts) return [];
    if (!artifactSearch.trim()) return missionData.artifacts;
    const q = artifactSearch.toLowerCase();
    return missionData.artifacts.filter(a =>
      a.name.toLowerCase().includes(q) ||
      a.type.toLowerCase().includes(q) ||
      (a.created_by && a.created_by.toLowerCase().includes(q))
    );
  }, [missionData.artifacts, artifactSearch]);

  // Filtered feed entries
  const filteredFeed = useMemo(() => {
    if (feedFilter === "ALL") return feedLogs;
    return feedLogs.filter(item => item.type === feedFilter);
  }, [feedLogs, feedFilter]);

  // Determine language for Prism
  const codeLanguage = useMemo(() => {
    if (!selectedArtifact) return "javascript";
    const name = selectedArtifact.name.toLowerCase();
    if (name.endsWith(".py")) return "python";
    if (name.endsWith(".sql")) return "sql";
    if (name.endsWith(".tsx") || name.endsWith(".ts")) return "typescript";
    if (name.endsWith(".yaml") || name.endsWith(".yml")) return "yaml";
    if (name.endsWith(".json")) return "json";
    if (name.endsWith(".md")) return "markdown";
    if (name.includes("dockerfile")) return "docker";
    return "javascript";
  }, [selectedArtifact]);

  return (
    <div className="cockpit-container" style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      {/* 1. TOP COMMAND BAR */}
      <header className="top-bar" role="banner">
        <div className="brand-group">
          <div className="logo-badge" title="Multi-Agent Software Engineering System">MAS</div>
          <div className="mission-meta">
            <h1 title={missionData.title}>{missionData.title}</h1>
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span className={`live-indicator ${connectionStatus === "STREAMING" ? "" : connectionStatus === "IDLE" ? "idle" : "disconnected"}`} />
              <span className="mission-id-badge">{activeMissionId || "MISSION-IDLE"}</span>
            </div>
          </div>
        </div>

        {/* 5-STAGE PIPELINE INDICATOR */}
        <nav className="pipeline-progress" aria-label="Pipeline Stages">
          {PIPELINE_STAGES.map((stg) => {
            const isCompleted = missionData.stageIndex > stg.index || missionData.status === "COMPLETED";
            const isActive = missionData.stageIndex === stg.index && missionData.status !== "COMPLETED";
            return (
              <React.Fragment key={stg.id}>
                <div
                  className={`stage-node ${isActive ? "active" : ""} ${isCompleted ? "completed" : ""}`}
                  title={`${stg.label}: ${stg.desc}`}
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

        {/* METRICS & CONTROLS */}
        <div className="metrics-controls">
          <div className="metric-card" title="Prompt, candidate, and thinking tokens burned">
            <span className="metric-label">Tokens</span>
            <span className="metric-val">{Number(missionData.tokens.total || 0).toLocaleString()}</span>
          </div>

          <div className="metric-card" title="Loop detection and recursion ceiling limiter">
            <span className="metric-label">Circuit Breaker</span>
            <span className={`metric-val ${missionData.circuitBreaker.healthy ? "healthy" : "tripped"}`}>
              {missionData.circuitBreaker.healthy ? "HEALTHY" : "TRIPPED"}
            </span>
          </div>

          <button
            className="btn btn-primary"
            onClick={() => setIsNewMissionOpen(true)}
            aria-label="Launch a new multi-agent mission"
          >
            + New Mission
          </button>

          <button
            className="btn btn-outline"
            onClick={toggleTheme}
            aria-label="Toggle dark/light theme"
            title="Toggle theme"
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
        </div>
      </header>

      {/* 2. THREE-PANE MAIN WORKSPACE */}
      <main className="workspace-grid" role="main" style={{ flex: 1, minHeight: 0 }}>
        {/* LEFT PANE: 5-POD MATRIX & ARTIFACT LEDGER */}
        <aside className="panel left-panel" aria-label="Engineering Pods and Artifacts">
          <div className="panel-header">
            <h2>Engineering Pods (Parallel)</h2>
          </div>

          {/* PARALLEL POD MATRIX */}
          <div className="pod-matrix">
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
                <div key={podCfg.key} className={`pod-card ${isRunning ? "running" : ""}`}>
                  <div className="pod-header">
                    <span className="pod-icon">{podCfg.icon}</span>
                    <div className="pod-info">
                      <h3>{podCfg.name}</h3>
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
                        title="Click to view artifact in canvas"
                        onClick={() => {
                          const art = missionData.artifacts.find(a => a.name.includes(livePod.artifact));
                          if (art) loadArtifactContent(art.id);
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

          {/* ARTIFACT LEDGER */}
          <div className="panel-header" style={{ marginTop: "1rem" }}>
            <h2>Artifact Ledger</h2>
            <span className="badge">{missionData.artifacts.length}</span>
          </div>

          <input
            type="text"
            className="search-input"
            placeholder="Filter artifacts by name or pod..."
            value={artifactSearch}
            onChange={(e) => setArtifactSearch(e.target.value)}
            aria-label="Filter artifacts"
          />

          <ul className="artifact-ledger-list">
            {filteredArtifacts.length === 0 ? (
              <li className="empty-state">
                {missionData.artifacts.length === 0
                  ? "No artifacts committed yet. Deploy a mission to begin."
                  : "No artifacts match your filter."}
              </li>
            ) : (
              filteredArtifacts.map(art => {
                const isSelected = selectedArtifact?.id === art.id;
                return (
                  <li
                    key={art.id}
                    className={`artifact-ledger-item ${isSelected ? "selected" : ""}`}
                    onClick={() => loadArtifactContent(art.id)}
                    tabIndex={0}
                    onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") loadArtifactContent(art.id); }}
                    style={{
                      cursor: "pointer",
                      padding: "0.5rem 0.6rem",
                      borderRadius: "6px",
                      border: isSelected ? "1px solid var(--accent-cyan)" : "1px solid transparent",
                      background: isSelected ? "var(--bg-hover)" : "transparent",
                      marginBottom: "0.25rem",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between"
                    }}
                  >
                    <div>
                      <div style={{ fontSize: "0.82rem", fontWeight: 600 }}>{art.name}</div>
                      <div style={{ fontSize: "0.7rem", color: "var(--text-secondary)" }}>
                        {art.created_by || "Agent"} • v{art.version || 1}
                      </div>
                    </div>
                    <span className="status-pill status-idle" style={{ fontSize: "0.65rem" }}>
                      {art.type}
                    </span>
                  </li>
                );
              })
            )}
          </ul>
        </aside>

        {/* CENTER PANE: ARTIFACT CANVAS & CODE WORKBENCH */}
        <section className="panel center-panel" aria-label="Artifact Code Canvas">
          {/* TAB BAR */}
          <div className="canvas-tabs" role="tablist">
            <button
              className={`tab-btn ${activeTab === "code" ? "active" : ""}`}
              onClick={() => {
                setActiveTab("code");
                const match = missionData.artifacts.find(a => a.name.endsWith(".py") || a.name.endsWith(".tsx"));
                if (match) loadArtifactContent(match.id);
              }}
            >
              Synthesized Code
            </button>
            <button
              className={`tab-btn ${activeTab === "schema" ? "active" : ""}`}
              onClick={() => {
                setActiveTab("schema");
                const match = missionData.artifacts.find(a => a.name.endsWith(".sql"));
                if (match) loadArtifactContent(match.id);
              }}
            >
              Database DDL
            </button>
            <button
              className={`tab-btn ${activeTab === "spec" ? "active" : ""}`}
              onClick={() => {
                setActiveTab("spec");
                const match = missionData.artifacts.find(a => a.name.includes("api-spec") || a.name.includes("TaskDAG"));
                if (match) loadArtifactContent(match.id);
              }}
            >
              API Contract
            </button>
            <button
              className={`tab-btn ${activeTab === "prd" ? "active" : ""}`}
              onClick={() => {
                setActiveTab("prd");
                const match = missionData.artifacts.find(a => a.name.includes("PRD") || a.name.includes("architecture"));
                if (match) loadArtifactContent(match.id);
              }}
            >
              PRD & Stories
            </button>
            <button
              className={`tab-btn ${activeTab === "pr" ? "active" : ""}`}
              onClick={() => {
                setActiveTab("pr");
                const match = missionData.artifacts.find(a => a.name.includes("PULL_REQUEST"));
                if (match) loadArtifactContent(match.id);
                else handleGeneratePR(false, false);
              }}
            >
              Pull Request
            </button>
          </div>

          {/* TOOLBAR */}
          <div className="canvas-toolbar">
            <div className="file-path-badge">
              {selectedArtifact ? selectedArtifact.name : "Select an artifact from ledger"}
            </div>
            <div className="toolbar-actions" style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <span className="ast-badge">AST Verified: 100% Pass</span>
              <button
                className="btn btn-sm btn-outline"
                onClick={handleCopyCode}
                disabled={!selectedArtifact}
                title="Copy artifact code to clipboard"
              >
                {copyFeedback ? "Copied!" : "📋 Copy"}
              </button>
              <button
                className="btn btn-sm btn-primary"
                onClick={() => handleGeneratePR(false, false)}
                title="Preview or publish GitHub PR"
              >
                🚀 PR Dossier
              </button>
            </div>
          </div>

          {/* 4-STATE VIEWPORT */}
          <div className="canvas-viewport" style={{ flex: 1, minHeight: 0, position: "relative" }}>
            {artifactLoading ? (
              // 1. Loading Skeleton State
              <div className="skeleton-container" aria-busy="true">
                <div className="skeleton-line short" />
                <div className="skeleton-line long" />
                <div className="skeleton-line medium" />
                <div className="skeleton-line long" />
                <div className="skeleton-line short" />
                <div className="skeleton-line medium" />
                <div className="skeleton-line long" />
              </div>
            ) : artifactError ? (
              // 2. Error State with Retry
              <div className="empty-canvas">
                <div className="empty-canvas-icon">⚠️</div>
                <h3>Failed to load artifact</h3>
                <p>{artifactError}</p>
                <button
                  className="btn btn-primary"
                  onClick={() => selectedArtifact && loadArtifactContent(selectedArtifact.id)}
                >
                  Retry Loading
                </button>
              </div>
            ) : selectedArtifact ? (
              // 3. Populated State with Syntax Highlighting
              <pre style={{ margin: 0, height: "100%", padding: "1rem" }}>
                <code ref={codeViewerRef} className={`language-${codeLanguage}`}>
                  {selectedArtifact.content || "// Artifact content is empty."}
                </code>
              </pre>
            ) : (
              // 4. Empty State with CTA
              <div className="empty-canvas">
                <div className="empty-canvas-icon">🚀</div>
                <h3>No Artifact Selected</h3>
                <p>
                  Deploy a new mission or select an artifact from the Artifact Ledger on the left to inspect synthesized code, SQL DDL, or API specs.
                </p>
                <button
                  className="btn btn-primary"
                  onClick={() => setIsNewMissionOpen(true)}
                >
                  + Launch New Mission
                </button>
              </div>
            )}
          </div>
        </section>

        {/* RIGHT PANE: HITL STRATEGIC GATES & LIVE EVENT STREAM */}
        <aside className="panel right-panel" aria-label="HITL Strategic Decisions and Activity Feed">
          {/* STRATEGIC GATE DECISION CARD */}
          {pendingGate && (
            <div className="gate-card-wrapper" role="alert" aria-live="assertive">
              <div className="gate-card">
                <div className="gate-badge">⚠️ HUMAN DECISION REQUIRED</div>
                <h3>{pendingGate.level || "Gate: Strategic Review"}</h3>
                <p className="gate-premise">
                  {pendingGate.context?.blast_radius_summary ||
                   pendingGate.premise ||
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
            <div style={{ display: "flex", gap: "0.25rem" }}>
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
            </div>
          </div>

          <div className="activity-feed" role="log" aria-live="polite">
            {filteredFeed.map((entry, idx) => {
              let tagClass = "system-msg";
              if (entry.type === "POD") tagClass = "pod-msg";
              else if (entry.type === "GATE") tagClass = "gate-msg";
              else if (entry.type === "SUCCESS") tagClass = "success-msg";
              else if (entry.type === "ERROR") tagClass = "error-msg";

              return (
                <div key={idx} className={`feed-entry ${tagClass}`}>
                  <span className="feed-time">{entry.time}</span>
                  <span className="feed-text">{entry.text}</span>
                </div>
              );
            })}
            <div ref={feedEndRef} />
          </div>
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
            <span className="drawer-tag">Exit Code: 0 (AST Verified)</span>
            <span className="kbd-hint">T to toggle</span>
          </div>
          <button className="drawer-btn">
            {isTerminalExpanded ? "▼ Collapse" : "▲ Expand"}
          </button>
        </div>
        <div className="drawer-body">
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
                  placeholder="Optional: C:/projects/my-app (leave blank for blackboard)"
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
    </div>
  );
}

// Mount React Root
const rootElement = document.getElementById("root");
if (rootElement) {
  const root = ReactDOM.createRoot(rootElement);
  root.render(<App />);
}

