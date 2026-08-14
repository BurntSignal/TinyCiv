const $ = (id) => document.getElementById(id);

const VISIT_REFRESH_AFTER_MS = 5 * 60 * 1000;
const CHRONICLE_PAGE_SIZE = 12;
let hiddenAt = null;
let visitBaseline = null;
let chroniclePage = 1;
let chronicleOrder = "desc";

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

function renderDelta(id, current, baseline) {
  const el = $(`${id}-delta`);
  if (!el) return;

  if (baseline === null || baseline === undefined) {
    el.hidden = true;
    el.textContent = "";
    return;
  }

  const delta = Math.round(current) - Math.round(baseline);
  el.hidden = false;
  el.classList.remove("up", "down", "same");

  if (delta > 0) {
    el.textContent = `+${number(delta)}`;
    el.classList.add("up");
  } else if (delta < 0) {
    el.textContent = `−${number(Math.abs(delta))}`;
    el.classList.add("down");
  } else {
    el.textContent = "±0";
    el.classList.add("same");
  }

  el.title = "Change since your previous visit";
}

function renderChronicle(events) {
  const chronicle = $("chronicle");
  chronicle.innerHTML = "";

  if (!events.length) {
    const empty = document.createElement("div");
    empty.className = "chronicle-empty";
    empty.textContent = "The chronicle is waiting for its first entry.";
    chronicle.appendChild(empty);
    return;
  }

  for (const event of events) {
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

function pageButton(label, page, { active = false, disabled = false, ariaLabel = "" } = {}) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `page-button${active ? " active" : ""}`;
  button.textContent = label;
  button.disabled = disabled;
  if (ariaLabel) button.setAttribute("aria-label", ariaLabel);
  if (!disabled && !active) {
    button.addEventListener("click", () => loadChroniclePage(page));
  }
  return button;
}

function renderPagination(meta) {
  const nav = $("chronicle-pages");
  nav.innerHTML = "";

  const totalPages = Math.max(1, meta?.total_pages || 1);
  chroniclePage = Math.max(1, Math.min(meta?.page || chroniclePage, totalPages));
  chronicleOrder = meta?.order === "asc" ? "asc" : "desc";

  $("sort-desc").classList.toggle("active", chronicleOrder === "desc");
  $("sort-asc").classList.toggle("active", chronicleOrder === "asc");

  if (totalPages <= 1) return;

  nav.appendChild(pageButton("«", 1, {
    disabled: chroniclePage === 1,
    ariaLabel: "First page",
  }));
  nav.appendChild(pageButton("‹", chroniclePage - 1, {
    disabled: chroniclePage === 1,
    ariaLabel: "Previous page",
  }));

  const candidates = new Set([1, totalPages, chroniclePage]);
  for (let offset = -2; offset <= 2; offset += 1) {
    const page = chroniclePage + offset;
    if (page >= 1 && page <= totalPages) candidates.add(page);
  }
  const pages = [...candidates].sort((a, b) => a - b);

  let previous = 0;
  for (const page of pages) {
    if (previous && page - previous > 1) {
      const gap = document.createElement("span");
      gap.className = "page-gap";
      gap.textContent = "…";
      nav.appendChild(gap);
    }
    nav.appendChild(pageButton(String(page), page, { active: page === chroniclePage }));
    previous = page;
  }

  nav.appendChild(pageButton("›", chroniclePage + 1, {
    disabled: chroniclePage === totalPages,
    ariaLabel: "Next page",
  }));
  nav.appendChild(pageButton("»", totalPages, {
    disabled: chroniclePage === totalPages,
    ariaLabel: "Last page",
  }));
}

function renderState(state) {
  $("civ-name").textContent = state.name;
  $("year").textContent = number(state.year);
  $("era").textContent = state.era.toUpperCase();
  $("population").textContent = number(state.population);
  $("food").textContent = metric(state.metrics.food);
  $("health").textContent = metric(state.metrics.health);
  $("morale").textContent = metric(state.metrics.morale);
  $("knowledge").textContent = number(state.metrics.knowledge);
  $("stability").textContent = metric(state.metrics.stability);
  $("civ-summary").textContent =
    `${state.era}. Population ${number(state.population)}. The world continues without you.`;

  renderDelta("population", state.population, visitBaseline?.population);
  renderDelta("food", state.metrics.food, visitBaseline?.food);
  renderDelta("health", state.metrics.health, visitBaseline?.health);
  renderDelta("morale", state.metrics.morale, visitBaseline?.morale);
  renderDelta("knowledge", state.metrics.knowledge, visitBaseline?.knowledge);
  renderDelta("stability", state.metrics.stability, visitBaseline?.stability);

  renderChronicle(state.chronicle || []);
  renderPagination(state.chronicle_pagination);
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

async function saveNotificationSettings() {
  const enabled = $("notifications-enabled").checked;
  const notificationEntity = $("notification-target").value;
  const status = $("notification-status");
  status.className = "notification-status muted";
  status.textContent = "Saving observer notification settings…";
  try {
    const payload = await getJSON("api/notifications", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        enabled,
        notification_entity: notificationEntity,
      }),
    });
    renderNotificationSettings(payload);
  } catch (error) {
    status.className = "notification-status warn";
    status.textContent = `Could not save notification settings: ${error.message}`;
  }
}

