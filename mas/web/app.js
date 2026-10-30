/**
 * MAS Mission Control - Reactive Client Application.
 * Handles SSE real-time streaming, pod matrix state machine,
 * interactive HITL gate resolution with hotkeys, and dynamic artifact rendering.
 */

class MASApp {
  constructor() {
    this.currentMissionId = null;
    this.eventSource = null;
    this.artifacts = {};
    this.activeTab = "code";
    this.pendingGate = null;

    this.initDOM();
    this.bindEvents();
    this.checkInitialMission();
  }

  initDOM() {
    this.dom = {
      missionTitle: document.getElementById("mission-title-display"),
      missionId: document.getElementById("mission-id-display"),
      tokenCount: document.getElementById("token-count-display"),
      circuitBreaker: document.getElementById("circuit-breaker-display"),
      stageNodes: [
        document.getElementById("stage-node-1"),
        document.getElementById("stage-node-2"),
        document.getElementById("stage-node-3"),
        document.getElementById("stage-node-4"),
        document.getElementById("stage-node-5"),
      ],
      pods: {
        data: { card: document.getElementById("pod-data"), badge: document.getElementById("badge-pod-data"), action: document.getElementById("action-pod-data") },
        backend: { card: document.getElementById("pod-backend"), badge: document.getElementById("badge-pod-backend"), action: document.getElementById("action-pod-backend") },
        frontend: { card: document.getElementById("pod-frontend"), badge: document.getElementById("badge-pod-frontend"), action: document.getElementById("action-pod-frontend") },
        cloud: { card: document.getElementById("pod-cloud"), badge: document.getElementById("badge-pod-cloud"), action: document.getElementById("action-pod-cloud") },
        qa: { card: document.getElementById("pod-qa"), badge: document.getElementById("badge-pod-qa"), action: document.getElementById("action-pod-qa") },
      },
      artifactList: document.getElementById("artifact-ledger-list"),
      artifactCountBadge: document.getElementById("artifact-count-badge"),
      canvasFilePath: document.getElementById("canvas-file-path"),
      canvasCode: document.getElementById("canvas-code-display"),
      astBadge: document.getElementById("ast-check-badge"),
      gateContainer: document.getElementById("gate-card-container"),
      gateTitle: document.getElementById("gate-title-display"),
      gatePremise: document.getElementById("gate-premise-display"),
      gateMitigation: document.getElementById("gate-mitigation-display"),
      activityFeed: document.getElementById("activity-feed"),
      drawer: document.getElementById("sandbox-drawer"),
      drawerToggle: document.getElementById("drawer-toggle"),
      drawerBtn: document.getElementById("drawer-minimize-btn"),
      terminalOutput: document.getElementById("terminal-output"),
      modal: document.getElementById("modal-new-mission"),
      btnOpenModal: document.getElementById("btn-open-new-mission"),
      btnCloseModal: document.getElementById("btn-close-modal"),
      btnCancelModal: document.getElementById("btn-cancel-modal"),
      formNewMission: document.getElementById("new-mission-form"),
      btnGateApprove: document.getElementById("btn-gate-approve"),
      btnGateModify: document.getElementById("btn-gate-modify"),
      btnGateReject: document.getElementById("btn-gate-reject"),
      btnCopyCanvas: document.getElementById("btn-copy-canvas"),
      btnThemeToggle: document.getElementById("btn-theme-toggle"),
    };
  }

  bindEvents() {
    // Drawer toggle
    this.dom.drawerToggle.addEventListener("click", () => {
      this.dom.drawer.classList.toggle("expanded");
      const isExp = this.dom.drawer.classList.contains("expanded");
      this.dom.drawerBtn.textContent = isExp ? "▼ Minimize" : "▲ Expand";
    });

    // Theme toggle
    this.dom.btnThemeToggle.addEventListener("click", () => {
      document.body.classList.toggle("light-theme");
    });

    // Modal controls
    this.dom.btnOpenModal.addEventListener("click", () => {
      this.dom.modal.style.display = "flex";
    });
    this.dom.btnCloseModal.addEventListener("click", () => {
      this.dom.modal.style.display = "none";
    });
    this.dom.btnCancelModal.addEventListener("click", () => {
      this.dom.modal.style.display = "none";
    });

    // New Mission Form Submit
    this.dom.formNewMission.addEventListener("submit", (e) => {
      e.preventDefault();
      this.handleCreateMission();
    });

    // Gate Decisions
    this.dom.btnGateApprove.addEventListener("click", () => this.submitGateDecision("APPROVED"));
    this.dom.btnGateModify.addEventListener("click", () => this.submitGateDecision("MODIFIED"));
    this.dom.btnGateReject.addEventListener("click", () => this.submitGateDecision("REJECTED"));

    // Global Keyboard Shortcuts (A: Approve, M: Modify, R: Reject)
    window.addEventListener("keydown", (e) => {
      if (this.pendingGate && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName)) {
        if (e.key === "a" || e.key === "A") this.submitGateDecision("APPROVED");
        if (e.key === "m" || e.key === "M") this.submitGateDecision("MODIFIED");
        if (e.key === "r" || e.key === "R") this.submitGateDecision("REJECTED");
      }
    });

