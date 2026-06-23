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
  overviewRange: "30",
  homePageIndex: 1,
  homePageSize: 25,
  expandedDeliveryDate: "",
  collapsedGlassTypes: new Set(),
  baySearch: "",
  bayStatusFilter: "all",
  bayCategoryFilter: "all",
  selectedBayCode: "",
  bayEditMode: false,
  pendingBayMove: null,
  collapsedBaySections: new Set(),
  bayActionUndoStack: [],
  bayActionRedoStack: [],
  bayLayoutUndoStack: [],
  bayLayoutRedoStack: [],
  bayLayoutDraft: null,
  bayLayoutOriginal: null,
  bayHoldingSections: new Set(),
  bayGroupColumns: {},
  printContext: null,
  lastImportResult: null,
  bayLayout: null,
  bays: [],
  bayEvents: [],
  adminCustomerRouteRules: [],
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
  globalPrintExportBtn: document.getElementById("globalPrintExportBtn"),

  homePage: document.getElementById("homePage"),
  homeWelcome: document.getElementById("homeWelcome"),
  overviewStats: document.getElementById("overviewStats"),
  overviewRangeSelect: document.getElementById("overviewRangeSelect"),
  homeUserCard: document.getElementById("homeUserCard"),
  homeRecentLists: document.getElementById("homeRecentLists"),
  homeActivity: document.getElementById("homeActivity"),
  homeListSearch: document.getElementById("homeListSearch"),
  homeStageFilter: document.getElementById("homeStageFilter"),
  homeListGrid: document.getElementById("homeListGrid"),
  homeListCount: document.getElementById("homeListCount"),
  homePageSize: document.getElementById("homePageSize"),
  homePager: document.getElementById("homePager"),
  homePagerTop: document.getElementById("homePagerTop"),
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
  manualAssignPanel: document.getElementById("manualAssignPanel"),
  manualAssignForm: document.getElementById("manualAssignForm"),
  manualAssignOrderInput: document.getElementById("manualAssignOrderInput"),
  manualAssignItemInput: document.getElementById("manualAssignItemInput"),
  manualAssignQtyInput: document.getElementById("manualAssignQtyInput"),
  manualAssignStatus: document.getElementById("manualAssignStatus"),
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
  countRemakes: document.getElementById("countRemakes"),
  countRushes: document.getElementById("countRushes"),
  countUpdated: document.getElementById("countUpdated"),
  countErrors: document.getElementById("countErrors"),
  countIndianTrailRoute: document.getElementById("countIndianTrailRoute"),
  countCpuRoute: document.getElementById("countCpuRoute"),
  countDtcRoute: document.getElementById("countDtcRoute"),
  countGreenvilleRoute: document.getElementById("countGreenvilleRoute"),
  remainingQty: document.getElementById("remainingQty"),
  partialQty: document.getElementById("partialQty"),
  completeQty: document.getElementById("completeQty"),
  errorQty: document.getElementById("errorQty"),
  remainingPct: document.getElementById("remainingPct"),
  partialPct: document.getElementById("partialPct"),
  completePct: document.getElementById("completePct"),
  pageSize: document.getElementById("pageSize"),
  pageSizeBottom: document.getElementById("pageSizeBottom"),
  scanPagerTop: document.getElementById("scanPagerTop"),
  scanPagerBottom: document.getElementById("scanPagerBottom"),
  undoBtn: document.getElementById("undoBtn"),
  redoBtn: document.getElementById("redoBtn"),

  bayMapPage: document.getElementById("bayMapPage"),
  bayOverviewStats: document.getElementById("bayOverviewStats"),
  bayMapSearch: document.getElementById("bayMapSearch"),
  bayScanOutForm: document.getElementById("bayScanOutForm"),
  bayScanOutInput: document.getElementById("bayScanOutInput"),
  bayScanBayInput: document.getElementById("bayScanBayInput"),
  bayScanModeToggle: document.getElementById("bayScanModeToggle"),
  bayManualOrderInput: document.getElementById("bayManualOrderInput"),
  bayManualItemInput: document.getElementById("bayManualItemInput"),
  bayManualQtyInput: document.getElementById("bayManualQtyInput"),
  bayManualSubmitBtn: document.getElementById("bayManualSubmitBtn"),
  bayScanOutStatus: document.getElementById("bayScanOutStatus"),
  bayScanOutRecent: document.getElementById("bayScanOutRecent"),
  bayUndoBtn: document.getElementById("bayUndoBtn"),
  bayRedoBtn: document.getElementById("bayRedoBtn"),
  bayStatusFilter: document.getElementById("bayStatusFilter"),
  bayCategoryFilters: document.getElementById("bayCategoryFilters"),
  baySelectedPanel: document.getElementById("baySelectedPanel"),
  baySelectedModal: document.getElementById("baySelectedModal"),
  baySelectedBackdrop: document.getElementById("baySelectedBackdrop"),
  baySelectedCloseBtn: document.getElementById("baySelectedCloseBtn"),
  bayAllBaysList: document.getElementById("bayAllBaysList"),
  bayCheckBtn: document.getElementById("bayCheckBtn"),
  bayFlowPanel: document.getElementById("bayFlowPanel"),
  indianTrailSummary: document.getElementById("indianTrailSummary"),
  bayActionButtons: document.getElementById("bayActionButtons"),
  bayMapCanvas: document.getElementById("bayMapCanvas"),
  baySelectedText: document.getElementById("baySelectedText"),
  sdiPanel: document.getElementById("sdiPanel"),
  sdiBackdrop: document.getElementById("sdiBackdrop"),
  sdiForm: document.getElementById("sdiForm"),
  sdiCloseBtn: document.getElementById("sdiCloseBtn"),
  sdiClearBtn: document.getElementById("sdiClearBtn"),
  sdiOrderInput: document.getElementById("sdiOrderInput"),
  sdiBayInput: document.getElementById("sdiBayInput"),
  sdiTruckExemptInput: document.getElementById("sdiTruckExemptInput"),
  sdiReasonInput: document.getElementById("sdiReasonInput"),
  sdiTypeInput: document.getElementById("sdiTypeInput"),
  sdiCurrentList: document.getElementById("sdiCurrentList"),
  bayLayoutManager: document.getElementById("bayLayoutManager"),
  bayLayoutCloseBtn: document.getElementById("bayLayoutCloseBtn"),
  bayLayoutSelect: document.getElementById("bayLayoutSelect"),
  bayLayoutDisplayInput: document.getElementById("bayLayoutDisplayInput"),
  bayLayoutSectionInput: document.getElementById("bayLayoutSectionInput"),
  bayLayoutCategoryInput: document.getElementById("bayLayoutCategoryInput"),
  bayLayoutRowInput: document.getElementById("bayLayoutRowInput"),
  bayLayoutColInput: document.getElementById("bayLayoutColInput"),
  bayLayoutCapacityInput: document.getElementById("bayLayoutCapacityInput"),
  bayLayoutActiveInput: document.getElementById("bayLayoutActiveInput"),
  bayLayoutSaveBtn: document.getElementById("bayLayoutSaveBtn"),
  bayLayoutDeleteBtn: document.getElementById("bayLayoutDeleteBtn"),
  bayLayoutUndoBtn: document.getElementById("bayLayoutUndoBtn"),
  bayLayoutRedoBtn: document.getElementById("bayLayoutRedoBtn"),
  bayCollapseAllBtn: document.getElementById("bayCollapseAllBtn"),
  bayExpandAllBtn: document.getElementById("bayExpandAllBtn"),
  bayHoldAllBtn: document.getElementById("bayHoldAllBtn"),
  bayLayoutConfirmBtn: document.getElementById("bayLayoutConfirmBtn"),
  bayLayoutCancelBtn: document.getElementById("bayLayoutCancelBtn"),

  printOptionsPanel: document.getElementById("printOptionsPanel"),
  printOptionsBackdrop: document.getElementById("printOptionsBackdrop"),
  printOptionsDate: document.getElementById("printOptionsDate"),
  printOptionsStages: document.getElementById("printOptionsStages"),
  printOptionsGlassType: document.getElementById("printOptionsGlassType"),
  printMirrorMode: document.getElementById("printMirrorMode"),
  printCustomerFilter: document.getElementById("printCustomerFilter"),
  printOrderFilter: document.getElementById("printOrderFilter"),
  printUpdatedOnly: document.getElementById("printUpdatedOnly"),
  printRushOnly: document.getElementById("printRushOnly"),
  printRemakeOnly: document.getElementById("printRemakeOnly"),
  printOptionsClose: document.getElementById("printOptionsClose"),
  printOptionsSubmit: document.getElementById("printOptionsSubmit"),

  adminPage: document.getElementById("adminPage"),
  adminSummary: document.getElementById("adminSummary"),
  folderImportBtn: document.getElementById("folderImportBtn"),
  importBtn: document.getElementById("importBtn"),
  checkUpdatesBtn: document.getElementById("checkUpdatesBtn"),
  importFile: document.getElementById("importFile"),
  tempFolderInput: document.getElementById("tempFolderInput"),
  importPreviewBox: document.getElementById("importPreviewBox"),
  importHistory: document.getElementById("importHistory"),
  importFromDate: document.getElementById("importFromDate"),
  importToDate: document.getElementById("importToDate"),
  importWindowResetBtn: document.getElementById("importWindowResetBtn"),
  deleteDateSelect: document.getElementById("deleteDateSelect"),
  deleteListSelect: document.getElementById("deleteListSelect"),
  deleteListBtn: document.getElementById("deleteListBtn"),
  deleteDateBtn: document.getElementById("deleteDateBtn"),
  deleteListStatus: document.getElementById("deleteListStatus"),
  resetListSelect: document.getElementById("resetListSelect"),
  adminResetScansBtn: document.getElementById("adminResetScansBtn"),
  resetScansStatus: document.getElementById("resetScansStatus"),
  createUserForm: document.getElementById("createUserForm"),
  newUserName: document.getElementById("newUserName"),
  newUserDisplay: document.getElementById("newUserDisplay"),
  newUserPassword: document.getElementById("newUserPassword"),
  newUserRole: document.getElementById("newUserRole"),
  adminUsers: document.getElementById("adminUsers"),
  newStationInput: document.getElementById("newStationInput"),
  addStationBtn: document.getElementById("addStationBtn"),
  adminStations: document.getElementById("adminStations"),
  customerRouteRuleForm: document.getElementById("customerRouteRuleForm"),
  customerRoutePatternInput: document.getElementById("customerRoutePatternInput"),
  customerRouteSelect: document.getElementById("customerRouteSelect"),
  customerRouteRules: document.getElementById("customerRouteRules"),
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

function formatDateTime(value) {
  if (!value) return "";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString();
}

function todayKey() {
  const now = new Date();
  return `${now.getFullYear()}-${pad(now.getMonth() + 1, 2)}-${pad(now.getDate(), 2)}`;
}

