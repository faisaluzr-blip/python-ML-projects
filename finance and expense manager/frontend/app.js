const state = { token: localStorage.getItem("token"), user: null, dashboard: null, stream: null };
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const api = async (path, opts = {}) => {
  const headers = opts.body instanceof FormData ? {} : { "Content-Type": "application/json" };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const res = await fetch(path, { ...opts, headers: { ...headers, ...(opts.headers || {}) } });
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Request failed");
  return res.json();
};
const money = (v) => new Intl.NumberFormat(undefined, { style: "currency", currency: state.user?.currency || "USD", maximumFractionDigits: 0 }).format(v || 0);
const toast = (msg) => { $("#toast").textContent = msg; $("#toast").classList.add("show"); setTimeout(() => $("#toast").classList.remove("show"), 2600); };
const today = () => new Date().toISOString().slice(0, 10);

function setSession(payload) {
  state.token = payload.access_token;
  state.user = payload.user;
  localStorage.setItem("token", state.token);
  $("#authPanel").classList.add("hidden");
  $("#appView").classList.remove("hidden");
  $("#welcome").textContent = `Welcome, ${state.user.name}`;
  initLiveStream();
  refreshAll();
}

async function boot() {
  $("[name=occurred_on]").value = today();
  $("#goalForm [name=deadline]").value = new Date(Date.now() + 15552e6).toISOString().slice(0, 10);
  if (!state.token) return;
  try {
    state.user = await api("/api/auth/me");
    setSession({ access_token: state.token, user: state.user });
  } catch {
    localStorage.removeItem("token");
  }
}

async function refreshAll() {
  const [dash, txs, goals, reminders] = await Promise.all([
    api("/api/dashboard"),
    api("/api/transactions"),
    api("/api/goals"),
    api("/api/reminders"),
  ]);
  state.dashboard = dash;
  renderDashboard(dash);
  renderTransactions(txs.transactions);
  renderAutomation(dash.budgets, goals.goals, reminders.reminders);
}

function renderDashboard(d) {
  animateNumber($("#income"), d.income, money);
  animateNumber($("#expense"), d.expense, money);
  animateNumber($("#net"), d.net, money);
  animateNumber($("#healthScore"), d.health_score, (v) => Math.round(v));
  $("#healthRing").parentElement.style.setProperty("--score", `${d.health_score * 3.6}deg`);
  drawLineChart($("#cashflowChart"), d.monthly, ["income", "expense"], ["#3ee8b5", "#ff5e7a"]);
  drawLineChart($("#forecastChart"), d.forecast.map(x => ({ month: x.month, predicted_expense: x.predicted_expense })), ["predicted_expense"], ["#5b8cff"]);
  drawSpark($("#incomeSpark"), d.monthly.map(x => x.income), "#3ee8b5");
  drawSpark($("#expenseSpark"), d.monthly.map(x => x.expense), "#ff5e7a");
  drawSpark($("#netSpark"), d.monthly.map(x => x.income - x.expense), "#5b8cff");
  const maxCat = Math.max(...d.top_categories.map(x => x.amount), 1);
  $("#categoryBars").innerHTML = d.top_categories.map(x => `
    <div class="bar-row"><div class="bar-meta"><span>${x.category}</span><strong>${money(x.amount)}</strong></div>
    <div class="bar-track"><span style="width:${Math.max(8, x.amount / maxCat * 100)}%"></span></div></div>`).join("");
  $("#alerts").innerHTML = d.alerts.length ? d.alerts.map(a => `<div class="feed-item">${a.message}</div>`).join("") : `<div class="feed-item">No overspending alerts. Budgets are stable.</div>`;
  $("#anomalies").innerHTML = d.anomalies.length ? d.anomalies.map(tx => `<div class="row"><span>${tx.occurred_on}</span><strong>${tx.merchant}</strong><span>${tx.category}</span><span>${money(tx.amount)}</span><span>${tx.risk_score}% risk</span></div>`).join("") : `<div class="feed-item">No high-risk anomaly detected.</div>`;
}