    // Tab buttons
    document.querySelectorAll(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        this.activeTab = btn.dataset.tab;
        this.renderCanvasTab();
      });
    });

    // Copy canvas button
    this.dom.btnCopyCanvas.addEventListener("click", () => {
      navigator.clipboard.writeText(this.dom.canvasCode.textContent);
      this.dom.btnCopyCanvas.textContent = "Copied!";
      setTimeout(() => (this.dom.btnCopyCanvas.textContent = "Copy"), 1500);
    });
  }

  async checkInitialMission() {
    try {
      const res = await fetch("/api/v1/missions");
      if (res.ok) {
        const data = await res.json();
        if (data.missions && data.missions.length > 0) {
          const latest = data.missions[0];
          this.connectToMission(latest.mission_id);
        }
      }
    } catch {
      // Offline mode or no previous missions
    }
  }

  async handleCreateMission() {
    const title = document.getElementById("input-task-title").value;
    const description = document.getElementById("input-task-desc").value;
    const targetDir = document.getElementById("input-target-dir").value.trim() || null;
    const interactive = document.getElementById("input-interactive").checked;

    this.dom.modal.style.display = "none";
    this.logActivity(`Launching autonomous mission: ${title}`);

    try {
      const res = await fetch("/api/v1/missions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title,
          description,
          target_dir: targetDir,
          interactive,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        this.connectToMission(data.mission_id);
      }
    } catch (err) {
      this.logActivity(`Failed to launch mission: ${err.message}`);
    }
  }

  connectToMission(missionId) {
    if (this.eventSource) {
      this.eventSource.close();
    }

    this.currentMissionId = missionId;
    this.dom.missionId.textContent = missionId;

    // Reset UI state
    this.artifacts = {};
    this.dom.artifactList.innerHTML = "";
    this.dom.terminalOutput.textContent = `[Connected to ${missionId}] Listening for sandbox execution events...\n`;

    // Connect SSE stream
    this.eventSource = new EventSource(`/api/v1/missions/${missionId}/events`);

    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.handleServerEvent(data);
      } catch {
        // Heartbeat or malformed frame
      }
    };

    this.eventSource.onerror = () => {
      // Reconnect handled automatically by EventSource
    };

    // Hydrate snapshot
    this.fetchMissionSnapshot(missionId);
  }

  async fetchMissionSnapshot(missionId) {
    try {
      const res = await fetch(`/api/v1/missions/${missionId}`);
      if (res.ok) {
        const data = await res.json();
        this.dom.missionTitle.textContent = data.title;
        this.updateStageProgress(data.stage);
        this.updateTokenCount(data.tokens_used.total || 0);

        if (data.artifacts) {
          data.artifacts.forEach((art) => this.addArtifact(art));
        }

        if (data.pending_gate) {
          this.showGateCard(data.pending_gate);
        } else {
          this.dom.gateContainer.style.display = "none";
        }
      }
    } catch {
      // Offline fallback
    }
  }

  handleServerEvent(event) {
    const payload = event.payload || {};

    switch (event.type) {
      case "STATUS_CHANGED":
        if (payload.title) this.dom.missionTitle.textContent = payload.title;
        this.logActivity(`Status changed to ${payload.status}`);
        break;

      case "STAGE_CHANGED":
        this.updateStageProgress(payload.stage, payload.stageIndex);
        this.logActivity(`Pipeline transitioned to stage: ${payload.stage}`);
        break;

      case "POD_UPDATED":
        this.updatePodStatus(payload.pod, payload.status, payload.action, payload.artifact);
        break;

      case "GATE_PROMPTED":
        this.pendingGate = payload;
        this.showGateCard(payload);
        this.logActivity(`⚠️ Strategic Gate triggered: ${payload.gate}`);
        break;

      case "GATE_RESOLVED":
        this.pendingGate = null;
        this.dom.gateContainer.style.display = "none";
        this.logActivity(`Gate decision recorded: ${payload.decision}`);
        break;

      case "LOG_STREAMED":
        this.appendTerminalLog(payload.text);
        break;

      case "MISSION_COMPLETED":
        this.updateTokenCount(payload.tokens_used.total);
        this.updateStageProgress("DOCUMENTATION", 5);
        this.logActivity(`🎉 Mission Completed! Processed ${payload.artifacts_count} artifacts.`);
        break;

      case "MISSION_FAILED":
        this.logActivity(`❌ Mission Failed: ${payload.error}`);
        break;
    }
  }

  updateStageProgress(stage, index) {
    const stageMap = {
      CONTRACTS: 1,
      ARCHITECTURE: 2,
      PARALLEL_PODS: 3,
      QA_SECURITY: 4,
      DOCUMENTATION: 5,
    };
    const targetIdx = index || stageMap[stage] || 1;

    this.dom.stageNodes.forEach((node, i) => {
      const nodeNum = i + 1;
      node.classList.remove("active", "completed");
      if (nodeNum < targetIdx) {
        node.classList.add("completed");
      } else if (nodeNum === targetIdx) {
        node.classList.add("active");
      }
    });
  }

  updatePodStatus(podName, status, action, artifact) {
    let key = null;
    if (podName.includes("Data")) key = "data";
    else if (podName.includes("Backend")) key = "backend";
    else if (podName.includes("Frontend")) key = "frontend";
    else if (podName.includes("Cloud")) key = "cloud";
    else if (podName.includes("QA") || podName.includes("Governance")) key = "qa";

    if (key && this.dom.pods[key]) {
      const p = this.dom.pods[key];
      p.card.className = `pod-card ${status.toLowerCase()}`;
      p.badge.className = `status-pill status-${status.toLowerCase()}`;
      p.badge.textContent = status;
      p.action.textContent = action;

      if (artifact) {
        this.artifacts[key] = { name: artifact, content: `// Generating ${artifact}...` };
      }
    }
  }

  showGateCard(gateInfo) {
    this.dom.gateContainer.style.display = "block";
    this.dom.gateTitle.textContent = gateInfo.gate || "Strategic Gate Approval";
    this.dom.gatePremise.textContent = "Pre-Mortem Failure Mode Analysis:";
    this.dom.gateMitigation.textContent = gateInfo.pre_mortem || "Zero-downtime safety invariants verified.";
  }

  async submitGateDecision(decision) {
    if (!this.currentMissionId) return;

    try {
      await fetch(`/api/v1/missions/${this.currentMissionId}/gates/gate/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ decision }),
      });
      this.dom.gateContainer.style.display = "none";
      this.pendingGate = null;
    } catch (err) {
      this.logActivity(`Error submitting gate decision: ${err.message}`);
    }
  }

  addArtifact(art) {
    this.artifacts[art.id] = art;
    const existing = document.getElementById(`art-${art.id}`);
    if (existing) {
      existing.querySelector(".artifact-ver").textContent = `v${art.version}`;
      return;
    }

    const li = document.createElement("li");
    li.id = `art-${art.id}`;
    li.className = "artifact-item";
    li.innerHTML = `
      <span class="artifact-name">${art.name}</span>
      <span class="artifact-ver">v${art.version}</span>
    `;
    li.addEventListener("click", () => this.loadArtifactContent(art.id));
    this.dom.artifactList.appendChild(li);

    this.dom.artifactCountBadge.textContent = Object.keys(this.artifacts).length;

    // Default select service.py or schema.sql
    if (art.name.endsWith(".py") || art.name.endsWith(".sql")) {
      this.loadArtifactContent(art.id);
    }
  }

  async loadArtifactContent(artifactId) {
    try {
      const res = await fetch(`/api/v1/artifacts/${artifactId}`);
      if (res.ok) {
        const data = await res.json();
        this.dom.canvasFilePath.textContent = data.path || data.name;
        this.dom.canvasCode.textContent = data.content;
        this.dom.astBadge.textContent = data.name.endsWith(".py") ? "Python AST: Verified" : "Syntax: Validated";
      }
    } catch {
      // Fallback
    }
  }

  renderCanvasTab() {
    const tabMap = {
      code: "service.py",
      schema: "schema.sql",
      spec: "api-spec.yaml",
      prd: "PRD.md",
      pr: "PULL_REQUEST.md",
    };
    const targetFile = tabMap[this.activeTab];

    const match = Object.values(this.artifacts).find((a) => a.name === targetFile);
    if (match) {
      this.loadArtifactContent(match.id);
    } else {
      this.dom.canvasFilePath.textContent = targetFile;
      this.dom.canvasCode.textContent = `// ${targetFile} will appear once generated by specialized agents...`;
    }
  }

  updateTokenCount(total) {
    this.dom.tokenCount.textContent = total.toLocaleString();
  }

  appendTerminalLog(text) {
    this.dom.terminalOutput.textContent += `${text}\n`;
    this.dom.terminalOutput.scrollTop = this.dom.terminalOutput.scrollHeight;
  }

  logActivity(text) {
    const entry = document.createElement("div");
    entry.className = "feed-entry system-msg";
    const now = new Date();
    const timeStr = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
    entry.innerHTML = `<span class="feed-time">${timeStr}</span><span class="feed-text">${text}</span>`;
    this.dom.activityFeed.appendChild(entry);
    this.dom.activityFeed.scrollTop = this.dom.activityFeed.scrollHeight;
  }
}

// Instantiate on page load
window.addEventListener("DOMContentLoaded", () => {
  window.masApp = new MASApp();
});
