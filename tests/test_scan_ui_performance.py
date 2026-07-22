import pathlib
import re
import unittest
import wave


ROOT = pathlib.Path(__file__).resolve().parents[1]


def source(name):
    return (ROOT / name).read_text(encoding="utf-8")


def between(text, start, end):
    start_index = text.index(start)
    end_index = text.index(end, start_index)
    return text[start_index:end_index]


class ScanUiPerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = source("app.js")
        cls.html = source("index.html")
        cls.css = source("styles.css")
        cls.store = source("delivery_store.py")

    def test_manual_line_save_does_not_reload_catalog_or_modal(self):
        body = between(
            self.app,
            "async function saveManualLineItem",
            "async function deleteManualLineItem",
        )
        self.assertNotIn("loadDeliveryLists", body)
        self.assertNotIn("runManualEditModalSearch", body)
        self.assertIn('row.classList.add("is-saving")', body)
        self.assertIn('row.classList.add("is-saved")', body)

    def test_sound_playback_is_unlocked_immediate_and_print_silent(self):
        body = between(self.app, "function playAppSound(", "function soundTestControlsHtml")
        enabled = between(
            self.app,
            "const APP_SOUND_ENABLED_KINDS",
            "const appSoundRuntime",
        )
        self.assertIn("await loadAppSoundBuffer(normalizedKind)", body)
        self.assertNotIn("schedulePattern();", body)
        self.assertIn("playHtmlAppSound(normalizedKind, delay)", body)
        for restored_action in ("login", "logout", "save", "email_sent", "undo", "redo", "notification"):
            self.assertIn(f'"{restored_action}"', enabled)
        self.assertNotIn('"print_ready"', enabled)
        self.assertIn('document.addEventListener("pointerdown", () => void unlockAppSounds()', self.app)
        self.assertIn('document.addEventListener("keydown", () => void unlockAppSounds()', self.app)
        self.assertIn('"collapse_open"', enabled)
        self.assertIn('"collapse_close"', enabled)

    def test_new_browser_sound_defaults_to_audible_and_has_diagnostics(self):
        runtime = between(self.app, "const appSoundRuntime", "const els")
        self.assertIn("savedValue === null", runtime)
        self.assertIn("return 100", runtime)
        self.assertIn("async function testAppSoundCue", self.app)
        self.assertIn('data-scan-sound-test="scan_success"', self.html)
        self.assertIn("data-app-sound-status", self.html)

    def test_enabled_sound_assets_are_present_and_valid_wav_files(self):
        files_block = between(self.app, "const APP_SOUND_FILES", "const APP_SOUND_ALIASES")
        enabled_block = between(self.app, "const APP_SOUND_ENABLED_KINDS", "const appSoundRuntime")
        sound_files = dict(re.findall(r'([a-z_]+): "([^"]+\.wav)"', files_block))
        enabled = re.findall(r'"([a-z_]+)"', enabled_block)

        self.assertNotIn("print_ready", enabled)
        for kind in enabled:
            path = ROOT / sound_files[kind]
            self.assertTrue(path.is_file(), f"Missing sound file for {kind}: {path}")
            with wave.open(str(path), "rb") as wav_file:
                self.assertGreater(wav_file.getnframes(), 0)
                self.assertGreater(wav_file.getframerate(), 0)

    def test_custom_selects_do_not_poll_the_document(self):
        body = between(self.app, "function initCustomSelectSystem", "function canonicalBarcode")
        self.assertNotIn("setInterval", body)
        self.assertIn("MutationObserver", body)

    def test_scan_page_renders_only_the_active_viewport_layout(self):
        body = between(self.app, "function renderScanPage", "function scheduleScanRender")
        self.assertIn("if (mobileViewport) renderMobileCards()", body)
        self.assertIn("else renderTable()", body)

    def test_compact_filter_drawer_and_active_chips_are_present(self):
        self.assertEqual(self.html.count('id="scanFilterDrawer"'), 1)
        self.assertEqual(self.html.count('id="scanActiveFilterChips"'), 1)
        self.assertIn('data-clear-scan-filters', self.html)
        self.assertIn(".scan-filter-drawer-panel", self.css)
        self.assertIn(".scan-active-filter-chips", self.css)
        self.assertIn(".scan-filter-drawer {\n  z-index: 20;", self.css)

    def test_manual_editor_uses_collapsed_twenty_row_batches_and_predictive_search(self):
        editor = between(self.app, "function manualEditResultsHtml", "async function saveManualLineItem")
        self.assertIn("visibleCount = 20", editor)
        self.assertIn('<details class="manual-edit-card"', editor)
        self.assertIn("data-manual-edit-load-more", editor)
        self.assertIn("Load 20 more", editor)
        self.assertIn('event.target.closest("#manualEditModalSearch")', self.app)
        self.assertIn("manualEditSearchTimer", self.app)
        self.assertIn("li.job LIKE ?", self.store)

    def test_timed_scan_outcomes_cover_backend_and_local_scans(self):
        self.assertIn("function showStageScanConfirmation", self.app)
        self.assertGreaterEqual(self.app.count("showStageScanConfirmation("), 7)
        self.assertIn('id: "stageScanConfirmationShell"', self.app)
        self.assertIn("data-scan-result-rack", self.app)
        self.assertIn(".scan-result-confirmation.is-error", self.css)
        self.assertIn(".scan-result-confirmation.is-notice", self.css)

    def test_all_scans_staging_view_supports_safe_rack_edits(self):
        modal = between(self.app, "function allScansRackControl", "function renderMeta")
        self.assertIn("Order ${escapeHtml(item.order)} / Item ${escapeHtml(item.item)}", modal)
        self.assertIn("Job Nr. ${escapeHtml(item.job", modal)
        self.assertIn("data-scan-event-rack", modal)
        self.assertIn("item.outboundScanned", modal)
        self.assertIn("rackIsLockedForLineAssignment", modal)

    def test_modal_lock_uses_real_visibility_and_bay_truck_restarts_after_paint(self):
        lock = between(self.app, "function updateModalScrollLock", "async function fetchJson")
        self.assertIn("getClientRects().length > 0", lock)
        self.assertIn("requestAnimationFrame(() => updateModalScrollLock())", self.app)
        self.assertIn("function restartBayTruckAnimation", self.app)
        self.assertIn("bayRouteFlowSignature", self.app)

    def test_frontend_cache_key_was_bumped(self):
        self.assertIn('styles.css?v=20260721-v102', self.html)
        self.assertIn('app.js?v=20260721-v102', self.html)


if __name__ == "__main__":
    unittest.main()
