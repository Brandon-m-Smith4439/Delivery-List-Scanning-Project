(() => {
  "use strict";

  const API_ROOT = "/api/admin/delivery-automation";
  const ACTION_LABELS = {
    "folder-import-only": "Import Temp Folder Only",
    "sql-export-only": "Query SQL & Export Only",
    "sql-export-and-import": "Query SQL, Export & Import",
  };
  const RANGE_LABELS = {
    "one-date": "one delivery date",
    custom: "a custom date range",
    incremental: "the normal automatic window",
    full: "the full safety refresh window",
  };

  let modal = null;
  let backdrop = null;
  let pollTimer = null;
  let lastDashboard = null;
  let lastCompletedRunKey = "";
  let recentImportsRefreshTimer = null;
  let importHistoryModal = null;
  let importHistorySearchTimer = null;
  let lastImportHistoryPayload = null;
  let importHistoryHasNewResults = false;
  const importHistoryState = {
    page: 1,
    pageSize: 20,
    query: "",
    classification: "",
    dateFrom: "",
    dateTo: "",
  };
  let deliveryCatalogHeartbeat = null;
  let deliveryCatalogRefreshInFlight = false;
  let latestImportRefreshInFlight = false;
  let lastDeliveryCatalogSignature = "";
  let lastLatestImportSignature = "";
  let autoFollowLog = true;

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  async function api(path = "", options = {}) {
    const response = await fetch(`${API_ROOT}${path}`, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.error || payload.message || `Request failed (${response.status})`);
    }
    return payload;
  }

  function localDateIso(offset = 0) {
    const date = new Date();
    date.setHours(12, 0, 0, 0);
    date.setDate(date.getDate() + offset);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function formatTimestamp(value) {
    if (!value) return "No completed run yet";
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return String(value);
    return parsed.toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  }


  function formatDeliveryDate(value) {
    const text = String(value || "").trim();
    if (!text) return "Unknown date";
    const parsed = new Date(`${text.slice(0, 10)}T12:00:00`);
    if (Number.isNaN(parsed.getTime())) return text;
    return parsed.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
  }

  function deliveryCatalogSignature(lists = []) {
    return lists.map((item) => [
      item.id,
      item.deliveryDate,
      item.revision,
      item.status,
      item.totalQty,
      item.scannedQty,
    ].map((value) => String(value ?? "")).join("|")).sort().join("\n");
  }

  function publishDeliveryCatalog(lists, source = "poll", force = false) {
    if (!Array.isArray(lists)) return false;
    const signature = deliveryCatalogSignature(lists);
    if (!force && signature === lastDeliveryCatalogSignature) return false;
    lastDeliveryCatalogSignature = signature;
    document.dispatchEvent(new CustomEvent("dls:delivery-list-data-refreshed", {
      detail: { lists, source, catalogOnly: true },
    }));
    return true;
  }

  function stampLatestImportResults(items, checkedAt = "") {
    const completedAt = String(checkedAt || "").trim();
    return (Array.isArray(items) ? items : []).map((item) => {
      const stamped = { ...item };
      if (completedAt) {
        stamped.importedAt = completedAt;
        stamped.checkedAt = completedAt;
        stamped.updatedAt = completedAt;
      }
      stamped.stageSummaries = (Array.isArray(item?.stageSummaries) ? item.stageSummaries : [])
        .map((stage) => completedAt
          ? { ...stage, importedAt: completedAt, checkedAt: completedAt, updatedAt: completedAt }
          : { ...stage });
      return stamped;
    });
  }

  function latestImportSignature(payload = {}) {
    const results = Array.isArray(payload.latestImportResults)
      ? payload.latestImportResults
      : (Array.isArray(payload.recentImports) ? payload.recentImports : []);
    return JSON.stringify({
      latestRunKey: payload.latestRunKey || "",
      lastCheckedAt: payload.lastCheckedAt || "",
      results: results.map((item) => ({
        deliveryDate: item.deliveryDate || "",
        sourceName: item.sourceName || item.fileName || "",
        classification: item.classification || "",
        importedAt: item.importedAt || "",
        checkedAt: item.checkedAt || "",
        createdCount: Number(item.createdCount || 0),
        reactivatedCount: Number(item.reactivatedCount || 0),
        updatedCount: Number(item.updatedCount || 0),
        addedPieceQty: Number(item.addedPieceQty || 0),
        changedPieceQty: Number(item.changedPieceQty || 0),
        errors: Array.isArray(item.errors) ? item.errors : [],
      })),
    });
  }

  function publishLatestImportResult(payload = {}, source = "latest-import", force = false) {
    const rawResults = Array.isArray(payload.latestImportResults)
      ? payload.latestImportResults
      : (Array.isArray(payload.recentImports) ? payload.recentImports : []);
    const results = stampLatestImportResults(rawResults, payload.lastCheckedAt || payload.latestRun?.completedAt || "");
    const signature = latestImportSignature({ ...payload, latestImportResults: results });
    if (!force && signature === lastLatestImportSignature) return false;
    lastLatestImportSignature = signature;
    updateAdminImportTimestamp(payload);
    document.dispatchEvent(new CustomEvent("dls:delivery-list-data-refreshed", {
      detail: {
        lists: Array.isArray(payload.lists) ? payload.lists : undefined,
        recentImports: results,
        latestImportResults: results,
        lastCheckedAt: payload.lastCheckedAt || "",
        latestRun: payload.latestRun || {},
        latestRunKey: payload.latestRunKey || "",
        source,
        catalogOnly: false,
      },
    }));
    return true;
  }

  async function refreshLatestImportResult(force = false) {
    if (latestImportRefreshInFlight || document.visibilityState === "hidden") return;
    latestImportRefreshInFlight = true;
    try {
      const payload = await api("/latest-import");
      publishLatestImportResult(payload, "latest-import", force);
      if (Array.isArray(payload.lists)) {
        publishDeliveryCatalog(payload.lists, "latest-import-catalog", force);
      }
    } catch {
      // The next Admin visibility check, notification, or heartbeat retries.
    } finally {
      latestImportRefreshInFlight = false;
    }
  }

  async function refreshDeliveryListCatalog(force = false) {
    if (deliveryCatalogRefreshInFlight || document.visibilityState === "hidden") return;
    deliveryCatalogRefreshInFlight = true;
    try {
      const response = await fetch("/api/delivery-lists", {
        credentials: "same-origin",
        cache: "no-store",
        headers: { Accept: "application/json" },
      });
      if (response.status === 401 || response.status === 403) return;
      const payload = await response.json().catch(() => ({}));
      if (response.ok && Array.isArray(payload.lists)) {
        publishDeliveryCatalog(payload.lists, "catalog-poll", force);
      }
    } catch {
      // Keep scanning uninterrupted when a background catalog refresh cannot run.
    } finally {
      deliveryCatalogRefreshInFlight = false;
    }
  }

  function startDeliveryCatalogHeartbeat() {
    if (deliveryCatalogHeartbeat) return;
    refreshDeliveryListCatalog(true);
    if (adminPageIsVisible()) refreshLatestImportResult(true);
    deliveryCatalogHeartbeat = window.setInterval(() => {
      refreshDeliveryListCatalog(false);
      if (adminPageIsVisible()) refreshLatestImportResult(false);
    }, 10000);
  }



  function importResultsFromNotification(item) {
    const details = item?.details && typeof item.details === "object" ? item.details : {};
    return Array.isArray(details.importResults) ? details.importResults : [];
  }

  function openDeliveryListManagementFromNotification(item) {
    const details = item?.details && typeof item.details === "object" ? item.details : {};
    const adminButton = document.querySelector('[data-page-target="admin"]:not([hidden])');
    const results = importResultsFromNotification(item);
    const completedAt = String(details.completedAt || item?.createdAt || "");

    if (!adminButton) {
      const scanButton = document.querySelector('[data-page-target="scan"]:not([hidden])');
      scanButton?.click();
      window.setTimeout(() => {
        const updatedFilter = document.querySelector('[data-filter="updated"]');
        if (updatedFilter && !updatedFilter.classList.contains("active") && !updatedFilter.classList.contains("is-active")) {
          updatedFilter.click();
        }
      }, 350);
      return;
    }

    adminButton.click();
    window.setTimeout(() => {
      if (results.length) {
        publishLatestImportResult({
          latestImportResults: results,
          recentImports: results,
          lastCheckedAt: completedAt,
          latestRunKey: `notification-${Number(item?.id || 0)}`,
          latestRun: {
            completedAt,
            succeeded: details.succeeded,
            mode: details.mode || "",
            runAction: details.runAction || "",
            error: details.error || "",
          },
        }, "notification-click", true);
      } else {
        refreshLatestImportResult(true);
      }
      const management = document.getElementById("adminDeliveryLists");
      management?.scrollIntoView({ behavior: "smooth", block: "start" });
      const panel = management?.closest(".panel") || management;
      panel?.classList.add("dls-import-result-focus");
      window.setTimeout(() => panel?.classList.remove("dls-import-result-focus"), 1800);
    }, 180);
  }

  function classificationDetails(value) {
    const classification = String(value || "no_changes").toLowerCase();
    const values = {
      new: { label: "New", className: "is-new" },
      updated: { label: "Updated", className: "is-updated" },
      new_updated: { label: "New + Updated", className: "is-new-updated" },
      failed: { label: "Failed", className: "is-failed" },
      no_changes: { label: "No Changes", className: "is-no-changes" },
    };
    return values[classification] || values.no_changes;
  }

  function recentImportMessage(item) {
    const classification = String(item.classification || "").toLowerCase();
    const errors = Array.isArray(item.errors) ? item.errors.filter(Boolean) : [];
    if (classification === "failed") {
      return errors[0] || item.reason || "The scanner importer could not process this delivery-list file.";
    }
    if (classification === "no_changes" && item.reason) return String(item.reason);

    const details = [];
    const createdCount = Number(item.createdCount || 0);
    const reactivatedCount = Number(item.reactivatedCount || 0);
    const brandNewCount = Math.max(createdCount - reactivatedCount, 0);
    if (brandNewCount) details.push(`${brandNewCount} new stage list${brandNewCount === 1 ? "" : "s"}`);
    if (reactivatedCount) details.push(`${reactivatedCount} restored stage list${reactivatedCount === 1 ? "" : "s"}`);
    if (Number(item.updatedCount || 0)) details.push(`${Number(item.updatedCount)} updated stage list${Number(item.updatedCount) === 1 ? "" : "s"}`);
    if (Number(item.addedPieceQty || 0)) details.push(`${Number(item.addedPieceQty)} added piece${Number(item.addedPieceQty) === 1 ? "" : "s"}`);
    if (Number(item.changedPieceQty || 0)) details.push(`${Number(item.changedPieceQty)} changed piece${Number(item.changedPieceQty) === 1 ? "" : "s"}`);
    if (Number(item.removedPieceQty || 0)) details.push(`${Number(item.removedPieceQty)} removed source piece${Number(item.removedPieceQty) === 1 ? "" : "s"}`);
    if (!details.length && Number(item.rowCount || 0)) details.push(`${Number(item.rowCount)} line item${Number(item.rowCount) === 1 ? "" : "s"}`);
    if (!details.length) details.push("No delivery-list line changes detected");
    return details.join(" · ");
  }

  function stageSummaryLabel(stage = {}) {
    return String(
      stage.label
      || stage.stage
      || stage.scanner
      || stage.listLabel
      || stage.listId
      || "Delivery-list stage"
    );
  }

  function stageSummaryStatus(stage = {}) {
    const created = Boolean(stage.created);
    const reactivated = Boolean(stage.reactivated);
    const changedLines = Number(stage.changedLineCount || 0);
    const changedPieces = Number(stage.changedPieceQty || 0);
    const updatedPieces = Number(stage.updatedPieceQty || 0);
    const addedPieces = Number(stage.addedPieceQty || stage.newPieceQty || 0);
    const removedLines = Number(stage.removedLineCount || 0);
    const removedPieces = Number(stage.removedPieceQty || 0);
    const changed = changedLines > 0 || changedPieces > 0 || updatedPieces > 0 || addedPieces > 0 || removedLines > 0 || removedPieces > 0;

    if ((created || reactivated) && changed) return { label: "New + Updated", className: "is-new-updated", newStage: true };
    if (created || reactivated) return { label: "New Stage", className: "is-new", newStage: true };
    if (changed) return { label: "Updated", className: "is-updated", newStage: false };
    return { label: "No Changes", className: "is-no-changes", newStage: false };
  }

  function stageSummaryMessage(stage = {}) {
    const parts = [];
    const addedPieces = Number(stage.addedPieceQty || stage.newPieceQty || 0);
    const updatedPieces = Number(stage.updatedPieceQty || 0);
    const changedPieces = Number(stage.changedPieceQty || 0);
    const changedLines = Number(stage.changedLineCount || 0);
    const removedLines = Number(stage.removedLineCount || 0);
    const removedPieces = Number(stage.removedPieceQty || 0);
    const totalQty = Number(stage.totalQty || 0);

    if (stage.reactivated) parts.push("Restored after deletion");
    else if (stage.created) parts.push("Entirely new stage");
    if (addedPieces) parts.push(`${addedPieces} added piece${addedPieces === 1 ? "" : "s"}`);
    if (updatedPieces) parts.push(`${updatedPieces} updated piece${updatedPieces === 1 ? "" : "s"}`);
    else if (changedPieces) parts.push(`${changedPieces} changed piece${changedPieces === 1 ? "" : "s"}`);
    if (changedLines) parts.push(`${changedLines} changed line${changedLines === 1 ? "" : "s"}`);
    if (removedLines) parts.push(`${removedLines} removed source line${removedLines === 1 ? "" : "s"}`);
    if (removedPieces) parts.push(`${removedPieces} removed source piece${removedPieces === 1 ? "" : "s"}`);
    if (!parts.length && totalQty) parts.push(`${totalQty} total piece${totalQty === 1 ? "" : "s"}`);
    if (!parts.length) parts.push("No stage changes detected");
    return parts.join(" · ");
  }

  function renderStageSummaries(item = {}) {
    const stages = Array.isArray(item.stageSummaries) ? item.stageSummaries : [];
    if (!stages.length) {
      return `<div class="automation-import-stage-empty">${escapeHtml(recentImportMessage(item))}</div>`;
    }
    return `
      <div class="automation-import-stage-list">
        ${stages.map((stage) => {
          const status = stageSummaryStatus(stage);
          return `
            <div class="automation-import-stage-row ${status.className}">
              <div class="automation-import-stage-copy">
                <strong>${escapeHtml(stageSummaryLabel(stage))}</strong>
                <small>${escapeHtml(stageSummaryMessage(stage))}</small>
              </div>
              <span class="automation-import-stage-pill">${escapeHtml(status.label)}</span>
            </div>`;
        }).join("")}
      </div>`;
  }

  function updateAdminImportTimestamp(payload = {}) {
    lastImportHistoryPayload = payload;
    const adminLastUpdated = document.getElementById("adminLastUpdated");
    if (adminLastUpdated && payload.lastCheckedAt) {
      adminLastUpdated.textContent = `Last updated: ${formatTimestamp(payload.lastCheckedAt)}`;
    }
  }

  // Import history is part of the main control center. It refreshes only when
  // the History tab is opened, a history control changes, Refresh is selected,
  // or the complete control center closes and performs a hidden catalog sync.
  function wireImportHistoryPanel() {
    importHistoryModal = modal;
    if (!importHistoryModal || importHistoryModal.dataset.historyWired === "true") return;
    importHistoryModal.dataset.historyWired = "true";

    importHistoryModal.querySelector("#importHistoryRefreshBtn").addEventListener("click", () => refreshImportHistory(false));
    importHistoryModal.querySelector("#importHistoryClearBtn").addEventListener("click", () => {
      importHistoryState.page = 1;
      importHistoryState.query = "";
      importHistoryState.classification = "";
      importHistoryState.dateFrom = "";
      importHistoryState.dateTo = "";
      importHistoryModal.querySelector("#importHistorySearch").value = "";
      importHistoryModal.querySelector("#importHistoryStatusFilter").value = "";
      importHistoryModal.querySelector("#importHistoryDateFrom").value = "";
      importHistoryModal.querySelector("#importHistoryDateTo").value = "";
      refreshImportHistory(false);
    });

    importHistoryModal.querySelector("#importHistorySearch").addEventListener("input", (event) => {
      clearTimeout(importHistorySearchTimer);
      importHistorySearchTimer = window.setTimeout(() => {
        importHistoryState.page = 1;
        importHistoryState.query = event.target.value.trim();
        refreshImportHistory(false);
      }, 300);
    });
    importHistoryModal.querySelector("#importHistoryStatusFilter").addEventListener("change", (event) => {
      importHistoryState.page = 1;
      importHistoryState.classification = event.target.value;
      refreshImportHistory(false);
    });
    importHistoryModal.querySelector("#importHistoryDateFrom").addEventListener("change", (event) => {
      importHistoryState.page = 1;
      importHistoryState.dateFrom = event.target.value;
      refreshImportHistory(false);
    });
    importHistoryModal.querySelector("#importHistoryDateTo").addEventListener("change", (event) => {
      importHistoryState.page = 1;
      importHistoryState.dateTo = event.target.value;
      refreshImportHistory(false);
    });
    importHistoryModal.querySelector("#importHistoryPageSize").addEventListener("change", (event) => {
      importHistoryState.page = 1;
      importHistoryState.pageSize = Number(event.target.value || 20);
      refreshImportHistory(false);
    });
    importHistoryModal.querySelector("#importHistoryPager").addEventListener("click", (event) => {
      const button = event.target.closest("button[data-history-page]");
      if (!button || button.disabled) return;
      importHistoryState.page = Number(button.dataset.historyPage || 1);
      refreshImportHistory(false);
    });
  }

  function importHistoryRequestPath() {
    const params = new URLSearchParams({
      page: String(importHistoryState.page),
      pageSize: String(importHistoryState.pageSize),
    });
    if (importHistoryState.query) params.set("q", importHistoryState.query);
    if (importHistoryState.classification) params.set("classification", importHistoryState.classification);
    if (importHistoryState.dateFrom) params.set("dateFrom", importHistoryState.dateFrom);
    if (importHistoryState.dateTo) params.set("dateTo", importHistoryState.dateTo);
    return `/recent-imports?${params.toString()}`;
  }

  function historyPageNumbers(page, totalPages) {
    const values = new Set([1, totalPages, page - 2, page - 1, page, page + 1, page + 2]);
    return [...values].filter((value) => value >= 1 && value <= totalPages).sort((a, b) => a - b);
  }

  function renderImportHistoryPager(payload = {}) {
    const pager = importHistoryModal?.querySelector("#importHistoryPager");
    const pageSummary = importHistoryModal?.querySelector("#importHistoryPageSummary");
    if (!pager || !pageSummary) return;
    const page = Number(payload.page || 1);
    const totalPages = Math.max(1, Number(payload.totalPages || 1));
    pageSummary.textContent = `Page ${page} of ${totalPages}`;
    const pageNumbers = historyPageNumbers(page, totalPages);
    const buttons = [
      `<button type="button" data-history-page="${Math.max(1, page - 1)}"${page <= 1 ? " disabled" : ""}>Previous</button>`,
    ];
    let previousNumber = 0;
    pageNumbers.forEach((number) => {
      if (previousNumber && number - previousNumber > 1) buttons.push('<span class="import-history-page-gap">…</span>');
      buttons.push(`<button type="button" data-history-page="${number}" class="${number === page ? "is-active" : ""}"${number === page ? ' aria-current="page"' : ""}>${number}</button>`);
      previousNumber = number;
    });
    buttons.push(`<button type="button" data-history-page="${Math.min(totalPages, page + 1)}"${page >= totalPages ? " disabled" : ""}>Next</button>`);
    pager.innerHTML = buttons.join("");
  }

  function renderImportHistory(payload = {}) {
    if (!importHistoryModal) return;
    updateAdminImportTimestamp(payload);
    const results = importHistoryModal.querySelector("#importHistoryResults");
    const resultSummary = importHistoryModal.querySelector("#importHistoryResultSummary");
    const lastChecked = importHistoryModal.querySelector("#importHistoryLastChecked");
    const imports = Array.isArray(payload.imports)
      ? payload.imports
      : (Array.isArray(payload.recentImports) ? payload.recentImports : []);
    const totalCount = Number(payload.totalCount ?? imports.length);
    const page = Number(payload.page || 1);
    const pageSize = Number(payload.pageSize || importHistoryState.pageSize);
    const first = totalCount ? ((page - 1) * pageSize) + 1 : 0;
    const last = totalCount ? Math.min(page * pageSize, totalCount) : 0;
    resultSummary.textContent = totalCount
      ? `Showing ${first}-${last} of ${totalCount} import result${totalCount === 1 ? "" : "s"}`
      : "No import results match these filters";
    lastChecked.textContent = payload.lastCheckedAt
      ? `Last automation check ${formatTimestamp(payload.lastCheckedAt)}`
      : "No automation check recorded";

    if (!imports.length) {
      results.innerHTML = `
        <div class="import-history-empty">
          <strong>No matching imports</strong>
          <span>Adjust the search, status, or delivery-date filters.</span>
        </div>`;
      renderImportHistoryPager(payload);
      return;
    }

    results.innerHTML = imports.map((item, index) => {
      const status = classificationDetails(item.classification);
      const sourceName = item.sourceName || `Delivery List ${item.deliveryDate || ""}`;
      return `
        <details class="import-history-entry automation-recent-import-row ${status.className}">
          <summary class="import-history-entry-summary">
            <span class="automation-recent-import-status">${escapeHtml(status.label)}</span>
            <span class="import-history-entry-copy">
              <strong>${escapeHtml(formatDeliveryDate(item.deliveryDate))}</strong>
              <span>${escapeHtml(sourceName)}</span>
              <small>${escapeHtml(recentImportMessage(item))}</small>
            </span>
            <span class="import-history-entry-meta">
              <strong>${escapeHtml(formatTimestamp(item.importedAt))}</strong>
              <span>${escapeHtml(item.importedBy || "system")}</span>
              <i aria-hidden="true"></i>
            </span>
          </summary>
          <div class="import-history-entry-details">
            ${renderStageSummaries(item)}
            <div class="import-history-entry-footnote">
              <span><b>Source:</b> ${escapeHtml(item.importKind || "scanner import")}</span>
              ${item.sourcePath ? `<span title="${escapeHtml(item.sourcePath)}"><b>Path:</b> ${escapeHtml(item.sourcePath)}</span>` : ""}
            </div>
          </div>
        </details>`;
    }).join("");
    renderImportHistoryPager(payload);
  }

  async function refreshImportHistory(resetPage = false) {
    createModal();
    importHistoryModal = modal;
    if (resetPage) importHistoryState.page = 1;
    const results = importHistoryModal.querySelector("#importHistoryResults");
    const previousScrollTop = results.scrollTop;
    results.innerHTML = '<div class="import-history-loading"><span></span><strong>Loading import history...</strong></div>';
    try {
      const payload = await api(importHistoryRequestPath());
      importHistoryState.page = Number(payload.page || importHistoryState.page);
      importHistoryState.pageSize = Number(payload.pageSize || importHistoryState.pageSize);
      renderImportHistory(payload);
      results.scrollTop = resetPage ? 0 : previousScrollTop;
      importHistoryHasNewResults = false;
      const refreshButton = importHistoryModal.querySelector("#importHistoryRefreshBtn");
      if (refreshButton) {
        refreshButton.textContent = "Refresh";
        refreshButton.classList.remove("has-new-results");
      }
      if (Array.isArray(payload.lists)) publishDeliveryCatalog(payload.lists, "import-history", true);
    } catch (error) {
      results.innerHTML = `<div class="import-history-empty is-error"><strong>Import history could not be loaded</strong><span>${escapeHtml(error.message)}</span></div>`;
    }
  }


  async function refreshRecentImports(options = {}) {
    clearTimeout(recentImportsRefreshTimer);
    const refreshHistoryWindow = Boolean(options.refreshHistoryWindow);
    await refreshLatestImportResult(true);
    if (refreshHistoryWindow && importHistoryModal && !importHistoryModal.hidden) {
      refreshImportHistory(false);
    }
  }

  function scheduleRecentImportsRefresh(delay = 250, options = {}) {
    clearTimeout(recentImportsRefreshTimer);
    recentImportsRefreshTimer = setTimeout(() => refreshRecentImports(options), delay);
  }

  function adminPageIsVisible() {
    const adminPage = document.getElementById("adminPage");
    return Boolean(adminPage && !adminPage.hidden && document.visibilityState !== "hidden");
  }

  function observeAdminPage() {
    const adminPage = document.getElementById("adminPage");
    if (!adminPage) return;
    const refreshAdminSources = () => {
      if (adminPage.hidden) return;
      refreshDeliveryListCatalog(true);
      refreshLatestImportResult(true);
    };
    const observer = new MutationObserver(refreshAdminSources);
    observer.observe(adminPage, { attributes: true, attributeFilter: ["hidden"] });
    refreshAdminSources();
  }

  function actionCard(value, icon, title, description, tag, checked = false) {
    return `
      <label class="automation-action-card${checked ? " is-selected" : ""}" data-action-card="${value}">
        <input type="radio" name="automationAction" value="${value}"${checked ? " checked" : ""}>
        <span class="automation-card-icon ${icon}" aria-hidden="true"></span>
        <span class="automation-card-copy">
          <strong>${title}</strong>
          <small>${description}</small>
          <span class="automation-card-tag">${tag}</span>
        </span>
      </label>`;
  }

  function modeCard(value, icon, title, description, tag) {
    return `
      <label class="automation-mode-card" data-mode-card="${value}">
        <input type="radio" name="automationMode" value="${value}">
        <span class="automation-card-icon ${icon}" aria-hidden="true"></span>
        <span class="automation-card-copy">
          <strong>${title}</strong>
          <small>${description}</small>
          <span class="automation-card-tag">${tag}</span>
        </span>
      </label>`;
  }

  function createModal() {
    if (modal) return;

    backdrop = document.createElement("div");
    backdrop.className = "delivery-automation-backdrop";
    backdrop.hidden = true;

    modal = document.createElement("section");
    modal.className = "delivery-automation-modal";
    modal.hidden = true;
    modal.setAttribute("role", "dialog");
    modal.setAttribute("aria-modal", "true");
    modal.setAttribute("aria-labelledby", "deliveryAutomationTitle");
    modal.innerHTML = `
      <header class="delivery-automation-header">
        <div class="delivery-automation-heading">
          <span class="delivery-automation-eyebrow">Delivery List Management</span>
          <h2 id="deliveryAutomationTitle">Automation Control Center</h2>
          <p>Run a one-time update, choose what this computer does automatically, and review the latest result without leaving the scanner.</p>
        </div>
        <div class="delivery-automation-header-actions">
          <span class="delivery-automation-health-pill" id="automationHeaderHealth"><i></i><span>Checking runtime</span></span>
          <button class="delivery-automation-close" type="button" data-automation-close aria-label="Close automation window">×</button>
        </div>
      </header>

      <nav class="delivery-automation-tabs" role="tablist" aria-label="Delivery list automation sections">
        <button type="button" class="is-active" data-automation-tab="manual" role="tab" aria-selected="true"><span class="automation-tab-icon run" aria-hidden="true"></span>Run Manually</button>
        <button type="button" data-automation-tab="settings" role="tab" aria-selected="false"><span class="automation-tab-icon schedule" aria-hidden="true"></span>Automatic Schedule</button>
        <button type="button" data-automation-tab="status" role="tab" aria-selected="false"><span class="automation-tab-icon status" aria-hidden="true"></span>Status & Logs</button>
        <button type="button" data-automation-tab="history" role="tab" aria-selected="false"><span class="automation-tab-icon history" aria-hidden="true"></span>Import History</button>
      </nav>

      <div class="delivery-automation-content">
        <section class="delivery-automation-tab is-active" data-automation-panel="manual" role="tabpanel">
          <div class="automation-section-heading">
            <div><small>Step 1</small><h3>Choose what should happen</h3></div>
            <span>Nothing runs until Start Update is selected.</span>
          </div>

          <div class="automation-action-grid">
            ${actionCard("folder-import-only", "folder", "Import Temp Folder Only", "Reads existing delivery-list workbooks and imports changes into this scanner database. Does not contact A+W SQL.", "Floor computer", true)}
            ${actionCard("sql-export-only", "database", "Query SQL & Export Only", "Queries A+W and publishes one workbook per delivery date without importing into this scanner database.", "Export only")}
            ${actionCard("sql-export-and-import", "sync", "Query SQL, Export & Import", "Runs the complete central workflow: query A+W, publish dated workbooks, and immediately update the scanner.", "Central system")}
          </div>

          <div class="automation-section-heading">
            <div><small>Step 2</small><h3>Choose the delivery-date window</h3></div>
          </div>

          <section class="automation-range-panel">
            <div class="automation-range-intro">
              <strong>Delivery dates to check</strong>
              <p>Use one date for a targeted correction, a custom range for testing, or one of the saved automatic windows for a normal refresh.</p>
              <div class="automation-run-summary" id="automationRunSummary">Import Temp Folder Only for one delivery date.</div>
            </div>
            <div class="automation-range-fields">
              <label>
                <span>Date window</span>
                <select id="automationRangeMode">
                  <option value="one-date">One delivery date</option>
                  <option value="custom">Custom date range</option>
                  <option value="incremental">Normal automatic window</option>
                  <option value="full">Full safety refresh window</option>
                </select>
              </label>
              <label data-automation-date-field="from"><span>Delivery date</span><input id="automationDateFrom" type="date"></label>
              <label data-automation-date-field="to"><span>Through date</span><input id="automationDateTo" type="date"></label>
            </div>
          </section>

          <footer class="automation-command-bar">
            <div class="automation-command-state">
              <strong id="automationManualHeading">Ready to run</strong>
              <span id="automationManualMessage">Choose an operation and date window, then start the update.</span>
            </div>
            <button type="button" class="automation-primary-button" id="automationRunBtn">Start Update</button>
          </footer>
        </section>

        <section class="delivery-automation-tab" data-automation-panel="settings" role="tabpanel">
          <div class="automation-section-heading">
            <div><small>Automatic behavior</small><h3>Choose this computer's role</h3></div>
            <span id="automationScheduleBadge">Checking scheduled tasks...</span>
          </div>

          <div class="automation-mode-grid">
            ${modeCard("disabled", "off", "Manual Only", "No scheduled delivery-list runs. All manual commands remain available.", "Disabled")}
            ${modeCard("folder-import-only", "folder", "Import Folder", "Best for floor computers that can read the shared folder but cannot query A+W.", "Floor")}
            ${modeCard("sql-export-only", "database", "Export SQL", "Queries A+W and keeps the Temp Delivery Lists folder current without importing locally.", "Publisher")}
            ${modeCard("sql-export-and-import", "sync", "Full Workflow", "Queries, exports, and imports. Recommended for the authorized central host.", "Central")}
          </div>

          <section class="automation-settings-panel">
            <div class="automation-settings-section">
              <div class="automation-settings-section-heading">
                <strong>Incremental schedule</strong>
                <span>The frequent lightweight check used during the workday.</span>
              </div>
              <div class="automation-settings-grid">
                <label><span>Run every</span><div class="automation-number-unit"><input id="automationInterval" type="number" min="5" max="1440" step="5"><b>minutes</b></div></label>
                <label><span>Past delivery days</span><input id="automationPastDays" type="number" min="0" max="365"></label>
                <label><span>Future delivery days</span><input id="automationFutureDays" type="number" min="0" max="365"></label>
              </div>
            </div>

            <div class="automation-settings-section">
              <div class="automation-settings-section-heading">
                <strong>Daily full refresh</strong>
                <span>The broader safety sweep that catches older and far-future changes.</span>
              </div>
              <div class="automation-settings-grid">
                <label><span>Full refresh time</span><input id="automationFullTime" type="time"></label>
                <label><span>Past delivery days</span><input id="automationFullPastDays" type="number" min="0" max="365"></label>
                <label><span>Future delivery days</span><input id="automationFullFutureDays" type="number" min="0" max="365"></label>
              </div>
            </div>

            <div class="automation-settings-section">
              <div class="automation-settings-section-heading">
                <strong>Files and notifications</strong>
                <span>The bell keeps notification history even after a popup closes or scanning continues.</span>
              </div>
              <label class="automation-wide-field"><span>Temp Delivery Lists folder</span><input id="automationDestinationFolder" type="text" autocomplete="off"><small>Use the UNC path so scheduled tasks and floor computers do not depend on a mapped drive letter.</small></label>
              <div class="automation-toggle-grid">
                <label class="automation-toggle-card"><input id="automationNotifications" type="checkbox"><span><strong>Show brief popup alerts</strong><small>Display success and failure alerts while users are signed in. The bell history remains available separately.</small></span></label>
                <label class="automation-toggle-card"><input id="automationNoChangeNotifications" type="checkbox"><span><strong>Notify when nothing changed</strong><small>Add an informational result after a successful check that found no workbook changes.</small></span></label>
              </div>
            </div>

            <div class="automation-settings-actions">
              <button type="button" class="automation-secondary-button" id="automationSaveBtn">Save Settings</button>
              <button type="button" class="automation-primary-button" id="automationInstallScheduleBtn">Save & Install Schedule</button>
              <button type="button" class="automation-danger-button" id="automationRemoveScheduleBtn">Disable Scheduled Tasks</button>
            </div>
            <p id="automationSettingsMessage" class="automation-inline-message">Settings have not been changed.</p>
          </section>
        </section>

        <section class="delivery-automation-tab" data-automation-panel="status" role="tabpanel">
          <div class="automation-section-heading">
            <div><small>Runtime health</small><h3>Latest automation result</h3></div>
            <button type="button" class="automation-text-button" id="automationRefreshStatusBtn">Refresh Status</button>
          </div>

          <section class="automation-status-hero" id="automationStatusHero">
            <span class="automation-status-symbol" aria-hidden="true"></span>
            <div class="automation-status-copy"><strong id="automationStatusTitle">Not run yet</strong><span id="automationStatusMessage">No automation result has been recorded.</span></div>
            <span class="automation-status-time" id="automationStatusTime">No completed run yet</span>
          </section>

          <div id="automationStatusSummary" class="automation-status-summary"></div>
          <details class="automation-log-details" id="automationLogDetails" open>
            <summary>
              <span>Live command log</span>
              <small id="automationLogLineCount">0 lines</small>
            </summary>
            <div class="automation-log-toolbar">
              <div class="automation-log-location">
                <small>Log file</small>
                <span id="automationLogPath">No log file recorded yet.</span>
              </div>
              <label class="automation-log-follow"><input id="automationLogFollow" type="checkbox" checked><span>Follow newest activity</span></label>
              <button type="button" class="automation-text-button" id="automationCopyLogBtn">Copy Full Log</button>
            </div>
            <pre id="automationStatusLog" tabindex="0">No command output yet.</pre>
          </details>
        </section>

        <section class="delivery-automation-tab import-history-workspace" data-automation-panel="history" role="tabpanel">
          <div class="import-history-panel-heading">
            <div>
              <small>Delivery List Management</small>
              <h3>Import Audit History</h3>
              <p>Review the newest imports first, then search or filter older delivery-list results.</p>
            </div>
            <button class="automation-secondary-button" id="importHistoryRefreshBtn" type="button">Refresh</button>
          </div>

          <section class="import-history-toolbar" aria-label="Import history filters">
            <label class="import-history-search search-box">
              <span class="search-icon" aria-hidden="true"></span>
              <input id="importHistorySearch" type="search" autocomplete="off" placeholder="Search date, filename, stage, user, status...">
            </label>
            <label>
              <span>Status</span>
              <select id="importHistoryStatusFilter">
                <option value="">All statuses</option>
                <option value="new">New</option>
                <option value="updated">Updated</option>
                <option value="new_updated">New + Updated</option>
                <option value="no_changes">No Changes</option>
                <option value="failed">Failed</option>
              </select>
            </label>
            <label><span>Delivery date from</span><input id="importHistoryDateFrom" type="date"></label>
            <label><span>Delivery date through</span><input id="importHistoryDateTo" type="date"></label>
            <label>
              <span>Rows per page</span>
              <select id="importHistoryPageSize">
                <option value="20">20</option>
                <option value="50">50</option>
                <option value="100">100</option>
              </select>
            </label>
            <button class="automation-text-button import-history-clear" id="importHistoryClearBtn" type="button">Clear filters</button>
          </section>

          <section class="import-history-status-row">
            <strong id="importHistoryResultSummary">Open Import History to load results.</strong>
            <span id="importHistoryLastChecked">Waiting for current status</span>
          </section>
          <div class="import-history-results" id="importHistoryResults" aria-live="polite"></div>
          <footer class="import-history-footer">
            <span id="importHistoryPageSummary">Page 1 of 1</span>
            <nav class="import-history-pager" id="importHistoryPager" aria-label="Import history pages"></nav>
          </footer>
        </section>
      </div>`;

    document.body.append(backdrop, modal);
    wireImportHistoryPanel();

    backdrop.addEventListener("click", closeModal);
    modal.querySelector("[data-automation-close]").addEventListener("click", closeModal);
    modal.querySelectorAll("[data-automation-tab]").forEach((button) => {
      button.addEventListener("click", () => selectTab(button.dataset.automationTab));
    });
    modal.querySelectorAll('input[name="automationAction"]').forEach((input) => {
      input.addEventListener("change", () => {
        updateSelectedCards();
        updateRunSummary();
      });
    });
    modal.querySelectorAll('input[name="automationMode"]').forEach((input) => {
      input.addEventListener("change", updateSelectedCards);
    });
    modal.querySelector("#automationRangeMode").addEventListener("change", () => {
      updateDateVisibility();
      updateRunSummary();
    });
    modal.querySelector("#automationDateFrom").addEventListener("change", updateRunSummary);
    modal.querySelector("#automationDateTo").addEventListener("change", updateRunSummary);
    modal.querySelector("#automationRunBtn").addEventListener("click", runManual);
    modal.querySelector("#automationSaveBtn").addEventListener("click", () => saveSettings(false));
    modal.querySelector("#automationInstallScheduleBtn").addEventListener("click", () => saveSettings(true));
    modal.querySelector("#automationRemoveScheduleBtn").addEventListener("click", removeSchedule);
    modal.querySelector("#automationRefreshStatusBtn").addEventListener("click", refreshDashboard);
    modal.querySelector("#automationCopyLogBtn").addEventListener("click", copyFullLog);
    modal.querySelector("#automationLogFollow").addEventListener("change", (event) => {
      autoFollowLog = event.target.checked;
      if (autoFollowLog) {
        const log = modal.querySelector("#automationStatusLog");
        log.scrollTop = log.scrollHeight;
      }
    });

    modal.querySelector("#automationDateFrom").value = localDateIso();
    modal.querySelector("#automationDateTo").value = localDateIso();
    updateSelectedCards();
    updateDateVisibility();
    updateRunSummary();
  }

  function selectTab(name) {
    modal.querySelectorAll("[data-automation-tab]").forEach((button) => {
      const active = button.dataset.automationTab === name;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-selected", String(active));
    });
    modal.querySelectorAll("[data-automation-panel]").forEach((panel) => {
      panel.classList.toggle("is-active", panel.dataset.automationPanel === name);
    });
    if (name === "history") {
      refreshImportHistory(false);
      window.setTimeout(() => modal.querySelector("#importHistorySearch")?.focus(), 30);
    }
  }

  function updateSelectedCards() {
    modal.querySelectorAll("[data-action-card]").forEach((card) => {
      card.classList.toggle("is-selected", card.querySelector("input")?.checked === true);
    });
    modal.querySelectorAll("[data-mode-card]").forEach((card) => {
      card.classList.toggle("is-selected", card.querySelector("input")?.checked === true);
    });
  }

  function updateDateVisibility() {
    const mode = modal.querySelector("#automationRangeMode").value;
    const fromField = modal.querySelector('[data-automation-date-field="from"]');
    const toField = modal.querySelector('[data-automation-date-field="to"]');
    fromField.classList.toggle("automation-hidden", !["one-date", "custom"].includes(mode));
    toField.classList.toggle("automation-hidden", mode !== "custom");
    fromField.querySelector("span").textContent = mode === "one-date" ? "Delivery date" : "From date";
  }

  function updateRunSummary() {
    const action = modal.querySelector('input[name="automationAction"]:checked')?.value || "folder-import-only";
    const rangeMode = modal.querySelector("#automationRangeMode").value;
    const dateFrom = modal.querySelector("#automationDateFrom").value;
    const dateTo = modal.querySelector("#automationDateTo").value;
    let suffix = RANGE_LABELS[rangeMode] || "the selected window";
    if (rangeMode === "one-date" && dateFrom) suffix = `delivery date ${dateFrom}`;
    if (rangeMode === "custom" && dateFrom && dateTo) suffix = `${dateFrom} through ${dateTo}`;
    modal.querySelector("#automationRunSummary").textContent = `${ACTION_LABELS[action]} for ${suffix}.`;
  }

  function openModal() {
    createModal();
    backdrop.hidden = false;
    modal.hidden = false;
    document.body.classList.add("modal-open");
    refreshDashboard();
    scheduleRecentImportsRefresh(0);
    const activeTab = modal.querySelector("[data-automation-tab].is-active")?.dataset.automationTab || "manual";
    if (activeTab === "history") refreshImportHistory(false);
    setTimeout(() => modal.querySelector("[data-automation-close]")?.focus(), 0);
  }

  function closeModal() {
    if (!modal) return;
    backdrop.hidden = true;
    modal.hidden = true;
    document.body.classList.remove("modal-open");
    refreshRecentImports({ refreshHistoryWindow: false });
    if (pollTimer) {
      clearTimeout(pollTimer);
      pollTimer = null;
    }
  }

  function fillSettings(settings = {}) {
    const mode = settings.automationMode || "sql-export-and-import";
    const modeInput = modal.querySelector(`input[name="automationMode"][value="${CSS.escape(mode)}"]`);
    if (modeInput) modeInput.checked = true;
    modal.querySelector("#automationInterval").value = settings.intervalMinutes ?? 60;
    modal.querySelector("#automationPastDays").value = settings.incrementalPastDays ?? 2;
    modal.querySelector("#automationFutureDays").value = settings.incrementalFutureDays ?? 14;
    modal.querySelector("#automationFullTime").value = settings.fullRefreshTime || "17:00";
    modal.querySelector("#automationFullPastDays").value = settings.fullPastDays ?? 7;
    modal.querySelector("#automationFullFutureDays").value = settings.fullFutureDays ?? 90;
    modal.querySelector("#automationDestinationFolder").value = settings.destinationFolder || "";
    modal.querySelector("#automationNotifications").checked = settings.notificationsEnabled !== false;
    modal.querySelector("#automationNoChangeNotifications").checked = settings.notifyOnNoChanges !== false;
    updateSelectedCards();
  }

  async function copyFullLog() {
    const button = modal.querySelector("#automationCopyLogBtn");
    const logText = modal.querySelector("#automationStatusLog").textContent || "";
    const originalText = button.textContent;
    try {
      await navigator.clipboard.writeText(logText);
      button.textContent = "Copied";
    } catch {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(modal.querySelector("#automationStatusLog"));
      selection.removeAllRanges();
      selection.addRange(range);
      button.textContent = "Log selected";
    }
    setTimeout(() => { button.textContent = originalText; }, 1600);
  }

  function renderStatus(dashboard) {
    lastDashboard = dashboard;
    const last = dashboard.lastRun || {};
    const running = Boolean(dashboard.running || last.running);
    const succeeded = last.succeeded;
    const state = running ? "Automation is running" : succeeded === true ? "Update completed" : succeeded === false ? "Update failed" : "Not run yet";
    const stateClass = running ? "is-running" : succeeded === true ? "is-success" : succeeded === false ? "is-error" : "";

    const health = modal.querySelector("#automationHeaderHealth");
    health.className = `delivery-automation-health-pill ${running ? "is-running" : dashboard.runtimeReady ? "is-ready" : ""}`;
    health.querySelector("span").textContent = running ? "Update running" : dashboard.runtimeReady ? "Runtime ready" : "Runtime unavailable";

    modal.querySelector("#automationScheduleBadge").textContent = dashboard.scheduleInstalled
      ? "Scheduled tasks are installed"
      : "Scheduled tasks are not installed";

    const hero = modal.querySelector("#automationStatusHero");
    hero.className = `automation-status-hero ${stateClass}`;
    modal.querySelector("#automationStatusTitle").textContent = state;
    modal.querySelector("#automationStatusMessage").textContent = running
      ? last.currentStep || last.message || "Waiting for the next automation step..."
      : last.message || "No automation result has been recorded.";
    modal.querySelector("#automationStatusTime").textContent = running
      ? `Started ${formatTimestamp(last.startedAt)}`
      : formatTimestamp(last.completedAt);

    const modeLabel = ACTION_LABELS[dashboard.settings?.automationMode] || (dashboard.settings?.automationMode === "disabled" ? "Manual Only" : "Not configured");
    modal.querySelector("#automationStatusSummary").innerHTML = `
      <article class="automation-status-card"><small>Runtime</small><strong>${dashboard.runtimeReady ? "Ready" : "Not installed"}</strong><span>${escapeHtml(dashboard.configPath || "Runtime configuration was not found.")}</span></article>
      <article class="automation-status-card"><small>Automatic mode</small><strong>${escapeHtml(modeLabel)}</strong><span>${dashboard.scheduleInstalled ? "Windows scheduled tasks are active." : "Manual commands are still available."}</span></article>
      <article class="automation-status-card"><small>Last command</small><strong>${escapeHtml(last.action ? ACTION_LABELS[last.action] || last.action : "No command")}</strong><span>Started by ${escapeHtml(last.startedBy || last.createdBy || "system")}</span></article>`;

    const output = last.commandOutput || [last.stdout, last.stderr, last.error].filter(Boolean).join("\n\n");
    const logElement = modal.querySelector("#automationStatusLog");
    const wasNearBottom = logElement.scrollHeight - logElement.scrollTop - logElement.clientHeight < 48;
    logElement.textContent = output || "No command output yet.";
    const lineCount = Number(last.outputLineCount || (output ? output.split(/\r?\n/).length : 0));
    modal.querySelector("#automationLogLineCount").textContent = `${lineCount} line${lineCount === 1 ? "" : "s"}${running ? " - live" : ""}`;
    modal.querySelector("#automationLogPath").textContent = last.logPath || "No log file recorded yet.";
    if (autoFollowLog || wasNearBottom) logElement.scrollTop = logElement.scrollHeight;
    if (running || succeeded === false) modal.querySelector("#automationLogDetails").open = true;
    modal.querySelector("#automationManualHeading").textContent = running ? "Update in progress" : succeeded === false ? "Last update failed" : "Ready to run";
    modal.querySelector("#automationManualMessage").textContent = running
      ? "The automation is running in the background. Status refreshes automatically."
      : last.message || "Choose an operation and date window, then start the update.";

    const completedRunKey = !running && last.completedAt
      ? `${last.taskId || last.mode || "run"}|${last.completedAt}`
      : "";
    const importedResult = Array.isArray(last.importResults) && last.importResults.length > 0;
    const importAction = ["folder-import-only", "sql-export-and-import"].includes(last.action)
      || ["FolderImportOnly", "SqlExportAndImport"].includes(last.runAction);
    if (completedRunKey && completedRunKey !== lastCompletedRunKey && (importedResult || importAction)) {
      lastCompletedRunKey = completedRunKey;
      scheduleRecentImportsRefresh(150);
      window.setTimeout(() => refreshDeliveryListCatalog(true), 175);
      window.setTimeout(() => refreshLatestImportResult(true), 200);
    }

    if (running) {
      if (pollTimer) clearTimeout(pollTimer);
      pollTimer = setTimeout(refreshDashboard, 1000);
    }
  }

  async function refreshDashboard() {
    if (!modal || modal.hidden) return;
    try {
      const dashboard = await api();
      fillSettings(dashboard.settings);
      renderStatus(dashboard);
    } catch (error) {
      modal.querySelector("#automationHeaderHealth").querySelector("span").textContent = "Status unavailable";
      modal.querySelector("#automationManualMessage").textContent = error.message;
      modal.querySelector("#automationSettingsMessage").textContent = error.message;
    }
  }

  async function runManual() {
    const button = modal.querySelector("#automationRunBtn");
    const message = modal.querySelector("#automationManualMessage");
    const heading = modal.querySelector("#automationManualHeading");
    const action = modal.querySelector('input[name="automationAction"]:checked')?.value;
    const rangeMode = modal.querySelector("#automationRangeMode").value;
    button.disabled = true;
    button.textContent = "Starting...";
    heading.textContent = "Starting update";
    message.textContent = "The command is being handed to the automation runtime.";
    try {
      await api("/run", {
        method: "POST",
        body: JSON.stringify({
          action,
          rangeMode,
          dateFrom: modal.querySelector("#automationDateFrom").value,
          dateTo: modal.querySelector("#automationDateTo").value,
        }),
      });
      selectTab("status");
      await refreshDashboard();
    } catch (error) {
      heading.textContent = "Could not start update";
      message.textContent = error.message;
    } finally {
      button.disabled = false;
      button.textContent = "Start Update";
    }
  }

  function settingsPayload() {
    return {
      automationMode: modal.querySelector('input[name="automationMode"]:checked')?.value || "disabled",
      intervalMinutes: modal.querySelector("#automationInterval").value,
      incrementalPastDays: modal.querySelector("#automationPastDays").value,
      incrementalFutureDays: modal.querySelector("#automationFutureDays").value,
      fullRefreshTime: modal.querySelector("#automationFullTime").value,
      fullPastDays: modal.querySelector("#automationFullPastDays").value,
      fullFutureDays: modal.querySelector("#automationFullFutureDays").value,
      destinationFolder: modal.querySelector("#automationDestinationFolder").value,
      notificationsEnabled: modal.querySelector("#automationNotifications").checked,
      notifyOnNoChanges: modal.querySelector("#automationNoChangeNotifications").checked,
    };
  }

  async function saveSettings(installSchedule) {
    const message = modal.querySelector("#automationSettingsMessage");
    const saveButton = installSchedule ? modal.querySelector("#automationInstallScheduleBtn") : modal.querySelector("#automationSaveBtn");
    saveButton.disabled = true;
    message.textContent = installSchedule ? "Saving settings and updating Windows scheduled tasks..." : "Saving settings...";
    try {
      await api("/config", { method: "POST", body: JSON.stringify(settingsPayload()) });
      if (installSchedule) {
        await api("/schedule/install", { method: "POST", body: "{}" });
      }
      message.textContent = installSchedule
        ? "Settings saved and scheduled tasks installed successfully."
        : "Settings saved. Reinstall the schedule when you need trigger times changed.";
      await refreshDashboard();
    } catch (error) {
      message.textContent = error.message;
    } finally {
      saveButton.disabled = false;
    }
  }

  async function removeSchedule() {
    const message = modal.querySelector("#automationSettingsMessage");
    if (!window.confirm("Disable both delivery-list automation scheduled tasks on this computer? Manual commands will remain available.")) return;
    message.textContent = "Disabling scheduled tasks...";
    try {
      await api("/schedule/remove", { method: "POST", body: "{}" });
      message.textContent = "Scheduled tasks disabled. Manual commands remain available.";
      await refreshDashboard();
    } catch (error) {
      message.textContent = error.message;
    }
  }

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (modal && !modal.hidden) closeModal();
  });



  document.addEventListener("dls:open-delivery-list-management-import", (event) => {
    const item = event.detail?.notification;
    if (item) openDeliveryListManagementFromNotification(item);
  });

  document.addEventListener("dls:delivery-list-import-history-changed", () => {
    importHistoryHasNewResults = true;
    const refreshButton = modal?.querySelector("#importHistoryRefreshBtn");
    const historyPanel = modal?.querySelector('[data-automation-panel="history"]');
    if (refreshButton && modal && !modal.hidden && historyPanel?.classList.contains("is-active")) {
      refreshButton.textContent = "Refresh - new results";
      refreshButton.classList.add("has-new-results");
    }
    scheduleRecentImportsRefresh(100, { refreshHistoryWindow: false });
  });

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "hidden") {
      refreshDeliveryListCatalog(true);
      if (adminPageIsVisible()) refreshLatestImportResult(true);
    }
  });

  document.addEventListener("click", (event) => {
    const target = event.target.closest("#folderImportBtn");
    if (!target) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    openModal();
  }, true);

  function initializeRecentImportHistory() {
    observeAdminPage();
    startDeliveryCatalogHeartbeat();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeRecentImportHistory, { once: true });
  } else {
    initializeRecentImportHistory();
  }
})();
