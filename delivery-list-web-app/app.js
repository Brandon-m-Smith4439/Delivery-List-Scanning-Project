const STORAGE_KEY = "delivery-list-scanner-demo-v1";
const STATIONS_KEY = "delivery-list-scanner-stations-v1";
const DEFAULT_STATIONS = ["Airport Rd", "Indian Trail", "Greenville", "Customer Pickup"];

const state = {
  page: "home",
  meta: null,
  lists: [],
  stations: DEFAULT_STATIONS.slice(),
  activeListId: "",
  items: [],
  recent: [],
  errors: [],
  selectedId: null,
  filter: "all",
  search: "",
  pageIndex: 1,
  pageSize: 25,
  homeSearch: "",
  homeStageFilter: "all",
  baySearch: "",
  bayStatusFilter: "all",
  bayLayout: null,
  bays: [],
  activeSessions: [],
  adminUsers: [],
  backend: false,
  authenticated: false,
  user: null,
  permissions: [],
  eventsWired: false,
  pollTimer: null,
  lastScan: null,
};

const els = {
  loginPanel: document.getElementById("loginPanel"),
  loginForm: document.getElementById("loginForm"),
  loginUsername: document.getElementById("loginUsername"),
  loginPassword: document.getElementById("loginPassword"),
  loginError: document.getElementById("loginError"),
  signedInUser: document.getElementById("signedInUser"),
  backendStatus: document.getElementById("backendStatus"),
  logoutBtn: document.getElementById("logoutBtn"),
  headerGlobalSearchInput: document.getElementById("headerGlobalSearchInput"),
  headerGlobalSearchBtn: document.getElementById("headerGlobalSearchBtn"),
  headerGlobalSearchResults: document.getElementById("headerGlobalSearchResults"),

  homePage: document.getElementById("homePage"),
  homeWelcome: document.getElementById("homeWelcome"),
  overviewStats: document.getElementById("overviewStats"),
  homeUserCard: document.getElementById("homeUserCard"),
  homeRecentLists: document.getElementById("homeRecentLists"),
  homeActivity: document.getElementById("homeActivity"),
  homeListSearch: document.getElementById("homeListSearch"),
  homeStageFilter: document.getElementById("homeStageFilter"),
  homeListGrid: document.getElementById("homeListGrid"),
  homeListCount: document.getElementById("homeListCount"),

  scanPage: document.getElementById("scanPage"),
  pageTitle: document.getElementById("pageTitle"),
  stageSubtitle: document.getElementById("stageSubtitle"),
  stageHeading: document.getElementById("stageHeading"),
  scannerName: document.getElementById("scannerName"),
  deliveryListSelect: document.getElementById("deliveryListSelect"),
  stationSelect: document.getElementById("stationSelect"),
  operatorInput: document.getElementById("operatorInput"),
  progressText: document.getElementById("progressText"),
  progressFill: document.getElementById("progressFill"),
  searchInput: document.getElementById("searchInput"),
  scanForm: document.getElementById("scanForm"),
  scanInput: document.getElementById("scanInput"),
  listRows: document.getElementById("listRows"),
  recentRows: document.getElementById("recentRows"),
  mobileListCards: document.getElementById("mobileListCards"),
  lastCard: document.getElementById("lastCard"),
  lastScanTime: document.getElementById("lastScanTime"),
  lastJob: document.getElementById("lastJob"),
  lastOrder: document.getElementById("lastOrder"),
  lastItem: document.getElementById("lastItem"),
  lastQty: document.getElementById("lastQty"),
  lastDims: document.getElementById("lastDims"),
  lastCustomer: document.getElementById("lastCustomer"),
  totalItemsText: document.getElementById("totalItemsText"),
  countAll: document.getElementById("countAll"),
  countRemaining: document.getElementById("countRemaining"),
  countPartial: document.getElementById("countPartial"),
  countComplete: document.getElementById("countComplete"),
  countErrors: document.getElementById("countErrors"),
  remainingQty: document.getElementById("remainingQty"),
  partialQty: document.getElementById("partialQty"),
  completeQty: document.getElementById("completeQty"),
  errorQty: document.getElementById("errorQty"),
  remainingPct: document.getElementById("remainingPct"),
  partialPct: document.getElementById("partialPct"),
  completePct: document.getElementById("completePct"),
  needsReviewList: document.getElementById("needsReviewList"),
  noticeList: document.getElementById("noticeList"),
  needsReviewCount: document.getElementById("needsReviewCount"),
  noticeCount: document.getElementById("noticeCount"),
  pageSize: document.getElementById("pageSize"),
  scanPagerTop: document.getElementById("scanPagerTop"),
  scanPagerBottom: document.getElementById("scanPagerBottom"),
  printBtn: document.getElementById("printBtn"),
  exportBtn: document.getElementById("exportBtn"),
  undoBtn: document.getElementById("undoBtn"),
  resetBtn: document.getElementById("resetBtn"),
  loadExampleBtn: document.getElementById("loadExampleBtn"),

  bayMapPage: document.getElementById("bayMapPage"),
  bayOverviewStats: document.getElementById("bayOverviewStats"),
  bayMapSearch: document.getElementById("bayMapSearch"),
  bayStatusFilter: document.getElementById("bayStatusFilter"),
  bayCheckBtn: document.getElementById("bayCheckBtn"),
  indianTrailSummary: document.getElementById("indianTrailSummary"),
  bayMapCanvas: document.getElementById("bayMapCanvas"),
  bayMapUnmapped: document.getElementById("bayMapUnmapped"),

  adminPage: document.getElementById("adminPage"),
  adminSummary: document.getElementById("adminSummary"),
  importBtn: document.getElementById("importBtn"),
  importFile: document.getElementById("importFile"),
  importPreviewBox: document.getElementById("importPreviewBox"),
  createUserForm: document.getElementById("createUserForm"),
  newUserName: document.getElementById("newUserName"),
  newUserDisplay: document.getElementById("newUserDisplay"),
  newUserPassword: document.getElementById("newUserPassword"),
  newUserRole: document.getElementById("newUserRole"),
  adminUsers: document.getElementById("adminUsers"),
  newStationInput: document.getElementById("newStationInput"),
  addStationBtn: document.getElementById("addStationBtn"),
  adminStations: document.getElementById("adminStations"),
  manualEditSearch: document.getElementById("manualEditSearch"),
  manualEditSearchBtn: document.getElementById("manualEditSearchBtn"),
  manualEditResults: document.getElementById("manualEditResults"),
  exceptionCenter: document.getElementById("exceptionCenter"),
  activeSessions: document.getElementById("activeSessions"),
};

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function pad(value, length) {
  return String(value).padStart(length, "0");
}

function canonicalBarcode(order, item) {
  return `T200${pad(order, 6)}${pad(item, 3)}000`;
}

function formatDisplayDate(value) {
  const parts = String(value || "").split("-").map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) return String(value || "");
  return `${parts[1]}/${parts[2]}/${parts[0]}`;
}

function uniqueText(values) {
  const seen = new Set();
  const result = [];
  for (const value of values) {
    const clean = String(value || "").trim();
    if (!clean || seen.has(clean.toLowerCase())) continue;
    seen.add(clean.toLowerCase());
    result.push(clean);
  }
  return result;
}

function hasPermission(permission) {
  if (!state.backend) return true;
  return state.permissions.includes(permission);
}

function hasAnyPermission(permissions) {
  return permissions.some((permission) => hasPermission(permission));
}

function setControlAllowed(element, allowed, hide = false) {
  if (!element) return;
  element.disabled = !allowed;
  if (hide) element.hidden = !allowed;
  element.classList.toggle("is-disabled", !allowed);
}

function requestContext() {
  return {
    user: state.user?.username || els.operatorInput?.value || "Scanner",
    station: els.stationSelect?.value || state.meta?.scanner || "",
  };
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    cache: "no-store",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const text = await response.text();
    let message = text || `Request failed: ${response.status}`;
    try {
      const payload = JSON.parse(text);
      message = payload.error || payload.message || message;
    } catch {
      // Keep raw text when the server does not return JSON.
    }
    if (response.status === 401 && state.backend && url !== "/api/login") {
      state.authenticated = false;
      state.user = null;
      state.permissions = [];
      showLogin("Please sign in to continue.");
    }
    throw new Error(message);
  }
  return response.json();
}

