const tabButtons = document.querySelectorAll(".tab-btn");
const views = document.querySelectorAll(".view");

function showView(name) {
  tabButtons.forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  views.forEach((v) => v.classList.toggle("active", v.id === `view-${name}`));
  if (name === "dashboard") loadDashboard();
}

tabButtons.forEach((b) => b.addEventListener("click", () => showView(b.dataset.view)));

let pollTimer = null;

async function loadScenarios() {
  const res = await fetch("/api/scenarios");
  const scenarios = await res.json();
  const grid = document.getElementById("scenario-grid");
  grid.innerHTML = "";
  scenarios.forEach((s) => {
    const el = document.createElement("div");
    el.className = "scenario-card";
    const badgeClass = s.key === "happy_path" ? "happy" : "edge";
    const badgeLabel = s.key === "happy_path" ? "Happy path" : "Edge case";
    el.innerHTML = `
      <span class="badge ${badgeClass}">${badgeLabel}</span>
      <h3>${s.label}</h3>
      <p>${s.description}</p>
    `;
    el.addEventListener("click", () => runScenario(s.key));
    grid.appendChild(el);
  });
}

async function runScenario(key) {
  const res = await fetch(`/api/scenarios/${key}/run`, { method: "POST" });
  const data = await res.json();
  showView("run");
  watchRun(data.run_id);
}

document.getElementById("submit-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const res = await fetch("/api/submit", { method: "POST", body: form });
  const data = await res.json();
  showView("run");
  watchRun(data.run_id);
});

const STAGE_ICON = { passed: "passed", flagged: "flagged", failed: "failed", skipped: "skipped" };
const ROUTING_LABELS = {
  internal_audit: "routed to Internal Audit",
  finance_verification: "on hold — out-of-band verification required",
  awaiting_vendor: "waiting on vendor resubmission",
};

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function renderRun(run) {
  const container = document.getElementById("run-content");
  const isRunning = run.status === "running";
  const awaitingDocs = run.status === "pending_documents";
  const statusKnown = !isRunning;
  const statusLabel = run.status.replace("_", " ");

  let html = `<div class="card decision-card">
    <div style="display:flex;align-items:center;justify-content:space-between;">
      <div>
        <div style="font-size:16px;font-weight:600;">${run.vendor_name}</div>
        <div style="font-size:12px;color:var(--text-dim);margin-top:2px;">
          ${run.scenario_key ? "Scenario: " + run.scenario_key : "Custom submission"}
        </div>
      </div>
      <span class="status-pill ${run.status}">${statusLabel}</span>
    </div>`;

  if (statusKnown) {
    const routingLabel = ROUTING_LABELS[run.routing];
    html += `<p style="margin:14px 0 0;font-size:13px;line-height:1.6;white-space:pre-wrap;">${escapeHtml(run.reason_summary)}
      ${routingLabel ? `<span class="routing-tag">&rarr; ${routingLabel}</span>` : ""}
    </p>`;
  }

  if (awaitingDocs) {
    html += `
      <form id="resubmit-form" style="margin-top:16px;border-top:1px solid var(--panel-border);padding-top:16px;">
        <label style="display:block;font-size:12px;color:var(--text-dim);margin-bottom:6px;">
          Vendor resubmits the missing document
        </label>
        <input type="file" name="document" accept="application/pdf" required
          style="font-size:13px;color:var(--text);" />
        <button class="primary" type="submit" style="margin-left:12px;">Resubmit & continue this run</button>
      </form>`;
  }
  html += `</div>`;

  html += `<div class="card"><ul class="stage-list">`;
  run.stages.forEach((stage) => {
    html += `<li class="stage">
      <div class="stage-dot ${stage.status}"></div>
      <div>
        <div class="stage-name">${stage.stage_name}</div>
        <div class="stage-detail" style="white-space:pre-wrap;">${escapeHtml(stage.detail || "")}</div>
      </div>
    </li>`;
  });
  if (!statusKnown) {
    html += `<li class="stage"><div class="stage-dot" style="background:var(--text-dim);opacity:0.4;animation:pulse 1s infinite;"></div>
      <div class="stage-detail">Running next stage&hellip;</div></li>`;
  }
  html += `</ul></div>`;

  container.innerHTML = html;

  const resubmitForm = document.getElementById("resubmit-form");
  if (resubmitForm) {
    resubmitForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const form = new FormData(e.target);
      await fetch(`/api/runs/${run.id}/resubmit`, { method: "POST", body: form });
      watchRun(run.id);
    });
  }
}

async function watchRun(runId) {
  if (pollTimer) clearInterval(pollTimer);
  const poll = async () => {
    const res = await fetch(`/api/runs/${runId}`);
    const run = await res.json();
    renderRun(run);
    if (run.status !== "running") {
      clearInterval(pollTimer);
      pollTimer = null;
    }
  };
  await poll();
  pollTimer = setInterval(poll, 700);
}

async function loadDashboard() {
  const res = await fetch("/api/runs");
  const runs = await res.json();
  const tbody = document.querySelector("#runs-table tbody");
  tbody.innerHTML = "";
  if (runs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No runs yet.</td></tr>`;
    return;
  }
  runs.forEach((r) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>#${r.id}</td>
      <td>${r.vendor_name}</td>
      <td>${r.scenario_key || "custom"}</td>
      <td><span class="status-pill ${r.status}">${r.status}</span></td>
      <td>${r.routing === "internal_audit" ? "Internal Audit" : "Procurement"}</td>
    `;
    tr.addEventListener("click", () => {
      showView("run");
      watchRun(r.id);
    });
    tbody.appendChild(tr);
  });
}

loadScenarios();
