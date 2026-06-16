const STORAGE_KEY = "delivery-list-scanner-demo-v1";
const STATIONS_KEY = "delivery-list-scanner-stations-v1";
const DEFAULT_STATIONS = ["Airport Rd", "Indian Trail", "Greenville", "Customer Pickup", "DTC"];
const ROLE_OPTIONS = ["Operator", "Supervisor", "Indian Trail Operator", "Indian Trail Lead", "Indian Trail Manager", "Admin"];

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
  expandedDeliveryDate: "",
  baySearch: "",
  bayStatusFilter: "all",
  bayCategoryFilter: "all",
  selectedBayCode: "",
  printContext: null,
  lastImportResult: null,
  bayLayout: null,
  bays: [],
  bayEvents: [],
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
  todayDateLabel: document.getElementById("todayDateLabel"),
  todayStageGrid: document.getElementById("todayStageGrid"),

  scanPage: document.getElementById("scanPage"),
  pageTitle: document.getElementById("pageTitle"),
  stageSubtitle: document.getElementById("stageSubtitle"),
  stageHeading: document.getElementById("stageHeading"),
  scannerName: document.getElementById("scannerName"),
  deliveryListSelect: document.getElementById("deliveryListSelect"),
  deliveryDateSelect: document.getElementById("deliveryDateSelect"),
  deliveryStageSelect: document.getElementById("deliveryStageSelect"),
  stationSelect: document.getElementById("stationSelect"),
  operatorInput: document.getElementById("operatorInput"),
  progressText: document.getElementById("progressText"),
  progressFill: document.getElementById("progressFill"),
  searchInput: document.getElementById("searchInput"),
  scanForm: document.getElementById("scanForm"),
  scanInput: document.getElementById("scanInput"),
  manualScanForm: document.getElementById("manualScanForm"),
  manualOrderInput: document.getElementById("manualOrderInput"),
  manualItemInput: document.getElementById("manualItemInput"),
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
  bayCategoryFilters: document.getElementById("bayCategoryFilters"),
  baySelectedPanel: document.getElementById("baySelectedPanel"),
  bayAllBaysList: document.getElementById("bayAllBaysList"),
  bayCheckBtn: document.getElementById("bayCheckBtn"),
  bayFlowPanel: document.getElementById("bayFlowPanel"),
  indianTrailSummary: document.getElementById("indianTrailSummary"),
  bayActionButtons: document.getElementById("bayActionButtons"),
  bayMapCanvas: document.getElementById("bayMapCanvas"),
  bayRecentActions: document.getElementById("bayRecentActions"),
  baySelectedText: document.getElementById("baySelectedText"),
  sdiPanel: document.getElementById("sdiPanel"),
  sdiForm: document.getElementById("sdiForm"),
  sdiCloseBtn: document.getElementById("sdiCloseBtn"),
  sdiClearBtn: document.getElementById("sdiClearBtn"),
  sdiOrderInput: document.getElementById("sdiOrderInput"),
  sdiBayInput: document.getElementById("sdiBayInput"),
  sdiTruckExemptInput: document.getElementById("sdiTruckExemptInput"),
  sdiReasonInput: document.getElementById("sdiReasonInput"),

  printOptionsPanel: document.getElementById("printOptionsPanel"),
  printOptionsBackdrop: document.getElementById("printOptionsBackdrop"),
  printOptionsDate: document.getElementById("printOptionsDate"),
  printOptionsStages: document.getElementById("printOptionsStages"),
  printOptionsGlassType: document.getElementById("printOptionsGlassType"),
  printUpdatedOnly: document.getElementById("printUpdatedOnly"),
  printRushOnly: document.getElementById("printRushOnly"),
  printRemakeOnly: document.getElementById("printRemakeOnly"),
  printCpuOnly: document.getElementById("printCpuOnly"),
  printDtcOnly: document.getElementById("printDtcOnly"),
  printOptionsClose: document.getElementById("printOptionsClose"),
  printOptionsSubmit: document.getElementById("printOptionsSubmit"),

  adminPage: document.getElementById("adminPage"),
  adminSummary: document.getElementById("adminSummary"),
  folderImportBtn: document.getElementById("folderImportBtn"),
  importBtn: document.getElementById("importBtn"),
  importFile: document.getElementById("importFile"),
  tempFolderInput: document.getElementById("tempFolderInput"),
  importPreviewBox: document.getElementById("importPreviewBox"),
  importHistory: document.getElementById("importHistory"),
  deleteDateSelect: document.getElementById("deleteDateSelect"),
  deleteListSelect: document.getElementById("deleteListSelect"),
  deleteListBtn: document.getElementById("deleteListBtn"),
  deleteDateBtn: document.getElementById("deleteDateBtn"),
  deleteListStatus: document.getElementById("deleteListStatus"),
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

function todayKey() {
  const now = new Date();
  return `${now.getFullYear()}-${pad(now.getMonth() + 1, 2)}-${pad(now.getDate(), 2)}`;
}

function latestDeliveryDate(lists = state.lists) {
  const dates = lists.map((list) => list.deliveryDate).filter(Boolean).sort();
  return dates[dates.length - 1] || todayKey();
}

function dashboardDateKey(lists = state.lists) {
  const today = todayKey();
  return lists.some((list) => list.deliveryDate === today) ? today : latestDeliveryDate(lists);
}

function progressPercent(list) {
  return Number(list?.totalQty || 0) ? (Number(list.scannedQty || 0) / Number(list.totalQty || 1)) * 100 : 0;
}

function stageCategory(list) {
  const stage = `${list?.stage || ""} ${list?.scanner || ""}`.toLowerCase();
  if (stage.includes("outbound")) return "outbound";
  if (stage.includes("dtc") || stage.includes("deliver to customer")) return "dtc";
  if (stage.includes("greenville") || /\bgnv\b/.test(stage)) return "greenville";
  if (stage.includes("indian trail") || stage.includes("inbound")) return "received";
  if (stage.includes("customer pickup")) return "pickup";
  return "staged";
}

function stageLabel(list) {
  const category = stageCategory(list);
  if (category === "outbound") return "Outbound";
  if (category === "greenville") return "BFS Greenville";
  if (category === "received") return "Received";
  if (category === "pickup") return "Customer Pickup";
  if (category === "dtc") return "DTC";
  return "Staged";
}