async function detectBackend() {
  try {
    const health = await fetchJson("/api/health");
    state.backend = Boolean(health.ok);
  } catch {
    state.backend = false;
  }
}

function showLogin(message = "") {
  if (!els.loginPanel) return;
  els.loginPanel.hidden = false;
  document.querySelector(".app")?.setAttribute("aria-hidden", "true");
  if (els.loginError) els.loginError.textContent = message;
  window.setTimeout(() => (els.loginPassword || els.loginUsername)?.focus(), 30);
}

function hideLogin() {
  if (!els.loginPanel) return;
  els.loginPanel.hidden = true;
  document.querySelector(".app")?.removeAttribute("aria-hidden");
  if (els.loginError) els.loginError.textContent = "";
}

async function loadSession() {
  const payload = await fetchJson("/api/session");
  state.authenticated = Boolean(payload.authenticated);
  state.user = payload.user || null;
  state.permissions = state.user?.permissions || [];
  if (state.authenticated) {
    hideLogin();
    if (els.operatorInput) els.operatorInput.value = state.user.displayName || state.user.username || "Scanner";
  }
  return payload;
}

async function login(username, password) {
  const payload = await fetchJson("/api/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  state.authenticated = true;
  state.user = payload.user;
  state.permissions = payload.user?.permissions || [];
  hideLogin();
  if (els.loginPassword) els.loginPassword.value = "";
  if (els.operatorInput) els.operatorInput.value = state.user.displayName || state.user.username || "Scanner";
}

async function logout() {
  if (state.backend) {
    await fetchJson("/api/logout", { method: "POST", body: JSON.stringify({}) });
  }
  state.authenticated = false;
  state.user = null;
  state.permissions = [];
  stopPolling();
  showLogin("Signed out.");
}

function cleanBarcode(value) {
  return String(value || "")
    .replace(/\*/g, "")
    .replace(/[\r\n]/g, "")
    .trim()
    .split("")
    .filter((ch) => /[0-9a-z]/i.test(ch))
    .join("")
    .toUpperCase();
}

function digitsOnly(value) {
  return String(value || "").replace(/\D/g, "");
}

function isCpuItem(item) {
  const route = String(item.route || "").trim().toUpperCase();
  const text = [item.route, item.job, item.customer, item.product, item.processState, item.queueState].join(" ");
  return route === "CPU" || /\bCPU\b/i.test(text);
}

function filterItemsForProfile(items, profile) {
  return profile === "cpu" ? items.filter(isCpuItem) : items.slice();
}

function cloneItems(items) {
  const seen = new Map();
  return (items || []).map((item, index) => {
    const baseId = item.id || `${item.order}-${item.item}`;
    const count = seen.get(baseId) || 0;
    seen.set(baseId, count + 1);
    return {
      ...item,
      id: count ? `${baseId}-${count + 1}` : baseId,
      sourceId: baseId,
      lineIndex: index + 1,
      scanned: Number(item.scanned || 0),
      qty: Number(item.qty || 0),
      lastError: item.lastError || "",
    };
  });
}

function createDemoLists(payload) {
  const baseItems = payload.items || [];
  return [
    {
      id: "2026-04-01-staging-airport",
      label: "4/1/2026 - Staging - Airport Rd",
      deliveryDate: payload.deliveryDate,
      stage: "Staging - Airport Rd",
      scanner: "Airport Rd",
      items: cloneItems(filterItemsForProfile(baseItems, "all")),
    },
    {
      id: "2026-04-01-outbound-airport",
      label: "4/1/2026 - Outbound - Airport Rd",
      deliveryDate: payload.deliveryDate,
      stage: "Outbound - Airport Rd",
      scanner: "Airport Rd",
      items: cloneItems(filterItemsForProfile(baseItems, "all")),
    },
    {
      id: "2026-04-01-inbound-indian-trail",
      label: "4/1/2026 - Inbound - Indian Trail",
      deliveryDate: payload.deliveryDate,
      stage: "Inbound - Indian Trail",
      scanner: "Indian Trail",
      items: cloneItems(filterItemsForProfile(baseItems, "all")),
    },
    {
      id: "2026-04-01-customer-pickup",
      label: "4/1/2026 - Customer Pickup",
      deliveryDate: payload.deliveryDate,
      stage: "Customer Pickup",
      scanner: "Customer Pickup",
      items: cloneItems(filterItemsForProfile(baseItems, "cpu")),
    },
  ];
}

function loadLocalStations() {
  try {
    const saved = JSON.parse(localStorage.getItem(STATIONS_KEY) || "[]");
    state.stations = uniqueText([...DEFAULT_STATIONS, ...saved]);
  } catch {
    state.stations = DEFAULT_STATIONS.slice();
  }
}

function saveLocalStations() {
  localStorage.setItem(STATIONS_KEY, JSON.stringify(state.stations));
}

function renderStationOptions(preferredStation = "") {
  if (!els.stationSelect) return;
  const current = preferredStation || els.stationSelect.value || state.meta?.scanner || DEFAULT_STATIONS[0];
  state.stations = uniqueText([...DEFAULT_STATIONS, ...state.stations, current]);
  els.stationSelect.innerHTML = state.stations
    .map((station) => `<option value="${escapeHtml(station)}">${escapeHtml(station)}</option>`)
    .join("");
  els.stationSelect.value = state.stations.includes(current) ? current : state.stations[0];
}

async function loadStations() {
  if (state.backend) {
    const payload = await fetchJson("/api/stations");
    state.stations = uniqueText([...DEFAULT_STATIONS, ...(payload.stations || [])]);
  } else {
    loadLocalStations();
  }
  renderStationOptions(state.meta?.scanner);
}

async function addStationFromInput() {
  const name = els.newStationInput?.value.trim() || "";
  if (!name) {
    els.newStationInput?.focus();
    return;
  }
  if (state.backend) {
    const payload = await fetchJson("/api/stations", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
    state.stations = uniqueText([...DEFAULT_STATIONS, ...(payload.stations || [])]);
  } else {
    state.stations = uniqueText([...state.stations, name]);
    saveLocalStations();
  }
  if (els.newStationInput) els.newStationInput.value = "";
  renderStationOptions(name);
  renderAdminStations();
}

async function removeStation(name) {
  if (!state.backend) return;
  const payload = await fetchJson("/api/stations/remove", {
    method: "POST",
    body: JSON.stringify({ name }),
  });
  state.stations = uniqueText([...DEFAULT_STATIONS, ...(payload.stations || [])]);
  renderStationOptions();
  renderAdminStations();
}

function applyBackendPayload(payload) {
  state.meta = payload.meta;
  state.activeListId = payload.meta.id;
  state.items = cloneItems(payload.items || []);
  state.recent = payload.recent || [];
  state.errors = payload.errors || [];
  state.lastScan = payload.lastScan || state.recent[0] || null;
  state.selectedId = state.lastScan?.item?.id || state.selectedId;
  renderStationOptions(payload.meta.scanner);
}

async function loadDeliveryLists(preferredListId = "") {
  if (state.backend) {
    const payload = await fetchJson("/api/delivery-lists");
    state.lists = payload.lists || [];
  }
  renderHome();
  renderDeliveryListSelect();
  if (preferredListId) {
    await activateList(preferredListId, false);
  }
}

function setActiveList(listId) {
  const nextList = state.lists.find((list) => list.id === listId) || state.lists[0];
  if (!nextList) return;
  state.activeListId = nextList.id;
  state.meta = {
    deliveryDate: nextList.deliveryDate,
    stage: nextList.stage,
    scanner: nextList.scanner,
    label: nextList.label,
  };
  state.items = cloneItems(nextList.items || []);
  state.recent = [];
  state.errors = [];
  state.selectedId = null;
  state.lastScan = null;
  restoreState();
  renderStationOptions(nextList.scanner);
}

async function activateList(listId, navigate = true) {
  if (!listId) return;
  if (state.backend) {
    const payload = await fetchJson(`/api/delivery-lists/${encodeURIComponent(listId)}`);
    applyBackendPayload(payload);
  } else {
    setActiveList(listId);
  }
  state.pageIndex = 1;
  renderScanPage();
  if (navigate) showPage("scan");
  els.scanInput?.focus();
}

function storageKey() {
  return `${STORAGE_KEY}-${state.activeListId || "default"}`;
}

function saveState() {
  if (state.backend) return;
  const payload = {
    scanned: Object.fromEntries(state.items.map((item) => [item.id, item.scanned])),
    recent: state.recent,
    errors: state.errors,
    selectedId: state.selectedId,
    lastScan: state.lastScan,
  };
  localStorage.setItem(storageKey(), JSON.stringify(payload));
}

function restoreState() {
  if (state.backend) return;
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey()) || "{}");
    if (saved.scanned) {
      for (const item of state.items) {
        item.scanned = Math.min(Number(saved.scanned[item.id] || 0), item.qty);
      }
    }
    state.recent = Array.isArray(saved.recent) ? saved.recent.slice(0, 30) : [];
    state.errors = Array.isArray(saved.errors) ? saved.errors.slice(0, 30) : [];
    state.selectedId = saved.selectedId || null;
    state.lastScan = saved.lastScan || null;
  } catch {
    localStorage.removeItem(storageKey());
  }
}

