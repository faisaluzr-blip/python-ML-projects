const $ = (q) => document.querySelector(q);
const $$ = (q) => [...document.querySelectorAll(q)];
let sensorChart, weatherChart, marketChart, latestSnapshot = {};
const alerts = [];

window.addEventListener("load", () => {
  setTimeout(() => $("#loader").classList.add("hidden"), 550);
  initNavigation();
  initCharts();
  bindForms();
  pollSensors();
  loadWeather();
  loadAdmin();
  setInterval(pollSensors, 3500);
  setInterval(loadWeather, 60000);
});

function initNavigation() {
  $$(".nav-link").forEach((btn) => btn.addEventListener("click", () => showSection(btn.dataset.section)));
  $("#menuBtn").addEventListener("click", () => $("#sidebar").classList.toggle("open"));
  $("#themeBtn").addEventListener("click", () => {
    const root = document.documentElement;
    root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
    toast(`${root.dataset.theme} mode enabled`);
  });
  $("#notifyBtn").addEventListener("click", () => $("#notifications").classList.toggle("open"));
  $$(".metric-card").forEach((card) => card.addEventListener("click", () => {
    $("#chartFilter").value = card.dataset.focus === "moisture" ? "moisture" : "all";
    toast(`Focused analytics: ${card.dataset.focus}`);
  }));
  $$(".map button").forEach((btn) => btn.addEventListener("click", () => {
    $$(".map button").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    $("#zoneInfo").textContent = `Zone ${btn.dataset.zone}: moisture ${latestSnapshot.soil_moisture || "--"}%, crop health ${latestSnapshot.crop_health || "--"}%, valve status optimized.`;
  }));
}

function showSection(id) {
  $$(".nav-link").forEach((b) => b.classList.toggle("active", b.dataset.section === id));
  $$(".page-section").forEach((s) => s.classList.toggle("active", s.id === id));
  $("#sidebar").classList.remove("open");
}

function initCharts() {
  const grid = "rgba(160,255,210,.1)";
  sensorChart = new Chart($("#sensorChart"), {
    type: "line",
    data: { labels: [], datasets: [
      ds("Moisture", "#38f2a2"), ds("Temperature", "#35c9ff"), ds("Humidity", "#ffd166")
    ]},
    options: chartOptions(grid)
  });
  weatherChart = new Chart($("#weatherChart"), {
    type: "bar",
    data: { labels: [], datasets: [ds("Rain %", "#35c9ff", "bar"), ds("Temp C", "#38f2a2", "line")] },
    options: chartOptions(grid)
  });
  marketChart = new Chart($("#marketChart"), {
    type: "line",
    data: { labels: [], datasets: [ds("Predicted price", "#38f2a2")] },
    options: chartOptions(grid)
  });
}

function ds(label, color, type = "line") {
  return { label, type, data: [], borderColor: color, backgroundColor: color + "33", fill: true, tension: .42, pointRadius: 3 };
}

function chartOptions(grid) {
  return { responsive: true, interaction: { mode: "index", intersect: false }, plugins: { legend: { labels: { color: getTextColor() } } }, scales: { x: { ticks: { color: getTextColor() }, grid: { color: grid } }, y: { ticks: { color: getTextColor() }, grid: { color: grid } } } };
}

function getTextColor() { return getComputedStyle(document.documentElement).getPropertyValue("--text").trim(); }

async function pollSensors() {
  const data = await api("/api/sensors");
  latestSnapshot = data.snapshot;
  animateNumber("#moistureVal", latestSnapshot.soil_moisture, "%");
  animateNumber("#healthVal", latestSnapshot.crop_health, "%");
  animateNumber("#waterVal", latestSnapshot.water_usage, " L");
  animateNumber("#yieldVal", latestSnapshot.yield_forecast, " t/ha");
  updateMeter(latestSnapshot.soil_moisture);
  if (data.alerts.length) data.alerts.forEach(addAlert);
  const now = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  pushChart(sensorChart, now, [latestSnapshot.soil_moisture, latestSnapshot.temperature, latestSnapshot.humidity], 24);
}

function animateNumber(selector, value, suffix) {
  const el = $(selector);
  el.textContent = `${value}${suffix}`;
}