function slugify(value) {
  return String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
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

function listsByDeliveryDate(lists = state.lists) {
  const groups = new Map();
  for (const list of lists) {
    const key = list.deliveryDate || "undated";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(list);
  }
  return [...groups.entries()]
    .sort(([dateA], [dateB]) => String(dateB).localeCompare(String(dateA)))
    .map(([date, dateLists]) => ({
      date,
      lists: dateLists.slice().sort((a, b) => stageSort(a) - stageSort(b) || a.label.localeCompare(b.label)),
    }));
}

function stageSort(list) {
  return { staged: 1, outbound: 2, received: 3, greenville: 4, pickup: 5, dtc: 6 }[stageCategory(list)] || 9;
}

function selectedDeliveryDate() {
  return state.meta?.deliveryDate || state.lists.find((list) => list.id === state.activeListId)?.deliveryDate || state.lists[0]?.deliveryDate || "";
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

function inferredRoute(item) {
  const route = String(item.route || "").trim().toUpperCase();
  const text = [item.route, item.job, item.customer, item.product, item.processState, item.queueState].join(" ");
  if (/\bCPU[-\s]*(IT|INT)\b/i.test(text) || /\bIT[-\s]*CPU\b/i.test(text)) return "";
  if (/\bCPU[-\s]*AIR\b/i.test(text)) return "CPU";
  if (/\b(GNV|GREENVILLE)\b/i.test(text)) return "GNV";
  if (/\b(DTC|DELIVER\s+TO\s+CUSTOMER)\b/i.test(text)) return "DTC";
  if (/\b(INT|INDIAN\s+TRAIL)\b/i.test(text)) return "";
  if (route === "CPU" || /\bCPU\b/i.test(text)) return "CPU";
  if (["INT", "IT", "INDIAN TRAIL"].includes(route)) return "";
  return route;
}

function routeCategory(item) {
  const route = inferredRoute(item);
  if (route === "CPU") return "cpu";
  if (route === "GNV") return "greenville";
  if (route === "DTC") return "dtc";
  return "indian_trail";
}

function routeLabel(item) {
  const route = inferredRoute(item);
  if (route === "CPU") return "CPU";
  if (route === "GNV") return "GNV";
  if (route === "DTC") return "DTC";
  return "";
}

function isCpuItem(item) {
  return routeCategory(item) === "cpu";
}

function filterItemsForProfile(items, profile) {
  if (profile === "cpu") return items.filter(isCpuItem);
  if (profile === "indian_trail") return items.filter((item) => routeCategory(item) === "indian_trail");
  if (profile === "greenville") return items.filter((item) => routeCategory(item) === "greenville");
  if (profile === "dtc") return items.filter((item) => routeCategory(item) === "dtc");
  return items.slice();
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
  const definitions = [
    ["staging-airport", "Staging - Airport Rd", "Airport Rd", "all"],
    ["outbound-airport", "Outbound - Airport Rd", "Airport Rd", "all"],
    ["inbound-indian-trail", "Inbound - Indian Trail", "Indian Trail", "indian_trail"],
    ["bfs-greenville", "BFS Greenville", "Greenville", "greenville"],
    ["customer-pickup", "Customer Pickup", "Customer Pickup", "cpu"],
    ["dtc", "DTC - Deliver to Customer", "DTC", "dtc"],
  ];
  return definitions
    .map(([suffix, stage, scanner, profile]) => {
      const items = filterItemsForProfile(baseItems, profile);
      if (profile !== "all" && !items.length) return null;
      const cloned = cloneItems(items);
      const totalQty = cloned.reduce((sum, item) => sum + Number(item.qty || 0), 0);
      const scannedQty = cloned.reduce((sum, item) => sum + Number(item.scanned || 0), 0);
      return {
        id: `${payload.deliveryDate}-${suffix}`,
        label: `${formatDisplayDate(payload.deliveryDate)} - ${stage}`,
        deliveryDate: payload.deliveryDate,
        stage,
        scanner,
        itemCount: cloned.length,
        totalQty,
        scannedQty,
        deliveryPercent: totalQty ? (scannedQty / totalQty) * 100 : 0,
        onTimeQty: 0,
        lateQty: 0,
        onTimePercent: 0,
        items: cloned,
      };
    })
    .filter(Boolean);
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
  const changingList = listId !== state.activeListId;
  if (state.backend) {
    const payload = await fetchJson(`/api/delivery-lists/${encodeURIComponent(listId)}`);
    applyBackendPayload(payload);
  } else {
    setActiveList(listId);
  }
  if (changingList || navigate) state.pageIndex = 1;
  renderScanPage();
  if (navigate) showPage("scan");
  if (navigate || document.activeElement === els.scanInput) els.scanInput?.focus();
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
  if (stage.includes("greenville")) return "Greenville";
  if (stage.includes("dtc") || stage.includes("deliver to customer")) return "Delivered";
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
          const route = routeLabel(item);
          const routeTag = route ? `<span class="route-tag ${escapeHtml(route.toLowerCase())}">${escapeHtml(route)}</span>` : "";
          return `
            <tr class="${selected ? "is-selected" : ""} ${status === "complete" ? "is-complete" : ""}" data-id="${escapeHtml(item.id)}">
              <td><span class="job-title">${escapeHtml(item.product || item.job)}</span><span class="job-subtitle">${escapeHtml(item.job)}</span></td>
              <td>${escapeHtml(item.order)}</td>
              <td>${escapeHtml(item.item)}</td>
              <td><span class="qty-pill ${status}">${item.scanned} / ${item.qty}</span></td>
              <td>${escapeHtml(item.dimensions)}</td>
              <td>${escapeHtml(item.customer)}</td>
              <td></td>
              <td>${routeTag}</td>
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
        const mark = status === "complete" ? "&#10003;" : routeLabel(item) || "-";
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
  const groups = listsByDeliveryDate();
  const activeDate = selectedDeliveryDate();
  if (els.deliveryDateSelect) {
    els.deliveryDateSelect.innerHTML = groups
      .map((group) => `<option value="${escapeHtml(group.date)}">${escapeHtml(formatDisplayDate(group.date))}</option>`)
      .join("");
    els.deliveryDateSelect.value = activeDate;
  }
  if (els.deliveryStageSelect) {
    const stageLists = (groups.find((group) => group.date === activeDate)?.lists || state.lists).filter((list) => list.deliveryDate === activeDate);
    els.deliveryStageSelect.innerHTML = stageLists
      .map((list) => `<option value="${escapeHtml(list.id)}">${escapeHtml(list.stage)} - ${escapeHtml(list.scanner)}</option>`)
      .join("");
    els.deliveryStageSelect.value = state.activeListId;
  }
  if (els.deliveryListSelect) {
    els.deliveryListSelect.innerHTML = state.lists
      .map((list) => `<option value="${escapeHtml(list.id)}">${escapeHtml(list.label)}</option>`)
      .join("");
    els.deliveryListSelect.value = state.activeListId;
  }
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
  setControlAllowed(els.folderImportBtn, hasPermission("import_delivery_lists"), true);
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

function aggregateListStats(lists) {
  const totalLists = lists.length;
  const totalItems = lists.reduce((sum, list) => sum + Number(list.itemCount || 0), 0);
  const totalQty = lists.reduce((sum, list) => sum + Number(list.totalQty || 0), 0);
  const scannedQty = lists.reduce((sum, list) => sum + Number(list.scannedQty || 0), 0);
  const onTimeQty = lists.reduce((sum, list) => sum + Number(list.onTimeQty || 0), 0);
  const lateQty = lists.reduce((sum, list) => sum + Number(list.lateQty || 0), 0);
  const timedQty = onTimeQty + lateQty;
  return {
    totalLists,
    totalItems,
    totalQty,
    scannedQty,
    remainingQty: Math.max(totalQty - scannedQty, 0),
    deliveryPercent: totalQty ? (scannedQty / totalQty) * 100 : 0,
    onTimeQty,
    lateQty,
    onTimePercent: timedQty ? (onTimeQty / timedQty) * 100 : 0,
  };
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

function deliveryListCard(list, extraClass = "") {
  const percent = progressPercent(list);
  const category = stageCategory(list);
  const onTime = Number(list.onTimePercent || 0);
  return `
    <article class="delivery-list-card ${escapeHtml(category)} ${escapeHtml(extraClass)}" data-open-list="${escapeHtml(list.id)}">
      <div>
        <strong>${escapeHtml(list.label)}</strong>
        <span>${escapeHtml(list.stage)} - ${escapeHtml(list.scanner)}</span>
      </div>
      <div class="list-card-progress"><span style="width:${Math.min(percent, 100)}%"></span></div>
      <small>${escapeHtml(list.itemCount || 0)} lines - ${escapeHtml(list.scannedQty || 0)}/${escapeHtml(list.totalQty || 0)} pieces - On-time ${onTime.toFixed(1)}%</small>
    </article>
  `;
}

function renderTodayProgress() {
  if (!els.todayStageGrid) return;
  const key = dashboardDateKey();
  const isActualToday = key === todayKey();
  const lists = state.lists
    .filter((list) => list.deliveryDate === key)
    .sort((a, b) => {
      return stageSort(a) - stageSort(b) || a.label.localeCompare(b.label);
    });
  if (els.todayDateLabel) {
    els.todayDateLabel.textContent = `${isActualToday ? "Today" : "Latest"} - ${formatDisplayDate(key)}`;
  }
  els.todayStageGrid.innerHTML = lists.length
    ? lists
        .map((list) => {
          const percent = progressPercent(list);
          return `
            <article class="today-stage-card ${escapeHtml(stageCategory(list))}" data-open-list="${escapeHtml(list.id)}">
              <div>
                <span>${escapeHtml(stageLabel(list))}</span>
                <strong>${escapeHtml(list.scannedQty || 0)} / ${escapeHtml(list.totalQty || 0)}</strong>
              </div>
              <div class="list-card-progress"><span style="width:${Math.min(percent, 100)}%"></span></div>
              <small>${escapeHtml(list.stage)} - ${percent.toFixed(1)}%</small>
            </article>
          `;
        })
        .join("")
    : `<div class="admin-empty">No delivery lists are loaded for ${formatDisplayDate(key)}.</div>`;
}

function renderHome() {
  if (!els.homePage) return;
  const overview = aggregateListStats(state.lists);
  if (els.homeWelcome) {
    els.homeWelcome.textContent = `Signed in as ${state.user?.displayName || state.user?.username || "Demo user"}`;
  }
  if (els.overviewStats) {
    els.overviewStats.innerHTML = [
      miniStat("Delivery %", `${overview.deliveryPercent.toFixed(1)}%`, `${overview.scannedQty}/${overview.totalQty} scanned`),
      miniStat("On-Time %", `${overview.onTimePercent.toFixed(1)}%`, `${overview.onTimeQty} on time`),
      miniStat("Late Items", overview.lateQty),
      miniStat("Delivery Lists", overview.totalLists),
    ].join("");
  }
  if (els.homeUserCard) {
    els.homeUserCard.innerHTML = `
      <strong>${escapeHtml(state.user?.displayName || state.user?.username || "Demo")}</strong>
      <span>${escapeHtml((state.user?.roles || ["Local Demo"]).join(", "))}</span>
      <small>Stages: ${escapeHtml((state.user?.stageAccess || ["All demo stages"]).join(", "))}</small>
    `;
  }
  renderTodayProgress();
  const filtered = filteredDeliveryLists();
  const dateGroups = listsByDeliveryDate(filtered);
  if (!dateGroups.some((group) => group.date === state.expandedDeliveryDate)) {
    state.expandedDeliveryDate = dateGroups[0]?.date || "";
  }
  if (els.homeListCount) els.homeListCount.textContent = `${dateGroups.length} dates / ${filtered.length} stages`;
  if (els.homeListGrid) {
    els.homeListGrid.innerHTML = dateGroups.length
      ? dateGroups
          .map((group) => {
            const stats = aggregateListStats(group.lists);
            return `
              <details class="delivery-date-group" data-delivery-date="${escapeHtml(group.date)}" ${group.date === state.expandedDeliveryDate ? "open" : ""}>
                <summary>
                  <span>
                    <strong>${escapeHtml(formatDisplayDate(group.date))}</strong>
                    <small>${escapeHtml(group.lists.length)} stages - Delivery on-time ${stats.onTimePercent.toFixed(1)}%</small>
                    <span class="list-card-progress date-progress"><span style="width:${Math.min(stats.deliveryPercent, 100)}%"></span></span>
                  </span>
                  <span><strong>${stats.deliveryPercent.toFixed(1)}%</strong><small>${escapeHtml(stats.scannedQty)} / ${escapeHtml(stats.totalQty)} pieces</small></span>
                </summary>
                <div class="delivery-stage-list">
                  ${group.lists.map((list) => deliveryListCard(list, "date-grouped")).join("")}
                </div>
              </details>
            `;
          })
          .join("")
      : `<div class="admin-empty">No delivery lists match.</div>`;
    els.homeListGrid.querySelectorAll(".delivery-date-group").forEach((details) => {
      details.addEventListener("toggle", () => {
        if (!details.open) return;
        state.expandedDeliveryDate = details.dataset.deliveryDate || "";
        els.homeListGrid.querySelectorAll(".delivery-date-group").forEach((other) => {
          if (other !== details) other.open = false;
        });
      });
    });
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

async function submitManualScan() {
  const order = digitsOnly(els.manualOrderInput?.value || "");
  const item = digitsOnly(els.manualItemInput?.value || "");
  if (!order || !item) {
    showInlineError("Manual scan needs an order number and item number.", false);
    return;
  }
  await processScan(canonicalBarcode(order, item));
  if (els.manualOrderInput) els.manualOrderInput.value = "";
  if (els.manualItemInput) els.manualItemInput.value = "";
  els.scanInput?.focus();
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
    const [layout, baysPayload, summary, eventsPayload] = await Promise.all([
      fetchJson("/api/indian-trail/layout"),
      fetchJson("/api/indian-trail/bays"),
      hasPermission("view_indian_trail") ? fetchJson("/api/indian-trail/summary") : Promise.resolve(null),
      fetchJson("/api/indian-trail/events"),
    ]);
    state.bayLayout = layout;
    state.bays = baysPayload.bays || [];
    state.bayEvents = eventsPayload.events || [];
    renderIndianTrailSummary(summary);
    renderBayRouteFlow(summary);
  } else {
    const response = await fetch("data/indian-trail-bay-layout.json");
    state.bayLayout = await response.json();
    state.bays = (state.bayLayout.bays || []).map((bay) => ({ ...bay, assignedQty: 0, capacityQty: bay.autoAssignable ? 1 : 0, status: bay.autoAssignable ? "Empty" : "ManualHold", assignments: [] }));
    state.bayEvents = [];
    renderBayRouteFlow(null);
  }
  renderBayMapPage();
}

function renderBayRouteFlow(summary) {
  if (!els.bayFlowPanel) return;
  const key = dashboardDateKey();
  const dayLists = state.lists.filter((list) => list.deliveryDate === key);
  const outbound = dayLists.find((list) => stageCategory(list) === "outbound");
  const inbound = dayLists.find((list) => stageCategory(list) === "received") || state.lists.find((list) => list.id === summary?.activeInboundListId);
  const outboundQty = Number(outbound?.scannedQty || 0);
  const outboundTotal = Number(outbound?.totalQty || 0);
  const inboundQty = Number(inbound?.scannedQty ?? summary?.receivedQty ?? 0);
  const inboundTotal = Number(inbound?.totalQty ?? summary?.inboundToday ?? 0);
  els.bayFlowPanel.innerHTML = `
    <button class="flow-card outbound" type="button" ${outbound ? `data-open-list="${escapeHtml(outbound.id)}"` : ""}>
      <small>Today's Outbound</small>
      <strong>${escapeHtml(outboundQty)} / ${escapeHtml(outboundTotal)}</strong>
      <span>${outbound ? escapeHtml(outbound.stage) : "No outbound list"}</span>
    </button>
    <div class="flow-lane" aria-hidden="true">
      <span class="flow-truck"></span>
    </div>
    <button class="flow-card inbound" type="button" ${inbound ? `data-open-list="${escapeHtml(inbound.id)}"` : ""}>
      <small>Indian Trail Delivery List</small>
      <strong>${escapeHtml(inboundQty)} / ${escapeHtml(inboundTotal)}</strong>
      <span>${inbound ? escapeHtml(inbound.stage) : "No Indian Trail list"}</span>
    </button>
  `;
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
  const statusKind = bayStatusKind(bay);
  const matchesCategory = state.bayCategoryFilter === "all" || bayCategoryKind(bay) === state.bayCategoryFilter;
  const matchesStatus =
    state.bayStatusFilter === "all" ||
    state.bayStatusFilter === statusKind ||
    (state.bayStatusFilter === "manual" && (!bay?.active || sourceStatus.includes("manual"))) ||
    (state.bayStatusFilter === "empty" && (status.includes("empty") || status.includes("available"))) ||
    status.includes(state.bayStatusFilter);
  if (!matchesCategory || !matchesStatus) return false;
  if (!search) return true;
  return text.toLowerCase().includes(search);
}

function isWorkbookLegendCell(cell) {
  return Number(cell.row || 0) >= 11 && Number(cell.row || 0) <= 18 && Number(cell.col || 0) >= 17 && Number(cell.col || 0) <= 20;
}

function statusAbbreviation(status, bay) {
  if (!bay) return "";
  if (!bay.active || String(status).toLowerCase() === "manualhold") return "MAN";
  if (status === "SDI") return "SDI";
  if (/pre|assign/i.test(status)) return "PRE";
  if (status === "Full" || status === "Occupied") return "OCC";
  if (status === "Partial") return "PAR";
  if (status === "Empty" || status === "Available") return "AVL";
  return "";
}

function bayCategoryKind(bay) {
  const text = [bay?.bayCategory, bay?.bayType, bay?.mapSection, bay?.displayName, bay?.bayCode].join(" ").toLowerCase();
  if (text.includes("coral")) return "coral";
  if (/\blr\b/.test(text)) return "lr";
  if (/\brr\b/.test(text)) return "rr";
  if (text.includes("framed mirror") || /\bfm\b/.test(text)) return "framed-mirror";
  if (text.includes("bfs mir")) return "bfs-mirror";
  if (text.includes("mirror") || text.includes("annealed")) return "mirror";
  if (text.includes("crl") || text.includes("laurence")) return "crl";
  if (text.includes("shower") || text.includes("tempered") || /^t-bay/.test(String(bay?.bayCode || "").toLowerCase())) return "showers";
  return "standard";
}

function bayCategoryLabel(kind) {
  const labels = {
    coral: "Coral",
    lr: "LR",
    rr: "RR",
    showers: "Showers",
    mirror: "Mirrors",
    "bfs-mirror": "BFS Mirrors",
    "framed-mirror": "Framed Mirrors",
    crl: "CRL Laurence",
    standard: "Other Bays",
  };
  return labels[kind] || "Other Bays";
}

function bayCategoryOrder(kind) {
  return { coral: 1, lr: 2, rr: 3, showers: 4, mirror: 5, "bfs-mirror": 6, "framed-mirror": 7, crl: 8, standard: 9 }[kind] || 9;
}

function bayRackLabel(bay) {
  return bay?.mapSection || (bay?.bayNumber ? `Bay ${bay.bayNumber}` : "Unmapped");
}

function baySearchText(bay) {
  return [
    bay?.displayName,
    bay?.bayCode,
    bay?.status,
    bay?.mapSection,
    bay?.bayCategory,
    bay?.bayType,
    ...(bay?.assignments || []).map((assignment) => `${assignment.order} ${assignment.item} ${assignment.customer} ${assignment.product} ${assignment.job} ${assignment.dimensions}`),
  ].join(" ");
}

function bayStatusKind(bay) {
  const status = String(bay?.status || "").toLowerCase();
  const assigned = Number(bay?.assignedQty || 0);
  if (!bay?.active || status.includes("manual") || status.includes("blocked")) return "blocked";
  if (status.includes("sdi") || status.includes("pick")) return "picking";
  if (status.includes("pre") || status.includes("assign")) return "preassigned";
  if (assigned > 0 || status.includes("occupied") || status.includes("full") || status.includes("partial")) return "occupied";
  return "available";
}

function bayUtilization(bay) {
  const capacity = Number(bay?.capacityQty || 0);
  const assigned = Number(bay?.assignedQty || 0);
  if (!capacity) return assigned ? 100 : 0;
  return Math.min((assigned / capacity) * 100, 100);
}

function bayCategoryFilterOptions() {
  return [
    ["all", "All Bays"],
    ["showers", "Showers"],
    ["lr", "LR"],
    ["rr", "RR"],
    ["crl", "CRL Laurence"],
    ["framed-mirror", "Framed Mirrors"],
    ["mirror", "Mirrors"],
    ["bfs-mirror", "BFS Mirrors"],
    ["coral", "Coral"],
  ];
}

function bayOverview() {
  const total = state.bays.length;
  const available = state.bays.filter((bay) => bayStatusKind(bay) === "available").length;
  const occupied = state.bays.filter((bay) => bayStatusKind(bay) === "occupied").length;
  const preassigned = state.bays.filter((bay) => bayStatusKind(bay) === "preassigned").length;
  const blocked = state.bays.filter((bay) => bayStatusKind(bay) === "blocked").length;
  return { total, available, occupied, preassigned, blocked };
}

function renderBaySlotButton(bay, mode = "physical") {
  const assignment = bay.assignments?.[0];
  const status = bay.status || "ManualHold";
  const text = baySearchText(bay);
  const search = state.baySearch.trim().toLowerCase();
  const searchMatch = Boolean(search) && text.toLowerCase().includes(search);
  const dimmed = !bayMatchesFilter(bay, text);
  const abbreviation = statusAbbreviation(status, bay);
  const kind = bayCategoryKind(bay);
  const statusKind = bayStatusKind(bay);
  const label = bay.displayName || bay.bayCode;
  return `
    <button class="${mode === "physical" ? "physical-bay-slot" : "bay-slot"} type-${escapeHtml(kind)} status-${escapeHtml(statusKind)} ${escapeHtml(String(status).toLowerCase())} ${dimmed ? "is-dimmed" : ""} ${searchMatch ? "is-search-match" : ""} ${state.selectedBayCode === bay.bayCode ? "is-selected" : ""}"
      type="button"
      data-bay-code="${escapeHtml(bay.bayCode)}"
      data-assignment-id="${escapeHtml(assignment?.id || "")}"
      title="${escapeHtml(text)}">
      <span class="bay-code">${escapeHtml(label)}</span>
      ${abbreviation ? `<span class="bay-state">${escapeHtml(abbreviation)}</span>` : ""}
      <small>${assignment ? `${escapeHtml(assignment.order)} ${escapeHtml(assignment.customer || "")}` : escapeHtml(bay.bayCategory || status)}</small>
    </button>
  `;
}

function bayTypeSections() {
  const groups = new Map();
  for (const bay of state.bays || []) {
    const kind = bayCategoryKind(bay);
    if (!groups.has(kind)) groups.set(kind, []);
    groups.get(kind).push(bay);
  }
  return [...groups.entries()]
    .map(([kind, bays]) => {
      const racks = new Map();
      for (const bay of bays) {
        const rack = bayRackLabel(bay);
        if (!racks.has(rack)) racks.set(rack, []);
        racks.get(rack).push(bay);
      }
      return {
        kind,
        label: bayCategoryLabel(kind),
        bays,
        racks: [...racks.entries()]
          .map(([label, rackBays]) => ({
            label,
            bays: rackBays
              .slice()
              .sort((a, b) => Number(a.baySlot || a.layoutRow || 9999) - Number(b.baySlot || b.layoutRow || 9999) || Number(a.layoutCol || 9999) - Number(b.layoutCol || 9999)),
          }))
          .sort((a, b) => {
            const aNum = Number(String(a.label).match(/\d+/)?.[0] || 9999);
            const bNum = Number(String(b.label).match(/\d+/)?.[0] || 9999);
            return aNum - bNum || a.label.localeCompare(b.label);
          }),
      };
    })
    .sort((a, b) => bayCategoryOrder(a.kind) - bayCategoryOrder(b.kind) || a.label.localeCompare(b.label));
}

function renderBayMapPage() {
  if (!els.bayMapCanvas || !state.bayLayout) return;
  const sectionMap = new Map();
  for (const bay of state.bays || []) {
    const label = bayRackLabel(bay);
    if (!sectionMap.has(label)) sectionMap.set(label, []);
    sectionMap.get(label).push(bay);
  }
  const physicalSections = [...sectionMap.entries()]
    .map(([label, bays]) => {
      const positioned = bays.filter((bay) => Number(bay.layoutRow || 0) || Number(bay.layoutCol || 0));
      const row = positioned.reduce((sum, bay) => sum + Number(bay.layoutRow || 9999), 0) / Math.max(positioned.length, 1);
      const col = positioned.reduce((sum, bay) => sum + Number(bay.layoutCol || 9999), 0) / Math.max(positioned.length, 1);
      const kind = bayCategoryKind(bays[0]);
      return { label, bays, row, col, kind };
    })
    .sort((a, b) => a.col - b.col || a.row - b.row || a.label.localeCompare(b.label));
  els.bayMapCanvas.innerHTML = physicalSections
    .map((section) => {
      const visible = section.bays.filter((bay) => bayMatchesFilter(bay, baySearchText(bay))).length;
      const dimmed = !visible && (state.bayStatusFilter !== "all" || state.bayCategoryFilter !== "all" || state.baySearch);
      return `
        <section class="physical-bay-section type-${escapeHtml(section.kind)} ${dimmed ? "is-dimmed" : ""}">
          <header><strong>${escapeHtml(section.label)}</strong><span>${escapeHtml(visible || section.bays.length)} slots</span></header>
          <div class="physical-slot-grid">
            ${section.bays.map((bay) => renderBaySlotButton(bay, "physical")).join("")}
          </div>
        </section>
      `;
    })
    .join("");
  const overview = bayOverview();
  if (els.bayOverviewStats) {
    els.bayOverviewStats.innerHTML = [
      miniStat("Total Bays", overview.total),
      miniStat("Available", overview.available),
      miniStat("Occupied", overview.occupied),
      miniStat("Pre Assigned", overview.preassigned),
      miniStat("Blocked", overview.blocked),
    ].join("");
  }
  if (els.baySelectedText) els.baySelectedText.textContent = state.selectedBayCode ? `Selected: ${state.selectedBayCode}` : "No bay selected";
  renderBaySidePanels();
  renderBayRecentActions();
}

function renderBaySidePanels() {
  if (els.bayCategoryFilters) {
    els.bayCategoryFilters.innerHTML = bayCategoryFilterOptions()
      .map(([value, label]) => `<button class="tab ${state.bayCategoryFilter === value ? "is-active" : ""}" type="button" data-bay-category-filter="${escapeHtml(value)}">${escapeHtml(label)}</button>`)
      .join("");
  }
  const bay = selectedBay();
  if (els.baySelectedPanel) {
    if (!bay) {
      els.baySelectedPanel.innerHTML = `<div class="admin-empty">Select a bay to see assigned orders, capacity, and route details.</div>`;
    } else {
      const assignments = bay.assignments || [];
      els.baySelectedPanel.innerHTML = `
        <div class="selected-bay-heading">
          <span class="bay-status-dot status-${escapeHtml(bayStatusKind(bay))}"></span>
          <div><strong>${escapeHtml(bay.displayName || bay.bayCode)}</strong><small>${escapeHtml(bay.mapSection || bay.area || "")}</small></div>
          <span class="status-chip status-${escapeHtml(bayStatusKind(bay))}">${escapeHtml(bay.status || "Available")}</span>
        </div>
        <div class="selected-bay-stats">
          ${miniStat("Category", bayCategoryLabel(bayCategoryKind(bay)))}
          ${miniStat("Items", assignments.reduce((sum, item) => sum + Number(item.assignedQty || item.qty || 0), 0))}
          ${miniStat("Utilization", `${bayUtilization(bay).toFixed(0)}%`)}
        </div>
        <div class="capacity-meter"><span style="width:${bayUtilization(bay)}%"></span></div>
        <div class="selected-assignment-list">
          ${
            assignments.length
              ? assignments
                  .map(
                    (assignment) => `
                      <article>
                        <strong>${escapeHtml(assignment.order)}-${escapeHtml(assignment.item)} <span>${escapeHtml(assignment.customer || "")}</span></strong>
                        <small>${escapeHtml(assignment.product || assignment.job || "")}</small>
                        <small>${escapeHtml(assignment.dimensions || "")} - Qty ${escapeHtml(assignment.assignedQty || assignment.qty || 0)}</small>
                        <small>${escapeHtml(assignment.job || "")}</small>
                      </article>
                    `
                  )
                  .join("")
              : `<article><strong>No assigned orders</strong><small>This bay is ready for assignment if it is available.</small></article>`
          }
        </div>
      `;
    }
  }
  if (els.bayAllBaysList) {
    const sections = bayTypeSections().filter((section) => state.bayCategoryFilter === "all" || section.kind === state.bayCategoryFilter);
    els.bayAllBaysList.innerHTML = sections
      .map((section) => {
        const sectionOpen = state.bayCategoryFilter !== "all" || section.bays.some((item) => item.bayCode === state.selectedBayCode);
        return `
          <details class="bay-type-section type-${escapeHtml(section.kind)}" ${sectionOpen ? "open" : ""}>
            <summary><span><strong>${escapeHtml(section.label)}</strong><small>${escapeHtml(section.bays.length)} bays</small></span></summary>
            <div class="bay-rack-list">
              ${section.racks
                .map((rack) => {
                  const capacity = rack.bays.reduce((sum, item) => sum + Number(item.capacityQty || 0), 0);
                  const assigned = rack.bays.reduce((sum, item) => sum + Number(item.assignedQty || 0), 0);
                  const percent = capacity ? Math.min((assigned / capacity) * 100, 100) : assigned ? 100 : 0;
                  const rackHasSelected = rack.bays.some((item) => item.bayCode === state.selectedBayCode);
                  return `
                    <details class="bay-rack" ${state.bayCategoryFilter !== "all" || rackHasSelected ? "open" : ""}>
                      <summary>
                        <strong>${escapeHtml(rack.label)}</strong>
                        <span>${escapeHtml(assigned)} / ${escapeHtml(capacity || rack.bays.length)}</span>
                      </summary>
                      <div class="capacity-meter"><span style="width:${percent}%"></span></div>
                      <div class="bay-slot-grid">${rack.bays.map((item) => renderBaySlotButton(item, "list")).join("")}</div>
                    </details>
                  `;
                })
                .join("")}
            </div>
          </details>
        `;
      })
      .join("");
  }
}

function renderBayLegend() {
  if (!els.bayLegend) return;
  const legend = [
    ["Coral", "Reserved coral bays", "coral"],
    ["LR / RR", "Deep blue LR and RR bays", "lr-rr"],
    ["Showers", "Green shower bays", "showers"],
    ["Mirror", "Purple mirror and BFS mirror bays", "mirror"],
    ["Framed", "Teal framed mirror bays", "framed-mirror"],
    ["CRL", "Yellow CRL Laurence bays", "crl"],
    ["AVL", "Available bay", "empty"],
    ["OCC", "Occupied / assigned", "occupied"],
    ["SDI", "Needs special handling", "sdi"],
  ];
  els.bayLegend.innerHTML = legend
    .map(([abbr, label, kind]) => `<span class="legend-item ${escapeHtml(kind)}"><i></i><strong>${escapeHtml(abbr)}</strong>${escapeHtml(label)}</span>`)
    .join("");
}

function formatEventType(value) {
  return String(value || "")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/_/g, " ");
}

function renderBayRecentActions() {
  if (!els.bayRecentActions) return;
  const events = state.bayEvents || [];
  els.bayRecentActions.innerHTML = events.length
    ? events
        .slice(0, 12)
        .map((event) => {
          const when = new Date(event.time || event.createdAt || "");
          const time = Number.isNaN(when.getTime()) ? "" : when.toLocaleString();
          const bay = event.bayDisplay || event.bayCode || event.newBayCode || event.oldBayCode || "Bay";
          const order = event.order ? `${event.order}-${event.item || ""}` : "";
          return `
            <div>
              <strong>${escapeHtml(formatEventType(event.eventType))} - ${escapeHtml(bay)}</strong>
              <span>${escapeHtml([order, event.customer, event.reason].filter(Boolean).join(" - "))}</span>
              <small>${escapeHtml(event.user || "")}${time ? ` - ${escapeHtml(time)}` : ""}</small>
            </div>
          `;
        })
        .join("")
    : `<div><strong>No bay actions yet</strong><span>Receive, move, clear, and SDI actions will appear here.</span></div>`;
}

function scrollToBaySearchMatch() {
  if (!els.bayMapCanvas) return;
  renderBayMapPage();
  const target =
    els.bayMapCanvas.querySelector(".physical-bay-slot.is-search-match:not(.is-dimmed), .physical-bay-slot.is-search-match") ||
    els.bayAllBaysList?.querySelector(".bay-slot.is-search-match:not(.is-dimmed), .bay-slot.is-search-match");
  if (!target) {
    showInlineError("No bay map match found for that search.", false);
    return;
  }
  target.classList.add("is-found");
  target.scrollIntoView({ behavior: "smooth", block: "center", inline: "center" });
  window.setTimeout(() => target.classList.remove("is-found"), 1800);
}

function selectedBay() {
  return state.bays.find((bay) => bay.bayCode === state.selectedBayCode) || null;
}

function selectBay(bayCode) {
  state.selectedBayCode = bayCode || "";
  const bay = selectedBay();
  if (bay && els.bayMapSearch) els.bayMapSearch.value = bay.displayName || bay.bayCode;
  renderBayMapPage();
}

function requireSelectedBay() {
  const bay = selectedBay();
  if (!bay) {
    showInlineError("Select a bay first.", false);
    return null;
  }
  return bay;
}

async function postBayAction(path, payload) {
  const result = await fetchJson(path, {
    method: "POST",
    body: JSON.stringify({ ...payload, ...requestContext() }),
  });
  await refreshBayMapPage();
  return result;
}

function selectedBayAssignment() {
  return selectedBay()?.assignments?.[0] || null;
}

function openSdiPanel() {
  const bay = selectedBay();
  const assignment = selectedBayAssignment();
  if (els.sdiPanel) els.sdiPanel.hidden = false;
  if (els.sdiOrderInput && assignment?.order) els.sdiOrderInput.value = assignment.order;
  if (els.sdiBayInput) els.sdiBayInput.value = bay?.bayCode || "";
  if (els.sdiReasonInput && !els.sdiReasonInput.value) els.sdiReasonInput.value = "Same-day install";
  els.sdiOrderInput?.focus();
}

function closeSdiPanel() {
  if (els.sdiPanel) els.sdiPanel.hidden = true;
}

async function submitSdi(mark = true) {
  const assignment = selectedBayAssignment();
  const payload = {
    assignmentId: assignment?.id || "",
    orderNo: els.sdiOrderInput?.value || "",
    bayCode: els.sdiBayInput?.value || state.selectedBayCode || "",
    truckExempt: Boolean(els.sdiTruckExemptInput?.checked),
    reason: els.sdiReasonInput?.value || (mark ? "Same-day install" : "SDI cleared"),
  };
  const result = await postBayAction(mark ? "/api/indian-trail/mark-sdi" : "/api/indian-trail/remove-sdi", payload);
  closeSdiPanel();
  if (mark && result?.rush && window.confirm(result.message || "A Rush order has been marked. Print rush order?")) {
    const listId = state.activeListId || selectedBay()?.assignments?.[0]?.deliveryListId || "";
    if (listId) window.open(`/api/print/package?listId=${encodeURIComponent(listId)}&rushOnly=1`, "_blank", "noopener");
  }
}

async function runBayAction(action) {
  if (action === "sdi") {
    openSdiPanel();
    return;
  }
  const bay = requireSelectedBay();
  if (!bay) return;
  const assignment = bay.assignments?.[0];
  if (action === "clear") {
    if (!window.confirm(`Clear ${bay.displayName || bay.bayCode}?`)) return;
    await postBayAction("/api/indian-trail/clear", { bayCode: bay.bayCode, reason: "Cleared from bay map" });
    return;
  }
  if (action === "manual-assign") {
    if (!state.selectedId) {
      showInlineError("Select a delivery-list row first, then choose the bay.", false);
      return;
    }
    await postBayAction("/api/indian-trail/assign", { lineItemId: state.selectedId, bayCode: bay.bayCode, reason: "Manual assignment from bay map" });
    return;
  }
  if (action === "move") {
    if (!assignment?.id) {
      showInlineError("That bay does not have an assignment to move.", false);
      return;
    }
    const newBayCode = window.prompt("Move assignment to which bay code?");
    if (!newBayCode) return;
    await postBayAction("/api/indian-trail/move", { assignmentId: assignment.id, newBayCode, reason: `Moved from ${bay.displayName || bay.bayCode}` });
  }
}

function openPrintPackage(printCandidates, filters = {}) {
  const listIds = [...new Set(printCandidates.flatMap((candidate) => candidate.listIds || []))];
  if (!listIds.length) return;
  const params = new URLSearchParams({ listId: listIds.join(",") });
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  window.open(`/api/print/package?${params.toString()}`, "_blank", "noopener");
}

function renderPrintOptionStages() {
  if (!els.printOptionsStages || !els.printOptionsDate) return;
  const date = els.printOptionsDate.value || selectedDeliveryDate() || dashboardDateKey();
  const lists = state.lists.filter((list) => list.deliveryDate === date).sort((a, b) => stageSort(a) - stageSort(b));
  const contextIds = new Set(state.printContext?.listIds || []);
  const hasContextIds = contextIds.size > 0;
  els.printOptionsStages.innerHTML = lists
    .map((list) => {
      const checked = hasContextIds ? contextIds.has(list.id) : true;
      return `
        <label>
          <input type="checkbox" value="${escapeHtml(list.id)}" ${checked ? "checked" : ""}>
          <span>${escapeHtml(list.stage)} <small>${escapeHtml(list.scannedQty || 0)} / ${escapeHtml(list.totalQty || 0)}</small></span>
        </label>
      `;
    })
    .join("");
}

function openPrintOptions(context = {}) {
  state.printContext = context;
  const groups = listsByDeliveryDate();
  if (!groups.length) {
    showInlineError("No delivery lists are available to print.", false);
    return;
  }
  const requestedDate = context.date || state.meta?.deliveryDate || selectedDeliveryDate() || groups[0].date;
  if (els.printOptionsDate) {
    els.printOptionsDate.innerHTML = groups.map((group) => `<option value="${escapeHtml(group.date)}">${escapeHtml(formatDisplayDate(group.date))}</option>`).join("");
    els.printOptionsDate.value = groups.some((group) => group.date === requestedDate) ? requestedDate : groups[0].date;
  }
  for (const input of [els.printUpdatedOnly, els.printRushOnly, els.printRemakeOnly, els.printCpuOnly, els.printDtcOnly]) {
    if (input) input.checked = false;
  }
  if (els.printOptionsGlassType) els.printOptionsGlassType.value = "";
  renderPrintOptionStages();
  if (els.printOptionsBackdrop) els.printOptionsBackdrop.hidden = false;
  if (els.printOptionsPanel) els.printOptionsPanel.hidden = false;
}

function closePrintOptions() {
  if (els.printOptionsBackdrop) els.printOptionsBackdrop.hidden = true;
  if (els.printOptionsPanel) els.printOptionsPanel.hidden = true;
}

function submitPrintOptions() {
  const listIds = [...(els.printOptionsStages?.querySelectorAll("input:checked") || [])].map((input) => input.value);
  if (!listIds.length) {
    showInlineError("Select at least one stage to print.", false);
    return;
  }
  if (!state.backend) {
    closePrintOptions();
    window.print();
    return;
  }
  const filters = {
    updatedOnly: els.printUpdatedOnly?.checked ? "1" : "",
    rushOnly: els.printRushOnly?.checked ? "1" : "",
    remakeOnly: els.printRemakeOnly?.checked ? "1" : "",
    cpuOnly: els.printCpuOnly?.checked ? "1" : "",
    dtcOnly: els.printDtcOnly?.checked ? "1" : "",
    glassType: els.printOptionsGlassType?.value.trim() || "",
  };
  openPrintPackage([{ listIds }], filters);
  closePrintOptions();
}

async function importTempDeliveryFolder() {
  const sourceFolder = els.tempFolderInput?.value.trim() || "";
  const result = await fetchJson("/api/import/folder", {
    method: "POST",
    body: JSON.stringify({ ...requestContext(), sourceFolder }),
  });
  state.lastImportResult = result;
  state.lists = result.lists || state.lists;
  if (result.activeListId) await activateList(result.activeListId, false);
  renderHome();
  await refreshAdminPage();
  const imported = result.importedFiles?.length || 0;
  const updated = result.updatedFiles?.length || 0;
  const skipped = result.skippedFiles?.length || 0;
  const failed = result.failedFiles?.length || 0;
  const printCandidates = result.printCandidates || [];
  if (els.importPreviewBox) {
    els.importPreviewBox.classList.toggle("success", !failed);
    els.importPreviewBox.classList.toggle("review", Boolean(failed));
    els.importPreviewBox.innerHTML = `
      <strong>Temp folder import complete</strong>
      <span>${imported} new files, ${updated} updated files, ${skipped} unchanged, ${failed} failed.</span>
      ${result.failedFiles?.length ? `<span>${escapeHtml(result.failedFiles.map((file) => `${file.fileName}: ${(file.errors || []).join("; ")}`).join(" | "))}</span>` : ""}
      ${printCandidates.length ? `<button type="button" data-print-import="latest">Print updated package</button>` : ""}
    `;
  }
  if (printCandidates.length) {
    const pieces = printCandidates.reduce((sum, candidate) => sum + Number(candidate.pieceCount || 0), 0);
    if (window.confirm(`${printCandidates.length} new/updated delivery-list package(s) are ready with ${pieces} printable pieces. Print now?`)) {
      openPrintPackage(printCandidates);
    }
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
  if (summary) {
    renderImportHistory(summary.recentImports || []);
    renderAdminDeleteControls();
    if (els.tempFolderInput && !els.tempFolderInput.value && summary.tempDeliveryListsDir) els.tempFolderInput.value = summary.tempDeliveryListsDir;
  }
  state.adminUsers = users?.users || [];
  state.activeSessions = sessions?.sessions || [];
  renderAdminUsers();
  renderAdminStations();
  renderExceptionCenter(exceptions?.exceptions || []);
  renderActiveSessions();
}

function renderImportHistory(imports) {
  if (!els.importHistory) return;
  els.importHistory.innerHTML = imports.length
    ? imports
        .map(
          (entry) => `
            <button type="button" data-print-lists="${escapeHtml((entry.listIds || []).join(","))}">
              <strong>${escapeHtml(entry.sourceName || "Imported delivery list")}</strong>
              <span>${escapeHtml(formatDisplayDate(entry.deliveryDate))} - ${escapeHtml(entry.rowCount)} rows / ${escapeHtml(entry.totalQty)} pieces</span>
              <small>${escapeHtml(entry.importKind || "manual")} by ${escapeHtml(entry.importedBy || "")}</small>
            </button>
          `,
        )
        .join("")
    : `<div><strong>No import history yet</strong><span>Imports from the temp folder or single files will appear here.</span></div>`;
}

function renderAdminDeleteControls() {
  if (!els.deleteDateSelect || !els.deleteListSelect) return;
  const groups = listsByDeliveryDate();
  const selectedDate = els.deleteDateSelect.value || groups[0]?.date || "";
  els.deleteDateSelect.innerHTML = groups
    .map((group) => `<option value="${escapeHtml(group.date)}">${escapeHtml(formatDisplayDate(group.date))}</option>`)
    .join("");
  els.deleteDateSelect.value = groups.some((group) => group.date === selectedDate) ? selectedDate : groups[0]?.date || "";
  const lists = groups.find((group) => group.date === els.deleteDateSelect.value)?.lists || [];
  const selectedList = els.deleteListSelect.value || lists[0]?.id || "";
  els.deleteListSelect.innerHTML = lists
    .map((list) => `<option value="${escapeHtml(list.id)}">${escapeHtml(list.stage)} - ${escapeHtml(list.scanner)}</option>`)
    .join("");
  els.deleteListSelect.value = lists.some((list) => list.id === selectedList) ? selectedList : lists[0]?.id || "";
}

async function deleteSelectedDeliveryList(deleteDate = false) {
  if (!state.backend) return;
  const deliveryDate = els.deleteDateSelect?.value || "";
  const listId = els.deleteListSelect?.value || "";
  if (deleteDate) {
    if (!deliveryDate || !window.confirm(`Delete every stage for ${formatDisplayDate(deliveryDate)}?`)) return;
    const result = await fetchJson("/api/admin/delete-date", {
      method: "POST",
      body: JSON.stringify({ deliveryDate, ...requestContext() }),
    });
    state.lists = result.lists || [];
    if (els.deleteListStatus) els.deleteListStatus.innerHTML = `<strong>Deleted date</strong><span>${escapeHtml(result.deletedCount || 0)} stages removed.</span>`;
  } else {
    if (!listId || !window.confirm("Delete this delivery-list stage?")) return;
    const result = await fetchJson("/api/admin/delete-list", {
      method: "POST",
      body: JSON.stringify({ listId, ...requestContext() }),
    });
    state.lists = result.lists || [];
    if (els.deleteListStatus) els.deleteListStatus.innerHTML = `<strong>Deleted stage</strong><span>${escapeHtml(result.deletedListId || listId)} removed.</span>`;
  }
  if (!state.lists.some((list) => list.id === state.activeListId)) {
    state.activeListId = state.lists[0]?.id || "";
    if (state.activeListId) await activateList(state.activeListId, false);
  }
  renderHome();
  renderDeliveryListSelect();
  renderAdminDeleteControls();
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
                <td>
                  ${hasPermission("manage_roles") ? `
                    <select data-user-role-select="${escapeHtml(user.username)}">
                      ${ROLE_OPTIONS.map((role) => `<option value="${escapeHtml(role)}" ${(user.roles || []).includes(role) ? "selected" : ""}>${escapeHtml(role)}</option>`).join("")}
                    </select>
                  ` : escapeHtml((user.roles || []).join(", "))}
                </td>
                <td>${escapeHtml((user.stageAccess || []).join(", "))}</td>
                <td>${user.active ? "Active" : "Inactive"}</td>
                <td>
                  ${hasPermission("manage_roles") ? `<button type="button" data-update-user-role="${escapeHtml(user.username)}">Save role</button>` : ""}
                  ${user.active && hasPermission("deactivate_users") ? `<button type="button" data-deactivate-user="${escapeHtml(user.username)}">Deactivate</button>` : ""}
                </td>
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

function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer);
  const chunks = [];
  const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    chunks.push(String.fromCharCode(...bytes.subarray(index, index + chunkSize)));
  }
  return btoa(chunks.join(""));
}

async function importDeliveryListFile(file) {
  if (state.backend) {
    let result;
    if (file.name.toLowerCase().endsWith(".json")) {
      const text = await file.text();
      const payload = JSON.parse(text);
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
      result = await fetchJson("/api/import", {
        method: "POST",
        body: JSON.stringify({ payload, fileName: file.name, ...requestContext() }),
      });
    } else {
      const contentBase64 = arrayBufferToBase64(await file.arrayBuffer());
      result = await fetchJson("/api/import/upload", {
        method: "POST",
        body: JSON.stringify({ fileName: file.name, contentBase64, ...requestContext() }),
      });
    }
    state.lastImportResult = result;
    state.lists = result.lists || [];
    await activateList(result.activeListId || state.lists[0]?.id, false);
    renderHome();
    await refreshAdminPage();
    if (els.importPreviewBox) {
      const created = result.createdCount ?? 0;
      const updated = result.updatedCount ?? 0;
      els.importPreviewBox.classList.add("success");
      els.importPreviewBox.classList.remove("review");
      els.importPreviewBox.innerHTML = `
        <strong>Single file import complete</strong>
        <span>${escapeHtml(file.name)} created ${escapeHtml(created)} stages and updated ${escapeHtml(updated)} stages.</span>
        ${result.printCandidates?.length ? `<button type="button" data-print-import="latest">Print imported updates</button>` : ""}
      `;
    }
    const printCandidates = result.printCandidates || [];
    if (printCandidates.length) {
      const pieces = printCandidates.reduce((sum, candidate) => sum + Number(candidate.pieceCount || 0), 0);
      if (window.confirm(`${printCandidates.length} delivery-list package(s) are ready with ${pieces} printable pieces. Print now?`)) {
        openPrintPackage(printCandidates);
      }
    }
  } else {
    const text = await file.text();
    const payload = JSON.parse(text);
    state.lists = createDemoLists(payload);
    setActiveList(state.lists[0]?.id);
    renderHome();
  }
}

async function legacyImportDeliveryListFile(file) {
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
    if (activeElement === els.manualOrderInput || activeElement === els.manualItemInput) return;
    try {
      await activateList(state.activeListId, false);
      if (activeElement === els.scanInput) els.scanInput.focus();
    } catch {
      // Keep polling quiet so scanning is not interrupted.
    }
  }, 38000);
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
  els.deliveryDateSelect?.addEventListener("change", () => {
    const date = els.deliveryDateSelect.value;
    const firstStage = listsByDeliveryDate().find((group) => group.date === date)?.lists?.[0];
    if (firstStage) activateList(firstStage.id).catch((error) => showInlineError(error.message));
  });
  els.deliveryStageSelect?.addEventListener("change", () => {
    activateList(els.deliveryStageSelect.value).catch((error) => showInlineError(error.message));
  });
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
  els.manualScanForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await submitManualScan();
    } catch (error) {
      showInlineError(error.message, false);
    }
  });
  els.printBtn?.addEventListener("click", () => {
    if (state.backend && state.activeListId) {
      openPrintOptions({ listIds: [state.activeListId], date: state.meta?.deliveryDate });
    } else {
      window.print();
    }
  });
  els.printOptionsDate?.addEventListener("change", () => {
    state.printContext = { ...(state.printContext || {}), listIds: [] };
    renderPrintOptionStages();
  });
  els.printOptionsClose?.addEventListener("click", () => closePrintOptions());
  els.printOptionsBackdrop?.addEventListener("click", () => closePrintOptions());
  els.printOptionsSubmit?.addEventListener("click", () => submitPrintOptions());
  els.exportBtn?.addEventListener("click", () => {
    if (state.backend) {
      window.location.href = `/api/export.xlsx?listId=${encodeURIComponent(state.activeListId)}`;
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
  els.folderImportBtn?.addEventListener("click", () => {
    importTempDeliveryFolder().catch((error) => showInlineError(error.message, true));
  });
  els.deleteDateSelect?.addEventListener("change", () => renderAdminDeleteControls());
  els.deleteListBtn?.addEventListener("click", () => deleteSelectedDeliveryList(false).catch((error) => showInlineError(error.message, true)));
  els.deleteDateBtn?.addEventListener("click", () => deleteSelectedDeliveryList(true).catch((error) => showInlineError(error.message, true)));
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
  els.bayMapSearch?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      state.baySearch = els.bayMapSearch.value;
      scrollToBaySearchMatch();
    }
  });
  els.bayStatusFilter?.addEventListener("change", () => {
    state.bayStatusFilter = els.bayStatusFilter.value;
    renderBayMapPage();
  });
  els.bayCategoryFilters?.addEventListener("click", (event) => {
    const target = event.target.closest("[data-bay-category-filter]");
    if (!target) return;
    state.bayCategoryFilter = target.dataset.bayCategoryFilter || "all";
    renderBayMapPage();
  });
  els.bayCheckBtn?.addEventListener("click", () => {
    state.baySearch = els.bayMapSearch?.value || "";
    scrollToBaySearchMatch();
  });
  els.bayMapCanvas?.addEventListener("click", (event) => {
    const target = event.target.closest("[data-bay-code]");
    if (!target) return;
    selectBay(target.dataset.bayCode || "");
  });
  els.bayActionButtons?.addEventListener("click", (event) => {
    const target = event.target.closest("[data-bay-action]");
    if (!target) return;
    runBayAction(target.dataset.bayAction).catch((error) => showInlineError(error.message, true));
  });
  els.sdiCloseBtn?.addEventListener("click", () => closeSdiPanel());
  els.sdiClearBtn?.addEventListener("click", () => submitSdi(false).catch((error) => showInlineError(error.message, true)));
  els.sdiForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    submitSdi(true).catch((error) => showInlineError(error.message, true));
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
    const updateUserRoleButton = event.target.closest("[data-update-user-role]");
    if (updateUserRoleButton) {
      const username = updateUserRoleButton.dataset.updateUserRole;
      const select = document.querySelector(`[data-user-role-select="${CSS.escape(username)}"]`);
      fetchJson("/api/admin/users/roles", {
        method: "POST",
        body: JSON.stringify({ username, roles: [select?.value || "Operator"] }),
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
    const printImportButton = event.target.closest("[data-print-import]");
    if (printImportButton) {
      openPrintPackage(state.lastImportResult?.printCandidates || []);
      return;
    }
    const printListsButton = event.target.closest("[data-print-lists]");
    if (printListsButton?.dataset.printLists) {
      window.open(`/api/print/package?listId=${encodeURIComponent(printListsButton.dataset.printLists)}`, "_blank", "noopener");
      return;
    }
    const printActiveButton = event.target.closest("[data-print-active]");
    if (printActiveButton) {
      const date = printActiveButton.dataset.printActive === "home" || printActiveButton.dataset.printActive === "bays" ? dashboardDateKey() : state.meta?.deliveryDate;
      const listIds = state.lists.filter((list) => !date || list.deliveryDate === date).map((list) => list.id);
      openPrintOptions({ date, listIds });
      return;
    }
    const bayCell = event.target.closest("[data-bay-code]");
    if (bayCell?.dataset.bayCode) {
      if (els.bayMapCanvas?.contains(bayCell)) return;
      selectBay(bayCell.dataset.bayCode || "");
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