function itemStatus(item) {
  if (item.scanned >= item.qty) return "complete";
  if (item.scanned > 0) return "partial";
  return "remaining";
}

function getStats(items = state.items, errors = state.errors) {
  const totalQty = items.reduce((sum, item) => sum + Number(item.qty || 0), 0);
  const scannedQty = items.reduce((sum, item) => sum + Math.min(Number(item.scanned || 0), Number(item.qty || 0)), 0);
  const remainingQty = Math.max(totalQty - scannedQty, 0);
  const partialItems = items.filter((item) => itemStatus(item) === "partial").length;
  const completeItems = items.filter((item) => itemStatus(item) === "complete").length;
  const remainingItems = items.filter((item) => itemStatus(item) === "remaining").length;
  const percent = totalQty ? (scannedQty / totalQty) * 100 : 0;
  return { totalQty, scannedQty, remainingQty, partialItems, completeItems, remainingItems, percent, errorCount: errors.length };
}

function filteredItems() {
  const search = state.search.trim().toLowerCase();
  const errorItemIds = new Set((state.errors || []).map((entry) => entry.item?.id).filter(Boolean));
  return state.items.filter((item) => {
    const status = itemStatus(item);
    const matchesFilter =
      state.filter === "all" ||
      state.filter === status ||
      (state.filter === "errors" && errorItemIds.has(item.id));
    if (!matchesFilter) return false;
    if (!search) return true;
    const haystack = [item.order, item.item, item.job, item.customer, item.dimensions, item.product, item.route, item.barcode]
      .join(" ")
      .toLowerCase();
    return haystack.includes(search);
  });
}

function getPagedItems() {
  const rows = filteredItems();
  const totalPages = Math.max(1, Math.ceil(rows.length / state.pageSize));
  state.pageIndex = Math.min(Math.max(state.pageIndex, 1), totalPages);
  const start = (state.pageIndex - 1) * state.pageSize;
  return { rows, pageRows: rows.slice(start, start + state.pageSize), totalPages };
}

function stageVerb() {
  const stage = String(state.meta?.stage || "").toLowerCase();
  if (stage.includes("indian trail") || stage.includes("inbound")) return "Received";
  if (stage.includes("outbound")) return "Outbound";
  if (stage.includes("customer pickup")) return "CPU";
  return "Staged";
}

function renderProcessState(item) {
  return `${stageVerb()}: ${item.scanned}/${item.qty}`;
}

function renderCounts() {
  const stats = getStats();
  const totalItems = state.items.length;
  if (els.countAll) els.countAll.textContent = `(${totalItems})`;
  if (els.countRemaining) els.countRemaining.textContent = `(${stats.remainingItems})`;
  if (els.countPartial) els.countPartial.textContent = `(${stats.partialItems})`;
  if (els.countComplete) els.countComplete.textContent = `(${stats.completeItems})`;
  if (els.countErrors) els.countErrors.textContent = `(${stats.errorCount})`;
  if (els.totalItemsText) els.totalItemsText.textContent = `${totalItems} total items`;
  if (els.progressText) els.progressText.textContent = `${stageVerb()} Qty: ${stats.scannedQty}/${stats.totalQty} - ${stats.percent.toFixed(1)}% Complete`;
  if (els.progressFill) els.progressFill.style.width = `${Math.min(stats.percent, 100)}%`;
  if (els.remainingQty) els.remainingQty.textContent = String(stats.remainingQty);
  if (els.partialQty) els.partialQty.textContent = String(stats.partialItems);
  if (els.completeQty) els.completeQty.textContent = String(stats.completeItems);
  if (els.errorQty) els.errorQty.textContent = String(stats.errorCount);
  if (els.remainingPct) els.remainingPct.textContent = `${(100 - stats.percent).toFixed(1)}%`;
  if (els.partialPct) els.partialPct.textContent = `${stats.totalQty ? ((stats.partialItems / Math.max(state.items.length, 1)) * 100).toFixed(1) : "0.0"}%`;
  if (els.completePct) els.completePct.textContent = `${stats.percent.toFixed(1)}%`;
}

function renderPagers(totalRows, totalPages) {
  const render = () => {
    const buttons = [];
    buttons.push(`<button type="button" data-page-action="prev" ${state.pageIndex <= 1 ? "disabled" : ""}>&lt;</button>`);
    const pages = [];
    for (let page = 1; page <= totalPages; page += 1) {
      if (page === 1 || page === totalPages || Math.abs(page - state.pageIndex) <= 2) {
        pages.push(page);
      }
    }
    let previous = 0;
    for (const page of pages) {
      if (page - previous > 1) buttons.push("<span>...</span>");
      buttons.push(`<button type="button" data-page-number="${page}" class="${page === state.pageIndex ? "is-active" : ""}">${page}</button>`);
      previous = page;
    }
    buttons.push(`<button type="button" data-page-action="next" ${state.pageIndex >= totalPages ? "disabled" : ""}>&gt;</button>`);
    buttons.push(`<span class="pager-summary">${totalRows} rows</span>`);
    return `<div class="pager">${buttons.join("")}</div>`;
  };
  if (els.scanPagerTop) els.scanPagerTop.innerHTML = render();
  if (els.scanPagerBottom) els.scanPagerBottom.innerHTML = render();
}

function renderTable() {
  if (!els.listRows) return;
  const { rows, pageRows, totalPages } = getPagedItems();
  renderPagers(rows.length, totalPages);
  els.listRows.innerHTML = pageRows.length
    ? pageRows
        .map((item) => {
          const status = itemStatus(item);
          const selected = item.id === state.selectedId;
          const route = item.route ? `<span class="route-tag">${escapeHtml(item.route)}</span>` : "";
          return `
            <tr class="${selected ? "is-selected" : ""} ${status === "complete" ? "is-complete" : ""}" data-id="${escapeHtml(item.id)}">
              <td><span class="job-title">${escapeHtml(item.product || item.job)}</span><span class="job-subtitle">${escapeHtml(item.job)}</span></td>
              <td>${escapeHtml(item.order)}</td>
              <td>${escapeHtml(item.item)}</td>
              <td><span class="qty-pill ${status}">${item.scanned} / ${item.qty}</span></td>
              <td>${escapeHtml(item.dimensions)}</td>
              <td>${escapeHtml(item.customer)}</td>
              <td></td>
              <td>${route}</td>
              <td><span class="process-pill ${status}">${escapeHtml(renderProcessState(item))}</span></td>
            </tr>
          `;
        })
        .join("")
    : `<tr><td colspan="9">No rows match the current filters.</td></tr>`;
}

