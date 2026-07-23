(() => {
  "use strict";

  const HISTORY_ENDPOINT = "/api/notifications/history?limit=50";
  const ACK_ENDPOINT = "/api/notifications/acknowledge";
  const READ_ALL_ENDPOINT = "/api/notifications/read-all";
  const SESSION_ENDPOINT = "/api/session";
  const LINE_UPDATES_ENDPOINT = "/api/delivery-list-updates";
  const LINE_UPDATES_ACK_ENDPOINT = "/api/delivery-list-updates/acknowledge";
  const POLL_MS = 10000;

  let host = null;
  let button = null;
  let badge = null;
  let panel = null;
  let list = null;
  let summary = null;
  let toast = null;
  let toastTimer = null;
  let updateBanner = null;
  let updateBannerTimer = null;
  let updateSummaryRequestId = 0;
  let notifications = [];
  let username = "anonymous";
  let pollTimer = null;
  let latestAutomationNotificationId = 0;
  const pendingUpdateSignatureByList = new Map();
  const pendingUpdateIdsByList = new Map();
  const reviewedUpdateSignatureByList = new Map();

  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  async function jsonFetch(url, options = {}) {
    const response = await fetch(url, {
      credentials: "same-origin",
      cache: "no-store",
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || payload.message || `Request failed (${response.status})`);
    return payload;
  }

  function storageKey() {
    return `dls.notification-center.last-seen.${username.toLowerCase()}`;
  }

  function getLastSeenId() {
    const value = Number.parseInt(localStorage.getItem(storageKey()) || "0", 10);
    return Number.isFinite(value) ? value : 0;
  }

  function setLastSeenId(value) {
    const id = Math.max(0, Number.parseInt(String(value || 0), 10) || 0);
    localStorage.setItem(storageKey(), String(id));
  }

  function formatTime(value) {
    if (!value) return "Unknown time";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    const now = new Date();
    const sameDay = date.toDateString() === now.toDateString();
    return date.toLocaleString([], sameDay
      ? { hour: "numeric", minute: "2-digit" }
      : { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
  }

  function typeSymbol(type) {
    if (type === "success") return "✓";
    if (type === "warning") return "!";
    if (type === "error") return "×";
    return "i";
  }

  function isAutomationNotification(item) {
    return String(item?.details?.source || "").trim().toLowerCase() === "sql-delivery-automation";
  }

  function createUi() {
    if (host) return;
    const headerActions = document.querySelector(".header-quick-actions") || document.querySelector(".header-actions");
    if (!headerActions) return;

    host = document.createElement("span");
    host.className = "notification-center-host";
    host.innerHTML = `
      <button class="tool-button header-utility-button notification-center-button" id="notificationCenterBtn" type="button" aria-label="Open notifications" aria-expanded="false" title="Notifications">
        <span class="notification-center-bell" aria-hidden="true"></span>
        <span class="notification-center-badge" id="notificationCenterBadge" hidden>0</span>
      </button>`;

    const languageButton = headerActions.querySelector("#languageToggleBtn");
    if (languageButton) headerActions.insertBefore(host, languageButton);
    else headerActions.prepend(host);

    button = host.querySelector("#notificationCenterBtn");
    badge = host.querySelector("#notificationCenterBadge");

    panel = document.createElement("aside");
    panel.className = "notification-center-panel";
    panel.id = "notificationCenterPanel";
    panel.hidden = true;
    panel.setAttribute("aria-label", "Application notifications");
    panel.innerHTML = `
      <header class="notification-center-header">
        <div class="notification-center-header-copy"><small>System messages</small><strong>Notifications</strong></div>
        <button class="notification-center-close" type="button" aria-label="Close notifications">×</button>
      </header>
      <div class="notification-center-toolbar"><span id="notificationCenterSummary">Checking notifications...</span></div>
      <div class="notification-center-list" id="notificationCenterList"></div>
      <footer class="notification-center-footer">Select a delivery-list update to open Delivery List Management. Scan feedback and Rush alerts stay in their own workflows.</footer>`;
    document.body.append(panel);

    toast = document.createElement("aside");
    toast.className = "automation-update-toast";
    toast.hidden = true;
    toast.setAttribute("role", "status");
    toast.setAttribute("aria-live", "polite");
    document.body.append(toast);

    list = panel.querySelector("#notificationCenterList");
    summary = panel.querySelector("#notificationCenterSummary");

    button.addEventListener("click", (event) => {
      event.stopPropagation();
      panel.hidden ? openPanel() : closePanel();
    });
    panel.querySelector(".notification-center-close").addEventListener("click", closePanel);
    panel.addEventListener("click", (event) => event.stopPropagation());
    window.addEventListener("resize", positionPanel);
    document.addEventListener("click", closePanel);
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && panel && !panel.hidden) closePanel();
    });

    wireLineUpdateAwareness();
  }

  function positionPanel() {
    if (!panel || panel.hidden || !button) return;
    const rect = button.getBoundingClientRect();
    const width = Math.min(390, window.innerWidth - 24);
    const left = Math.max(12, Math.min(window.innerWidth - width - 12, rect.right - width));
    panel.style.left = `${left}px`;
    panel.style.top = `${Math.min(window.innerHeight - 80, rect.bottom + 9)}px`;
  }

  function openPanel() {
    panel.hidden = false;
    button.classList.add("is-open");
    button.setAttribute("aria-expanded", "true");
    positionPanel();
    render();
    refresh({ markReadAfterRefresh: true });
  }

  function closePanel() {
    if (!panel) return;
    panel.hidden = true;
    button?.classList.remove("is-open");
    button?.setAttribute("aria-expanded", "false");
  }

  function unreadNotifications() {
    const lastSeen = getLastSeenId();
    return notifications.filter((item) => Number(item.id || 0) > lastSeen);
  }

  function renderBadge() {
    if (!badge) return;
    const unread = unreadNotifications().length;
    badge.hidden = unread === 0;
    badge.textContent = unread > 99 ? "99+" : String(unread);
    button?.setAttribute("aria-label", unread ? `Open notifications, ${unread} unread` : "Open notifications");
  }

  function render() {
    renderBadge();
    if (!list) return;
    const lastSeen = getLastSeenId();
    const unread = unreadNotifications().length;
    summary.textContent = unread ? `${unread} unread notification${unread === 1 ? "" : "s"}` : "You're caught up";

    if (!notifications.length) {
      list.innerHTML = `<div class="notification-center-empty"><div><strong>No notifications yet</strong><span>Delivery-list automation results and other non-scan system messages will appear here.</span></div></div>`;
      return;
    }

    list.innerHTML = notifications.map((item) => {
      const id = Number(item.id || 0);
      const unreadClass = id > lastSeen ? " is-unread" : "";
      const type = String(item.type || "notice").toLowerCase();
      const actionText = isAutomationNotification(item) ? " · Open Delivery List Management" : "";
      return `
        <button class="notification-center-item${unreadClass}" type="button" data-notification-id="${id}" data-type="${escapeHtml(type)}">
          <span class="notification-center-type-icon" aria-hidden="true">${typeSymbol(type)}</span>
          <span class="notification-center-item-copy">
            <strong>${escapeHtml(item.title || "Notification")}</strong>
            <span>${escapeHtml(item.message || "")}</span>
            <small>${escapeHtml(formatTime(item.createdAt))} · ${escapeHtml(item.createdBy || "system")}${escapeHtml(actionText)}</small>
          </span>
        </button>`;
    }).join("");

    list.querySelectorAll("[data-notification-id]").forEach((itemButton) => {
      itemButton.addEventListener("click", () => {
        const id = Number(itemButton.dataset.notificationId || 0);
        const item = notifications.find((entry) => Number(entry.id || 0) === id);
        if (item) openNotification(item);
      });
    });
  }

  async function markThrough(notificationId) {
    if (!notificationId) return;
    setLastSeenId(Math.max(getLastSeenId(), notificationId));
    render();
    try {
      await jsonFetch(ACK_ENDPOINT, {
        method: "POST",
        body: JSON.stringify({ notificationId }),
      });
    } catch (error) {
      console.warn("Notification acknowledgement could not be saved:", error);
    }
  }

  async function openNotification(item) {
    await markThrough(Number(item.id || 0));
    if (!isAutomationNotification(item)) return;
    closePanel();
    dismissToast();
    document.dispatchEvent(new CustomEvent("dls:open-delivery-list-management-import", {
      detail: { notification: item },
    }));
  }

  async function markAllReadOnOpen() {
    const maxId = notifications.reduce((highest, item) => Math.max(highest, Number(item.id || 0)), 0);
    setLastSeenId(maxId);
    render();
    try {
      await jsonFetch(READ_ALL_ENDPOINT, { method: "POST", body: "{}" });
    } catch (error) {
      console.warn("Notification read state could not be saved:", error);
    }
  }

  function dismissToast() {
    clearTimeout(toastTimer);
    if (!toast) return;
    toast.classList.remove("is-visible");
    window.setTimeout(() => {
      if (!toast.classList.contains("is-visible")) toast.hidden = true;
    }, 180);
  }

  function showAutomationToast(item) {
    if (!toast || !item) return;
    const type = String(item.type || "notice").toLowerCase();
    toast.dataset.type = type;
    toast.innerHTML = `
      <span class="automation-update-toast-icon" aria-hidden="true">${typeSymbol(type)}</span>
      <span class="automation-update-toast-copy">
        <strong>${escapeHtml(item.title || "Delivery lists updated")}</strong>
        <span>${escapeHtml(item.message || "The delivery-list catalog has been refreshed.")}</span>
      </span>
      <button class="automation-update-toast-view" type="button">View</button>
      <button class="automation-update-toast-close" type="button" aria-label="Dismiss notification">×</button>`;
    toast.querySelector(".automation-update-toast-view").addEventListener("click", () => openNotification(item));
    toast.querySelector(".automation-update-toast-close").addEventListener("click", dismissToast);
    toast.hidden = false;
    window.requestAnimationFrame(() => toast.classList.add("is-visible"));
    clearTimeout(toastTimer);
    toastTimer = window.setTimeout(dismissToast, 20000);
  }

  async function refresh(options = {}) {
    try {
      const payload = await jsonFetch(HISTORY_ENDPOINT);
      notifications = Array.isArray(payload.notifications) ? payload.notifications : [];

      const automationItems = notifications
        .filter(isAutomationNotification)
        .filter((item) => Number(item.id || 0) > 0);
      const newestAutomationItem = automationItems.reduce(
        (newest, item) => Number(item.id || 0) > Number(newest?.id || 0) ? item : newest,
        null,
      );
      const newestAutomationNotificationId = Number(newestAutomationItem?.id || 0);
      if (newestAutomationNotificationId > latestAutomationNotificationId) {
        const isNewAfterInitialization = latestAutomationNotificationId > 0;
        latestAutomationNotificationId = newestAutomationNotificationId;
        if (isNewAfterInitialization) {
          showAutomationToast(newestAutomationItem);
          document.dispatchEvent(new CustomEvent("dls:delivery-list-import-history-changed", {
            detail: { notificationId: newestAutomationNotificationId },
          }));
          scheduleLineUpdateSummaryRefresh(800);
        }
      }

      if (options.markReadAfterRefresh) await markAllReadOnOpen();
      else render();
    } catch (error) {
      if (/authentication required/i.test(error.message)) {
        host.hidden = true;
        clearTimeout(pollTimer);
        pollTimer = setTimeout(initialize, 3000);
        return;
      }
      if (summary) summary.textContent = "Notifications unavailable";
      if (list && !notifications.length) {
        list.innerHTML = `<div class="notification-center-empty"><div><strong>Could not load notifications</strong><span>${escapeHtml(error.message)}</span></div></div>`;
      }
    } finally {
      if (!host.hidden) {
        clearTimeout(pollTimer);
        pollTimer = setTimeout(refresh, POLL_MS);
      }
    }
  }

  function activeListId() {
    return String(document.getElementById("deliveryStageSelect")?.value || "").trim();
  }

  function scanPageIsVisible() {
    const scanPage = document.getElementById("scanPage");
    return Boolean(scanPage && !scanPage.hidden && document.visibilityState !== "hidden");
  }

  function ensureUpdateBanner() {
    if (updateBanner?.isConnected) return updateBanner;
    const toolbar = document.querySelector("#scanPage .scan-filter-toolbar") || document.querySelector("#scanPage .list-toolbar");
    if (!toolbar) return null;
    updateBanner = document.createElement("section");
    updateBanner.className = "user-line-update-banner";
    updateBanner.hidden = true;
    toolbar.insertAdjacentElement("afterend", updateBanner);
    return updateBanner;
  }

  function scheduleLineUpdateSummaryRefresh(delay = 250) {
    clearTimeout(updateBannerTimer);
    updateBannerTimer = window.setTimeout(refreshLineUpdateSummary, delay);
  }

  async function refreshLineUpdateSummary() {
    const banner = ensureUpdateBanner();
    const listId = activeListId();
    if (!banner || !scanPageIsVisible() || !listId) {
      if (banner) banner.hidden = true;
      return;
    }
    const requestId = ++updateSummaryRequestId;
    try {
      const payload = await jsonFetch(`${LINE_UPDATES_ENDPOINT}?listId=${encodeURIComponent(listId)}`);
      if (requestId !== updateSummaryRequestId || listId !== activeListId()) return;
      const lineCount = Number(payload.pendingLineCount || 0);
      if (!lineCount) {
        banner.hidden = true;
        return;
      }
      const newCount = Number(payload.newLineCount || 0);
      const updatedCount = Number(payload.updatedLineCount || 0);
      const noticeIds = (Array.isArray(payload.notices) ? payload.notices : [])
        .map((notice) => Number(notice.id || 0))
        .filter((id) => id > 0)
        .sort((a, b) => a - b);
      const noticeSignature = noticeIds.join(",");
      pendingUpdateSignatureByList.set(listId, noticeSignature);
      pendingUpdateIdsByList.set(listId, noticeIds);
      const reviewIsCurrent = Boolean(noticeSignature)
        && reviewedUpdateSignatureByList.get(listId) === noticeSignature;
      const parts = [];
      if (newCount) parts.push(`${newCount} new`);
      if (updatedCount) parts.push(`${updatedCount} updated`);
      banner.innerHTML = `
        <span class="user-line-update-banner-icon" aria-hidden="true">!</span>
        <span class="user-line-update-banner-copy">
          <strong>${lineCount} unseen line update${lineCount === 1 ? "" : "s"} on this list</strong>
          <span>${escapeHtml(parts.join(" and ") || "Delivery-list changes are waiting for review")}. These stay highlighted for you until marked reviewed.</span>
        </span>
        <button class="user-line-update-review" type="button">Review updates</button>
        <button class="user-line-update-ack" type="button"${reviewIsCurrent ? "" : " disabled"} title="${reviewIsCurrent ? "Mark these displayed changes reviewed" : "Review the updated lines first"}">Mark reviewed</button>`;
      banner.hidden = false;
      banner.querySelector(".user-line-update-review").addEventListener("click", reviewCurrentListUpdates);
      banner.querySelector(".user-line-update-ack").addEventListener("click", acknowledgeCurrentListUpdates);
    } catch {
      banner.hidden = true;
    }
  }

  function reviewCurrentListUpdates() {
    const stageSelect = document.getElementById("deliveryStageSelect");
    const listId = String(stageSelect?.value || "").trim();
    if (!listId) return;
    stageSelect.dispatchEvent(new Event("change", { bubbles: true }));
    window.setTimeout(() => {
      const filterButton = document.querySelector('[data-filter="updated"]');
      if (!filterButton) return;
      const isActive = filterButton.classList.contains("active")
        || filterButton.classList.contains("is-active")
        || filterButton.getAttribute("aria-pressed") === "true";
      if (!isActive) filterButton.click();
      const signature = pendingUpdateSignatureByList.get(listId) || "";
      if (signature) reviewedUpdateSignatureByList.set(listId, signature);
      const acknowledgeButton = updateBanner?.querySelector(".user-line-update-ack");
      if (acknowledgeButton && signature) {
        acknowledgeButton.disabled = false;
        acknowledgeButton.title = "Mark these displayed changes reviewed";
      }
      document.getElementById("listPanel")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }, 450);
  }


  function stripReviewedImportLabels(value) {
    return String(value || "")
      .replace(/\b(?:New|Updated) Line\b/gi, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function clearReviewedLabelsFromActiveState(listId) {
    try {
      if (typeof state !== "object" || String(state.activeListId || "") !== String(listId || "")) return;
      if (!Array.isArray(state.items)) return;
      state.items = state.items.map((item) => {
        if (!item || typeof item !== "object") return item;
        const next = { ...item };
        next.processState = stripReviewedImportLabels(next.processState);
        if (Object.prototype.hasOwnProperty.call(next, "process_state")) {
          next.process_state = stripReviewedImportLabels(next.process_state);
        }
        next.userUpdateState = "";
        next.userUpdateNoticeIds = [];
        next.hasUnseenUpdate = false;
        return next;
      });
      if (typeof renderScan === "function") renderScan();
      else if (typeof renderScanTable === "function") renderScanTable();
      else if (typeof renderList === "function") renderList();
    } catch (error) {
      console.warn("Reviewed line labels could not be cleared from the current view:", error);
    }
  }

  async function reloadReviewedList(listId) {
    clearReviewedLabelsFromActiveState(listId);
    try {
      const refreshed = await jsonFetch(`/api/delivery-lists/${encodeURIComponent(listId)}?reviewed=${Date.now()}`);
      if (typeof state === "object" && String(state.activeListId || "") === String(listId || "") && Array.isArray(refreshed.items)) {
        state.items = refreshed.items.slice();
        if (Array.isArray(refreshed.recent)) state.recent = refreshed.recent.slice();
        if (Array.isArray(refreshed.errors)) state.errors = refreshed.errors.slice();
        if (refreshed.meta && typeof refreshed.meta === "object") state.meta = refreshed.meta;
        if (typeof renderScan === "function") renderScan();
        else if (typeof renderScanTable === "function") renderScanTable();
        else if (typeof renderList === "function") renderList();
      }
    } catch (error) {
      console.warn("The reviewed list could not be reloaded immediately:", error);
    }
    document.dispatchEvent(new CustomEvent("dls:user-line-updates-reviewed", {
      detail: { listId, forceReload: true },
    }));
    const stageSelect = document.getElementById("deliveryStageSelect");
    if (!stageSelect || stageSelect.value !== listId) return;
    stageSelect.dispatchEvent(new Event("input", { bubbles: true }));
    stageSelect.dispatchEvent(new Event("change", { bubbles: true }));
    window.setTimeout(() => {
      if (stageSelect.value !== listId) return;
      stageSelect.dispatchEvent(new Event("change", { bubbles: true }));
    }, 450);
  }

  async function acknowledgeCurrentListUpdates() {
    const listId = activeListId();
    if (!listId || !updateBanner) return;
    const acknowledgeButton = updateBanner.querySelector(".user-line-update-ack");
    if (acknowledgeButton) {
      acknowledgeButton.disabled = true;
      acknowledgeButton.textContent = "Saving...";
    }
    try {
      const expectedSignature = pendingUpdateSignatureByList.get(listId) || "";
      if (!expectedSignature || reviewedUpdateSignatureByList.get(listId) !== expectedSignature) {
        throw new Error("Review the updated lines before marking them reviewed.");
      }
      const noticeIds = pendingUpdateIdsByList.get(listId) || [];
      const result = await jsonFetch(LINE_UPDATES_ACK_ENDPOINT, {
        method: "POST",
        body: JSON.stringify({ listId, noticeIds }),
      });
      if (Number(result.pendingLineCount || 0) > 0) {
        pendingUpdateSignatureByList.delete(listId);
        pendingUpdateIdsByList.delete(listId);
        reviewedUpdateSignatureByList.delete(listId);
        await refreshLineUpdateSummary();
        throw new Error("New delivery-list updates arrived while you were reviewing. Review the latest changes before marking them reviewed.");
      }
      pendingUpdateSignatureByList.delete(listId);
      pendingUpdateIdsByList.delete(listId);
      reviewedUpdateSignatureByList.delete(listId);
      updateBanner.hidden = true;
      await reloadReviewedList(listId);
    } catch (error) {
      if (acknowledgeButton) {
        acknowledgeButton.disabled = false;
        acknowledgeButton.textContent = "Try again";
        acknowledgeButton.title = error.message;
      }
    }
  }

  function wireLineUpdateAwareness() {
    document.getElementById("deliveryStageSelect")?.addEventListener("change", () => scheduleLineUpdateSummaryRefresh(500));
    document.addEventListener("dls:delivery-list-catalog-synced", () => scheduleLineUpdateSummaryRefresh(500));
    document.addEventListener("dls:user-line-updates-reviewed", () => scheduleLineUpdateSummaryRefresh(250));
    const scanPage = document.getElementById("scanPage");
    if (scanPage) {
      new MutationObserver(() => scheduleLineUpdateSummaryRefresh(250))
        .observe(scanPage, { attributes: true, attributeFilter: ["hidden"] });
    }
    scheduleLineUpdateSummaryRefresh(800);
  }

  async function initialize() {
    createUi();
    if (!host) {
      setTimeout(initialize, 500);
      return;
    }
    try {
      const session = await jsonFetch(SESSION_ENDPOINT);
      if (!session.authenticated) {
        host.hidden = true;
        clearTimeout(pollTimer);
        pollTimer = setTimeout(initialize, 3000);
        return;
      }
      username = String(session.user?.username || session.user?.displayName || "user");
      host.hidden = false;
      await refresh();
      scheduleLineUpdateSummaryRefresh(500);
    } catch {
      host.hidden = true;
      clearTimeout(pollTimer);
      pollTimer = setTimeout(initialize, 3000);
    }
  }

  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      refresh();
      scheduleLineUpdateSummaryRefresh(250);
    }
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize);
  else initialize();
})();