function renderTransactions(items) {
  $("#txTable").innerHTML = items.map(tx => `<div class="row"><span>${tx.occurred_on}</span><strong>${tx.merchant || tx.description}</strong><span>${tx.category}</span><span>${tx.kind === "income" ? "+" : "-"}${money(tx.amount)}</span><button class="danger small" data-delete="${tx.id}">Delete</button></div>`).join("");
}

function renderAutomation(budgets, goals, reminders) {
  $("#budgetList").innerHTML = budgets.map(b => `<div class="feed-item"><strong>${b.category}</strong><br>${money(b.limit_amount)} ${b.period}</div>`).join("");
  $("#goalList").innerHTML = goals.map(g => {
    const pct = Math.min(100, Math.round(g.saved_amount / g.target_amount * 100));
    return `<div class="feed-item"><strong>${g.name}</strong><br>${money(g.saved_amount)} of ${money(g.target_amount)} by ${g.deadline}<div class="bar-track"><span style="width:${pct}%"></span></div></div>`;
  }).join("");
  $("#reminderList").innerHTML = reminders.map(r => `<div class="feed-item"><strong>${r.name}</strong><br>${money(r.amount)} due day ${r.due_day}</div>`).join("");
}

function animateNumber(el, target, format) {
  const start = Number(el.dataset.value || 0);
  const end = Number(target || 0);
  const t0 = performance.now();
  el.dataset.value = end;
  requestAnimationFrame(function tick(t) {
    const p = Math.min(1, (t - t0) / 650);
    el.textContent = format(start + (end - start) * (1 - Math.pow(1 - p, 3)));
    if (p < 1) requestAnimationFrame(tick);
  });
}

function setupCanvas(canvas) {
  const rect = canvas.getBoundingClientRect();
  const scale = window.devicePixelRatio || 1;
  canvas.width = rect.width * scale;
  canvas.height = rect.height * scale;
  const ctx = canvas.getContext("2d");
  ctx.setTransform(scale, 0, 0, scale, 0, 0);
  return { ctx, w: rect.width, h: rect.height };
}

function drawLineChart(canvas, rows, keys, colors) {
  const { ctx, w, h } = setupCanvas(canvas);
  ctx.clearRect(0, 0, w, h);
  ctx.strokeStyle = "rgba(255,255,255,.12)";
  ctx.lineWidth = 1;
  for (let i = 0; i < 5; i++) { ctx.beginPath(); ctx.moveTo(0, i * h / 4); ctx.lineTo(w, i * h / 4); ctx.stroke(); }
  const values = rows.flatMap(r => keys.map(k => Number(r[k] || 0)));
  const max = Math.max(...values, 1);
  keys.forEach((key, ki) => {
    ctx.beginPath();
    ctx.lineWidth = 3;
    ctx.strokeStyle = colors[ki];
    rows.forEach((r, i) => {
      const x = rows.length === 1 ? w / 2 : i / (rows.length - 1) * (w - 24) + 12;
      const y = h - 18 - (Number(r[key] || 0) / max) * (h - 38);
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    });
    ctx.stroke();
  });
}