function renderMobileCards() {
  if (!els.mobileListCards) return;
  const { pageRows } = getPagedItems();
  els.mobileListCards.innerHTML = `
    <div class="section-heading">
      <h3>Delivery List</h3>
      <span>${state.items.length} items</span>
    </div>
    <div class="filter-tabs mobile-tabs">
      <button class="tab ${state.filter === "all" ? "is-active" : ""}" data-filter="all" type="button">All (${state.items.length})</button>
      <button class="tab ${state.filter === "remaining" ? "is-active" : ""}" data-filter="remaining" type="button">Remaining (${getStats().remainingItems})</button>
      <button class="tab ${state.filter === "partial" ? "is-active" : ""}" data-filter="partial" type="button">Partial (${getStats().partialItems})</button>
      <button class="tab ${state.filter === "complete" ? "is-active" : ""}" data-filter="complete" type="button">Complete (${getStats().completeItems})</button>
      <button class="tab ${state.filter === "errors" ? "is-active" : ""}" data-filter="errors" type="button">Review (${state.errors.length})</button>
    </div>
    ${pageRows
      .slice(0, 12)
      .map((item) => {
        const status = itemStatus(item);
        const selected = item.id === state.selectedId;
        const mark = status === "complete" ? "&#10003;" : item.route || "-";
        return `
          <article class="mobile-list-card ${selected ? "is-selected" : ""}" data-id="${escapeHtml(item.id)}">
            <span><small>Order #</small><b>${escapeHtml(item.order)}</b></span>
            <span><small>Item #</small><b>${escapeHtml(item.item)}</b></span>
            <span><small>Qty</small><b><span class="qty-pill ${status}">${item.scanned} / ${item.qty}</span></b></span>
            <span class="dims"><small>Dimensions</small><b>${escapeHtml(item.dimensions)}</b></span>
            <span class="card-status">${mark}</span>
            <span class="card-customer">${escapeHtml(item.customer)}</span>
          </article>
        `;
      })
      .join("")}
  `;
}

function setLastScan(entry) {
  if (!entry || !els.lastCard) return;
  state.lastScan = entry;
  els.lastCard.classList.remove("ok", "error");
  els.lastCard.classList.add(entry.ok ? "ok" : "error");
  if (els.lastScanTime) els.lastScanTime.textContent = entry.ok ? "Just now" : entry.eventType === "duplicate" ? "Notice" : "Needs review";
  if (els.lastJob) els.lastJob.textContent = entry.item ? entry.item.job : entry.message;
  if (els.lastOrder) els.lastOrder.textContent = entry.item ? entry.item.order : "-";
  if (els.lastItem) els.lastItem.textContent = entry.item ? entry.item.item : "-";
  if (els.lastQty) els.lastQty.textContent = entry.item ? String(entry.item.scanned) : "-";
  if (els.lastDims) els.lastDims.textContent = entry.item ? entry.item.dimensions : "-";
  if (els.lastCustomer) els.lastCustomer.textContent = entry.item ? entry.item.customer : "-";
}

function renderLastScan() {
  if (state.lastScan) {
    setLastScan(state.lastScan);
    return;
  }
  els.lastCard?.classList.remove("ok", "error");
  if (els.lastScanTime) els.lastScanTime.textContent = "Waiting";
  if (els.lastJob) els.lastJob.textContent = "No scans yet";
  if (els.lastOrder) els.lastOrder.textContent = "-";
  if (els.lastItem) els.lastItem.textContent = "-";
  if (els.lastQty) els.lastQty.textContent = "-";
  if (els.lastDims) els.lastDims.textContent = "-";
  if (els.lastCustomer) els.lastCustomer.textContent = "-";
}

function renderRecent() {
  if (!els.recentRows) return;
  const rows = state.recent.slice(0, 7);
  els.recentRows.innerHTML = rows.length
    ? rows
        .map((entry) => {
          const item = entry.item;
          const time = new Date(entry.time);
          return `
            <tr class="${entry.ok ? "ok" : "error"}">
              <td>${escapeHtml(entry.barcode)}</td>
              <td>${item ? escapeHtml(item.order) : "-"}</td>
              <td>${item ? escapeHtml(item.item) : "-"}</td>
              <td>${item ? item.scanned : "-"}</td>
              <td>${Number.isNaN(time.getTime()) ? "" : time.toLocaleString()}</td>
              <td><span class="check-dot ${entry.ok ? "" : "error"}">${entry.ok ? "&#10003;" : "!"}</span></td>
            </tr>
          `;
        })
        .join("")
    : `<tr><td colspan="6">No scans yet</td></tr>`;
}

function renderScanMessages() {
  const needsReview = state.errors || [];
  const notices = (state.recent || []).filter((entry) => !entry.ok && entry.eventType !== "error").slice(0, 6);
  if (els.needsReviewCount) els.needsReviewCount.textContent = String(needsReview.length);
  if (els.noticeCount) els.noticeCount.textContent = String(notices.length);
  if (els.needsReviewList) {
    els.needsReviewList.innerHTML = needsReview.length
      ? needsReview
          .slice(0, 6)
          .map((entry) => `<article class="message-card review"><strong>${escapeHtml(entry.message)}</strong><span>${escapeHtml(entry.barcode)} - ${escapeHtml(entry.reason)}</span></article>`)
          .join("")
      : `<article class="message-card ok"><strong>No review items</strong><span>Resolvable scan issues will appear here.</span></article>`;
  }
  if (els.noticeList) {
    els.noticeList.innerHTML = notices.length
      ? notices
          .map((entry) => `<article class="message-card notice"><strong>${escapeHtml(entry.message)}</strong><span>${escapeHtml(entry.reason || entry.barcode)}</span></article>`)
          .join("")
      : `<article class="message-card ok"><strong>No notices</strong><span>Duplicate scans and resolved notices appear here.</span></article>`;
  }
}

function renderMeta() {
  if (!state.meta) return;
  const dateText = formatDisplayDate(state.meta.deliveryDate);
  if (els.pageTitle) els.pageTitle.textContent = `Delivery List for ${dateText}`;
  if (els.stageSubtitle) els.stageSubtitle.textContent = state.meta.stage;
  if (els.stageHeading) els.stageHeading.textContent = state.meta.stage;
  if (els.scannerName) els.scannerName.textContent = state.meta.scanner;
  if (els.backendStatus) {
    els.backendStatus.textContent = state.backend ? "SQLite live" : "Local demo";
    els.backendStatus.classList.toggle("online", state.backend);
  }
  renderDeliveryListSelect();
}

function renderDeliveryListSelect() {
  if (!els.deliveryListSelect) return;
  els.deliveryListSelect.innerHTML = state.lists
    .map((list) => `<option value="${escapeHtml(list.id)}">${escapeHtml(list.label)}</option>`)
    .join("");
  els.deliveryListSelect.value = state.activeListId;
}

function applyPermissionUi() {
  if (els.signedInUser) {
    els.signedInUser.textContent = state.user ? `${state.user.displayName || state.user.username}` : "Demo";
  }
  if (els.logoutBtn) els.logoutBtn.hidden = !state.backend || !state.user;
  document.querySelectorAll("[data-permission-any]").forEach((element) => {
    const permissions = element.dataset.permissionAny.split(",").map((value) => value.trim());
    element.hidden = !hasAnyPermission(permissions);
  });
  const canScan = hasPermission("scan") || hasPermission("indian_trail_receive");
  setControlAllowed(els.scanInput, canScan);
  setControlAllowed(els.exportBtn, hasPermission("export_reports"), true);
  setControlAllowed(els.undoBtn, hasPermission("undo_scan"), true);
  setControlAllowed(els.resetBtn, hasPermission("reset_lists"), true);
  setControlAllowed(els.loadExampleBtn, hasPermission("undo_scan") || hasPermission("view_admin"), true);
  setControlAllowed(els.importBtn, hasPermission("import_delivery_lists"), true);
  setControlAllowed(els.addStationBtn, hasPermission("manage_stations"));
  setControlAllowed(els.newStationInput, hasPermission("manage_stations"));
}

function renderScanPage() {
  renderMeta();
  renderCounts();
  renderTable();
  renderMobileCards();
  renderRecent();
  renderScanMessages();
  renderLastScan();
  applyPermissionUi();
}

function miniStat(label, value, detail = "") {
  return `<div class="mini-stat"><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong>${detail ? `<span>${escapeHtml(detail)}</span>` : ""}</div>`;
}

function filteredDeliveryLists() {
  const search = state.homeSearch.trim().toLowerCase();
  return state.lists.filter((list) => {
    const matchesStage = state.homeStageFilter === "all" || `${list.stage} ${list.scanner}`.toLowerCase().includes(state.homeStageFilter.toLowerCase());
    if (!matchesStage) return false;
    if (!search) return true;
    return [list.label, list.stage, list.scanner, list.deliveryDate].join(" ").toLowerCase().includes(search);
  });
}

