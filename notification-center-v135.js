(() => {
  "use strict";

  const HISTORY_ENDPOINT = "/api/notifications/history?limit=75";
  const ACK_ENDPOINT = "/api/notifications/acknowledge";
  const READ_ALL_ENDPOINT = "/api/notifications/read-all";
  const SESSION_ENDPOINT = "/api/session";
  const FLAGS_ENDPOINT = "/api/operations/line-flags";
  const UPDATE_ACK_ENDPOINT = "/api/operations/line-flags/acknowledge";
  const POLL_MS = 10000;

  let host = null;
  let button = null;
  let badge = null;
  let panel = null;
  let list = null;
  let summary = null;
  let toast = null;
  let toastTimer = 0;
  let rejectToast = null;
  let rejectToastTimer = 0;
  let notifications = [];
  let username = "anonymous";
  let pollTimer = 0;
  let newestAutomationId = 0;
  let newestRejectId = 0;
  let currentPromptListId = "";
  let currentFlags = null;
  const flagsByList = new Map();
  const inflightByList = new Map();
  const reviewedSignatureByList = new Map();

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

  function formatTime(value) {
    const date = new Date(value || "");
    if (Number.isNaN(date.getTime())) return String(value || "Unknown time");
    const sameDay = date.toDateString() === new Date().toDateString();
    return date.toLocaleString([], sameDay
      ? { hour: "numeric", minute: "2-digit", second: "2-digit" }
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

  function isInternalRejectNotification(item) {
    return String(item?.details?.source || "").trim().toLowerCase() === "internal-reject";
  }

  function storageKey() {
    return `dls.notification-center.last-seen.v138.${username.toLowerCase()}`;
  }

  function lastSeenId() {
    const value = Number.parseInt(localStorage.getItem(storageKey()) || "0", 10);
    return Number.isFinite(value) ? value : 0;
  }

  function setLastSeenId(value) {
    localStorage.setItem(storageKey(), String(Math.max(0, Number(value || 0))));
  }

  function ensureUi() {
    if (host) return;
    const actions = document.querySelector(".header-quick-actions") || document.querySelector(".header-actions");
    if (!actions) return;

    host = document.createElement("span");
    host.className = "notification-center-host";
    host.innerHTML = `
      <button class="tool-button header-utility-button notification-center-button" id="notificationCenterBtn" type="button" aria-label="Open notifications" aria-expanded="false" title="Notifications">
        <span class="notification-center-bell" aria-hidden="true"></span>
        <span class="notification-center-badge" id="notificationCenterBadge" hidden>0</span>
      </button>`;
    const languageButton = actions.querySelector("#languageToggleBtn");
    if (languageButton) actions.insertBefore(host, languageButton);
    else actions.prepend(host);

    button = host.querySelector("#notificationCenterBtn");
    badge = host.querySelector("#notificationCenterBadge");

    panel = document.createElement("aside");
    panel.className = "notification-center-panel";
    panel.hidden = true;
    panel.innerHTML = `
      <header class="notification-center-header">
        <div class="notification-center-header-copy"><small>System messages</small><strong>Notifications</strong></div>
        <button class="notification-center-close" type="button" aria-label="Close notifications">×</button>
      </header>
      <div class="notification-center-toolbar"><span id="notificationCenterSummary">Checking notifications...</span></div>
      <div class="notification-center-list" id="notificationCenterList"></div>
      <footer class="notification-center-footer">Import notifications open their exact saved run. New and updated delivery-list lines remain personal to your account until you mark them reviewed.</footer>`;
    document.body.append(panel);
    list = panel.querySelector("#notificationCenterList");
    summary = panel.querySelector("#notificationCenterSummary");

    toast = document.createElement("aside");
    toast.className = "automation-update-toast";
    toast.hidden = true;
    toast.setAttribute("role", "status");
    toast.setAttribute("aria-live", "polite");
    document.body.append(toast);

    rejectToast = document.createElement("aside");
    rejectToast.className = "internal-reject-notification-toast";
    rejectToast.hidden = true;
    rejectToast.setAttribute("role", "alert");
    rejectToast.setAttribute("aria-live", "assertive");
    document.body.append(rejectToast);

    button.addEventListener("click", (event) => {
      event.stopPropagation();
      if (panel.hidden) openPanel();
      else closePanel();
    });
    panel.querySelector(".notification-center-close")?.addEventListener("click", closePanel);
    panel.addEventListener("click", (event) => event.stopPropagation());
    document.addEventListener("click", closePanel);
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closePanel();
        closeUpdatePrompt();
      }
    });
    window.addEventListener("resize", positionPanel);
  }

  function positionPanel() {
    if (!panel || panel.hidden || !button) return;
    const rect = button.getBoundingClientRect();
    const width = Math.min(410, window.innerWidth - 24);
    panel.style.left = `${Math.max(12, Math.min(window.innerWidth - width - 12, rect.right - width))}px`;
    panel.style.top = `${Math.min(window.innerHeight - 80, rect.bottom + 9)}px`;
  }

  function openPanel() {
    if (!panel) return;
    panel.hidden = false;
    button?.classList.add("is-open");
    button?.setAttribute("aria-expanded", "true");
    positionPanel();
    renderNotifications();
    refreshNotifications({ markRead: true });
  }

  function closePanel() {
    if (!panel) return;
    panel.hidden = true;
    button?.classList.remove("is-open");
    button?.setAttribute("aria-expanded", "false");
  }

  function renderBadge() {
    if (!badge) return;
    const unread = notifications.filter((item) => Number(item.id || 0) > lastSeenId()).length;
    badge.hidden = unread === 0;
    badge.textContent = unread > 99 ? "99+" : String(unread);
    button?.setAttribute("aria-label", unread ? `Open notifications, ${unread} unread` : "Open notifications");
  }

  function renderNotifications() {
    renderBadge();
    if (!list || !summary) return;
    const unread = notifications.filter((item) => Number(item.id || 0) > lastSeenId()).length;
    summary.textContent = unread ? `${unread} unread notification${unread === 1 ? "" : "s"}` : "You're caught up";
    if (!notifications.length) {
      list.innerHTML = `<div class="notification-center-empty"><div><strong>No notifications yet</strong><span>Automation results and system messages will appear here.</span></div></div>`;
      return;
    }
    list.innerHTML = notifications.map((item) => {
      const id = Number(item.id || 0);
      const type = String(item.type || "notice").toLowerCase();
      const unreadClass = id > lastSeenId() ? " is-unread" : "";
      const action = isAutomationNotification(item)
        ? "Open saved import run"
        : isInternalRejectNotification(item)
          ? "Open reject tracking"
          : "View details";
      return `
        <button class="notification-center-item${unreadClass}" type="button" data-notification-id="${id}" data-type="${escapeHtml(type)}">
          <span class="notification-center-type-icon" aria-hidden="true">${typeSymbol(type)}</span>
          <span class="notification-center-item-copy">
            <strong>${escapeHtml(item.title || "Notification")}</strong>
            <span>${escapeHtml(item.message || "")}</span>
            <small>${escapeHtml(formatTime(item.createdAt))} · ${escapeHtml(action)}</small>
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

  async function markNotification(notificationId) {
    if (!notificationId) return;
    setLastSeenId(Math.max(lastSeenId(), notificationId));
    renderNotifications();
    try {
      await jsonFetch(ACK_ENDPOINT, { method: "POST", body: JSON.stringify({ notificationId }) });
    } catch (error) {
      console.warn("Notification acknowledgement failed", error);
    }
  }

  async function markAllRead() {
    const maxId = notifications.reduce((value, item) => Math.max(value, Number(item.id || 0)), 0);
    setLastSeenId(maxId);
    renderNotifications();
    try {
      await jsonFetch(READ_ALL_ENDPOINT, { method: "POST", body: "{}" });
    } catch (error) {
      console.warn("Notification read-all failed", error);
    }
  }

  async function openNotification(item) {
    await markNotification(Number(item.id || 0));
    if (isInternalRejectNotification(item)) {
      closePanel();
      dismissRejectToast();
      document.dispatchEvent(new CustomEvent("dls:open-internal-reject-notification", {
        detail: { notification: item },
      }));
      return;
    }
    if (!isAutomationNotification(item)) return;
    closePanel();
    dismissToast();
    document.dispatchEvent(new CustomEvent("dls:open-delivery-list-management-import", {
      detail: { notification: item },
    }));
  }

  function dismissToast() {
    clearTimeout(toastTimer);
    if (!toast) return;
    toast.classList.remove("is-visible");
    window.setTimeout(() => {
      if (!toast.classList.contains("is-visible")) toast.hidden = true;
    }, 180);
  }

  function dismissRejectToast() {
    clearTimeout(rejectToastTimer);
    if (!rejectToast) return;
    rejectToast.classList.remove("is-visible");
    window.setTimeout(() => {
      if (!rejectToast.classList.contains("is-visible")) rejectToast.hidden = true;
    }, 180);
  }

  function showInternalRejectToast(item) {
    if (!rejectToast || !item) return;
    const details = item.details || {};
    rejectToast.innerHTML = `
      <span class="internal-reject-toast-icon" aria-hidden="true">IR</span>
      <span class="internal-reject-toast-copy">
        <small>Internal reject reported</small>
        <strong>${escapeHtml(item.title || "Internal reject logged")}</strong>
        <span>${escapeHtml(item.message || "A piece was rejected and restarted.")}</span>
        <b>Order ${escapeHtml(details.order || "-")} · Item ${escapeHtml(details.item || "-")} · ${escapeHtml(details.location || "Location not specified")}</b>
      </span>
      <button class="internal-reject-toast-open" type="button">View</button>
      <button class="internal-reject-toast-ack" type="button">Acknowledge</button>`;
    rejectToast.querySelector(".internal-reject-toast-open")?.addEventListener("click", () => openNotification(item));
    rejectToast.querySelector(".internal-reject-toast-ack")?.addEventListener("click", async () => {
      await markNotification(Number(item.id || 0));
      dismissRejectToast();
    });
    rejectToast.hidden = false;
    requestAnimationFrame(() => rejectToast.classList.add("is-visible"));
    clearTimeout(rejectToastTimer);
    rejectToastTimer = window.setTimeout(dismissRejectToast, 30000);
    window.playAppSound?.("notification", { force: true });
  }

  function showAutomationToast(item) {
    if (!toast || !item) return;
    const type = String(item.type || "notice").toLowerCase();
    toast.dataset.type = type;
    toast.innerHTML = `
      <span class="automation-update-toast-icon" aria-hidden="true">${typeSymbol(type)}</span>
      <span class="automation-update-toast-copy">
        <strong>${escapeHtml(item.title || "Delivery lists updated")}</strong>
        <span>${escapeHtml(item.message || "The delivery-list catalog has been checked.")}</span>
      </span>
      <button class="automation-update-toast-view" type="button">View run</button>
      <button class="automation-update-toast-close" type="button" aria-label="Dismiss notification">×</button>`;
    toast.querySelector(".automation-update-toast-view")?.addEventListener("click", () => openNotification(item));
    toast.querySelector(".automation-update-toast-close")?.addEventListener("click", dismissToast);
    toast.hidden = false;
    requestAnimationFrame(() => toast.classList.add("is-visible"));
    clearTimeout(toastTimer);
    toastTimer = window.setTimeout(dismissToast, 20000);
  }

  async function refreshNotifications(options = {}) {
    try {
      const payload = await jsonFetch(HISTORY_ENDPOINT);
      notifications = Array.isArray(payload.notifications) ? payload.notifications : [];
      const newest = notifications.filter(isAutomationNotification).reduce(
        (candidate, item) => Number(item.id || 0) > Number(candidate?.id || 0) ? item : candidate,
        null,
      );
      const nextId = Number(newest?.id || 0);
      if (nextId > newestAutomationId) {
        const shouldToast = newestAutomationId > 0;
        newestAutomationId = nextId;
        if (shouldToast) {
          // A completed import can create new per-user line notices without changing
          // the active list selection. Drop cached flags before the catalog refresh so
          // the next render cannot reuse a stale "no updates" response.
          flagsByList.clear();
          reviewedSignatureByList.clear();
          showAutomationToast(newest);
          document.dispatchEvent(new CustomEvent("dls:delivery-list-import-history-changed", { detail: { notification: newest } }));
          const activeListId = String(state?.activeListId || document.getElementById("deliveryStageSelect")?.value || "").trim();
          if (activeListId) {
            window.setTimeout(() => loadFlags(activeListId, { force: true, prompt: false }).catch(() => {}), 900);
          }
        }
      }
      const newestReject = notifications.filter(isInternalRejectNotification).reduce(
        (candidate, item) => Number(item.id || 0) > Number(candidate?.id || 0) ? item : candidate,
        null,
      );
      const nextRejectId = Number(newestReject?.id || 0);
      if (nextRejectId > newestRejectId) {
        const shouldToastReject = newestRejectId > 0;
        newestRejectId = nextRejectId;
        if (shouldToastReject && nextRejectId > lastSeenId()) showInternalRejectToast(newestReject);
      }
      if (options.markRead) await markAllRead();
      else renderNotifications();
    } catch (error) {
      if (summary) summary.textContent = "Notifications unavailable";
    } finally {
      clearTimeout(pollTimer);
      pollTimer = window.setTimeout(refreshNotifications, POLL_MS);
    }
  }

  function normalizeFlags(payload, listId) {
    const items = Array.isArray(payload?.items) ? payload.items : [];
    const noticeIds = Array.isArray(payload?.noticeIds)
      ? payload.noticeIds.map(Number).filter((id) => id > 0).sort((a, b) => a - b)
      : items.flatMap((item) => item.userUpdateNoticeIds || []).map(Number).filter((id) => id > 0).sort((a, b) => a - b);
    return {
      listId,
      pendingLineCount: Number(payload?.pendingLineCount || items.filter((item) => item.hasUnseenUpdate).length || 0),
      newLineCount: Number(payload?.newLineCount || items.filter((item) => item.userUpdateState === "new").length || 0),
      updatedLineCount: Number(payload?.updatedLineCount || items.filter((item) => item.userUpdateState === "updated").length || 0),
      noticeIds: [...new Set(noticeIds)],
      signature: [...new Set(noticeIds)].join(","),
      items,
    };
  }

  function applyFlagsToCurrentList(flags, options = {}) {
    if (typeof state !== "object" || String(state.activeListId || "") !== String(flags?.listId || "")) return;
    const byId = new Map((flags.items || []).map((item) => [String(item.lineItemId || item.id || ""), item]));
    state.items = (state.items || []).map((item) => {
      const current = byId.get(String(item.id || "")) || {};
      return {
        ...item,
        manualOnly: Boolean(current.manualOnly),
        manualSource: String(current.manualSource || ""),
        internalRejectCount: Number(current.internalRejectCount || 0),
        lastRejectReason: String(current.lastRejectReason || ""),
        lastRejectLocation: String(current.lastRejectLocation || ""),
        lastRejectedAt: String(current.lastRejectedAt || ""),
        hasUnseenUpdate: Boolean(current.hasUnseenUpdate),
        userUpdateState: String(current.userUpdateState || ""),
        userUpdateNoticeIds: Array.isArray(current.userUpdateNoticeIds) ? current.userUpdateNoticeIds.slice() : [],
      };
    });
    currentFlags = flags;
    if (options.render !== false && typeof renderScanPage === "function") renderScanPage();
    renderReviewControl(flags);
    document.dispatchEvent(new CustomEvent("dls:line-update-flags-applied", { detail: flags }));
  }

  async function loadFlags(listId, options = {}) {
    const cleanListId = String(listId || "").trim();
    if (!cleanListId) return normalizeFlags({}, "");
    if (!options.force && flagsByList.has(cleanListId)) {
      const cached = flagsByList.get(cleanListId);
      applyFlagsToCurrentList(cached, options);
      if (options.prompt) maybeShowUpdatePrompt(cached);
      return cached;
    }
    if (inflightByList.has(cleanListId)) return inflightByList.get(cleanListId);
    const request = jsonFetch(`${FLAGS_ENDPOINT}?listId=${encodeURIComponent(cleanListId)}`)
      .then((payload) => {
        const flags = normalizeFlags(payload, cleanListId);
        flagsByList.set(cleanListId, flags);
        applyFlagsToCurrentList(flags, options);
        if (options.prompt) maybeShowUpdatePrompt(flags);
        return flags;
      })
      .finally(() => inflightByList.delete(cleanListId));
    inflightByList.set(cleanListId, request);
    return request;
  }

  function reviewControlElements() {
    return {
      control: document.getElementById("scanUpdateReviewControl"),
      summary: document.getElementById("scanUpdateReviewSummary"),
      review: document.getElementById("scanUpdateReviewBtn"),
      acknowledge: document.getElementById("scanUpdateMarkReviewedBtn"),
    };
  }

  function renderReviewControl(flags = currentFlags) {
    const elements = reviewControlElements();
    const activeListId = String(state?.activeListId || "");
    if (!elements.control) return;
    if (!flags || !flags.pendingLineCount || String(flags.listId) !== activeListId) {
      elements.control.hidden = true;
      return;
    }

    const updatedFilterActive = Boolean(state?.activeFilters?.has?.("updated"));
    const reviewComplete = reviewedSignatureByList.get(flags.listId) === flags.signature && Boolean(flags.signature);
    const parts = [];
    if (flags.newLineCount) parts.push(`${flags.newLineCount} new`);
    if (flags.updatedLineCount) parts.push(`${flags.updatedLineCount} updated`);
    if (elements.summary) {
      elements.summary.textContent = `${parts.join(" · ") || `${flags.pendingLineCount} changed`} line${flags.pendingLineCount === 1 ? "" : "s"} for your account`;
    }
    if (elements.review) {
      elements.review.textContent = updatedFilterActive ? "Updates Shown" : "Review Updates";
      elements.review.disabled = updatedFilterActive;
      elements.review.onclick = () => reviewUpdates(flags);
    }
    if (elements.acknowledge) {
      elements.acknowledge.hidden = !updatedFilterActive;
      elements.acknowledge.disabled = !updatedFilterActive || !reviewComplete;
      elements.acknowledge.textContent = "Mark Reviewed";
      elements.acknowledge.title = reviewComplete
        ? "Clear the displayed New/Updated status for your account"
        : "Use Review Updates first so the changed lines are displayed";
      elements.acknowledge.onclick = () => acknowledgeUpdates(flags);
    }
    elements.control.classList.toggle("is-reviewing", updatedFilterActive);
    elements.control.hidden = false;
  }

  function closeUpdatePrompt() {
    document.getElementById("lineUpdateReviewPromptV135")?.remove();
    currentPromptListId = "";
  }

  function maybeShowUpdatePrompt(flags) {
    if (!flags?.pendingLineCount || !flags.signature) return;
    if (currentPromptListId === flags.listId && document.getElementById("lineUpdateReviewPromptV135")) return;
    closeUpdatePrompt();
    currentPromptListId = flags.listId;
    const shell = document.createElement("div");
    shell.id = "lineUpdateReviewPromptV135";
    shell.className = "line-update-review-prompt-shell";
    shell.innerHTML = `
      <section class="line-update-review-prompt" role="dialog" aria-modal="false" aria-labelledby="lineUpdatePromptTitle">
        <button class="line-update-review-close" type="button" aria-label="Close">×</button>
        <span class="line-update-review-icon" aria-hidden="true">!</span>
        <div>
          <small>Delivery list updated</small>
          <h2 id="lineUpdatePromptTitle">${flags.pendingLineCount} changed line${flags.pendingLineCount === 1 ? "" : "s"} need review</h2>
          <p>${flags.newLineCount ? `${flags.newLineCount} new` : ""}${flags.newLineCount && flags.updatedLineCount ? " · " : ""}${flags.updatedLineCount ? `${flags.updatedLineCount} updated` : ""}. Review them now, then use Mark Reviewed beside Filters.</p>
        </div>
        <button class="line-update-review-primary" type="button">Review now</button>
      </section>`;
    document.body.append(shell);
    shell.querySelector(".line-update-review-close")?.addEventListener("click", closeUpdatePrompt);
    shell.querySelector(".line-update-review-primary")?.addEventListener("click", () => {
      closeUpdatePrompt();
      reviewUpdates(flags);
    });
  }

  function reviewUpdates(flags = currentFlags) {
    if (!flags?.signature) return;
    if (typeof state === "object") {
      state.activeFilters?.add?.("updated");
      state.pageIndex = 1;
    }
    reviewedSignatureByList.set(flags.listId, flags.signature);
    if (typeof renderScanPage === "function") renderScanPage();
    renderReviewControl(flags);
    document.getElementById("listPanel")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function acknowledgeUpdates(flags = currentFlags) {
    if (!flags?.listId || !flags?.signature) return;
    if (reviewedSignatureByList.get(flags.listId) !== flags.signature) {
      if (typeof showFloatingNotice === "function") showFloatingNotice("Review the updated lines before marking them reviewed.", "notice");
      return;
    }
    const buttonElement = document.getElementById("scanUpdateMarkReviewedBtn");
    if (buttonElement) {
      buttonElement.disabled = true;
      buttonElement.textContent = "Saving...";
    }
    try {
      await jsonFetch(UPDATE_ACK_ENDPOINT, {
        method: "POST",
        body: JSON.stringify({ listId: flags.listId, noticeIds: flags.noticeIds }),
      });
      flagsByList.delete(flags.listId);
      reviewedSignatureByList.delete(flags.listId);
      const refreshed = await loadFlags(flags.listId, { force: true, prompt: false });
      if (refreshed.pendingLineCount > 0) {
        throw new Error("New updates arrived while you were reviewing. Review the latest changes before clearing them.");
      }
      if (typeof state === "object") {
        state.activeFilters?.delete?.("updated");
        state.pageIndex = 1;
      }
      if (typeof renderScanPage === "function") renderScanPage();
      if (typeof showSaveConfirmation === "function") showSaveConfirmation("The new and updated status is cleared for your account on this list.");
      renderReviewControl(refreshed);
      document.dispatchEvent(new CustomEvent("dls:user-line-updates-reviewed", { detail: { listId: flags.listId } }));
    } catch (error) {
      if (buttonElement) {
        buttonElement.disabled = false;
        buttonElement.textContent = "Try again";
      }
      if (typeof showFloatingNotice === "function") showFloatingNotice(error.message, "error");
    }
  }

  async function initialize() {
    document.getElementById("userLineUpdateBannerV135")?.remove();
    ensureUi();
    if (!host) {
      window.setTimeout(initialize, 500);
      return;
    }
    try {
      const session = await jsonFetch(SESSION_ENDPOINT);
      if (!session.authenticated) {
        host.hidden = true;
        window.setTimeout(initialize, 3000);
        return;
      }
      username = String(session.user?.username || session.user?.displayName || "user");
      host.hidden = false;
      await refreshNotifications();
      const listId = String(document.getElementById("deliveryStageSelect")?.value || "");
      if (listId) loadFlags(listId, { force: true, prompt: false }).catch(() => {});
    } catch {
      host.hidden = true;
      window.setTimeout(initialize, 3000);
    }
  }

  window.DLSLineUpdates = {
    applyPayload: (payload, listId, options = {}) => {
      const flags = normalizeFlags(payload, String(listId || ""));
      flagsByList.set(flags.listId, flags);
      applyFlagsToCurrentList(flags, options);
      if (options.prompt) maybeShowUpdatePrompt(flags);
      return flags;
    },
    loadAndApply: loadFlags,
    refresh: (options = {}) => loadFlags(String(state?.activeListId || ""), { force: true, ...options }),
    review: reviewUpdates,
    acknowledge: acknowledgeUpdates,
    getCurrent: () => currentFlags,
    getCached: (listId) => flagsByList.get(String(listId || "")) || null,
    clearCache: (listId = "") => listId ? flagsByList.delete(String(listId)) : flagsByList.clear(),
  };

  document.addEventListener("dls:scan-filters-changed", () => renderReviewControl(currentFlags));
  document.addEventListener("dls:user-line-updates-reviewed", () => renderReviewControl(currentFlags));

  document.addEventListener("dls:delivery-list-catalog-synced", () => {
    flagsByList.clear();
    const listId = String(state?.activeListId || "");
    if (listId) loadFlags(listId, { force: true, prompt: false }).catch(() => {});
  });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      refreshNotifications();
      const listId = String(state?.activeListId || "");
      if (listId) loadFlags(listId, { force: true, prompt: false }).catch(() => {});
    }
  });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize);
  else initialize();
})();
