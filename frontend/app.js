const tabButtons = document.querySelectorAll(".tab-btn");
const views = document.querySelectorAll(".view");

function showView(name) {
  tabButtons.forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  views.forEach((v) => v.classList.toggle("active", v.id === `view-${name}`));
  if (name === "dashboard") loadDashboard();
}

tabButtons.forEach((b) => b.addEventListener("click", () => showView(b.dataset.view)));

let pollTimer = null;

// Category -> accent color, purely cosmetic grouping for the scenario cards.
const CATEGORY = {
  happy_path: { color: "#2dd4a7", bg: "rgba(45,212,167,0.14)", label: "Happy path" },
  prompt_injection: { color: "#a78bfa", bg: "rgba(167,139,250,0.14)", label: "AI security" },
  pdf_forensics: { color: "#f97316", bg: "rgba(249,115,22,0.14)", label: "Document forensics" },
  ghost_vendor: { color: "#fb5a6a", bg: "rgba(251,90,106,0.14)", label: "Insider fraud" },
  homoglyph: { color: "#ec4899", bg: "rgba(236,72,153,0.14)", label: "Impersonation" },
  cin_mismatch: { color: "#60a5fa", bg: "rgba(96,165,250,0.14)", label: "Identity check" },
  proprietorship_mismatch: { color: "#60a5fa", bg: "rgba(96,165,250,0.14)", label: "Identity check" },
  tax_identity_mismatch: { color: "#60a5fa", bg: "rgba(96,165,250,0.14)", label: "Identity check" },
  gstin_typo: { color: "#60a5fa", bg: "rgba(96,165,250,0.14)", label: "Identity check" },
  bank_change_attack: { color: "#fb5a6a", bg: "rgba(251,90,106,0.14)", label: "Insider fraud" },
  incomplete_submission: { color: "#2dd4bf", bg: "rgba(45,212,191,0.14)", label: "Workflow" },
};

const STAGE_GLYPH = { passed: "✓", flagged: "⚑", failed: "✕", skipped: "–", incomplete: "⚑" };

const ROUTING_LABELS = {
  internal_audit: "routed to Internal Audit",
  finance_verification: "on hold — out-of-band verification required",
  awaiting_vendor: "waiting on vendor resubmission",
};

const ROUTING_TABLE_LABELS = {
  internal_audit: "Internal Audit",
  finance_verification: "Finance Verification",
  awaiting_vendor: "Awaiting Vendor",
  procurement: "Procurement",
};

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

async function loadScenarios() {
  const res = await fetch("/api/scenarios");
  const scenarios = await res.json();
  const grid = document.getElementById("scenario-grid");
  grid.innerHTML = "";
  scenarios.forEach((s) => {
    const cat = CATEGORY[s.key] || { color: "#7c6cf6", bg: "rgba(124,108,246,0.14)", label: "Edge case" };
    const isHappy = s.key === "happy_path";
    const el = document.createElement("div");
    el.className = "scenario-card";
    el.style.setProperty("--cat-color", cat.color);
    el.style.setProperty("--cat-bg", cat.bg);
    el.innerHTML = `
      <span class="badge ${isHappy ? "happy" : "edge"}">${cat.label}</span>
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

function renderRun(run) {
  const container = document.getElementById("run-content");
  const isRunning = run.status === "running";
  const awaitingDocs = run.status === "pending_documents";
  const statusKnown = !isRunning;
  const statusLabel = run.status.replace("_", " ");

  let html = `<div class="card decision-card">
    <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;">
      <div>
        <div style="font-size:17px;font-weight:700;letter-spacing:-0.01em;">${escapeHtml(run.vendor_name)}</div>
        <div style="font-size:12px;color:var(--text-dim);margin-top:3px;">
          ${run.scenario_key ? "Scenario: " + run.scenario_key : "Custom submission"}
        </div>
      </div>
      <span class="status-pill ${run.status}">${statusLabel}</span>
    </div>`;

  if (statusKnown) {
    const routingLabel = ROUTING_LABELS[run.routing];
    html += `<p style="margin:16px 0 0;font-size:13.5px;line-height:1.7;white-space:pre-wrap;">${escapeHtml(run.reason_summary)}
      ${routingLabel ? `<span class="routing-tag">&rarr; ${routingLabel}</span>` : ""}
    </p>`;
  }

  if (awaitingDocs) {
    html += `
      <form id="resubmit-form" style="margin-top:18px;border-top:1px solid var(--panel-border);padding-top:18px;">
        <label style="display:block;font-size:11.5px;color:var(--text-dim);text-transform:uppercase;letter-spacing:0.03em;font-weight:600;margin-bottom:8px;">
          Vendor resubmits the missing document
        </label>
        <div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap;">
          <input type="file" name="document" accept="application/pdf" required
            style="font-size:13px;color:var(--text);" />
          <button class="primary" type="submit" style="margin-top:0;">Resubmit &amp; continue this run</button>
        </div>
      </form>`;
  }
  html += `</div>`;

  html += `<div class="card"><ul class="stage-list">`;
  run.stages.forEach((stage) => {
    html += `<li class="stage">
      <div class="stage-badge ${stage.status}">${STAGE_GLYPH[stage.status] || "•"}</div>
      <div style="flex:1;min-width:0;">
        <div class="stage-name">${escapeHtml(stage.stage_name)}</div>
        <div class="stage-detail">${escapeHtml(stage.detail || "")}</div>
      </div>
    </li>`;
  });
  if (!statusKnown) {
    html += `<li class="stage">
      <div class="stage-badge" style="background:rgba(139,147,173,0.14);color:var(--text-dim);animation:livepulse 1.2s infinite;">&hellip;</div>
      <div class="stage-detail" style="font-family:var(--font-sans);">Running next stage&hellip;</div>
    </li>`;
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

function renderStatTiles(runs) {
  const counts = { total: runs.length, approved: 0, pending: 0, rejected: 0, awaiting: 0 };
  runs.forEach((r) => {
    if (r.status === "approved") counts.approved++;
    else if (r.status === "rejected") counts.rejected++;
    else if (r.status === "pending_documents") counts.awaiting++;
    else if (r.status === "pending") counts.pending++;
  });
  const tiles = [
    { label: "Total runs", value: counts.total },
    { label: "Approved", value: counts.approved },
    { label: "Pending", value: counts.pending },
    { label: "Rejected", value: counts.rejected },
    { label: "Awaiting vendor", value: counts.awaiting },
  ];
  document.getElementById("stat-grid").innerHTML = tiles
    .map((t) => `<div class="stat-tile"><div class="stat-value">${t.value}</div><div class="stat-label">${t.label}</div></div>`)
    .join("");
}

async function loadDashboard() {
  const res = await fetch("/api/runs");
  const runs = await res.json();
  renderStatTiles(runs);
  const tbody = document.querySelector("#runs-table tbody");
  tbody.innerHTML = "";
  if (runs.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No runs yet.</td></tr>`;
    return;
  }
  runs.forEach((r) => {
    const tr = document.createElement("tr");
    const statusLabel = r.status.replace("_", " ");
    tr.innerHTML = `
      <td>#${r.id}</td>
      <td>${escapeHtml(r.vendor_name)}</td>
      <td>${r.scenario_key || "custom"}</td>
      <td><span class="status-pill ${r.status}">${statusLabel}</span></td>
      <td>${ROUTING_TABLE_LABELS[r.routing] || r.routing}</td>
    `;
    tr.addEventListener("click", () => {
      showView("run");
      watchRun(r.id);
    });
    tbody.appendChild(tr);
  });
}

loadScenarios();