function renderHome() {
  if (!els.homePage) return;
  const totalLists = state.lists.length;
  const totalItems = state.lists.reduce((sum, list) => sum + Number(list.itemCount || 0), 0);
  const totalQty = state.lists.reduce((sum, list) => sum + Number(list.totalQty || 0), 0);
  const scannedQty = state.lists.reduce((sum, list) => sum + Number(list.scannedQty || 0), 0);
  const remainingQty = Math.max(totalQty - scannedQty, 0);
  if (els.homeWelcome) {
    els.homeWelcome.textContent = `Signed in as ${state.user?.displayName || state.user?.username || "Demo user"}`;
  }
  if (els.overviewStats) {
    els.overviewStats.innerHTML = [
      miniStat("Delivery Lists", totalLists),
      miniStat("Open Items", totalItems),
      miniStat("Scanned Qty", `${scannedQty}/${totalQty}`),
      miniStat("Remaining Qty", remainingQty),
    ].join("");
  }
  if (els.homeUserCard) {
    els.homeUserCard.innerHTML = `
      <strong>${escapeHtml(state.user?.displayName || state.user?.username || "Demo")}</strong>
      <span>${escapeHtml((state.user?.roles || ["Local Demo"]).join(", "))}</span>
      <small>Stages: ${escapeHtml((state.user?.stageAccess || ["All demo stages"]).join(", "))}</small>
    `;
  }
  const filtered = filteredDeliveryLists();
  if (els.homeListCount) els.homeListCount.textContent = `${filtered.length} lists`;
  if (els.homeListGrid) {
    els.homeListGrid.innerHTML = filtered.length
      ? filtered
          .map((list) => {
            const percent = Number(list.totalQty || 0) ? (Number(list.scannedQty || 0) / Number(list.totalQty || 1)) * 100 : 0;
            return `
              <article class="delivery-list-card" data-open-list="${escapeHtml(list.id)}">
                <div>
                  <strong>${escapeHtml(list.label)}</strong>
                  <span>${escapeHtml(list.stage)} - ${escapeHtml(list.scanner)}</span>
                </div>
                <div class="list-card-progress"><span style="width:${Math.min(percent, 100)}%"></span></div>
                <small>${escapeHtml(list.itemCount || 0)} lines - ${escapeHtml(list.scannedQty || 0)}/${escapeHtml(list.totalQty || 0)} pieces</small>
              </article>
            `;
          })
          .join("")
      : `<div class="admin-empty">No delivery lists match.</div>`;
  }
  if (els.homeRecentLists) {
    els.homeRecentLists.innerHTML = state.lists
      .slice(0, 5)
      .map((list) => `<button type="button" data-open-list="${escapeHtml(list.id)}"><strong>${escapeHtml(list.label)}</strong><span>${escapeHtml(list.stage)}</span></button>`)
      .join("");
  }
  if (els.homeActivity) {
    els.homeActivity.innerHTML = state.recent.length
      ? state.recent.slice(0, 5).map((entry) => `<div><strong>${escapeHtml(entry.message)}</strong><span>${escapeHtml(entry.barcode)}</span></div>`).join("")
      : `<div><strong>Ready</strong><span>Select a list to begin scanning.</span></div>`;
  }
  applyPermissionUi();
}

function showPage(page) {
  if (page === "admin" && !hasAnyPermission(["view_admin", "manage_users", "manage_stations", "edit_delivery_lists"])) page = "home";
  if (page === "bays" && !hasAnyPermission(["view_bays", "view_indian_trail"])) page = "home";
  state.page = page;
  document.body.dataset.page = page;
  document.querySelectorAll(".page-view").forEach((view) => {
    view.hidden = view.id !== `${page === "bays" ? "bayMap" : page}Page`;
  });
  document.querySelectorAll("[data-page-target]").forEach((button) => {
    button.classList.toggle("is-active", button.dataset.pageTarget === page);
  });
  if (page === "home") renderHome();
  if (page === "scan") renderScanPage();
  if (page === "bays") refreshBayMapPage().catch((error) => showInlineError(error.message));
  if (page === "admin") refreshAdminPage().catch((error) => showInlineError(error.message));
  if (page === "scan") els.scanInput?.focus();
}

async function processScan(rawScan) {
  const scanText = rawScan.trim();
  if (!scanText || !state.activeListId) return;
  if (state.backend) {
    const indianTrailReceive =
      hasPermission("indian_trail_receive") &&
      /indian trail/i.test(`${state.meta?.stage || ""} ${els.stationSelect?.value || ""}`);
    if (indianTrailReceive) {
      const result = await fetchJson("/api/indian-trail/receive", {
        method: "POST",
        body: JSON.stringify({ listId: state.activeListId, barcode: scanText, ...requestContext() }),
      });
      await activateList(state.activeListId, false);
      state.lastScan = result.lastScan || state.lastScan;
      renderScanPage();
      void refreshBayMapPage().catch(() => {});
      return;
    }
    const payload = await fetchJson("/api/scans", {
      method: "POST",
      body: JSON.stringify({ listId: state.activeListId, barcode: scanText, ...requestContext() }),
    });
    applyBackendPayload(payload);
    renderScanPage();
    return;
  }
  processLocalScan(scanText);
}

function processLocalScan(scanText) {
  const recovered = recoverScan(scanText);
  const timestamp = new Date().toISOString();
  if (!recovered.ok) {
    const entry = { ok: false, eventType: "error", barcode: scanText, message: "BAD SCAN format", reason: recovered.reason, time: timestamp };
    state.errors.unshift(entry);
    state.recent.unshift(entry);
    state.lastScan = entry;
    saveState();
    renderScanPage();
    return;
  }
  const item = recovered.item;
  if (item.scanned >= item.qty) {
    const entry = { ok: false, eventType: "duplicate", barcode: recovered.barcode, item, message: "Item already complete", reason: "Quantity already scanned", time: timestamp };
    state.recent.unshift(entry);
    state.lastScan = entry;
    saveState();
    renderScanPage();
    return;
  }
  item.scanned += 1;
  state.selectedId = item.id;
  const entry = { ok: true, eventType: "scan", barcode: recovered.barcode, raw: scanText, item, message: recovered.reason, time: timestamp };
  state.recent.unshift(entry);
  state.lastScan = entry;
  saveState();
  renderScanPage();
}

function buildIndexes() {
  const byOrderItem = new Map();
  const bySuffixItem = new Map();
  for (const item of state.items) {
    const orderItemKey = `${Number(item.order)}-${Number(item.item)}`;
    const orderMatches = byOrderItem.get(orderItemKey) || [];
    orderMatches.push(item);
    byOrderItem.set(orderItemKey, orderMatches);
    const suffixKey = `${pad(item.order, 6).slice(-3)}-${Number(item.item)}`;
    const suffixMatches = bySuffixItem.get(suffixKey) || [];
    suffixMatches.push(item);
    bySuffixItem.set(suffixKey, suffixMatches);
  }
  return { byOrderItem, bySuffixItem };
}

function recoverScan(rawScan) {
  const cleanText = cleanBarcode(rawScan);
  const { byOrderItem, bySuffixItem } = buildIndexes();
  if (/^T200\d{12}$/.test(cleanText)) {
    const order = Number(cleanText.slice(4, 10));
    const item = Number(cleanText.slice(10, 13));
    const matches = byOrderItem.get(`${order}-${item}`) || [];
    if (matches.length === 1) return { ok: true, item: matches[0], barcode: cleanText, reason: "Exact label" };
    if (matches.length > 1) return { ok: false, barcode: cleanText, reason: "Ambiguous delivery-list match" };
  }
  const numbers = digitsOnly(cleanText);
  for (let start = 0; start <= numbers.length - 12; start += 1) {
    const windowText = numbers.slice(start, start + 12);
    const order = Number(windowText.slice(0, 6));
    const item = Number(windowText.slice(6, 9));
    const matches = byOrderItem.get(`${order}-${item}`) || [];
    if (matches.length === 1) return { ok: true, item: matches[0], barcode: canonicalBarcode(order, item), reason: "Recovered order/item" };
    if (matches.length > 1) return { ok: false, barcode: canonicalBarcode(order, item), reason: "Ambiguous delivery-list match" };
  }
  for (let start = 0; start <= numbers.length - 9; start += 1) {
    const windowText = numbers.slice(start, start + 9);
    const suffix = windowText.slice(0, 3);
    const itemNumber = Number(windowText.slice(3, 6));
    const matches = bySuffixItem.get(`${suffix}-${itemNumber}`);
    if (matches && matches.length === 1) {
      const match = matches[0];
      return { ok: true, item: match, barcode: canonicalBarcode(match.order, itemNumber), reason: "Recovered suffix/item" };
    }
    if (matches && matches.length > 1) return { ok: false, barcode: cleanText, reason: "Ambiguous delivery-list match" };
  }
  return { ok: false, barcode: cleanText, reason: "No unique delivery-list match" };
}

