const runId = document.body.dataset.runId;
const rail = document.querySelector("#agent-rail");
const logList = document.querySelector("#live-log");
const statusText = document.querySelector("#live-status");
const captionEl = document.querySelector("#live-caption");
const mediaEl = document.querySelector("#live-media");
const resultLink = document.querySelector("#result-link");
const pipelineStateEl = document.querySelector("#pipeline-state");
const activeNodeTitleEl = document.querySelector("#active-node-title");
const activeNodeFocusEl = document.querySelector("#active-node-focus");
const activeNodeMessageEl = document.querySelector("#active-node-message");
const activeProviderEl = document.querySelector("#active-provider");
const activeImageProviderEl = document.querySelector("#active-image-provider");
const nodeProgressFillEl = document.querySelector("#node-progress-fill");
const nodeProgressPercentEl = document.querySelector("#node-progress-percent");

const statusLabels = {
  waiting: "Waiting",
  active: "Working",
  done: "Done",
  skipped: "Skipped",
  error: "Error",
};

let lastLogCount = 0;

async function pollRun() {
  const response = await fetch(`/api/run/${runId}`);
  const data = await response.json();
  renderAgents(data.agents || []);
  renderLogs(data.logs || []);
  renderOutput(data);
  renderDetails(data);

  statusText.textContent = statusMessage(data);
  if (pipelineStateEl) {
    pipelineStateEl.textContent = data.status === "finished" ? "Pipeline Complete" : data.status === "error" ? "Pipeline Error" : "Pipeline Active";
  }

  if (data.result_url) {
    resultLink.href = data.result_url;
    resultLink.hidden = false;
  }

  if (data.status === "finished" || data.status === "error") {
    return;
  }

  window.setTimeout(pollRun, 850);
}

function renderAgents(agents) {
  rail.style.setProperty("--agent-count", String(Math.max(agents.length, 1)));
  const progress = updateMetroProgress(agents);

  for (const [index, agent] of agents.entries()) {
    const node = rail.querySelector(`[data-agent="${agent.key}"]`);
    if (!node) continue;
    const reached = ["done", "active", "error"].includes(agent.status) ? " reached" : "";
    node.className = `tracking-agent ${agent.status}${reached}`;
    node.style.setProperty("--station-index", String(index));
    const statusLabel = node.querySelector(".node-status-label");
    const message = node.querySelector(".node-message");
    if (statusLabel) statusLabel.textContent = statusLabels[agent.status] || agent.status;
    if (message) message.textContent = agent.message || agent.description;
  }

  if (nodeProgressFillEl) nodeProgressFillEl.style.width = `${Math.round(progress * 100)}%`;
  if (nodeProgressPercentEl) nodeProgressPercentEl.textContent = `${Math.round(progress * 100)}%`;
}

function updateMetroProgress(agents) {
  if (!agents.length) {
    rail.style.setProperty("--metro-progress", "0");
    rail.classList.remove("is-moving");
    return 0;
  }

  const activeIndex = agents.findIndex((agent) => agent.status === "active");
  const reachedIndex = Math.max(
    activeIndex,
    ...agents
      .map((agent, index) => ["done", "skipped", "error"].includes(agent.status) ? index : -1)
      .filter((index) => index >= 0)
  );
  const safeReachedIndex = Math.max(reachedIndex, 0);
  const ratio = agents.length <= 1 ? 1 : safeReachedIndex / (agents.length - 1);

  const progress = Math.min(Math.max(ratio, 0), 1);
  rail.style.setProperty("--metro-progress", String(progress));
  rail.classList.toggle("is-moving", activeIndex > 0);
  return progress;
}

function renderLogs(logs) {
  if (logs.length === lastLogCount) return;
  lastLogCount = logs.length;
  logList.innerHTML = logs.map((log) => `
    <li class="${escapeHtml(log.status)}">
      <strong>${escapeHtml(log.step)}</strong>
      <span>${escapeHtml(log.status)}</span>
      <p>${escapeHtml(log.message)}</p>
    </li>
  `).join("");
  logList.scrollTop = logList.scrollHeight;
}

function renderOutput(data) {
  if (data.caption) {
    captionEl.textContent = data.caption;
    captionEl.classList.remove("muted");
  }

  if (data.media_url) {
    mediaEl.className = "tracking-media";
    mediaEl.innerHTML = `<img src="${data.media_url}" alt="Generated media">`;
  }
}

function renderDetails(data) {
  const agents = data.agents || [];
  const lastDone = [...agents].reverse().find((agent) => agent.status === "done");
  const active = agents.find((agent) => agent.status === "active") || agents.find((agent) => agent.status === "error") || lastDone;
  const latestLog = (data.logs || []).at(-1);

  if (activeNodeTitleEl) activeNodeTitleEl.textContent = active?.label || "Task Manager";
  if (activeNodeFocusEl) activeNodeFocusEl.textContent = data.topic || active?.description || "Routing user request";
  if (activeNodeMessageEl) activeNodeMessageEl.textContent = active?.message || latestLog?.message || "Initializing pipeline...";
  if (activeProviderEl) activeProviderEl.textContent = data.status === "queued" ? "Waiting" : "NVIDIA / local fallback";
  if (activeImageProviderEl) activeImageProviderEl.textContent = data.image_provider || "Waiting";
}

function statusMessage(data) {
  if (data.status === "queued") return "Queued. Waiting for Task Manager.";
  if (data.status === "error") return `Stopped with error: ${data.error || "unknown error"}`;
  if (data.status === "finished") return "Finished. Final post is ready for review.";

  const active = (data.agents || []).find((agent) => agent.status === "active");
  if (!active) return "Agents are synchronizing...";
  return `${active.label} is working: ${active.message}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

pollRun();