function pushChart(chart, label, values, max = 20) {
  chart.data.labels.push(label);
  values.forEach((v, i) => chart.data.datasets[i].data.push(v));
  if (chart.data.labels.length > max) {
    chart.data.labels.shift();
    chart.data.datasets.forEach((d) => d.data.shift());
  }
  chart.update("none");
}

function addAlert(alert) {
  alerts.unshift({ ...alert, time: new Date().toLocaleTimeString() });
  if (alerts.length > 8) alerts.pop();
  $("#alertDot").classList.add("on");
  renderAlerts();
  toast(alert.title);
}

function renderAlerts() {
  $("#alertList").innerHTML = alerts.map((a) => `<div class="alert-item ${a.severity}"><b>${a.title}</b><p>${a.message}</p><small>${a.time}</small></div>`).join("");
}

function bindForms() {
  $("#weatherBtn").addEventListener("click", loadWeather);
  $("#soilForm").addEventListener("submit", submitSoil);
  $("#cropForm").addEventListener("submit", submitCrop);
  $("#marketForm").addEventListener("submit", submitMarket);
  $("#irrigationBtn").addEventListener("click", runIrrigation);
  $("#chatBtn").addEventListener("click", sendChat);
  $("#chatText").addEventListener("keydown", (e) => { if (e.key === "Enter") sendChat(); });
  $("#adminRefresh").addEventListener("click", loadAdmin);
  initDiseaseUpload();
  initVoice();
  submitSoil(new Event("submit"));
  submitCrop(new Event("submit"));
  submitMarket(new Event("submit"));
  addMessage("AI", "Ask me about irrigation, disease prevention, NPK balance, weather risk, or market timing.");
}

function initDiseaseUpload() {
  const drop = $("#dropZone"), input = $("#leafInput"), preview = $("#leafPreview");
  drop.addEventListener("click", () => input.click());
  ["dragenter", "dragover"].forEach((eventName) => drop.addEventListener(eventName, (e) => { e.preventDefault(); drop.classList.add("drag"); }));
  ["dragleave", "drop"].forEach((eventName) => drop.addEventListener(eventName, (e) => { e.preventDefault(); drop.classList.remove("drag"); }));
  drop.addEventListener("drop", (e) => { input.files = e.dataTransfer.files; previewImage(); });
  input.addEventListener("change", previewImage);
  $("#scanBtn").addEventListener("click", scanDisease);
  function previewImage() {
    const file = input.files[0];
    if (!file) return;
    preview.src = URL.createObjectURL(file);
    preview.style.display = "block";
    toast("Leaf image ready for scanning");
  }
}

async function scanDisease() {
  const file = $("#leafInput").files[0];
  if (!file) return toast("Choose a leaf image first");
  const fd = new FormData();
  fd.append("image", file);
  $("#scanLine").classList.add("on");
  const result = await fetch("/api/disease", { method: "POST", body: fd }).then((r) => r.json());
  $("#scanLine").classList.remove("on");
  if (result.error) return toast(result.error);
  $("#diseaseResult").innerHTML = `
    <h3>${result.disease}</h3>
    <div class="big-score">${result.confidence}%</div>
    <p><b>Status:</b> ${result.status}</p>
    <p>${result.treatment}</p>
    <div class="summary-strip">
      <div class="summary-card"><b>${result.comparison.healthy_index}%</b><span> Healthy index</span></div>
      <div class="summary-card"><b>${result.comparison.stress_index}%</b><span> Stress index</span></div>
      <div class="summary-card"><b>${result.status}</b><span> Classification</span></div>
    </div>`;
}

async function loadWeather() {
  const city = encodeURIComponent($("#cityInput")?.value || "Ludhiana");
  const data = await api(`/api/weather?city=${city}`);
  $("#weatherCards").innerHTML = [
    ["Temperature", `${data.temperature} C`], ["Humidity", `${data.humidity}%`], ["Wind", `${data.wind_speed} m/s`], ["Rain Risk", `${data.rain_probability}%`]
  ].map(([k, v]) => `<div class="weather-card"><span>${k}</span><strong>${v}</strong></div>`).join("") + `<div class="weather-card" style="grid-column:1/-1">${data.recommendation} ${data.live ? "Live API" : "Offline forecast"}</div>`;
  weatherChart.data.labels = data.forecast.map((d) => d.day);
  weatherChart.data.datasets[0].data = data.forecast.map((d) => d.rain_probability);
  weatherChart.data.datasets[1].data = data.forecast.map((d) => d.temperature);
  weatherChart.update();
}