async function resetState() {
  if (state.backend) {
    const payload = await fetchJson("/api/reset", {
      method: "POST",
      body: JSON.stringify({ listId: state.activeListId, ...requestContext() }),
    });
    applyBackendPayload(payload);
    renderScanPage();
    return;
  }
  for (const item of state.items) item.scanned = 0;
  state.recent = [];
  state.errors = [];
  state.selectedId = null;
  state.lastScan = null;
  saveState();
  renderScanPage();
}

function showInlineError(message, needsReview = false) {
  const entry = { ok: false, eventType: needsReview ? "error" : "notice", barcode: "SYSTEM", message: "System notice", reason: message, time: new Date().toISOString() };
  if (needsReview) state.errors.unshift(entry);
  state.recent.unshift(entry);
  state.lastScan = entry;
  renderScanPage();
}

async function runGlobalSearch() {
  if (!hasPermission("global_search")) return [];
  const query = els.headerGlobalSearchInput?.value.trim() || "";
  if (query.length < 2) {
    renderGlobalSearchResults([]);
    return [];
  }
  const payload = await fetchJson(`/api/search?q=${encodeURIComponent(query)}`);
  renderGlobalSearchResults(payload.results || []);
  return payload.results || [];
}

function renderGlobalSearchResults(results) {
  if (!els.headerGlobalSearchResults) return;
  if (!results.length) {
    els.headerGlobalSearchResults.hidden = true;
    els.headerGlobalSearchResults.innerHTML = "";
    return;
  }
  els.headerGlobalSearchResults.hidden = false;
  els.headerGlobalSearchResults.innerHTML = results
    .slice(0, 8)
    .map(
      (result) => `
        <button type="button" data-open-list="${escapeHtml(result.deliveryListId)}">
          <strong>${escapeHtml(result.order)}-${escapeHtml(result.item)}</strong>
          <span>${escapeHtml(result.customer)} ${result.bay ? `- Bay ${escapeHtml(result.bay)}` : ""}</span>
        </button>
      `,
    )
    .join("");
}

async function refreshBayMapPage() {
  if (!hasAnyPermission(["view_bays", "view_indian_trail"])) return;
  if (state.backend) {
    const [layout, baysPayload, summary] = await Promise.all([
      fetchJson("/api/indian-trail/layout"),
      fetchJson("/api/indian-trail/bays"),
      hasPermission("view_indian_trail") ? fetchJson("/api/indian-trail/summary") : Promise.resolve(null),
    ]);
    state.bayLayout = layout;
    state.bays = baysPayload.bays || [];
    renderIndianTrailSummary(summary);
  } else {
    const response = await fetch("data/indian-trail-bay-layout.json");
    state.bayLayout = await response.json();
    state.bays = (state.bayLayout.bays || []).map((bay) => ({ ...bay, assignedQty: 0, capacityQty: bay.autoAssignable ? 1 : 0, status: bay.autoAssignable ? "Empty" : "ManualHold", assignments: [] }));
  }
  renderBayMapPage();
}

function renderIndianTrailSummary(summary) {
  if (!els.indianTrailSummary) return;
  if (!summary) {
    els.indianTrailSummary.innerHTML = "";
    return;
  }
  els.indianTrailSummary.innerHTML = `
    <div class="mini-stat-grid">
      ${miniStat("Inbound", summary.inboundToday ?? 0, "qty")}
      ${miniStat("Received", summary.receivedQty ?? 0)}
      ${miniStat("Assigned", summary.assignedToBays ?? 0)}
      ${miniStat("Needs Check", summary.needsCheck ?? 0)}
    </div>
  `;
}

function bayMatchesFilter(bay, text) {
  const search = state.baySearch.trim().toLowerCase();
  const status = String(bay?.status || "").toLowerCase();
  const sourceStatus = String(bay?.sourceStatus || "").toLowerCase();
  const matchesStatus =
    state.bayStatusFilter === "all" ||
    (state.bayStatusFilter === "manual" && (!bay?.active || sourceStatus.includes("manual"))) ||
    status.includes(state.bayStatusFilter);
  if (!matchesStatus) return false;
  if (!search) return true;
  return text.toLowerCase().includes(search);
}

function renderBayMapPage() {
  if (!els.bayMapCanvas || !state.bayLayout) return;
  const bayByCode = new Map((state.bays || []).map((bay) => [bay.bayCode, bay]));
  const layout = state.bayLayout;
  const cells = layout.cells || [];
  const maxRow = layout.grid?.maxRow || 180;
  const maxCol = layout.grid?.maxCol || 24;
  if (els.bayMapCanvas) {
    els.bayMapCanvas.style.setProperty("--map-rows", maxRow);
    els.bayMapCanvas.style.setProperty("--map-cols", maxCol);
    els.bayMapCanvas.innerHTML = cells
      .map((cell) => {
        const bayCodes = cell.bayCodes || [];
        const bay = bayCodes.map((code) => bayByCode.get(code)).find(Boolean);
        const label = bay?.displayName || cell.value;
        const status = bay?.status || (bayCodes.length ? "ManualHold" : "");
        const text = [label, status, bay?.mapSection, bay?.bayCategory, ...(bay?.assignments || []).map((a) => `${a.order} ${a.customer}`)].join(" ");
        const dimmed = bayCodes.length && !bayMatchesFilter(bay || { status: "ManualHold", sourceStatus: "ManualHold" }, text);
        const assignment = bay?.assignments?.[0];
        return `
          <div class="map-cell ${escapeHtml(cell.kind)} ${escapeHtml(String(status).toLowerCase())} ${dimmed ? "is-dimmed" : ""}"
               style="grid-row:${cell.row};grid-column:${cell.col};"
               data-bay-code="${escapeHtml(bay?.bayCode || "")}">
            <strong>${escapeHtml(label)}</strong>
            ${assignment ? `<span>${escapeHtml(assignment.order)} ${escapeHtml(assignment.customer || "")}</span>` : cell.kind === "bay" ? `<span>${escapeHtml(status)}</span>` : ""}
          </div>
        `;
      })
      .join("");
  }
  const occupied = state.bays.filter((bay) => Number(bay.assignedQty || 0) > 0).length;
  const empty = state.bays.filter((bay) => bay.status === "Empty").length;
  const manual = state.bays.filter((bay) => !bay.active).length;
  if (els.bayOverviewStats) {
    els.bayOverviewStats.innerHTML = [miniStat("Visible Slots", state.bays.length), miniStat("Occupied", occupied), miniStat("Empty", empty), miniStat("Manual Hold", manual)].join("");
  }
  if (els.bayMapUnmapped) {
    const unmapped = state.bays.filter((bay) => !bay.layoutRow).slice(0, 50);
    els.bayMapUnmapped.innerHTML = unmapped.length
      ? unmapped.map((bay) => `<div><strong>${escapeHtml(bay.displayName || bay.bayCode)}</strong><span>${escapeHtml(bay.mapSection)} - ${escapeHtml(bay.status)}</span></div>`).join("")
      : `<div><strong>All visible</strong><span>Workbook-visible bays are on the map.</span></div>`;
  }
}

async function refreshAdminPage() {
  if (!state.backend) return;
  const requests = [];
  requests.push(hasPermission("view_admin") ? fetchJson("/api/admin/summary") : Promise.resolve(null));
  requests.push(hasPermission("manage_users") ? fetchJson("/api/admin/users") : Promise.resolve(null));
  requests.push(hasPermission("view_active_sessions") ? fetchJson("/api/admin/sessions") : Promise.resolve(null));
  requests.push(hasPermission("view_exceptions") ? fetchJson(`/api/exceptions?listId=${encodeURIComponent(state.activeListId || "")}`) : Promise.resolve(null));
  const [summary, users, sessions, exceptions] = await Promise.all(requests);
  if (summary && els.adminSummary) {
    els.adminSummary.innerHTML = [
      miniStat("Lists", summary.activeDeliveryLists ?? 0),
      miniStat("Line Items", summary.lineItems ?? 0),
      miniStat("Open Review", summary.openExceptions ?? 0),
      miniStat("Active Users", summary.activeUsers ?? 0),
      miniStat("Bays", summary.activeBays ?? 0),
    ].join("");
  }
  state.adminUsers = users?.users || [];
  state.activeSessions = sessions?.sessions || [];
  renderAdminUsers();
  renderAdminStations();
  renderExceptionCenter(exceptions?.exceptions || []);
  renderActiveSessions();
}

