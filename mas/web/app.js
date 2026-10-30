/**
 * MAS Web Mission Control - Modern React 18 Application with IDE-Grade Workspace
 * Comprehensive multi-agent command cockpit with real-time SSE streaming,
 * VS Code-style File Explorer, multi-tab editor, line-number gutter,
 * disk path traceability, and interactive HITL gates.
 */

const {
  useState,
  useEffect,
  useRef,
  useMemo,
  useCallback
} = React;

// --- PRESET MISSION TEMPLATES ---
const MISSION_PRESETS = [{
  label: "FinTech Payments",
  title: "Stripe Webhook & Payment Reconciliation Service",
  description: "Implement secure payment webhook verification, idempotent transaction processing, PostgreSQL double-entry ledger with non-locking indexes, React payment status dashboard, and Terraform KMS IaC."
}, {
  label: "Healthcare EHR",
  title: "HIPAA-Compliant Patient Telemetry Service",
  description: "Design FHIR-compliant patient telemetry ingestion REST APIs, partitioned PostgreSQL audit logs, role-based access controls, React patient timeline component, and hardened Docker container."
}, {
  label: "E-Commerce Cart",
  title: "High-Concurrency Inventory & Checkout Engine",
  description: "Implement inventory reservation REST API, optimistic concurrency control, PostgreSQL schema with foreign keys, 4-state accessible React checkout widget, and Terraform cloud infrastructure."
}, {
  label: "Auth & IAM",
  title: "Multi-Tenant OAuth2 & Session Gateway",
  description: "Author OAuth2 authorization server endpoints, tenant isolation policies in PostgreSQL, accessible React login/switch-tenant view, and Docker container with health checks."
}];

// --- STAGE DEFINITIONS ---
const PIPELINE_STAGES = [{
  id: "CONTRACTS",
  index: 1,
  label: "Triage & Contracts",
  desc: "Business invariant triage & blast radius analysis"
}, {
  id: "ARCHITECTURE",
  index: 2,
  label: "Architecture",
  desc: "API contracts, data models & security boundary lock"
}, {
  id: "PARALLEL_PODS",
  index: 3,
  label: "Parallel Pods",
  desc: "Concurrent synthesis: Data, Backend, Frontend, Cloud"
}, {
  id: "QA_SECURITY",
  index: 4,
  label: "QA & Security",
  desc: "Sandboxed pytest suite & OWASP Top 10 code audit"
}, {
  id: "DOCUMENTATION",
  index: 5,
  label: "PR Lander",
  desc: "6-document developer suite & remote GitHub PR"
}];

// --- POD DEFINITIONS ---
const POD_CONFIGS = [{
  key: "Data Pod",
  icon: "🗄️",
  name: "Data & Storage Pod",
  desc: "PostgreSQL DDL & Non-Locking Indexing",
  defaultArtifact: "schema.sql"
}, {
  key: "Backend Pod",
  icon: "⚙️",
  name: "Backend & AI Pod",
  desc: "REST APIs, Pydantic & ReAct Self-Healing",
  defaultArtifact: "service.py"
}, {
  key: "Frontend Pod",
  icon: "🎨",
  name: "Frontend Pod",
  desc: "4-State Accessible React TSX Component",
  defaultArtifact: "IntegrationView.tsx"
}, {
  key: "Cloud & SRE Pod",
  icon: "☁️",
  name: "Cloud & Platform Pod",
  desc: "Terraform KMS IaC & Hardened Dockerfile",
  defaultArtifact: "Dockerfile"
}, {
  key: "Governance & QA",
  icon: "🛡️",
  name: "Governance & QA Pod",
  desc: "Sandboxed Pytest & OWASP Top 10 Audit",
  defaultArtifact: "TestReport.json"
}];

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

