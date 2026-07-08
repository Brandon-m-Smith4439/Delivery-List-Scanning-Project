const STORAGE_KEY = "delivery-list-scanner-demo-v1";
const STATIONS_KEY = "delivery-list-scanner-stations-v1";
const DEFAULT_STATIONS = ["Airport Rd", "Indian Trail", "Greenville", "Customer Pickup", "DTC"];
const ROLE_OPTIONS = ["Operator", "Supervisor", "Indian Trail Operator", "Indian Trail Lead", "Indian Trail Manager", "Admin"];
const CUSTOMER_ROUTE_OPTIONS = [
  { value: "CPU", label: "CPU / Customer Pickup" },
  { value: "DTC", label: "DTC / Deliver to Customer" },
  { value: "GNV", label: "GNV / Greenville" },
];

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
  glassTypeFilter: "all",
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
  bayQuickFilter: "all",
  bayStatusFilter: "all",
  bayCategoryFilter: "all",
  bayGlassFilter: "all",
  baySpecialFilter: "all",
  staleBayOrders: [],
  staleBayAlertDate: "",
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
  racks: [],
  rackSummary: null,
  selectedRackCode: "T",
  selectedRackOverviewCode: "",
  selectedRackSetLabel: "",
  rackScanListId: "",
  rackModal: null,
  rackMoveItemId: "",
  rackManagerSelectedCode: "",
  printContext: null,
  bayLayout: null,
  bays: [],
  bayEvents: [],
  adminCustomerRouteRules: [],
  activeSessions: [],
  adminUsers: [],
  adminRoles: [],
  allPermissions: [],
  adminRecentImports: [],
  adminListSearchTimer: null,
  rolePermissionOpenRoles: new Set(),
  rolePermissionOpenCategories: new Set(),
  rolePermissionScrollTop: 0,
  manualEditLookups: { products: [], routes: [], processes: [] },
  manualEditDirty: false,
  manualEditListId: "",
  manualEditQuery: "",
  expandedRackGroups: new Set(),
  expandedRackCodes: new Set(),
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
  signedInRole: document.getElementById("signedInRole"),
  userMenuDisplayName: document.getElementById("userMenuDisplayName"),
  userMenuDetails: document.getElementById("userMenuDetails"),
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
  scanRackPanel: document.getElementById("scanRackPanel"),
  scanRackSelect: document.getElementById("scanRackSelect"),
  scanRackCompleteBtn: document.getElementById("scanRackCompleteBtn"),
  scanRackPrintBtn: document.getElementById("scanRackPrintBtn"),
  scanRackStatus: document.getElementById("scanRackStatus"),
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
  viewAllRecent: document.getElementById("viewAllRecent"),
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
  glassFilterTabs: document.getElementById("glassFilterTabs"),
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

  racksPage: document.getElementById("racksPage"),
  rackSummary: document.getElementById("rackSummary"),
  rackListSelect: document.getElementById("rackListSelect"),
  rackSelect: document.getElementById("rackSelect"),
  rackScanForm: document.getElementById("rackScanForm"),
  rackScanInput: document.getElementById("rackScanInput"),
  rackScanStatus: document.getElementById("rackScanStatus"),
  rackGrid: document.getElementById("rackGrid"),
  rackCreateOpenBtn: document.getElementById("rackCreateOpenBtn"),
  rackSetCreateOpenBtn: document.getElementById("rackSetCreateOpenBtn"),
  rackEditOpenBtn: document.getElementById("rackEditOpenBtn"),

  bayMapPage: document.getElementById("bayMapPage"),
  bayOverviewStats: document.getElementById("bayOverviewStats"),
  bayQuickFilters: document.getElementById("bayQuickFilters"),
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
  bayGlassFilter: document.getElementById("bayGlassFilter"),
  baySpecialFilter: document.getElementById("baySpecialFilter"),
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
  staleBayBackdrop: document.getElementById("staleBayBackdrop"),
  staleBayPanel: document.getElementById("staleBayPanel"),
  staleBayList: document.getElementById("staleBayList"),
  staleBayCloseBtn: document.getElementById("staleBayCloseBtn"),
  staleBayOkBtn: document.getElementById("staleBayOkBtn"),
  staleBayPrintBtn: document.getElementById("staleBayPrintBtn"),
  staleBaySnoozeAllBtn: document.getElementById("staleBaySnoozeAllBtn"),
  staleBaySnoozeAllDays: document.getElementById("staleBaySnoozeAllDays"),
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
  printCustomerFilter: document.getElementById("printCustomerFilter"),
  printOrderFilter: document.getElementById("printOrderFilter"),
  printUpdatedOnly: document.getElementById("printUpdatedOnly"),
  printRushOnly: document.getElementById("printRushOnly"),
  printRemakeOnly: document.getElementById("printRemakeOnly"),
  printOptionsClose: document.getElementById("printOptionsClose"),
  printOptionsSubmit: document.getElementById("printOptionsSubmit"),

  adminPage: document.getElementById("adminPage"),
  adminSummary: document.getElementById("adminSummary"),
  adminLastUpdated: document.getElementById("adminLastUpdated"),
  adminDeliveryLists: document.getElementById("adminDeliveryLists"),
  adminModal: document.getElementById("adminModal"),
  adminModalBackdrop: document.getElementById("adminModalBackdrop"),
  adminModalTitle: document.getElementById("adminModalTitle"),
  adminModalBody: document.getElementById("adminModalBody"),
  adminModalClose: document.getElementById("adminModalClose"),
  folderImportBtn: document.getElementById("folderImportBtn"),
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
  manualEditStageSelect: document.getElementById("manualEditStageSelect"),
  manualEditSearchBtn: document.getElementById("manualEditSearchBtn"),
  manualEditResults: document.getElementById("manualEditResults"),
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

const IMPORT_MAX_DATE = "9999-12-31";

function defaultImportFromDate() {
  const from = new Date();
  from.setDate(from.getDate() - 7);
  return dateInputValue(from);
}

function resetImportDateWindow() {
  if (els.importFromDate) els.importFromDate.value = defaultImportFromDate();
  if (els.importToDate) els.importToDate.value = IMPORT_MAX_DATE;
}

