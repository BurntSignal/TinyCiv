const $ = (id) => document.getElementById(id);

const VISIT_REFRESH_AFTER_MS = 5 * 60 * 1000;
let hiddenAt = null;

function number(value) {
  return new Intl.NumberFormat().format(value);
}

function metric(value) {
  return `${Math.round(value)}%`;
}

function setConnectionStatus(online) {
  const el = $("connection-status");
  if (!el) return;
  el.textContent = online ? "● LIVE" : "● ARCHIVE OFFLINE";
  el.classList.toggle("offline", !online);
}

function renderState(state) {
  $("civ-name").textContent = state.name;
  $("year").textContent = number(state.year);
  $("era").textContent = state.era.toUpperCase();
  $("population").textContent = number(state.population);
  $("food").textContent = metric(state.metrics.food);
  $("health").textContent = metric(state.metrics.health);
  $("morale").textContent = metric(state.metrics.morale);
  $("knowledge").textContent = metric(state.metrics.knowledge);
  $("stability").textContent = metric(state.metrics.stability);
  $("civ-summary").textContent =
    `${state.era}. Population ${number(state.population)}. The world continues without you.`;

  const chronicle = $("chronicle");
  chronicle.innerHTML = "";
  for (const event of state.chronicle) {
    const row = document.createElement("div");
    row.className = `entry ${event.major ? "major" : ""}`;
    const year = document.createElement("div");
    year.className = "entry-year";
    year.textContent = `YR ${event.year}`;
    const text = document.createElement("p");
    text.textContent = event.text;
    row.append(year, text);
    chronicle.appendChild(row);
  }
}

function renderVisit(report) {
  $("visit-headline").textContent = report.headline;
  const box = $("visit-events");
  box.innerHTML = "";

  if (!report.events.length) {
    const item = document.createElement("div");
    item.className = "visit-event";
    item.textContent = "The chronicle records nothing extraordinary.";
    box.appendChild(item);
    return;
  }

  if (report.omitted_count > 0) {
    const omitted = document.createElement("div");
    omitted.className = "visit-event muted-event";
    omitted.textContent = `${report.omitted_count} earlier chronicle ${report.omitted_count === 1 ? "entry was" : "entries were"} recorded while you were away.`;
    box.appendChild(omitted);
  }

  for (const event of report.events) {
    const item = document.createElement("div");
    item.className = "visit-event";
    item.textContent = `Year ${event.year}: ${event.text}`;
    box.appendChild(item);
  }
}

async function getJSON(url, options = {}) {
  const response = await fetch(url, { cache: "no-store", ...options });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

async function initialLoad() {
  try {
    const payload = await getJSON("api/visit");
    renderVisit(payload.report);
    renderState(payload.state);
    setConnectionStatus(true);
  } catch (error) {
    setConnectionStatus(false);
    $("visit-headline").textContent = "The archive cannot be reached right now.";
    console.error(error);
  }
}

async function refreshState() {
  try {
    renderState(await getJSON("api/state"));
    setConnectionStatus(true);
  } catch (error) {
    setConnectionStatus(false);
    console.error(error);
  }
}

$("nuke-button").addEventListener("click", async () => {
  if (!confirm("This permanently erases the current TinyCiv world and founds a new civilization. Continue?")) return;
  if (!confirm("Last chance. There is no undo. Nuke this civilization?")) return;

  const button = $("nuke-button");
  button.disabled = true;
  button.textContent = "Erasing world...";
  try {
    await getJSON("api/nuke", { method: "POST" });
    window.location.reload();
  } catch (error) {
    alert(`TinyCiv could not reset: ${error.message}`);
    button.disabled = false;
    button.textContent = "☢ Nuke civilization & begin again";
  }
});

window.addEventListener("online", refreshState);
window.addEventListener("offline", () => setConnectionStatus(false));

document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    hiddenAt = Date.now();
    return;
  }

  const awayFor = hiddenAt ? Date.now() - hiddenAt : 0;
  hiddenAt = null;
  if (awayFor >= VISIT_REFRESH_AFTER_MS) {
    initialLoad();
  } else {
    refreshState();
  }
});

if (window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true) {
  document.documentElement.classList.add("standalone");
}

if ("serviceWorker" in navigator && window.isSecureContext) {
  navigator.serviceWorker.register("sw.js").catch(console.error);
}

initialLoad();
setInterval(refreshState, 60_000);