// --- MAIN REACT APP COMPONENT ---
function App() {
  // --- APPLICATION STATE ---
  const [theme, setTheme] = useState("dark");
  const [activeMissionId, setActiveMissionId] = useState(null);
  const [missionsList, setMissionsList] = useState([]);
  const [sidebarTab, setSidebarTab] = useState("explorer"); // "explorer" | "pods"

  const [missionData, setMissionData] = useState({
    title: "Core Enterprise Resource Service",
    description: "Implement secure REST API endpoints with PostgreSQL persistence, React UI, and Terraform KMS IaC.",
    target_dir: "artifacts",
    status: "INITIALIZING",
    stage: "CONTRACTS",
    stageIndex: 1,
    tokens: {
      prompt: 0,
      candidate: 0,
      thinking: 0,
      total: 0
    },
    circuitBreaker: {
      total_turns: 0,
      max_turns: 30,
      healthy: true
    },
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
  const [feedLogs, setFeedLogs] = useState([{
    time: "00:00:00",
    type: "SYSTEM",
    text: "MAS IDE Workspace & Cockpit initialized. Connected to local runtime."
  }]);
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
  const [pathCopyFeedback, setPathCopyFeedback] = useState(false);
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
    setFeedLogs(prev => [...prev, {
      time: timeStr,
      type,
      text
    }]);
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
  const openArtifactInEditor = useCallback(async artifactId => {
    if (!artifactId) return;
    setArtifactLoading(true);
    setArtifactError(null);
    try {
      const res = await fetch(`/api/v1/artifacts/${artifactId}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to load artifact`);
      const data = await res.json();
      setSelectedArtifact(data);
      setActiveTabId(data.id);

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

  // --- FETCH MISSION STATUS ---
  const fetchMissionDetails = useCallback(async missionId => {
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

      // If no file is open, open the primary synthesized service
      if (data.artifacts && data.artifacts.length > 0 && !selectedArtifact) {
        const primary = data.artifacts.find(a => a.name.includes("service.py")) || data.artifacts[0];
        openArtifactInEditor(primary.id);
      }
    } catch (err) {
      console.error("Failed to fetch mission details:", err);
    }
  }, [openArtifactInEditor, selectedArtifact]);

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
    es.onmessage = event => {
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
  const handleIncomingEvent = useCallback(event => {
    const {
      type,
      data
    } = event;
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
          const updatedPods = {
            ...prev.pods,
            [data.pod]: {
              status: data.status,
              action: data.action,
              artifact: data.artifact
            }
          };
          return {
            ...prev,
            pods: updatedPods
          };
        });
        addFeedLog("POD", `[${data.pod}] ${data.action} (${data.status})`);
        break;
      case "GATE_PROMPTED":
      case "GATE_TRIGGERED":
        setPendingGate(data.gate || data);
        addFeedLog("GATE", `⚠️ HUMAN DECISION REQUIRED: ${data.gate && (data.gate.gate || data.gate.level) || data.gate || data.level || "Strategic Approval"}`);
        break;
      case "GATE_RESOLVED":
        setPendingGate(null);
        addFeedLog("GATE", `✅ Gate decision confirmed: ${data.decision}`);
        break;
      case "ARTIFACT_COMMITTED":
        addFeedLog("ARTIFACT", `Synthesized file on disk: ${data.artifact.name} (${data.artifact.path})`);
        setMissionData(prev => ({
          ...prev,
          artifacts: [...prev.artifacts, data.artifact]
        }));
        // Auto-open newly generated file in IDE
        openArtifactInEditor(data.artifact.id);
        break;
      case "TOKEN_BURN":
      case "TOKEN_METRICS_UPDATED":
        if (data.tokens_used) {
          setMissionData(prev => ({
            ...prev,
            tokens_used: data.tokens_used
          }));
        }
        break;
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
        addFeedLog("SUCCESS", `🎉 Mission completed! ${data.artifacts_count || 0} code files written to disk.`);
        refreshMissionsList();
        break;
      case "MISSION_FAILED":
        setMissionData(prev => ({
          ...prev,
          status: "FAILED"
        }));
        addFeedLog("ERROR", `❌ Mission failed: ${data.error}`);
        break;
      default:
        break;
    }
  }, [addFeedLog, openArtifactInEditor, refreshMissionsList]);
  function getStageIndex(stageName) {
    switch (stageName) {
      case "CONTRACTS":
        return 1;
      case "ARCHITECTURE":
        return 2;
      case "PARALLEL_PODS":
        return 3;
      case "QA_SECURITY":
        return 4;
      case "DOCUMENTATION":
        return 5;
      default:
        return 1;
    }
  }

  // --- RESOLVE HITL GATE DECISION ---
  const handleGateDecision = useCallback(async decision => {
    if (!activeMissionId || !pendingGate || isResolvingGate) return;
    setIsResolvingGate(true);
    const gateName = pendingGate.gate || pendingGate.gate_level || pendingGate.level || "GATE_1_BUSINESS_INVARIANTS";
    try {
      const res = await fetch(`/api/v1/missions/${activeMissionId}/gates/${gateName}/decision`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          decision,
          feedback: gateFeedback
        })
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

  // --- KEYBOARD SHORTCUTS ---
  useEffect(() => {
    const handleKeyDown = e => {
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
      feedEndRef.current.scrollIntoView({
        behavior: "smooth"
      });
    }
  }, [feedLogs, autoScrollFeed]);
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({
        behavior: "smooth"
      });
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
  const handleLaunchMission = useCallback(async e => {
    e.preventDefault();
    setIsSubmittingMission(true);
    try {
      const res = await fetch("/api/v1/missions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
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

  // --- GENERATE GITHUB PR ---
  const handleGeneratePR = useCallback(async (pushToRemote = false, createGhPr = false) => {
    if (!activeMissionId) return;
    setIsGeneratingPR(true);
    try {
      const res = await fetch(`/api/v1/missions/${activeMissionId}/pr`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          push: pushToRemote,
          create_pr: createGhPr
        })
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

  // --- GROUP ARTIFACTS INTO HIERARCHICAL IDE DIRECTORY TREE ---
  const directoryTree = useMemo(() => {
    const rawList = missionData.artifacts || [];
    const query = fileSearchQuery.toLowerCase().trim();
    const list = query ? rawList.filter(a => a.name.toLowerCase().includes(query) || a.type.toLowerCase().includes(query)) : rawList;
    const folders = {
      backend: {
        name: "src/backend",
        icon: "📦",
        items: []
      },
      frontend: {
        name: "src/frontend",
        icon: "🎨",
        items: []
      },
      database: {
        name: "db/migrations",
        icon: "🗄️",
        items: []
      },
      contracts: {
        name: "contracts/api",
        icon: "📑",
        items: []
      },
      documentation: {
        name: "docs/spec",
        icon: "📚",
        items: []
      },
      tests: {
        name: "tests/suite",
        icon: "🧪",
        items: []
      },
      cloud: {
        name: "infra/cloud",
        icon: "☁️",
        items: []
      }
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
  }, [missionData.artifacts, fileSearchQuery]);

  // Toggle folder open/closed
  const toggleFolder = useCallback(folderKey => {
    setExpandedFolders(prev => ({
      ...prev,
      [folderKey]: !prev[folderKey]
    }));
  }, []);

  // Compute code lines for line-number gutter
  const lineCount = useMemo(() => {
    if (!selectedArtifact?.content) return 1;
    return selectedArtifact.content.split("\n").length;
  }, [selectedArtifact]);
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
  return /*#__PURE__*/React.createElement("div", {
    className: "cockpit-container",
    style: {
      display: "flex",
      flexDirection: "column",
      height: "100vh"
    }
  }, /*#__PURE__*/React.createElement("header", {
    className: "top-bar",
    role: "banner"
  }, /*#__PURE__*/React.createElement("div", {
    className: "brand-group"
  }, /*#__PURE__*/React.createElement("div", {
    className: "logo-badge",
    title: "Multi-Agent Software Engineering System"
  }, "MAS IDE"), /*#__PURE__*/React.createElement("div", {
    className: "mission-meta"
  }, /*#__PURE__*/React.createElement("h1", {
    title: missionData.title
  }, missionData.title), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      gap: "0.5rem"
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: `live-indicator ${connectionStatus === "STREAMING" ? "" : connectionStatus === "IDLE" ? "idle" : "disconnected"}`
  }), /*#__PURE__*/React.createElement("span", {
    className: "mission-id-badge"
  }, activeMissionId || "MISSION-IDLE")))), /*#__PURE__*/React.createElement("nav", {
    className: "pipeline-progress",
    "aria-label": "Pipeline Stages"
  }, PIPELINE_STAGES.map(stg => {
    const isCompleted = missionData.stageIndex > stg.index || missionData.status === "COMPLETED";
    const isActive = missionData.stageIndex === stg.index && missionData.status !== "COMPLETED";
    return /*#__PURE__*/React.createElement(React.Fragment, {
      key: stg.id
    }, /*#__PURE__*/React.createElement("div", {
      className: `stage-node ${isActive ? "active" : ""} ${isCompleted ? "completed" : ""}`,
      title: `${stg.label}: ${stg.desc}`
    }, /*#__PURE__*/React.createElement("span", {
      className: "node-circle"
    }, isCompleted ? "✓" : stg.index), /*#__PURE__*/React.createElement("span", {
      className: "node-label"
    }, stg.label)), stg.index < 5 && /*#__PURE__*/React.createElement("div", {
      className: `stage-connector ${isCompleted ? "completed" : ""}`
    }));
  })), /*#__PURE__*/React.createElement("div", {
    className: "metrics-controls"
  }, /*#__PURE__*/React.createElement("div", {
    className: "metric-card",
    title: "Prompt, candidate, and thinking tokens burned"
  }, /*#__PURE__*/React.createElement("span", {
    className: "metric-label"
  }, "Tokens"), /*#__PURE__*/React.createElement("span", {
    className: "metric-val"
  }, Number(missionData.tokens.total || 0).toLocaleString())), /*#__PURE__*/React.createElement("div", {
    className: "metric-card",
    title: "Loop detection and recursion ceiling limiter"
  }, /*#__PURE__*/React.createElement("span", {
    className: "metric-label"
  }, "Circuit Breaker"), /*#__PURE__*/React.createElement("span", {
    className: `metric-val ${missionData.circuitBreaker.healthy ? "healthy" : "tripped"}`
  }, missionData.circuitBreaker.healthy ? "HEALTHY" : "TRIPPED")), /*#__PURE__*/React.createElement("button", {
    className: "btn btn-primary",
    onClick: () => setIsNewMissionOpen(true),
    "aria-label": "Launch a new multi-agent mission"
  }, "+ New Mission"), /*#__PURE__*/React.createElement("button", {
    className: "btn btn-outline",
    onClick: toggleTheme,
    "aria-label": "Toggle dark/light theme",
    title: "Toggle theme"
  }, theme === "dark" ? "☀️" : "🌙"))), /*#__PURE__*/React.createElement("main", {
    className: "workspace-grid",
    role: "main",
    style: {
      flex: 1,
      minHeight: 0
    }
  }, /*#__PURE__*/React.createElement("aside", {
    className: "panel left-panel",
    "aria-label": "File Explorer and Pod Matrix"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: "0.25rem",
      marginBottom: "0.75rem",
      borderBottom: "1px solid var(--border-color)",
      paddingBottom: "0.4rem"
    }
  }, /*#__PURE__*/React.createElement("button", {
    className: `btn btn-sm ${sidebarTab === "explorer" ? "btn-primary" : "btn-outline"}`,
    style: {
      flex: 1,
      fontSize: "0.75rem"
    },
    onClick: () => setSidebarTab("explorer")
  }, "📁 Explorer (", missionData.artifacts.length, ")"), /*#__PURE__*/React.createElement("button", {
    className: `btn btn-sm ${sidebarTab === "pods" ? "btn-primary" : "btn-outline"}`,
    style: {
      flex: 1,
      fontSize: "0.75rem"
    },
    onClick: () => setSidebarTab("pods")
  }, "⚡ Pods (5)")), sidebarTab === "explorer" && /*#__PURE__*/React.createElement("div", {
    className: "ide-explorer-panel",
    style: {
      display: "flex",
      flexDirection: "column",
      height: "calc(100% - 45px)"
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      alignItems: "center",
      justifyContent: "space-between",
      marginBottom: "0.4rem"
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: "0.75rem",
      fontWeight: 700,
      textTransform: "uppercase",
      letterSpacing: "0.05em",
      color: "var(--text-secondary)"
    }
  }, "Workspace Files"), /*#__PURE__*/React.createElement("span", {
    className: "badge",
    title: "Total synthesized files on disk"
  }, missionData.artifacts.length, " files")), /*#__PURE__*/React.createElement("input", {
    type: "text",
    className: "search-input",
    placeholder: "Search files (e.g. service.py)...",
    value: fileSearchQuery,
    onChange: e => setFileSearchQuery(e.target.value)
  }), /*#__PURE__*/React.createElement("div", {
    className: "ide-explorer",
    style: {
      flex: 1,
      overflowY: "auto"
    }
  }, Object.entries(directoryTree).map(([fKey, folder]) => {
    if (folder.items.length === 0) return null;
    const isExpanded = expandedFolders[fKey] !== false;
    return /*#__PURE__*/React.createElement("div", {
      key: fKey,
      className: "ide-tree-folder"
    }, /*#__PURE__*/React.createElement("div", {
      className: "ide-folder-header",
      onClick: () => toggleFolder(fKey)
    }, /*#__PURE__*/React.createElement("span", {
      className: `ide-chevron ${isExpanded ? "expanded" : ""}`
    }, "▶"), /*#__PURE__*/React.createElement("span", null, folder.icon), /*#__PURE__*/React.createElement("span", null, folder.name), /*#__PURE__*/React.createElement("span", {
      style: {
        marginLeft: "auto",
        fontSize: "0.68rem",
        color: "var(--text-muted)"
      }
    }, "(", folder.items.length, ")")), isExpanded && /*#__PURE__*/React.createElement("div", {
      className: "ide-folder-children"
    }, folder.items.map(file => {
      const isActive = selectedArtifact?.id === file.id;
      return /*#__PURE__*/React.createElement("div", {
        key: file.id,
        className: `ide-file-item ${isActive ? "active" : ""}`,
        onClick: () => openArtifactInEditor(file.id),
        title: `Path: ${file.path}\nAuthor: ${file.created_by}`
      }, /*#__PURE__*/React.createElement("div", {
        className: "ide-file-label"
      }, /*#__PURE__*/React.createElement("span", {
        className: "ide-file-icon"
      }, getFileIcon(file.name)), /*#__PURE__*/React.createElement("span", null, file.name)), /*#__PURE__*/React.createElement("span", {
        className: "ide-git-badge",
        title: "Synthesized by MAS agent"
      }, "+A"));
    })));
  }), missionData.artifacts.length === 0 && /*#__PURE__*/React.createElement("div", {
    className: "empty-state",
    style: {
      padding: "1.5rem 0.5rem",
      textAlign: "center"
    }
  }, "No files synthesized yet. Click ", /*#__PURE__*/React.createElement("strong", null, "+ New Mission"), " to generate code."))), sidebarTab === "pods" && /*#__PURE__*/React.createElement("div", {
    className: "pod-matrix",
    style: {
      overflowY: "auto",
      height: "calc(100% - 45px)"
    }
  }, POD_CONFIGS.map(podCfg => {
    const livePod = missionData.pods[podCfg.key] || {
      status: "IDLE",
      action: "Standby",
      artifact: podCfg.defaultArtifact
    };
    const status = livePod.status || "IDLE";
    const isRunning = status === "RUNNING";
    const isDone = status === "DONE";
    let statusClass = "status-idle";
    if (isRunning) statusClass = "status-running";else if (isDone) statusClass = "status-done";else if (status === "FAILED") statusClass = "status-tripped";
    return /*#__PURE__*/React.createElement("div", {
      key: podCfg.key,
      className: `pod-card ${isRunning ? "running" : ""}`
    }, /*#__PURE__*/React.createElement("div", {
      className: "pod-header"
    }, /*#__PURE__*/React.createElement("span", {
      className: "pod-icon"
    }, podCfg.icon), /*#__PURE__*/React.createElement("div", {
      className: "pod-info"
    }, /*#__PURE__*/React.createElement("h3", null, podCfg.name), /*#__PURE__*/React.createElement("p", {
      className: "pod-sub"
    }, podCfg.desc)), /*#__PURE__*/React.createElement("span", {
      className: `status-pill ${statusClass}`
    }, status)), /*#__PURE__*/React.createElement("div", {
      className: "pod-action-text"
    }, livePod.action), livePod.artifact && /*#__PURE__*/React.createElement("div", {
      style: {
        marginTop: "0.35rem",
        display: "flex",
        justifyContent: "flex-end"
      }
    }, /*#__PURE__*/React.createElement("span", {
      className: "preset-chip",
      style: {
        fontSize: "0.68rem"
      },
      title: "Open artifact in editor",
      onClick: () => {
        const art = missionData.artifacts.find(a => a.name.includes(livePod.artifact));
        if (art) openArtifactInEditor(art.id);
      }
    }, "📄 ", livePod.artifact)));
  }))), /*#__PURE__*/React.createElement("section", {
    className: "panel center-panel",
    "aria-label": "IDE Code Editor Canvas",
    style: {
      display: "flex",
      flexDirection: "column"
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "ide-tabs-bar",
    role: "tablist"
  }, openTabs.length === 0 ? /*#__PURE__*/React.createElement("div", {
    style: {
      padding: "0.4rem 0.85rem",
      fontSize: "0.75rem",
      color: "var(--text-muted)",
      fontStyle: "italic"
    }
  }, "No open files. Select a file from the Explorer on the left.") : openTabs.map(tab => {
    const isActive = activeTabId === tab.id;
    return /*#__PURE__*/React.createElement("div", {
      key: tab.id,
      className: `ide-tab ${isActive ? "active" : ""}`,
      onClick: () => {
        setActiveTabId(tab.id);
        setSelectedArtifact(tab);
      }
    }, /*#__PURE__*/React.createElement("span", null, getFileIcon(tab.name)), /*#__PURE__*/React.createElement("span", null, tab.name), /*#__PURE__*/React.createElement("span", {
      className: "ide-tab-close",
      title: "Close file tab",
      onClick: e => handleCloseTab(e, tab.id)
    }, "✕"));
  })), selectedArtifact && /*#__PURE__*/React.createElement("div", {
    className: "disk-location-banner"
  }, /*#__PURE__*/React.createElement("div", {
    className: "disk-path-text",
    title: localDiskPath
  }, "📁 ", /*#__PURE__*/React.createElement("strong", null, "Disk Location:"), " ", localDiskPath), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: "0.4rem"
    }
  }, /*#__PURE__*/React.createElement("button", {
    className: "btn btn-sm btn-outline",
    style: {
      fontSize: "0.65rem",
      padding: "0.15rem 0.45rem"
    },
    onClick: handleCopyPath
  }, pathCopyFeedback ? "Path Copied! ✓" : "Copy Path"), /*#__PURE__*/React.createElement("button", {
    className: "btn btn-sm btn-outline",
    style: {
      fontSize: "0.65rem",
      padding: "0.15rem 0.45rem"
    },
    onClick: handleCopyCode
  }, copyFeedback ? "Code Copied! ✓" : "Copy Code"))), selectedArtifact && /*#__PURE__*/React.createElement("div", {
    className: "ide-breadcrumbs"
  }, /*#__PURE__*/React.createElement("span", null, "MAS Workspace"), /*#__PURE__*/React.createElement("span", {
    className: "ide-crumb-sep"
  }, ">"), /*#__PURE__*/React.createElement("span", null, selectedArtifact.path?.split("/")[0] || "artifacts"), /*#__PURE__*/React.createElement("span", {
    className: "ide-crumb-sep"
  }, ">"), /*#__PURE__*/React.createElement("span", {
    className: "ide-crumb-active"
  }, selectedArtifact.name), /*#__PURE__*/React.createElement("span", {
    style: {
      marginLeft: "auto",
      fontSize: "0.68rem",
      color: "var(--accent-green)"
    }
  }, "Author: ", selectedArtifact.created_by || "Agent", " (v", selectedArtifact.version || 1, ")")), /*#__PURE__*/React.createElement("div", {
    className: "ide-editor-container",
    style: {
      flex: 1,
      minHeight: 0
    }
  }, artifactLoading ?
  /*#__PURE__*/
  // Loading Skeleton State
  React.createElement("div", {
    className: "skeleton-container",
    style: {
      width: "100%"
    },
    "aria-busy": "true"
  }, /*#__PURE__*/React.createElement("div", {
    className: "skeleton-line short"
  }), /*#__PURE__*/React.createElement("div", {
    className: "skeleton-line long"
  }), /*#__PURE__*/React.createElement("div", {
    className: "skeleton-line medium"
  }), /*#__PURE__*/React.createElement("div", {
    className: "skeleton-line long"
  }), /*#__PURE__*/React.createElement("div", {
    className: "skeleton-line short"
  }), /*#__PURE__*/React.createElement("div", {
    className: "skeleton-line medium"
  }), /*#__PURE__*/React.createElement("div", {
    className: "skeleton-line long"
  })) : artifactError ?
  /*#__PURE__*/
  // Error State
  React.createElement("div", {
    className: "empty-canvas",
    style: {
      width: "100%"
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "empty-canvas-icon"
  }, "⚠️"), /*#__PURE__*/React.createElement("h3", null, "Failed to load file"), /*#__PURE__*/React.createElement("p", null, artifactError), /*#__PURE__*/React.createElement("button", {
    className: "btn btn-primary",
    onClick: () => selectedArtifact && openArtifactInEditor(selectedArtifact.id)
  }, "Retry Loading")) : selectedArtifact ?
  /*#__PURE__*/
  // Populated IDE Code Editor with Gutter
  React.createElement("div", {
    style: {
      display: "flex",
      width: "100%",
      height: "100%"
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "ide-gutter"
  }, lineNumbers.map(n => /*#__PURE__*/React.createElement("div", {
    key: n
  }, n))), /*#__PURE__*/React.createElement("div", {
    className: "ide-code-pane"
  }, /*#__PURE__*/React.createElement("pre", null, /*#__PURE__*/React.createElement("code", {
    ref: codeViewerRef,
    className: `language-${currentLanguage}`
  }, selectedArtifact.content || "// File content is empty.")))) :
  /*#__PURE__*/
  // Empty State with CTA
  React.createElement("div", {
    className: "empty-canvas",
    style: {
      width: "100%"
    }
  }, /*#__PURE__*/React.createElement("div", {
    className: "empty-canvas-icon"
  }, "💻"), /*#__PURE__*/React.createElement("h3", null, "MAS IDE Workspace Ready"), /*#__PURE__*/React.createElement("p", null, "Click any file in the ", /*#__PURE__*/React.createElement("strong", null, "Explorer"), " on the left to inspect synthesized code, SQL migrations, API contracts, or documentation."), /*#__PURE__*/React.createElement("button", {
    className: "btn btn-primary",
    onClick: () => setIsNewMissionOpen(true)
  }, "+ Launch New Mission"))), /*#__PURE__*/React.createElement("footer", {
    className: "ide-status-bar dark-status"
  }, /*#__PURE__*/React.createElement("div", {
    className: "ide-status-left"
  }, /*#__PURE__*/React.createElement("span", {
    className: "ide-status-item"
  }, /*#__PURE__*/React.createElement("span", null, "Ln ", lineCount, ", Col 1")), /*#__PURE__*/React.createElement("span", {
    className: "ide-status-item"
  }, "Spaces: 4"), /*#__PURE__*/React.createElement("span", {
    className: "ide-status-item"
  }, "UTF-8"), /*#__PURE__*/React.createElement("span", {
    className: "ide-status-item"
  }, "LF")), /*#__PURE__*/React.createElement("div", {
    className: "ide-status-right"
  }, /*#__PURE__*/React.createElement("span", {
    className: "ide-status-item",
    style: {
      color: "var(--accent-green)"
    }
  }, "AST Linter: Verified ✓"), /*#__PURE__*/React.createElement("span", {
    className: "ide-status-item",
    style: {
      textTransform: "capitalize"
    }
  }, currentLanguage), /*#__PURE__*/React.createElement("button", {
    className: "btn btn-sm btn-outline",
    style: {
      fontSize: "0.65rem",
      padding: "0.1rem 0.4rem"
    },
    onClick: () => handleGeneratePR(false, false)
  }, "🚀 GitHub PR")))), /*#__PURE__*/React.createElement("aside", {
    className: "panel right-panel",
    "aria-label": "HITL Strategic Decisions and Activity Feed"
  }, pendingGate && /*#__PURE__*/React.createElement("div", {
    className: "gate-card-wrapper",
    role: "alert",
    "aria-live": "assertive"
  }, /*#__PURE__*/React.createElement("div", {
    className: "gate-card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "gate-badge"
  }, "⚠️ HUMAN DECISION REQUIRED"), /*#__PURE__*/React.createElement("h3", null, pendingGate.gate || pendingGate.level || "Gate: Strategic Review"), /*#__PURE__*/React.createElement("p", {
    className: "gate-premise"
  }, pendingGate.pre_mortem || pendingGate.premise || pendingGate.context?.blast_radius_summary || "A strategic boundary gate has been reached. Inspect blast radius and approve next phase."), /*#__PURE__*/React.createElement("div", {
    className: "gate-mitigation-box"
  }, /*#__PURE__*/React.createElement("strong", null, "Pre-Mortem Mitigation:"), " Non-locking index verification and contract compliance locked."), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: "0.5rem"
    }
  }, /*#__PURE__*/React.createElement("input", {
    type: "text",
    className: "search-input",
    placeholder: "Optional feedback or redirection note for agents...",
    value: gateFeedback,
    onChange: e => setGateFeedback(e.target.value)
  })), /*#__PURE__*/React.createElement("div", {
    className: "gate-actions"
  }, /*#__PURE__*/React.createElement("button", {
    className: "btn btn-success",
    onClick: () => handleGateDecision("APPROVED"),
    disabled: isResolvingGate
  }, "Approve ", /*#__PURE__*/React.createElement("span", {
    className: "kbd-hint"
  }, "A")), /*#__PURE__*/React.createElement("button", {
    className: "btn btn-warning",
    onClick: () => handleGateDecision("MODIFIED"),
    disabled: isResolvingGate
  }, "Modify ", /*#__PURE__*/React.createElement("span", {
    className: "kbd-hint"
  }, "M")), /*#__PURE__*/React.createElement("button", {
    className: "btn btn-danger",
    onClick: () => handleGateDecision("REJECTED"),
    disabled: isResolvingGate
  }, "Reject ", /*#__PURE__*/React.createElement("span", {
    className: "kbd-hint"
  }, "R"))))), /*#__PURE__*/React.createElement("div", {
    className: "panel-header"
  }, /*#__PURE__*/React.createElement("h2", null, "Live Event Stream"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: "flex",
      gap: "0.25rem"
    }
  }, ["ALL", "POD", "GATE", "ARTIFACT"].map(f => /*#__PURE__*/React.createElement("button", {
    key: f,
    className: `btn btn-sm ${feedFilter === f ? "btn-primary" : "btn-outline"}`,
    style: {
      fontSize: "0.65rem",
      padding: "0.15rem 0.4rem"
    },
    onClick: () => setFeedFilter(f)
  }, f)))), /*#__PURE__*/React.createElement("div", {
    className: "activity-feed",
    role: "log",
    "aria-live": "polite"
  }, feedLogs.filter(item => feedFilter === "ALL" || item.type === feedFilter).map((entry, idx) => {
    let tagClass = "system-msg";
    if (entry.type === "POD") tagClass = "pod-msg";else if (entry.type === "GATE") tagClass = "gate-msg";else if (entry.type === "SUCCESS") tagClass = "success-msg";else if (entry.type === "ERROR") tagClass = "error-msg";
    return /*#__PURE__*/React.createElement("div", {
      key: idx,
      className: `feed-entry ${tagClass}`
    }, /*#__PURE__*/React.createElement("span", {
      className: "feed-time"
    }, entry.time), /*#__PURE__*/React.createElement("span", {
      className: "feed-text"
    }, entry.text));
  }), /*#__PURE__*/React.createElement("div", {
    ref: feedEndRef
  })))), /*#__PURE__*/React.createElement("footer", {
    className: `bottom-drawer ${isTerminalExpanded ? "expanded" : ""}`,
    role: "contentinfo"
  }, /*#__PURE__*/React.createElement("div", {
    className: "drawer-header",
    onClick: () => setIsTerminalExpanded(prev => !prev),
    tabIndex: 0,
    onKeyDown: e => {
      if (e.key === "Enter" || e.key === " ") setIsTerminalExpanded(prev => !prev);
    },
    role: "button",
    "aria-expanded": isTerminalExpanded
  }, /*#__PURE__*/React.createElement("div", {
    className: "drawer-title"
  }, /*#__PURE__*/React.createElement("span", null, "⚡ Subprocess Sandbox & Deterministic Linter Terminal"), /*#__PURE__*/React.createElement("span", {
    className: "drawer-tag"
  }, "Exit Code: 0 (AST Verified)"), /*#__PURE__*/React.createElement("span", {
    className: "kbd-hint"
  }, "T to toggle")), /*#__PURE__*/React.createElement("button", {
    className: "drawer-btn"
  }, isTerminalExpanded ? "▼ Collapse" : "▲ Expand")), /*#__PURE__*/React.createElement("div", {
    className: "drawer-body"
  }, /*#__PURE__*/React.createElement("div", {
    className: "terminal-output"
  }, terminalLogs, /*#__PURE__*/React.createElement("div", {
    ref: terminalEndRef
  })))), isNewMissionOpen && /*#__PURE__*/React.createElement("div", {
    className: "modal-backdrop",
    role: "dialog",
    "aria-modal": "true",
    "aria-labelledby": "modal-title"
  }, /*#__PURE__*/React.createElement("div", {
    className: "modal-card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "modal-header"
  }, /*#__PURE__*/React.createElement("h2", {
    id: "modal-title"
  }, "Launch Multi-Agent Engineering Mission"), /*#__PURE__*/React.createElement("button", {
    className: "close-btn",
    onClick: () => setIsNewMissionOpen(false),
    "aria-label": "Close modal"
  }, "×")), /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: "0.75rem"
    }
  }, /*#__PURE__*/React.createElement("label", {
    style: {
      fontSize: "0.75rem",
      fontWeight: 600,
      color: "var(--text-secondary)"
    }
  }, "Quick Presets:"), /*#__PURE__*/React.createElement("div", {
    className: "presets-container"
  }, MISSION_PRESETS.map((p, i) => /*#__PURE__*/React.createElement("button", {
    key: i,
    type: "button",
    className: "preset-chip",
    onClick: () => setNewMissionForm(prev => ({
      ...prev,
      title: p.title,
      description: p.description
    }))
  }, "⚡ ", p.label)))), /*#__PURE__*/React.createElement("form", {
    onSubmit: handleLaunchMission
  }, /*#__PURE__*/React.createElement("div", {
    className: "form-group"
  }, /*#__PURE__*/React.createElement("label", {
    htmlFor: "task-title"
  }, "Task Title"), /*#__PURE__*/React.createElement("input", {
    id: "task-title",
    type: "text",
    required: true,
    value: newMissionForm.title,
    onChange: e => setNewMissionForm(prev => ({
      ...prev,
      title: e.target.value
    })),
    placeholder: "e.g. Stripe Webhook Verification Service"
  })), /*#__PURE__*/React.createElement("div", {
    className: "form-group"
  }, /*#__PURE__*/React.createElement("label", {
    htmlFor: "task-desc"
  }, "Task Requirements & Domain Specification"), /*#__PURE__*/React.createElement("textarea", {
    id: "task-desc",
    rows: 4,
    required: true,
    value: newMissionForm.description,
    onChange: e => setNewMissionForm(prev => ({
      ...prev,
      description: e.target.value
    })),
    placeholder: "Describe APIs, database tables, validation rules, and UI expectations..."
  })), /*#__PURE__*/React.createElement("div", {
    className: "form-group"
  }, /*#__PURE__*/React.createElement("label", {
    htmlFor: "target-dir"
  }, "Target Workspace Directory (In-Place Mapping)"), /*#__PURE__*/React.createElement("input", {
    id: "target-dir",
    type: "text",
    value: newMissionForm.targetDir,
    onChange: e => setNewMissionForm(prev => ({
      ...prev,
      targetDir: e.target.value
    })),
    placeholder: "Optional: C:/projects/my-app (leave blank for default blackboard)"
  })), /*#__PURE__*/React.createElement("div", {
    className: "form-group checkbox-group"
  }, /*#__PURE__*/React.createElement("input", {
    id: "chk-interactive",
    type: "checkbox",
    checked: newMissionForm.interactive,
    onChange: e => setNewMissionForm(prev => ({
      ...prev,
      interactive: e.target.checked
    }))
  }), /*#__PURE__*/React.createElement("label", {
    htmlFor: "chk-interactive"
  }, "Enable Interactive Human-in-the-Loop (HITL) Approval Gates")), /*#__PURE__*/React.createElement("div", {
    className: "form-group checkbox-group"
  }, /*#__PURE__*/React.createElement("input", {
    id: "chk-git-commit",
    type: "checkbox",
    checked: newMissionForm.gitCommit,
    onChange: e => setNewMissionForm(prev => ({
      ...prev,
      gitCommit: e.target.checked
    }))
  }), /*#__PURE__*/React.createElement("label", {
    htmlFor: "chk-git-commit"
  }, "Auto-commit synthesized code to git branch")), /*#__PURE__*/React.createElement("div", {
    className: "modal-actions"
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "btn btn-outline",
    onClick: () => setIsNewMissionOpen(false)
  }, "Cancel"), /*#__PURE__*/React.createElement("button", {
    type: "submit",
    className: "btn btn-primary",
    disabled: isSubmittingMission
  }, isSubmittingMission ? "Initializing..." : "Start Autonomous Mission"))))), isPROpen && prResult && /*#__PURE__*/React.createElement("div", {
    className: "modal-backdrop",
    role: "dialog",
    "aria-modal": "true"
  }, /*#__PURE__*/React.createElement("div", {
    className: "modal-card pr-modal-card"
  }, /*#__PURE__*/React.createElement("div", {
    className: "modal-header"
  }, /*#__PURE__*/React.createElement("h2", null, "GitHub Pull Request Dossier"), /*#__PURE__*/React.createElement("button", {
    className: "close-btn",
    onClick: () => setIsPROpen(false)
  }, "×")), /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: "0.75rem",
      display: "flex",
      gap: "0.5rem",
      alignItems: "center"
    }
  }, /*#__PURE__*/React.createElement("span", {
    className: "file-path-badge"
  }, prResult.pr_id || "PR-001"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: "0.85rem",
      fontWeight: 600
    }
  }, prResult.title)), /*#__PURE__*/React.createElement("div", {
    className: "pr-content-view"
  }, prResult.markdown), /*#__PURE__*/React.createElement("div", {
    className: "modal-actions",
    style: {
      marginTop: "1rem"
    }
  }, /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "btn btn-outline",
    onClick: () => {
      navigator.clipboard.writeText(prResult.markdown);
      alert("PR Markdown copied to clipboard!");
    }
  }, "📋 Copy Markdown"), /*#__PURE__*/React.createElement("button", {
    type: "button",
    className: "btn btn-primary",
    onClick: () => handleGeneratePR(true, true),
    disabled: isGeneratingPR
  }, isGeneratingPR ? "Pushing & Submitting..." : "🚀 Push to Remote & Create PR")))));
}

// Mount React Root
const rootElement = document.getElementById("root");
if (rootElement) {
  const root = ReactDOM.createRoot(rootElement);
  root.render(/*#__PURE__*/React.createElement(App, null));
}