function renderNotificationSettings(payload) {
  const enabled = $("notifications-enabled");
  const select = $("notification-target");
  const test = $("notification-test");
  const status = $("notification-status");

  enabled.checked = payload.enabled !== false;
  select.innerHTML = "";

  const empty = document.createElement("option");
  empty.value = "";
  if (!payload.supervisor_available) {
    empty.textContent = "Home Assistant API unavailable";
  } else if (!payload.targets?.length) {
    empty.textContent = "No notification targets found";
  } else {
    empty.textContent = "Choose a notification target…";
  }
  select.appendChild(empty);

  for (const target of payload.targets || []) {
    const option = document.createElement("option");
    option.value = target.entity_id;
    option.textContent = target.available === false
      ? `${target.name} — unavailable`
      : target.name;
    option.disabled = target.available === false;
    select.appendChild(option);
  }

  if (payload.notification_entity) {
    const savedExists = [...select.options].some((option) => option.value === payload.notification_entity);
    if (!savedExists) {
      const missing = document.createElement("option");
      missing.value = payload.notification_entity;
      missing.textContent = `${payload.notification_entity} — missing`;
      select.appendChild(missing);
    }
    select.value = payload.notification_entity;
  }

  select.disabled = !enabled.checked || !payload.supervisor_available || !(payload.targets || []).length;
  test.disabled = !enabled.checked || !select.value;

  status.className = "notification-status muted";
  if (!enabled.checked) {
    status.textContent = "Chronicle notifications are off.";
  } else if (!payload.supervisor_available) {
    status.classList.add("warn");
    status.textContent = "TinyCiv cannot reach the Home Assistant notification API.";
  } else if (!payload.targets?.length) {
    status.classList.add("warn");
    status.textContent = "No Home Assistant notify entities were found. The Companion App may need notifications enabled.";
  } else if (select.value) {
    status.classList.add("good");
    status.textContent = `Armed. Chronicle alerts will be delivered to ${select.options[select.selectedIndex].textContent}.`;
  } else {
    status.classList.add("warn");
    status.textContent = "Choose where TinyCiv should send Chronicle alerts.";
  }
}

async function loadNotificationSettings() {
  const status = $("notification-status");
  try {
    renderNotificationSettings(await getJSON("api/notifications"));
  } catch (error) {
    status.className = "notification-status warn";
    status.textContent = `Could not load notification settings: ${error.message}`;
  }
}

function stateURL(page = chroniclePage, order = chronicleOrder) {
  const params = new URLSearchParams({
    chronicle_page: String(page),
    chronicle_order: order,
    page_size: String(CHRONICLE_PAGE_SIZE),
  });
  return `api/state?${params.toString()}`;
}

async function initialLoad() {
  try {
    chroniclePage = 1;
    chronicleOrder = "desc";
    const payload = await getJSON("api/visit");
    visitBaseline = payload.report.metric_baseline || null;
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
    renderState(await getJSON(stateURL()));
    setConnectionStatus(true);
  } catch (error) {
    setConnectionStatus(false);
    console.error(error);
  }
}

async function loadChroniclePage(page) {
  chroniclePage = page;
  await refreshState();
}

async function setChronicleOrder(order) {
  chronicleOrder = order === "asc" ? "asc" : "desc";
  chroniclePage = 1;
  await refreshState();
}

$("sort-desc").addEventListener("click", () => setChronicleOrder("desc"));
$("sort-asc").addEventListener("click", () => setChronicleOrder("asc"));

$("notifications-enabled").addEventListener("change", saveNotificationSettings);
$("notification-target").addEventListener("change", saveNotificationSettings);
$("notification-test").addEventListener("click", async () => {
  const button = $("notification-test");
  const status = $("notification-status");
  button.disabled = true;
  status.className = "notification-status muted";
  status.textContent = "Sending a test notification…";
  try {
    await getJSON("api/notifications/test", { method: "POST" });
    status.className = "notification-status good";
    status.textContent = "Test sent. Check your device.";
  } catch (error) {
    status.className = "notification-status warn";
    status.textContent = "The test could not be delivered. Choose an available notification target and try again.";
  } finally {
    button.disabled = !$("notifications-enabled").checked || !$("notification-target").value;
  }
});

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
loadNotificationSettings();
setInterval(refreshState, 60_000);
