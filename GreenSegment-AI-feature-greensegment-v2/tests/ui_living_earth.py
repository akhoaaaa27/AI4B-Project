"""Independent Living Earth browser checks. No backend/Gemini or external assets.

Start Vite/preview; run python tests/ui_living_earth.py.
LIVING_EARTH_UI_URL defaults to http://127.0.0.1:5173.
Uses software WebGL in headless Chrome; this is not a real-device GPU benchmark.
"""
import json
import math
import os
from pathlib import Path
import time
import unittest

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOTS = ROOT / ".local" / "living-earth"
URL = os.environ.get("LIVING_EARTH_UI_URL", "http://127.0.0.1:5173").rstrip("/")


class LivingEarthBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path=os.environ.get("MARKET_CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            headless=True, args=["--enable-webgl", "--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
        )
        SCREENSHOTS.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 1050}, reduced_motion="reduce")
        self.page = self.context.new_page()
        self.errors, self.api_calls = [], []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.route("**/api/**", lambda route: (self.api_calls.append(route.request.url), route.abort()))

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])
        self.assertEqual(self.api_calls, [], "The prototype must not request backend APIs")

    def open_scene(self):
        self.page.goto(URL + "/living-earth-preview.html")
        expect(self.page.locator(".le-webgl")).to_have_attribute("data-scene-status", "ready", timeout=60000)
        expect(self.page.locator(".le-webgl")).to_have_attribute("data-hand-loaded", "true")

    def state(self):
        return self.page.locator(".le-webgl").evaluate("node => ({...node.dataset})")

    def test_earth_and_real_hand_load_without_backend(self):
        self.open_scene()
        state = self.state()
        self.assertEqual(state["rotationPeriod"], "60")
        self.assertGreater(float(state["earthBottom"]) - float(state["handTop"]), .25)
        self.assertLessEqual(int(state["drawCalls"]), 6)
        expect(self.page.locator("canvas")).to_have_count(1)
        expect(self.page.locator(".le-sample-cards article")).to_have_count(3)
        self.page.get_by_text("Tài nguyên & ghi chú", exact=True).click()
        expect(self.page.locator(".le-footer details")).to_have_attribute("open", "")
        expect(self.page.locator(".le-footer")).to_contain_text("CC BY 4.0")
        expect(self.page.locator(".le-footer")).to_contain_text("MIT")

    def test_rotation_speed_pause_and_particles(self):
        self.page.emulate_media(reduced_motion="no-preference")
        self.open_scene()
        sample = self.page.locator(".le-webgl").evaluate("node => ({angle: Number(node.dataset.earthAngle), now: performance.now()})")
        self.page.wait_for_function("angle => Number(document.querySelector('.le-webgl').dataset.earthAngle) - angle > .35", arg=sample["angle"], timeout=20000)
        end = self.page.locator(".le-webgl").evaluate("node => ({angle: Number(node.dataset.earthAngle), now: performance.now()})")
        speed = (end["angle"] - sample["angle"]) / ((end["now"] - sample["now"]) / 1000)
        self.assertAlmostEqual(speed, math.tau / 60, delta=.025)
        (SCREENSHOTS / "rotation-measurement.json").write_text(json.dumps({"radians_per_second": speed, "estimated_revolution_seconds": math.tau / speed, "renderer": "Chrome software WebGL"}, indent=2), encoding="utf-8")
        self.page.get_by_role("button", name="Tạm dừng", exact=True).click()
        expect(self.page.locator(".le-webgl")).to_have_attribute("data-motion", "paused")
        before = self.state()
        time.sleep(.4)
        self.assertEqual(self.state()["earthAngle"], before["earthAngle"])
        self.page.get_by_role("button", name="Hạt sáng", exact=True).click()
        expect(self.page.get_by_role("button", name="Hạt sáng", exact=True)).to_have_attribute("aria-pressed", "false")
        self.assertEqual(int(self.state()["drawCalls"]), int(before["drawCalls"]) - 1)
        self.page.get_by_role("button", name="Tiếp tục", exact=True).click()
        expect(self.page.locator(".le-webgl")).to_have_attribute("data-motion", "running")

    def test_reduced_motion_is_static_and_reacts_to_preference_changes(self):
        self.open_scene()
        expect(self.page.locator(".le-webgl")).to_have_attribute("data-motion", "reduced")
        expect(self.page.get_by_role("button", name="Cảnh tĩnh", exact=True)).to_be_disabled()
        before = self.state()["earthAngle"]
        time.sleep(.4)
        self.assertEqual(self.state()["earthAngle"], before)
        self.page.emulate_media(reduced_motion="no-preference")
        expect(self.page.locator(".le-webgl")).to_have_attribute("data-motion", "running")
        self.page.wait_for_function("angle => document.querySelector('.le-webgl').dataset.earthAngle !== angle", arg=before)
        self.page.emulate_media(reduced_motion="reduce")
        expect(self.page.locator(".le-webgl")).to_have_attribute("data-motion", "reduced")

    def test_webgl_unavailable_uses_local_static_fallback(self):
        self.page.add_init_script("""(() => {
          const original = HTMLCanvasElement.prototype.getContext;
          HTMLCanvasElement.prototype.getContext = function(type, ...args) {
            return type.startsWith('webgl') ? null : original.call(this, type, ...args);
          };
        })()""")
        self.page.goto(URL + "/living-earth-preview.html")
        expect(self.page.get_by_role("status")).to_contain_text("Ảnh tĩnh")
        expect(self.page.locator(".le-poster")).to_be_visible()
        self.page.wait_for_function("document.querySelector('.le-poster').naturalWidth > 0")
        expect(self.page.get_by_role("heading", level=1)).to_be_visible()
        self.page.screenshot(path=str(SCREENSHOTS / "fallback-no-webgl.png"), full_page=True)

    def test_missing_hand_asset_falls_back_without_crashing(self):
        self.page.route("**/living-earth/hand-left.glb", lambda route: route.fulfill(status=404, body="Missing test asset"))
        self.page.goto(URL + "/living-earth-preview.html")
        expect(self.page.get_by_role("status")).to_contain_text("Ảnh tĩnh", timeout=30000)
        self.page.wait_for_function("document.querySelector('.le-poster').naturalWidth > 0")
        expect(self.page.get_by_role("link", name="Về giao diện hiện tại", exact=True)).to_be_visible()

    def test_context_loss_and_restoration(self):
        self.open_scene()
        self.page.evaluate("""() => {
          const context = document.querySelector('canvas').getContext('webgl2');
          window.testContextLoss = context.getExtension('WEBGL_lose_context');
          window.testContextLoss.loseContext();
        }""")
        expect(self.page.get_by_role("status")).to_contain_text("Ảnh tĩnh")
        expect(self.page.locator(".le-poster")).to_be_visible()
        self.page.evaluate("testContextLoss.restoreContext()")
        expect(self.page.locator(".le-webgl")).to_have_attribute("data-scene-status", "ready", timeout=30000)
        expect(self.page.locator(".le-poster")).to_have_count(0)

    def test_offscreen_and_hidden_visibility_events_stop_rotation(self):
        self.page.emulate_media(reduced_motion="no-preference")
        self.page.set_viewport_size({"width": 1440, "height": 300})
        self.open_scene()
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        expect(self.page.locator(".le-webgl")).to_have_attribute("data-motion", "suspended")
        angle = self.state()["earthAngle"]
        time.sleep(.35)
        self.assertEqual(self.state()["earthAngle"], angle)
        self.page.evaluate("window.scrollTo(0, 0)")
        expect(self.page.locator(".le-webgl")).to_have_attribute("data-motion", "running")
        # Exercise the browser visibility handler deterministically in headless Chrome.
        self.page.evaluate("""() => {
          Object.defineProperty(document, 'visibilityState', {configurable: true, get: () => window.testVisibility || 'visible'});
          window.testVisibility = 'hidden'; document.dispatchEvent(new Event('visibilitychange'));
        }""")
        expect(self.page.locator(".le-webgl")).to_have_attribute("data-motion", "suspended")
        angle = self.state()["earthAngle"]
        time.sleep(.35)
        self.assertEqual(self.state()["earthAngle"], angle)
        self.page.evaluate("() => { window.testVisibility = 'visible'; document.dispatchEvent(new Event('visibilitychange')); }")
        expect(self.page.locator(".le-webgl")).to_have_attribute("data-motion", "running")

    def test_responsive_layout_and_mobile_quality(self):
        for width in (1440, 1024, 768, 390, 320):
            self.page.set_viewport_size({"width": width, "height": 1050})
            self.open_scene()
            self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Overflow at {width}px")
            self.assertEqual(self.state()["quality"], "mobile" if width <= 600 else "desktop")
            self.assertLessEqual(float(self.state()["pixelRatio"]), 1.25 if width <= 600 else 1.75)
            self.assertTrue(self.page.evaluate("""() => {
              const text = document.querySelector('.le-intro').getBoundingClientRect();
              const visual = document.querySelector('.le-webgl').getBoundingClientRect();
              return text.right <= visual.left || text.bottom <= visual.top || visual.right <= text.left;
            }"""), f"Text overlaps the scene at {width}px")
            self.page.screenshot(path=str(SCREENSHOTS / f"preview-{width}.png"), full_page=True)

    def test_existing_homepage_keeps_its_theme_and_skips_3d_downloads(self):
        self.page.unroute("**/api/**")
        self.page.route("**/api/**", lambda route: route.fulfill(status=503, json={"detail": "Backend not started for isolated preview test"}))
        requests = []
        self.page.on("request", lambda request: requests.append(request.url))
        self.page.goto(URL + "/")
        expect(self.page.get_by_role("heading", name="GreenSegment Artificial Intelligence", exact=True)).to_be_visible()
        self.assertFalse(self.page.locator("body").evaluate("node => node.classList.contains('living-earth-preview')"))
        self.assertEqual(self.page.evaluate("getComputedStyle(document.documentElement).backgroundColor"), "rgb(10, 27, 32)")
        self.assertFalse(any("/living-earth/" in request or "/scene-" in request or "GLTFLoader" in request for request in requests))


if __name__ == "__main__":
    unittest.main(verbosity=2)