function drawSpark(canvas, values, color) {
  const { ctx, w, h } = setupCanvas(canvas);
  const max = Math.max(...values, 1);
  ctx.clearRect(0, 0, w, h);
  ctx.beginPath();
  values.forEach((v, i) => {
    const x = values.length === 1 ? w / 2 : i / (values.length - 1) * w;
    const y = h - (v / max) * (h - 8) - 4;
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.stroke();
}

function initLiveStream() {
  if (state.stream) state.stream.close();
  state.stream = new EventSource(`/api/stream?token=${encodeURIComponent(state.token)}`);
  state.stream.onmessage = (event) => {
    const live = JSON.parse(event.data);
    $("#healthScore").textContent = live.health_score;
    $("#healthRing").parentElement.style.setProperty("--score", `${live.health_score * 3.6}deg`);
  };
  state.stream.onerror = () => state.stream?.close();
}

$("#loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target));
  try { setSession(await api("/api/auth/login", { method: "POST", body: JSON.stringify(data) })); } catch (err) { toast(err.message); }
});
$("#signupForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target));
  try { setSession(await api("/api/auth/signup", { method: "POST", body: JSON.stringify(data) })); } catch (err) { toast(err.message); }
});
$("#logoutBtn").addEventListener("click", () => { localStorage.removeItem("token"); location.reload(); });
$("#themeToggle").addEventListener("click", () => document.body.classList.toggle("light"));
$$("nav button").forEach(btn => btn.addEventListener("click", () => {
  $$("nav button").forEach(b => b.classList.remove("active"));
  $$(".tab").forEach(t => t.classList.remove("active"));
  btn.classList.add("active");
  $(`#${btn.dataset.tab}`).classList.add("active");
  if (btn.dataset.tab === "admin") loadAdmin();
}));
$("#txForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const data = Object.fromEntries(new FormData(e.target));
  data.amount = Number(data.amount);
  if (!data.category) delete data.category;
  try { await api("/api/transactions", { method: "POST", body: JSON.stringify(data) }); e.target.reset(); e.target.occurred_on.value = today(); toast("Transaction added with AI enrichment"); refreshAll(); } catch (err) { toast(err.message); }
});
$("#txTable").addEventListener("click", async (e) => {
  const id = e.target.dataset.delete;
  if (!id) return;
  await api(`/api/transactions/${id}`, { method: "DELETE" });
  refreshAll();
});
$("#scanBtn").addEventListener("click", async () => {
  const file = $("#receiptFile").files[0];
  if (!file) return toast("Choose a receipt file first");
  const form = new FormData();
  form.append("file", file);
  const res = await api("/api/ocr/receipt", { method: "POST", body: form });
  $("#scanResult").textContent = JSON.stringify(res.scan, null, 2);
});
$("#micBtn").addEventListener("click", () => {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) return toast("Speech recognition is not available in this browser");
  const rec = new Recognition();
  rec.onresult = (e) => $("#voiceText").value = e.results[0][0].transcript;
  rec.start();
});
$("#voiceAddBtn").addEventListener("click", async () => {
  const transcript = $("#voiceText").value.trim();
  if (!transcript) return toast("Enter or dictate a transaction");
  await api("/api/transactions/voice", { method: "POST", body: JSON.stringify({ transcript }) });
  $("#voiceText").value = "";
  refreshAll();
});
$("#budgetForm").addEventListener("submit", submitSimple("/api/budgets", "Budget saved"));
$("#goalForm").addEventListener("submit", submitSimple("/api/goals", "Goal added"));
$("#reminderForm").addEventListener("submit", submitSimple("/api/reminders", "Reminder added"));
function submitSimple(path, msg) {
  return async (e) => {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.target));
    Object.keys(data).forEach(k => { if (!Number.isNaN(Number(data[k])) && data[k] !== "") data[k] = Number(data[k]); });
    await api(path, { method: "POST", body: JSON.stringify(data) });
    e.target.reset();
    toast(msg);
    refreshAll();
  };
}
$$("[data-export]").forEach(btn => btn.addEventListener("click", () => {
  window.open(`/api/export/${btn.dataset.export}?token=${encodeURIComponent(state.token)}`, "_blank");
}));
$("#chatForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = new FormData(e.target).get("message");
  $("#chatLog").insertAdjacentHTML("beforeend", `<div class="msg user">${message}</div>`);
  e.target.reset();
  const res = await api("/api/assistant", { method: "POST", body: JSON.stringify({ message }) });
  $("#chatLog").insertAdjacentHTML("beforeend", `<div class="msg">${res.reply}</div>`);
});
async function loadAdmin() {
  try {
    const data = await api("/api/admin/overview");
    $("#adminStats").innerHTML = Object.entries(data).map(([k, v]) => `<article class="metric glass"><span>${k.replaceAll("_", " ")}</span><strong>${v}</strong></article>`).join("");
  } catch (err) {
    $("#adminStats").innerHTML = `<div class="feed-item">${err.message}</div>`;
  }
}
window.addEventListener("resize", () => state.dashboard && renderDashboard(state.dashboard));
boot();
