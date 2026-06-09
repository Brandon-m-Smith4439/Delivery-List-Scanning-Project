const STORAGE_KEY = "delivery-list-scanner-demo-v1";
const STATIONS_KEY = "delivery-list-scanner-stations-v1";
const DEFAULT_STATIONS = ["Airport Rd", "Indian Trail", "Greenville", "Customer Pickup"];

const state = {
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
  auto: true,
  lastScan: null,
  backend: false,
};

const els = {
  pageTitle: document.getElementById("pageTitle"),
  stageSubtitle: document.getElementById("stageSubtitle"),
  stageHeading: document.getElementById("stageHeading"),
  scannerName: document.getElementById("scannerName"),
  deliveryListSelect: document.getElementById("deliveryListSelect"),
  progressText: document.getElementById("progressText"),
  progressFill: document.getElementById("progressFill"),
  searchInput: document.getElementById("searchInput"),
  scanForm: document.getElementById("scanForm"),
  scanInput: document.getElementById("scanInput"),
  listRows: document.getElementById("listRows"),
  recentRows: document.getElementById("recentRows"),
  mobileListCards: document.getElementById("mobileListCards"),
  alertsList: document.getElementById("alertsList"),
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
  refreshBtn: document.getElementById("refreshBtn"),
  autoToggle: document.getElementById("autoToggle"),
  resetBtn: document.getElementById("resetBtn"),
  undoBtn: document.getElementById("undoBtn"),
  loadExampleBtn: document.getElementById("loadExampleBtn"),
  importBtn: document.getElementById("importBtn"),
  importFile: document.getElementById("importFile"),
  printBtn: document.getElementById("printBtn"),
  exportBtn: document.getElementById("exportBtn"),
  bayGrid: document.getElementById("bayGrid"),
  bayStatus: document.getElementById("bayStatus"),
  backendStatus: document.getElementById("backendStatus"),
  operatorInput: document.getElementById("operatorInput"),
  stationSelect: document.getElementById("stationSelect"),
  newStationInput: document.getElementById("newStationInput"),
  addStationBtn: document.getElementById("addStationBtn"),
};

function formatDisplayDate(value) {
  const [year, month, day] = value.split("-").map(Number);
  return `${month}/${day}/${year}`;
}

function pad(value, length) {
  return String(value).padStart(length, "0");
}