function dateInputValue(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1, 2)}-${pad(date.getDate(), 2)}`;
}

function resetImportDateWindow() {
  const from = new Date();
  from.setDate(from.getDate() - 7);
  const to = new Date();
  to.setFullYear(to.getFullYear() + 1);
  if (els.importFromDate) els.importFromDate.value = dateInputValue(from);
  if (els.importToDate) els.importToDate.value = dateInputValue(to);
}

function parseDateKey(value) {
  const parts = String(value || "").split("-").map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) return null;
  return new Date(parts[0], parts[1] - 1, parts[2]);
}

function filterListsByOverviewRange(lists = state.lists) {
  if (state.overviewRange === "all") return lists.slice();
  const days = Number(state.overviewRange || 30);
  if (!days) return lists.slice();
  const end = new Date();
  end.setHours(23, 59, 59, 999);
  const start = new Date(end);
  start.setDate(start.getDate() - days + 1);
  start.setHours(0, 0, 0, 0);
  return lists.filter((list) => {
    const date = parseDateKey(list.deliveryDate);
    return date && date >= start && date <= end;
  });
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

function formatPercent(value) {
  return `${Math.round(Number(value || 0))}%`;
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
  if (category === "dtc") return "Delivery to Customer";
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

function itemText(item) {
  return [item.product, item.job, item.customer, item.route, item.processState, item.queueState, item.suggestedBay].join(" ");
}

function isRemakeItem(item) {
  return /\b(REMAKE|RM)\b/i.test(itemText(item));
}

function isRushItem(item) {
  return /\b(RUSH|SDI)\b/i.test(itemText(item));
}

function isRemakeOrRush(item) {
  return isRemakeItem(item) || isRushItem(item);
}

function isNewOrUpdatedItem(item) {
  return /\b(NEW LINE|NEW|UPDATED|UPDATE|CHANGED|CHANGE)\b/i.test(`${item.processState || ""} ${item.queueState || ""}`);
}

function unresolvedPriorityItems(items = state.items) {
  return items.filter((item) => isRemakeOrRush(item) && itemStatus(item) !== "complete");
}

function unresolvedRemakeItems(items = state.items) {
  return items.filter((item) => isRemakeItem(item) && itemStatus(item) !== "complete");
}

function unresolvedRushItems(items = state.items) {
  return items.filter((item) => isRushItem(item) && itemStatus(item) !== "complete");
}

function scanFlash(kind = "notice") {
  const className = kind === "success" ? "scan-flash-success" : kind === "error" ? "scan-flash-error" : "scan-flash-notice";
  document.body.classList.remove("scan-flash-success", "scan-flash-error", "scan-flash-notice");
  void document.body.offsetWidth;
  document.body.classList.add(className);
  window.setTimeout(() => document.body.classList.remove(className), 900);
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
      (state.filter === "errors" && errorItemIds.has(item.id)) ||
      (state.filter === "remakes" && isRemakeItem(item)) ||
      (state.filter === "rushes" && isRushItem(item)) ||
      (state.filter === "priority" && isRemakeOrRush(item)) ||
      (state.filter === "updated" && isNewOrUpdatedItem(item)) ||
      (state.filter === "cpu-route" && /\bCPU\b|customer pickup/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`)) ||
      (state.filter === "dtc-route" && /\bDTC\b|deliver to customer/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`)) ||
      (state.filter === "greenville-route" && /\bGNV\b|greenville/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`)) ||
      (state.filter === "indian-trail-route" && !/\bCPU\b|\bDTC\b|\bGNV\b|customer pickup|deliver to customer|greenville/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`));
    if (!matchesFilter) return false;
    if (!search) return true;
    const haystack = [item.order, item.item, item.job, item.customer, item.dimensions, item.product, item.route, item.barcode]
      .join(" ")
      .toLowerCase();
    return haystack.includes(search);
  });
}

function groupItemsByGlass(items) {
  const groups = new Map();
  for (const item of items) {
    const label = glassTypeLabel(item);
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label).push(item);
  }
  return [...groups.entries()].map(([label, items]) => ({ label, items }));
}

function getPagedItems() {
  const rows = filteredItems();
  const groups = groupItemsByGlass(rows);
  const groupPages = [];
  let currentPage = [];
  let currentCount = 0;
  for (const group of groups) {
    const groupCount = group.items.length;
    if (currentPage.length && currentCount + groupCount > state.pageSize) {
      groupPages.push(currentPage);
      currentPage = [];
      currentCount = 0;
    }
    currentPage.push(group);
    currentCount += groupCount;
  }
  if (currentPage.length || !groupPages.length) groupPages.push(currentPage);
  const totalPages = Math.max(1, groupPages.length);
  state.pageIndex = Math.min(Math.max(state.pageIndex, 1), totalPages);
  const pageGroups = groupPages[state.pageIndex - 1] || [];
  const pageRows = pageGroups.flatMap((group) => group.items);
  return { rows, pageRows, pageGroups, totalPages };
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
  const remakeOpen = unresolvedRemakeItems().length;
  const remakeAll = state.items.filter(isRemakeItem).length;
  const rushOpen = unresolvedRushItems().length;
  const rushAll = state.items.filter(isRushItem).length;
  const updatedCount = state.items.filter(isNewOrUpdatedItem).length;
  const routeCounts = {
    "indian-trail-route": state.items.filter((item) => !/\bCPU\b|\bDTC\b|\bGNV\b|customer pickup|deliver to customer|greenville/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`)).length,
    "cpu-route": state.items.filter((item) => /\bCPU\b|customer pickup/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`)).length,
    "dtc-route": state.items.filter((item) => /\bDTC\b|deliver to customer/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`)).length,
    "greenville-route": state.items.filter((item) => /\bGNV\b|greenville/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`)).length,
  };
  if (els.countAll) els.countAll.textContent = `(${totalItems})`;
  if (els.countRemaining) els.countRemaining.textContent = `(${stats.remainingItems})`;
  if (els.countPartial) els.countPartial.textContent = `(${stats.partialItems})`;
  if (els.countComplete) els.countComplete.textContent = `(${stats.completeItems})`;
  if (els.countRemakes) els.countRemakes.textContent = `(${remakeAll})`;
  if (els.countRushes) els.countRushes.textContent = `(${rushAll})`;
  document.querySelectorAll('[data-filter="remakes"]').forEach((button) => {
    button.classList.toggle("has-alert", Boolean(remakeOpen));
    button.classList.toggle("is-clear", !remakeOpen);
  });
  document.querySelectorAll('[data-filter="rushes"]').forEach((button) => {
    button.classList.toggle("has-alert", Boolean(rushOpen));
    button.classList.toggle("is-clear", !rushOpen);
  });
  if (els.countUpdated) els.countUpdated.textContent = `(${updatedCount})`;
  if (els.countErrors) els.countErrors.textContent = `(${stats.errorCount})`;
  if (els.countIndianTrailRoute) els.countIndianTrailRoute.textContent = `(${routeCounts["indian-trail-route"]})`;
  if (els.countCpuRoute) els.countCpuRoute.textContent = `(${routeCounts["cpu-route"]})`;
  if (els.countDtcRoute) els.countDtcRoute.textContent = `(${routeCounts["dtc-route"]})`;
  if (els.countGreenvilleRoute) els.countGreenvilleRoute.textContent = `(${routeCounts["greenville-route"]})`;
  document.querySelectorAll(".route-filter-tab").forEach((button) => {
    const count = routeCounts[button.dataset.filter] || 0;
    button.hidden = count === 0;
  });
  if (state.filter.endsWith("-route") && !routeCounts[state.filter]) {
    state.filter = "all";
    document.querySelectorAll("[data-filter]").forEach((button) => button.classList.toggle("is-active", button.dataset.filter === state.filter));
  }
  if (els.totalItemsText) els.totalItemsText.textContent = `${totalItems} total items`;
  if (els.progressText) els.progressText.textContent = `${stageVerb()} Qty: ${stats.scannedQty}/${stats.totalQty} - ${formatPercent(stats.percent)} Complete`;
  if (els.progressFill) els.progressFill.style.width = `${Math.min(stats.percent, 100)}%`;
  if (els.remainingQty) els.remainingQty.textContent = String(stats.remainingQty);
  if (els.partialQty) els.partialQty.textContent = String(stats.partialItems);
  if (els.completeQty) els.completeQty.textContent = String(stats.completeItems);
  if (els.errorQty) els.errorQty.textContent = String(stats.errorCount);
  if (els.remainingPct) els.remainingPct.textContent = formatPercent(100 - stats.percent);
  if (els.partialPct) els.partialPct.textContent = formatPercent(stats.totalQty ? (stats.partialItems / Math.max(state.items.length, 1)) * 100 : 0);
  if (els.completePct) els.completePct.textContent = formatPercent(stats.percent);
}

function renderPagers(totalRows, totalPages) {
  if (els.pageSize && Number(els.pageSize.value) !== state.pageSize) els.pageSize.value = String(state.pageSize);
  if (els.pageSizeBottom && Number(els.pageSizeBottom.value) !== state.pageSize) els.pageSizeBottom.value = String(state.pageSize);
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

function glassTypeLabel(item) {
  return String(item.product || item.job || item.suggestedBay || "Other Glass").trim() || "Other Glass";
}

function renderItemRow(item) {
  const status = itemStatus(item);
  const selected = item.id === state.selectedId;
  const route = routeLabel(item);
  const routeTag = route ? `<span class="route-tag ${escapeHtml(route.toLowerCase())}">${escapeHtml(route)}</span>` : "";
  const markers = [
    isRemakeItem(item) ? '<span class="rush-marker remake-marker" title="Remake">RM</span>' : "",
    isRushItem(item) ? '<span class="rush-marker" title="Rush">!</span>' : "",
  ].join("");
  return `
    <tr class="${selected ? "is-selected" : ""} ${status === "complete" ? "is-complete" : ""} ${isNewOrUpdatedItem(item) ? "is-new-line" : ""}" data-id="${escapeHtml(item.id)}">
      <td><span class="job-title">${escapeHtml(item.product || item.job)}</span><span class="job-subtitle">${escapeHtml(item.job)}</span></td>
      <td>${escapeHtml(item.order)}</td>
      <td>${escapeHtml(item.item)}</td>
      <td><span class="qty-pill ${status}">${item.scanned} / ${item.qty}</span></td>
      <td>${escapeHtml(item.dimensions)}</td>
      <td>${escapeHtml(item.customer)}</td>
      <td>${markers}</td>
      <td>${routeTag}</td>
      <td><span class="process-pill ${status}">${escapeHtml(renderProcessState(item))}</span></td>
    </tr>
  `;
}

function renderTable() {
  if (!els.listRows) return;
  const { rows, pageGroups, totalPages } = getPagedItems();
  renderPagers(rows.length, totalPages);
  if (!pageGroups.length) {
    els.listRows.innerHTML = `<tr><td colspan="9">No rows match the current filters.</td></tr>`;
    return;
  }
  els.listRows.innerHTML = pageGroups
    .map(({ label, items: groupItems }) => {
      const totalQty = groupItems.reduce((sum, item) => sum + Number(item.qty || 0), 0);
      const scannedQty = groupItems.reduce((sum, item) => sum + Math.min(Number(item.scanned || 0), Number(item.qty || 0)), 0);
      const updatedCount = groupItems.filter(isNewOrUpdatedItem).length;
      const collapsed = state.collapsedGlassTypes.has(label);
      return `
        <tr class="glass-group-row" data-glass-group="${escapeHtml(label)}">
          <td colspan="9">
            <button type="button" data-toggle-glass-group="${escapeHtml(label)}">
              <strong>${escapeHtml(label)}${updatedCount ? ` <span class="new-line-marker group-marker" title="New or updated lines">${escapeHtml(updatedCount)} New</span>` : ""}</strong>
              <span>${escapeHtml(scannedQty)} / ${escapeHtml(totalQty)} pieces</span>
              <small>${collapsed ? "Expand" : "Collapse"}</small>
            </button>
          </td>
        </tr>
        ${collapsed ? "" : groupItems.map(renderItemRow).join("")}
      `;
    })
    .join("");
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
      <button class="tab ${state.filter === "remakes" ? "is-active" : ""}" data-filter="remakes" type="button">Remakes (${state.items.filter(isRemakeItem).length})</button>
      <button class="tab ${state.filter === "rushes" ? "is-active" : ""}" data-filter="rushes" type="button">Rushes (${state.items.filter(isRushItem).length})</button>
      <button class="tab ${state.filter === "updated" ? "is-active" : ""}" data-filter="updated" type="button">Updated (${state.items.filter(isNewOrUpdatedItem).length})</button>
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
  const scanMessage = [entry.message, entry.reason].filter(Boolean).join(" - ");
  if (els.lastJob) els.lastJob.textContent = scanMessage && !entry.ok ? scanMessage : entry.item ? entry.item.job : entry.message;
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
          const note = [entry.message, entry.reason].filter(Boolean).join(" - ");
          return `
            <tr class="${entry.ok ? "ok" : "error"}">
              <td><strong>${escapeHtml(entry.barcode)}</strong>${note ? `<small class="scan-row-note">${escapeHtml(note)}</small>` : ""}</td>
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
  setControlAllowed(els.globalPrintExportBtn, hasPermission("export_reports"), true);
  setControlAllowed(els.undoBtn, hasPermission("undo_scan"), true);
  setControlAllowed(els.redoBtn, hasPermission("undo_scan"), true);
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
  renderLastScan();
  renderManualAssignTools();
  applyPermissionUi();
}

function isIndianTrailScanContext() {
  return /indian trail|inbound/i.test(`${state.meta?.stage || ""} ${state.meta?.scanner || ""}`);
}

function renderManualAssignTools() {
  if (!els.manualAssignPanel) return;
  els.manualAssignPanel.hidden = true;
}

function compatibleBayCandidates(item) {
  const suggested = String(item?.suggestedBay || item?.product || "").toLowerCase();
  const targetKind =
    suggested.includes("mirror") && suggested.includes("framed") ? "framed-mirror" :
    suggested.includes("mirror") ? "mirror" :
    suggested.includes("crl") ? "crl" :
    suggested.includes("shower") || suggested.includes("tempered") ? "showers" :
    "";
  return (state.bays || [])
    .filter((bay) => bayStatusKind(bay) === "available")
    .filter((bay) => !targetKind || bayCategoryKind(bay) === targetKind || bayCategoryKind(bay) === "standard")
    .slice(0, 16);
}

async function submitManualBayAssign() {
  const order = digitsOnly(els.manualAssignOrderInput?.value || "");
  const itemNo = digitsOnly(els.manualAssignItemInput?.value || "");
  const qty = Math.max(1, Number(els.manualAssignQtyInput?.value || 1));
  if (!order) {
    showInlineError("Manual bay assign needs an order number.", false);
    return;
  }
  if (!state.bays.length && state.backend) {
    const payload = await fetchJson("/api/indian-trail/bays");
    state.bays = payload.bays || [];
  }
  const matches = state.items.filter((item) => digitsOnly(item.order) === order && (!itemNo || digitsOnly(item.item) === itemNo));
  if (matches.length !== 1) {
    if (els.manualAssignStatus) {
      els.manualAssignStatus.innerHTML = `<article class="message-card review"><strong>${matches.length ? "Multiple matches" : "No match"}</strong><span>Enter an item number to pick one exact row.</span></article>`;
    }
    return;
  }
  const item = matches[0];
  const bays = compatibleBayCandidates(item);
  if (els.manualAssignStatus) {
    els.manualAssignStatus.innerHTML = bays.length
      ? `<article class="message-card notice"><strong>Choose a bay for ${escapeHtml(item.order)}-${escapeHtml(item.item)}</strong><span>${escapeHtml(item.customer)} - Qty ${qty}</span></article>
         <div class="bay-picker">${bays.map((bay) => `<button type="button" data-manual-assign-bay="${escapeHtml(bay.bayCode)}" data-line-item-id="${escapeHtml(item.id)}" data-assigned-qty="${escapeHtml(qty)}">${escapeHtml(bay.displayName || bay.bayCode)}</button>`).join("")}</div>`
      : `<article class="message-card review"><strong>No empty compatible bay found</strong><span>Use the Bay Map to free a bay or pick manually.</span></article>`;
  }
}

function miniStat(label, value, detail = "") {
  return `<div class="mini-stat"><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong>${detail ? `<span>${escapeHtml(detail)}</span>` : ""}</div>`;
}

function aggregateListStats(lists) {
  const totalLists = lists.length;
  const totalItems = lists.reduce((sum, list) => sum + Number(list.itemCount || 0), 0);
  const totalQty = lists.reduce((sum, list) => sum + Number(list.totalQty || 0), 0);
  const pieceQty = lists.reduce((maxQty, list) => Math.max(maxQty, Number(list.totalQty || 0)), 0);
  const scannedQty = lists.reduce((sum, list) => sum + Number(list.scannedQty || 0), 0);
  const outboundLists = lists.filter((list) => stageCategory(list) === "outbound");
  const timingLists = outboundLists.length ? outboundLists : lists;
  const onTimeQty = timingLists.reduce((sum, list) => sum + Number(list.onTimeQty || 0), 0);
  const lateQty = timingLists.reduce((sum, list) => sum + Number(list.lateQty || 0), 0);
  const timedQty = onTimeQty + lateQty;
  return {
    totalLists,
    totalItems,
    totalQty,
    pieceQty,
    scannedQty,
    remainingQty: Math.max(totalQty - scannedQty, 0),
    deliveryPercent: totalQty ? (scannedQty / totalQty) * 100 : 0,
    onTimeQty,
    lateQty,
    onTimePercent: timedQty ? (onTimeQty / timedQty) * 100 : 0,
  };
}

function stageProgressSegments(lists) {
  const total = lists.reduce((sum, list) => sum + Number(list.totalQty || 0), 0);
  if (!total) return [];
  const order = ["staged", "outbound", "received", "pickup", "greenville", "dtc"];
  const buckets = new Map();
  for (const list of lists) {
    const category = stageCategory(list);
    const current = buckets.get(category) || { category, label: stageLabel(list), qty: 0 };
    current.qty += Number(list.scannedQty || 0);
    buckets.set(category, current);
  }
  return [...buckets.values()]
    .sort((a, b) => order.indexOf(a.category) - order.indexOf(b.category))
    .map((segment) => ({ ...segment, percent: Math.min((segment.qty / total) * 100, 100) }));
}

function progressWidth(percent) {
  const value = Math.min(Math.max(Number(percent || 0), 0), 100);
  return value > 0 ? Math.max(value, 1.25) : 0;
}