function renderAdminUsers() {
  if (!els.adminUsers) return;
  if (!state.adminUsers.length) {
    els.adminUsers.innerHTML = `<div class="admin-empty">No users loaded.</div>`;
    return;
  }
  els.adminUsers.innerHTML = `
    <table>
      <thead><tr><th>User</th><th>Roles</th><th>Stages</th><th>Status</th><th></th></tr></thead>
      <tbody>
        ${state.adminUsers
          .map(
            (user) => `
              <tr>
                <td><strong>${escapeHtml(user.displayName)}</strong><span>${escapeHtml(user.username)}</span></td>
                <td>${escapeHtml((user.roles || []).join(", "))}</td>
                <td>${escapeHtml((user.stageAccess || []).join(", "))}</td>
                <td>${user.active ? "Active" : "Inactive"}</td>
                <td>${user.active && hasPermission("deactivate_users") ? `<button type="button" data-deactivate-user="${escapeHtml(user.username)}">Deactivate</button>` : ""}</td>
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  `;
}

function renderAdminStations() {
  if (!els.adminStations) return;
  els.adminStations.innerHTML = state.stations
    .map((station) => `<div><strong>${escapeHtml(station)}</strong>${hasPermission("remove_stations") && !DEFAULT_STATIONS.includes(station) ? `<button type="button" data-remove-station="${escapeHtml(station)}">Remove</button>` : ""}</div>`)
    .join("");
}

function renderExceptionCenter(exceptions) {
  if (!els.exceptionCenter) return;
  if (!exceptions.length) {
    els.exceptionCenter.innerHTML = `<div class="admin-empty">No open review items.</div>`;
    return;
  }
  els.exceptionCenter.innerHTML = `
    <div class="result-list">
      ${exceptions
        .slice(0, 12)
        .map(
          (entry) => `
            <article class="exception-row">
              <div>
                <strong>${escapeHtml(entry.type)} - ${escapeHtml(entry.status)}</strong>
                <span>${escapeHtml(entry.barcode || "No barcode")} - ${escapeHtml(entry.reason)}</span>
                <small>${escapeHtml(entry.user || "")} ${entry.station ? `at ${escapeHtml(entry.station)}` : ""}</small>
              </div>
              ${hasPermission("resolve_exceptions") && entry.status === "Open" ? `<button type="button" data-resolve-exception="${escapeHtml(entry.id)}">Review</button>` : ""}
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderActiveSessions() {
  if (!els.activeSessions) return;
  els.activeSessions.innerHTML = state.activeSessions.length
    ? state.activeSessions.map((session) => `<div><strong>${escapeHtml(session.displayName)}</strong><span>Last seen ${escapeHtml(session.lastSeenAt)}</span></div>`).join("")
    : `<div><strong>No active sessions</strong><span>Users appear here after login.</span></div>`;
}

async function createUserFromForm() {
  const username = els.newUserName?.value.trim() || "";
  const displayName = els.newUserDisplay?.value.trim() || username;
  const password = els.newUserPassword?.value || "";
  const role = els.newUserRole?.value || "Operator";
  if (!username || !password) throw new Error("Username and password are required");
  await fetchJson("/api/admin/users", {
    method: "POST",
    body: JSON.stringify({ username, displayName, password, roles: [role] }),
  });
  if (els.newUserName) els.newUserName.value = "";
  if (els.newUserDisplay) els.newUserDisplay.value = "";
  if (els.newUserPassword) els.newUserPassword.value = "";
  await refreshAdminPage();
}

async function importDeliveryListFile(file) {
  const text = await file.text();
  const payload = JSON.parse(text);
  if (state.backend) {
    if (hasPermission("preview_import")) {
      const preview = await fetchJson("/api/import/preview", {
        method: "POST",
        body: JSON.stringify({ payload }),
      });
      if (els.importPreviewBox) {
        els.importPreviewBox.innerHTML = `${preview.valid ? "Ready" : "Blocked"}: ${preview.rowCount} rows, ${preview.totalQty} pieces`;
      }
      if (!preview.valid) throw new Error(`Import blocked: ${preview.errors.join("; ")}`);
      if (preview.warnings.length && !window.confirm(`Import preview has warnings:\n${preview.warnings.join("\n")}\n\nContinue?`)) return;
    }
    const result = await fetchJson("/api/import", {
      method: "POST",
      body: JSON.stringify({ payload, fileName: file.name, ...requestContext() }),
    });
    state.lists = result.lists || [];
    await activateList(result.activeListId || state.lists[0]?.id, false);
    renderHome();
    await refreshAdminPage();
  } else {
    state.lists = createDemoLists(payload);
    setActiveList(state.lists[0]?.id);
    renderHome();
  }
}

async function runManualEditSearch() {
  const query = els.manualEditSearch?.value.trim() || "";
  if (query.length < 2) return;
  const payload = await fetchJson(`/api/search?q=${encodeURIComponent(query)}`);
  renderManualEditResults(payload.results || []);
}

function renderManualEditResults(results) {
  if (!els.manualEditResults) return;
  els.manualEditResults.innerHTML = results.length
    ? `
      <table>
        <thead><tr><th>Order</th><th>Customer</th><th>Qty</th><th>Scanned</th><th>Process</th><th></th></tr></thead>
        <tbody>
          ${results
            .slice(0, 20)
            .map(
              (item) => `
                <tr data-edit-row="${escapeHtml(item.lineItemId)}">
                  <td>${escapeHtml(item.order)}-${escapeHtml(item.item)}</td>
                  <td>${escapeHtml(item.customer)}</td>
                  <td><input data-edit-field="qty" type="number" min="0" value="${escapeHtml(item.qty)}"></td>
                  <td><input data-edit-field="scanned" type="number" min="0" value="${escapeHtml(item.scanned)}"></td>
                  <td><input data-edit-field="processState" type="text" value="${escapeHtml(item.bayStatus || "")}"></td>
                  <td><button type="button" data-save-line-item="${escapeHtml(item.lineItemId)}">Save</button></td>
                </tr>
              `,
            )
            .join("")}
        </tbody>
      </table>
    `
    : `<div class="admin-empty">No editable rows found.</div>`;
}

async function saveManualLineItem(lineItemId) {
  const row = document.querySelector(`[data-edit-row="${CSS.escape(lineItemId)}"]`);
  if (!row) return;
  const data = { lineItemId };
  row.querySelectorAll("[data-edit-field]").forEach((input) => {
    data[input.dataset.editField] = input.value;
  });
  const payload = await fetchJson("/api/admin/line-item", {
    method: "POST",
    body: JSON.stringify(data),
  });
  if (payload.meta?.id === state.activeListId) applyBackendPayload(payload);
  renderScanPage();
}

function exportStaticCsv() {
  const header = ["barcode", "order", "item", "qty", "scanned", "remaining", "dimensions", "customer", "route", "job", "product", "suggestedBay"];
  const rows = state.items.map((item) => {
    const row = { ...item, barcode: canonicalBarcode(item.order, item.item), remaining: Math.max(Number(item.qty) - Number(item.scanned), 0) };
    return header.map((key) => JSON.stringify(row[key] ?? "")).join(",");
  });
  const blob = new Blob([[header.join(","), ...rows].join("\n")], { type: "text/csv" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "delivery-list-export.csv";
  link.click();
  URL.revokeObjectURL(url);
}

function startPolling() {
  stopPolling();
  state.pollTimer = window.setInterval(async () => {
    if (!state.backend || state.page !== "scan" || !state.activeListId || document.hidden) return;
    const activeElement = document.activeElement;
    try {
      await activateList(state.activeListId, false);
      if (activeElement === els.scanInput) els.scanInput.focus();
    } catch {
      // Keep polling quiet so scanning is not interrupted.
    }
  }, 8000);
}

function stopPolling() {
  if (state.pollTimer) window.clearInterval(state.pollTimer);
  state.pollTimer = null;
}

async function loadAuthenticatedApp(params = new URLSearchParams(window.location.search)) {
  await loadStations();
  await loadDeliveryLists(params.get("list") || "");
  if (params.get("list")) {
    showPage("scan");
  } else {
    showPage("home");
  }
  startPolling();
}

async function init() {
  wireEvents();
  await detectBackend();
  if (state.backend) {
    await loadSession();
    if (!state.authenticated) {
      showLogin();
      return;
    }
    await loadAuthenticatedApp(new URLSearchParams(window.location.search));
    return;
  }
  loadLocalStations();
  renderStationOptions();
  const response = await fetch("data/sample-delivery-list.json");
  const payload = await response.json();
  state.lists = createDemoLists(payload);
  showPage("home");
}

function wireEvents() {
  if (state.eventsWired) return;
  state.eventsWired = true;

  els.loginForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await login(els.loginUsername?.value || "", els.loginPassword?.value || "");
      await loadAuthenticatedApp();
    } catch (error) {
      if (els.loginError) els.loginError.textContent = error.message;
    }
  });

  els.logoutBtn?.addEventListener("click", () => logout().catch((error) => showInlineError(error.message)));
  els.headerGlobalSearchBtn?.addEventListener("click", () => runGlobalSearch().catch((error) => showInlineError(error.message)));
  els.headerGlobalSearchInput?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      runGlobalSearch().catch((error) => showInlineError(error.message));
    }
  });
  els.homeListSearch?.addEventListener("input", () => {
    state.homeSearch = els.homeListSearch.value;
    renderHome();
  });
  els.homeStageFilter?.addEventListener("change", () => {
    state.homeStageFilter = els.homeStageFilter.value;
    renderHome();
  });
  els.searchInput?.addEventListener("input", () => {
    state.search = els.searchInput.value;
    state.pageIndex = 1;
    renderScanPage();
  });
  els.pageSize?.addEventListener("change", () => {
    state.pageSize = Number(els.pageSize.value) || 25;
    state.pageIndex = 1;
    renderScanPage();
  });
  els.deliveryListSelect?.addEventListener("change", () => activateList(els.deliveryListSelect.value).catch((error) => showInlineError(error.message)));
  els.scanForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await processScan(els.scanInput.value);
    } catch (error) {
      showInlineError(error.message, false);
    }
    els.scanInput.value = "";
    els.scanInput.focus();
  });
  els.printBtn?.addEventListener("click", () => window.print());
  els.exportBtn?.addEventListener("click", () => {
    if (state.backend) {
      window.location.href = `/api/export.csv?listId=${encodeURIComponent(state.activeListId)}`;
    } else {
      exportStaticCsv();
    }
  });
  els.undoBtn?.addEventListener("click", async () => {
    const payload = await fetchJson("/api/undo", {
      method: "POST",
      body: JSON.stringify({ listId: state.activeListId, ...requestContext() }),
    });
    applyBackendPayload(payload);
    renderScanPage();
  });
  els.resetBtn?.addEventListener("click", () => resetState().catch((error) => showInlineError(error.message)));
  els.loadExampleBtn?.addEventListener("click", () => {
    const first = state.items[0];
    if (!first) return;
    els.scanInput.value = `TDEXRTY${pad(first.order, 6).slice(-3)}${first.item}000`;
    els.scanInput.focus();
  });
  els.importBtn?.addEventListener("click", () => {
    if (!els.importFile) return;
    els.importFile.value = "";
    els.importFile.click();
  });
  els.importFile?.addEventListener("change", () => {
    const file = els.importFile.files?.[0];
    if (!file) return;
    importDeliveryListFile(file).catch((error) => showInlineError(error.message, true));
  });
  els.addStationBtn?.addEventListener("click", () => addStationFromInput().catch((error) => showInlineError(error.message)));
  els.newStationInput?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      addStationFromInput().catch((error) => showInlineError(error.message));
    }
  });
  els.createUserForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    createUserFromForm().catch((error) => showInlineError(error.message));
  });
  els.manualEditSearchBtn?.addEventListener("click", () => runManualEditSearch().catch((error) => showInlineError(error.message)));
  els.manualEditSearch?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      runManualEditSearch().catch((error) => showInlineError(error.message));
    }
  });
  els.bayMapSearch?.addEventListener("input", () => {
    state.baySearch = els.bayMapSearch.value;
    renderBayMapPage();
  });
  els.bayStatusFilter?.addEventListener("change", () => {
    state.bayStatusFilter = els.bayStatusFilter.value;
    renderBayMapPage();
  });

  document.addEventListener("click", (event) => {
    const pageButton = event.target.closest("[data-page-target]");
    if (pageButton) {
      showPage(pageButton.dataset.pageTarget);
      return;
    }
    const openListButton = event.target.closest("[data-open-list]");
    if (openListButton) {
      activateList(openListButton.dataset.openList).catch((error) => showInlineError(error.message));
      if (els.headerGlobalSearchResults) els.headerGlobalSearchResults.hidden = true;
      return;
    }
    const filterButton = event.target.closest("[data-filter]");
    if (filterButton) {
      state.filter = filterButton.dataset.filter;
      state.pageIndex = 1;
      document.querySelectorAll("[data-filter]").forEach((button) => button.classList.toggle("is-active", button.dataset.filter === state.filter));
      renderScanPage();
      return;
    }
    const pageNumber = event.target.closest("[data-page-number]");
    if (pageNumber) {
      state.pageIndex = Number(pageNumber.dataset.pageNumber) || 1;
      renderScanPage();
      return;
    }
    const pageAction = event.target.closest("[data-page-action]");
    if (pageAction) {
      state.pageIndex += pageAction.dataset.pageAction === "next" ? 1 : -1;
      renderScanPage();
      return;
    }
    const row = event.target.closest("[data-id]");
    if (row) {
      state.selectedId = row.dataset.id;
      saveState();
      renderScanPage();
      return;
    }
    const exceptionButton = event.target.closest("[data-resolve-exception]");
    if (exceptionButton) {
      fetchJson("/api/exceptions/resolve", {
        method: "POST",
        body: JSON.stringify({ id: exceptionButton.dataset.resolveException, status: "Reviewed", comment: "Reviewed from dashboard" }),
      })
        .then(() => refreshAdminPage())
        .catch((error) => showInlineError(error.message));
      return;
    }
    const removeStationButton = event.target.closest("[data-remove-station]");
    if (removeStationButton) {
      removeStation(removeStationButton.dataset.removeStation).catch((error) => showInlineError(error.message));
      return;
    }
    const deactivateUserButton = event.target.closest("[data-deactivate-user]");
    if (deactivateUserButton) {
      fetchJson("/api/admin/users/deactivate", {
        method: "POST",
        body: JSON.stringify({ username: deactivateUserButton.dataset.deactivateUser }),
      })
        .then(() => refreshAdminPage())
        .catch((error) => showInlineError(error.message));
      return;
    }
    const saveLineItemButton = event.target.closest("[data-save-line-item]");
    if (saveLineItemButton) {
      saveManualLineItem(saveLineItemButton.dataset.saveLineItem).catch((error) => showInlineError(error.message));
      return;
    }
    const bayCell = event.target.closest("[data-bay-code]");
    if (bayCell?.dataset.bayCode) {
      const bay = state.bays.find((item) => item.bayCode === bayCell.dataset.bayCode);
      if (bay?.assignedQty && hasPermission("clear_bay")) {
        const reason = window.prompt(`Clear ${bay.displayName || bay.bayCode}?`, "Bay cleared");
        if (reason) {
          fetchJson("/api/indian-trail/clear", {
            method: "POST",
            body: JSON.stringify({ bayCode: bay.bayCode, reason }),
          })
            .then(() => refreshBayMapPage())
            .catch((error) => showInlineError(error.message));
        }
      }
      return;
    }
    const navButton = event.target.closest("[data-mobile-target]");
    if (navButton) {
      showPage("scan");
      document.body.dataset.mobileView = navButton.dataset.mobileTarget;
      document.querySelectorAll("[data-mobile-target]").forEach((button) => button.classList.toggle("is-active", button === navButton));
    }
  });
}

init().catch((error) => {
  document.body.innerHTML = `<main class="app"><section class="last-card error"><strong>Unable to load delivery list</strong><p>${escapeHtml(error.message)}</p></section></main>`;
});