function canonicalBarcode(order, item) {
  return `T200${pad(order, 6)}${pad(item, 3)}000`;
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

function storageKey() {
  return `${STORAGE_KEY}-${state.activeListId || "default"}`;
}

function cloneItems(items) {
  const seen = new Map();
  return items.map((item, index) => {
    const baseId = item.id || `${item.order}-${item.item}`;
    const count = seen.get(baseId) || 0;
    seen.set(baseId, count + 1);
    return {
      ...item,
      id: count ? `${baseId}-${count + 1}` : baseId,
      sourceId: baseId,
      lineIndex: index + 1,
      scanned: 0,
      lastError: "",
    };
  });
}

function requestContext() {
  return {
    user: els.operatorInput?.value || "Scanner",
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
    throw new Error(text || `Request failed: ${response.status}`);
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

function isCpuItem(item) {
  const route = String(item.route || "").trim().toUpperCase();
  const text = [item.route, item.job, item.customer, item.product, item.processState, item.queueState].join(" ");
  return route === "CPU" || /\bCPU\b/i.test(text);
}

function filterItemsForProfile(items, profile) {
  if (profile === "cpu") {
    return items.filter(isCpuItem);
  }
  return items.slice();
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
  const name = els.newStationInput.value.trim();
  if (!name) {
    els.newStationInput.focus();
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
  renderStationOptions(name);
  els.newStationInput.value = "";
  els.scanInput.focus();
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
  state.items = cloneItems(nextList.items);
  state.recent = [];
  state.errors = [];
  state.selectedId = null;
  state.lastScan = null;
  restoreState();
  renderStationOptions(nextList.scanner);
}

function applyBackendPayload(payload) {
  state.meta = payload.meta;
  state.activeListId = payload.meta.id;
  state.items = cloneItems(payload.items || []);
  for (let i = 0; i < state.items.length; i += 1) {
    state.items[i].scanned = Number((payload.items || [])[i]?.scanned || 0);
  }
  state.recent = payload.recent || [];
  state.errors = payload.errors || [];
  state.lastScan = payload.lastScan || state.recent[0] || null;
  state.selectedId = state.lastScan?.item?.id || state.selectedId;
  if (els.stationSelect) {
    renderStationOptions(payload.meta.scanner);
  }
}

async function loadBackendLists(preferredListId) {
  const payload = await fetchJson("/api/delivery-lists");
  state.lists = payload.lists || [];
  const listId = preferredListId || state.lists[0]?.id;
  if (listId) {
    await activateList(listId);
  }
}

async function activateList(listId) {
  if (state.backend) {
    const payload = await fetchJson(`/api/delivery-lists/${encodeURIComponent(listId)}`);
    applyBackendPayload(payload);
    return;
  }
  setActiveList(listId);
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

function buildIndexes() {
  const byOrderItem = new Map();
  const bySuffixItem = new Map();

  for (const item of state.items) {
    const orderItemKey = `${Number(item.order)}-${Number(item.item)}`;
    const orderMatches = byOrderItem.get(orderItemKey) || [];
    orderMatches.push(item);
    byOrderItem.set(orderItemKey, orderMatches);

    const suffixKey = `${pad(item.order, 6).slice(-3)}-${Number(item.item)}`;
    const existing = bySuffixItem.get(suffixKey) || [];
    existing.push(item);
    bySuffixItem.set(suffixKey, existing);
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
    if (matches.length === 1) {
      return { ok: true, item: matches[0], barcode: cleanText, reason: "Exact label" };
    }
    if (matches.length > 1) {
      return { ok: false, barcode: cleanText, reason: "Ambiguous delivery-list match" };
    }
  }

  const numbers = digitsOnly(cleanText);
  for (let start = 0; start <= numbers.length - 12; start += 1) {
    const windowText = numbers.slice(start, start + 12);
    const order = Number(windowText.slice(0, 6));
    const item = Number(windowText.slice(6, 9));
    const matches = byOrderItem.get(`${order}-${item}`) || [];
    if (matches.length === 1) {
      return {
        ok: true,
        item: matches[0],
        barcode: canonicalBarcode(order, item),
        reason: "Recovered order/item",
      };
    }
    if (matches.length > 1) {
      return { ok: false, barcode: canonicalBarcode(order, item), reason: "Ambiguous delivery-list match" };
    }
  }

  for (let start = 0; start <= numbers.length - 9; start += 1) {
    const windowText = numbers.slice(start, start + 9);
    const suffix = windowText.slice(0, 3);
    const itemNumber = Number(windowText.slice(3, 6));
    const matches = bySuffixItem.get(`${suffix}-${itemNumber}`);
    if (matches && matches.length === 1) {
      const match = matches[0];
      return {
        ok: true,
        item: match,
        barcode: canonicalBarcode(match.order, itemNumber),
        reason: "Recovered suffix/item",
      };
    }
    if (matches && matches.length > 1) {
      return { ok: false, barcode: cleanText, reason: "Ambiguous delivery-list match" };
    }
  }

  return { ok: false, barcode: cleanText, reason: "No unique delivery-list match" };
}

function itemStatus(item) {
  if (item.scanned >= item.qty) return "complete";
  if (item.scanned > 0) return "partial";
  return "remaining";
}

function getStats() {
  const totalQty = state.items.reduce((sum, item) => sum + item.qty, 0);
  const scannedQty = state.items.reduce((sum, item) => sum + Math.min(item.scanned, item.qty), 0);
  const remainingQty = Math.max(totalQty - scannedQty, 0);
  const partialItems = state.items.filter((item) => itemStatus(item) === "partial").length;
  const completeItems = state.items.filter((item) => itemStatus(item) === "complete").length;
  const remainingItems = state.items.filter((item) => itemStatus(item) === "remaining").length;
  const percent = totalQty ? (scannedQty / totalQty) * 100 : 0;
  return {
    totalQty,
    scannedQty,
    remainingQty,
    partialItems,
    completeItems,
    remainingItems,
    percent,
    errorCount: state.errors.length,
  };
}

function visibleItems() {
  const search = state.search.trim().toLowerCase();
  return state.items.filter((item) => {
    const status = itemStatus(item);
    const matchesFilter =
      state.filter === "all" ||
      state.filter === status ||
      (state.filter === "errors" && item.lastError);
    if (!matchesFilter) return false;

    if (!search) return true;
    const haystack = [
      item.order,
      item.item,
      item.job,
      item.customer,
      item.dimensions,
      item.product,
      item.route,
      item.barcode,
    ]
      .join(" ")
      .toLowerCase();
    return haystack.includes(search);
  });
}

function saveState() {
  if (state.backend) return;
  const payload = {
    scanned: Object.fromEntries(state.items.map((item) => [item.id, item.scanned])),
    recent: state.recent,
    errors: state.errors,
    selectedId: state.selectedId,
    auto: state.auto,
    lastScan: state.lastScan,
  };
  localStorage.setItem(storageKey(), JSON.stringify(payload));
}

function restoreState() {
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
    state.auto = saved.auto !== false;
    state.lastScan = saved.lastScan || null;
  } catch {
    localStorage.removeItem(storageKey());
  }
}

async function resetState() {
  if (state.backend) {
    const payload = await fetchJson("/api/reset", {
      method: "POST",
      body: JSON.stringify({ listId: state.activeListId, ...requestContext() }),
    });
    applyBackendPayload(payload);
    render();
    els.scanInput.focus();
    return;
  }

  for (const item of state.items) {
    item.scanned = 0;
    item.lastError = "";
  }
  state.recent = [];
  state.errors = [];
  state.selectedId = null;
  state.lastScan = null;
  saveState();
  render();
  els.scanInput.focus();
}

function setLastScan(entry) {
  state.lastScan = entry;
  els.lastCard.classList.remove("ok", "error");
  els.lastCard.classList.add(entry.ok ? "ok" : "error");
  els.lastScanTime.textContent = entry.ok ? "Just now" : "Needs review";
  els.lastJob.textContent = entry.item ? entry.item.job : entry.message;
  els.lastOrder.textContent = entry.item ? entry.item.order : "-";
  els.lastItem.textContent = entry.item ? entry.item.item : "-";
  els.lastQty.textContent = entry.item ? String(entry.item.scanned) : "-";
  els.lastDims.textContent = entry.item ? entry.item.dimensions : "-";
  els.lastCustomer.textContent = entry.item ? entry.item.customer : "-";
}

async function processScan(rawScan) {
  const scanText = rawScan.trim();
  if (!scanText) return;

  if (state.backend) {
    const payload = await fetchJson("/api/scans", {
      method: "POST",
      body: JSON.stringify({ listId: state.activeListId, barcode: scanText, ...requestContext() }),
    });
    applyBackendPayload(payload);
    render();
    return;
  }

  const recovered = recoverScan(scanText);
  const timestamp = new Date();

  if (!recovered.ok) {
    const entry = {
      ok: false,
      barcode: scanText,
      message: "BAD SCAN format",
      reason: recovered.reason,
      time: timestamp.toISOString(),
    };
    state.errors.unshift(entry);
    state.errors = state.errors.slice(0, 30);
    state.recent.unshift(entry);
    state.recent = state.recent.slice(0, 30);
    setLastScan(entry);
    saveState();
    render();
    return;
  }

  const item = recovered.item;
  if (item.scanned >= item.qty) {
    const entry = {
      ok: false,
      barcode: recovered.barcode,
      item,
      message: "Item already complete",
      reason: "Quantity already scanned",
      time: timestamp.toISOString(),
    };
    item.lastError = entry.reason;
    state.errors.unshift(entry);
    state.errors = state.errors.slice(0, 30);
    state.recent.unshift(entry);
    state.recent = state.recent.slice(0, 30);
    state.selectedId = item.id;
    setLastScan(entry);
    saveState();
    render();
    return;
  }

  item.scanned += 1;
  item.lastError = "";
  state.selectedId = item.id;

  const entry = {
    ok: true,
    barcode: recovered.barcode,
    raw: scanText,
    item,
    message: recovered.reason,
    time: timestamp.toISOString(),
  };
  state.recent.unshift(entry);
  state.recent = state.recent.slice(0, 30);
  setLastScan(entry);
  saveState();
  render();
}

function renderCounts() {
  const stats = getStats();
  const totalItems = state.items.length;
  els.countAll.textContent = `(${totalItems})`;
  els.countRemaining.textContent = `(${stats.remainingItems})`;
  els.countPartial.textContent = `(${stats.partialItems})`;
  els.countComplete.textContent = `(${stats.completeItems})`;
  els.countErrors.textContent = `(${stats.errorCount})`;
  els.totalItemsText.textContent = `${totalItems} total items`;

  els.progressText.textContent = `Staged Qty: ${stats.scannedQty}/${stats.totalQty} - ${stats.percent.toFixed(1)}% Complete`;
  els.progressFill.style.width = `${Math.min(stats.percent, 100)}%`;

  els.remainingQty.textContent = String(stats.remainingQty);
  els.partialQty.textContent = String(stats.partialItems);
  els.completeQty.textContent = String(stats.completeItems);
  els.errorQty.textContent = String(stats.errorCount);
  els.remainingPct.textContent = `${(100 - stats.percent).toFixed(1)}%`;
  els.partialPct.textContent = `${stats.totalQty ? ((stats.partialItems / state.items.length) * 100).toFixed(1) : "0.0"}%`;
  els.completePct.textContent = `${stats.percent.toFixed(1)}%`;
}

function suggestedBay(item) {
  if (isCpuItem(item)) return "CPU";
  if (/mirror/i.test(item.product)) return "Mirror";

  const numbers = String(item.dimensions).match(/\d+(?:\s+\d+\/\d+|\/\d+)?/g) || [];
  const parsed = numbers.map((part) => {
    const pieces = part.trim().split(/\s+/);
    let value = Number(pieces[0]) || 0;
    if (pieces[1] && pieces[1].includes("/")) {
      const [top, bottom] = pieces[1].split("/").map(Number);
      if (bottom) value += top / bottom;
    } else if (pieces[0].includes("/")) {
      const [top, bottom] = pieces[0].split("/").map(Number);
      value = bottom ? top / bottom : value;
    }
    return value;
  });
  const largest = Math.max(0, ...parsed);
  if (largest >= 96) return "Oversize";
  if (largest >= 60) return "Tall";
  return "Standard";
}

function renderBaySort() {
  if (!els.bayGrid) return;
  const counts = new Map([
    ["Standard", 0],
    ["Tall", 0],
    ["Oversize", 0],
    ["Mirror", 0],
    ["CPU", 0],
  ]);
  for (const item of state.items) {
    const bay = item.suggestedBay || suggestedBay(item);
    counts.set(bay, (counts.get(bay) || 0) + item.qty);
  }
  els.bayStatus.textContent = state.meta?.stage?.includes("Indian Trail") ? "Active" : "Preview";
  els.bayGrid.innerHTML = [...counts.entries()]
    .map(([bay, qty]) => `<div class="bay-card"><strong>${escapeHtml(bay)}</strong><span>${qty} pieces suggested</span></div>`)
    .join("");
}

function renderTable() {
  const rows = visibleItems().slice(0, 50);
  els.listRows.innerHTML = rows
    .map((item) => {
      const status = itemStatus(item);
      const selected = item.id === state.selectedId;
      const stateMark = status === "complete" ? '<span class="state-mark complete">&#10003;</span>' : '<span class="state-mark">-</span>';
      const route = item.route ? `<span class="route-tag">${item.route}</span>` : "";
      return `
        <tr class="${selected ? "is-selected" : ""} ${status === "complete" ? "is-complete" : ""}" data-id="${item.id}">
          <td><span class="job-title">${escapeHtml(item.product || item.job)}</span><span class="job-subtitle">${escapeHtml(item.job)}</span></td>
          <td>${escapeHtml(item.order)}</td>
          <td>${escapeHtml(item.item)}</td>
          <td><span class="qty-pill ${status}">${item.scanned} / ${item.qty}</span></td>
          <td>${escapeHtml(item.dimensions)}</td>
          <td>${escapeHtml(item.customer)}</td>
          <td></td>
          <td>${route}</td>
          <td>${stateMark}</td>
          <td><span class="state-mark">-</span></td>
        </tr>
      `;
    })
    .join("");
}

function renderMobileCards() {
  const rows = visibleItems().slice(0, 8);
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
      <button class="tab ${state.filter === "errors" ? "is-active" : ""}" data-filter="errors" type="button">Errors (${state.errors.length})</button>
    </div>
    ${rows
      .map((item) => {
        const status = itemStatus(item);
        const selected = item.id === state.selectedId;
        const mark = status === "complete" ? "&#10003;" : item.route || "-";
        return `
          <article class="mobile-list-card ${selected ? "is-selected" : ""}" data-id="${item.id}">
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

function renderRecent() {
  const rows = state.recent.slice(0, 5);
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
              <td>${time.toLocaleString([], { month: "numeric", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit", second: "2-digit" })}</td>
              <td><span class="check-dot ${entry.ok ? "" : "error"}">${entry.ok ? "&#10003;" : "!"}</span></td>
            </tr>
          `;
        })
        .join("")
    : `<tr><td colspan="6">No scans yet</td></tr>`;
}

function renderAlerts() {
  els.alertsList.innerHTML = state.errors.length
    ? state.errors
        .slice(0, 8)
        .map((entry) => `<div class="last-card error"><strong>${escapeHtml(entry.message)}</strong><p>${escapeHtml(entry.barcode)} - ${escapeHtml(entry.reason)}</p></div>`)
        .join("")
    : `<div class="last-card ok"><strong>No alerts</strong><p>All scanned labels are clean.</p></div>`;
}

function renderLastScan() {
  if (state.lastScan) {
    setLastScan(state.lastScan);
    return;
  }
  els.lastCard.classList.remove("ok", "error");
  els.lastScanTime.textContent = "Waiting";
  els.lastJob.textContent = "No scans yet";
  els.lastOrder.textContent = "-";
  els.lastItem.textContent = "-";
  els.lastQty.textContent = "-";
  els.lastDims.textContent = "-";
  els.lastCustomer.textContent = "-";
}

function renderMeta() {
  if (!state.meta) return;
  const dateText = formatDisplayDate(state.meta.deliveryDate);
  els.pageTitle.textContent = `Delivery List for ${dateText}`;
  els.stageSubtitle.textContent = state.meta.stage;
  els.stageHeading.textContent = state.meta.stage;
  els.scannerName.textContent = state.meta.scanner;
  els.autoToggle.setAttribute("aria-pressed", String(state.auto));
  els.backendStatus.textContent = state.backend ? "SQLite live" : "Local demo";
  els.backendStatus.classList.toggle("online", state.backend);
  els.deliveryListSelect.innerHTML = state.lists
    .map((list) => `<option value="${escapeHtml(list.id)}">${escapeHtml(list.label)}</option>`)
    .join("");
  els.deliveryListSelect.value = state.activeListId;
}

function render() {
  renderMeta();
  renderCounts();
  renderTable();
  renderMobileCards();
  renderRecent();
  renderAlerts();
  renderBaySort();
  renderLastScan();
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function init() {
  const params = new URLSearchParams(window.location.search);
  await detectBackend();
  await loadStations();
  if (state.backend) {
    await loadBackendLists(params.get("list"));
  } else {
    const response = await fetch("data/sample-delivery-list.json");
    const payload = await response.json();
    state.lists = createDemoLists(payload);
    setActiveList(params.get("list") || state.lists[0].id);
  }
  wireEvents();
  render();
  await applyDemoQuery();
  els.scanInput.focus();
}

function wireEvents() {
  els.scanForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await processScan(els.scanInput.value);
    els.scanInput.value = "";
    els.scanInput.focus();
  });

  els.searchInput.addEventListener("input", () => {
    state.search = els.searchInput.value;
    render();
  });

  els.deliveryListSelect.addEventListener("change", async () => {
    await activateList(els.deliveryListSelect.value);
    render();
    els.scanInput.focus();
  });

  document.addEventListener("click", (event) => {
    const filterButton = event.target.closest("[data-filter]");
    if (filterButton) {
      state.filter = filterButton.dataset.filter;
      document.querySelectorAll("[data-filter]").forEach((button) => {
        button.classList.toggle("is-active", button.dataset.filter === state.filter);
      });
      render();
      return;
    }

    const navButton = event.target.closest("[data-mobile-target]");
    if (navButton) {
      document.body.dataset.mobileView = navButton.dataset.mobileTarget;
      document.querySelectorAll("[data-mobile-target]").forEach((button) => {
        button.classList.toggle("is-active", button === navButton);
      });
      if (navButton.dataset.mobileTarget === "scan") {
        window.setTimeout(() => els.scanInput.focus(), 30);
      }
      return;
    }

    const row = event.target.closest("[data-id]");
    if (row) {
      state.selectedId = row.dataset.id;
      saveState();
      render();
    }
  });

  els.refreshBtn.addEventListener("click", () => {
    if (state.backend) {
      activateList(state.activeListId).then(render).catch((error) => showInlineError(error.message));
    } else {
      render();
    }
    els.scanInput.focus();
  });

  els.autoToggle.addEventListener("click", () => {
    state.auto = !state.auto;
    saveState();
    render();
  });

  els.resetBtn.addEventListener("click", () => {
    resetState().catch((error) => showInlineError(error.message));
  });

  els.undoBtn.addEventListener("click", async () => {
    if (!state.backend) {
      showInlineError("Undo needs the SQLite backend so the audit trail stays correct.");
      return;
    }
    const payload = await fetchJson("/api/undo", {
      method: "POST",
      body: JSON.stringify({ listId: state.activeListId, ...requestContext() }),
    });
    applyBackendPayload(payload);
    render();
  });

  els.exportBtn.addEventListener("click", () => {
    if (state.backend) {
      window.location.href = `/api/export.csv?listId=${encodeURIComponent(state.activeListId)}`;
      return;
    }
    exportStaticCsv();
  });

  els.importBtn.addEventListener("click", () => {
    els.importFile.value = "";
    els.importFile.click();
  });

  els.importFile.addEventListener("change", () => {
    const file = els.importFile.files?.[0];
    if (!file) return;
    importDeliveryListFile(file).catch((error) => showInlineError(error.message));
  });

  els.printBtn.addEventListener("click", () => {
    window.print();
  });

  els.addStationBtn.addEventListener("click", () => {
    addStationFromInput().catch((error) => showInlineError(error.message));
  });

  els.newStationInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      addStationFromInput().catch((error) => showInlineError(error.message));
    }
  });

  els.loadExampleBtn.addEventListener("click", () => {
    const first = state.items[0];
    if (!first) return;
    els.scanInput.value = `TDEXRTY${pad(first.order, 6).slice(-3)}${first.item}000`;
    document.body.dataset.mobileView = "scan";
    document.querySelectorAll("[data-mobile-target]").forEach((button) => {
      button.classList.toggle("is-active", button.dataset.mobileTarget === "scan");
    });
    els.scanInput.focus();
  });
}

function showInlineError(message) {
  const entry = {
    ok: false,
    barcode: "SYSTEM",
    message: "System notice",
    reason: message,
    time: new Date().toISOString(),
  };
  state.errors.unshift(entry);
  state.recent.unshift(entry);
  state.lastScan = entry;
  render();
}

async function importDeliveryListFile(file) {
  const text = await file.text();
  const payload = JSON.parse(text);
  if (state.backend) {
    const result = await fetchJson("/api/import", {
      method: "POST",
      body: JSON.stringify({
        payload,
        fileName: file.name,
        ...requestContext(),
      }),
    });
    state.lists = result.lists || [];
    await activateList(result.activeListId || state.lists[0]?.id);
  } else {
    state.lists = createDemoLists(payload);
    setActiveList(state.lists[0]?.id);
  }
  state.filter = "all";
  state.search = "";
  els.searchInput.value = "";
  render();
}

function exportStaticCsv() {
  const header = ["barcode", "order", "item", "qty", "scanned", "remaining", "dimensions", "customer", "route", "job", "product", "suggestedBay"];
  const rows = state.items.map((item) => {
    const row = {
      ...item,
      barcode: canonicalBarcode(item.order, item.item),
      remaining: Math.max(Number(item.qty) - Number(item.scanned), 0),
      suggestedBay: item.suggestedBay || suggestedBay(item),
    };
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

async function applyDemoQuery() {
  const params = new URLSearchParams(window.location.search);
  if (params.get("reset") === "1") {
    await resetState();
  }
  const demoScan = params.get("demoScan");
  if (demoScan) {
    await processScan(demoScan);
  }
}

init().catch((error) => {
  document.body.innerHTML = `<main class="app"><section class="last-card error"><strong>Unable to load delivery list</strong><p>${escapeHtml(error.message)}</p></section></main>`;
});