async function submitSoil(e) {
  e.preventDefault();
  const result = await api("/api/soil", formData("#soilForm"), "POST");
  $("#soilResult").innerHTML = `<h3>Soil Health Report</h3><div class="score-ring" style="--score:${result.score}%"><span>${result.score}</span></div><p><b>Fertility:</b> ${result.fertility} · ${result.confidence}% confidence</p><p>${result.recommendation}</p><p>${result.irrigation}</p>`;
}

async function submitCrop(e) {
  e.preventDefault();
  const result = await api("/api/crop-recommendation", formData("#cropForm"), "POST");
  $("#cropCards").innerHTML = result.recommendations.map((r) => `<div class="crop-card"><h4>${r.crop}</h4><strong>${r.probability}%</strong><p>${r.reason}</p></div>`).join("");
}

async function runIrrigation() {
  const data = await api("/api/irrigation", { moisture: latestSnapshot.soil_moisture || 45, crop: $("#irrigationCrop").value, acreage: $("#irrigationAcreage").value }, "POST");
  $("#irrigationResult").innerHTML = `<h3>${data.mode}</h3><div class="big-score">${data.water_required_liters}</div><p>Liters required now</p><p><b>Water saving:</b> ${data.water_saving_percent}%</p><p>${data.alert}</p>`;
}

async function submitMarket(e) {
  e.preventDefault();
  const data = await api("/api/market", formData("#marketForm"), "POST");
  $("#priceSummary").innerHTML = `<div class="summary-card"><b>₹${data.predicted_price}</b><span> per quintal</span></div><div class="summary-card"><b>₹${data.profit_estimate}</b><span> estimated profit</span></div><div class="summary-card"><b>${data.crop}</b><span> selected crop</span></div>`;
  marketChart.data.labels = data.trend.map((d) => d.week);
  marketChart.data.datasets[0].data = data.trend.map((d) => d.price);
  marketChart.update();
}

async function sendChat() {
  const input = $("#chatText");
  const message = input.value.trim();
  if (!message) return;
  addMessage("You", message, true);
  input.value = "";
  addMessage("AI", "Typing...");
  const data = await api("/api/chat", { message, language: $("#chatLang").value }, "POST");
  $("#chatLog").lastElementChild.remove();
  addMessage("AI", data.reply);
}

function addMessage(author, text, user = false) {
  const div = document.createElement("div");
  div.className = `msg ${user ? "user" : ""}`;
  div.innerHTML = `<b>${author}</b><p>${text}</p>`;
  $("#chatLog").appendChild(div);
  $("#chatLog").scrollTop = $("#chatLog").scrollHeight;
}

function initVoice() {
  $("#voiceBtn").addEventListener("click", () => {
    const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Speech) return toast("Voice input is not supported in this browser");
    const rec = new Speech();
    rec.lang = "en-IN";
    rec.onresult = (e) => { $("#chatText").value = e.results[0][0].transcript; sendChat(); };
    rec.start();
  });
}

async function loadAdmin() {
  const data = await api("/api/admin");
  $("#adminStats").innerHTML = [
    ["Farmers", data.farmers.length], ["Sensor Events", data.system.sensor_events], ["Models", data.system.model_status], ["Latency", `${data.system.api_latency_ms} ms`]
  ].map(([k, v]) => `<div class="metric-card glass"><span>${k}</span><strong>${v}</strong></div>`).join("");
  $("#farmersTable").innerHTML = `<table><thead><tr><th>Name</th><th>Location</th><th>Crop</th><th>Acreage</th><th>Status</th></tr></thead><tbody>${data.farmers.map((f) => `<tr><td>${f.name}</td><td>${f.location}</td><td>${f.crop}</td><td>${f.acreage}</td><td>${f.status}</td></tr>`).join("")}</tbody></table>`;
}

function updateMeter(value) {
  const deg = -82 + (Math.max(0, Math.min(100, value)) / 100) * 164;
  $("#moistureNeedle").style.transform = `rotate(${deg}deg)`;
  $("#meterText").textContent = `${value}%`;
}

function formData(selector) {
  return Object.fromEntries(new FormData($(selector)).entries());
}

async function api(url, body, method = "GET") {
  const options = { method, headers: {} };
  if (body) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function toast(text) {
  const el = $("#toast");
  el.textContent = text;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2300);
}
