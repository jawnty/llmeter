const fmt = (n) => (n == null ? "—" : n.toLocaleString());
const fmtCost = (n) => (n == null ? "—" : "$" + (n).toFixed(4));
const esc = (value) => String(value ?? "").replace(/[<>&"']/g, (c) => ({
  "<": "&lt;",
  ">": "&gt;",
  "&": "&amp;",
  "\"": "&quot;",
  "'": "&#39;",
}[c]));
const fmtTime = (iso) => {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
};

async function loadToday() {
  const r = await fetch("/api/today");
  const d = await r.json();
  document.getElementById("day").textContent = d.day;
  document.getElementById("total-tokens").textContent = fmt(d.totals.total_tokens);
  document.getElementById("total-turns").textContent = `${fmt(d.totals.turns)} turns`;
  document.getElementById("total-cost").textContent = fmtCost(d.totals.cost_usd);
  document.getElementById("claude-tokens").textContent = fmt(d.totals.claude_tokens);
  document.getElementById("codex-tokens").textContent = fmt(d.totals.codex_tokens);
  drawChart(d.series);
}

function drawChart(series) {
  const w = 1200, h = 160, pad = 24;
  const max = Math.max(1, ...series.map((s) => s.total_tokens));
  const barW = (w - pad * 2) / 24;
  const bars = series.map((s, i) => {
    const x = pad + i * barW + 2;
    const bh = (s.total_tokens / max) * (h - pad * 2);
    const y = h - pad - bh;
    const title = `${s.label}:00 — ${s.total_tokens.toLocaleString()} tokens, ${s.turns} turns`;
    return `<rect class="bar" x="${x}" y="${y}" width="${barW - 4}" height="${bh}"><title>${title}</title></rect>
            <text x="${x + (barW-4)/2}" y="${h - pad + 12}" text-anchor="middle">${s.hour}</text>`;
  }).join("");
  document.getElementById("chart").innerHTML =
    `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none">${bars}</svg>`;
}

async function loadSessions() {
  const r = await fetch("/api/sessions");
  const d = await r.json();
  const tbody = document.querySelector("#sessions tbody");
  if (!d.sessions.length) {
    tbody.innerHTML = `<tr><td colspan="8" class="muted" style="text-align:center;padding:24px">No sessions yet today.</td></tr>`;
    return;
  }
  tbody.innerHTML = d.sessions.map((s) => {
    const prompt = s.opening_prompt ? esc(s.opening_prompt.replace(/\s+/g, " ").slice(0, 200)) : `<span class="muted">(no opening prompt captured)</span>`;
    const side = s.is_sidechain ? `<span class="badge side">subagent</span>` : "";
    return `<tr data-id="${s.id}">
      <td>${fmtTime(s.first_ts)}</td>
      <td class="src"><span class="badge ${esc(s.source)}">${esc(s.source)}</span>${side}</td>
      <td>${s.project ? esc(s.project) : "<span class='muted'>—</span>"}</td>
      <td class="prompt" title="${esc(s.opening_prompt || "")}">${prompt}</td>
      <td class="num">${fmt(s.total_tokens)}</td>
      <td class="num">${fmt(s.turns)}</td>
      <td class="num">${fmtCost(s.cost_usd)}</td>
      <td><span class="muted">${esc((s.models || "").split(",").filter(Boolean).join(", ") || "—")}</span></td>
    </tr>`;
  }).join("");
  tbody.querySelectorAll("tr").forEach((tr) => {
    tr.addEventListener("click", () => showDetail(tr.dataset.id));
  });
  if (location.hash === "#first-session" && !window.__tokmonOpenedFirstSession) {
    window.__tokmonOpenedFirstSession = true;
    showDetail(d.sessions[0].id);
  }
}

async function showDetail(sid) {
  const r = await fetch(`/api/session/${sid}`);
  const d = await r.json();
  const s = d.session;
  const turns = d.turns.map((t) => `
    <div class="turn-row">
      <span>${fmtTime(t.ts)}</span>
      <span class="muted">${esc(t.model || "")}</span>
      <span></span>
      <span class="num">in ${fmt(t.input_tokens)}</span>
      <span class="num">out ${fmt(t.output_tokens)}</span>
      <span class="num">${fmt(t.total_tokens)}</span>
    </div>`).join("");
  document.getElementById("detail-body").innerHTML = `
    <h3 style="margin-top:0">${esc(s.project || "(unknown project)")} <span class="badge ${esc(s.source)}">${esc(s.source)}</span></h3>
    <div class="muted" style="font-size:12px">${esc(s.cwd || "")}</div>
    <div class="muted" style="font-size:12px">${esc(s.id)}</div>
    <div class="detail-prompt">${esc(s.opening_prompt || "(no opening prompt captured)")}</div>
    <div class="turn-row" style="font-weight:600">
      <span class="h">Time</span><span class="h">Model</span><span></span>
      <span class="h num">Input</span><span class="h num">Output</span><span class="h num">Total</span>
    </div>
    ${turns}
  `;
  document.getElementById("session-detail").showModal();
}

function refreshAll() {
  loadToday();
  loadSessions();
}

let es;
function connectStream() {
  es = new EventSource("/stream");
  const status = document.getElementById("status");
  es.addEventListener("tick", (e) => {
    status.textContent = "live";
    status.className = "status live";
    refreshAll();
  });
  es.addEventListener("ping", () => {
    status.textContent = "live";
    status.className = "status live";
  });
  es.onerror = () => {
    status.textContent = "reconnecting…";
    status.className = "status stale";
    es.close();
    setTimeout(connectStream, 3000);
  };
}

refreshAll();
connectStream();
setInterval(refreshAll, 15000); // periodic refresh as belt-and-suspenders