function renderStackedProgress(lists, stats) {
  const segments = stageProgressSegments(lists);
  const segmentHtml = segments.length
    ? segments.map((segment) => `<span class="stage-segment ${escapeHtml(segment.category)}" style="width:${progressWidth(segment.percent)}%;" title="${escapeHtml(segment.label)} ${segment.qty}"></span>`).join("")
    : `<span style="width:0%"></span>`;
  return `
    <div class="progress-line">
      <span>Progress:</span>
      <div class="list-card-progress stacked">${segmentHtml}</div>
      <strong>${formatPercent(stats.deliveryPercent)}</strong>
    </div>
  `;
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
  const title = stageLabel(list);
  const onTimeText = category === "outbound" ? ` - On-time ${formatPercent(onTime)}` : "";
  return `
    <article class="delivery-list-card ${escapeHtml(category)} ${escapeHtml(extraClass)}" data-open-list="${escapeHtml(list.id)}">
      <div class="delivery-card-main">
        <strong>${escapeHtml(title)}</strong>
      </div>
      <small class="delivery-card-meta">${escapeHtml(list.totalQty || 0)} pieces - ${escapeHtml(list.scannedQty || 0)}/${escapeHtml(list.totalQty || 0)} scanned${onTimeText}</small>
      <div class="progress-line delivery-card-progress"><span>Progress:</span><div class="list-card-progress"><span style="width:${progressWidth(percent)}%"></span></div><strong>${formatPercent(percent)}</strong></div>
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
              <small>${formatPercent(percent)}</small>
            </article>
          `;
        })
        .join("")
    : `<div class="admin-empty">No delivery lists are loaded for ${formatDisplayDate(key)}.</div>`;
}