function currentImportDateWindow() {
  const dateFrom = (els.importFromDate?.value || defaultImportFromDate()).trim();
  const dateTo = (els.importToDate?.value || IMPORT_MAX_DATE).trim();

  if (els.importFromDate && !els.importFromDate.value) els.importFromDate.value = dateFrom;
  if (els.importToDate && !els.importToDate.value) els.importToDate.value = dateTo;

  return { dateFrom, dateTo };
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

function userAssignedStation(user = state.user) {
  return String(user?.station || user?.assignedStation || "").trim();
}

function currentScanStation() {
  return userAssignedStation() || els.stationSelect?.value || state.meta?.scanner || DEFAULT_STATIONS[0] || "";
}

function requestContext() {
  return {
    user: state.user?.username || els.operatorInput?.value || "Scanner",
    station: currentScanStation(),
  };
}

function showImportStatusLoading(message, detail = "") {
  if (!els.importPreviewBox) return;

  els.importPreviewBox.hidden = false;
  els.importPreviewBox.classList.remove("success", "review", "notice", "import-status-compact");
  els.importPreviewBox.classList.add("loading");

  els.importPreviewBox.innerHTML = `
    <strong>${escapeHtml(message)}</strong>
    <span class="loading-bar"><i></i></span>
    ${detail ? `<span>${escapeHtml(detail)}</span>` : ""}
  `;
}

function showImportStatusResult(kind, title, detail = "", actionsHtml = "") {
  if (!els.importPreviewBox) return;

  const statusClass = kind === "review" ? "review" : kind === "notice" ? "notice" : "success";

  els.importPreviewBox.hidden = false;
  els.importPreviewBox.classList.remove("loading", "success", "review", "notice");
  els.importPreviewBox.classList.add(statusClass, "import-status-compact");

  els.importPreviewBox.innerHTML = `
    <strong>${escapeHtml(title)}</strong>
    ${detail ? `<span>${escapeHtml(detail)}</span>` : ""}
    ${actionsHtml ? `<div class="import-status-actions">${actionsHtml}</div>` : ""}
  `;
}

function waitForNextPaint() {
  return new Promise((resolve) => {
    requestAnimationFrame(() => {
      requestAnimationFrame(resolve);
    });
  });
}

function updateModalScrollLock() {
  const modalIsOpen = [
    els.adminModal,
    els.printOptionsPanel,
    els.baySelectedModal,
    els.staleBayPanel,
    els.sdiPanel,
  ].some((panel) => panel && !panel.hidden);

  document.body.classList.toggle("modal-scroll-locked", modalIsOpen);
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

  const assignedStation = userAssignedStation();
  const current = assignedStation || preferredStation || els.stationSelect.value || state.meta?.scanner || DEFAULT_STATIONS[0];

  state.stations = uniqueText([...DEFAULT_STATIONS, ...state.stations, current]);
  els.stationSelect.innerHTML = state.stations
    .map((station) => `<option value="${escapeHtml(station)}">${escapeHtml(station)}</option>`)
    .join("");
  els.stationSelect.value = state.stations.includes(current) ? current : state.stations[0];
  els.stationSelect.disabled = Boolean(assignedStation);
  els.stationSelect.title = assignedStation ? "Station is assigned to your login by an admin." : "Station defaults to the selected delivery list.";
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
  if (changingList || navigate) {
    state.pageIndex = 1;
    state.glassTypeFilter = "all";
  }
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
  return /\b(REMAKE|RM)\b/i.test(`${item.processState || ""} ${item.queueState || ""}`);
}

function isRushItem(item) {
  return /\b(RUSH|SDI)\b/i.test(`${item.processState || ""} ${item.queueState || ""}`);
}

function isRemakeOrRush(item) {
  return isRemakeItem(item) || isRushItem(item);
}

function isNewOrUpdatedItem(item) {
  return /\b(NEW LINE|NEW|UPDATED|UPDATE|CHANGED|CHANGE)\b/i.test(`${item.processState || ""} ${item.queueState || ""}`);
}

function hasScanError(item) {
  return Boolean(String(item?.errorReason || item?.lastError || "").trim());
}

function itemPieceQty(item) {
  return Math.max(Number(item?.qty || 0), 0);
}

function itemScannedPieceQty(item) {
  return Math.min(Math.max(Number(item?.scanned || 0), 0), itemPieceQty(item));
}

function pieceCount(items) {
  return items.reduce((sum, item) => sum + itemPieceQty(item), 0);
}

function unscannedPieceCount(items) {
  return items.reduce((sum, item) => sum + Math.max(itemPieceQty(item) - itemScannedPieceQty(item), 0), 0);
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
  const totalQty = pieceCount(items);
  const scannedQty = items.reduce((sum, item) => sum + itemScannedPieceQty(item), 0);
  const remainingQty = Math.max(totalQty - scannedQty, 0);

  const remainingItems = pieceCount(items.filter((item) => itemStatus(item) === "remaining"));
  const partialItems = pieceCount(items.filter((item) => itemStatus(item) === "partial"));
  const completeItems = pieceCount(items.filter((item) => itemStatus(item) === "complete"));
  const errorCount = unscannedPieceCount(items.filter(hasScanError));

  const percent = totalQty ? (scannedQty / totalQty) * 100 : 0;

  return { totalQty, scannedQty, remainingQty, partialItems, completeItems, remainingItems, percent, errorCount };
}

function filteredItems() {
  const search = state.search.trim().toLowerCase();

  return state.items.filter((item) => {
    const status = itemStatus(item);
    const matchesFilter =
      state.filter === "all" ||
      state.filter === status ||
      (state.filter === "errors" && hasScanError(item)) ||
      (state.filter === "remakes" && isRemakeItem(item)) ||
      (state.filter === "rushes" && isRushItem(item)) ||
      (state.filter === "priority" && isRemakeOrRush(item)) ||
      (state.filter === "updated" && isNewOrUpdatedItem(item)) ||
      (state.filter === "cpu-route" && /\bCPU\b|customer pickup/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`)) ||
      (state.filter === "dtc-route" && /\bDTC\b|deliver to customer/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`)) ||
      (state.filter === "greenville-route" && /\bGNV\b|greenville/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`)) ||
      (state.filter === "indian-trail-route" && !/\bCPU\b|\bDTC\b|\bGNV\b|customer pickup|deliver to customer|greenville/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`));

    if (!matchesFilter) return false;
    if (state.glassTypeFilter !== "all" && glassTypeLabel(item) !== state.glassTypeFilter) return false;
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

  const orderedEntries = groups.flatMap((group) =>
    group.items.map((item) => ({
      label: group.label,
      item,
    })),
  );

  const totalPages = Math.max(1, Math.ceil(orderedEntries.length / state.pageSize));
  state.pageIndex = Math.min(Math.max(state.pageIndex, 1), totalPages);

  const pageStart = (state.pageIndex - 1) * state.pageSize;
  const pageEntries = orderedEntries.slice(pageStart, pageStart + state.pageSize);

  const pageGroups = [];
  for (const entry of pageEntries) {
    const lastGroup = pageGroups[pageGroups.length - 1];

    if (lastGroup && lastGroup.label === entry.label) {
      lastGroup.items.push(entry.item);
    } else {
      pageGroups.push({
        label: entry.label,
        items: [entry.item],
      });
    }
  }

  const pageRows = pageEntries.map((entry) => entry.item);
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

function locationLabel(item) {
  const stageText = `${state.meta?.stage || ""} ${state.meta?.scanner || ""}`.toLowerCase();
  if (stageText.includes("indian trail")) return item.bayCode ? `Bay ${item.bayCode}` : "";
  if (item.rackCode === "T") return "Truck";
  if (item.rackCode) return item.rackCode;
  return "";
}

function renderCounts() {
  const stats = getStats();
  const totalItems = pieceCount(state.items);
  const glassCounts = new Map();
  for (const item of state.items) {
    const label = glassTypeLabel(item);
    glassCounts.set(label, (glassCounts.get(label) || 0) + Number(item.qty || 0));
  }

  const remakeItems = state.items.filter(isRemakeItem);
  const rushItems = state.items.filter(isRushItem);
  const updatedItems = state.items.filter(isNewOrUpdatedItem);

  const remakeOpen = unscannedPieceCount(remakeItems);
  const remakeAll = pieceCount(remakeItems);
  const rushOpen = unscannedPieceCount(rushItems);
  const rushAll = pieceCount(rushItems);
  const updatedCount = pieceCount(updatedItems);

  const routeCounts = {
    "indian-trail-route": pieceCount(state.items.filter((item) => !/\bCPU\b|\bDTC\b|\bGNV\b|customer pickup|deliver to customer|greenville/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`))),
    "cpu-route": pieceCount(state.items.filter((item) => /\bCPU\b|customer pickup/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`))),
    "dtc-route": pieceCount(state.items.filter((item) => /\bDTC\b|deliver to customer/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`))),
    "greenville-route": pieceCount(state.items.filter((item) => /\bGNV\b|greenville/i.test(`${item.route || ""} ${item.customer || ""} ${item.job || ""}`))),
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

  document.querySelectorAll('[data-filter="errors"]').forEach((button) => {
    button.classList.toggle("has-alert", Boolean(stats.errorCount));
  });

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
  if (state.glassTypeFilter !== "all" && !glassCounts.has(state.glassTypeFilter)) state.glassTypeFilter = "all";
  if (els.glassFilterTabs) {
    const sortedGlassEntries = [...glassCounts.entries()].sort(
      (a, b) => Number(b[1] || 0) - Number(a[1] || 0) || a[0].localeCompare(b[0]),
    );

    const visibleGlassEntries = sortedGlassEntries.slice(0, 3);
    const hiddenGlassEntries = sortedGlassEntries.slice(3);
    const selectedHiddenGlass = hiddenGlassEntries.find(([label]) => label === state.glassTypeFilter);
    const selectedHiddenCount = selectedHiddenGlass ? selectedHiddenGlass[1] : 0;

    const visibleGlassButtons = visibleGlassEntries.map(
      ([label, count]) =>
        `<button class="tab glass-filter-tab ${state.glassTypeFilter === label ? "is-active" : ""}" data-glass-filter="${escapeHtml(label)}" type="button">${escapeHtml(label)} <span>(${escapeHtml(count)})</span></button>`,
    );

    const moreGlassButton = hiddenGlassEntries.length
      ? `
        <details class="glass-filter-more">
          <summary class="tab glass-filter-tab glass-filter-more-summary ${selectedHiddenGlass ? "is-active" : ""}">
            ${selectedHiddenGlass ? escapeHtml(state.glassTypeFilter) : "More Glass Types"}
            <span>${selectedHiddenGlass ? `(${escapeHtml(selectedHiddenCount)})` : `+${hiddenGlassEntries.length}`}</span>
          </summary>
          <div class="glass-filter-menu">
            ${hiddenGlassEntries
              .map(
                ([label, count]) =>
                  `<button class="tab glass-filter-tab ${state.glassTypeFilter === label ? "is-active" : ""}" data-glass-filter="${escapeHtml(label)}" type="button">${escapeHtml(label)} <span>(${escapeHtml(count)})</span></button>`,
              )
              .join("")}
          </div>
        </details>
      `
      : "";

    const glassButtons = [
      `<button class="tab glass-filter-tab ${state.glassTypeFilter === "all" ? "is-active" : ""}" data-glass-filter="all" type="button">All Glass <span>(${totalItems})</span></button>`,
      ...visibleGlassButtons,
      moreGlassButton,
    ];

    els.glassFilterTabs.innerHTML = glassButtons.join("");
  }
  if (els.totalItemsText) els.totalItemsText.textContent = `${state.items.length} rows / ${totalItems} pieces`;
  if (els.progressText) els.progressText.textContent = `${stageVerb()} Qty: ${stats.scannedQty}/${stats.totalQty} - ${formatPercent(stats.percent)} Complete`;
  if (els.progressFill) els.progressFill.style.width = `${Math.min(stats.percent, 100)}%`;
  if (els.remainingQty) els.remainingQty.textContent = String(stats.remainingQty);
  if (els.partialQty) els.partialQty.textContent = String(stats.partialItems);
  if (els.completeQty) els.completeQty.textContent = String(stats.completeItems);
  if (els.errorQty) els.errorQty.textContent = String(stats.errorCount);
  if (els.remainingPct) els.remainingPct.textContent = formatPercent(100 - stats.percent);
  if (els.partialPct) els.partialPct.textContent = formatPercent(stats.totalQty ? (stats.partialItems / stats.totalQty) * 100 : 0);
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
  const routeTag = route
    ? `<span class="route-tag ${escapeHtml(route.toLowerCase())}">${escapeHtml(route)}</span>`
    : "";
  const location = locationLabel(item);
  const locationClass = location
    ? `location-badge ${
        location.toLowerCase().includes("bay")
          ? "bay"
          : location.toLowerCase().includes("truck")
            ? "truck"
            : "rack"
      }`
    : "";

  const markers = [
    isRemakeItem(item) ? '<span class="row-marker remake-marker">RM</span>' : "",
    isRushItem(item) ? '<span class="row-marker rush-marker">Rush</span>' : "",
  ]
    .filter(Boolean)
    .join("");

  const rowError = hasScanError(item);
  const processClass = rowError ? "error" : status;
  const processText = rowError ? item.errorReason || item.lastError || "Scan issue" : renderProcessState(item);
  const lastScanNote = item.lastScannedAt
    ? `<span class="last-scan-note">Scanned: ${escapeHtml(formatDateTime(item.lastScannedAt))}${item.lastScannedStation ? ` - ${escapeHtml(item.lastScannedStation)}` : ""}</span>`
    : "";

  return `
    <tr class="${selected ? "is-selected" : ""} ${status === "complete" ? "is-complete" : ""} ${isNewOrUpdatedItem(item) ? "is-new-line" : ""}" data-id="${escapeHtml(item.id)}">
      <td><span class="job-title">${escapeHtml(item.product || item.job)}</span><span class="job-subtitle">${escapeHtml(item.job)}</span>${lastScanNote}</td>
      <td>${escapeHtml(item.order)}</td>
      <td>${escapeHtml(item.item)}</td>
      <td><span class="qty-pill ${status}">${item.scanned} / ${item.qty}</span></td>
      <td>${escapeHtml(item.dimensions)}</td>
      <td>${escapeHtml(item.customer)}</td>
      <td>${markers}</td>
      <td>${routeTag}</td>
      <td class="location-cell">${location ? `<span class="${escapeHtml(locationClass)}">${escapeHtml(location)}</span>` : ""}</td>
      <td><span class="process-pill ${processClass}">${escapeHtml(processText)}</span></td>
    </tr>
  `;
}

function renderTable() {
  if (!els.listRows) return;
  const { rows, pageGroups, totalPages } = getPagedItems();
  renderPagers(rows.length, totalPages);
  if (!pageGroups.length) {
    els.listRows.innerHTML = `<tr><td colspan="10">No rows match the current filters.</td></tr>`;
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
          <td colspan="10">
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

function stagingLists() {
  return state.lists.filter((list) => /staging/i.test(`${list.stage || ""} ${list.label || ""}`));
}

async function refreshRacksPage() {
  if (!hasAnyPermission(["view_racks", "scan_racks", "manage_racks"])) return;
  if (state.backend) {
    const payload = await fetchJson("/api/racks");
    state.racks = payload.racks || [];
    state.rackSummary = payload.summary || null;
  }
  renderRacksPage();
}

function renderRackSelects() {
  const stageLists = stagingLists();
  if (!state.rackScanListId || !stageLists.some((list) => list.id === state.rackScanListId)) {
    state.rackScanListId = stageLists[0]?.id || "";
  }
  if (!state.selectedRackCode || !state.racks.some((rack) => rack.code === state.selectedRackCode)) {
    state.selectedRackCode = state.racks.find((rack) => rack.code === "T")?.code || state.racks[0]?.code || "";
  }
  if (els.rackListSelect) {
    els.rackListSelect.innerHTML = stageLists
      .map((list) => `<option value="${escapeHtml(list.id)}">${escapeHtml(formatDisplayDate(list.deliveryDate))} - ${escapeHtml(list.stage)}</option>`)
      .join("");
    els.rackListSelect.value = state.rackScanListId;
  }
  if (els.rackSelect) {
    els.rackSelect.innerHTML = state.racks
      .map((rack) => `<option value="${escapeHtml(rack.code)}">${rackOptionLabel(rack)}</option>`)
      .join("");
    els.rackSelect.value = state.selectedRackCode;
  }
}

function rackGroupLabel(rack) {
  return rack.code === "T" || /truck/i.test(rack.type || "") ? "Truck" : rack.type || "Racks";
}

function rackOptionLabel(rack) {
  const status = String(rack.status || "Open");
  const qty = Number(rack.qty || 0);
  const stateText = status.toLowerCase() === "closed" ? "Complete" : qty ? "Open with items" : "Empty";
  return `${escapeHtml(rack.code)} - ${escapeHtml(rack.name)} (${escapeHtml(qty)} pcs, ${escapeHtml(stateText)})`;
}

function rackVisualClass(rack) {
  const status = String(rack.status || "").toLowerCase();
  if (status === "closed") return "is-complete";
  if (Number(rack.qty || 0) > 0) return "has-items";
  return "is-empty";
}

function renderRacksPage() {
  renderRackSelects();

  const summary = state.rackSummary || {};

  if (els.rackSummary) {
    els.rackSummary.innerHTML = [
      miniStat("Rack Pieces", summary.rackQty || 0),
      miniStat("Truck Pieces", summary.truckQty || 0),
      miniStat("Active Racks", summary.rackCount || 0),
    ].join("");
  }

  if (!els.rackGrid) return;

  const rackGroups = new Map();

  for (const rack of state.racks) {
    const label = rack.code === "T" || /truck/i.test(rack.type) ? "Truck" : rack.type || "Racks";

    if (!rackGroups.has(label)) {
      rackGroups.set(label, []);
    }

    rackGroups.get(label).push(rack);
  }

  const groups = [...rackGroups.entries()].sort(([a], [b]) => {
    if (a === "Truck") return 1;
    if (b === "Truck") return -1;

    const order = { Steel: 1, Wood: 2 };
    return (order[a] || 50) - (order[b] || 50) || a.localeCompare(b);
  });

  const renderRackItem = (item, currentRackCode = "") => {
    const rackItemId = String(item.rackItemId || "");
    const moveOpen = state.rackMoveItemId === rackItemId;

    const destinationOptions = state.racks
      .filter((target) => target.code !== currentRackCode)
      .map((target) => `<option value="${escapeHtml(target.code)}">${rackOptionLabel(target)}</option>`)
      .join("");

    return `
      <article class="rack-item ${moveOpen ? "is-moving" : ""}">
        <div>
          <strong>${escapeHtml(item.order)}-${escapeHtml(item.item)} <span>${escapeHtml(item.customer || "")}</span></strong>
          <small>${escapeHtml(item.job || item.product || "")}</small>
          <small>${escapeHtml(item.product || item.job || "")} | ${escapeHtml(item.dimensions || "")} | Qty ${escapeHtml(item.rackQty || 1)}</small>
          <small class="rack-scan-time">${escapeHtml(item.deliveryLabel || "")}${item.rackAddedAt ? ` | Scanned ${escapeHtml(formatDateTime(item.rackAddedAt))}` : ""}</small>
        </div>

        ${
          hasPermission("manage_racks")
            ? `<div class="rack-item-actions">
                <button
                  type="button"
                  class="icon-only icon-move"
                  data-rack-move-open="${escapeHtml(rackItemId)}"
                  title="Move piece"
                  aria-label="Move ${escapeHtml(item.order)}-${escapeHtml(item.item)}"
                ></button>
                <button
                  type="button"
                  class="icon-only icon-trash danger"
                  data-rack-clear-item="${escapeHtml(rackItemId)}"
                  data-rack-clear-label="${escapeHtml(`${item.order}-${item.item}`)}"
                  title="Clear piece"
                  aria-label="Clear ${escapeHtml(item.order)}-${escapeHtml(item.item)}"
                ></button>
              </div>

              ${
                moveOpen
                  ? `<div class="rack-move-popover">
                      <div class="rack-move-title">
                        <strong>Move Piece</strong>
                        <span>${escapeHtml(item.order)}-${escapeHtml(item.item)}</span>
                      </div>

                      <label>
                        <span>Move to</span>
                        <select data-rack-target="${escapeHtml(rackItemId)}">
                          <option value="">Select destination...</option>
                          ${destinationOptions}
                        </select>
                      </label>

                      <div class="rack-move-actions">
                        <button type="button" class="rack-move-cancel" data-rack-move-cancel="${escapeHtml(rackItemId)}">Cancel</button>
                        <button type="button" class="rack-move-confirm" data-rack-move="${escapeHtml(rackItemId)}" ${destinationOptions ? "" : "disabled"}>Confirm Move</button>
                      </div>
                    </div>`
                  : ""
              }`
            : ""
        }
      </article>
    `;
  };

  const renderRackItems = (rack) => {
    const items = rack.items || [];

    if (!items.length) {
      return `<p class="admin-empty">No pieces assigned.</p>`;
    }

    const isTruck = rack.code === "T" || /truck/i.test(rack.type || "");
    const isComplete = String(rack.status || "").toLowerCase() === "closed";

    if (!isTruck) {
      return items.map((item) => renderRackItem(item, rack.code)).join("");
    }

    const byDate = new Map();

    for (const item of items) {
      const key = item.deliveryDate || "No delivery date";

      if (!byDate.has(key)) {
        byDate.set(key, []);
      }

      byDate.get(key).push(item);
    }

    return [...byDate.entries()]
      .sort(([a], [b]) => String(a).localeCompare(String(b)))
      .map(([date, dateItems]) => {
        const dateHasMoveOpen = dateItems.some((item) => String(item.rackItemId || "") === state.rackMoveItemId);
        const dateQty = dateItems.reduce((sum, item) => sum + Number(item.rackQty || 1), 0);

        return `
          <details class="rack-date-group" ${dateHasMoveOpen ? "open" : ""}>
            <summary>
              <strong>${escapeHtml(formatDisplayDate(date))}</strong>
              <span>${escapeHtml(dateQty)} pcs</span>
              ${isComplete ? `<button type="button" data-rack-print="${escapeHtml(rack.code)}" data-rack-print-date="${escapeHtml(date)}">Print This Date</button>` : ""}
            </summary>
            <div>${dateItems.map((item) => renderRackItem(item, rack.code)).join("")}</div>
          </details>
        `;
      })
      .join("");
  };

  const renderRack = (rack) => {
    const hasItems = Number(rack.qty || 0) > 0;
    const isTruck = rack.code === "T" || /truck/i.test(rack.type || "");
    const isComplete = String(rack.status || "").toLowerCase() === "closed";
    const rackHasMoveOpen = (rack.items || []).some((item) => String(item.rackItemId || "") === state.rackMoveItemId);
    const rackOpen = state.expandedRackCodes.has(rack.code) || rackHasMoveOpen;

    const adminActions = hasPermission("manage_racks")
      ? `<span class="rack-summary-actions">
          <button
            type="button"
            class="icon-only icon-pencil"
            data-rack-edit="${escapeHtml(rack.code)}"
            title="Edit rack"
            aria-label="Edit ${escapeHtml(rack.code)}"
          ></button>
          <button
            type="button"
            class="icon-only icon-trash danger"
            data-rack-clear="${escapeHtml(rack.code)}"
            title="Clear rack"
            aria-label="Clear ${escapeHtml(rack.code)}"
          ></button>
        </span>`
      : "";

    const printLabel = isTruck ? "Print Truck Packing List" : "Print Packing List";
    const printAction =
      hasItems && isComplete
        ? `<button type="button" data-rack-print="${escapeHtml(rack.code)}">${printLabel}</button>`
        : "";

    return `
      <details class="rack-card ${rackVisualClass(rack)}" data-rack-code="${escapeHtml(rack.code)}" ${rackOpen ? "open" : ""}>
        <summary>
          <span class="rack-summary-main">
            <strong>${escapeHtml(rack.code)}</strong>
            <small>${escapeHtml(rack.name)}</small>
          </span>
          <span class="rack-summary-qty">${escapeHtml(rack.qty || 0)} pcs</span>
          ${adminActions}
        </summary>
        <div class="rack-card-actions">
          ${
            hasItems
              ? `${printAction}${
                  isComplete
                    ? `<button type="button" data-rack-uncomplete="${escapeHtml(rack.code)}">Uncomplete Rack</button>`
                    : `<button type="button" data-rack-complete="${escapeHtml(rack.code)}">Complete Rack</button>`
                }`
              : ""
          }
        </div>
        <div class="rack-item-list">
          ${hasItems ? renderRackItems(rack) : `<p class="admin-empty">No pieces assigned.</p>`}
        </div>
      </details>
    `;
  };

  const renderRackColumnActions = (label) => {
    if (!hasPermission("manage_racks")) return "";

    if (label === "Truck") {
      return `
        <div class="rack-column-actions">
          <button
            type="button"
            class="icon-only icon-pencil light"
            data-rack-edit="T"
            title="Edit truck / no rack"
            aria-label="Edit truck / no rack"
          ></button>
        </div>
      `;
    }

    return `
      <div class="rack-column-actions">
        <button
          type="button"
          class="icon-only icon-pencil light"
          data-rack-set-edit="${escapeHtml(label)}"
          title="Edit rack set"
          aria-label="Edit ${escapeHtml(label)} rack set"
        ></button>
      </div>
    `;
  };

  const rackStatusText = (rack) => {
    const status = String(rack.status || "").toLowerCase();
    const qty = Number(rack.qty || 0);

    if (status === "closed") return "Complete";
    if (qty > 0) return "Open";
    return "Empty";
  };

  const rackStatusClass = (rack) => {
    const status = String(rack.status || "").toLowerCase();
    const qty = Number(rack.qty || 0);

    if (status === "closed") return "complete";
    if (qty > 0) return "open";
    return "empty";
  };

  const renderRackBoardCard = (rack) => {
    const selected = state.selectedRackOverviewCode === rack.code;
    const statusText = rackStatusText(rack);
    const statusClass = rackStatusClass(rack);
    const isTruck = rack.code === "T" || /truck/i.test(rack.type || "");

    return `
      <article
        class="rack-board-card ${rackVisualClass(rack)} ${selected ? "is-selected" : ""}"
        data-rack-select="${escapeHtml(rack.code)}"
        tabindex="0"
        role="button"
        aria-label="View ${escapeHtml(isTruck ? "Truck" : rack.code)} details"
      >
        <div class="rack-board-card-main">
          <strong>${escapeHtml(isTruck ? "Truck" : rack.code)}</strong>
          <span>${escapeHtml(rack.name || rack.type || "")}</span>
        </div>

        <div class="rack-board-card-meta">
          <b>${escapeHtml(rack.qty || 0)} pcs</b>
          <small class="rack-status-badge ${escapeHtml(statusClass)}">${escapeHtml(statusText)}</small>
          ${
            hasPermission("manage_racks")
              ? `<button type="button" class="icon-only icon-reset" data-rack-clear="${escapeHtml(rack.code)}" title="Clear rack" aria-label="Clear ${escapeHtml(rack.code)}"></button>`
              : ""
          }
        </div>
      </article>
    `;
  };

  const renderRackBoardGroup = ([label, racks]) => {
    const totalQty = racks.reduce((sum, rack) => sum + Number(rack.qty || 0), 0);
    const activeCount = racks.filter((rack) => Number(rack.qty || 0) > 0).length;
    const completeCount = racks.filter((rack) => String(rack.status || "").toLowerCase() === "closed").length;

    return `
      <section class="rack-board-group" data-rack-group="${escapeHtml(label)}">
        <header class="rack-board-group-header">
          <div>
            <h2>${escapeHtml(label)}</h2>
            <span>${escapeHtml(racks.length)} ${racks.length === 1 ? "rack" : "racks"} | ${escapeHtml(activeCount)} active | ${escapeHtml(completeCount)} complete</span>
          </div>

          <strong>${escapeHtml(totalQty)} pcs</strong>

          ${renderRackColumnActions(label)}
          ${
            hasPermission("manage_racks")
              ? `<button type="button" class="icon-only icon-reset light" data-rack-set-clear="${escapeHtml(label)}" title="Clear rack set" aria-label="Clear ${escapeHtml(label)} rack set"></button>`
              : ""
          }
        </header>

        <div class="rack-board-card-list">
          ${racks.map(renderRackBoardCard).join("") || `<p class="admin-empty">No ${escapeHtml(label.toLowerCase())} racks.</p>`}
        </div>
      </section>
    `;
  };

  const groupLabels = groups.map(([label]) => label);
  if (!state.selectedRackSetLabel || !groupLabels.includes(state.selectedRackSetLabel)) {
    state.selectedRackSetLabel = groupLabels.find((label) => label !== "Truck") || groupLabels[0] || "";
  }

  const selectedGroup = groups.find(([label]) => label === state.selectedRackSetLabel) || groups[0] || ["", []];
  const selectedGroupLabel = selectedGroup[0];
  const selectedGroupRacks = selectedGroup[1] || [];

  if (!state.selectedRackOverviewCode || !selectedGroupRacks.some((rack) => rack.code === state.selectedRackOverviewCode)) {
    state.selectedRackOverviewCode =
      selectedGroupRacks.find((rack) => Number(rack.qty || 0) > 0)?.code ||
      selectedGroupRacks[0]?.code ||
      state.racks.find((rack) => Number(rack.qty || 0) > 0)?.code ||
      state.racks[0]?.code ||
      "";
  }

  const selectedRack = state.racks.find((rack) => rack.code === state.selectedRackOverviewCode) || state.racks[0] || null;

  const renderRackSetCard = ([label, racks]) => {
    const selected = label === selectedGroupLabel;
    const totalQty = racks.reduce((sum, rack) => sum + Number(rack.qty || 0), 0);
    const activeCount = racks.filter((rack) => Number(rack.qty || 0) > 0).length;
    const completeCount = racks.filter((rack) => String(rack.status || "").toLowerCase() === "closed").length;
    const setClass = slugify(label || "rack-set") || "rack-set";

    return `
      <button type="button" class="rack-set-card ${escapeHtml(setClass)} ${selected ? "is-selected" : ""}" data-rack-set-select="${escapeHtml(label)}">
        <span class="rack-set-icon ${escapeHtml(setClass)}" aria-hidden="true"></span>
        <span class="rack-set-copy">
          <strong>${escapeHtml(label)}</strong>
          <small>${escapeHtml(racks.length)} rack${racks.length === 1 ? "" : "s"}</small>
          <b>${escapeHtml(totalQty)} piece${totalQty === 1 ? "" : "s"}</b>
        </span>
        <span class="rack-set-chevron">›</span>
        <span class="rack-set-meta">${escapeHtml(activeCount)} active | ${escapeHtml(completeCount)} complete</span>
        ${
          hasPermission("manage_racks")
            ? `<span class="rack-set-reset-inline icon-only icon-reset" data-rack-set-clear="${escapeHtml(label)}" title="Clear ${escapeHtml(label)}" aria-label="Clear ${escapeHtml(label)}"></span>`
            : ""
        }
      </button>
    `;
  };

  const renderSelectedRackDetails = (rack) => {
    if (!rack) {
      return `
        <section class="rack-detail-panel">
          <div class="admin-empty">No racks available. Create a rack to get started.</div>
        </section>
      `;
    }

    const hasItems = Number(rack.qty || 0) > 0;
    const isTruck = rack.code === "T" || /truck/i.test(rack.type || "");
    const isComplete = String(rack.status || "").toLowerCase() === "closed";
    const statusText = rackStatusText(rack);
    const statusClass = rackStatusClass(rack);
    const printLabel = isTruck ? "Print Truck Packing List" : "Print Packing List";

    return `
      <section class="rack-detail-panel ${escapeHtml(statusClass)}">
        <header class="rack-detail-header">
          <div>
            <span class="rack-detail-eyebrow">Selected Rack</span>
            <h2>${escapeHtml(isTruck ? "Truck / No Rack" : rack.code)}</h2>
            <p>${escapeHtml(rack.name || rack.type || "")}</p>
          </div>

          <div class="rack-detail-stats">
            <span><small>Pieces</small><strong>${escapeHtml(rack.qty || 0)}</strong></span>
            <span><small>Status</small><strong>${escapeHtml(statusText)}</strong></span>
          </div>
        </header>

        <div class="rack-detail-actions">
          ${
            hasItems
              ? isComplete
                ? `<button type="button" data-rack-uncomplete="${escapeHtml(rack.code)}">Uncomplete Rack</button>`
                : `<button type="button" data-rack-complete="${escapeHtml(rack.code)}">Complete Rack</button>`
              : ""
          }

          <button type="button" data-rack-print="${escapeHtml(rack.code)}" ${hasItems && isComplete ? "" : "disabled"}>${printLabel}</button>

          ${
            hasPermission("manage_racks")
              ? `
                <button type="button" data-rack-edit="${escapeHtml(rack.code)}">Edit Rack</button>
                <button type="button" class="danger" data-rack-clear="${escapeHtml(rack.code)}" ${hasItems ? "" : "disabled"}>Clear Rack</button>
              `
              : ""
          }
        </div>

        <div class="rack-detail-pieces">
          <div class="rack-detail-subheading">
            <strong>Pieces in ${escapeHtml(isTruck ? "Truck" : rack.code)}</strong>
            <span>${escapeHtml(rack.qty || 0)} pcs</span>
          </div>

          <div class="rack-item-list">
            ${hasItems ? renderRackItems(rack) : `<p class="admin-empty">No pieces assigned.</p>`}
          </div>
        </div>
      </section>
    `;
  };

  const selectedSetQty = selectedGroupRacks.reduce((sum, rack) => sum + Number(rack.qty || 0), 0);

  els.rackGrid.innerHTML = `
    <aside class="rack-sets-sidebar">
      <header>
        <h2>Rack Sets</h2>
        <span>All rack sets at a glance</span>
      </header>
      <div class="rack-set-list">
        ${groups.map(renderRackSetCard).join("") || `<div class="admin-empty">No rack sets found.</div>`}
      </div>
    </aside>

    <section class="rack-center-panel">
      <div class="rack-center-heading">
        <div>
          <h2>${escapeHtml(selectedGroupLabel || "Racks")}</h2>
          <span>${escapeHtml(selectedGroupRacks.length)} rack${selectedGroupRacks.length === 1 ? "" : "s"} | ${escapeHtml(selectedSetQty)} pieces</span>
        </div>
        <div class="rack-center-controls">
          <button type="button" class="rack-filter-button" disabled>Status: All</button>
          <button type="button" class="rack-filter-button" disabled>Sort: Rack ID (A-Z)</button>
          <button type="button" class="icon-only icon-reset" data-rack-set-clear="${escapeHtml(selectedGroupLabel)}" ${hasPermission("manage_racks") ? "" : "hidden"} title="Clear selected rack set" aria-label="Clear selected rack set"></button>
        </div>
      </div>

      <div class="rack-overview-card-grid">
        ${selectedGroupRacks.map(renderRackBoardCard).join("") || `<p class="admin-empty">No racks in this set.</p>`}
      </div>
    </section>

    ${renderSelectedRackDetails(selectedRack)}
  `;
}

async function submitRackScan() {
  const barcode = els.rackScanInput?.value || "";
  const rackCode = els.rackSelect?.value || state.selectedRackCode;
  const listId = els.rackListSelect?.value || state.rackScanListId;
  if (!barcode.trim() || !rackCode || !listId) {
    if (els.rackScanStatus) els.rackScanStatus.textContent = "Choose a staging list and rack, then scan a piece.";
    return;
  }
  const payload = await fetchJson("/api/racks/scan", {
    method: "POST",
    body: JSON.stringify({ listId, rackCode, barcode, ...requestContext() }),
  });
  state.racks = payload.racks || state.racks;
  state.rackSummary = payload.summary || state.rackSummary;
  if (els.rackScanStatus) els.rackScanStatus.textContent = payload.message || "Rack scan recorded.";
  if (els.rackScanInput) els.rackScanInput.value = "";
  renderRacksPage();
  if (listId === state.activeListId) await activateList(listId, false);
  els.rackScanInput?.focus();
}

async function completeRack(code) {
  const payload = await fetchJson("/api/racks/complete", { method: "POST", body: JSON.stringify({ rackCode: code }) });
  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  renderRacksPage();
  renderScanRackTools();
}

async function uncompleteRack(code) {
  const payload = await fetchJson("/api/racks/uncomplete", { method: "POST", body: JSON.stringify({ rackCode: code }) });
  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  renderRacksPage();
  renderScanRackTools();
}

async function clearRack(code) {
  if (!window.confirm(`Clear all active pieces from ${code}?`)) return;
  const payload = await fetchJson("/api/racks/clear", { method: "POST", body: JSON.stringify({ rackCode: code }) });
  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  renderRacksPage();
}

async function clearRackSet(label) {
  const racks = (state.racks || []).filter((rack) => rackGroupLabel(rack) === label);
  if (!racks.length) return;
  if (!window.confirm(`Clear all active pieces from every rack in ${label}? Individual pieces will be left as delivery-list scans.`)) return;
  let latestPayload = null;
  for (const rack of racks) {
    latestPayload = await fetchJson("/api/racks/clear", { method: "POST", body: JSON.stringify({ rackCode: rack.code }) });
  }
  if (latestPayload) {
    state.racks = latestPayload.racks || [];
    state.rackSummary = latestPayload.summary || null;
  }
  renderRacksPage();
}

async function moveRackItem(rackItemId) {
  const select = document.querySelector(`[data-rack-target="${CSS.escape(String(rackItemId))}"]`);
  const targetRackCode = select?.value || "";

  if (!targetRackCode) {
    showFloatingNotice("Choose a destination rack before confirming the move.", "notice");
    return;
  }

  const payload = await fetchJson("/api/racks/move-item", {
    method: "POST",
    body: JSON.stringify({ rackItemId, targetRackCode }),
  });

  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  state.rackMoveItemId = "";

  renderRacksPage();
}

async function clearRackItem(rackItemId, label = "this piece") {
  if (!window.confirm(`Clear ${label} from its rack? This does not change scan quantities.`)) return;
  const payload = await fetchJson("/api/racks/clear-item", { method: "POST", body: JSON.stringify({ rackItemId }) });
  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  renderRacksPage();
  renderScanRackTools();
}

function rackPackingListUrl(rackCode, deliveryDate = "") {
  const dateParam = deliveryDate ? `&deliveryDate=${encodeURIComponent(deliveryDate)}` : "";
  return `/api/racks/packing-list?rackCode=${encodeURIComponent(rackCode)}${dateParam}`;
}

function printSelectedRackPackingSlip() {
  if (!state.selectedRackCode) return;
  const rack = state.racks.find((item) => item.code === state.selectedRackCode);
  if (!rack || String(rack.status || "").toLowerCase() !== "closed") {
    showFloatingNotice("Complete this rack before printing its packing list.", "notice");
    return;
  }
  const activeList = state.lists.find((list) => list.id === state.activeListId);
  const dateParam = state.selectedRackCode === "T" && activeList?.deliveryDate ? activeList.deliveryDate : "";
  window.open(rackPackingListUrl(state.selectedRackCode, dateParam), "_blank", "noopener");
}

async function saveRackDefinition() {
  const payload = await fetchJson("/api/racks", {
    method: "POST",
    body: JSON.stringify({
      rackCode: document.getElementById("rackModalCode")?.value || "",
      name: document.getElementById("rackModalName")?.value || "",
      type: document.getElementById("rackModalType")?.value || "Steel",
    }),
  });
  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  renderRacksPage();
  closeAdminModal();
}

function selectedRackManagerRack(code = state.rackManagerSelectedCode) {
  return state.racks.find((rack) => rack.code === code) || state.racks[0] || null;
}

function populateRackManagerQuickEdit(code = "") {
  const select = document.getElementById("rackManagerQuickRackSelect");
  const nameInput = document.getElementById("rackManagerQuickName");
  const typeInput = document.getElementById("rackManagerQuickType");
  const rack = selectedRackManagerRack(code || select?.value || state.rackManagerSelectedCode);

  if (!rack) return;

  state.rackManagerSelectedCode = rack.code || "";
  if (select) select.value = rack.code || "";
  if (nameInput) nameInput.value = rack.name || rack.type || rack.code || "";
  if (typeInput) typeInput.value = rack.type || "Steel";
}

async function saveRackQuickEdit() {
  const code = document.getElementById("rackManagerQuickRackSelect")?.value || state.rackManagerSelectedCode || "";
  if (!code) return;

  const payload = await fetchJson("/api/racks", {
    method: "POST",
    body: JSON.stringify({
      rackCode: code,
      name: document.getElementById("rackManagerQuickName")?.value || code,
      type: document.getElementById("rackManagerQuickType")?.value || "Steel",
    }),
  });

  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  state.rackManagerSelectedCode = code;
  renderRacksPage();
  renderScanRackTools();

  if (!els.adminModal?.hidden && els.adminModalBody?.querySelector(".rack-manager-shell")) {
    els.adminModalBody.innerHTML = adminModalContent("racks");
  }

  showFloatingNotice(`Saved rack ${code}.`, "success");
}

async function deleteRackDefinition(rackCode = state.selectedRackCode) {
  if (!rackCode) return;
  const typed = window.prompt(`Delete rack ${rackCode}? Empty racks only. Type DELETE RACK to confirm.`);
  if (typed !== "DELETE RACK") return;
  const payload = await fetchJson("/api/racks/delete", { method: "POST", body: JSON.stringify({ rackCode }) });
  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  if (state.selectedRackOverviewCode === rackCode) state.selectedRackOverviewCode = "";
  renderRacksPage();
  renderScanRackTools();
  if (!els.adminModal?.hidden && els.adminModalBody?.querySelector(".rack-manager-shell")) {
    els.adminModalBody.innerHTML = adminModalContent("racks");
  }
}

async function createRackSet() {
  const prefix = document.getElementById("rackSetModalPrefix")?.value || "";
  const nameRoot = document.getElementById("rackSetModalName")?.value || prefix || "Rack";
  const payload = await fetchJson("/api/racks/create-set", {
    method: "POST",
    body: JSON.stringify({
      prefix,
      nameRoot,
      type: nameRoot,
      count: document.getElementById("rackSetModalCount")?.value || 10,
      start: document.getElementById("rackSetModalStart")?.value || 1,
    }),
  });
  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  renderRacksPage();
  renderScanRackTools();
  closeAdminModal();
  showFloatingNotice(`Created ${payload.created?.length || 0} rack(s).`, "success");
}

function openRackForm(rackCode = "") {
  const rack = state.racks.find((item) => item.code === rackCode) || {};
  state.rackModal = { rack };
  openAdminModal("rackForm");
}

function openRackSetForm(label = "") {
  const racks = state.racks.filter((rack) => (rack.code === "T" || /truck/i.test(rack.type || "") ? "Truck" : rack.type || "Racks") === label);
  state.rackModal = {
    set: {
      name: label && label !== "Truck" ? label : "",
      prefix: "",
      count: racks.length || 10,
      start: 1,
    },
  };
  openAdminModal("rackSetForm");
}

async function deleteRackSet(label) {
  const racks = state.racks.filter((rack) => (rack.code === "T" || /truck/i.test(rack.type || "") ? "Truck" : rack.type || "Racks") === label);
  const deletable = racks.filter((rack) => rack.code !== "T");
  if (!deletable.length) return;
  if (!window.confirm(`Delete ${deletable.length} rack(s) in ${label}? Empty racks only.`)) return;
  for (const rack of deletable) {
    await fetchJson("/api/racks/delete", { method: "POST", body: JSON.stringify({ rackCode: rack.code }) });
  }
  await ensureRacksLoaded();
  renderRacksPage();
  renderScanRackTools();
  if (!els.adminModal?.hidden && els.adminModalBody?.querySelector(".rack-manager-shell")) {
    els.adminModalBody.innerHTML = adminModalContent("racks");
  }
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
  const rows = state.recent.slice(0, 2);
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

function recentScansModalHtml() {
  const rows = state.recent || [];
  return `
    <div class="recent-scans-modal">
      <div class="modal-list-heading">
        <strong>${escapeHtml(state.meta?.label || state.meta?.stage || "Current stage")}</strong>
        <span>${escapeHtml(rows.length)} recent scan${rows.length === 1 ? "" : "s"}</span>
      </div>
      <div class="recent-table-wrap expanded">
        <table class="recent-table">
          <thead>
            <tr>
              <th>Barcode</th>
              <th>Order Nr.</th>
              <th>Item Nr.</th>
              <th>Qty Scanned</th>
              <th>Date & Time Scanned</th>
              <th>Check</th>
            </tr>
          </thead>
          <tbody>
            ${
              rows.length
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
                : `<tr><td colspan="6">No scans yet</td></tr>`
            }
          </tbody>
        </table>
      </div>
    </div>
  `;
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
  const displayName = state.user ? state.user.displayName || state.user.username : "Demo";
  const roleText = state.user?.roles?.length ? state.user.roles.join(", ") : state.backend ? "Signed in" : "Local demo";
  const stationText = userAssignedStation(state.user) || currentScanStation() || "No assigned station";
  const initials = state.user ? userInitials(state.user) : "DM";
  const accentClass = state.user ? userAccentClass(state.user) : "accent-default";

  if (els.signedInUser) {
    els.signedInUser.textContent = displayName;
  }

  if (els.signedInRole) {
    els.signedInRole.textContent = roleText;
  }

  if (els.userMenuDisplayName) {
    els.userMenuDisplayName.textContent = displayName;
  }

  if (els.userMenuDetails) {
    els.userMenuDetails.textContent = `${roleText} • ${stationText}`;
  }

  document.querySelectorAll(".user-menu .user-avatar").forEach((avatar) => {
    avatar.textContent = initials;
    avatar.className = `user-avatar ${accentClass}${avatar.classList.contains("user-menu-large-avatar") ? " user-menu-large-avatar" : ""}`;
    avatar.setAttribute("aria-hidden", "true");
  });

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
  renderScanRackTools();
  applyPermissionUi();
}

function isStagingScanContext() {
  return /staging/i.test(`${state.meta?.stage || ""} ${state.meta?.scanner || ""}`);
}

async function ensureRacksLoaded() {
  if (!state.backend || state.racks.length) return;
  const payload = await fetchJson("/api/racks");
  state.racks = payload.racks || [];
  state.rackSummary = payload.summary || null;
  renderScanRackTools();
}

function renderScanRackTools() {
  if (!els.scanRackPanel) return;
  const visible = isStagingScanContext() && hasPermission("scan_racks");
  els.scanRackPanel.hidden = !visible;
  if (!visible) return;
  if (!state.racks.length) {
    els.scanRackPanel.classList.add("is-loading");
    void ensureRacksLoaded().catch((error) => showInlineError(error.message, true));
    return;
  }
  els.scanRackPanel.classList.remove("is-loading");
  if (!state.selectedRackCode || !state.racks.some((rack) => rack.code === state.selectedRackCode)) {
    state.selectedRackCode = state.racks.find((rack) => rack.code === "T")?.code || state.racks[0]?.code || "";
  }
  const selectedRack = state.racks.find((rack) => rack.code === state.selectedRackCode);
  const selectedClosed = String(selectedRack?.status || "").toLowerCase() === "closed";
  els.scanRackPanel.classList.toggle("selected-rack-complete", selectedClosed);
  els.scanRackPanel.classList.toggle("selected-rack-loaded", Boolean(selectedRack && Number(selectedRack.qty || 0) > 0 && !selectedClosed));
  if (els.scanRackSelect) {
    els.scanRackSelect.innerHTML = state.racks
      .map((rack) => `<option value="${escapeHtml(rack.code)}">${rackOptionLabel(rack)}</option>`)
      .join("");
    els.scanRackSelect.value = state.selectedRackCode;
  }
  if (els.scanRackCompleteBtn) els.scanRackCompleteBtn.textContent = selectedClosed ? "Uncomplete" : "Complete";
  if (els.scanRackPrintBtn) els.scanRackPrintBtn.disabled = !selectedRack || !selectedClosed || Number(selectedRack.qty || 0) <= 0;
  if (els.scanRackStatus) els.scanRackStatus.textContent = "";
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
    els.todayDateLabel.textContent = formatDisplayDate(key);
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

function renderHomeStageFilter() {
  if (!els.homeStageFilter) return;
  const current = state.homeStageFilter || "all";
  const stageOptions = uniqueText(
    state.lists
      .map((list) => stageLabel(list) || list.stage || list.scanner || "")
      .filter(Boolean),
  ).sort((a, b) => a.localeCompare(b));

  els.homeStageFilter.innerHTML = [
    `<option value="all">All stages</option>`,
    ...stageOptions.map((stage) => `<option value="${escapeHtml(stage)}">${escapeHtml(stage)}</option>`),
  ].join("");
  els.homeStageFilter.value = stageOptions.some((stage) => stage.toLowerCase() === String(current).toLowerCase()) ? current : "all";
  state.homeStageFilter = els.homeStageFilter.value;
}

function renderHome() {
  if (!els.homePage) return;
  renderHomeStageFilter();
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
  if (!dateGroups.some((group) => group.date === state.expandedDeliveryDate)) state.expandedDeliveryDate = "";
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
  if (page === "racks" && !hasAnyPermission(["view_racks", "scan_racks", "manage_racks"])) page = "home";
  if (page === "home") state.expandedDeliveryDate = "";
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
  if (page === "racks") refreshRacksPage().catch((error) => showInlineError(error.message, true));
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
      /indian trail/i.test(`${state.meta?.stage || ""} ${currentScanStation()}`);
    if (indianTrailReceive) {
      const result = await fetchJson("/api/indian-trail/receive", {
        method: "POST",
        body: JSON.stringify({ listId: state.activeListId, barcode: scanText, ...requestContext() }),
      });
      await activateList(state.activeListId, false);
      state.lastScan = result.lastScan || state.lastScan;
      scanFlash(result.ok ? "success" : "error");
      if (result?.message) {
        const lastItem = result.lastScan?.item || {};
        const bayPrompt = result.ok && result.bayCode
          ? `Place order ${lastItem.order || ""}${lastItem.item ? `-${lastItem.item}` : ""} in Bay ${result.bayCode}.`
          : result.message;
        showFloatingNotice(bayPrompt, result.ok ? (/\bSDI|Rush\b/i.test(result.message) ? "notice" : "success") : "error");
      }
      renderScanPage();
      void refreshBayMapPage().catch(() => {});
      return;
    }
    const payload = await fetchJson("/api/scans", {
      method: "POST",
      body: JSON.stringify({
        listId: state.activeListId,
        barcode: scanText,
        rackCode: isStagingScanContext() ? state.selectedRackCode : "",
        ...requestContext(),
      }),
    });
    applyBackendPayload(payload);
    if (payload.message) {
      showFloatingNotice(payload.message, payload.lastScan?.ok ? "success" : "notice");
    }
    if (payload.racks) {
      state.racks = payload.racks || state.racks;
      state.rackSummary = payload.rackSummary || state.rackSummary;
    } else if (isStagingScanContext() && state.racks.length) {
      void ensureRacksLoaded().catch(() => {});
    }
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
    showFloatingNotice(`${entry.message}: ${entry.reason}`, "error");
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
    showFloatingNotice(entry.reason, "notice");
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
  showFloatingNotice(message, needsReview ? "error" : "notice");
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
  notice.classList.remove("is-hiding");
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
      (result) => {
        return `
        <button type="button" ${result.bayCode ? `data-open-bay="${escapeHtml(result.bayCode)}"` : `data-open-list="${escapeHtml(result.deliveryListId)}" data-open-search="${escapeHtml([result.order, result.item].filter(Boolean).join(" "))}"`}>
          <strong>${escapeHtml(result.order)}-${escapeHtml(result.item)}</strong>
          <span>${escapeHtml(result.job || result.product || "")}</span>
          <span>${escapeHtml(result.customer)}${result.bay ? ` - Bay ${escapeHtml(result.bay)}` : ""}</span>
          <small>${escapeHtml(result.locationText || result.stage || "")}</small>
        </button>
      `;
      },
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
  maybeShowStaleBayAlert().catch(() => {});
}

function renderBayRouteFlow(summary) {
  if (!els.bayFlowPanel) return;

  const key = dashboardDateKey();
  const dayLists = state.lists.filter((list) => list.deliveryDate === key);
  const outbound = dayLists.find((list) => stageCategory(list) === "outbound");
  const inbound = dayLists.find((list) => stageCategory(list) === "received") || state.lists.find((list) => list.id === summary?.activeInboundListId);

  const inboundQty = Number(inbound?.scannedQty ?? summary?.receivedQty ?? 0);
  const inboundTotal = Number(inbound?.totalQty ?? summary?.indianTrailOutboundTotal ?? summary?.inboundToday ?? 0);

  const outboundQty = Number(summary?.indianTrailOutboundScanned ?? outbound?.scannedQty ?? 0);
  const outboundTotal = inboundTotal || Number(summary?.indianTrailOutboundTotal ?? outbound?.totalQty ?? 0);

  const inTransitQty = Math.max(outboundQty - inboundQty, 0);
  const rackLine = (summary?.racksInTransit || [])
    .slice(0, 5)
    .map((rack) => `${rack.code}: ${rack.qty}`)
    .join(" | ");
  const truckQty = Number(summary?.truckInTransitQty || 0);
  const rackQty = Number(summary?.rackInTransitQty || 0);

  els.bayFlowPanel.innerHTML = `
    <button class="flow-card outbound" type="button" ${outbound ? `data-open-list="${escapeHtml(outbound.id)}"` : ""}>
      <small>Outbound to Indian Trail</small>
      <strong>${escapeHtml(outboundQty)} / ${escapeHtml(outboundTotal)}</strong>
      <span>${outbound ? escapeHtml(outbound.stage) : "No outbound list"}</span>
      <em>Truck ${escapeHtml(truckQty)} | Racks ${escapeHtml(rackQty)}</em>
    </button>
    <div class="flow-lane" aria-hidden="true">
      <span class="flow-truck"><b>In Transit: ${escapeHtml(inTransitQty)}</b></span>
    </div>
    <button class="flow-card inbound" type="button" ${inbound ? `data-open-list="${escapeHtml(inbound.id)}"` : ""}>
      <small>Indian Trail Delivery List</small>
      <strong>${escapeHtml(inboundQty)} / ${escapeHtml(inboundTotal)}</strong>
      <span>${inbound ? escapeHtml(inbound.stage) : "No Indian Trail list"}</span>
    </button>
    ${rackLine ? `<div class="flow-rack-line">In transit racks: ${escapeHtml(rackLine)}</div>` : ""}
  `;

  const miniRoute = document.getElementById("bayPanelRouteMini");
  if (miniRoute) {
    miniRoute.innerHTML = `
      <div class="bay-panel-route-node outbound">
        <small>Outbound</small>
        <strong>${escapeHtml(outboundQty)} / ${escapeHtml(outboundTotal)}</strong>
      </div>
      <div class="bay-panel-route-lane">
        <span>In Transit: ${escapeHtml(inTransitQty)} | Truck ${escapeHtml(truckQty)} | Racks ${escapeHtml(rackQty)}</span>
      </div>
      <div class="bay-panel-route-node inbound">
        <small>Indian Trail</small>
        <strong>${escapeHtml(inboundQty)} / ${escapeHtml(inboundTotal)}</strong>
      </div>
    `;
  }
}

function renderIndianTrailSummary(summary) {
  if (!els.indianTrailSummary) return;
  const overview = bayOverview();

  els.indianTrailSummary.innerHTML = `
    <div class="mini-stat-grid">
      ${miniStat("Total", overview.total)}
      ${miniStat("Available", overview.available)}
      ${miniStat("Occupied", overview.occupied)}
      ${miniStat("Preassigned", overview.preassigned)}
      ${miniStat("SDI", overview.sdi)}
      ${miniStat("Hold/Blocked", overview.blocked)}
      ${miniStat("Needs Check", summary?.needsCheck ?? 0)}
    </div>
  `;
}

function bayMatchesFilter(bay, text) {
  const search = state.baySearch.trim().toLowerCase();
  const status = String(bay?.status || "").toLowerCase();
  const sourceStatus = String(bay?.sourceStatus || "").toLowerCase();
  const statusKind = bayStatusKind(bay);
  const matchesQuick = bayMatchesQuickFilter(bay);
  const matchesCategory = state.bayCategoryFilter === "all" || bayCategoryKind(bay) === state.bayCategoryFilter;
  const matchesGlass =
    state.bayGlassFilter === "all" ||
    (bay.assignments || []).some((assignment) => normalizeFilterValue(assignment.product || assignment.job || "Other Glass") === state.bayGlassFilter) ||
    normalizeFilterValue(bayGlassLabel(bay)) === state.bayGlassFilter;
  const matchesSpecial =
    state.baySpecialFilter === "all" ||
    (state.baySpecialFilter === "old" && Number(bay.staleDays || 0) > 10) ||
    (state.baySpecialFilter === "sdi" && (statusKind === "picking" || (bay.assignments || []).some((assignment) => String(assignment.status || "").toLowerCase().includes("sdi")))) ||
    (state.baySpecialFilter === "new" && Boolean(bay.isNewToday || (bay.assignments || []).some((assignment) => assignment.isNewToday)));
  const matchesStatus =
    state.bayStatusFilter === "all" ||
    state.bayStatusFilter === statusKind ||
    (state.bayStatusFilter === "manual" && (!bay?.active || sourceStatus.includes("manual"))) ||
    (state.bayStatusFilter === "empty" && (status.includes("empty") || status.includes("available"))) ||
    status.includes(state.bayStatusFilter);
  if (!matchesQuick || !matchesCategory || !matchesStatus || !matchesGlass || !matchesSpecial) return false;
  if (!search) return true;
  return text.toLowerCase().includes(search);
}

function bayHasErrorState(bay) {
  const haystack = [
    bay?.status,
    bay?.sourceStatus,
    bay?.reason,
    ...(bay?.assignments || []).flatMap((assignment) => [
      assignment.status,
      assignment.processState,
      assignment.queueState,
      assignment.reason,
      assignment.lastStage,
    ]),
  ].join(" ").toLowerCase();
  return /error|exception|conflict|needs\s*check|bad|blocked|hold/.test(haystack);
}

function bayMatchesQuickFilter(bay) {
  const filter = state.bayQuickFilter || "all";
  const kind = bayStatusKind(bay);
  if (filter === "all") return true;
  if (filter === "occupied") return kind === "occupied";
  if (filter === "preassigned") return kind === "preassigned";
  if (filter === "available") return kind === "available";
  if (filter === "blocked") return kind === "blocked" || kind === "manual";
  if (filter === "error") return bayHasErrorState(bay);
  if (filter === "old") return Number(bay?.staleDays || 0) > 10 || (bay?.assignments || []).some((assignment) => assignment.isStale);
  if (filter === "sdi") return kind === "picking" || (bay?.assignments || []).some((assignment) => String(assignment.status || "").toLowerCase().includes("sdi"));
  if (filter === "new") return Boolean(bay?.isNewToday || (bay?.assignments || []).some((assignment) => assignment.isNewToday));
  return true;
}

function bayQuickFilterOptions() {
  return [
    ["all", "All"],
    ["occupied", "Occupied"],
    ["preassigned", "Pre Assigned"],
    ["error", "Errors"],
    ["old", "Old Orders"],
    ["sdi", "SDI"],
    ["new", "New Today"],
    ["blocked", "Blocked"],
    ["available", "Available"],
  ];
}

function renderBayQuickFilters() {
  if (!els.bayQuickFilters) return;
  const countable = (state.bays || []).filter((bay) => bayCategoryKind(bay) !== "spacer");
  els.bayQuickFilters.innerHTML = bayQuickFilterOptions()
    .map(([value, label]) => {
      const count = value === "all" ? countable.length : countable.filter((bay) => bayMatchesQuickFilterForCount(bay, value)).length;
      return `<button class="bay-filter-chip ${state.bayQuickFilter === value ? "is-active" : ""}" type="button" data-bay-quick-filter="${escapeHtml(value)}"><span>${escapeHtml(label)}</span><strong>${escapeHtml(count)}</strong></button>`;
    })
    .join("");
}

function bayMatchesQuickFilterForCount(bay, value) {
  const previous = state.bayQuickFilter;
  state.bayQuickFilter = value;
  const matches = bayMatchesQuickFilter(bay);
  state.bayQuickFilter = previous;
  return matches;
}

function normalizeFilterValue(value) {
  return String(value || "").trim().toLowerCase();
}

function bayGlassLabel(bay) {
  const assignment = (bay?.assignments || [])[0];
  return String(assignment?.product || assignment?.job || bay?.bayCategory || bay?.bayType || "Other Glass").trim() || "Other Glass";
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
    ...(bay?.assignments || []).map((assignment) => `${assignment.order} ${assignment.item} ${assignment.customer} ${assignment.product} ${assignment.job} ${assignment.dimensions} ${assignment.deliveryDate}`),
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

function bayGlassFilterOptions() {
  const values = new Map();
  for (const bay of state.bays || []) {
    for (const assignment of bay.assignments || []) {
      const label = String(assignment.product || assignment.job || "Other Glass").trim() || "Other Glass";
      values.set(normalizeFilterValue(label), label);
    }
  }
  return [["all", "All glass types"], ...[...values.entries()].sort((a, b) => a[1].localeCompare(b[1]))];
}

function bayOverview() {
  const countableBays = state.bays.filter((bay) => bayCategoryKind(bay) !== "spacer");

  const available = countableBays.filter((bay) => bayStatusKind(bay) === "available").length;
  const occupied = countableBays.filter((bay) => bayStatusKind(bay) === "occupied").length;
  const preassigned = countableBays.filter((bay) => bayStatusKind(bay) === "preassigned").length;
  const sdi = countableBays.filter((bay) => bayStatusKind(bay) === "picking").length;
  const blocked = countableBays.filter((bay) => {
    const kind = bayStatusKind(bay);
    return kind === "blocked" || kind === "manual";
  }).length;

  return {
    total: countableBays.length,
    available,
    occupied,
    preassigned,
    sdi,
    blocked,
  };
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
  const ribbons = [
    Number(bay.staleDays || 0) > 10 ? `<span class="bay-ribbon stale">${escapeHtml(bay.staleDays)}d</span>` : "",
    bay.isNewToday ? `<span class="bay-ribbon new">NEW</span>` : "",
  ].filter(Boolean).join("");
  return `
    <button class="${mode === "physical" ? "physical-bay-slot" : "bay-slot"} type-${escapeHtml(kind)} status-${escapeHtml(statusKind)} ${escapeHtml(String(status).toLowerCase())} ${dimmed ? "is-dimmed" : ""} ${searchMatch ? "is-search-match" : ""} ${state.selectedBayCode === bay.bayCode ? "is-selected" : ""}"
      type="button"
      data-bay-code="${escapeHtml(bay.bayCode)}"
      data-assignment-id="${escapeHtml(assignment?.id || "")}"
      ${state.bayEditMode && hasPermission("manage_bay_layout") ? 'draggable="true"' : ""}
      title="${escapeHtml(text)}">
      ${ribbons}
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
  const positions = {};
  sections.forEach((section, index) => {
    const row = Math.floor(index / 7) + 1;
    const col = (index % 7) + 1;
    if (row <= 7) {
      positions[section.label] = { row, col, holding: false };
    } else {
      positions[section.label] = { row: 0, col: 0, holding: true };
    }
  });
  return positions;
}

function renderBaySection(section) {
  const filtersActive = state.baySearch.trim() || state.bayQuickFilter !== "all" || state.bayStatusFilter !== "all" || state.bayCategoryFilter !== "all" || state.bayGlassFilter !== "all" || state.baySpecialFilter !== "all";
  const displayBays = filtersActive ? section.bays.filter((bay) => bayMatchesFilter(bay, baySearchText(bay))) : section.bays;
  const visible = displayBays.length;
  const dimmed = !visible && filtersActive;
  const occupied = section.bays.filter((bay) => Number(bay.assignedQty || 0) > 0).length;
  const open = Boolean(filtersActive) || !state.collapsedBaySections.has(section.label);
  const cols = Math.max(1, Math.min(Number(state.bayGroupColumns[section.label] || 1), 2));
  return `
    <details ${open ? "open" : ""} class="physical-bay-section type-${escapeHtml(section.kind)} cols-${cols} ${state.bayEditMode ? "is-editing" : ""} ${dimmed ? "is-dimmed" : ""}" data-bay-drop-section="${escapeHtml(section.label)}" data-bay-drop-category="${escapeHtml(section.kind)}">
      <summary ${state.bayEditMode && hasPermission("manage_bay_layout") ? 'draggable="true"' : ""} data-bay-group-drag="${escapeHtml(section.label)}"><strong>${escapeHtml(section.label)}</strong><span>${escapeHtml(occupied)} / ${escapeHtml(section.bays.length)}</span>${state.bayEditMode ? `<span class="bay-column-controls"><button type="button" data-bay-col-action="dec" data-bay-section="${escapeHtml(section.label)}">-</button><b>${cols} col</b><button type="button" data-bay-col-action="inc" data-bay-section="${escapeHtml(section.label)}">+</button></span>` : ""}</summary>
      <div class="physical-slot-grid" style="--bay-section-cols:${cols}">
        ${displayBays.map((bay) => renderBaySlotButton(bay, "physical")).join("")}
      </div>
    </details>
  `;
}

function renderBayGrid(physicalSections) {
  if (state.bayEditMode && !state.bayLayoutDraft) initializeBayLayoutDraft();
  if (!state.bayEditMode) {
    return `
      <section class="bay-dense-grid">
        ${physicalSections.length ? physicalSections.map((section) => renderBaySection(section)).join("") : `<div class="admin-empty">No bays match those filters.</div>`}
      </section>
    `;
  }
  const sectionByLabel = new Map(physicalSections.map((section) => [section.label, section]));
  const cells = [];
  for (let row = 1; row <= 7; row += 1) {
    for (let col = 1; col <= 7; col += 1) {
      const section = physicalSections.find((item) => {
        const draft = state.bayLayoutDraft?.[item.label];
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
  const filtersActive = state.baySearch.trim() || state.bayQuickFilter !== "all" || state.bayStatusFilter !== "all" || state.bayCategoryFilter !== "all" || state.bayGlassFilter !== "all" || state.baySpecialFilter !== "all";
  const physicalSections = bayPhysicalSections().filter((section) => !filtersActive || section.bays.some((bay) => bayMatchesFilter(bay, baySearchText(bay))));
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
  renderBayQuickFilters();
  renderBayRecentActions();
}

function renderBaySidePanels() {
  if (els.bayCategoryFilters) {
    els.bayCategoryFilters.innerHTML = bayCategoryFilterOptions()
      .map(([value, label]) => `<button class="tab ${state.bayCategoryFilter === value ? "is-active" : ""}" type="button" data-bay-category-filter="${escapeHtml(value)}">${escapeHtml(label)}</button>`)
      .join("");
  }
  if (els.bayGlassFilter) {
    const options = bayGlassFilterOptions();
    if (state.bayGlassFilter !== "all" && !options.some(([value]) => value === state.bayGlassFilter)) state.bayGlassFilter = "all";
    els.bayGlassFilter.innerHTML = options.map(([value, label]) => `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`).join("");
    els.bayGlassFilter.value = state.bayGlassFilter;
  }
  if (els.baySpecialFilter) els.baySpecialFilter.value = state.baySpecialFilter;
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

async function loadStaleBayOrders(includeSnoozed = false) {
  if (!state.backend) {
    state.staleBayOrders = [];
    return [];
  }
  const payload = await fetchJson(`/api/indian-trail/stale-bays${includeSnoozed ? "?includeSnoozed=1" : ""}`);
  state.staleBayOrders = payload.orders || [];
  return state.staleBayOrders;
}

async function maybeShowStaleBayAlert() {
  if (state.page !== "bays" || !hasPermission("view_bays")) return;
  const today = new Date().toISOString().slice(0, 10);
  const key = `staleBayAlertSeen:${state.user?.username || "user"}:${today}`;
  if (sessionStorage.getItem(key) === "1") return;
  const orders = await loadStaleBayOrders(false);
  if (!orders.length) return;
  sessionStorage.setItem(key, "1");
  openStaleBayPanel(orders);
}

function openStaleBayPanel(orders = state.staleBayOrders) {
  if (!els.staleBayPanel || !els.staleBayBackdrop) return;
  renderStaleBayPanel(orders || []);
  els.staleBayPanel.hidden = false;
  els.staleBayBackdrop.hidden = false;
  updateModalScrollLock();
}

function closeStaleBayPanel() {
  if (els.staleBayPanel) els.staleBayPanel.hidden = true;
  if (els.staleBayBackdrop) els.staleBayBackdrop.hidden = true;
  updateModalScrollLock();
}

function renderStaleBayPanel(orders) {
  if (!els.staleBayList) return;
  if (!orders.length) {
    els.staleBayList.innerHTML = `<div class="admin-empty">No bay orders are older than 10 days right now.</div>`;
    return;
  }
  els.staleBayList.innerHTML = orders
    .map((order) => `
      <article class="stale-bay-order">
        <span class="age-ribbon">${escapeHtml(order.daysOld)} days</span>
        <div class="stale-bay-main">
          <strong>${escapeHtml(order.order)}-${escapeHtml(order.item)} <span>${escapeHtml(order.customer || "")}</span></strong>
          <div class="stale-bay-meta-grid">
            <small><b>Bay</b>${escapeHtml(order.bayDisplay || order.bayCode)}</small>
            <small><b>Glass</b>${escapeHtml(order.job || order.product || "")}</small>
            <small><b>Size</b>${escapeHtml(order.dimensions || "")}</small>
            <small><b>Delivery</b>${escapeHtml(formatDisplayDate(order.deliveryDate || ""))}</small>
            <small><b>Last scanned</b>${escapeHtml(formatDateTime(order.lastScannedAt) || "Not scanned")}</small>
          </div>
        </div>
        <div class="stale-snooze-row">
          <label>
            <span>Snooze</span>
            <select data-stale-days="${escapeHtml(order.assignmentId)}" aria-label="Snooze days">
              <option value="1">1 day</option>
              <option value="3">3 days</option>
              <option value="7">1 week</option>
              <option value="14">2 weeks</option>
              <option value="30">30 days</option>
            </select>
          </label>
          <button type="button" data-stale-snooze="${escapeHtml(order.assignmentId)}">Apply</button>
        </div>
      </article>
    `)
    .join("");
}

async function snoozeStaleBayOrders(assignmentIds, days) {
  const payload = await fetchJson("/api/indian-trail/stale-bays/snooze", {
    method: "POST",
    body: JSON.stringify({ assignmentIds, days }),
  });
  state.staleBayOrders = payload.orders || [];
  renderStaleBayPanel(state.staleBayOrders);
  await refreshBayMapPage();
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
    updateModalScrollLock();
  }
}

function closeSelectedBayModal() {
  if (els.baySelectedModal) els.baySelectedModal.hidden = true;
  if (els.baySelectedBackdrop) els.baySelectedBackdrop.hidden = true;
  updateModalScrollLock();
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
  updateModalScrollLock();
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
  updateModalScrollLock();
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
  if (action === "old-bays") {
    const orders = await loadStaleBayOrders(false);
    openStaleBayPanel(orders);
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

function selectedPrintStageInputs() {
  return [...(els.printOptionsStages?.querySelectorAll('.print-stage-choice:not(.print-stage-all-choice) input[type="checkbox"]') || [])];
}

function selectedPrintListIds() {
  return selectedPrintStageInputs().filter((input) => input.checked).map((input) => input.value);
}

function updatePrintStageSelectState() {
  if (!els.printOptionsStages) return;

  const stageInputs = selectedPrintStageInputs();
  const checkedInputs = stageInputs.filter((input) => input.checked);
  const allInput = els.printOptionsStages.querySelector("[data-print-stage-select-all]");

  if (allInput) {
    allInput.checked = stageInputs.length > 0 && checkedInputs.length === stageInputs.length;
    allInput.indeterminate = checkedInputs.length > 0 && checkedInputs.length < stageInputs.length;
  }
}

function printGlassCategory(label) {
  const text = String(label || "").toLowerCase();

  if (/mirror|mirr|\bmir\b/.test(text)) return "Mirror";
  if (/tempered|temp\b|shower/.test(text)) return "Tempered";
  if (/annealed|anneal|\bann\b|plate|float/.test(text)) return "Annealed";

  return "Other";
}

function printGlassCategorySort(category) {
  return { Mirror: 1, Annealed: 2, Tempered: 3, Other: 4 }[category] || 9;
}

function selectedPrintGlassInputs() {
  return [...(els.printOptionsGlassType?.querySelectorAll('.print-glass-choice:not(.print-glass-all-choice) input[type="checkbox"]') || [])];
}

function updatePrintGlassSelectState() {
  if (!els.printOptionsGlassType) return;

  const glassInputs = selectedPrintGlassInputs();
  const checkedInputs = glassInputs.filter((input) => input.checked);
  const allInput = els.printOptionsGlassType.querySelector("[data-print-glass-select-all]");

  if (allInput) {
    allInput.checked = glassInputs.length > 0 && checkedInputs.length === glassInputs.length;
    allInput.indeterminate = checkedInputs.length > 0 && checkedInputs.length < glassInputs.length;
  }

  els.printOptionsGlassType.querySelectorAll("[data-print-glass-category]").forEach((categoryInput) => {
    const category = categoryInput.dataset.printGlassCategory || "";
    const categoryInputs = glassInputs.filter((input) => input.dataset.printGlassCategory === category);
    const checkedCategoryInputs = categoryInputs.filter((input) => input.checked);

    categoryInput.checked = categoryInputs.length > 0 && checkedCategoryInputs.length === categoryInputs.length;
    categoryInput.indeterminate = checkedCategoryInputs.length > 0 && checkedCategoryInputs.length < categoryInputs.length;
  });
}

async function ensurePrintListDetails(listIds) {
  if (!state.backend) return;

  const wanted = new Set(listIds);
  const listsToLoad = state.lists.filter((list) => {
    if (!wanted.has(list.id)) return false;
    if (list._printItemsLoaded) return false;
    return !Array.isArray(list.items) || !list.items.length;
  });

  if (!listsToLoad.length) return;

  await Promise.all(
    listsToLoad.map(async (list) => {
      const payload = await fetchJson(`/api/delivery-lists/${encodeURIComponent(list.id)}`);
      const items = cloneItems(payload.items || []);

      Object.assign(list, {
        items,
        itemCount: items.length || list.itemCount || 0,
        totalQty: items.length ? pieceCount(items) : list.totalQty,
        scannedQty: items.length ? items.reduce((sum, item) => sum + itemScannedPieceQty(item), 0) : list.scannedQty,
        _printItemsLoaded: true,
      });
    }),
  );
}

function printListIsFullCoverage(list) {
  const category = stageCategory(list);
  return category === "staged" || category === "outbound";
}

function printCountSourceLists(listIds) {
  const wanted = new Set(listIds);
  const selectedLists = state.lists.filter((list) => wanted.has(list.id));
  const fullCoverageLists = selectedLists
    .filter(printListIsFullCoverage)
    .sort((a, b) => stageSort(a) - stageSort(b));

  if (fullCoverageLists.length) {
    return [fullCoverageLists[0]];
  }

  return selectedLists;
}

function printItemsForCountList(list) {
  if (Array.isArray(list?.items) && list.items.length) {
    return list.items;
  }

  if (list?.id && list.id === state.activeListId) {
    return state.items;
  }

  return [];
}

function printGlassEntriesForLists(listIds) {
  const entries = new Map();
  const sourceLists = printCountSourceLists(listIds);

  const addEntry = (label, qty = 0) => {
    const cleanLabel = String(label || "").trim();

    if (!cleanLabel) return;

    const key = cleanLabel.toLowerCase();
    const existing = entries.get(key) || {
      label: cleanLabel,
      qty: 0,
      category: printGlassCategory(cleanLabel),
    };

    existing.qty += Math.max(Number(qty || 0), 0);
    entries.set(key, existing);
  };

  for (const list of sourceLists) {
    const items = printItemsForCountList(list);

    if (items.length) {
      for (const item of items) {
        addEntry(glassTypeLabel(item), itemPieceQty(item));
      }
    } else {
      for (const label of list.glassTypes || []) {
        addEntry(label, 0);
      }
    }
  }

  return [...entries.values()].sort((a, b) => {
    const categoryDiff = printGlassCategorySort(a.category) - printGlassCategorySort(b.category);
    if (categoryDiff) return categoryDiff;

    const qtyDiff = Number(b.qty || 0) - Number(a.qty || 0);
    if (qtyDiff) return qtyDiff;

    return a.label.localeCompare(b.label);
  });
}

function availableGlassTypesForLists(listIds) {
  return printGlassEntriesForLists(listIds).map((entry) => entry.label);
}

function ensurePrintGlassFieldWrapper() {
  if (!els.printOptionsGlassType) return null;

  const glassField = els.printOptionsGlassType.closest("label");

  if (!glassField) {
    return els.printOptionsGlassType.closest(".print-glass-field");
  }

  const wrapper = document.createElement("div");
  wrapper.className = `${glassField.className} print-glass-field`.trim();

  while (glassField.firstChild) {
    wrapper.appendChild(glassField.firstChild);
  }

  glassField.replaceWith(wrapper);
  return wrapper;
}

async function renderPrintGlassTypes() {
  if (!els.printOptionsGlassType) return;

  ensurePrintGlassFieldWrapper();

  const listIds = selectedPrintListIds();
  const renderToken = Symbol("print-glass-render");
  state.printGlassRenderToken = renderToken;

  const countSourceListIds = printCountSourceLists(listIds).map((list) => list.id);
  const detailIds = [...new Set([...listIds, ...countSourceListIds])];
  const needsDetails = state.backend && detailIds.some((listId) => {
    const list = state.lists.find((item) => item.id === listId);
    return list && !list._printItemsLoaded && (!Array.isArray(list.items) || !list.items.length);
  });

  if (needsDetails) {
    els.printOptionsGlassType.innerHTML = `<div class="admin-empty">Loading glass types...</div>`;

    try {
      await ensurePrintListDetails(detailIds);
    } catch (error) {
      els.printOptionsGlassType.innerHTML = `<div class="admin-empty review">Could not load glass type quantities. ${escapeHtml(error.message)}</div>`;
      return;
    }

    if (state.printGlassRenderToken === renderToken) {
      await renderPrintGlassTypes();
    }

    return;
  }

  const previousGroups = [...els.printOptionsGlassType.querySelectorAll(".print-glass-group[data-print-glass-group]")];
  const previousOpenCategories = new Set(previousGroups.filter((group) => group.open).map((group) => group.dataset.printGlassGroup));
  const hadPreviousGroups = previousGroups.length > 0;
  const currentInputs = selectedPrintGlassInputs();
  const current = new Set(currentInputs.filter((input) => input.checked).map((input) => input.value).filter(Boolean));
  const hadPrevious = currentInputs.length > 0;
  const entries = printGlassEntriesForLists(listIds);
  const groups = new Map();
  const checkedForEntry = (entry) => (hadPrevious ? current.has(entry.label) : !/mirror/i.test(entry.label));

  for (const entry of entries) {
    if (!groups.has(entry.category)) {
      groups.set(entry.category, []);
    }

    groups.get(entry.category).push(entry);
  }

  const selectedCount = entries.filter(checkedForEntry).length;
  const totalQty = entries.reduce((sum, entry) => sum + Number(entry.qty || 0), 0);

  els.printOptionsGlassType.innerHTML = entries.length
    ? `
        <div class="print-glass-toolbar">
          <span class="print-glass-choice print-glass-all-choice" data-print-glass-all-toggle>
            <input type="checkbox" data-print-glass-select-all ${selectedCount === entries.length ? "checked" : ""}>
            <span>All Glass Types</span>
            <small>${escapeHtml(selectedCount)} / ${escapeHtml(entries.length)} selected | ${escapeHtml(totalQty)} pcs</small>
          </span>
        </div>

        ${[...groups.entries()]
          .map(([category, groupEntries]) => {
            const groupQty = groupEntries.reduce((sum, entry) => sum + Number(entry.qty || 0), 0);
            const checkedGroupEntries = groupEntries.filter(checkedForEntry);
            const groupOpen = hadPreviousGroups ? previousOpenCategories.has(category) : false;

            return `
              <details
                class="print-glass-group print-glass-group-${escapeHtml(slugify(category))}"
                data-print-glass-group="${escapeHtml(category)}"
                ${groupOpen ? "open" : ""}
              >
                <summary>
                  <span class="print-glass-group-main">
                    <input
                      type="checkbox"
                      data-print-glass-category="${escapeHtml(category)}"
                      aria-label="Select all ${escapeHtml(category)} glass types"
                      ${checkedGroupEntries.length === groupEntries.length ? "checked" : ""}
                    >
                    <strong>${escapeHtml(category)}</strong>
                    <small>${escapeHtml(checkedGroupEntries.length)} / ${escapeHtml(groupEntries.length)} selected | ${escapeHtml(groupQty)} pcs</small>
                  </span>
                  <span class="print-glass-collapse-label">Expand / collapse</span>
                </summary>

                <div class="print-glass-group-options">
                  ${groupEntries
                    .map((entry) => {
                      const checked = checkedForEntry(entry);

                      return `
                        <span class="print-glass-choice">
                          <input
                            type="checkbox"
                            value="${escapeHtml(entry.label)}"
                            data-print-glass-category="${escapeHtml(category)}"
                            aria-label="Select ${escapeHtml(entry.label)}"
                            ${checked ? "checked" : ""}
                          >
                          <span title="${escapeHtml(entry.label)}">${escapeHtml(entry.label)}</span>
                          <small>${escapeHtml(entry.qty || 0)}</small>
                        </span>
                      `;
                    })
                    .join("")}
                </div>
              </details>
            `;
          })
          .join("")}
      `
    : `<div class="admin-empty">No glass types found for the selected stages.</div>`;

  updatePrintGlassSelectState();

  els.printOptionsGlassType.onclick = (event) => {
    const targetInput = event.target.closest('input[type="checkbox"]');

    if (targetInput && els.printOptionsGlassType.contains(targetInput)) {
      event.stopPropagation();

      window.setTimeout(() => {
        if (targetInput.matches("[data-print-glass-select-all]")) {
          selectedPrintGlassInputs().forEach((glassInput) => {
            glassInput.checked = targetInput.checked;
          });
        }

        if (targetInput.matches("[data-print-glass-category]")) {
          const category = targetInput.dataset.printGlassCategory || "";

          selectedPrintGlassInputs()
            .filter((input) => input.dataset.printGlassCategory === category)
            .forEach((input) => {
              input.checked = targetInput.checked;
            });
        }

        updatePrintGlassSelectState();
      }, 0);

      return;
    }

    const allToggle = event.target.closest("[data-print-glass-all-toggle]");

    if (allToggle && els.printOptionsGlassType.contains(allToggle)) {
      event.preventDefault();
      event.stopPropagation();

      const glassInputs = selectedPrintGlassInputs();
      const nextChecked = !glassInputs.length || glassInputs.some((input) => !input.checked);

      glassInputs.forEach((glassInput) => {
        glassInput.checked = nextChecked;
      });

      updatePrintGlassSelectState();
      return;
    }

    const choice = event.target.closest(".print-glass-choice:not(.print-glass-all-choice)");

    if (choice && els.printOptionsGlassType.contains(choice)) {
      event.preventDefault();
      event.stopPropagation();

      const input = choice.querySelector('input[type="checkbox"]');

      if (!input) return;

      input.checked = !input.checked;
      updatePrintGlassSelectState();
    }
  };
}

function printStageOptionLabel(list) {
  const category = stageCategory(list);

  if (category === "outbound") return "Outbound Airport";
  if (category === "received") return "Inbound IT";
  if (category === "greenville") return "BFS Greenville";
  if (category === "pickup") return "CPU";
  if (category === "dtc") return "DTC";

  return "Staging Airport";
}

function renderPrintOptionStages() {
  if (!els.printOptionsStages || !els.printOptionsDate) return;

  const date = els.printOptionsDate.value || selectedDeliveryDate() || dashboardDateKey();
  const lists = state.lists.filter((list) => list.deliveryDate === date).sort((a, b) => stageSort(a) - stageSort(b));
  const contextIds = new Set(state.printContext?.listIds || []);
  const hasContextIds = contextIds.size > 0;
  const checkedCount = lists.filter((list) => (hasContextIds ? contextIds.has(list.id) : false)).length;
  const fullCoverageList = lists.find(printListIsFullCoverage);
  const listQty = fullCoverageList?.totalQty || lists.reduce((maxQty, list) => Math.max(maxQty, Number(list.totalQty || 0)), 0);

  els.printOptionsStages.innerHTML = `
    <label class="print-stage-choice print-stage-all-choice">
      <input type="checkbox" data-print-stage-select-all ${lists.length && checkedCount === lists.length ? "checked" : ""}>
      <span>All Stages <small>${escapeHtml(lists.length)} stage${lists.length === 1 ? "" : "s"}${listQty ? ` | ${escapeHtml(listQty)} pcs` : ""}</small></span>
    </label>
    ${lists
      .map((list) => {
        const checked = hasContextIds ? contextIds.has(list.id) : false;

        return `
          <label class="print-stage-choice print-stage-${escapeHtml(stageCategory(list))}">
            <input type="checkbox" value="${escapeHtml(list.id)}" ${checked ? "checked" : ""}>
            <span>${escapeHtml(printStageOptionLabel(list))} <small>${escapeHtml(list.scannedQty || 0)} / ${escapeHtml(list.totalQty || 0)}</small></span>
          </label>
        `;
      })
      .join("")}
  `;

  updatePrintStageSelectState();
  void renderPrintGlassTypes();
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
  if (els.printUpdatedOnly) {
    els.printUpdatedOnly.checked = Boolean(context.updatedOnly);
  }
  if (els.printCustomerFilter) els.printCustomerFilter.value = "";
  if (els.printOrderFilter) els.printOrderFilter.value = "";
  renderPrintOptionStages();
  if (els.printOptionsBackdrop) els.printOptionsBackdrop.hidden = false;
  if (els.printOptionsPanel) els.printOptionsPanel.hidden = false;
  updateModalScrollLock();
}

function closePrintOptions() {
  if (els.printOptionsBackdrop) els.printOptionsBackdrop.hidden = true;
  if (els.printOptionsPanel) els.printOptionsPanel.hidden = true;
  updateModalScrollLock();
}

function submitPrintOptions() {
  let listIds = state.printContext?.fixedListIds ? [...(state.printContext.listIds || [])] : selectedPrintListIds();
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
    glassType: [...(els.printOptionsGlassType?.querySelectorAll('.print-glass-choice:not(.print-glass-all-choice) input[type="checkbox"]:checked') || [])].map((input) => input.value.trim()).filter(Boolean).join(","),
    mirrorMode: "include",
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
  const { dateFrom, dateTo } = currentImportDateWindow();

  showImportStatusLoading("Importing Temp folder...", `Checking delivery dates from ${formatDisplayDate(dateFrom)} forward.`);
  await waitForNextPaint();

  const result = await fetchJson("/api/import/folder", {
    method: "POST",
    body: JSON.stringify({ ...requestContext(), sourceFolder, dateFrom, dateTo }),
  });
  state.lists = result.lists || state.lists;
  if (result.activeListId) await activateList(result.activeListId, false);
  renderHome();
  await refreshAdminPage();
  const imported = result.importedFiles?.length || 0;
  const updated = result.updatedFiles?.length || 0;
  const skipped = result.skippedFiles?.length || 0;
  const ignored = result.ignoredFiles?.length || 0;
  const failed = result.failedFiles?.length || 0;
  const checked = result.checkedFiles ?? result.scannedFiles ?? imported + updated + skipped + failed;
  const total = result.totalFolderFiles ?? checked + ignored;
  if (els.importPreviewBox) {
    els.importPreviewBox.hidden = false;
    els.importPreviewBox.classList.remove("loading");
    els.importPreviewBox.classList.add("import-status-compact");
    els.importPreviewBox.classList.toggle("success", !failed);
    els.importPreviewBox.classList.toggle("review", Boolean(failed));

    const noUpdates = !imported && !updated && skipped && !failed;
    const windowText = `Checked ${checked} file${checked === 1 ? "" : "s"} in the active import window. ${ignored ? `Skipped ${ignored} older file${ignored === 1 ? "" : "s"} outside the date window. ` : ""}${total ? `Folder total: ${total}.` : ""}`;

    els.importPreviewBox.innerHTML = failed
      ? `
        <strong>Import completed with issues.</strong>
        <span>${imported} new, ${updated} updated, ${skipped} unchanged, ${failed} failed.</span>
        <small>${escapeHtml(windowText)}</small>
        ${result.failedFiles?.length ? `<small>${escapeHtml(result.failedFiles.map((file) => `${file.fileName}: ${(file.errors || []).join("; ")}`).join(" | "))}</small>` : ""}
      `
      : noUpdates
        ? `
          <strong>No updates found.</strong>
          <span>${skipped} delivery list file${skipped === 1 ? "" : "s"} checked. Existing New/Updated markers were refreshed where applicable.</span>
          <small>${escapeHtml(windowText)}</small>
        `
        : `
          <strong>Import complete.</strong>
          <span>${imported} new, ${updated} updated, ${skipped} unchanged.</span>
          <small>${escapeHtml(windowText)}</small>
        `;
  }
}

async function refreshAdminPage() {
  if (!state.backend) return;
  const requests = [];
  requests.push(hasPermission("view_admin") ? fetchJson("/api/admin/summary") : Promise.resolve(null));
  requests.push(hasPermission("manage_users") ? fetchJson("/api/admin/users") : Promise.resolve(null));
  requests.push(hasPermission("view_active_sessions") ? fetchJson("/api/admin/sessions") : Promise.resolve(null));
  requests.push(hasPermission("manage_customer_route_rules") ? fetchJson("/api/admin/customer-route-rules") : Promise.resolve(null));
  requests.push(hasPermission("manage_roles") ? fetchJson("/api/admin/roles") : Promise.resolve(null));
  const [summary, users, sessions, customerRules, roles] = await Promise.all(requests);
  if (summary) state.adminSummary = summary;
  if (summary && els.adminSummary) {
    els.adminSummary.innerHTML = [
      miniStat("Active Delivery Lists", summary.activeDeliveryDates ?? summary.activeDeliveryLists ?? 0, `${summary.activeDeliveryLists ?? 0} active stages`),
      miniStat("Scans Today", summary.scanEventsToday ?? summary.scanEvents ?? 0),
      miniStat("Line Items", summary.lineItems ?? 0),
      miniStat("Active Users", summary.activeUsers ?? 0),
    ].join("");
  }
  if (els.adminLastUpdated) els.adminLastUpdated.textContent = `Last updated: ${new Date().toLocaleString()}`;
  if (summary) {
    state.adminRecentImports = summary.recentImports || [];
    renderImportHistory(summary.recentImports || []);
    renderAdminDeleteControls();
    renderAdminResetControls();
    if (els.tempFolderInput && !els.tempFolderInput.value && summary.tempDeliveryListsDir) els.tempFolderInput.value = summary.tempDeliveryListsDir;
  }
  state.adminUsers = users?.users || [];
  state.activeSessions = sessions?.sessions || [];
  state.adminCustomerRouteRules = customerRules?.rules || [];
  state.adminRoles = roles?.roles || state.adminRoles || [];
  state.allPermissions = roles?.permissions || state.allPermissions || [];
  renderAdminUsers();
  renderAdminStations();
  renderManualEditStageOptions();
  renderCustomerRouteRules();
  renderActiveSessions();
}

function deliveryListAdminRows(lists = state.lists, limit = 7, editable = false) {
  const rows = lists
    .slice()
    .sort((a, b) => String(b.deliveryDate || "").localeCompare(String(a.deliveryDate || "")) || stageSort(a) - stageSort(b));

  const limitedRows = limit ? rows.slice(0, limit) : rows;

  if (!limitedRows.length) {
    return `<div class="admin-empty">No delivery lists loaded.</div>`;
  }

  const groups = listsByDeliveryDate(limitedRows);

  return `
    <div class="admin-delivery-edit-list">
      ${groups
        .map((group, index) => {
          const totalQty = group.lists.reduce((sum, list) => sum + Number(list.totalQty ?? list.itemCount ?? 0), 0);
          const scannedQty = group.lists.reduce((sum, list) => sum + Number(list.scannedQty || 0), 0);
          const percent = totalQty ? Math.round((scannedQty / totalQty) * 100) : 0;

          return `
            <details class="admin-delivery-date-group" ${index === 0 ? "open" : ""}>
              <summary class="admin-delivery-date-summary">
                <span class="admin-delivery-date-main">
                  <strong>${escapeHtml(formatDisplayDate(group.date))}</strong>
                  <small>${escapeHtml(group.lists.length)} stage${group.lists.length === 1 ? "" : "s"} | ${escapeHtml(scannedQty)} / ${escapeHtml(totalQty)} pcs | ${escapeHtml(percent)}%</small>
                </span>

                <span class="admin-delivery-date-progress">
                  <span class="progress-line"><i style="width: ${Math.min(percent, 100)}%"></i></span>
                </span>

                ${
                  editable
                    ? `<span class="admin-date-action-row">
                        <button
                          type="button"
                          class="icon-only icon-reset"
                          data-admin-date-reset="${escapeHtml(group.date)}"
                          title="Reset all stages for ${escapeHtml(formatDisplayDate(group.date))}"
                          aria-label="Reset all stages for ${escapeHtml(formatDisplayDate(group.date))}"
                        ></button>
                        <button
                          type="button"
                          class="icon-only icon-trash danger"
                          data-admin-date-delete="${escapeHtml(group.date)}"
                          title="Delete all stages for ${escapeHtml(formatDisplayDate(group.date))}"
                          aria-label="Delete all stages for ${escapeHtml(formatDisplayDate(group.date))}"
                        ></button>
                      </span>`
                    : ""
                }
              </summary>

              <div class="admin-delivery-stage-list">
                ${group.lists
                  .map((list) => {
                    const listTotalQty = Number(list.totalQty ?? list.itemCount ?? 0);
                    const listScannedQty = Number(list.scannedQty || 0);
                    const listPercent = listTotalQty ? Math.round((listScannedQty / listTotalQty) * 100) : 0;

                    return `
                      <article class="admin-delivery-stage-row">
                        <span class="admin-delivery-stage-main">
                          <strong>${escapeHtml(list.stage || list.label || list.id)}</strong>
                          <small>${escapeHtml(list.scanner || "")}</small>
                        </span>

                        <span class="admin-delivery-stage-qty">
                          ${escapeHtml(listScannedQty)} / ${escapeHtml(listTotalQty)} pcs
                          <span class="progress-line"><i style="width: ${Math.min(listPercent, 100)}%"></i></span>
                        </span>

                        ${
                          editable
                            ? `<span class="admin-action-cell">
                                <button
                                  type="button"
                                  class="icon-only icon-pencil"
                                  data-admin-list-edit="${escapeHtml(list.id)}"
                                  title="Edit ${escapeHtml(list.label || list.id)}"
                                  aria-label="Edit ${escapeHtml(list.label || list.id)}"
                                ></button>
                                <button
                                  type="button"
                                  class="icon-only icon-reset"
                                  data-admin-list-reset="${escapeHtml(list.id)}"
                                  title="Reset scans for ${escapeHtml(list.label || list.id)}"
                                  aria-label="Reset scans for ${escapeHtml(list.label || list.id)}"
                                ></button>
                                <button
                                  type="button"
                                  class="icon-only icon-trash danger"
                                  data-admin-list-delete="${escapeHtml(list.id)}"
                                  title="Delete ${escapeHtml(list.label || list.id)}"
                                  aria-label="Delete ${escapeHtml(list.label || list.id)}"
                                ></button>
                              </span>`
                            : ""
                        }
                      </article>
                    `;
                  })
                  .join("")}
              </div>
            </details>
          `;
        })
        .join("")}
    </div>
  `;
}

async function searchAdminDeliveryLists(query) {
  const clean = String(query || "").trim();
  const local = state.lists.filter((list) =>
    [list.label, list.deliveryDate, formatDisplayDate(list.deliveryDate), list.stage, list.scanner]
      .some((value) => String(value || "").toLowerCase().includes(clean.toLowerCase())),
  );
  if (!state.backend || clean.length < 2) return local;
  try {
    const payload = await fetchJson(`/api/admin/line-items/search?q=${encodeURIComponent(clean)}`);
    const matchingIds = new Set((payload.results || []).map((item) => item.listId).filter(Boolean));
    const merged = [...local];
    for (const list of state.lists) {
      if (matchingIds.has(list.id) && !merged.some((existing) => existing.id === list.id)) merged.push(list);
    }
    return merged;
  } catch (error) {
    console.warn("Admin delivery-list search failed", error);
    return local;
  }
}

function activeRecentImports(imports = state.adminRecentImports || []) {
  const activeListIds = new Set(state.lists.map((list) => list.id));

  return imports
    .map((entry) => {
      const listIds = Array.isArray(entry.listIds)
        ? entry.listIds.filter((listId) => activeListIds.has(listId))
        : [];

      const stageSummaries = Array.isArray(entry.stageSummaries)
        ? entry.stageSummaries.filter((row) => row.listId && activeListIds.has(row.listId))
        : [];

      return {
        ...entry,
        listIds,
        stageSummaries,
      };
    })
    .filter((entry) => {
      const hasActiveListIds = Array.isArray(entry.listIds) && entry.listIds.length > 0;
      const hasActiveStageSummaries = Array.isArray(entry.stageSummaries) && entry.stageSummaries.length > 0;

      return hasActiveListIds || hasActiveStageSummaries;
    });
}

function renderAdminDeliveryLists() {
  if (!els.adminDeliveryLists) return;
  els.adminDeliveryLists.innerHTML = importHistoryRows(activeRecentImports());
}

function openAdminModal(kind) {
  if (kind === "roles") {
  resetRolePermissionUiSession();
  }
  if (!els.adminModal || !els.adminModalBody || !els.adminModalTitle) return;
  const titleMap = {
    deliveryLists: "All Delivery Lists",
    deliveryActions: "Delivery List Actions",
    users: "All Users",
    roles: "Edit Role Permissions",
    sessions: "Active Sessions",
    stations: "Stations",
    customerRoutes: "Edit Customer Routes",
    manualEdit: "Manual Delivery List Edit",
    lookups: "Lookup Manager",
    rackForm: "Rack",
    rackSetForm: "Rack Set",
    racks: "Edit Racks",
    recentScans: "All Scans",
  };
  els.adminModalTitle.textContent = titleMap[kind] || "Admin";
  els.adminModalBody.innerHTML = adminModalContent(kind);
  els.adminModal.hidden = false;
  if (els.adminModalBackdrop) els.adminModalBackdrop.hidden = false;
  updateModalScrollLock();
  if (kind === "roles" && (!state.adminRoles.length || !state.allPermissions.length) && hasPermission("manage_roles")) {
    fetchJson("/api/admin/roles")
      .then((payload) => {
        state.adminRoles = payload.roles || [];
        state.allPermissions = payload.permissions || [];
        if (!els.adminModal.hidden) els.adminModalBody.innerHTML = adminModalContent("roles");
      })
      .catch((error) => showInlineError(error.message, true));
  }
}

function closeAdminModal() {
  if (state.manualEditDirty && !window.confirm("You have unsaved manual delivery-list edits. Close without saving?")) return;

  if (!els.adminModal?.hidden && els.adminModalBody?.querySelector(".role-permission-editor")) {
    resetRolePermissionUiSession();
  }

  state.manualEditDirty = false;

  if (els.adminModal) els.adminModal.hidden = true;
  if (els.adminModalBackdrop) els.adminModalBackdrop.hidden = true;
  updateModalScrollLock();
}

function adminModalContent(kind) {
  if (kind === "deliveryLists") {
    return `
      <label class="search-box admin-modal-search">
        <span class="search-icon"></span>
        <input id="adminDeliveryListModalSearch" type="search" autocomplete="off" placeholder="Search date, Job Nr., order number, stage...">
      </label>
      <div class="admin-table" id="adminDeliveryListModalResults">${deliveryListAdminRows(state.lists, state.lists.length || 1, true)}</div>
    `;
  }
  if (kind === "deliveryActions") {
    return `
      <label class="search-box admin-modal-search">
        <span class="search-icon"></span>
        <input id="adminDeliveryListModalSearch" type="search" autocomplete="off" placeholder="Search date, Job Nr., order number, stage...">
      </label>
      <div class="admin-table" id="adminDeliveryListModalResults">${deliveryListAdminRows(state.lists, state.lists.length || 1, true)}</div>
    `;
  }
  if (kind === "users") {
    return `
      <section class="users-modal-shell">
        <form id="createUserFormModal" class="admin-form admin-modal-create-user users-create-card">
          <label>
            <span>Username</span>
            <input id="newUserNameModal" type="text" autocomplete="off" placeholder="Enter username">
          </label>

          <label>
            <span>Display Name</span>
            <input id="newUserDisplayModal" type="text" autocomplete="off" placeholder="Enter display name">
          </label>

          <label>
            <span>Password</span>
            <input id="newUserPasswordModal" type="password" autocomplete="new-password" placeholder="Enter password">
          </label>

          <label>
            <span>Role</span>
            <select id="newUserRoleModal">
              ${ROLE_OPTIONS.map((role) => `<option>${escapeHtml(role)}</option>`).join("")}
            </select>
          </label>

          <label>
            <span>Station</span>
            <select id="newUserStationModal">
              <option value="">No assigned station</option>
              ${state.stations.map((station) => `<option value="${escapeHtml(station)}">${escapeHtml(station)}</option>`).join("")}
            </select>
          </label>

          <button type="submit" class="users-add-button">
            <span class="user-action-icon icon-user-add" aria-hidden="true"></span>
            <strong>Add user</strong>
          </button>
        </form>

        <div class="users-table-wrap">
          ${renderAdminUsersTable(true, state.adminUsers.length || 1)}
        </div>
      </section>
    `;
  }
  if (kind === "roles") {
    return rolePermissionsModalHtml();
  }
  if (kind === "sessions") {
    return `<div class="compact-list modal-list">${state.activeSessions.length ? state.activeSessions.map((session) => `<div><strong>${escapeHtml(session.displayName)}</strong><span>${escapeHtml(session.role || "")} - ${escapeHtml(session.station || "No station")}</span><small>Last seen ${escapeHtml(session.lastSeenAt)}</small></div>`).join("") : `<div><strong>No active sessions</strong><span>Users appear here after login.</span></div>`}</div>`;
  }
  if (kind === "stations") {
    return `
      <div class="station-add-row">
        <input id="newStationInputModal" type="text" autocomplete="off" placeholder="New station">
        <button id="addStationBtnModal" type="button">Add</button>
      </div>
      <div class="compact-list modal-list">${renderAdminStationsList(true, state.stations.length || 1)}</div>
    `;
  }
  if (kind === "customerRoutes") {
    return customerRouteRulesModalHtml();
  }
  if (kind === "manualEdit") {
    return manualEditModalHtml();
  }
  if (kind === "lookups") {
    return lookupManagerModalHtml();
  }
  if (kind === "recentScans") {
    return recentScansModalHtml();
  }
  if (kind === "racks") {
    return rackManagerModalHtml();
  }
  if (kind === "rackForm") {
    return rackFormModalHtml();
  }
  if (kind === "rackSetForm") {
    return rackSetFormModalHtml();
  }
  return `<div class="admin-empty">Choose a dashboard section to view details.</div>`;
}

function lookupTypeMeta(title) {
  const clean = String(title || "").toLowerCase();

  if (clean.includes("product")) {
    return {
      className: "products",
      label: "Product names",
      description: "Glass/product descriptions used in manual delivery-list edits.",
    };
  }

  if (clean.includes("route")) {
    return {
      className: "routes",
      label: "Route codes",
      description: "Routing values such as CPU, DTC, GNV, or custom customer routes.",
    };
  }

  return {
    className: "processes",
    label: "Process states",
    description: "Status values such as New, Updated, Rush, Remake, and SDI.",
  };
}

function lookupListHtml(title, items = []) {
  const meta = lookupTypeMeta(title);

  return `
    <section class="lookup-manager-list ${escapeHtml(meta.className)}">
      <header>
        <span class="lookup-type-icon" aria-hidden="true"></span>
        <div>
          <h3>${escapeHtml(meta.label)}</h3>
          <p>${escapeHtml(meta.description)}</p>
        </div>
        <strong>${escapeHtml(items.length)}</strong>
      </header>

      <div class="lookup-row-list">
        ${
          items.length
            ? items
                .map((item) => `
                  <article class="lookup-row">
                    <div class="lookup-row-main">
                      <strong>${escapeHtml(item.label || item.value)}</strong>
                      <span>${escapeHtml(item.value || "")}${item.category ? ` | ${escapeHtml(item.category)}` : ""}</span>
                      ${item.matchTerms ? `<small>Matches: ${escapeHtml(item.matchTerms)}</small>` : ""}
                    </div>
                    <em>${escapeHtml(item.source || "manual")}</em>
                  </article>
                `)
                .join("")
            : `<div class="lookup-empty-state"><strong>No ${escapeHtml(title.toLowerCase())} yet</strong><span>Add one above to make manual edits faster and cleaner.</span></div>`
        }
      </div>
    </section>
  `;
}

function lookupManagerModalHtml() {
  const lookups = state.manualEditLookups || { products: [], routes: [], processes: [] };
  const productCount = (lookups.products || []).length;
  const routeCount = (lookups.routes || []).length;
  const processCount = (lookups.processes || []).length;

  return `
    <div class="lookup-manager-shell lookup-manager-modern">
      <section class="lookup-manager-hero">
        <div>
          <span class="lookup-hero-label">Lookup Manager</span>
          <strong>Edit dropdown choices used by manual list editing</strong>
          <span>Add clean product names, route codes, and process states so the manual editor stays consistent.</span>
        </div>
        <div class="lookup-manager-kpis">
          ${miniStat("Products", productCount)}
          ${miniStat("Routes", routeCount)}
          ${miniStat("Processes", processCount)}
        </div>
      </section>

      <section class="lookup-add-card">
        <div class="lookup-add-copy">
          <strong>Add lookup value</strong>
          <span>Use Value for the actual saved code. Use Display label for the cleaner name people see.</span>
        </div>

        <form id="manualLookupForm" class="lookup-manager-form">
          <label>
            <span>Lookup type</span>
            <select id="lookupTypeInput">
              <option value="product">Product</option>
              <option value="route">Route</option>
              <option value="process">Process</option>
            </select>
          </label>
          <label>
            <span>Value / code</span>
            <input id="lookupValueInput" type="text" autocomplete="off" placeholder="CPU, 1/4 Mirror, Rush">
          </label>
          <label>
            <span>Display label</span>
            <input id="lookupLabelInput" type="text" autocomplete="off" placeholder="Customer Pickup">
          </label>
          <label>
            <span>Category</span>
            <input id="lookupCategoryInput" type="text" autocomplete="off" placeholder="Pickup, delivery, branch">
          </label>
          <label class="wide">
            <span>Match terms</span>
            <input id="lookupMatchTermsInput" type="text" autocomplete="off" placeholder="CPU-Air, customer pickup, will call">
          </label>
          <button type="submit">Add Lookup</button>
        </form>
      </section>

      <div class="lookup-manager-grid">
        ${lookupListHtml("Products", lookups.products || [])}
        ${lookupListHtml("Routes", lookups.routes || [])}
        ${lookupListHtml("Processes", lookups.processes || [])}
      </div>
    </div>
  `;
}

function rackManagerModalHtml() {
  const groups = new Map();
  for (const rack of state.racks || []) {
    const label = rackGroupLabel(rack);
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label).push(rack);
  }

  const sortedGroups = [...groups.entries()].sort(([a], [b]) => {
    if (a === "Truck") return 1;
    if (b === "Truck") return -1;
    const order = { Steel: 1, Wood: 2, Coral: 3 };
    return (order[a] || 50) - (order[b] || 50) || a.localeCompare(b);
  });

  const selectedRack = selectedRackManagerRack(state.rackManagerSelectedCode) || state.racks[0] || null;
  state.rackManagerSelectedCode = selectedRack?.code || "";

  return `
    <div class="rack-manager-shell">
      <div class="rack-manager-topbar">
        <div>
          <strong>Rack Manager</strong>
          <span>Edit individual racks, add rack sets, delete empty racks, or delete empty rack sets.</span>
        </div>
        <div class="rack-manager-actions">
          <button type="button" data-rack-manager-new-rack>Create Rack</button>
          <button type="button" data-rack-manager-new-set>Create Rack Set</button>
        </div>
      </div>

      <form id="rackManagerQuickEditForm" class="rack-manager-quick-edit">
        <div class="rack-manager-quick-copy">
          <strong>Quick rack edit</strong>
          <span>Select a rack, update its display name or set type, then save it without leaving this manager.</span>
        </div>
        <label>
          <span>Rack</span>
          <select id="rackManagerQuickRackSelect">
            ${(state.racks || [])
              .slice()
              .sort((a, b) => Number(a.sortOrder || 0) - Number(b.sortOrder || 0) || String(a.code).localeCompare(String(b.code), undefined, { numeric: true }))
              .map((rack) => `<option value="${escapeHtml(rack.code)}" ${selectedRack?.code === rack.code ? "selected" : ""}>${escapeHtml(rack.code === "T" ? "Truck / No Rack" : rack.code)} - ${escapeHtml(rack.name || rack.type || "")}</option>`)
              .join("")}
          </select>
        </label>
        <label>
          <span>Name</span>
          <input id="rackManagerQuickName" type="text" autocomplete="off" value="${escapeHtml(selectedRack?.name || selectedRack?.type || selectedRack?.code || "")}" placeholder="Rack display name">
        </label>
        <label>
          <span>Rack set / type</span>
          <input id="rackManagerQuickType" type="text" list="rackManagerRackTypes" autocomplete="off" value="${escapeHtml(selectedRack?.type || "Steel")}" placeholder="Steel, Wood, Coral, Truck">
          <datalist id="rackManagerRackTypes">
            ${["Steel", "Wood", "Coral", "Truck", "Aluminum", "Other"].map((type) => `<option value="${escapeHtml(type)}"></option>`).join("")}
          </datalist>
        </label>
        <button type="submit" class="rack-manager-save-button">Save Rack</button>
      </form>

      <div class="rack-manager-grid">
        ${
          sortedGroups.length
            ? sortedGroups
                .map(([label, racks]) => {
                  const totalQty = racks.reduce((sum, rack) => sum + Number(rack.qty || 0), 0);
                  const deletableCount = racks.filter((rack) => rack.code !== "T" && Number(rack.qty || 0) === 0).length;

                  return `
                    <section class="rack-manager-group">
                      <header>
                        <div>
                          <h3>${escapeHtml(label)}</h3>
                          <span>${escapeHtml(racks.length)} rack${racks.length === 1 ? "" : "s"} | ${escapeHtml(totalQty)} pcs</span>
                        </div>
                        <div class="rack-manager-group-actions">
                          <button type="button" class="icon-only icon-pencil" data-rack-set-edit="${escapeHtml(label)}" title="Edit ${escapeHtml(label)} set" aria-label="Edit ${escapeHtml(label)} set"></button>
                          <button type="button" class="icon-only icon-trash danger" data-rack-set-delete="${escapeHtml(label)}" ${deletableCount ? "" : "disabled"} title="Delete empty racks in ${escapeHtml(label)}" aria-label="Delete empty racks in ${escapeHtml(label)}"></button>
                        </div>
                      </header>

                      <div class="rack-manager-rows">
                        ${racks
                          .slice()
                          .sort((a, b) => Number(a.sortOrder || 0) - Number(b.sortOrder || 0) || String(a.code).localeCompare(String(b.code), undefined, { numeric: true }))
                          .map((rack) => {
                            const qty = Number(rack.qty || 0);
                            const isTruck = rack.code === "T" || /truck/i.test(rack.type || "");
                            const canDelete = !isTruck && qty === 0;
                            const status = String(rack.status || "Open").toLowerCase() === "closed" ? "Complete" : qty ? "Open" : "Empty";

                            return `
                              <article class="rack-manager-row">
                                <div>
                                  <strong>${escapeHtml(isTruck ? "Truck / No Rack" : rack.code)}</strong>
                                  <span>${escapeHtml(rack.name || rack.type || "")}</span>
                                </div>
                                <span class="rack-status-badge ${escapeHtml(status.toLowerCase())}">${escapeHtml(status)}</span>
                                <b>${escapeHtml(qty)} pcs</b>
                                <button type="button" class="icon-only icon-pencil" data-rack-edit="${escapeHtml(rack.code)}" title="Edit rack" aria-label="Edit ${escapeHtml(rack.code)}"></button>
                                <button type="button" class="icon-only icon-trash danger" data-rack-delete="${escapeHtml(rack.code)}" ${canDelete ? "" : "disabled"} title="Delete empty rack" aria-label="Delete ${escapeHtml(rack.code)}"></button>
                              </article>
                            `;
                          })
                          .join("")}
                      </div>
                    </section>
                  `;
                })
                .join("")
            : `<div class="admin-empty">No racks available. Create a rack set to get started.</div>`
        }
      </div>
    </div>
  `;
}

function rackFormModalHtml() {
  const rack = state.rackModal?.rack || {};
  return `
    <form id="rackFormModal" class="admin-form rack-modal-form">
      <label><span>Rack code</span><input id="rackModalCode" type="text" autocomplete="off" value="${escapeHtml(rack.code || "")}" ${rack.code ? "readonly" : ""} placeholder="R11S"></label>
      <label><span>Rack name</span><input id="rackModalName" type="text" autocomplete="off" value="${escapeHtml(rack.name || "")}" placeholder="Rack 11 Steel"></label>
      <label>
        <span>Rack type</span>
        <select id="rackModalType">
          ${["Steel", "Wood", "Truck", "Aluminum", "Other"].map((type) => `<option ${String(rack.type || "Steel") === type ? "selected" : ""}>${escapeHtml(type)}</option>`).join("")}
        </select>
      </label>
      <footer class="modal-actions">${rack.code && rack.code !== "T" ? `<button type="button" class="danger" data-rack-delete="${escapeHtml(rack.code)}">Delete Rack</button>` : ""}<button type="submit">Confirm</button></footer>
    </form>
  `;
}

function rackSetFormModalHtml() {
  const set = state.rackModal?.set || {};
  return `
    <form id="rackSetFormModal" class="admin-form rack-modal-form">
      <label><span>Set suffix</span><input id="rackSetModalPrefix" type="text" autocomplete="off" value="${escapeHtml(set.prefix || "")}" placeholder="S"></label>
      <label><span>Set name</span><input id="rackSetModalName" type="text" autocomplete="off" value="${escapeHtml(set.name || "")}" placeholder="Steel"></label>
      <label><span>Rack count</span><input id="rackSetModalCount" type="number" min="1" max="100" value="${escapeHtml(set.count || 10)}"></label>
      <label><span>Starting rack number</span><input id="rackSetModalStart" type="number" min="1" max="999" value="${escapeHtml(set.start || 1)}"></label>
      <footer class="modal-actions"><button type="submit">Confirm</button></footer>
    </form>
  `;
}

function permissionLabel(permission) {
  return String(permission || "")
    .split("_")
    .map((part) => part ? part[0].toUpperCase() + part.slice(1) : "")
    .join(" ");
}

const PERMISSION_CATEGORIES = [
  {
    title: "Scanning",
    description: "Main scanner access, scan visibility, undo, and reset controls.",
    permissions: ["scan", "view_lists", "view_stations", "view_own_scans", "undo_scan", "reset_lists"],
  },
  {
    title: "Delivery Lists",
    description: "Importing, previewing, editing, printing, reports, and global search.",
    permissions: ["import_delivery_lists", "preview_import", "edit_delivery_lists", "export_reports", "view_reports", "global_search"],
  },
  {
    title: "Exceptions & Manual Fixes",
    description: "Manual adjustments and exception review/resolution.",
    permissions: ["manual_adjust", "view_exceptions", "resolve_exceptions"],
  },
  {
    title: "Admin & Users",
    description: "Admin dashboard, users, roles, active sessions, passwords, and updates.",
    permissions: [
      "view_admin",
      "manage_users",
      "manage_roles",
      "deactivate_users",
      "reactivate_users",
      "update_user_passwords",
      "view_active_sessions",
    ],
  },
  {
    title: "Stations & Rules",
    description: "Station setup and customer route rule management.",
    permissions: ["manage_stations", "remove_stations", "manage_customer_route_rules"],
  },
  {
    title: "Indian Trail / Bays",
    description: "Indian Trail receiving, bay map, bay actions, SDI, reports, and layout.",
    permissions: [
      "view_indian_trail",
      "indian_trail_receive",
      "view_bays",
      "assign_bay",
      "move_bay",
      "clear_bay",
      "mark_sdi",
      "remove_sdi",
      "bay_check",
      "indian_trail_reports",
      "manage_bay_layout",
    ],
  },
  {
    title: "Racks",
    description: "Rack overview, rack scanning, and rack management.",
    permissions: ["view_racks", "scan_racks", "manage_racks"],
  },
];

function categorizedPermissions(permissions = []) {
  const allPermissions = permissions || [];
  const assigned = new Set(PERMISSION_CATEGORIES.flatMap((category) => category.permissions));

  const categories = PERMISSION_CATEGORIES
    .map((category) => ({
      ...category,
      permissions: category.permissions.filter((permission) => allPermissions.includes(permission)),
    }))
    .filter((category) => category.permissions.length);

  const uncategorized = allPermissions.filter((permission) => !assigned.has(permission));

  if (uncategorized.length) {
    categories.push({
      title: "Other",
      description: "New or uncategorized permissions.",
      permissions: uncategorized,
    });
  }

  return categories;
}

function rolePermissionCategoryKey(roleName, categoryTitle) {
  return `${String(roleName || "").trim()}::${String(categoryTitle || "").trim()}`;
}

function resetRolePermissionUiSession() {
  state.rolePermissionOpenRoles = new Set();
  state.rolePermissionOpenCategories = new Set();
  state.rolePermissionScrollTop = 0;
}

function rememberRolePermissionUiState() {
  const editor = document.querySelector(".role-permission-editor");

  if (els.adminModalBody?.contains(editor)) {
    state.rolePermissionScrollTop = els.adminModalBody.scrollTop || 0;
  }

  document.querySelectorAll(".role-permission-card[data-role-card]").forEach((details) => {
    const roleName = details.dataset.roleCard || "";

    if (details.open) {
      state.rolePermissionOpenRoles.add(roleName);
    } else {
      state.rolePermissionOpenRoles.delete(roleName);
    }
  });

  document.querySelectorAll(".permission-category[data-role-name][data-category-title]").forEach((details) => {
    const key = rolePermissionCategoryKey(details.dataset.roleName, details.dataset.categoryTitle);

    if (details.open) {
      state.rolePermissionOpenCategories.add(key);
    } else {
      state.rolePermissionOpenCategories.delete(key);
    }
  });
}

function restoreRolePermissionUiScroll() {
  window.requestAnimationFrame(() => {
    if (els.adminModalBody) {
      els.adminModalBody.scrollTop = state.rolePermissionScrollTop || 0;
    }
  });
}

function rolePermissionCategoryHtml(roleName, category, selected) {
  const checkedCount = category.permissions.filter((permission) => selected.has(permission)).length;
  const categoryKey = rolePermissionCategoryKey(roleName, category.title);
  const open = state.rolePermissionOpenCategories.has(categoryKey);

  return `
    <details
      class="permission-category"
      data-role-name="${escapeHtml(roleName)}"
      data-category-title="${escapeHtml(category.title)}"
      ${open ? "open" : ""}
    >
      <summary>
        <span>
          <strong>${escapeHtml(category.title)}</strong>
          <small>${escapeHtml(category.description)}</small>
        </span>
        <b>${escapeHtml(checkedCount)} / ${escapeHtml(category.permissions.length)}</b>
      </summary>

      <div class="role-permission-grid">
        ${category.permissions
          .map(
            (permission) => `
              <label class="${selected.has(permission) ? "is-checked" : ""}">
                <input type="checkbox" value="${escapeHtml(permission)}" ${selected.has(permission) ? "checked" : ""}>
                <span>${escapeHtml(permissionLabel(permission))}</span>
              </label>
            `,
          )
          .join("")}
      </div>
    </details>
  `;
}

function rolePermissionCountText(role, permissions) {
  const selectedCount = Array.isArray(role.permissions) ? role.permissions.length : 0;
  const totalCount = Array.isArray(permissions) ? permissions.length : 0;

  return `${selectedCount} of ${totalCount} permissions`;
}

function rolePermissionsModalHtml() {
  const roles = state.adminRoles || [];
  const permissions = state.allPermissions || [];

  if (!roles.length || !permissions.length) {
    return `<div class="admin-empty">Role permissions are loading. Close and reopen this panel if they do not appear.</div>`;
  }

  const categories = categorizedPermissions(permissions);

  return `
    <div class="role-permission-editor">
      <div class="role-permission-intro">
        <strong>Role Permissions</strong>
        <span>Open a role, review permissions by page/action group, then save that role.</span>
      </div>

      ${roles
        .map((role) => {
          const selected = new Set(role.permissions || []);
          const roleOpen = state.rolePermissionOpenRoles.has(role.name);

          return `
            <details class="role-permission-card" data-role-card="${escapeHtml(role.name)}" ${roleOpen ? "open" : ""}>
              <summary class="role-permission-summary">
                <span class="role-collapse-icon" aria-hidden="true"></span>

                <span class="role-permission-title">
                  <strong>${escapeHtml(role.name)}</strong>
                  <small>${escapeHtml(role.description || permissionSummaryFromPermissions(role.permissions || []))}</small>
                </span>

                <span class="role-permission-count">${escapeHtml(rolePermissionCountText(role, permissions))}</span>

                <button
                  type="button"
                  class="role-permission-save"
                  data-save-role-permissions="${escapeHtml(role.name)}"
                  title="Save ${escapeHtml(role.name)} permissions"
                >Save</button>
              </summary>

              <div class="role-permission-body">
                ${categories.map((category) => rolePermissionCategoryHtml(role.name, category, selected)).join("")}
              </div>
            </details>
          `;
        })
        .join("")}
    </div>
  `;
}

function permissionSummaryFromPermissions(permissions) {
  const list = permissions || [];
  if (list.includes("view_admin")) return "Full admin access";
  if (list.includes("manage_users")) return "User and system management";
  if (list.includes("manage_racks")) return "Rack and scan management";
  if (list.includes("view_bays")) return "Indian Trail bay access";
  if (list.includes("scan")) return "Scanning and list access";
  return "Custom access";
}

async function saveRolePermissions(roleName) {
  rememberRolePermissionUiState();

  const card = document.querySelector(`[data-role-card="${CSS.escape(roleName)}"]`);

  if (!card) return;

  const permissions = [...card.querySelectorAll("input[type='checkbox']:checked")].map((input) => input.value);

  if (!permissions.length && !window.confirm(`Save ${roleName} with no permissions?`)) return;

  const payload = await fetchJson("/api/admin/roles/permissions", {
    method: "POST",
    body: JSON.stringify({ role: roleName, permissions }),
  });

  state.adminRoles = payload.roles || [];
  state.allPermissions = payload.permissions || state.allPermissions;

  if (els.adminModalBody) {
    els.adminModalBody.innerHTML = adminModalContent("roles");
    restoreRolePermissionUiScroll();
  }

  await refreshAdminPage();

  showFloatingNotice(`${roleName} permissions saved. Users with that role will sign in again to refresh access.`, "success");
}

function manualEditDeliveryDateForList(listId) {
  const selectedList = state.lists.find((item) => item.id === listId);

  return selectedList?.deliveryDate || state.lists[0]?.deliveryDate || "";
}

function manualEditStageListsForCurrentDelivery(selectedListId) {
  const deliveryDate = manualEditDeliveryDateForList(selectedListId);
  const stageLists = state.lists
    .filter((list) => list.deliveryDate === deliveryDate)
    .sort((a, b) => stageSort(a) - stageSort(b) || String(a.label || "").localeCompare(String(b.label || "")));

  return stageLists.length ? stageLists : state.lists.slice();
}

function manualEditStageSummary(listId) {
  const list = state.lists.find((item) => item.id === listId) || state.lists[0] || {};

  if (!list.id) {
    return "No stage selected";
  }

  return `${formatDisplayDate(list.deliveryDate)} - ${list.stage || "Stage"} - ${list.scanner || ""}`;
}

function manualEditModalHtml(resultsHtml = `<div class="admin-empty">Select a delivery list to load editable rows.</div>`) {
  const selected = state.manualEditListId || state.activeListId || state.lists[0]?.id || "";
  const stageLists = manualEditStageListsForCurrentDelivery(selected);

  return `
    <div class="manual-edit-shell">
      <div class="manual-edit-nav-row">
        <button class="manual-edit-back-button" type="button" data-manual-edit-back>
          <span aria-hidden="true">&larr;</span>
          Back to delivery lists
        </button>
        <span class="manual-edit-current-stage">${escapeHtml(manualEditStageSummary(selected))}</span>
      </div>

      <div class="manual-edit-modal-tools">
        <label class="manual-edit-control stage-control">
          <span>Delivery list stage</span>
          <select id="manualEditModalStage">
            ${stageLists
              .map(
                (list) =>
                  `<option value="${escapeHtml(list.id)}" ${list.id === selected ? "selected" : ""}>${escapeHtml(formatDisplayDate(list.deliveryDate))} - ${escapeHtml(list.stage)} - ${escapeHtml(list.scanner || "")}</option>`,
              )
              .join("")}
          </select>
        </label>

        <label class="manual-edit-control search-control">
          <span>Search within stage</span>
          <input id="manualEditModalSearch" type="search" autocomplete="off" value="${escapeHtml(state.manualEditQuery || "")}" placeholder="Order, customer, job, route...">
        </label>

        <div class="manual-edit-tool-actions">
          <button id="manualEditModalSearchBtn" type="button">Search</button>
          <button id="manualEditModalReloadBtn" class="secondary" type="button">Load All</button>
        </div>
      </div>

      <div id="manualEditModalResults" class="admin-table manual-edit-modal-results">${resultsHtml}</div>
    </div>
  `;
}

async function ensureManualEditLookupsLoaded() {
  if (!state.backend) return;

  const lookups = await Promise.allSettled([
    fetchJson("/api/racks"),
    fetchJson("/api/indian-trail/bays"),
    fetchJson("/api/admin/manual-edit-lookups"),
  ]);

  const rackResult = lookups[0];

  if (rackResult.status === "fulfilled") {
    state.racks = rackResult.value.racks || [];
    state.rackSummary = rackResult.value.summary || null;
  }

  const bayResult = lookups[1];

  if (bayResult.status === "fulfilled") {
    state.bays = bayResult.value.bays || [];
    state.bayEvents = bayResult.value.events || state.bayEvents || [];
  }

  const manualLookupResult = lookups[2];

  if (manualLookupResult.status === "fulfilled") {
    state.manualEditLookups = {
      products: manualLookupResult.value.products || [],
      routes: manualLookupResult.value.routes || [],
      processes: manualLookupResult.value.processes || [],
    };
  }
}

async function openManualEditForList(listId) {
  state.manualEditDirty = false;
  state.manualEditListId = listId || state.activeListId || state.lists[0]?.id || "";
  state.manualEditQuery = "";

  openAdminModal("manualEdit");

  await ensureManualEditLookupsLoaded();
  await runManualEditModalSearch(true);
}

async function fetchManualEditResults(query, listId) {
  const params = new URLSearchParams();
  if (query) params.set("q", query);
  if (listId) params.set("listId", listId);
  const payload = await fetchJson(`/api/admin/line-items/search?${params.toString()}`);
  return payload.results || [];
}

async function runManualEditModalSearch(loadAll = false) {
  const stage = document.getElementById("manualEditModalStage")?.value || state.manualEditListId || "";
  const query = loadAll ? "" : (document.getElementById("manualEditModalSearch")?.value.trim() || "");

  state.manualEditListId = stage;
  state.manualEditQuery = query;

  const currentStageLabel = document.querySelector(".manual-edit-current-stage");
  if (currentStageLabel) {
    currentStageLabel.textContent = manualEditStageSummary(stage);
  }

  const target = document.getElementById("manualEditModalResults");

  if (target) {
    target.innerHTML = `
      <div class="manual-edit-loading">
        <div class="admin-empty loading">
          <strong>Loading editable rows...</strong>
          <span class="loading-bar"><i></i></span>
        </div>
      </div>
    `;
  }

  const results = await fetchManualEditResults(query, stage);
  const html = manualEditResultsHtml(results);

  if (target) {
    target.innerHTML = html;
  }

  if (els.manualEditResults) {
    els.manualEditResults.innerHTML = html;
  }

  state.manualEditDirty = false;
}

function renderManualEditStageOptions() {
  if (!els.manualEditStageSelect) return;
  const current = els.manualEditStageSelect.value;
  const options = [`<option value="">All stages</option>`].concat(
    state.lists
      .slice()
      .sort((a, b) => String(b.deliveryDate || "").localeCompare(String(a.deliveryDate || "")) || String(a.stage || "").localeCompare(String(b.stage || "")))
      .map((list) => `<option value="${escapeHtml(list.id)}">${escapeHtml(formatDisplayDate(list.deliveryDate))} - ${escapeHtml(list.stage)}${list.scanner ? ` (${escapeHtml(list.scanner)})` : ""}</option>`),
  );
  els.manualEditStageSelect.innerHTML = options.join("");
  els.manualEditStageSelect.value = state.lists.some((list) => list.id === current) ? current : "";
}

function renderImportHistory(imports) {
  state.adminRecentImports = imports || [];

  const activeImports = activeRecentImports(state.adminRecentImports);

  if (els.adminDeliveryLists) {
    els.adminDeliveryLists.innerHTML = importHistoryRows(activeImports);
  }

  if (!els.importHistory) return;

  els.importHistory.innerHTML = importHistoryRows(activeImports);
}

function importHistoryRows(imports = []) {
  const seenImportGroups = new Set();
  const rows = imports
    .slice()
    .sort((a, b) =>
      String(b.deliveryDate || "").localeCompare(String(a.deliveryDate || "")) ||
      String(b.importedAt || "").localeCompare(String(a.importedAt || "")) ||
      String(a.stage || "").localeCompare(String(b.stage || "")),
    )
    .filter((entry) => {
    const key = entry.deliveryDate || entry.sourceName || entry.fileName || entry.importedAt || "unknown";
    if (seenImportGroups.has(key)) return false;
    seenImportGroups.add(key);
    return true;
  }).slice(0, 12);

  if (!rows.length) {
    return `<div class="admin-empty">No import history yet. Imports from the temp folder or single files will appear here.</div>`;
  }

  const stageNameForRow = (row, list) =>
    String(row.stage || row.stageProfile || row.stageSheetName || list?.stage || list?.label || row.listId || "Updated stage");

  const isStagingRow = (row, list) => /staging/i.test(stageNameForRow(row, list));

  const stageCategoryForImportRow = (row, list) =>
    stageCategory({
      stage: stageNameForRow(row, list),
      scanner: row.stageProfile || row.scanner || list?.scanner || "",
    });

  const updatedQtyForRow = (row, list) =>
    Number(row.totalQty ?? row.updatedQty ?? row.newQty ?? list?.totalQty ?? 0);

  const changedQtyForRow = (row, list) => {
    const updatedQty = updatedQtyForRow(row, list);
    const explicitAddedQty = Number(row.addedPieceQty ?? row.addedQty ?? 0);
    const explicitChangedQty = Number(row.changedPieceQty ?? row.changedQty ?? 0);

    if (row.created) {
      return updatedQty;
    }

    if (!explicitAddedQty && !explicitChangedQty) {
      const explicitOriginalQty = row.originalQty ?? row.previousQty ?? row.oldQty ?? row.beforeQty;

      if (Number(explicitOriginalQty || 0) <= 0 && updatedQty > 0) {
        return updatedQty;
      }
    }

    return explicitAddedQty || explicitChangedQty || 0;
  };

  const originalQtyForRow = (row, list) => {
    const updatedQty = updatedQtyForRow(row, list);
    const changedQty = changedQtyForRow(row, list);
    const explicitOriginalQty = row.originalQty ?? row.originalPieceQty ?? row.previousQty ?? row.oldQty ?? row.beforeQty;

    if (explicitOriginalQty !== undefined && explicitOriginalQty !== null && explicitOriginalQty !== "") {
      return Number(explicitOriginalQty);
    }

    if (row.created) {
      return 0;
    }

    return Math.max(updatedQty - changedQty, 0);
  };

  const isNewStageRow = (row, list) => {
    const originalQty = originalQtyForRow(row, list);
    const updatedQty = updatedQtyForRow(row, list);

    return Boolean(row.created) || (originalQty <= 0 && updatedQty > 0);
  };

  const stageRowsForEntry = (entry) => {
    if (Array.isArray(entry.stageSummaries) && entry.stageSummaries.length) {
      return entry.stageSummaries;
    }

    return (entry.listIds || []).map((listId) => {
      const list = state.lists.find((item) => item.id === listId);

      return {
        listId,
        stage: list?.stage || listId,
        totalQty: list?.totalQty ?? entry.totalQty ?? 0,
        changedLineCount: entry.changedLineCount || 0,
        changedPieceQty: entry.changedPieceQty || entry.addedPieceQty || 0,
        addedPieceQty: entry.addedPieceQty || 0,
        created: Boolean(entry.createdCount),
      };
    });
  };

  const hasStageChanges = (row) =>
    row.created ||
    Number(row.changedLineCount || 0) ||
    Number(row.changedPieceQty || 0) ||
    Number(row.addedPieceQty || 0);

  const stageRowKey = (row) => {
    const list = state.lists.find((item) => item.id === row.listId);

    return String(row.listId || stageNameForRow(row, list))
      .trim()
      .toLowerCase()
      .replace(/\s+/g, " ");
  };

  const stageRowPriority = (row) => {
    const list = state.lists.find((item) => item.id === row.listId);
    const originalQty = originalQtyForRow(row, list);
    const updatedQty = updatedQtyForRow(row, list);
    const changedQty = changedQtyForRow(row, list);
    const changedLineCount = Number(row.changedLineCount || 0);
    const isNewStage = isNewStageRow(row, list);

    return (
      (originalQty > 0 ? 100000000 : 0) +
      (!isNewStage ? 10000000 : 0) +
      (changedLineCount * 100000) +
      (changedQty * 1000) +
      updatedQty
    );
  };

  const collapseDuplicateStageRows = (stageRows) => {
    const byStage = new Map();

    for (const row of stageRows) {
      const key = stageRowKey(row);

      if (!key) continue;

      const existing = byStage.get(key);

      if (!existing || stageRowPriority(row) > stageRowPriority(existing)) {
        byStage.set(key, row);
      }
    }

    return [...byStage.values()];
  };

  const stageSortForRow = (row) => {
    const list = state.lists.find((item) => item.id === row.listId);

    return stageSort(list || { stage: stageNameForRow(row, list), scanner: row.stageProfile || "" });
  };

  const allStageRowsForGroup = (group, changedStageRows) => {
    const byStage = new Map();

    const addRow = (row) => {
      const key = stageRowKey(row);

      if (!key || byStage.has(key)) return;

      byStage.set(key, row);
    };

    changedStageRows.forEach(addRow);

    state.lists
      .filter((list) => String(list.deliveryDate || "") === String(group.deliveryDate || ""))
      .forEach((list) => {
        addRow({
          listId: list.id,
          stage: list.stage,
          stageProfile: list.scanner,
          totalQty: list.totalQty || 0,
          changedLineCount: 0,
          changedPieceQty: 0,
          addedPieceQty: 0,
          created: false,
        });
      });

    return [...byStage.values()].sort((a, b) => {
      const sortDiff = stageSortForRow(a) - stageSortForRow(b);
      if (sortDiff) return sortDiff;

      const listA = state.lists.find((item) => item.id === a.listId);
      const listB = state.lists.find((item) => item.id === b.listId);

      return stageNameForRow(a, listA).localeCompare(stageNameForRow(b, listB));
    });
  };

  const groups = new Map();

  for (const entry of rows) {
    const groupKey = entry.deliveryDate || entry.sourceName || entry.fileName || entry.importedAt || "unknown";

    if (!groups.has(groupKey)) {
      groups.set(groupKey, {
        deliveryDate: entry.deliveryDate || "",
        sourceName: entry.sourceName || entry.fileName || "Imported delivery list",
        importedAt: entry.importedAt || entry.updatedAt || entry.createdAt || "",
        entries: [],
        stageRows: [],
        printableIds: new Set(),
      });
    }

    const group = groups.get(groupKey);
    const entryStageRows = stageRowsForEntry(entry);

    group.entries.push(entry);
    group.stageRows.push(...entryStageRows);

    for (const row of entryStageRows) {
      if (row.listId) {
        group.printableIds.add(row.listId);
      }
    }

    if (entry.importedAt || entry.updatedAt || entry.createdAt) {
      group.importedAt = entry.importedAt || entry.updatedAt || entry.createdAt;
    }
  }

  return `
    <div class="admin-import-date-list">
      ${[...groups.values()]
        .map((group, index) => {
          const changedStageRows = collapseDuplicateStageRows(group.stageRows.filter(hasStageChanges));
          const allStageRows = allStageRowsForGroup(group, changedStageRows);
          const stagingRows = allStageRows.filter((row) => {
            const list = state.lists.find((item) => item.id === row.listId);
            return isStagingRow(row, list);
          });

          const changedStagingRows = changedStageRows.filter((row) => {
            const list = state.lists.find((item) => item.id === row.listId);
            return isStagingRow(row, list);
          });

          const stagingOriginalQty = stagingRows.reduce((sum, row) => {
            const list = state.lists.find((item) => item.id === row.listId);
            return sum + originalQtyForRow(row, list);
          }, 0);

          const stagingChangedQty = changedStagingRows.reduce((sum, row) => {
            const list = state.lists.find((item) => item.id === row.listId);
            return sum + changedQtyForRow(row, list);
          }, 0);

          const stagingUpdatedQty = stagingRows.reduce((sum, row) => {
            const list = state.lists.find((item) => item.id === row.listId);
            return sum + updatedQtyForRow(row, list);
          }, 0);

          const newStageRows = changedStageRows.filter((row) => {
            const list = state.lists.find((item) => item.id === row.listId);
            return isNewStageRow(row, list);
          });

          const updatedStageRows = changedStageRows.filter((row) => {
            const list = state.lists.find((item) => item.id === row.listId);
            return !isNewStageRow(row, list);
          });

          const hasNewStages = newStageRows.length > 0;
          const hasUpdatedStages = updatedStageRows.length > 0;
          const isBrandNewDeliveryList = hasNewStages && !hasUpdatedStages;

          const newPrintableIds = [...new Set(newStageRows.map((row) => row.listId).filter(Boolean))];
          const updatedPrintableIds = [...new Set(updatedStageRows.map((row) => row.listId).filter(Boolean))];
          const printableIds = [...new Set([...updatedPrintableIds, ...newPrintableIds])];
          const printButtonLabel = isBrandNewDeliveryList
            ? "Print / Export New Delivery List"
            : hasNewStages && hasUpdatedStages
              ? "Print / Export Changed Stages"
              : "Print / Export Changed Stages";
          const hasAnyChanges = hasNewStages || hasUpdatedStages;
          const groupClass = !hasAnyChanges
            ? "is-no-update-batch"
            : isBrandNewDeliveryList
              ? "is-new-delivery-list"
              : hasNewStages && hasUpdatedStages
                ? "is-mixed-batch"
                : "is-updated-batch";
          const importedText = group.importedAt ? `Updated at: ${formatDateTime(group.importedAt)}` : "Updated at: --";
          const sourceFileText = group.sourceName ? `File: ${group.sourceName}` : "";
          const groupStatusHtml = hasAnyChanges
            ? `
              ${hasUpdatedStages ? `<span class="import-status-pill updated">Updated</span>` : ""}
              ${isBrandNewDeliveryList ? `<span class="import-status-pill new">New</span>` : ""}
              ${hasNewStages && hasUpdatedStages ? `<span class="import-status-pill new-stage">New Stage</span>` : ""}
            `
            : `<span class="import-status-pill no-change">No Updates</span>`;
          
          const stageHtml = allStageRows.length
            ? allStageRows
                .map((row) => {
                  const list = state.lists.find((item) => item.id === row.listId);
                  const stageName = stageNameForRow(row, list);
                  const originalQty = originalQtyForRow(row, list);
                  const changedQty = changedQtyForRow(row, list);
                  const updatedQty = updatedQtyForRow(row, list);
                  const rowHasChanges = hasStageChanges(row);
                  const rowIsNew = rowHasChanges && isNewStageRow(row, list);
                  const stageCategoryClass = `stage-row-${stageCategoryForImportRow(row, list)}`;
                  const rowChangeClass = rowIsNew ? "is-new-row" : rowHasChanges ? "is-updated-row" : "is-unchanged-row";
                  const rowClass = `${stageCategoryClass} ${rowChangeClass}`;
                  const kindLabel = rowIsNew ? "New Stage" : rowHasChanges ? "Updated" : "No Updates";
                  const kindClass = rowIsNew ? "new-stage" : rowHasChanges ? "updated" : "no-change";

                  return `
                    <tr class="${rowClass}">
                      <td><span class="stage-pill-admin">${escapeHtml(stageName)}</span></td>
                      <td><span class="qty-before">${escapeHtml(originalQty)} pcs</span></td>
                      <td><span class="qty-change ${rowHasChanges ? "" : "is-zero"}">${rowHasChanges ? `+${escapeHtml(changedQty)} pcs` : "0 pcs"}</span></td>
                      <td><strong>${escapeHtml(updatedQty)} pcs</strong></td>
                      <td><span class="import-status-pill ${kindClass}">${escapeHtml(kindLabel)}</span></td>
                      <td>
                        ${
                          row.listId
                            ? `<button
                                type="button"
                                class="admin-import-icon-button"
                                data-print-lists="${escapeHtml(row.listId)}"
                                data-print-date="${escapeHtml(group.deliveryDate)}"
                                data-print-updated-only="${rowHasChanges && !rowIsNew ? "1" : ""}"
                                aria-label="${rowIsNew ? "Print / Export New Stage" : rowHasChanges ? "Print / Export Stage" : "Print / Export Stage"}"
                                title="${rowIsNew ? "Print / Export New Stage" : rowHasChanges ? "Print / Export Stage" : "Print / Export Stage"}"
                              ><span class="admin-import-print-icon" aria-hidden="true"></span></button>`
                            : ""
                        }
                      </td>
                    </tr>
                  `;
                })
                .join("")
            : `
              <tr>
                <td colspan="6">No stages were found for this delivery date.</td>
              </tr>
            `;

          return `
            <details class="admin-import-date-group ${groupClass}">
<summary class="admin-import-date-summary">
  <span class="admin-import-date-main">
    <span class="admin-import-date-title">
      <strong>${escapeHtml(formatDisplayDate(group.deliveryDate))}</strong>
      <span class="admin-import-status-pills">
        ${groupStatusHtml}
      </span>
    </span>

    <span class="admin-import-date-meta">
      <small class="admin-import-updated-at">${escapeHtml(importedText)}</small>
      ${sourceFileText ? `<small class="admin-import-source-file">${escapeHtml(sourceFileText)}</small>` : ""}
    </span>
  </span>

  <span class="admin-import-date-qty">
    <span class="admin-import-qty-flow">
      <span class="qty-before">${escapeHtml(stagingOriginalQty)} pcs</span>
      <span class="qty-change ${stagingChangedQty ? "" : "is-zero"}">${stagingChangedQty ? `+${escapeHtml(stagingChangedQty)} pcs` : "0 pcs"}</span>
      <strong>${escapeHtml(stagingUpdatedQty)} pcs</strong>
    </span>
  </span>

  ${
    printableIds.length
      ? `<button
          type="button"
          class="admin-import-icon-button"
          data-print-lists="${escapeHtml(printableIds.join(","))}"
          data-print-date="${escapeHtml(group.deliveryDate)}"
          data-print-updated-only="${hasUpdatedStages && !isBrandNewDeliveryList ? "1" : ""}"
          aria-label="${escapeHtml(printButtonLabel)}"
          title="${escapeHtml(printButtonLabel)}"
        ><span class="admin-import-print-icon" aria-hidden="true"></span></button>`
      : ""
  }
</summary>

              <div class="admin-import-stage-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Stage</th>
                      <th>Original Qty</th>
                      <th>Changed Qty</th>
                      <th>Updated Qty</th>
                      <th>Status</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    ${stageHtml}
                  </tbody>
                </table>
              </div>
            </details>
          `;
        })
        .join("")}
    </div>
  `;
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
  await resetAdminScansForList(listId);
}

async function resetAdminScansForList(listId) {
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
  renderAdminDeliveryLists();
}

async function resetAdminScansForDate(deliveryDate) {
  const lists = state.lists.filter((list) => list.deliveryDate === deliveryDate);

  if (!lists.length) return;

  const firstConfirm = window.confirm(`Reset all scans for every stage on ${formatDisplayDate(deliveryDate)}?`);
  if (!firstConfirm) return;

  const typed = window.prompt(`Type RESET DATE to reset every stage for ${formatDisplayDate(deliveryDate)}.`);
  if (typed !== "RESET DATE") {
    if (els.resetScansStatus) {
      els.resetScansStatus.innerHTML = `<strong>Reset cancelled</strong><span>The confirmation text did not match.</span>`;
    }

    return;
  }

  for (const list of lists) {
    await fetchJson("/api/reset", {
      method: "POST",
      body: JSON.stringify({ listId: list.id, ...requestContext() }),
    });
  }

  await loadDeliveryLists(state.activeListId);
  if (state.activeListId && lists.some((list) => list.id === state.activeListId)) {
    await activateList(state.activeListId, false);
  }
  await refreshAdminPage();

  renderHome();
  renderScanPage();
  renderDeliveryListSelect();
  renderAdminDeleteControls();
  renderAdminResetControls();
  renderAdminDeliveryLists();

  const target = document.getElementById("adminDeliveryListModalResults");
  if (target) {
    target.innerHTML = deliveryListAdminRows(state.lists, state.lists.length || 1, true);
  }

  if (els.resetScansStatus) {
    els.resetScansStatus.innerHTML = `<strong>Scans reset</strong><span>Every stage for ${escapeHtml(formatDisplayDate(deliveryDate))} is back to zero scanned quantity.</span>`;
  }
}

async function deleteAdminDeliveryDateByDate(deliveryDate) {
  if (!deliveryDate || !window.confirm(`Delete every stage for ${formatDisplayDate(deliveryDate)}?`)) return;

  const result = await fetchJson("/api/admin/delete-date", {
    method: "POST",
    body: JSON.stringify({ deliveryDate, ...requestContext() }),
  });

  state.lists = result.lists || [];

  if (!state.lists.some((list) => list.id === state.activeListId)) {
    state.activeListId = state.lists[0]?.id || "";

    if (state.activeListId) {
      await activateList(state.activeListId, false);
    } else {
      state.meta = null;
      state.items = [];
      state.recent = [];
      state.errors = [];
      state.lastScan = null;
    }
  }

  await loadDeliveryLists(state.activeListId);
  await refreshAdminPage();

  renderHome();
  renderScanPage();
  renderDeliveryListSelect();
  renderAdminDeleteControls();
  renderAdminResetControls();
  renderAdminDeliveryLists();

  const target = document.getElementById("adminDeliveryListModalResults");
  if (target) {
    target.innerHTML = deliveryListAdminRows(state.lists, state.lists.length || 1, true);
  }

  if (els.deleteListStatus) {
    els.deleteListStatus.innerHTML = `<strong>Deleted date</strong><span>${escapeHtml(result.deletedCount || 0)} stages removed.</span>`;
  }
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

    if (state.activeListId) {
      await activateList(state.activeListId, false);
    } else {
      state.meta = null;
      state.items = [];
      state.recent = [];
      state.errors = [];
      state.lastScan = null;
    }
  }

  await loadDeliveryLists(state.activeListId);
  await refreshAdminPage();

  renderHome();
  renderScanPage();
  renderDeliveryListSelect();
  renderAdminDeleteControls();
  renderAdminDeliveryLists();
}

async function deleteAdminDeliveryListById(listId) {
  const list = state.lists.find((item) => item.id === listId);
  if (!list || !window.confirm(`Delete ${list.label}? This removes that delivery-list stage.`)) return;
  const result = await fetchJson("/api/admin/delete-list", {
    method: "POST",
    body: JSON.stringify({ listId, ...requestContext() }),
  });
  state.lists = result.lists || [];
  if (!state.lists.some((item) => item.id === state.activeListId)) {
    state.activeListId = state.lists[0]?.id || "";

    if (state.activeListId) {
      await activateList(state.activeListId, false);
    } else {
      state.meta = null;
      state.items = [];
      state.recent = [];
      state.errors = [];
      state.lastScan = null;
    }
  }

  await loadDeliveryLists(state.activeListId);
  await refreshAdminPage();

  renderHome();
  renderScanPage();
  renderDeliveryListSelect();
  renderAdminDeleteControls();
  renderAdminDeliveryLists();
  openAdminModal("deliveryLists");
}

function renderAdminUsers() {
  if (!els.adminUsers) return;
  if (!state.adminUsers.length) {
    els.adminUsers.innerHTML = `<div class="admin-empty">No users loaded.</div>`;
    return;
  }
  els.adminUsers.innerHTML = renderAdminUsersTable(false, state.adminUsers.length || 1);
}

function permissionSummaryForUser(user) {
  const roles = user.roles || [];
  const permissions = user.permissions || [];
  if (permissions.includes("view_admin")) return "Full admin access";
  if (roles.some((role) => /manager/i.test(role))) return "Manage scans, bays, users, and reports";
  if (roles.some((role) => /lead|supervisor/i.test(role))) return "Scan, undo, manage exceptions, and reports";
  if (roles.some((role) => /indian trail/i.test(role))) return "Indian Trail scanning and bay access";
  if (permissions.includes("scan_items")) return "Scan and view assigned stages";
  return "View assigned delivery lists";
}

function userInitials(user) {
  const display = String(user?.displayName || user?.username || "?").trim();

  const parts = display
    .split(/\s+/)
    .map((part) => part[0])
    .filter(Boolean);

  if (parts.length >= 2) return `${parts[0]}${parts[1]}`.toUpperCase();

  return display.slice(0, 2).toUpperCase() || "?";
}

function userAccentClass(user) {
  const text = String(user?.username || user?.displayName || "").toLowerCase();

  if (/admin/.test(text)) return "accent-admin";
  if (/lead|supervisor/.test(text)) return "accent-lead";
  if (/manager/.test(text)) return "accent-manager";
  if (/operator/.test(text)) return "accent-operator";
  if (/trail|it/.test(text)) return "accent-trail";

  return "accent-default";
}

function userActionButtonHtml({ className = "", attr = "", label = "", icon = "", disabled = false }) {
  const safeLabel = escapeHtml(label);

  return `
    <button
      type="button"
      class="user-icon-action ${className}"
      ${attr}
      ${disabled ? "disabled" : ""}
      aria-label="${safeLabel}"
      title="${safeLabel}"
    >
      <span class="user-action-icon ${escapeHtml(icon)}" aria-hidden="true"></span>
    </button>
  `;
}

function generateTemporaryPassword(length = 12) {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%";
  const values = new Uint32Array(length);

  if (window.crypto?.getRandomValues) {
    window.crypto.getRandomValues(values);
  }

  return Array.from({ length }, (_, index) => {
    const value = values[index] || Math.floor(Math.random() * alphabet.length);
    return alphabet[value % alphabet.length];
  }).join("");
}

async function refreshAdminUsersUi() {
  const usersModalOpen = Boolean(els.adminModal && !els.adminModal.hidden && els.adminModalBody?.querySelector(".users-modal-shell"));

  await refreshAdminPage();

  if (usersModalOpen && els.adminModalBody) {
    els.adminModalBody.innerHTML = adminModalContent("users");
  }
}

function confirmDeactivateUser(username) {
  return new Promise((resolve) => {
    const existingDialog = document.querySelector(".user-deactivate-backdrop");
    if (existingDialog) existingDialog.remove();

    const dialog = document.createElement("div");
    let keyHandler = () => {};

    dialog.className = "user-deactivate-backdrop";
    dialog.innerHTML = `
      <section class="user-deactivate-dialog" role="dialog" aria-modal="true" aria-labelledby="deactivateUserTitle">
        <button type="button" class="user-deactivate-close" data-user-deactivate-cancel aria-label="Close deactivate user confirmation">&times;</button>

        <span class="user-deactivate-icon" aria-hidden="true"></span>

        <div class="user-deactivate-copy">
          <h2 id="deactivateUserTitle">Deactivate user?</h2>
          <p>Deactivate <strong>${escapeHtml(username)}</strong>? This keeps the profile and history, but the user will no longer be able to sign in until reactivated.</p>
        </div>

        <div class="user-deactivate-actions">
          <button type="button" class="user-deactivate-cancel" data-user-deactivate-cancel>Cancel</button>
          <button type="button" class="user-deactivate-confirm" data-user-deactivate-confirm>Deactivate User</button>
        </div>
      </section>
    `;

    const close = (confirmed) => {
      document.removeEventListener("keydown", keyHandler);
      dialog.remove();
      document.body.classList.remove("modal-scroll-locked");
      resolve(Boolean(confirmed));
    };

    dialog.addEventListener("click", (event) => {
      if (event.target === dialog || event.target.closest("[data-user-deactivate-cancel]")) {
        close(false);
        return;
      }

      if (event.target.closest("[data-user-deactivate-confirm]")) {
        close(true);
      }
    });

    keyHandler = (event) => {
      if (event.key !== "Escape") return;
      close(false);
    };

    document.addEventListener("keydown", keyHandler);
    document.body.appendChild(dialog);
    document.body.classList.add("modal-scroll-locked");
    dialog.querySelector("[data-user-deactivate-cancel]")?.focus();
  });
}

function renderAdminUsersTable(editable = false, limit = 5) {
  const users = state.adminUsers.slice(0, limit);

  if (!users.length) return `<div class="admin-empty">No users loaded.</div>`;

  const activeSessionUsers = new Set((state.activeSessions || []).map((session) => String(session.username || "").toLowerCase()));

  if (!editable) {
    return `
      <div class="admin-user-preview-list">
        ${users
          .map((user) => {
            const loggedIn = activeSessionUsers.has(String(user.username || "").toLowerCase());

            return `
              <article class="admin-user-preview-row">
                <span class="user-avatar ${escapeHtml(userAccentClass(user))}">${escapeHtml(userInitials(user))}</span>

                <div>
                  <strong>${escapeHtml(user.displayName)}</strong>
                  <span>${escapeHtml(user.username)} · ${escapeHtml((user.roles || []).join(", ") || "No role")}</span>
                  <small>${escapeHtml(permissionSummaryForUser(user))}</small>
                  <small>Station: ${escapeHtml(userAssignedStation(user) || "No assigned station")}</small>
                </div>

                <span class="user-status-stack">
                  <span class="user-status-pill ${user.active ? "active" : "inactive"}">${user.active ? "Active profile" : "Inactive profile"}</span>
                  <span class="user-session-pill ${loggedIn ? "is-online" : "is-offline"}">${loggedIn ? "Signed in" : "Logged out"}</span>
                </span>
              </article>
            `;
          })
          .join("")}
      </div>
    `;
  }

  return `
    <div class="users-table">
      <div class="users-table-head">
        <span>User</span>
        <span>Role</span>
        <span>Station</span>
        <span>Permissions / Notes</span>
        <span>Password</span>
        <span>Status</span>
        <span>Actions</span>
      </div>

      <div class="users-table-body">
        ${users
          .map((user) => {
            const active = Boolean(user.active);
            const username = String(user.username || "");
            const roles = user.roles || [];
            const stageAccess = user.stageAccess || [];
            const assignedStation = userAssignedStation(user);
            const loggedIn = activeSessionUsers.has(username.toLowerCase());

            return `
              <article class="user-admin-row ${active ? "is-active-user" : "is-inactive-user"}">
                <div class="user-admin-main">
                  <span class="user-avatar ${escapeHtml(userAccentClass(user))}">${escapeHtml(userInitials(user))}</span>

                  <span class="user-admin-name">
                    <strong>${escapeHtml(user.displayName || username)}</strong>
                    <small>${escapeHtml(username)}</small>
                  </span>
                </div>

                <div class="user-admin-role">
                  ${
                    hasPermission("manage_roles")
                      ? `
                        <select data-user-role-select="${escapeHtml(username)}">
                          ${ROLE_OPTIONS.map((role) => `<option value="${escapeHtml(role)}" ${roles.includes(role) ? "selected" : ""}>${escapeHtml(role)}</option>`).join("")}
                        </select>
                      `
                      : `<span>${escapeHtml(roles.join(", ") || "No role")}</span>`
                  }
                </div>

                <div class="user-admin-station">
                  ${
                    hasPermission("manage_roles")
                      ? `
                        <select data-user-station-select="${escapeHtml(username)}">
                          <option value="">No assigned station</option>
                          ${state.stations
                            .map((station) => `<option value="${escapeHtml(station)}" ${assignedStation === station ? "selected" : ""}>${escapeHtml(station)}</option>`)
                            .join("")}
                        </select>
                      `
                      : `<span>${escapeHtml(assignedStation || "No assigned station")}</span>`
                  }
                </div>

                <div class="user-admin-permissions">
                  <strong>${escapeHtml(permissionSummaryForUser(user))}</strong>
                  <small>Stages: ${escapeHtml(stageAccess.join(", ") || "No stage access")}</small>
                </div>

                <div class="user-admin-password">
                  ${
                    hasPermission("update_user_passwords")
                      ? `
                        <div class="password-reset-row polished">
  <input data-user-password="${escapeHtml(username)}" type="password" placeholder="New password">
  ${userActionButtonHtml({
    className: "secondary",
    attr: `data-generate-user-password="${escapeHtml(username)}"`,
    label: "Generate temporary password",
    icon: "icon-key",
  })}
  ${userActionButtonHtml({
    className: "secondary",
    attr: `data-toggle-password="${escapeHtml(username)}"`,
    label: "Show password",
    icon: "icon-eye",
  })}
  ${userActionButtonHtml({
    className: "primary",
    attr: `data-update-user-password="${escapeHtml(username)}"`,
    label: "Save password",
    icon: "icon-save-user",
  })}
</div>
<small class="password-note">
  Existing password cannot be viewed.<br>
  Generate or enter a new one, then save it.
</small>
                      `
                      : `<span class="protected-pill">Protected</span>`
                  }
                </div>

                <div class="user-admin-status">
                  <span class="user-status-pill ${active ? "active" : "inactive"}">
                    <i></i>
                    ${active ? "Active profile" : "Inactive profile"}
                  </span>

                  <span class="user-session-pill ${loggedIn ? "is-online" : "is-offline"}">${loggedIn ? "Signed in" : "Logged out"}</span>
                </div>

                <div class="user-admin-actions">
                  ${
                    hasPermission("manage_roles")
                      ? userActionButtonHtml({
                          className: "secondary",
                          attr: `data-update-user-role="${escapeHtml(username)}"`,
                          label: "Save role",
                          icon: "icon-shield",
                        })
                      : ""
                  }

                  ${
                    active && hasPermission("deactivate_users")
                      ? userActionButtonHtml({
                          className: "danger",
                          attr: `data-deactivate-user="${escapeHtml(username)}"`,
                          label: "Deactivate",
                          icon: "icon-power",
                        })
                      : ""
                  }

                  ${
                    !active && hasPermission("reactivate_users")
                      ? userActionButtonHtml({
                          className: "success",
                          attr: `data-reactivate-user="${escapeHtml(username)}"`,
                          label: "Activate",
                          icon: "icon-power",
                        })
                      : ""
                  }

                  ${
                    hasPermission("manage_users")
                      ? userActionButtonHtml({
                          className: "danger",
                          attr: `data-delete-user="${escapeHtml(username)}"`,
                          label: "Delete user",
                          icon: "icon-trash",
                        })
                      : ""
                  }
                </div>
              </article>
            `;
          })
          .join("")}
      </div>
    </div>
  `;
}

function renderAdminStations() {
  if (!els.adminStations) return;
  els.adminStations.innerHTML = renderAdminStationsList(false, state.stations.length || 1);
}

function renderAdminStationsList(editable = false, limit = 6) {
  return state.stations
    .slice(0, limit)
    .map((station) => `
      <div class="station-row">
        ${editable ? `<input data-station-name="${escapeHtml(station)}" type="text" value="${escapeHtml(station)}">` : `<strong>${escapeHtml(station)}</strong><span>Online</span>`}
        ${editable && hasPermission("manage_stations") ? `<button type="button" data-rename-station="${escapeHtml(station)}">Save</button>` : ""}
        ${editable && hasPermission("remove_stations") && !DEFAULT_STATIONS.includes(station) ? `<button type="button" data-remove-station="${escapeHtml(station)}">Remove</button>` : ""}
      </div>
    `)
    .join("") || `<div class="admin-empty">No stations loaded.</div>`;
}

function customerRouteValue(route) {
  const raw = String(route || "").trim().toUpperCase();

  if (["GRN", "GNV", "GREENVILLE"].includes(raw)) return "GNV";
  if (raw === "DTC" || raw === "DELIVER TO CUSTOMER") return "DTC";
  if (raw === "CPU" || raw === "CUSTOMER PICKUP") return "CPU";

  const clean = raw.replace(/[^A-Z0-9_-]+/g, "-").replace(/^-+|-+$/g, "");

  if (["GRN", "GNV", "GREENVILLE"].includes(clean)) return "GNV";
  if (clean === "DTC") return "DTC";
  if (clean === "CPU" || clean === "CUSTOMER-PICKUP") return "CPU";

  return clean || "CPU";
}

function customerRouteDisplay(route) {
  const clean = customerRouteValue(route);

  if (clean === "CPU") return "CPU / Customer Pickup";
  if (clean === "DTC") return "DTC / Deliver to Customer";
  if (clean === "GNV") return "GNV / Greenville";

  return clean;
}

function customerRouteOptionList() {
  const customRoutes = [...new Set((state.adminCustomerRouteRules || [])
    .map((rule) => customerRouteValue(rule.route))
    .filter((route) => route && !CUSTOMER_ROUTE_OPTIONS.some((option) => option.value === route)))]
    .sort();

  return [...CUSTOMER_ROUTE_OPTIONS, ...customRoutes.map((route) => ({ value: route, label: route }))];
}

function customerRouteOptionsHtml(selectedRoute = "CPU") {
  const selected = customerRouteValue(selectedRoute);

  return customerRouteOptionList()
    .map((option) => `
      <option value="${escapeHtml(option.value)}" ${selected === option.value ? "selected" : ""}>${escapeHtml(option.label)}</option>
    `)
    .join("");
}

function customerRouteRuleRowsHtml(editable = false, limit = 0) {
  const rules = limit ? state.adminCustomerRouteRules.slice(0, limit) : state.adminCustomerRouteRules;

  if (!rules.length) {
    return `
      <div class="customer-route-empty">
        <strong>No customer route rules</strong>
        <span>Add customer-to-route rules here. Custom route codes create custom route stages during import.</span>
      </div>
    `;
  }

  return rules
    .map((rule) => {
      const routeCode = customerRouteValue(rule.route);
      const routeLabel = customerRouteDisplay(rule.route);

      return `
        <article class="customer-route-rule-row ${editable ? "is-editable" : ""}">
          <div class="customer-route-row-fields">
            <label class="customer-route-customer-field">
              <span>Customer / match text</span>
              ${
                editable
                  ? `<input data-customer-route-pattern="${escapeHtml(rule.id)}" type="text" value="${escapeHtml(rule.customerPattern)}" aria-label="Customer route customer">`
                  : `<strong>${escapeHtml(rule.customerPattern)}</strong>`
              }
            </label>

            <label class="customer-route-route-field">
              <span>Route</span>
              ${
                editable
                  ? `<select data-customer-route-route="${escapeHtml(rule.id)}" aria-label="Customer route code">
                      ${customerRouteOptionsHtml(rule.route)}
                    </select>`
                  : `<em class="customer-route-badge">${escapeHtml(routeLabel)}</em>`
              }
            </label>
          </div>

          ${
            editable
              ? `<div class="customer-route-row-actions">
                  <button type="button" class="icon-only icon-save" data-save-customer-route-rule="${escapeHtml(rule.id)}" title="Save route" aria-label="Save route"></button>
                  <button type="button" class="icon-only icon-trash danger" data-remove-customer-route-rule="${escapeHtml(rule.id)}" title="Delete route" aria-label="Delete route"></button>
                </div>`
              : ""
          }
        </article>
      `;
    })
    .join("");
}

function customerRouteRulesModalHtml() {
  const ruleCount = state.adminCustomerRouteRules.length;

  return `
    <div class="customer-route-modal-shell customer-route-modern">
      <section class="customer-route-modal-intro">
        <div>
          <span>Customer Route Rules</span>
          <strong>Match customers to the route they should import into.</strong>
          <p>New custom routes become their own stage during import when a customer matches that route.</p>
        </div>
        <b>${escapeHtml(ruleCount)} active rule${ruleCount === 1 ? "" : "s"}</b>
      </section>

      <form id="customerRouteRuleFormModal" class="customer-route-modal-form">
        <label>
          <span>New customer / job match text</span>
          <input id="customerRoutePatternInputModal" type="text" autocomplete="off" placeholder="Example: Lowe's, CPU AIR, Greenville">
        </label>

        <label>
          <span>New route code</span>
          <input id="customerRouteSelectModal" type="text" list="customerRouteCodes" autocomplete="off" placeholder="CPU, DTC, GNV, or custom route">
        </label>
        <datalist id="customerRouteCodes">
          ${customerRouteOptionsHtml("CPU")}
        </datalist>

        <div class="customer-route-modal-actions">
          <button id="customerRouteSubmitBtnModal" type="submit">Add Customer Route</button>
        </div>
      </form>

      <div class="customer-route-modal-list">
        <div class="customer-route-modal-list-heading">
          <strong>Current customer rules</strong>
          <span>Change the route dropdown, then use the save icon on that row.</span>
        </div>

        ${customerRouteRuleRowsHtml(true)}
      </div>
    </div>
  `;
}

function setCustomerRouteEditForm(ruleId = "") {
  const form = document.getElementById("customerRouteRuleFormModal");
  if (!form) return;

  const rule = state.adminCustomerRouteRules.find((item) => String(item.id) === String(ruleId)) || null;
  const idInput = document.getElementById("customerRouteEditIdModal");
  const originalPatternInput = document.getElementById("customerRouteEditOriginalPatternModal");
  const patternInput = document.getElementById("customerRoutePatternInputModal");
  const routeInput = document.getElementById("customerRouteSelectModal");
  const submitButton = document.getElementById("customerRouteSubmitBtnModal");

  if (idInput) idInput.value = rule?.id || "";
  if (originalPatternInput) originalPatternInput.value = rule?.customerPattern || "";
  if (patternInput) patternInput.value = rule?.customerPattern || "";
  if (routeInput) routeInput.value = customerRouteValue(rule?.route || "CPU");
  if (submitButton) submitButton.textContent = rule ? "Save Rule" : "Add Rule";

  patternInput?.focus();
}

function renderCustomerRouteRules() {
  if (!els.customerRouteRules) return;

  const rules = state.adminCustomerRouteRules || [];
  const previewLimit = 6;
  const hiddenCount = Math.max(rules.length - previewLimit, 0);

  const routeStats = customerRouteOptionList()
    .map((option) => {
      const count = rules.filter((rule) => customerRouteValue(rule.route) === option.value).length;
      if (!count) return "";

      return `
        <div class="customer-route-stat">
          <small>${escapeHtml(option.label)}</small>
          <strong>${escapeHtml(count)}</strong>
        </div>
      `;
    })
    .filter(Boolean)
    .join("");

  els.customerRouteRules.innerHTML = `
    <div class="customer-route-overview">
      <div class="customer-route-overview-heading">
        <strong>${escapeHtml(rules.length)} customer route rule${rules.length === 1 ? "" : "s"}</strong>
        <span>Quick view of customers that will be split to special/custom stages during import.</span>
      </div>

      <div class="customer-route-stat-grid">
        ${routeStats || `<div class="customer-route-stat"><small>No route rules yet</small><strong>0</strong></div>`}
      </div>

      <div class="customer-route-preview-list">
        ${customerRouteRuleRowsHtml(false, previewLimit)}
      </div>

      ${
        hiddenCount
          ? `<button type="button" class="link-button customer-route-more-button" data-admin-modal="customerRoutes">View ${escapeHtml(hiddenCount)} more rule${hiddenCount === 1 ? "" : "s"}</button>`
          : ""
      }
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
  const usernameInput = document.getElementById("newUserNameModal") || els.newUserName;
  const displayInput = document.getElementById("newUserDisplayModal") || els.newUserDisplay;
  const passwordInput = document.getElementById("newUserPasswordModal") || els.newUserPassword;
  const roleInput = document.getElementById("newUserRoleModal") || els.newUserRole;
  const stationInput = document.getElementById("newUserStationModal");
  const username = usernameInput?.value.trim() || "";
  const displayName = displayInput?.value.trim() || username;
  const password = passwordInput?.value || "";
  const role = roleInput?.value || "Operator";
  const station = stationInput?.value || "";
  if (!username || !password) throw new Error("Username and password are required");
  await fetchJson("/api/admin/users", {
    method: "POST",
    body: JSON.stringify({ username, displayName, password, roles: [role], station }),
  });
  if (usernameInput) usernameInput.value = "";
  if (displayInput) displayInput.value = "";
  if (passwordInput) passwordInput.value = "";
  if (stationInput) stationInput.value = "";
  await refreshAdminPage();
  if (!els.adminModal?.hidden) openAdminModal("users");
}


async function runManualEditSearch() {
  const query = els.manualEditSearch?.value.trim() || "";
  if (query.length < 2 && !els.manualEditStageSelect?.value) return;
  renderManualEditResults(await fetchManualEditResults(query, els.manualEditStageSelect?.value || ""));
}

function renderManualEditResults(results) {
  if (!els.manualEditResults) return;
  els.manualEditResults.innerHTML = manualEditResultsHtml(results);
}

const MANUAL_EDIT_CUSTOM_VALUE = "__manual_edit_custom__";

function manualEditOptionHasValue(options, value) {
  const cleanValue = String(value ?? "");

  return options.some(([optionValue]) => String(optionValue ?? "") === cleanValue);
}

function lookupOptions(items = [], blankLabel = "Blank") {
  const seen = new Set();
  const options = [["", blankLabel]];
  for (const item of items || []) {
    const value = String(item.value ?? "").trim();
    if (!value || seen.has(value)) continue;
    seen.add(value);
    options.push([value, item.label || value]);
  }
  return options;
}

function manualEditIsCustomChoice(options, value) {
  const cleanValue = String(value ?? "").trim();

  return Boolean(cleanValue) && !manualEditOptionHasValue(options, cleanValue);
}

function manualEditSelectOptions(options, selectedValue = "", customLabel = "Custom value...") {
  const selected = String(selectedValue ?? "");
  const selectedIsCustom = manualEditIsCustomChoice(options, selected);
  const seen = new Set();

  const optionHtml = options
    .filter(([value]) => {
      const key = String(value ?? "");

      if (seen.has(key)) return false;

      seen.add(key);
      return true;
    })
    .map(([value, label]) => {
      const cleanValue = String(value ?? "");
      const isSelected = !selectedIsCustom && cleanValue === selected;

      return `<option value="${escapeHtml(cleanValue)}" ${isSelected ? "selected" : ""}>${escapeHtml(label)}</option>`;
    })
    .join("");

  return `
    ${optionHtml}
    <option value="${MANUAL_EDIT_CUSTOM_VALUE}" ${selectedIsCustom ? "selected" : ""}>${escapeHtml(customLabel)}</option>
  `;
}

function manualEditChoiceFieldHtml({ field, label, value = "", options = [], customLabel = "", wide = false }) {
  const cleanField = String(field || "");
  const cleanLabel = String(label || cleanField);
  const cleanValue = String(value ?? "");
  const customText = customLabel || `Custom ${cleanLabel.toLowerCase()}...`;
  const isCustom = manualEditIsCustomChoice(options, cleanValue);

  return `
    <label class="manual-field has-custom ${wide ? "wide" : ""}">
      <span>${escapeHtml(cleanLabel)}</span>

      <div class="manual-choice-control ${isCustom ? "is-custom" : ""}" data-choice-control data-choice-field="${escapeHtml(cleanField)}">
        <select
          class="manual-edit-select manual-edit-choice-select"
          data-choice-field="${escapeHtml(cleanField)}"
          aria-label="${escapeHtml(cleanLabel)} dropdown"
          title="${escapeHtml(cleanValue || cleanLabel)}"
          ${isCustom ? "hidden" : ""}
        >
          ${manualEditSelectOptions(options, cleanValue, customText)}
        </select>

        <div class="manual-custom-control" ${isCustom ? "" : "hidden"}>
          <input
            class="manual-edit-input manual-edit-custom-input"
            data-custom-field="${escapeHtml(cleanField)}"
            type="text"
            value="${escapeHtml(isCustom ? cleanValue : "")}"
            placeholder="${escapeHtml(customText.replace("...", ""))}"
            aria-label="Custom ${escapeHtml(cleanLabel)}"
          >
          <button
            type="button"
            class="manual-custom-clear"
            data-manual-custom-clear="${escapeHtml(cleanField)}"
            title="Back to ${escapeHtml(cleanLabel)} dropdown"
            aria-label="Back to ${escapeHtml(cleanLabel)} dropdown"
          >×</button>
        </div>

        <input data-edit-field="${escapeHtml(cleanField)}" type="hidden" value="${escapeHtml(cleanValue)}">
      </div>
    </label>
  `;
}

function manualEditChoiceHiddenInput(control) {
  const field = control?.dataset?.choiceField || "";

  return control?.querySelector(`[data-edit-field="${CSS.escape(field)}"]`) || null;
}

function manualEditSetChoiceValue(control, value, markDirty = true) {
  const hiddenInput = manualEditChoiceHiddenInput(control);

  if (!hiddenInput) return;

  hiddenInput.value = value;

  if (markDirty) {
    state.manualEditDirty = true;
    hiddenInput.dispatchEvent(new Event("input", { bubbles: true }));
  }
}

function manualEditShowCustomChoice(control, startingValue = "") {
  if (!control) return;

  const select = control.querySelector(".manual-edit-choice-select");
  const customWrap = control.querySelector(".manual-custom-control");
  const customInput = control.querySelector(".manual-edit-custom-input");

  control.classList.add("is-custom");

  if (select) {
    select.hidden = true;
    select.value = MANUAL_EDIT_CUSTOM_VALUE;
  }

  if (customWrap) customWrap.hidden = false;

  if (customInput) {
    customInput.value = startingValue;
    manualEditSetChoiceValue(control, startingValue, false);
    window.setTimeout(() => customInput.focus(), 20);
  }
}

function manualEditShowSelectChoice(control) {
  if (!control) return;

  const select = control.querySelector(".manual-edit-choice-select");
  const customWrap = control.querySelector(".manual-custom-control");
  const customInput = control.querySelector(".manual-edit-custom-input");

  control.classList.remove("is-custom");

  if (customInput) customInput.value = "";
  if (customWrap) customWrap.hidden = true;

  if (select) {
    select.hidden = false;

    if (select.value === MANUAL_EDIT_CUSTOM_VALUE) {
      select.value = "";
    }

    manualEditSetChoiceValue(control, select.value, true);
    window.setTimeout(() => select.focus(), 20);
  }
}

function manualEditApplyChoiceSelect(select) {
  const control = select?.closest("[data-choice-control]");

  if (!control) return;

  if (select.value === MANUAL_EDIT_CUSTOM_VALUE) {
    manualEditShowCustomChoice(control, "");
    state.manualEditDirty = true;
    return;
  }

  manualEditSetChoiceValue(control, select.value, true);
}

function manualEditApplyCustomInput(customInput) {
  const control = customInput?.closest("[data-choice-control]");

  if (!control) return;

  manualEditSetChoiceValue(control, customInput.value, false);
  state.manualEditDirty = true;
}

function manualEditClearCustomChoice(button) {
  const control = button?.closest("[data-choice-control]");

  if (!control) return;

  manualEditShowSelectChoice(control);
  state.manualEditDirty = true;
}

function manualEditSyncChoiceSelect(input) {
  const field = input?.dataset?.editField || "";
  const row = input?.closest("[data-edit-row]");
  const control = row?.querySelector(`[data-choice-control][data-choice-field="${CSS.escape(field)}"]`);
  const select = control?.querySelector(".manual-edit-choice-select");

  if (!control || !select) return;

  const value = String(input.value ?? "");
  const hasMatchingOption = [...select.options].some((option) => option.value === value);

  if (value && !hasMatchingOption) {
    manualEditShowCustomChoice(control, value);
    return;
  }

  manualEditShowSelectChoice(control);
  select.value = hasMatchingOption ? value : "";
}

function manualEditCurrentLocationValue(item) {
  return String(item.location || item.rackCode || item.bayCode || "").trim();
}

function manualEditLocationOptions(item) {
  const options = [
    ["", "No location / clear"],
    ["T", "Truck / no rack"],
  ];

  const racks = (state.racks || [])
    .slice()
    .sort((a, b) => {
      if (a.code === "T") return -1;
      if (b.code === "T") return 1;

      return String(a.code || "").localeCompare(String(b.code || ""), undefined, { numeric: true });
    });

  for (const rack of racks) {
    const code = String(rack.code || "").trim();

    if (!code) continue;

    const name = rack.name || rack.type || "Rack";
    const qty = Number(rack.qty || 0);
    const status = String(rack.status || "Open");

    options.push([
      code,
      code === "T"
        ? `T - Truck / no rack (${qty} pcs)`
        : `${code} - ${name} (${qty} pcs, ${status})`,
    ]);
  }

  const bays = (state.bays || [])
    .slice()
    .sort((a, b) => String(a.bayCode || a.code || "").localeCompare(String(b.bayCode || b.code || ""), undefined, { numeric: true }));

  for (const bay of bays) {
    const bayCode = String(bay.bayCode || bay.code || "").trim();

    if (!bayCode) continue;

    options.push([
      bayCode,
      `Bay ${bay.displayName || bayCode}`,
    ]);
  }

  return options;
}

function manualEditRouteOptions() {
  const lookupRoutes = lookupOptions(state.manualEditLookups?.routes || [], "Indian Trail / Standard");
  if (lookupRoutes.length > 1) return lookupRoutes;
  return [
    ["", "Indian Trail / Standard"],
    ["CPU", "Customer Pickup"],
    ["GNV", "Greenville"],
    ["DTC", "Deliver to Customer"],
  ];
}

function manualEditProcessOptions() {
  const lookupProcesses = lookupOptions(state.manualEditLookups?.processes || [], "Normal / blank");
  if (lookupProcesses.length > 1) return lookupProcesses;
  return [
    ["", "Normal / blank"],
    ["New", "New"],
    ["Updated", "Updated"],
    ["Rush", "Rush"],
    ["Remake", "Remake"],
    ["SDI", "SDI"],
    ["Review", "Needs Review"],
  ];
}

function manualEditProductOptions(results = []) {
  const productValues = uniqueText([
    ...(state.manualEditLookups?.products || []).map((item) => item.value),
    ...results.map((item) => item.product),
    ...state.items.map((item) => item.product),
    ...state.lists.flatMap((list) => list.items || []).map((item) => item.product),
  ]).sort((a, b) => a.localeCompare(b));

  return [
    ["", "Blank product"],
    ...productValues.map((value) => {
      const lookup = (state.manualEditLookups?.products || []).find((item) => String(item.value) === String(value));
      return [value, lookup?.label || value];
    }),
  ];
}

function manualEditSetRowError(row, message = "") {
  if (!row) return;

  const errorBox = row.querySelector(".manual-edit-row-error");

  row.classList.toggle("is-invalid", Boolean(message));

  row.querySelectorAll(".manual-edit-input.is-invalid, .manual-edit-select.is-invalid").forEach((field) => {
    field.classList.remove("is-invalid");
  });

  if (errorBox) {
    errorBox.hidden = !message;
    errorBox.textContent = message;
  }
}

function manualEditValidateRow(row) {
  if (!row) return false;

  const qtyInput = row.querySelector('[data-edit-field="qty"]');
  const scannedInput = row.querySelector('[data-edit-field="scanned"]');

  if (!qtyInput || !scannedInput) {
    manualEditSetRowError(row, "");
    return true;
  }

  const qty = Number(qtyInput.value || 0);
  const scanned = Number(scannedInput.value || 0);

  scannedInput.max = String(Math.max(qty, 0));

  if (!Number.isFinite(qty) || qty < 0) {
    qtyInput.classList.add("is-invalid");
    manualEditSetRowError(row, "Qty must be zero or greater.");
    return false;
  }

  if (!Number.isFinite(scanned) || scanned < 0) {
    scannedInput.classList.add("is-invalid");
    manualEditSetRowError(row, "Scanned quantity must be zero or greater.");
    return false;
  }

  if (scanned > qty) {
    scannedInput.classList.add("is-invalid");
    manualEditSetRowError(row, "Scanned quantity cannot be greater than Qty.");
    return false;
  }

  manualEditSetRowError(row, "");

  return true;
}

function manualEditResultsHtml(results) {
  const visibleRows = results.slice(0, 100);

  return results.length
    ? `
      <div class="manual-edit-result-summary">
        <span>Showing ${escapeHtml(visibleRows.length)} of ${escapeHtml(results.length)} row${results.length === 1 ? "" : "s"}</span>
        <small>Choose from dropdowns or type a custom value.</small>
      </div>

      <div class="manual-edit-card-list">
        ${visibleRows
          .map((item) => {
            const rowLabel = `${item.order || ""}-${item.item || ""}`;
            const stageText = item.stage || item.deliveryLabel || "";
            const qtyValue = Math.max(Number(item.qty || 0), 0);
            const scannedValue = Math.min(Math.max(Number(item.scanned || 0), 0), qtyValue);
            const locationValue = manualEditCurrentLocationValue(item);

            return `
              <article class="manual-edit-card" data-edit-row="${escapeHtml(item.lineItemId)}">
                <header class="manual-edit-card-header">
                  <div class="manual-edit-card-title">
                    <strong>${escapeHtml(item.order)}-${escapeHtml(item.item)}</strong>
                    <span>${escapeHtml(item.customer || "")}</span>
                  </div>

                  <div class="manual-edit-card-stage" title="${escapeHtml(stageText)}">
                    <span>Stage</span>
                    <strong>${escapeHtml(stageText || "No stage")}</strong>
                  </div>

                  <div class="manual-edit-row-actions">
                    <button
                      type="button"
                      class="icon-only icon-save manual-edit-action-button"
                      data-save-line-item="${escapeHtml(item.lineItemId)}"
                      title="Save ${escapeHtml(rowLabel)}"
                      aria-label="Save ${escapeHtml(rowLabel)}"
                    ></button>
                    <button
                      type="button"
                      class="icon-only icon-trash danger manual-edit-action-button"
                      data-delete-line-item="${escapeHtml(item.lineItemId)}"
                      title="Delete ${escapeHtml(rowLabel)}"
                      aria-label="Delete ${escapeHtml(rowLabel)}"
                    ></button>
                  </div>
                </header>

                <div class="manual-edit-card-grid">

                  <label class="manual-field">
                    <span>Order</span>
                    <input class="manual-edit-input" data-edit-field="order" type="text" value="${escapeHtml(item.order)}">
                  </label>

                  <label class="manual-field small">
                    <span>Item</span>
                    <input class="manual-edit-input" data-edit-field="item" type="text" value="${escapeHtml(item.item)}">
                  </label>

                  <label class="manual-field wide">
                    <span>Customer</span>
                    <input class="manual-edit-input" data-edit-field="customer" type="text" value="${escapeHtml(item.customer)}">
                  </label>

                  <label class="manual-field small">
                    <span>Qty</span>
                    <input class="manual-edit-input" data-edit-field="qty" type="number" min="0" value="${escapeHtml(qtyValue)}">
                  </label>

                  <label class="manual-field small">
                    <span>Scanned</span>
                    <input class="manual-edit-input" data-edit-field="scanned" type="number" min="0" max="${escapeHtml(qtyValue)}" value="${escapeHtml(scannedValue)}">
                  </label>

                  ${manualEditChoiceFieldHtml({
                    field: "location",
                    label: "Location",
                    value: locationValue,
                    options: manualEditLocationOptions(item),
                    customLabel: "Custom location...",
                  })}

                  ${manualEditChoiceFieldHtml({
                    field: "route",
                    label: "Route",
                    value: item.route || "",
                    options: manualEditRouteOptions(),
                    customLabel: "Custom route...",
                  })}

                  ${manualEditChoiceFieldHtml({
                    field: "processState",
                    label: "Process",
                    value: item.processState || "",
                    options: manualEditProcessOptions(),
                    customLabel: "Custom process...",
                  })}

                  ${manualEditChoiceFieldHtml({
                    field: "product",
                    label: "Product",
                    value: item.product || "",
                    options: manualEditProductOptions(visibleRows),
                    customLabel: "Custom product...",
                    wide: true,
                  })}

                  <label class="manual-field wide">
                    <span>Dimensions</span>
                    <input class="manual-edit-input" data-edit-field="dimensions" type="text" value="${escapeHtml(item.dimensions || "")}">
                  </label>

                  <label class="manual-field wide">
                    <span>Job</span>
                    <input class="manual-edit-input" data-edit-field="job" type="text" value="${escapeHtml(item.job || "")}">
                  </label>

                  <input data-edit-field="queueState" type="hidden" value="${escapeHtml(item.queueState || "")}">
                </div>

                <div class="manual-edit-row-error" hidden aria-live="polite"></div>
              </article>
            `;
          })
          .join("")}
      </div>
    `
    : `<div class="admin-empty">No editable rows found.</div>`;
}

async function saveManualLineItem(lineItemId) {
  const row = document.querySelector(`[data-edit-row="${CSS.escape(lineItemId)}"]`);

  if (!row) return;

  if (!manualEditValidateRow(row)) {
    row.querySelector(".is-invalid")?.focus();
    return;
  }

  const data = { lineItemId };

  row.querySelectorAll("[data-edit-field]").forEach((input) => {
    data[input.dataset.editField] = input.value;
  });

  const payload = await fetchJson("/api/admin/line-item", {
    method: "POST",
    body: JSON.stringify(data),
  });

  if (payload.meta?.id === state.activeListId) {
    applyBackendPayload(payload);
  }

  if (!els.adminModal?.hidden && state.manualEditListId) {
    await runManualEditModalSearch(!state.manualEditQuery);
  } else {
    await runManualEditSearch();
  }

  state.manualEditDirty = false;
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
  if (!els.adminModal?.hidden && state.manualEditListId) await runManualEditModalSearch(!state.manualEditQuery);
  else await runManualEditSearch();
  state.manualEditDirty = false;
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
  els.viewAllRecent?.addEventListener("click", () => openAdminModal("recentScans"));
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
  document.addEventListener("input", (event) => {
    const modalSearch = event.target.closest("#adminDeliveryListModalSearch");
    if (!modalSearch) return;

    const target = document.getElementById("adminDeliveryListModalResults");
    const searchBox = modalSearch.closest(".admin-modal-search");
    const query = modalSearch.value.trim();

    window.clearTimeout(state.adminListSearchTimer);

    searchBox?.classList.add("is-searching");
    target?.classList.add("is-searching");

    state.adminListSearchTimer = window.setTimeout(() => {
      searchAdminDeliveryLists(query)
        .then((filtered) => {
          const stillCurrent = document.getElementById("adminDeliveryListModalSearch")?.value.trim() === query;

          if (target && stillCurrent) {
            target.innerHTML = deliveryListAdminRows(filtered, filtered.length || 1, true);
          }
        })
        .catch((error) => {
          if (target) {
            target.innerHTML = `<div class="admin-empty">Search failed: ${escapeHtml(error.message)}</div>`;
          }
        })
        .finally(() => {
          const stillCurrent = document.getElementById("adminDeliveryListModalSearch")?.value.trim() === query;

          if (stillCurrent) {
            searchBox?.classList.remove("is-searching");
            target?.classList.remove("is-searching");
          }
        });
    }, 180);
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
  els.printOptionsStages?.addEventListener("change", (event) => {
    const allInput = event.target.closest("[data-print-stage-select-all]");

    if (allInput && els.printOptionsStages.contains(allInput)) {
      selectedPrintStageInputs().forEach((stageInput) => {
        stageInput.checked = allInput.checked;
      });
    }

    updatePrintStageSelectState();
    void renderPrintGlassTypes();
  });
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
  els.rackListSelect?.addEventListener("change", () => {
    state.rackScanListId = els.rackListSelect.value;
  });
  els.rackSelect?.addEventListener("change", () => {
    state.selectedRackCode = els.rackSelect.value;
  });
  els.scanRackSelect?.addEventListener("change", () => {
    state.selectedRackCode = els.scanRackSelect.value;
    renderScanRackTools();
  });
  els.scanRackCompleteBtn?.addEventListener("click", async () => {
    if (!state.selectedRackCode) return;
    try {
      const selectedRack = state.racks.find((rack) => rack.code === state.selectedRackCode);
      if (String(selectedRack?.status || "").toLowerCase() === "closed") {
        await uncompleteRack(state.selectedRackCode);
      } else {
        await completeRack(state.selectedRackCode);
      }
      await ensureRacksLoaded();
      renderScanRackTools();
    } catch (error) {
      showInlineError(error.message, true);
    }
  });
  els.scanRackPrintBtn?.addEventListener("click", () => printSelectedRackPackingSlip());
  els.rackScanForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      await submitRackScan();
    } catch (error) {
      showInlineError(error.message, true);
    }
  });
  els.rackGrid?.addEventListener("toggle", (event) => {
    const group = event.target.closest?.("[data-rack-group]");
    if (group && event.target === group) {
      const label = group.dataset.rackGroup || "";
      if (group.open) state.expandedRackGroups.add(label);
      else state.expandedRackGroups.delete(label);
      return;
    }
    const rack = event.target.closest?.("[data-rack-code]");
    if (rack && event.target === rack) {
      const code = rack.dataset.rackCode || "";
      if (rack.open) state.expandedRackCodes.add(code);
      else state.expandedRackCodes.delete(code);
    }
  }, true);
  els.rackGrid?.addEventListener("click", (event) => {
    const printButton = event.target.closest("[data-rack-print]");
    if (printButton) {
      event.preventDefault();
      event.stopPropagation();

      const rack = state.racks.find((item) => item.code === printButton.dataset.rackPrint);

      if (!rack || String(rack.status || "").toLowerCase() !== "closed") {
        showFloatingNotice("Complete this rack before printing its packing list.", "notice");
        return;
      }

      window.open(rackPackingListUrl(printButton.dataset.rackPrint, printButton.dataset.rackPrintDate || ""), "_blank", "noopener");

      return;
    }

    const completeButton = event.target.closest("[data-rack-complete]");
    if (completeButton) {
      event.preventDefault();
      event.stopPropagation();

      completeRack(completeButton.dataset.rackComplete).catch((error) => showInlineError(error.message, true));

      return;
    }

    const uncompleteButton = event.target.closest("[data-rack-uncomplete]");
    if (uncompleteButton) {
      event.preventDefault();
      event.stopPropagation();

      uncompleteRack(uncompleteButton.dataset.rackUncomplete).catch((error) => showInlineError(error.message, true));

      return;
    }

    const clearButton = event.target.closest("[data-rack-clear]");
    if (clearButton) {
      event.preventDefault();
      event.stopPropagation();

      clearRack(clearButton.dataset.rackClear).catch((error) => showInlineError(error.message, true));

      return;
    }

    const rackManagerNewRackButton = event.target.closest("[data-rack-manager-new-rack]");
    if (rackManagerNewRackButton) {
      event.preventDefault();
      event.stopPropagation();

      openRackForm("");

      return;
    }

    const rackManagerNewSetButton = event.target.closest("[data-rack-manager-new-set]");
    if (rackManagerNewSetButton) {
      event.preventDefault();
      event.stopPropagation();

      openRackSetForm("");

      return;
    }

    const deleteRackButton = event.target.closest("[data-rack-delete]");
    if (deleteRackButton) {
      event.preventDefault();
      event.stopPropagation();

      deleteRackDefinition(deleteRackButton.dataset.rackDelete || "").catch((error) => showInlineError(error.message, true));

      return;
    }

    const editRackButton = event.target.closest("[data-rack-edit]");
    if (editRackButton) {
      event.preventDefault();
      event.stopPropagation();

      openRackForm(editRackButton.dataset.rackEdit || "");

      return;
    }

    const editRackSetButton = event.target.closest("[data-rack-set-edit]");
    if (editRackSetButton) {
      event.preventDefault();
      event.stopPropagation();

      openRackSetForm(editRackSetButton.dataset.rackSetEdit || "");

      return;
    }

    const deleteRackSetButton = event.target.closest("[data-rack-set-delete]");
    if (deleteRackSetButton) {
      event.preventDefault();
      event.stopPropagation();

      deleteRackSet(deleteRackSetButton.dataset.rackSetDelete || "").catch((error) => showInlineError(error.message, true));

      return;
    }

    const clearRackSetButton = event.target.closest("[data-rack-set-clear]");
    if (clearRackSetButton) {
      event.preventDefault();
      event.stopPropagation();

      clearRackSet(clearRackSetButton.dataset.rackSetClear || "").catch((error) => showInlineError(error.message, true));

      return;
    }

    const moveOpenButton = event.target.closest("[data-rack-move-open]");
    if (moveOpenButton) {
      event.preventDefault();
      event.stopPropagation();

      const rackItemId = moveOpenButton.dataset.rackMoveOpen || "";
      state.rackMoveItemId = state.rackMoveItemId === rackItemId ? "" : rackItemId;

      renderRacksPage();

      return;
    }

    const moveCancelButton = event.target.closest("[data-rack-move-cancel]");
    if (moveCancelButton) {
      event.preventDefault();
      event.stopPropagation();

      state.rackMoveItemId = "";

      renderRacksPage();

      return;
    }

    const moveButton = event.target.closest("[data-rack-move]");
    if (moveButton) {
      event.preventDefault();
      event.stopPropagation();

      moveRackItem(moveButton.dataset.rackMove).catch((error) => showInlineError(error.message, true));

      return;
    }

    const clearItemButton = event.target.closest("[data-rack-clear-item]");
    if (clearItemButton) {
      event.preventDefault();
      event.stopPropagation();

      clearRackItem(clearItemButton.dataset.rackClearItem, clearItemButton.dataset.rackClearLabel).catch((error) => showInlineError(error.message, true));

      return;
    }

    const rackSetCard = event.target.closest("[data-rack-set-select]");
    if (rackSetCard) {
      event.preventDefault();
      if (event.target.closest("[data-rack-set-clear]")) return;

      state.selectedRackSetLabel = rackSetCard.dataset.rackSetSelect || "";
      const matchingRacks = state.racks.filter((rack) => rackGroupLabel(rack) === state.selectedRackSetLabel);
      state.selectedRackOverviewCode = matchingRacks.find((rack) => Number(rack.qty || 0) > 0)?.code || matchingRacks[0]?.code || "";
      state.rackMoveItemId = "";

      renderRacksPage();

      return;
    }

    const rackSelectCard = event.target.closest("[data-rack-select]");
    if (rackSelectCard) {
      event.preventDefault();

      state.selectedRackOverviewCode = rackSelectCard.dataset.rackSelect || "";
      state.rackMoveItemId = "";

      renderRacksPage();

      return;
    }
  });

  els.rackGrid?.addEventListener("keydown", (event) => {
    const rackSelectCard = event.target.closest("[data-rack-select]");

    if (!rackSelectCard) return;
    if (!["Enter", " "].includes(event.key)) return;

    event.preventDefault();

    state.selectedRackOverviewCode = rackSelectCard.dataset.rackSelect || "";
    state.rackMoveItemId = "";

    renderRacksPage();
  });

  els.rackCreateOpenBtn?.addEventListener("click", () => openRackForm(""));
  els.rackSetCreateOpenBtn?.addEventListener("click", () => openRackSetForm(""));
  els.rackEditOpenBtn?.addEventListener("click", () => openAdminModal("racks"));

  els.folderImportBtn?.addEventListener("click", () => {
    importTempDeliveryFolder().catch((error) => showInlineError(error.message, true));
  });

  els.importWindowResetBtn?.addEventListener("click", () => resetImportDateWindow());

  els.deleteDateSelect?.addEventListener("change", () => renderAdminDeleteControls());
  els.deleteListBtn?.addEventListener("click", () => deleteSelectedDeliveryList(false).catch((error) => showInlineError(error.message, true)));
  els.deleteDateBtn?.addEventListener("click", () => deleteSelectedDeliveryList(true).catch((error) => showInlineError(error.message, true)));
  els.adminResetScansBtn?.addEventListener("click", () => resetSelectedAdminScans().catch((error) => showInlineError(error.message, true)));
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
  document.addEventListener("submit", (event) => {
    if (event.target.closest("#createUserFormModal")) {
      event.preventDefault();
      createUserFromForm().catch((error) => showInlineError(error.message));
      return;
    }
    if (event.target.closest("#rackFormModal")) {
      event.preventDefault();
      saveRackDefinition().catch((error) => showInlineError(error.message, true));
      return;
    }
    if (event.target.closest("#rackSetFormModal")) {
      event.preventDefault();
      createRackSet().catch((error) => showInlineError(error.message, true));
      return;
    }
    if (event.target.closest("#rackManagerQuickEditForm")) {
      event.preventDefault();
      saveRackQuickEdit().catch((error) => showInlineError(error.message, true));
      return;
    }
    if (event.target.closest("#manualLookupForm")) {
      event.preventDefault();
      saveManualEditLookup().catch((error) => showInlineError(error.message, true));
      return;
    }

    if (event.target.closest("#customerRouteRuleFormModal")) {
      event.preventDefault();
      saveCustomerRouteRule().catch((error) => showInlineError(error.message, true));
      return;
    }
  });
  els.customerRouteRuleForm?.addEventListener("submit", (event) => {
    event.preventDefault();
    saveCustomerRouteRule().catch((error) => showInlineError(error.message, true));
  });
  els.manualEditSearchBtn?.addEventListener("click", () => runManualEditSearch().catch((error) => showInlineError(error.message)));
  els.manualEditStageSelect?.addEventListener("change", () => {
    if ((els.manualEditSearch?.value.trim() || "").length >= 2) runManualEditSearch().catch((error) => showInlineError(error.message));
  });
  els.manualEditSearch?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      runManualEditSearch().catch((error) => showInlineError(error.message));
    }
  });
  document.addEventListener("input", (event) => {
    const customField = event.target.closest("#manualEditModalResults [data-custom-field]");

    if (customField) {
      manualEditApplyCustomInput(customField);
      return;
    }

    const editField = event.target.closest("#manualEditModalResults [data-edit-field]");

    if (!editField) return;

    state.manualEditDirty = true;

    const row = editField.closest("[data-edit-row]");

    if (editField.type !== "hidden") {
      manualEditSyncChoiceSelect(editField);
    }

    if (row && ["qty", "scanned"].includes(editField.dataset.editField)) {
      manualEditValidateRow(row);
    }
  });

  document.addEventListener("change", (event) => {
    const rackQuickSelect = event.target.closest("#rackManagerQuickRackSelect");

    if (rackQuickSelect) {
      populateRackManagerQuickEdit(rackQuickSelect.value);
      return;
    }

    const choiceSelect = event.target.closest("#manualEditModalResults .manual-edit-choice-select");

    if (choiceSelect) {
      manualEditApplyChoiceSelect(choiceSelect);
      state.manualEditDirty = true;
      return;
    }

    const editField = event.target.closest("#manualEditModalResults [data-edit-field]");

    if (editField) {
      state.manualEditDirty = true;

      const row = editField.closest("[data-edit-row]");

      if (editField.type !== "hidden") {
        manualEditSyncChoiceSelect(editField);
      }

      if (row && ["qty", "scanned"].includes(editField.dataset.editField)) {
        manualEditValidateRow(row);
      }

      return;
    }

    if (event.target.closest("#manualEditModalStage")) {
      if (state.manualEditDirty && !window.confirm("You have unsaved manual delivery-list edits. Load another stage without saving?")) {
        event.target.value = state.manualEditListId || "";
        return;
      }

      state.manualEditDirty = false;
      runManualEditModalSearch(true).catch((error) => showInlineError(error.message, true));
    }
  });
  document.addEventListener("keydown", (event) => {
    if (event.target.closest("#manualEditModalSearch") && event.key === "Enter") {
      event.preventDefault();
      runManualEditModalSearch(false).catch((error) => showInlineError(error.message, true));
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
  els.bayGlassFilter?.addEventListener("change", () => {
    state.bayGlassFilter = els.bayGlassFilter.value;
    renderBayMapPage();
  });
  els.baySpecialFilter?.addEventListener("change", () => {
    state.baySpecialFilter = els.baySpecialFilter.value;
    renderBayMapPage();
  });
  els.bayQuickFilters?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-bay-quick-filter]");
    if (!button) return;
    state.bayQuickFilter = button.dataset.bayQuickFilter || "all";
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
  els.staleBayCloseBtn?.addEventListener("click", () => closeStaleBayPanel());
  els.staleBayOkBtn?.addEventListener("click", () => closeStaleBayPanel());
  els.staleBayBackdrop?.addEventListener("click", () => closeStaleBayPanel());
  els.staleBayPrintBtn?.addEventListener("click", () => window.open("/api/indian-trail/stale-bays/print", "_blank", "noopener"));
  els.adminModalClose?.addEventListener("click", () => closeAdminModal());
  els.adminModalBackdrop?.addEventListener("click", () => closeAdminModal());
  els.staleBaySnoozeAllBtn?.addEventListener("click", () => {
    const ids = (state.staleBayOrders || []).map((order) => order.assignmentId).filter(Boolean);
    if (!ids.length) return;
    snoozeStaleBayOrders(ids, Number(els.staleBaySnoozeAllDays?.value || 1)).catch((error) => showInlineError(error.message, true));
  });
  els.staleBayList?.addEventListener("click", (event) => {
    const target = event.target.closest("[data-stale-snooze]");
    if (!target) return;
    const assignmentId = target.dataset.staleSnooze;
    const days = Number(els.staleBayList.querySelector(`[data-stale-days="${CSS.escape(String(assignmentId))}"]`)?.value || 1);
    snoozeStaleBayOrders([assignmentId], days).catch((error) => showInlineError(error.message, true));
  });
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
    if ((state.bayEditMode && state.bayHoldingSections.size) || state.manualEditDirty) {
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

    const rackHeaderAction = event.target.closest(".rack-summary-actions button");

    if (rackHeaderAction) {
      event.preventDefault();
    }

     const openGlassMenu = event.target.closest(".glass-filter-more");

    document.querySelectorAll(".glass-filter-more[open]").forEach((menu) => {
      if (menu !== openGlassMenu) {
        menu.open = false;
      }
    });

    document.addEventListener("toggle", (event) => {
    const roleCard = event.target.closest?.(".role-permission-card[data-role-card]");

    if (roleCard && els.adminModalBody?.contains(roleCard)) {
      const roleName = roleCard.dataset.roleCard || "";

      if (roleCard.open) {
        state.rolePermissionOpenRoles.add(roleName);
      } else {
        state.rolePermissionOpenRoles.delete(roleName);
      }

      return;
    }

    const category = event.target.closest?.(".permission-category[data-role-name][data-category-title]");

    if (category && els.adminModalBody?.contains(category)) {
      const key = rolePermissionCategoryKey(category.dataset.roleName, category.dataset.categoryTitle);

      if (category.open) {
        state.rolePermissionOpenCategories.add(key);
      } else {
        state.rolePermissionOpenCategories.delete(key);
      }
    }
  }, true);

    const pageButton = event.target.closest("[data-page-target]");
    if (pageButton) {
      if (state.manualEditDirty && !window.confirm("You have unsaved manual delivery-list edits. Leave without saving?")) return;
      state.manualEditDirty = false;
      showPage(pageButton.dataset.pageTarget);
      return;
    }
    const adminModalButton = event.target.closest("[data-admin-modal]");
    if (adminModalButton) {
      const modalKind = adminModalButton.dataset.adminModal || "";

      if (modalKind === "lookups") {
        ensureManualEditLookupsLoaded()
          .then(() => openAdminModal("lookups"))
          .catch((error) => showInlineError(error.message, true));
      } else if (modalKind === "customerRoutes") {
        fetchJson("/api/admin/customer-route-rules")
          .then((payload) => {
            state.adminCustomerRouteRules = payload.rules || [];
            openAdminModal("customerRoutes");
          })
          .catch((error) => showInlineError(error.message, true));
      } else if (modalKind === "deliveryLists" || modalKind === "deliveryActions") {
        loadDeliveryLists(state.activeListId)
          .then(() => openAdminModal(modalKind))
          .catch((error) => showInlineError(error.message, true));
      } else {
        openAdminModal(modalKind);
      }

      return;
    }
    const modalStationButton = event.target.closest("#addStationBtnModal");
    if (modalStationButton) {
      const input = document.getElementById("newStationInputModal");
      if (els.newStationInput && input) els.newStationInput.value = input.value;
      addStationFromInput()
        .then(() => openAdminModal("stations"))
        .catch((error) => showInlineError(error.message));
      return;
    }
    const manualCustomClearButton = event.target.closest("[data-manual-custom-clear]");
    if (manualCustomClearButton) {
      event.preventDefault();
      manualEditClearCustomChoice(manualCustomClearButton);
      return;
    }
    const manualEditBackButton = event.target.closest("[data-manual-edit-back]");
    if (manualEditBackButton) {
      event.preventDefault();

      if (state.manualEditDirty && !window.confirm("You have unsaved manual delivery-list edits. Go back without saving?")) {
        return;
      }

      state.manualEditDirty = false;
      openAdminModal("deliveryLists");

      return;
    }
    const manualModalSearchButton = event.target.closest("#manualEditModalSearchBtn");
    if (manualModalSearchButton) {
      runManualEditModalSearch(false).catch((error) => showInlineError(error.message, true));
      return;
    }
    const manualModalReloadButton = event.target.closest("#manualEditModalReloadBtn");
    if (manualModalReloadButton) {
      runManualEditModalSearch(true).catch((error) => showInlineError(error.message, true));
      return;
    }
    const adminReportButton = event.target.closest("[data-admin-report]");
    if (adminReportButton) {
      openPrintOptions({ date: dashboardDateKey(), listIds: state.lists.map((list) => list.id) });
      return;
    }
    const adminListEditButton = event.target.closest("[data-admin-list-edit]");
    if (adminListEditButton) {
      const listId = adminListEditButton.dataset.adminListEdit || "";
      if (els.manualEditStageSelect) els.manualEditStageSelect.value = listId;
      openManualEditForList(listId).catch((error) => showInlineError(error.message, true));
      return;
    }
    const adminDateResetButton = event.target.closest("[data-admin-date-reset]");
    if (adminDateResetButton) {
      event.preventDefault();
      event.stopPropagation();

      resetAdminScansForDate(adminDateResetButton.dataset.adminDateReset).catch((error) => showInlineError(error.message, true));

      return;
    }

    const adminDateDeleteButton = event.target.closest("[data-admin-date-delete]");
    if (adminDateDeleteButton) {
      event.preventDefault();
      event.stopPropagation();

      deleteAdminDeliveryDateByDate(adminDateDeleteButton.dataset.adminDateDelete).catch((error) => showInlineError(error.message, true));

      return;
    }
    const adminListResetButton = event.target.closest("[data-admin-list-reset]");
    if (adminListResetButton) {
      resetAdminScansForList(adminListResetButton.dataset.adminListReset).catch((error) => showInlineError(error.message, true));
      return;
    }
    const adminListDeleteButton = event.target.closest("[data-admin-list-delete]");
    if (adminListDeleteButton) {
      deleteAdminDeliveryListById(adminListDeleteButton.dataset.adminListDelete).catch((error) => showInlineError(error.message, true));
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
    const glassFilterButton = event.target.closest("[data-glass-filter]");
    if (glassFilterButton) {
      state.glassTypeFilter = glassFilterButton.dataset.glassFilter || "all";
      state.pageIndex = 1;
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
      const username = deactivateUserButton.dataset.deactivateUser || "";

      confirmDeactivateUser(username).then((confirmed) => {
        if (!confirmed) return;

        fetchJson("/api/admin/users/deactivate", {
          method: "POST",
          body: JSON.stringify({ username }),
        })
          .then(() => refreshAdminUsersUi())
          .catch((error) => showInlineError(error.message));
      });

      return;
    }

    const reactivateUserButton = event.target.closest("[data-reactivate-user]");
    if (reactivateUserButton) {
      const username = reactivateUserButton.dataset.reactivateUser || "";

      fetchJson("/api/admin/users/reactivate", {
        method: "POST",
        body: JSON.stringify({ username }),
      })
        .then(() => refreshAdminUsersUi())
        .catch((error) => showInlineError(error.message));

      return;
    }

    const deleteUserButton = event.target.closest("[data-delete-user]");
    if (deleteUserButton) {
      const username = deleteUserButton.dataset.deleteUser || "";
      const typed = window.prompt(`Delete user ${username}? Type DELETE USER to confirm.`);
      if (typed !== "DELETE USER") return;

      fetchJson("/api/admin/users/delete", {
        method: "POST",
        body: JSON.stringify({ username }),
      })
        .then(() => refreshAdminUsersUi())
        .catch((error) => showInlineError(error.message));

      return;
    }

    const generatePasswordButton = event.target.closest("[data-generate-user-password]");
    if (generatePasswordButton) {
      const username = generatePasswordButton.dataset.generateUserPassword;
      const input = document.querySelector(`[data-user-password="${CSS.escape(username)}"]`);

      if (input) {
        input.value = generateTemporaryPassword();
        input.type = "text";
        input.focus();
        input.select();
      }

      showFloatingNotice("Temporary password generated. Save it, then give it to the user.", "notice");

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
      const password = input?.value || "";

      if (!password.trim()) {
        showFloatingNotice("Enter or generate a new password before saving.", "notice");
        input?.focus();
        return;
      }

      fetchJson("/api/admin/users/password", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      })
        .then(() => {
          if (input) input.value = "";
          showFloatingNotice(`Password updated for ${username}.`, "success");
          return refreshAdminUsersUi();
        })
        .catch((error) => showInlineError(error.message));

      return;
    }

    const updateUserRoleButton = event.target.closest("[data-update-user-role]");
    if (updateUserRoleButton) {
      const username = updateUserRoleButton.dataset.updateUserRole;
      const select = document.querySelector(`[data-user-role-select="${CSS.escape(username)}"]`);
      const stationSelect = document.querySelector(`[data-user-station-select="${CSS.escape(username)}"]`);

      fetchJson("/api/admin/users/roles", {
        method: "POST",
        body: JSON.stringify({
          username,
          roles: [select?.value || "Operator"],
          station: stationSelect?.value || "",
        }),
      })
        .then(() => refreshAdminUsersUi())
        .catch((error) => showInlineError(error.message));

      return;
    }

    const saveRolePermissionsButton = event.target.closest("[data-save-role-permissions]");
    if (saveRolePermissionsButton) {
      event.preventDefault();
      event.stopPropagation();

      saveRolePermissions(saveRolePermissionsButton.dataset.saveRolePermissions).catch((error) => showInlineError(error.message, true));

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
    const saveCustomerRouteButton = event.target.closest("[data-save-customer-route-rule]");
    if (saveCustomerRouteButton) {
      saveCustomerRouteRuleRow(saveCustomerRouteButton.dataset.saveCustomerRouteRule).catch((error) => showInlineError(error.message, true));
      return;
    }

    const removeCustomerRouteButton = event.target.closest("[data-remove-customer-route-rule]");
    if (removeCustomerRouteButton) {
      removeCustomerRouteRule(removeCustomerRouteButton.dataset.removeCustomerRouteRule).catch((error) => showInlineError(error.message, true));
      return;
    }
    
    const printListsButton = event.target.closest("[data-print-lists]");
    if (printListsButton) {
      event.preventDefault();
      event.stopPropagation();

      const listIds = String(printListsButton.dataset.printLists || "")
        .split(",")
        .filter(Boolean);
      const firstList = state.lists.find((list) => list.id === listIds[0]);
      const date = printListsButton.dataset.printDate || firstList?.deliveryDate || selectedDeliveryDate();
      const updatedOnly = printListsButton.dataset.printUpdatedOnly === "1";

      if (listIds.length) {
        openPrintOptions({ date, listIds, updatedOnly });
      }

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