function renderHome() {
  if (!els.homePage) return;
  const overviewLists = filterListsByOverviewRange(state.lists);
  const overview = aggregateListStats(overviewLists);
  if (els.homeWelcome) {
    els.homeWelcome.textContent = `Signed in as ${state.user?.displayName || state.user?.username || "Demo user"}`;
  }
  if (els.overviewRangeSelect && els.overviewRangeSelect.value !== state.overviewRange) {
    els.overviewRangeSelect.value = state.overviewRange;
  }
  if (els.overviewStats) {
    els.overviewStats.innerHTML = [
      miniStat("Delivery %", formatPercent(overview.deliveryPercent), `${overview.scannedQty}/${overview.totalQty} scanned`),
      miniStat("On-Time %", formatPercent(overview.onTimePercent), `${overview.onTimeQty} on time`),
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
  const totalHomePages = Math.max(1, Math.ceil(dateGroups.length / state.homePageSize));
  state.homePageIndex = Math.min(Math.max(state.homePageIndex, 1), totalHomePages);
  const pageStart = (state.homePageIndex - 1) * state.homePageSize;
  const visibleDateGroups = dateGroups.slice(pageStart, pageStart + state.homePageSize);
  if (!dateGroups.some((group) => group.date === state.expandedDeliveryDate)) {
    state.expandedDeliveryDate = visibleDateGroups[0]?.date || dateGroups[0]?.date || "";
  }
  if (els.homeListCount) els.homeListCount.textContent = `${dateGroups.length} dates / ${filtered.length} stages`;
  if (els.homeListGrid) {
    els.homeListGrid.innerHTML = visibleDateGroups.length
      ? visibleDateGroups
          .map((group) => {
            const stats = aggregateListStats(group.lists);
            return `
              <details class="delivery-date-group" data-delivery-date="${escapeHtml(group.date)}" ${group.date === state.expandedDeliveryDate ? "open" : ""}>
                <summary>
                  <span>
                    <strong>${escapeHtml(formatDisplayDate(group.date))}</strong>
                    <small>${escapeHtml(group.lists.length)} stages - Delivery on-time ${formatPercent(stats.onTimePercent)}</small>
                    ${renderStackedProgress(group.lists, stats)}
                  </span>
                  <span class="delivery-date-total"><small>Pieces</small><strong>${escapeHtml(stats.pieceQty || stats.totalQty)}</strong></span>
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
  if (els.homePager) {
    const pagerHtml = `
      <button type="button" data-home-page-action="prev" ${state.homePageIndex <= 1 ? "disabled" : ""}>&lt;</button>
      <span class="pager-summary">Page ${state.homePageIndex} of ${totalHomePages}</span>
      <button type="button" data-home-page-action="next" ${state.homePageIndex >= totalHomePages ? "disabled" : ""}>&gt;</button>
    `;
    els.homePager.innerHTML = pagerHtml;
    if (els.homePagerTop) els.homePagerTop.innerHTML = pagerHtml;
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
  if (state.bayEditMode && state.bayHoldingSections.size && page !== "bays") {
    showFloatingNotice("Move all grouped bays out of the temporary holding area before leaving the Bay Map.", "error");
    return;
  }
  if (page === "admin" && !hasAnyPermission(["view_admin", "manage_users", "manage_stations", "edit_delivery_lists"])) page = "home";
  if (page === "bays" && !hasAnyPermission(["view_bays", "view_indian_trail"])) page = "home";
  state.page = page;
  document.body.dataset.page = page;
  window.scrollTo({ top: 0, left: 0, behavior: "auto" });
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
      scanFlash(result.ok ? "success" : "error");
      if (result?.message) {
        showFloatingNotice(result.message, result.ok ? (/\bSDI|Rush\b/i.test(result.message) ? "notice" : "success") : "error");
      }
      renderScanPage();
      void refreshBayMapPage().catch(() => {});
      return;
    }
    const payload = await fetchJson("/api/scans", {
      method: "POST",
      body: JSON.stringify({ listId: state.activeListId, barcode: scanText, ...requestContext() }),
    });
    applyBackendPayload(payload);
    scanFlash(payload.lastScan?.ok ? "success" : payload.lastScan?.eventType === "duplicate" || payload.lastScan?.eventType === "notice" ? "notice" : "error");
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
    scanFlash("error");
    saveState();
    renderScanPage();
    return;
  }
  const item = recovered.item;
  if (item.scanned >= item.qty) {
    const entry = { ok: false, eventType: "duplicate", barcode: recovered.barcode, item, message: "Item already complete", reason: "Quantity already scanned", time: timestamp };
    state.recent.unshift(entry);
    state.lastScan = entry;
    scanFlash("notice");
    saveState();
    renderScanPage();
    return;
  }
  item.scanned += 1;
  state.selectedId = item.id;
  const entry = { ok: true, eventType: "scan", barcode: recovered.barcode, raw: scanText, item, message: recovered.reason, time: timestamp };
  state.recent.unshift(entry);
  state.lastScan = entry;
  scanFlash("success");
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
  scanFlash(needsReview ? "error" : "notice");
  renderScanPage();
}

function showFloatingNotice(message, kind = "notice") {
  let notice = document.getElementById("floatingScanNotice");
  if (!notice) {
    notice = document.createElement("div");
    notice.id = "floatingScanNotice";
    notice.className = "floating-scan-notice";
    document.body.appendChild(notice);
  }
  notice.className = `floating-scan-notice ${kind}`;
  notice.innerHTML = `<strong>${escapeHtml(kind === "success" ? "Scan accepted" : kind === "error" ? "Needs review" : "Notice")}</strong><span>${escapeHtml(message)}</span>`;
  window.clearTimeout(notice._hideTimer);
  notice._hideTimer = window.setTimeout(() => {
    notice.classList.add("is-hiding");
  }, 5200);
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
    els.headerGlobalSearchResults.hidden = false;
    els.headerGlobalSearchResults.innerHTML = `<div class="no-search-results"><strong>No results</strong><span>No order, item, customer, or bay matched that search.</span></div>`;
    return;
  }
  els.headerGlobalSearchResults.hidden = false;
  els.headerGlobalSearchResults.innerHTML = results
    .slice(0, 8)
    .map(
      (result) => `
        <button type="button" ${result.bayCode ? `data-open-bay="${escapeHtml(result.bayCode)}"` : `data-open-list="${escapeHtml(result.deliveryListId)}" data-open-search="${escapeHtml([result.order, result.item, result.customer].filter(Boolean).join(" "))}"`}>
          <strong>${escapeHtml(result.order)}-${escapeHtml(result.item)}</strong>
          <span>${escapeHtml(result.customer)}${result.bay ? ` - Bay ${escapeHtml(result.bay)}` : ""}</span>
          <small>${escapeHtml(result.locationText || result.stage || "")}</small>
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
    renderIndianTrailSummary(null);
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
  const outboundQty = Number(summary?.indianTrailOutboundScanned ?? outbound?.scannedQty ?? 0);
  const outboundTotal = Number(summary?.indianTrailOutboundTotal ?? outbound?.totalQty ?? 0);
  const inboundQty = Number(inbound?.scannedQty ?? summary?.receivedQty ?? 0);
  const inboundTotal = Number(inbound?.totalQty ?? summary?.inboundToday ?? 0);
  const inTransitQty = Math.max(outboundQty - inboundQty, 0);
  els.bayFlowPanel.innerHTML = `
    <button class="flow-card outbound" type="button" ${outbound ? `data-open-list="${escapeHtml(outbound.id)}"` : ""}>
      <small>Today's Outbound</small>
      <strong>${escapeHtml(outboundQty)} / ${escapeHtml(outboundTotal)}</strong>
      <span>${outbound ? escapeHtml(outbound.stage) : "No outbound list"}</span>
    </button>
    <div class="flow-lane" aria-hidden="true">
      <span class="flow-truck"><b>${escapeHtml(inTransitQty)}</b></span>
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
  const overview = bayOverview();
  els.indianTrailSummary.innerHTML = `
    <div class="mini-stat-grid">
      ${miniStat("Total Bays", overview.total)}
      ${miniStat("Blocked Bays", overview.blocked)}
      ${miniStat("Available", overview.available)}
      ${miniStat("Preassigned", overview.preassigned)}
      ${miniStat("Occupied", overview.occupied)}
      ${miniStat("SDI", summary?.sdiCount ?? state.bays.filter((bay) => bayStatusKind(bay) === "picking").length)}
      ${miniStat("Needs Check", summary?.needsCheck ?? 0)}
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
  if (bayCategoryKind(bay) === "spacer") return "";
  if (String(status).toLowerCase().includes("hold")) return "HLD";
  if (!bay.active || String(status).toLowerCase() === "manualhold") return "MAN";
  if (String(status).toLowerCase().includes("block")) return "BLK";
  if (status === "SDI") return "SDI";
  if (/pre|assign/i.test(status)) return "PRE";
  if (status === "Full" || status === "Occupied") return "OCC";
  if (status === "Partial") return "PAR";
  if (status === "Empty" || status === "Available") return "AVL";
  return "";
}

function bayCategoryKind(bay) {
  const text = [bay?.bayCategory, bay?.bayType, bay?.mapSection, bay?.displayName, bay?.bayCode].join(" ").toLowerCase();
  if (text.includes("spacer")) return "spacer";
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
    spacer: "Spacers",
    standard: "Other Bays",
  };
  return labels[kind] || "Other Bays";
}

function bayCategoryOrder(kind) {
  return { coral: 1, lr: 2, rr: 3, showers: 4, mirror: 5, "bfs-mirror": 6, "framed-mirror": 7, crl: 8, standard: 9, spacer: 10 }[kind] || 9;
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
  if (status.includes("hold")) return "manual";
  if (bayCategoryKind(bay) === "spacer") return "spacer";
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
  const stateLine = assignment ? `${abbreviation || statusAbbreviation(status, bay) || statusKind.toUpperCase()}: ${assignment.order}` : `${abbreviation || "AVL"}: Empty`;
  return `
    <button class="${mode === "physical" ? "physical-bay-slot" : "bay-slot"} type-${escapeHtml(kind)} status-${escapeHtml(statusKind)} ${escapeHtml(String(status).toLowerCase())} ${dimmed ? "is-dimmed" : ""} ${searchMatch ? "is-search-match" : ""} ${state.selectedBayCode === bay.bayCode ? "is-selected" : ""}"
      type="button"
      data-bay-code="${escapeHtml(bay.bayCode)}"
      data-assignment-id="${escapeHtml(assignment?.id || "")}"
      ${state.bayEditMode && hasPermission("manage_bay_layout") ? 'draggable="true"' : ""}
      title="${escapeHtml(text)}">
      <span class="bay-code">${escapeHtml(label)}</span>
      ${abbreviation ? `<span class="bay-state">${escapeHtml(abbreviation)}</span>` : ""}
      <small>${escapeHtml(stateLine)}</small>
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

function bayPhysicalSections() {
  const sectionMap = new Map();
  for (const bay of state.bays || []) {
    const label = bayRackLabel(bay);
    if (!sectionMap.has(label)) sectionMap.set(label, []);
    sectionMap.get(label).push(bay);
  }
  return [...sectionMap.entries()]
    .map(([label, bays]) => {
      const positioned = bays.filter((bay) => Number(bay.layoutRow || 0) || Number(bay.layoutCol || 0));
      const row = positioned.reduce((sum, bay) => sum + Number(bay.layoutRow || 9999), 0) / Math.max(positioned.length, 1);
      const col = positioned.reduce((sum, bay) => sum + Number(bay.layoutCol || 9999), 0) / Math.max(positioned.length, 1);
      const kind = bayCategoryKind(bays[0]);
      return { label, bays, row, col, kind };
    })
    .sort((a, b) => a.col - b.col || a.row - b.row || a.label.localeCompare(b.label));
}

function initializeBayLayoutDraft() {
  const sections = bayPhysicalSections();
  const used = new Set();
  state.bayLayoutDraft = {};
  state.bayHoldingSections = new Set();
  sections.forEach((section, index) => {
    let row = Math.round(Number(section.row || 0));
    let col = Math.round(Number(section.col || 0));
    if (row < 1 || row > 7 || col < 1 || col > 7 || used.has(`${row}:${col}`)) {
      row = Math.floor(index / 7) + 1;
      col = (index % 7) + 1;
      while (row <= 7 && used.has(`${row}:${col}`)) {
        col += 1;
        if (col > 7) {
          col = 1;
          row += 1;
        }
      }
    }
    if (row > 7) {
      state.bayHoldingSections.add(section.label);
      state.bayLayoutDraft[section.label] = { row: 0, col: 0, holding: true };
    } else {
      used.add(`${row}:${col}`);
      state.bayLayoutDraft[section.label] = { row, col, holding: false };
    }
  });
  state.bayLayoutOriginal = JSON.parse(JSON.stringify(state.bayLayoutDraft));
}

function normalizedBayGridPositions(sections) {
  const used = new Set();
  const positions = {};
  sections.forEach((section, index) => {
    let row = Math.round(Number(section.row || 0));
    let col = Math.round(Number(section.col || 0));
    if (row < 1 || row > 7 || col < 1 || col > 7 || used.has(`${row}:${col}`)) {
      row = Math.floor(index / 7) + 1;
      col = (index % 7) + 1;
      while (row <= 7 && used.has(`${row}:${col}`)) {
        col += 1;
        if (col > 7) {
          col = 1;
          row += 1;
        }
      }
    }
    if (row <= 7) {
      used.add(`${row}:${col}`);
      positions[section.label] = { row, col, holding: false };
    } else {
      positions[section.label] = { row: 0, col: 0, holding: true };
    }
  });
  return positions;
}

function renderBaySection(section) {
  const visible = section.bays.filter((bay) => bayMatchesFilter(bay, baySearchText(bay))).length;
  const dimmed = !visible && (state.bayStatusFilter !== "all" || state.bayCategoryFilter !== "all" || state.baySearch);
  const occupied = section.bays.filter((bay) => Number(bay.assignedQty || 0) > 0).length;
  const open = !state.collapsedBaySections.has(section.label);
  const cols = Math.max(1, Math.min(Number(state.bayGroupColumns[section.label] || 1), 2));
  return `
    <details ${open ? "open" : ""} class="physical-bay-section type-${escapeHtml(section.kind)} cols-${cols} ${state.bayEditMode ? "is-editing" : ""} ${dimmed ? "is-dimmed" : ""}" data-bay-drop-section="${escapeHtml(section.label)}" data-bay-drop-category="${escapeHtml(section.kind)}">
      <summary ${state.bayEditMode && hasPermission("manage_bay_layout") ? 'draggable="true"' : ""} data-bay-group-drag="${escapeHtml(section.label)}"><strong>${escapeHtml(section.label)}</strong><span>${escapeHtml(occupied)} / ${escapeHtml(section.bays.length)}</span>${state.bayEditMode ? `<span class="bay-column-controls"><button type="button" data-bay-col-action="dec" data-bay-section="${escapeHtml(section.label)}">-</button><b>${cols} col</b><button type="button" data-bay-col-action="inc" data-bay-section="${escapeHtml(section.label)}">+</button></span>` : ""}</summary>
      <div class="physical-slot-grid" style="--bay-section-cols:${cols}">
        ${section.bays.map((bay) => renderBaySlotButton(bay, "physical")).join("")}
      </div>
    </details>
  `;
}

function renderBayGrid(physicalSections) {
  if (state.bayEditMode && !state.bayLayoutDraft) initializeBayLayoutDraft();
  const sectionByLabel = new Map(physicalSections.map((section) => [section.label, section]));
  const normalPositions = state.bayEditMode ? null : normalizedBayGridPositions(physicalSections);
  const cells = [];
  for (let row = 1; row <= 7; row += 1) {
    for (let col = 1; col <= 7; col += 1) {
      const section = physicalSections.find((item) => {
        const draft = state.bayEditMode ? state.bayLayoutDraft?.[item.label] : normalPositions?.[item.label];
        const sectionRow = draft ? draft.row : Math.round(Number(item.row || 0));
        const sectionCol = draft ? draft.col : Math.round(Number(item.col || 0));
        const holding = draft?.holding;
        return !holding && sectionRow === row && sectionCol === col;
      });
      cells.push(`
        <div class="bay-grid-cell ${section ? "has-section" : ""}" data-grid-row="${row}" data-grid-col="${col}" data-bay-drop-section="${escapeHtml(section?.label || `grid-${row}-${col}`)}" data-bay-grid-cell="true">
          ${section ? renderBaySection(section) : `<span class="empty-grid-slot">Empty</span>`}
        </div>
      `);
    }
  }
  const holding = [...state.bayHoldingSections]
    .map((label) => sectionByLabel.get(label))
    .filter(Boolean);
  return `
    ${state.bayEditMode ? `<section class="bay-holding-area" data-bay-holding-area="true">
      <header><strong>Temporary Holding Area</strong><span>${escapeHtml(holding.length)} group${holding.length === 1 ? "" : "s"}</span></header>
      <div class="bay-holding-list" data-bay-drop-section="__holding" data-bay-holding-drop="true">
        ${holding.length ? holding.map((section) => renderBaySection(section)).join("") : `<div class="empty-grid-slot">Drop grouped bay sets here while reorganizing.</div>`}
      </div>
    </section>` : ""}
    <section class="bay-edit-grid">${cells.join("")}</section>
  `;
}

function renderBayMapPage() {
  if (!els.bayMapCanvas || !state.bayLayout) return;
  const physicalSections = bayPhysicalSections();
  els.bayMapCanvas.innerHTML = renderBayGrid(physicalSections);
  els.bayMapCanvas.querySelectorAll(".physical-bay-section").forEach((details) => {
    details.addEventListener("toggle", () => {
      const label = details.dataset.bayDropSection || "";
      if (!label) return;
      if (details.open) state.collapsedBaySections.delete(label);
      else state.collapsedBaySections.add(label);
    });
  });
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
        <div class="selected-bay-actions">
          <button type="button" data-bay-action="hold" data-permission-any="clear_bay,move_bay">Hold Bay</button>
          <button type="button" data-bay-action="block" data-permission-any="clear_bay,move_bay">Block Bay</button>
          <button type="button" data-bay-action="unblock" data-permission-any="clear_bay,move_bay">Remove Hold/Block</button>
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
                      <article class="selected-assignment" data-assignment-id="${escapeHtml(assignment.id)}">
                        <div>
                          <strong>${isNewOrUpdatedItem(assignment) ? '<span class="bay-new-star" title="New or updated line">*</span>' : ""}${escapeHtml(assignment.order)}-${escapeHtml(assignment.item)} <span>${escapeHtml(assignment.customer || "")}</span></strong>
                          <small>${escapeHtml(assignment.product || assignment.job || "")}</small>
                          <small>${escapeHtml(assignment.dimensions || "")} - Qty ${escapeHtml(assignment.assignedQty || assignment.qty || 0)}</small>
                          <small>${escapeHtml(assignment.job || "")}</small>
                          <small>Delivery: ${escapeHtml(formatDisplayDate(assignment.deliveryDate || ""))}</small>
                          <small>Last scanned: ${escapeHtml(formatDateTime(assignment.lastScannedAt) || "Not scanned yet")}</small>
                          <small>Last stage: ${escapeHtml(assignment.lastStage || assignment.lastScannedStation || "Not started")}</small>
                        </div>
                        <div class="assignment-actions">
                          <button type="button" title="Clear order from bay" data-assignment-action="clear" data-assignment-id="${escapeHtml(assignment.id)}">X</button>
                          <button type="button" title="Move order" data-assignment-action="move" data-assignment-id="${escapeHtml(assignment.id)}">Move</button>
                          <button type="button" title="Mark or clear SDI" data-assignment-action="sdi" data-assignment-id="${escapeHtml(assignment.id)}" data-order-no="${escapeHtml(assignment.order)}">!</button>
                        </div>
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
        const occupiedBays = section.bays.filter((item) => Number(item.assignedQty || 0) > 0).length;
        return `
          <details class="bay-type-section type-${escapeHtml(section.kind)}" ${sectionOpen ? "open" : ""}>
            <summary><span><strong>${escapeHtml(section.label)} ${escapeHtml(section.bays.length)} bays</strong><small>${escapeHtml(occupiedBays)} / ${escapeHtml(section.bays.length)} occupied</small></span></summary>
            <div class="bay-rack-list">
              ${section.racks
                .map((rack) => {
                  const capacity = rack.bays.reduce((sum, item) => sum + Number(item.capacityQty || 0), 0);
                  const assigned = rack.bays.reduce((sum, item) => sum + Number(item.assignedQty || 0), 0);
                  const percent = capacity ? Math.min((assigned / capacity) * 100, 100) : assigned ? 100 : 0;
                  const rackHasSelected = rack.bays.some((item) => item.bayCode === state.selectedBayCode);
                  return `
                    <details class="bay-rack" ${state.bayCategoryFilter !== "all" || rackHasSelected ? "open" : ""} data-bay-drop-section="${escapeHtml(rack.label)}" data-bay-drop-category="${escapeHtml(section.kind)}">
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

function bayEventTone(event) {
  const text = `${event.eventType || ""} ${event.reason || ""}`.toLowerCase();
  if (text.includes("error") || text.includes("blocked") || text.includes("needs")) return "error";
  if (text.includes("hold") || text.includes("move") || text.includes("sdi") || text.includes("layout") || text.includes("available")) return "notice";
  return "ok";
}

function renderBayRecentActions() {
  const events = state.bayEvents || [];
  if (els.bayScanOutRecent) {
    els.bayScanOutRecent.innerHTML = events.length
      ? `<div class="recent-table-wrap bay-recent-table-wrap">
          <table class="recent-table bay-recent-table">
            <thead><tr><th>Action</th><th>Order</th><th>Bay</th><th>Time</th><th>Check</th></tr></thead>
            <tbody>
              ${events.slice(0, 10)
          .map((event) => {
            const when = new Date(event.time || event.createdAt || "");
            const time = Number.isNaN(when.getTime()) ? "" : when.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
            const bay = event.bayDisplay || event.bayCode || event.newBayCode || event.oldBayCode || "Bay";
            const order = event.order ? `${event.order}-${event.item || ""}` : "Bay action";
            const tone = bayEventTone(event);
            const check = tone === "error" ? "!" : tone === "notice" ? "i" : "✓";
            return `
                <tr class="${escapeHtml(tone)}">
                  <td><strong>${escapeHtml(formatEventType(event.eventType))}</strong><small>${escapeHtml(event.reason || "")}</small></td>
                  <td>${escapeHtml(order)}</td>
                  <td>${escapeHtml(bay)}</td>
                  <td>${escapeHtml(time)}</td>
                  <td><span class="scan-check ${escapeHtml(tone)}">${escapeHtml(check)}</span></td>
                </tr>
              `;
          })
          .join("")}
            </tbody>
          </table>
        </div>`
      : `<div><strong>No recent bay removals</strong><span>Scan-out actions will appear here.</span></div>`;
  }
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
  renderBayMapPage();
  if (state.bayEditMode) {
    renderBayLayoutSelect();
    if (els.bayLayoutSelect) els.bayLayoutSelect.value = bayCode;
    populateBayLayoutForm();
  }
  if (bayCode && els.baySelectedModal) {
    els.baySelectedModal.hidden = false;
    if (els.baySelectedBackdrop) els.baySelectedBackdrop.hidden = false;
  }
}

function closeSelectedBayModal() {
  if (els.baySelectedModal) els.baySelectedModal.hidden = true;
  if (els.baySelectedBackdrop) els.baySelectedBackdrop.hidden = true;
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

function pushBayHistory(entry) {
  if (!entry?.undo || !entry?.redo) return;
  state.bayActionUndoStack.push(entry);
  state.bayActionRedoStack = [];
}

async function runBayHistory(direction) {
  const from = direction === "undo" ? state.bayActionUndoStack : state.bayActionRedoStack;
  const to = direction === "undo" ? state.bayActionRedoStack : state.bayActionUndoStack;
  const entry = from.pop();
  if (!entry) {
    showFloatingNotice(`No bay action to ${direction}.`, "notice");
    return;
  }
  await (direction === "undo" ? entry.undo() : entry.redo());
  to.push(entry);
  await refreshBayMapPage();
  showFloatingNotice(`${direction === "undo" ? "Undid" : "Redid"} ${entry.label}.`, "success");
}

async function submitBayScanOut() {
  const barcode = els.bayScanOutInput?.value.trim() || "";
  if (!barcode) return;
  const bayCode = els.bayScanBayInput?.value.trim() || "";
  const adding = Boolean(els.bayScanModeToggle?.checked);
  const result = adding
    ? await postBayAction("/api/indian-trail/receive", { barcode, bayCode, reason: "Scanned into bay map" })
    : await postBayAction("/api/indian-trail/scan-out", { barcode, bayCode, reason: "Scanned out from bay map" });
  if (!adding && result.assignmentId) {
    pushBayHistory({
      label: `scan-out ${result.order}-${result.item}`,
      undo: () => postBayAction("/api/indian-trail/restore-assignment", { assignmentId: result.assignmentId, reason: "Undo bay scan-out" }),
      redo: () => postBayAction("/api/indian-trail/scan-out", { barcode, bayCode: result.bayCode || bayCode, reason: "Redo bay scan-out" }),
    });
  }
  if (els.bayScanOutInput) els.bayScanOutInput.value = "";
  if (els.bayScanOutStatus) els.bayScanOutStatus.textContent = adding ? result.message : `Removed ${result.order}-${result.item} from ${result.bayDisplay || result.bayCode}`;
  scanFlash("success");
  showFloatingNotice(adding ? result.message : `Removed ${result.order}-${result.item} from ${result.bayDisplay || result.bayCode}`, "success");
}

function manualBayBarcode() {
  const order = digitsOnly(els.bayManualOrderInput?.value || "");
  const item = digitsOnly(els.bayManualItemInput?.value || "");
  if (!order) throw new Error("Enter an order number.");
  return item ? `T200${order.padStart(6, "0")}${item.padStart(3, "0")}000` : `T200${order.padStart(6, "0")}`;
}

async function submitManualBayScan() {
  const barcode = manualBayBarcode();
  if (els.bayScanOutInput) els.bayScanOutInput.value = barcode;
  await submitBayScanOut();
  if (els.bayManualOrderInput) els.bayManualOrderInput.value = "";
  if (els.bayManualItemInput) els.bayManualItemInput.value = "";
}

function selectedBayAssignment() {
  return selectedBay()?.assignments?.[0] || null;
}

function assignmentById(assignmentId) {
  const id = String(assignmentId || "");
  for (const bay of state.bays || []) {
    const match = (bay.assignments || []).find((assignment) => String(assignment.id) === id);
    if (match) return { bay, assignment: match };
  }
  return { bay: selectedBay(), assignment: selectedBayAssignment() };
}

function openSdiPanel(assignmentId = "") {
  const found = assignmentById(assignmentId);
  if (found.bay?.bayCode) state.selectedBayCode = found.bay.bayCode;
  const bay = selectedBay();
  const assignment = found.assignment || selectedBayAssignment();
  if (els.sdiPanel) els.sdiPanel.dataset.assignmentId = assignment?.id || "";
  if (els.sdiPanel) els.sdiPanel.hidden = false;
  if (els.sdiBackdrop) els.sdiBackdrop.hidden = false;
  if (els.sdiOrderInput && assignment?.order) els.sdiOrderInput.value = assignment.order;
  if (els.sdiBayInput) els.sdiBayInput.value = bay?.bayCode || "";
  if (els.sdiReasonInput && !els.sdiReasonInput.value) els.sdiReasonInput.value = "Same-day install";
  renderSdiCurrentList();
  els.sdiOrderInput?.focus();
}

function renderSdiCurrentList() {
  if (!els.sdiCurrentList) return;
  const rows = [];
  for (const bay of state.bays || []) {
    for (const assignment of bay.assignments || []) {
      if (assignment.status === "SDIOverride") rows.push({ bay, assignment });
    }
  }
  els.sdiCurrentList.innerHTML = `
    <strong>Current SDI Orders</strong>
    <div>
      ${
        rows.length
          ? rows.slice(0, 30).map(({ bay, assignment }) => `<button type="button" data-assignment-action="sdi" data-assignment-id="${escapeHtml(assignment.id)}"><span>${escapeHtml(assignment.order)}-${escapeHtml(assignment.item)}</span><small>${escapeHtml(bay.displayName || bay.bayCode)} - ${escapeHtml(assignment.customer || "")}</small></button>`).join("")
          : `<span class="admin-empty">No current SDI orders.</span>`
      }
    </div>
  `;
}

function closeSdiPanel() {
  if (els.sdiPanel) els.sdiPanel.hidden = true;
  if (els.sdiBackdrop) els.sdiBackdrop.hidden = true;
}

async function submitSdi(mark = true) {
  const assignment = assignmentById(els.sdiPanel?.dataset.assignmentId || "").assignment || selectedBayAssignment();
  const payload = {
    assignmentId: assignment?.id || "",
    orderNo: els.sdiOrderInput?.value || "",
    bayCode: els.sdiBayInput?.value || state.selectedBayCode || "",
    truckExempt: Boolean(els.sdiTruckExemptInput?.checked),
    reason: `${els.sdiTypeInput?.value || "Rush"} - ${els.sdiReasonInput?.value || (mark ? "Same-day install" : "SDI cleared")}`,
  };
  if (mark && !els.sdiTypeInput?.value) {
    showInlineError("Select Rush or Remake before marking SDI.", false);
    return;
  }
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
  if (action === "layout") {
    openBayLayoutManager();
    return;
  }
  if (action === "item-management") {
    openSdiPanel();
    showFloatingNotice("Use the selected bay order buttons to move, clear, or mark items while the Item Management panel is expanded here.", "notice");
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
  if (action === "move") {
    if (!assignment?.id) {
      showInlineError("That bay does not have an assignment to move.", false);
      return;
    }
    state.pendingBayMove = { assignmentId: assignment.id, fromBay: bay.bayCode, order: assignment.order, item: assignment.item };
    showFloatingNotice(`Select a destination bay for ${assignment.order}-${assignment.item}.`, "notice");
    document.body.classList.add("bay-move-mode");
    return;
  }
  if (action === "hold" || action === "block" || action === "unblock") {
    const status = action === "hold" ? "Hold" : action === "block" ? "Blocked" : "Available";
    const previousStatus = ["Hold", "Blocked", "Available"].includes(String(bay.status || "")) ? bay.status : "Available";
    const result = await postBayAction("/api/indian-trail/bay-status", { bayCode: bay.bayCode, status, reason: `${status} from bay map` });
    pushBayHistory({
      label: `bay status ${bay.displayName || bay.bayCode}`,
      undo: () => postBayAction("/api/indian-trail/bay-status", { bayCode: bay.bayCode, status: previousStatus, reason: `Undo status change to ${previousStatus}` }),
      redo: () => postBayAction("/api/indian-trail/bay-status", { bayCode: bay.bayCode, status, reason: `Redo status change to ${status}` }),
    });
    state.bays = result.bays || state.bays;
    showFloatingNotice(`${bay.displayName || bay.bayCode} set to ${status}.`, "success");
  }
}

function renderBayLayoutSelect() {
  if (!els.bayLayoutSelect) return;
  const current = els.bayLayoutSelect.value || state.selectedBayCode || state.bays[0]?.bayCode || "";
  els.bayLayoutSelect.innerHTML = (state.bays || [])
    .map((bay) => `<option value="${escapeHtml(bay.bayCode)}">${escapeHtml(bay.displayName || bay.bayCode)} - ${escapeHtml(bay.mapSection || "")}</option>`)
    .join("");
  els.bayLayoutSelect.value = state.bays.some((bay) => bay.bayCode === current) ? current : state.bays[0]?.bayCode || "";
}

function populateBayLayoutForm() {
  const bay = state.bays.find((item) => item.bayCode === els.bayLayoutSelect?.value) || selectedBay() || state.bays[0];
  if (!bay) return;
  state.selectedBayCode = bay.bayCode;
  if (els.bayLayoutDisplayInput) els.bayLayoutDisplayInput.value = bay.displayName || bay.bayCode;
  if (els.bayLayoutSectionInput) els.bayLayoutSectionInput.value = bay.mapSection || "";
  if (els.bayLayoutCategoryInput) els.bayLayoutCategoryInput.value = bay.bayCategory || "";
  if (els.bayLayoutRowInput) els.bayLayoutRowInput.value = bay.layoutRow || "";
  if (els.bayLayoutColInput) els.bayLayoutColInput.value = bay.layoutCol || "";
  if (els.bayLayoutCapacityInput) els.bayLayoutCapacityInput.value = bay.capacityQty || 0;
  if (els.bayLayoutActiveInput) els.bayLayoutActiveInput.checked = Boolean(bay.active);
}

function openBayLayoutManager() {
  if (!hasPermission("manage_bay_layout")) {
    showInlineError("Only admins can edit the bay map layout.", false);
    return;
  }
  state.bayEditMode = true;
  initializeBayLayoutDraft();
  state.bayLayoutUndoStack = [];
  state.bayLayoutRedoStack = [];
  if (els.bayLayoutManager) els.bayLayoutManager.hidden = false;
  renderBayLayoutSelect();
  populateBayLayoutForm();
  renderBayMapPage();
}

function closeBayLayoutManager() {
  if (state.bayHoldingSections.size) {
    showFloatingNotice("Move all grouped bays out of the temporary holding area before closing edit mode.", "error");
    return;
  }
  state.bayEditMode = false;
  state.bayLayoutDraft = null;
  state.bayLayoutOriginal = null;
  state.bayHoldingSections = new Set();
  if (els.bayLayoutManager) els.bayLayoutManager.hidden = true;
  renderBayMapPage();
}

function moveBaySectionDraft(sectionLabel, row, col, holding = false) {
  if (!sectionLabel || !state.bayLayoutDraft?.[sectionLabel]) return;
  const before = JSON.parse(JSON.stringify(state.bayLayoutDraft));
  if (holding) {
    state.bayHoldingSections.add(sectionLabel);
    state.collapsedBaySections.add(sectionLabel);
    state.bayLayoutDraft[sectionLabel] = { row: 0, col: 0, holding: true };
  } else {
    const displaced = Object.entries(state.bayLayoutDraft).find(([, pos]) => !pos.holding && pos.row === row && pos.col === col);
    if (displaced?.[0] && displaced[0] !== sectionLabel) {
      state.bayHoldingSections.add(displaced[0]);
      state.bayLayoutDraft[displaced[0]] = { row: 0, col: 0, holding: true };
    }
    state.bayHoldingSections.delete(sectionLabel);
    state.bayLayoutDraft[sectionLabel] = { row, col, holding: false };
  }
  const after = JSON.parse(JSON.stringify(state.bayLayoutDraft));
  state.bayLayoutUndoStack.push({ label: `move ${sectionLabel}`, beforeDraft: before, afterDraft: after });
  state.bayLayoutRedoStack = [];
  renderBayMapPage();
}

function holdAllBaySections() {
  if (!state.bayEditMode) return;
  const before = JSON.parse(JSON.stringify(state.bayLayoutDraft || {}));
  const sections = bayPhysicalSections();
  for (const section of sections) {
    state.bayHoldingSections.add(section.label);
    state.collapsedBaySections.add(section.label);
    state.bayLayoutDraft[section.label] = { row: 0, col: 0, holding: true };
  }
  const after = JSON.parse(JSON.stringify(state.bayLayoutDraft || {}));
  state.bayLayoutUndoStack.push({ label: "hold all bay groups", beforeDraft: before, afterDraft: after });
  state.bayLayoutRedoStack = [];
  renderBayMapPage();
}

function applyBayLayoutDraft(draft) {
  state.bayLayoutDraft = JSON.parse(JSON.stringify(draft || {}));
  state.bayHoldingSections = new Set(Object.entries(state.bayLayoutDraft).filter(([, pos]) => pos.holding).map(([label]) => label));
  renderBayMapPage();
}

async function confirmBayLayoutDraft() {
  if (!state.bayEditMode || !state.bayLayoutDraft) return;
  if (state.bayHoldingSections.size) {
    showFloatingNotice("Move all grouped bays out of the temporary holding area before confirming.", "error");
    return;
  }
  const sections = bayPhysicalSections();
  for (const section of sections) {
    const pos = state.bayLayoutDraft[section.label];
    if (!pos || pos.holding) continue;
    await fetchJson("/api/indian-trail/layout", {
      method: "POST",
      body: JSON.stringify({
        setGroupPosition: true,
        mapSection: section.label,
        layoutRow: pos.row,
        layoutCol: pos.col,
        ...requestContext(),
      }),
    });
  }
  state.bayEditMode = false;
  state.bayLayoutDraft = null;
  state.bayLayoutOriginal = null;
  state.bayHoldingSections = new Set();
  if (els.bayLayoutManager) els.bayLayoutManager.hidden = true;
  await refreshBayMapPage();
  showFloatingNotice("Bay map layout confirmed.", "success");
}

function cancelBayLayoutDraft() {
  state.bayEditMode = false;
  state.bayLayoutDraft = null;
  state.bayLayoutOriginal = null;
  state.bayHoldingSections = new Set();
  state.bayLayoutUndoStack = [];
  state.bayLayoutRedoStack = [];
  if (els.bayLayoutManager) els.bayLayoutManager.hidden = true;
  renderBayMapPage();
  showFloatingNotice("Bay map layout changes were cancelled.", "notice");
}

async function saveBayLayoutForm() {
  if (!els.bayLayoutSelect?.value) return;
  const payload = await fetchJson("/api/indian-trail/layout", {
    method: "POST",
    body: JSON.stringify({
      bayCode: els.bayLayoutSelect.value,
      displayName: els.bayLayoutDisplayInput?.value || "",
      mapSection: els.bayLayoutSectionInput?.value || "",
      bayCategory: els.bayLayoutCategoryInput?.value || "",
      layoutRow: els.bayLayoutRowInput?.value || "",
      layoutCol: els.bayLayoutColInput?.value || "",
      capacityQty: els.bayLayoutCapacityInput?.value || 0,
      active: Boolean(els.bayLayoutActiveInput?.checked),
      ...requestContext(),
    }),
  });
  state.bays = payload.bays || state.bays;
  renderBayMapPage();
}

function bayLayoutSnapshot(filter = () => true) {
  return (state.bays || [])
    .filter(filter)
    .map((bay) => ({
      bayCode: bay.bayCode,
      displayName: bay.displayName || bay.bayCode,
      mapSection: bay.mapSection || "",
      bayCategory: bay.bayCategory || bayCategoryKind(bay),
      layoutRow: bay.layoutRow || "",
      layoutCol: bay.layoutCol || "",
      capacityQty: bay.capacityQty || 0,
      active: Boolean(bay.active),
    }));
}

async function applyBayLayoutSnapshot(snapshot) {
  for (const bay of snapshot || []) {
    await fetchJson("/api/indian-trail/layout", {
      method: "POST",
      body: JSON.stringify({ ...bay, ...requestContext() }),
    });
  }
  await refreshBayMapPage();
  renderBayLayoutSelect();
  populateBayLayoutForm();
}

function pushBayLayoutHistory(label, before, after) {
  if (!before?.length || !after?.length) return;
  state.bayLayoutUndoStack.push({ label, before, after });
  state.bayLayoutRedoStack = [];
}

async function runBayLayoutHistory(direction) {
  const from = direction === "undo" ? state.bayLayoutUndoStack : state.bayLayoutRedoStack;
  const to = direction === "undo" ? state.bayLayoutRedoStack : state.bayLayoutUndoStack;
  const entry = from.pop();
  if (!entry) {
    showFloatingNotice(`No layout change to ${direction}.`, "notice");
    return;
  }
  if (entry.beforeDraft || entry.afterDraft) {
    applyBayLayoutDraft(direction === "undo" ? entry.beforeDraft : entry.afterDraft);
    to.push(entry);
    showFloatingNotice(`${direction === "undo" ? "Undid" : "Redid"} ${entry.label}.`, "success");
    return;
  }
  await applyBayLayoutSnapshot(direction === "undo" ? entry.before : entry.after);
  to.push(entry);
  showFloatingNotice(`${direction === "undo" ? "Undid" : "Redid"} ${entry.label}.`, "success");
}

async function moveBayToGroup(bayCode, mapSection, bayCategory = "", targetBayCode = "") {
  const bay = state.bays.find((item) => item.bayCode === bayCode);
  const targetBay = state.bays.find((item) => item.bayCode === targetBayCode);
  if (!bay || !mapSection) return;
  const impactedSections = new Set([bay.mapSection, mapSection, targetBay?.mapSection].filter(Boolean));
  const before = bayLayoutSnapshot((item) => impactedSections.has(item.mapSection || "") || item.bayCode === bayCode || item.bayCode === targetBayCode);
  const payload = await fetchJson("/api/indian-trail/layout", {
    method: "POST",
    body: JSON.stringify({
      bayCode,
      displayName: bay.displayName || bay.bayCode,
      mapSection,
      bayCategory: bayCategory || bay.bayCategory || bayCategoryKind(bay),
      layoutRow: targetBay?.layoutRow || bay.layoutRow || "",
      layoutCol: targetBay?.layoutCol || bay.layoutCol || "",
      insertBeforeBayCode: targetBayCode || "",
      capacityQty: bay.capacityQty || 0,
      active: Boolean(bay.active),
      ...requestContext(),
    }),
  });
  state.bays = payload.bays || state.bays;
  const after = bayLayoutSnapshot((item) => impactedSections.has(item.mapSection || "") || item.bayCode === bayCode || item.bayCode === targetBayCode);
  pushBayLayoutHistory(`move ${bayCode}`, before, after);
  state.selectedBayCode = bayCode;
  renderBayMapPage();
  renderBayLayoutSelect();
  populateBayLayoutForm();
  showFloatingNotice(`${bayCode} moved to ${mapSection}`, "success");
}

async function addBaysFromForm() {
  const result = await fetchJson("/api/indian-trail/bays/add", {
    method: "POST",
    body: JSON.stringify({
      mapSection: els.bayAddGroupInput?.value || "",
      bayCategory: els.bayAddCategoryInput?.value || "",
      prefix: els.bayAddPrefixInput?.value || "",
      count: els.bayAddCountInput?.value || 1,
      ...requestContext(),
    }),
  });
  state.bays = result.bays || state.bays;
  if (result.created?.[0]) state.selectedBayCode = result.created[0];
  renderBayMapPage();
  renderBayLayoutSelect();
  populateBayLayoutForm();
  showFloatingNotice(`Added ${result.created?.length || 0} bay(s)`, "success");
}

async function addSpacerBay() {
  const selected = selectedBay();
  const mapSection = window.prompt("Add spacer to which bay group?", selected?.mapSection || "");
  if (!mapSection) return;
  const before = bayLayoutSnapshot((bay) => bay.mapSection === mapSection);
  const result = await fetchJson("/api/indian-trail/bays/add", {
    method: "POST",
    body: JSON.stringify({
      mapSection,
      bayCategory: "Spacer",
      prefix: "Spacer",
      count: 1,
      spacer: true,
      ...requestContext(),
    }),
  });
  state.bays = result.bays || state.bays;
  const after = bayLayoutSnapshot((bay) => bay.mapSection === mapSection || result.created?.includes(bay.bayCode));
  pushBayLayoutHistory("add spacer", before, after);
  if (result.created?.[0]) state.selectedBayCode = result.created[0];
  renderBayMapPage();
  renderBayLayoutSelect();
  populateBayLayoutForm();
  showFloatingNotice("Spacer added to the bay map.", "success");
}

async function deleteSelectedBay() {
  const bayCode = els.bayLayoutSelect?.value || state.selectedBayCode;
  if (!bayCode) return;
  if (!window.confirm(`Delete bay ${bayCode}? Active assignments must be cleared first.`)) return;
  const result = await fetchJson("/api/indian-trail/bays/delete", {
    method: "POST",
    body: JSON.stringify({ bayCode, ...requestContext() }),
  });
  state.bays = result.bays || state.bays;
  state.selectedBayCode = "";
  renderBayMapPage();
  renderBayLayoutSelect();
  populateBayLayoutForm();
}

async function deleteSelectedBayGroup() {
  const mapSection = els.bayAddGroupInput?.value || els.bayLayoutSectionInput?.value || selectedBay()?.mapSection || "";
  if (!mapSection) return;
  if (!window.confirm(`Delete bay group ${mapSection}? Active assignments must be cleared first.`)) return;
  const result = await fetchJson("/api/indian-trail/bays/delete-group", {
    method: "POST",
    body: JSON.stringify({ mapSection, ...requestContext() }),
  });
  state.bays = result.bays || state.bays;
  state.selectedBayCode = "";
  renderBayMapPage();
  renderBayLayoutSelect();
  populateBayLayoutForm();
}

async function moveBayGroup(direction) {
  const section = els.bayLayoutSectionInput?.value || selectedBay()?.mapSection || "";
  const delta = {
    up: { rowDelta: -1, colDelta: 0 },
    down: { rowDelta: 1, colDelta: 0 },
    left: { rowDelta: 0, colDelta: -1 },
    right: { rowDelta: 0, colDelta: 1 },
  }[direction];
  if (!section || !delta) return;
  const payload = await fetchJson("/api/indian-trail/layout", {
    method: "POST",
    body: JSON.stringify({ moveGroup: true, mapSection: section, ...delta, ...requestContext() }),
  });
  state.bays = payload.bays || state.bays;
  renderBayMapPage();
  renderBayLayoutSelect();
  populateBayLayoutForm();
}

async function swapBayGroups(sourceSection, targetSection) {
  if (!sourceSection || !targetSection || sourceSection === targetSection) return;
  const before = bayLayoutSnapshot((bay) => bay.mapSection === sourceSection || bay.mapSection === targetSection);
  const payload = await fetchJson("/api/indian-trail/layout", {
    method: "POST",
    body: JSON.stringify({ moveGroup: true, mapSection: sourceSection, targetMapSection: targetSection, ...requestContext() }),
  });
  state.bays = payload.bays || state.bays;
  const after = bayLayoutSnapshot((bay) => bay.mapSection === sourceSection || bay.mapSection === targetSection);
  pushBayLayoutHistory(`swap ${sourceSection}`, before, after);
  renderBayMapPage();
  renderBayLayoutSelect();
  populateBayLayoutForm();
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

function importCandidateSummary(result) {
  const imported = result.importedFiles || [];
  const updated = result.updatedFiles || [];
  const rows = [
    ...imported.map((entry) => ({ ...entry, kind: "New" })),
    ...updated.map((entry) => ({ ...entry, kind: "Updated" })),
  ];
  if (!rows.length) return `<div class="admin-empty">No new or updated delivery lists were found.</div>`;
  return rows
    .map((entry, index) => `
      <details class="import-result-item">
        <summary>
          <label class="checkbox-row"><input class="import-candidate-check" type="checkbox" checked data-import-candidate-listids="${escapeHtml((entry.listIds || []).join(","))}"><span><strong>${escapeHtml(entry.kind)} - ${escapeHtml(entry.fileName)}</strong><small>${escapeHtml(formatDisplayDate(entry.deliveryDate))} - ${escapeHtml(entry.rowCount || 0)} rows / ${escapeHtml(entry.totalQty || 0)} pieces</small></span></label>
          ${entry.listIds?.length ? `<button type="button" data-print-candidate-index="${index}">Print updated items</button>` : ""}
        </summary>
        <div class="compact-list">
          ${(entry.listIds || []).map((listId) => `<div><strong>${escapeHtml(listId)}</strong><span>Changed stage included in this package.</span></div>`).join("") || "<div><strong>No changed stages reported</strong></div>"}
        </div>
      </details>
    `)
    .join("");
}

function showImportResultDialog(result) {
  let backdrop = document.getElementById("importResultBackdrop");
  let panel = document.getElementById("importResultPanel");
  if (!backdrop) {
    backdrop = document.createElement("div");
    backdrop.id = "importResultBackdrop";
    backdrop.className = "modal-backdrop";
    document.body.appendChild(backdrop);
  }
  if (!panel) {
    panel = document.createElement("section");
    panel.id = "importResultPanel";
    panel.className = "modal-panel import-result-panel";
    document.body.appendChild(panel);
  }
  const imported = result.importedFiles?.length || 0;
  const updated = result.updatedFiles?.length || 0;
  const skipped = result.skippedFiles?.length || 0;
  const failed = result.failedFiles?.length || 0;
  panel.innerHTML = `
    <div class="section-heading">
      <h2>Import / Update Complete</h2>
      <button type="button" data-close-import-result>OK</button>
    </div>
    <p class="admin-empty success">${imported} new, ${updated} updated, ${skipped} unchanged, ${failed} failed.</p>
    <div class="admin-button-row">
      <button type="button" data-print-import="latest">Print all updated items</button>
      <button type="button" data-print-selected-imports>Print selected updates</button>
    </div>
    <div class="import-result-list">${importCandidateSummary(result)}</div>
  `;
  backdrop.hidden = false;
  panel.hidden = false;
  backdrop.addEventListener("click", closeImportResultDialog, { once: true });
}

function closeImportResultDialog() {
  const backdrop = document.getElementById("importResultBackdrop");
  const panel = document.getElementById("importResultPanel");
  if (backdrop) backdrop.hidden = true;
  if (panel) panel.hidden = true;
}

async function runAssignmentAction(action, assignmentId) {
  const found = assignmentById(assignmentId);
  const assignment = found.assignment;
  if (!assignment?.id) {
    showInlineError("Assignment not found.", true);
    return;
  }
  if (found.bay?.bayCode) state.selectedBayCode = found.bay.bayCode;
  if (action === "sdi") {
    openSdiPanel(assignment.id);
    return;
  }
  if (action === "clear") {
    if (!window.confirm(`Clear ${assignment.order}-${assignment.item} from this bay?`)) return;
    await postBayAction("/api/indian-trail/clear-assignment", { assignmentId: assignment.id, reason: "Cleared selected order from bay map" });
    pushBayHistory({
      label: `clear ${assignment.order}-${assignment.item}`,
      undo: () => postBayAction("/api/indian-trail/restore-assignment", { assignmentId: assignment.id, reason: "Undo selected bay clear" }),
      redo: () => postBayAction("/api/indian-trail/clear-assignment", { assignmentId: assignment.id, reason: "Redo selected bay clear" }),
    });
    return;
  }
  if (action === "move") {
    const newBayCode = window.prompt("Move this order to which bay code?");
    if (!newBayCode) return;
    await postBayAction("/api/indian-trail/move", { assignmentId: assignment.id, newBayCode, reason: `Moved selected order from ${found.bay?.displayName || found.bay?.bayCode || "bay"}` });
    const oldBayCode = found.bay?.bayCode || "";
    pushBayHistory({
      label: `move ${assignment.order}-${assignment.item}`,
      undo: () => postBayAction("/api/indian-trail/move", { assignmentId: assignment.id, newBayCode: oldBayCode, reason: `Undo move from ${newBayCode}` }),
      redo: () => postBayAction("/api/indian-trail/move", { assignmentId: assignment.id, newBayCode, reason: `Redo move from ${oldBayCode}` }),
    });
  }
}

function selectedPrintListIds() {
  return [...(els.printOptionsStages?.querySelectorAll("input:checked") || [])].map((input) => input.value);
}

function availableGlassTypesForLists(listIds) {
  const wanted = new Set(listIds);
  const types = new Set();
  const sourceLists = state.lists.filter((list) => wanted.has(list.id));
  for (const list of sourceLists) {
    for (const label of list.glassTypes || []) {
      if (label) types.add(label);
    }
    for (const item of list.items || []) {
      const label = glassTypeLabel(item);
      if (label) types.add(label);
    }
  }
  if (state.activeListId && wanted.has(state.activeListId)) {
    for (const item of state.items) {
      const label = glassTypeLabel(item);
      if (label) types.add(label);
    }
  }
  return [...types].sort((a, b) => a.localeCompare(b));
}

function renderPrintGlassTypes() {
  if (!els.printOptionsGlassType) return;
  const current = els.printOptionsGlassType.value || "";
  const types = availableGlassTypesForLists(selectedPrintListIds());
  els.printOptionsGlassType.innerHTML = [
    `<option value="">All glass types</option>`,
    ...types.map((type) => `<option value="${escapeHtml(type)}">${escapeHtml(type)}</option>`),
  ].join("");
  els.printOptionsGlassType.value = types.includes(current) ? current : "";
}

function renderPrintOptionStages() {
  if (!els.printOptionsStages || !els.printOptionsDate) return;
  const date = els.printOptionsDate.value || selectedDeliveryDate() || dashboardDateKey();
  const lists = state.lists.filter((list) => list.deliveryDate === date).sort((a, b) => stageSort(a) - stageSort(b));
  const contextIds = new Set(state.printContext?.listIds || []);
  const hasContextIds = Boolean(state.printContext?.fixedListIds) && contextIds.size > 0;
  els.printOptionsStages.innerHTML = lists
    .map((list) => {
      const checked = hasContextIds ? contextIds.has(list.id) : false;
      return `
        <label>
          <input type="checkbox" value="${escapeHtml(list.id)}" ${checked ? "checked" : ""}>
          <span>${escapeHtml(list.stage)} <small>${escapeHtml(list.scannedQty || 0)} / ${escapeHtml(list.totalQty || 0)}</small></span>
        </label>
      `;
    })
    .join("");
  renderPrintGlassTypes();
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
  for (const input of [els.printUpdatedOnly, els.printRushOnly, els.printRemakeOnly]) {
    if (input) input.checked = false;
  }
  if (els.printMirrorMode) els.printMirrorMode.value = "exclude";
  if (els.printCustomerFilter) els.printCustomerFilter.value = "";
  if (els.printOrderFilter) els.printOrderFilter.value = "";
  renderPrintOptionStages();
  if (els.printOptionsBackdrop) els.printOptionsBackdrop.hidden = false;
  if (els.printOptionsPanel) els.printOptionsPanel.hidden = false;
}

function closePrintOptions() {
  if (els.printOptionsBackdrop) els.printOptionsBackdrop.hidden = true;
  if (els.printOptionsPanel) els.printOptionsPanel.hidden = true;
}

function submitPrintOptions() {
  let listIds = state.printContext?.fixedListIds ? [...(state.printContext.listIds || [])] : selectedPrintListIds();
  if (state.printContext?.useImportCandidates) {
    const importIds = [...new Set((state.lastImportResult?.printCandidates || []).flatMap((candidate) => candidate.listIds || []))];
    if (importIds.length) listIds = importIds;
  }
  if (!listIds.length) {
    showInlineError("Select at least one stage to print or export.", false);
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
    glassType: els.printOptionsGlassType?.value.trim() || "",
    mirrorMode: els.printMirrorMode?.value || "exclude",
    customers: els.printCustomerFilter?.value.trim() || "",
    orders: els.printOrderFilter?.value.trim() || "",
  };
  const params = new URLSearchParams({ listId: listIds.join(",") });
  for (const [key, value] of Object.entries(filters)) {
    if (value) params.set(key, value);
  }
  const mode = document.querySelector('input[name="printExportMode"]:checked')?.value || "print";
  if (mode === "export") {
    window.open(`/api/export/package.xlsx?${params.toString()}`, "_blank", "noopener");
  } else {
    window.open(`/api/print/package?${params.toString()}`, "_blank", "noopener");
  }
  closePrintOptions();
}

async function importTempDeliveryFolder() {
  const sourceFolder = els.tempFolderInput?.value.trim() || "";
  const dateFrom = els.importFromDate?.value || "";
  const dateTo = els.importToDate?.value || "";
  if (els.importPreviewBox) {
    els.importPreviewBox.classList.remove("success", "review");
    els.importPreviewBox.classList.add("loading");
    els.importPreviewBox.innerHTML = `<strong>Importing Temp folder...</strong><span class="loading-bar"><i></i></span>`;
  }
  const result = await fetchJson("/api/import/folder", {
    method: "POST",
    body: JSON.stringify({ ...requestContext(), sourceFolder, dateFrom, dateTo }),
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
    els.importPreviewBox.classList.remove("loading");
    els.importPreviewBox.classList.toggle("success", !failed);
    els.importPreviewBox.classList.toggle("review", Boolean(failed));
    els.importPreviewBox.innerHTML = `
      <strong>Temp folder import complete</strong>
      <span>${imported} new files, ${updated} updated files, ${skipped} unchanged, ${failed} failed.</span>
      ${result.failedFiles?.length ? `<span>${escapeHtml(result.failedFiles.map((file) => `${file.fileName}: ${(file.errors || []).join("; ")}`).join(" | "))}</span>` : ""}
      ${printCandidates.length ? `<button type="button" data-print-import="latest">Print updated package</button>` : ""}
      <details class="import-run-details" open>
        <summary>View imported and updated delivery lists</summary>
        <div class="import-result-list">${importCandidateSummary(result)}</div>
      </details>
    `;
  }
  if (printCandidates.length) {
    showImportResultDialog(result);
  }
}

async function refreshAdminPage() {
  if (!state.backend) return;
  const requests = [];
  requests.push(hasPermission("view_admin") ? fetchJson("/api/admin/summary") : Promise.resolve(null));
  requests.push(hasPermission("manage_users") ? fetchJson("/api/admin/users") : Promise.resolve(null));
  requests.push(hasPermission("view_active_sessions") ? fetchJson("/api/admin/sessions") : Promise.resolve(null));
  requests.push(hasPermission("view_exceptions") ? fetchJson(`/api/exceptions?listId=${encodeURIComponent(state.activeListId || "")}`) : Promise.resolve(null));
  requests.push(hasPermission("manage_customer_route_rules") ? fetchJson("/api/admin/customer-route-rules") : Promise.resolve(null));
  const [summary, users, sessions, exceptions, customerRules] = await Promise.all(requests);
  if (summary) state.adminSummary = summary;
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
    renderAdminResetControls();
    if (els.tempFolderInput && !els.tempFolderInput.value && summary.tempDeliveryListsDir) els.tempFolderInput.value = summary.tempDeliveryListsDir;
  }
  state.adminUsers = users?.users || [];
  state.activeSessions = sessions?.sessions || [];
  state.adminCustomerRouteRules = customerRules?.rules || [];
  renderAdminUsers();
  renderAdminStations();
  renderCustomerRouteRules();
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

function renderAdminResetControls() {
  if (!els.resetListSelect) return;
  const selected = els.resetListSelect.value || state.activeListId || state.lists[0]?.id || "";
  els.resetListSelect.innerHTML = state.lists
    .map((list) => `<option value="${escapeHtml(list.id)}">${escapeHtml(formatDisplayDate(list.deliveryDate))} - ${escapeHtml(list.stage)} - ${escapeHtml(list.scanner)}</option>`)
    .join("");
  els.resetListSelect.value = state.lists.some((list) => list.id === selected) ? selected : state.lists[0]?.id || "";
}

async function resetSelectedAdminScans() {
  const listId = els.resetListSelect?.value || "";
  const list = state.lists.find((item) => item.id === listId);
  if (!list) return;
  const firstConfirm = window.confirm(`Reset all scans for ${list.label}?`);
  if (!firstConfirm) return;
  const typed = window.prompt(`Type RESET to delete all scans associated with ${list.label}.`);
  if (typed !== "RESET") {
    if (els.resetScansStatus) els.resetScansStatus.innerHTML = `<strong>Reset cancelled</strong><span>The confirmation text did not match.</span>`;
    return;
  }
  const payload = await fetchJson("/api/reset", {
    method: "POST",
    body: JSON.stringify({ listId, ...requestContext() }),
  });
  if (payload.meta?.id === state.activeListId) applyBackendPayload(payload);
  await loadDeliveryLists(state.activeListId);
  if (els.resetScansStatus) els.resetScansStatus.innerHTML = `<strong>Scans reset</strong><span>${escapeHtml(list.label)} is back to zero scanned quantity.</span>`;
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
      <thead><tr><th>User</th><th>Roles</th><th>Stages</th><th>Password</th><th>Status</th><th></th></tr></thead>
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
                <td>
                  ${hasPermission("update_user_passwords") ? `
                    <div class="password-reset-row">
                      <input data-user-password="${escapeHtml(user.username)}" type="password" placeholder="Reset password">
                      <button type="button" data-toggle-password="${escapeHtml(user.username)}" title="Show password">Show</button>
                      <button type="button" data-update-user-password="${escapeHtml(user.username)}">Save</button>
                    </div>
                    <small class="password-note">Existing password is securely hashed.</small>
                  ` : `<span>Protected</span>`}
                </td>
                <td>${user.active ? "Active" : "Inactive"}</td>
                <td>
                  ${hasPermission("manage_roles") ? `<button type="button" data-update-user-role="${escapeHtml(user.username)}">Save role</button>` : ""}
                  ${user.active && hasPermission("deactivate_users") ? `<button type="button" data-deactivate-user="${escapeHtml(user.username)}">Deactivate</button>` : ""}
                  ${!user.active && hasPermission("reactivate_users") ? `<button type="button" data-reactivate-user="${escapeHtml(user.username)}">Reactivate</button>` : ""}
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
    .map((station) => `
      <div class="station-row">
        <input data-station-name="${escapeHtml(station)}" type="text" value="${escapeHtml(station)}">
        ${hasPermission("manage_stations") ? `<button type="button" data-rename-station="${escapeHtml(station)}">Save</button>` : ""}
        ${hasPermission("remove_stations") && !DEFAULT_STATIONS.includes(station) ? `<button type="button" data-remove-station="${escapeHtml(station)}">Remove</button>` : ""}
      </div>
    `)
    .join("");
}

function renderCustomerRouteRules() {
  if (!els.customerRouteRules) return;
  els.customerRouteRules.innerHTML = state.adminCustomerRouteRules.length
    ? state.adminCustomerRouteRules
        .map((rule) => `
          <div>
            <strong>${escapeHtml(rule.customerPattern)}</strong>
            <span>${escapeHtml(rule.route)}</span>
            <button type="button" data-remove-customer-route-rule="${escapeHtml(rule.id)}">Remove</button>
          </div>
        `)
        .join("")
    : `<div><strong>No route rules</strong><span>Add CPU, DTC, or GNV customer defaults here.</span></div>`;
}

async function saveCustomerRouteRule() {
  const customerPattern = els.customerRoutePatternInput?.value.trim() || "";
  const route = els.customerRouteSelect?.value || "CPU";
  if (!customerPattern) return;
  const payload = await fetchJson("/api/admin/customer-route-rules", {
    method: "POST",
    body: JSON.stringify({ customerPattern, route }),
  });
  state.adminCustomerRouteRules = payload.rules || [];
  if (els.customerRoutePatternInput) els.customerRoutePatternInput.value = "";
  renderCustomerRouteRules();
}

async function removeCustomerRouteRule(ruleId) {
  const payload = await fetchJson("/api/admin/customer-route-rules/remove", {
    method: "POST",
    body: JSON.stringify({ ruleId }),
  });
  state.adminCustomerRouteRules = payload.rules || [];
  renderCustomerRouteRules();
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
    if (els.importPreviewBox) {
      els.importPreviewBox.classList.remove("success", "review");
      els.importPreviewBox.classList.add("loading");
      els.importPreviewBox.innerHTML = `<strong>Importing ${escapeHtml(file.name)}...</strong><span class="loading-bar"><i></i></span>`;
    }
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
      els.importPreviewBox.classList.remove("loading");
      els.importPreviewBox.classList.add("success");
      els.importPreviewBox.classList.remove("review");
      els.importPreviewBox.innerHTML = `
        <strong>Single file import complete</strong>
        <span>${escapeHtml(file.name)} created ${escapeHtml(created)} stages and updated ${escapeHtml(updated)} stages.</span>
        ${result.printCandidates?.length ? `<button type="button" data-print-import="latest">Print imported updates</button>` : ""}
        <details class="import-run-details" open>
          <summary>View imported and updated delivery lists</summary>
          <div class="import-result-list">${importCandidateSummary({
            importedFiles: created ? [{ fileName: file.name, deliveryDate: result.printCandidates?.[0]?.deliveryDate || "", rowCount: "", totalQty: "", listIds: result.changedListIds || [] }] : [],
            updatedFiles: updated ? [{ fileName: file.name, deliveryDate: result.printCandidates?.[0]?.deliveryDate || "", rowCount: "", totalQty: "", listIds: result.changedListIds || [] }] : [],
          })}</div>
        </details>
      `;
    }
    const printCandidates = result.printCandidates || [];
    if (printCandidates.length) {
      showImportResultDialog({
        ...result,
        importedFiles: created ? [{ fileName: file.name, deliveryDate: printCandidates[0]?.deliveryDate || "", rowCount: "", totalQty: "", listIds: result.changedListIds || [] }] : [],
        updatedFiles: updated ? [{ fileName: file.name, deliveryDate: printCandidates[0]?.deliveryDate || "", rowCount: "", totalQty: "", listIds: result.changedListIds || [] }] : [],
        skippedFiles: [],
        failedFiles: [],
      });
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
        <thead><tr><th>Order</th><th>Item</th><th>Customer</th><th>Qty</th><th>Scanned</th><th>Dims</th><th>Route</th><th>Job</th><th>Product</th><th>Process</th><th>Queue</th><th></th></tr></thead>
        <tbody>
          ${results
            .slice(0, 20)
            .map(
              (item) => `
                <tr data-edit-row="${escapeHtml(item.lineItemId)}">
                  <td><input data-edit-field="order" type="text" value="${escapeHtml(item.order)}"></td>
                  <td><input data-edit-field="item" type="text" value="${escapeHtml(item.item)}"></td>
                  <td><input data-edit-field="customer" type="text" value="${escapeHtml(item.customer)}"></td>
                  <td><input data-edit-field="qty" type="number" min="0" value="${escapeHtml(item.qty)}"></td>
                  <td><input data-edit-field="scanned" type="number" min="0" value="${escapeHtml(item.scanned)}"></td>
                  <td><input data-edit-field="dimensions" type="text" value="${escapeHtml(item.dimensions || "")}"></td>
                  <td><input data-edit-field="route" type="text" value="${escapeHtml(item.route || "")}"></td>
                  <td><input data-edit-field="job" type="text" value="${escapeHtml(item.job || "")}"></td>
                  <td><input data-edit-field="product" type="text" value="${escapeHtml(item.product || "")}"></td>
                  <td><input data-edit-field="processState" type="text" value="${escapeHtml(item.processState || "")}"></td>
                  <td><input data-edit-field="queueState" type="text" value="${escapeHtml(item.queueState || "")}"></td>
                  <td>
                    <button type="button" data-save-line-item="${escapeHtml(item.lineItemId)}">Save</button>
                    <button type="button" data-delete-line-item="${escapeHtml(item.lineItemId)}">Delete</button>
                  </td>
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

async function deleteManualLineItem(lineItemId) {
  if (!window.confirm("Delete this line item from its delivery list?")) return;
  const payload = await fetchJson("/api/admin/line-item/delete", {
    method: "POST",
    body: JSON.stringify({ lineItemId }),
  });
  if (payload.meta?.id === state.activeListId) applyBackendPayload(payload);
  await loadDeliveryLists(state.activeListId);
  await runManualEditSearch();
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
  resetImportDateWindow();
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
  els.globalPrintExportBtn?.addEventListener("click", () => {
    const date = state.page === "scan" ? state.meta?.deliveryDate : dashboardDateKey();
    const listIds = state.lists.filter((list) => !date || list.deliveryDate === date).map((list) => list.id);
    openPrintOptions({ date, listIds });
  });
  els.headerGlobalSearchBtn?.addEventListener("click", () => runGlobalSearch().catch((error) => showInlineError(error.message)));
  els.headerGlobalSearchInput?.addEventListener("input", () => {
    window.clearTimeout(runGlobalSearch._timer);
    runGlobalSearch._timer = window.setTimeout(() => runGlobalSearch().catch((error) => showInlineError(error.message)), 180);
  });
  els.headerGlobalSearchInput?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      runGlobalSearch().catch((error) => showInlineError(error.message));
    }
  });
  els.homeListSearch?.addEventListener("input", () => {
    state.homeSearch = els.homeListSearch.value;
    state.homePageIndex = 1;
    renderHome();
  });
  els.homeStageFilter?.addEventListener("change", () => {
    state.homeStageFilter = els.homeStageFilter.value;
    state.homePageIndex = 1;
    renderHome();
  });
  els.overviewRangeSelect?.addEventListener("change", () => {
    state.overviewRange = els.overviewRangeSelect.value || "30";
    renderHome();
  });
  els.homePageSize?.addEventListener("change", () => {
    state.homePageSize = Number(els.homePageSize.value) || 25;
    state.homePageIndex = 1;
    renderHome();
  });
  els.searchInput?.addEventListener("input", () => {
    state.search = els.searchInput.value;
    state.pageIndex = 1;
    renderScanPage();
  });
  els.pageSize?.addEventListener("change", () => {
    state.pageSize = Number(els.pageSize.value) || 25;
    if (els.pageSizeBottom) els.pageSizeBottom.value = String(state.pageSize);
    state.pageIndex = 1;
    renderScanPage();
  });
  els.pageSizeBottom?.addEventListener("change", () => {
    state.pageSize = Number(els.pageSizeBottom.value) || 25;
    if (els.pageSize) els.pageSize.value = String(state.pageSize);
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
  els.manualAssignForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await submitManualBayAssign();
    } catch (error) {
      showInlineError(error.message, true);
    }
  });
  els.printOptionsDate?.addEventListener("change", () => {
    state.printContext = { ...(state.printContext || {}), listIds: [] };
    renderPrintOptionStages();
  });
  els.printOptionsStages?.addEventListener("change", () => renderPrintGlassTypes());
  els.printOptionsClose?.addEventListener("click", () => closePrintOptions());
  els.printOptionsBackdrop?.addEventListener("click", () => closePrintOptions());
  els.printOptionsSubmit?.addEventListener("click", () => submitPrintOptions());
  els.undoBtn?.addEventListener("click", async () => {
    const payload = await fetchJson("/api/undo", {
      method: "POST",
      body: JSON.stringify({ listId: state.activeListId, ...requestContext() }),
    });
    applyBackendPayload(payload);
    scanFlash(payload.lastScan?.ok ? "success" : "notice");
    renderScanPage();
  });
  els.redoBtn?.addEventListener("click", async () => {
    const payload = await fetchJson("/api/redo", {
      method: "POST",
      body: JSON.stringify({ listId: state.activeListId, ...requestContext() }),
    });
    applyBackendPayload(payload);
    scanFlash(payload.lastScan?.ok ? "success" : "notice");
    renderScanPage();
  });
  els.importBtn?.addEventListener("click", () => {
    if (!els.importFile) return;
    els.importFile.value = "";
    els.importFile.click();
  });
  els.folderImportBtn?.addEventListener("click", () => {
    importTempDeliveryFolder().catch((error) => showInlineError(error.message, true));
  });
  els.importWindowResetBtn?.addEventListener("click", () => resetImportDateWindow());
  els.checkUpdatesBtn?.addEventListener("click", async () => {
    const oldText = els.checkUpdatesBtn.textContent;
    try {
      els.checkUpdatesBtn.disabled = true;
      els.checkUpdatesBtn.textContent = "Checking...";
      if (els.importPreviewBox) {
        els.importPreviewBox.classList.add("loading");
        els.importPreviewBox.innerHTML = `<strong>Checking GitHub for updates...</strong><span class="loading-bar"><i></i></span>`;
      }
      const status = await fetchJson("/api/admin/update-check");
      if (!status.ok) {
        if (els.importPreviewBox) els.importPreviewBox.innerHTML = `<strong>Update check unavailable</strong><span>${escapeHtml(status.error || "Git upstream is not configured.")}</span>`;
        window.alert(`Could not check GitHub updates from this local copy.\n\n${status.error || "Git upstream is not configured."}`);
        return;
      }
      if (status.updateAvailable) {
        if (els.importPreviewBox) els.importPreviewBox.innerHTML = `<strong>Update available</strong><span>${escapeHtml(status.behind)} commit(s) behind ${escapeHtml(status.upstream)}.</span>`;
        window.alert(`Update available: ${status.behind} commit(s) behind ${status.upstream}.\n\nLocal: ${status.local}\nRemote: ${status.remote}`);
      } else {
        if (els.importPreviewBox) els.importPreviewBox.innerHTML = `<strong>No updates found</strong><span>${escapeHtml(status.branch)} is current with ${escapeHtml(status.upstream)}.</span>`;
        window.alert(`No new updates found for ${status.branch}. You have the latest version from ${status.upstream}.`);
      }
    } catch (error) {
      showInlineError(error.message, true);
    } finally {
      els.checkUpdatesBtn.disabled = false;
      els.checkUpdatesBtn.textContent = oldText || "Check updates";
      if (els.importPreviewBox) els.importPreviewBox.classList.remove("loading");
    }
  });
  els.deleteDateSelect?.addEventListener("change", () => renderAdminDeleteControls());
  els.deleteListBtn?.addEventListener("click", () => deleteSelectedDeliveryList(false).catch((error) => showInlineError(error.message, true)));
  els.deleteDateBtn?.addEventListener("click", () => deleteSelectedDeliveryList(true).catch((error) => showInlineError(error.message, true)));
  els.adminResetScansBtn?.addEventListener("click", () => resetSelectedAdminScans().catch((error) => showInlineError(error.message, true)));
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
  els.customerRouteRuleForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    saveCustomerRouteRule().catch((error) => showInlineError(error.message, true));
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
  els.bayScanOutForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    submitBayScanOut().catch((error) => showInlineError(error.message, true));
  });
  els.bayManualSubmitBtn?.addEventListener("click", () => submitManualBayScan().catch((error) => showInlineError(error.message, true)));
  els.bayScanModeToggle?.addEventListener("change", () => {
    if (els.bayScanOutInput) els.bayScanOutInput.placeholder = els.bayScanModeToggle.checked ? "Scan order to add to bay..." : "Scan order to remove from bay...";
  });
  els.bayUndoBtn?.addEventListener("click", () => runBayHistory("undo").catch((error) => showInlineError(error.message, true)));
  els.bayRedoBtn?.addEventListener("click", () => runBayHistory("redo").catch((error) => showInlineError(error.message, true)));
  els.bayMapCanvas?.addEventListener("click", (event) => {
    const columnButton = event.target.closest("[data-bay-col-action]");
    if (columnButton) {
      event.preventDefault();
      event.stopPropagation();
      const section = columnButton.dataset.baySection || "";
      const current = Math.max(1, Math.min(Number(state.bayGroupColumns[section] || 1), 2));
      state.bayGroupColumns[section] = columnButton.dataset.bayColAction === "inc" ? Math.min(current + 1, 2) : Math.max(current - 1, 1);
      renderBayMapPage();
      return;
    }
    const target = event.target.closest("[data-bay-code]");
    if (!target) return;
    if (state.pendingBayMove?.assignmentId) {
      const pendingMove = { ...state.pendingBayMove };
      const newBayCode = target.dataset.bayCode || "";
      const label = `${pendingMove.order}-${pendingMove.item}`;
      if (newBayCode && window.confirm(`Move ${label} to ${newBayCode}?`)) {
        postBayAction("/api/indian-trail/move", {
          assignmentId: pendingMove.assignmentId,
          newBayCode,
          reason: `Moved from ${pendingMove.fromBay}`,
        })
          .then(() => {
            if (pendingMove.fromBay) {
              pushBayHistory({
                label: `move ${label}`,
                undo: () => postBayAction("/api/indian-trail/move", { assignmentId: pendingMove.assignmentId, newBayCode: pendingMove.fromBay, reason: `Undo move from ${newBayCode}` }),
                redo: () => postBayAction("/api/indian-trail/move", { assignmentId: pendingMove.assignmentId, newBayCode, reason: `Redo move from ${pendingMove.fromBay}` }),
              });
            }
            showFloatingNotice(`Moved ${label} to ${newBayCode}.`, "success");
            scanFlash("success");
          })
          .catch((error) => showInlineError(error.message, true));
      }
      state.pendingBayMove = null;
      document.body.classList.remove("bay-move-mode");
      return;
    }
    selectBay(target.dataset.bayCode || "");
  });
  els.baySelectedCloseBtn?.addEventListener("click", () => closeSelectedBayModal());
  els.baySelectedBackdrop?.addEventListener("click", () => closeSelectedBayModal());
  els.bayActionButtons?.addEventListener("click", (event) => {
    const target = event.target.closest("[data-bay-action]");
    if (!target) return;
    runBayAction(target.dataset.bayAction).catch((error) => showInlineError(error.message, true));
  });
  els.sdiCloseBtn?.addEventListener("click", () => closeSdiPanel());
  els.sdiBackdrop?.addEventListener("click", () => closeSdiPanel());
  els.sdiClearBtn?.addEventListener("click", () => submitSdi(false).catch((error) => showInlineError(error.message, true)));
  els.sdiForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    submitSdi(true).catch((error) => showInlineError(error.message, true));
  });
  els.bayLayoutCloseBtn?.addEventListener("click", () => closeBayLayoutManager());
  els.bayLayoutSelect?.addEventListener("change", () => populateBayLayoutForm());
  els.bayLayoutSaveBtn?.addEventListener("click", () => saveBayLayoutForm().catch((error) => showInlineError(error.message, true)));
  els.bayLayoutDeleteBtn?.addEventListener("click", () => deleteSelectedBay().catch((error) => showInlineError(error.message, true)));
  els.bayLayoutUndoBtn?.addEventListener("click", () => runBayLayoutHistory("undo").catch((error) => showInlineError(error.message, true)));
  els.bayLayoutRedoBtn?.addEventListener("click", () => runBayLayoutHistory("redo").catch((error) => showInlineError(error.message, true)));
  els.bayLayoutConfirmBtn?.addEventListener("click", () => confirmBayLayoutDraft().catch((error) => showInlineError(error.message, true)));
  els.bayLayoutCancelBtn?.addEventListener("click", () => cancelBayLayoutDraft());
  els.bayCollapseAllBtn?.addEventListener("click", () => {
    (state.bays || []).forEach((bay) => state.collapsedBaySections.add(bayRackLabel(bay)));
    renderBayMapPage();
  });
  els.bayExpandAllBtn?.addEventListener("click", () => {
    state.collapsedBaySections.clear();
    renderBayMapPage();
  });
  els.bayHoldAllBtn?.addEventListener("click", () => holdAllBaySections());
  window.addEventListener("beforeunload", (event) => {
    if (state.bayEditMode && state.bayHoldingSections.size) {
      event.preventDefault();
      event.returnValue = "";
    }
  });
  for (const container of [els.bayMapCanvas, els.bayAllBaysList]) {
    container?.addEventListener("dragstart", (event) => {
      const groupTarget = event.target.closest("[data-bay-group-drag]");
      if (groupTarget && state.bayEditMode && hasPermission("manage_bay_layout")) {
        event.dataTransfer.setData("text/bay-group", groupTarget.dataset.bayGroupDrag || "");
        event.dataTransfer.effectAllowed = "move";
        return;
      }
      const target = event.target.closest("[data-bay-code]");
      if (!target || !state.bayEditMode || !hasPermission("manage_bay_layout")) return;
      event.dataTransfer.setData("text/plain", target.dataset.bayCode || "");
      event.dataTransfer.effectAllowed = "move";
    });
    container?.addEventListener("dragover", (event) => {
      const target = event.target.closest("[data-bay-holding-drop], [data-bay-grid-cell], [data-bay-drop-section]");
      if (!target || !state.bayEditMode || !hasPermission("manage_bay_layout")) return;
      event.preventDefault();
      if (event.clientY < 90) window.scrollBy({ top: -24, behavior: "auto" });
      if (window.innerHeight - event.clientY < 90) window.scrollBy({ top: 24, behavior: "auto" });
      event.dataTransfer.dropEffect = "move";
    });
    container?.addEventListener("drop", (event) => {
      const target = event.target.closest("[data-bay-holding-drop], [data-bay-grid-cell], [data-bay-drop-section]");
      if (!target || !state.bayEditMode || !hasPermission("manage_bay_layout")) return;
      event.preventDefault();
      const sourceGroup = event.dataTransfer.getData("text/bay-group");
      if (sourceGroup) {
        if (target.dataset.bayHoldingDrop === "true") {
          moveBaySectionDraft(sourceGroup, 0, 0, true);
          return;
        }
        if (target.dataset.bayGridCell === "true") {
          moveBaySectionDraft(sourceGroup, Number(target.dataset.gridRow || 1), Number(target.dataset.gridCol || 1), false);
          return;
        }
        swapBayGroups(sourceGroup, target.dataset.bayDropSection || "").catch((error) => showInlineError(error.message, true));
        return;
      }
      const bayCode = event.dataTransfer.getData("text/plain");
      if (target.dataset.bayGridCell === "true" || target.dataset.bayHoldingDrop === "true") {
        showFloatingNotice("Use the grouped bay header to move bay sets around the edit grid.", "notice");
        return;
      }
      const targetBay = event.target.closest("[data-bay-code]");
      moveBayToGroup(bayCode, target.dataset.bayDropSection || "", target.dataset.bayDropCategory || "", targetBay?.dataset.bayCode || "").catch((error) => showInlineError(error.message, true));
    });
  }

  document.addEventListener("click", (event) => {
    if (
      els.headerGlobalSearchResults &&
      !event.target.closest(".global-search") &&
      !event.target.closest("#headerGlobalSearchResults")
    ) {
      els.headerGlobalSearchResults.hidden = true;
    }
    const pageButton = event.target.closest("[data-page-target]");
    if (pageButton) {
      showPage(pageButton.dataset.pageTarget);
      return;
    }
    const openListButton = event.target.closest("[data-open-list]");
    if (openListButton) {
      const searchText = openListButton.dataset.openSearch || "";
      activateList(openListButton.dataset.openList)
        .then(() => {
          if (searchText) {
            state.search = searchText;
            if (els.searchInput) els.searchInput.value = searchText;
            renderScanPage();
            window.setTimeout(() => document.querySelector("[data-id]")?.scrollIntoView({ behavior: "smooth", block: "center" }), 150);
          }
        })
        .catch((error) => showInlineError(error.message));
      if (els.headerGlobalSearchResults) els.headerGlobalSearchResults.hidden = true;
      return;
    }
    const openBayButton = event.target.closest("[data-open-bay]");
    if (openBayButton) {
      state.selectedBayCode = openBayButton.dataset.openBay || "";
      if (els.headerGlobalSearchResults) els.headerGlobalSearchResults.hidden = true;
      showPage("bays");
      window.setTimeout(() => {
        state.baySearch = state.selectedBayCode;
        scrollToBaySearchMatch();
      }, 350);
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
    const homePageAction = event.target.closest("[data-home-page-action]");
    if (homePageAction) {
      state.homePageIndex += homePageAction.dataset.homePageAction === "next" ? 1 : -1;
      renderHome();
      return;
    }
    const glassToggle = event.target.closest("[data-toggle-glass-group]");
    if (glassToggle) {
      const label = glassToggle.dataset.toggleGlassGroup || "";
      if (state.collapsedGlassTypes.has(label)) state.collapsedGlassTypes.delete(label);
      else state.collapsedGlassTypes.add(label);
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
    const renameStationButton = event.target.closest("[data-rename-station]");
    if (renameStationButton) {
      const oldName = renameStationButton.dataset.renameStation;
      const input = document.querySelector(`[data-station-name="${CSS.escape(oldName)}"]`);
      fetchJson("/api/stations/rename", {
        method: "POST",
        body: JSON.stringify({ oldName, newName: input?.value || "" }),
      })
        .then((payload) => {
          state.stations = uniqueText([...(payload.stations || [])]);
          renderStationOptions();
          renderAdminStations();
        })
        .catch((error) => showInlineError(error.message));
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
    const reactivateUserButton = event.target.closest("[data-reactivate-user]");
    if (reactivateUserButton) {
      fetchJson("/api/admin/users/reactivate", {
        method: "POST",
        body: JSON.stringify({ username: reactivateUserButton.dataset.reactivateUser }),
      })
        .then(() => refreshAdminPage())
        .catch((error) => showInlineError(error.message));
      return;
    }
    const togglePasswordButton = event.target.closest("[data-toggle-password]");
    if (togglePasswordButton) {
      const username = togglePasswordButton.dataset.togglePassword;
      const input = document.querySelector(`[data-user-password="${CSS.escape(username)}"]`);
      if (input) input.type = input.type === "password" ? "text" : "password";
      return;
    }
    const updatePasswordButton = event.target.closest("[data-update-user-password]");
    if (updatePasswordButton) {
      const username = updatePasswordButton.dataset.updateUserPassword;
      const input = document.querySelector(`[data-user-password="${CSS.escape(username)}"]`);
      fetchJson("/api/admin/users/password", {
        method: "POST",
        body: JSON.stringify({ username, password: input?.value || "" }),
      })
        .then(() => {
          if (input) input.value = "";
          refreshAdminPage();
        })
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
    const deleteLineItemButton = event.target.closest("[data-delete-line-item]");
    if (deleteLineItemButton) {
      deleteManualLineItem(deleteLineItemButton.dataset.deleteLineItem).catch((error) => showInlineError(error.message, true));
      return;
    }
    const removeCustomerRouteButton = event.target.closest("[data-remove-customer-route-rule]");
    if (removeCustomerRouteButton) {
      removeCustomerRouteRule(removeCustomerRouteButton.dataset.removeCustomerRouteRule).catch((error) => showInlineError(error.message, true));
      return;
    }
    const printImportButton = event.target.closest("[data-print-import]");
    if (printImportButton) {
      const listIds = [...new Set((state.lastImportResult?.printCandidates || []).flatMap((candidate) => candidate.listIds || []))];
      openPrintOptions({ listIds, date: state.lastImportResult?.printCandidates?.[0]?.deliveryDate || selectedDeliveryDate(), fixedListIds: true });
      return;
    }
    const closeImportButton = event.target.closest("[data-close-import-result]");
    if (closeImportButton) {
      closeImportResultDialog();
      return;
    }
    const printSelectedImportsButton = event.target.closest("[data-print-selected-imports]");
    if (printSelectedImportsButton) {
      const checkedIds = [...document.querySelectorAll(".import-candidate-check:checked")]
        .flatMap((input) => String(input.dataset.importCandidateListids || "").split(",").filter(Boolean));
      const listIds = [...new Set(checkedIds.length ? checkedIds : (state.lastImportResult?.printCandidates || []).flatMap((candidate) => candidate.listIds || []))];
      openPrintOptions({ listIds, date: state.lastImportResult?.printCandidates?.[0]?.deliveryDate || selectedDeliveryDate(), fixedListIds: true });
      return;
    }
    const printCandidateButton = event.target.closest("[data-print-candidate-index]");
    if (printCandidateButton) {
      const rows = [...(state.lastImportResult?.importedFiles || []), ...(state.lastImportResult?.updatedFiles || [])];
      const entry = rows[Number(printCandidateButton.dataset.printCandidateIndex || 0)];
      if (entry?.listIds?.length) {
        openPrintOptions({ listIds: entry.listIds, date: entry.deliveryDate || selectedDeliveryDate(), fixedListIds: true });
      }
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
    const manualAssignBay = event.target.closest("[data-manual-assign-bay]");
    if (manualAssignBay) {
      postBayAction("/api/indian-trail/assign", {
        lineItemId: manualAssignBay.dataset.lineItemId,
        bayCode: manualAssignBay.dataset.manualAssignBay,
        assignedQty: manualAssignBay.dataset.assignedQty || 1,
        reason: "Manual assignment from Indian Trail scan page",
      })
        .then(() => {
          if (els.manualAssignStatus) els.manualAssignStatus.innerHTML = `<article class="message-card ok"><strong>Assigned</strong><span>Bay ${escapeHtml(manualAssignBay.dataset.manualAssignBay)} selected.</span></article>`;
        })
        .catch((error) => showInlineError(error.message, true));
      return;
    }
    const assignmentAction = event.target.closest("[data-assignment-action]");
    if (assignmentAction) {
      runAssignmentAction(assignmentAction.dataset.assignmentAction, assignmentAction.dataset.assignmentId).catch((error) => showInlineError(error.message, true));
      return;
    }
    const bayAction = event.target.closest("[data-bay-action]");
    if (bayAction && !els.bayActionButtons?.contains(bayAction)) {
      runBayAction(bayAction.dataset.bayAction).catch((error) => showInlineError(error.message, true));
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
