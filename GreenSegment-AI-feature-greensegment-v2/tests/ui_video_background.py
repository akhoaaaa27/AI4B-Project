"""Video layout/lifecycle acceptance checks using real CSV-backed APIs.

Start Vite/preview, then run python tests/ui_video_background.py.
VIDEO_UI_URL defaults to http://127.0.0.1:5173. No Gemini calls.
"""
import os
from pathlib import Path
import sys
import time
import unittest
from urllib.parse import urlsplit
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from playwright.sync_api import expect, sync_playwright
from api import advisor_service as advisor
from api.main import app

ROOT = Path(__file__).resolve().parents[1]
URL = os.environ.get("VIDEO_UI_URL", "http://127.0.0.1:5173").rstrip("/")
SCREENSHOTS = ROOT / ".local" / "earth-video"
VIDEO_PATH = "/media/earth_smooth_loop_preview_2x_upscaled.mp4"


class VideoBackgroundBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path=os.environ.get("MARKET_CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe"), headless=True)
        cls.api = TestClient(app)
        SCREENSHOTS.mkdir(parents=True, exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.api.close()
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="no-preference")
        self.page = self.context.new_page()
        self.errors, self.requests = [], []
        self.page.on("pageerror", lambda error: self.errors.append(str(error)))
        self.page.on("request", lambda request: self.requests.append(request.url))
        self.page.route("**/api/**", self.api_route)
        self.page.route("https://*.tile.openstreetmap.org/**", lambda route: route.abort())
        self.page.route("https://tiles.stadiamaps.com/**", lambda route: route.abort())

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.errors, [])

    def api_route(self, route):
        request = route.request
        self.assertEqual(request.method, "GET", "Background must never trigger Gemini")
        url = urlsplit(request.url)
        with patch.object(advisor, "_advisor", side_effect=AssertionError("No Gemini during background checks")):
            response = self.api.get(url.path + ("?" + url.query if url.query else ""))
        route.fulfill(status=response.status_code, content_type="application/json", body=response.content)

    def open_app(self, *, video=True):
        self.page.goto(URL + "/#/overview")
        expect(self.page.locator(".ce-profile-id")).to_have_text("Cụm 0")
        if video:
            self.page.wait_for_function("document.querySelector('.video-background video')?.readyState >= 2 && !document.querySelector('.video-background video').paused")
        self.page.wait_for_function("document.querySelector('.video-background-poster').naturalWidth > 0")

    def assert_fullscreen(self):
        geometry = self.page.locator(".video-background").evaluate("""node => {
          const rect = node.getBoundingClientRect(), style = getComputedStyle(node);
          return {x:rect.x,y:rect.y,width:rect.width,height:rect.height,position:style.position,
                  z:style.zIndex,pointer:style.pointerEvents,viewportWidth:innerWidth,clientWidth:document.documentElement.clientWidth,viewportHeight:innerHeight};
        }""")
        self.assertEqual((geometry["x"], geometry["y"]), (0, 0))
        self.assertGreaterEqual(geometry["width"], geometry["clientWidth"])
        self.assertLessEqual(geometry["width"], geometry["viewportWidth"])
        self.assertEqual(geometry["height"], geometry["viewportHeight"])
        self.assertEqual(geometry["position"], "fixed")
        self.assertEqual(geometry["pointer"], "none")
        self.assertLess(int(geometry["z"]), 0)

    def test_shared_video_persists_across_all_pages_and_scrolling(self):
        self.open_app()
        self.page.evaluate("""() => {
          window.testVideo = document.querySelector('.video-background video');
          window.testLoadStarts = 0;
          testVideo.addEventListener('loadstart', () => window.testLoadStarts++);
          testVideo.currentTime = 2;
        }""")
        properties = self.page.locator(".video-background video").evaluate("v => ({autoplay:v.autoplay, muted:v.muted, loop:v.loop, inline:v.playsInline, preload:v.preload, controls:v.controls, width:v.videoWidth, height:v.videoHeight, duration:v.duration})")
        self.assertTrue(all(properties[key] for key in ("autoplay", "muted", "loop", "inline")))
        self.assertFalse(properties["controls"])
        self.assertEqual((properties["width"], properties["height"]), (1472, 828))
        self.assertAlmostEqual(properties["duration"], 14, places=1)
        self.assertEqual(properties["preload"], "auto")
        self.assertEqual(urlsplit(self.page.locator('.video-background video').evaluate("video => video.currentSrc")).path, VIDEO_PATH)
        self.assertFalse(any(urlsplit(url).path in {'/media/earth.mp4', '/media/earth_smooth_loop_preview.mp4'} for url in self.requests))
        for label, selector in (("Tra cứu đô thị", ".city-explorer"), ("Khám phá thị trường", ".market-explorer"),
                                ("Giới thiệu", ".about-hero"), ("Trang chủ", ".home-page"), ("Tổng quan", ".overview-page")):
            self.page.get_by_role("navigation", name="Điều hướng chính").get_by_role("link", name=label, exact=True).click()
            expect(self.page.locator(selector)).to_be_visible()
            expect(self.page.locator(".video-background video")).to_have_count(1)
            self.assertTrue(self.page.evaluate("document.querySelector('.video-background video') === testVideo"))
            self.assertEqual(self.page.evaluate("testLoadStarts"), 0)
            self.assert_fullscreen()
        before = self.page.evaluate("testVideo.currentTime")
        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        self.assert_fullscreen()
        self.page.wait_for_function("before => testVideo.currentTime > before + .1 || (before > testVideo.duration - 1 && testVideo.currentTime < 1)", arg=before)
        self.assertFalse(self.page.evaluate("testVideo.paused"))
        self.page.screenshot(path=str(SCREENSHOTS / "scrolling-overview.png"))

    def test_filter_rerenders_do_not_reload_video(self):
        self.open_app()
        self.page.evaluate("window.testVideo = document.querySelector('.video-background video')")
        self.page.locator("#country-filter").select_option("Japan")
        self.page.locator("#cluster-filter").select_option("2")
        expect(self.page.locator(".ce-profile-id")).to_have_text("Cụm 2")
        self.page.get_by_role("button", name="Đặt lại bộ lọc").click()
        expect(self.page.locator("#country-filter")).to_have_value("")
        self.assertTrue(self.page.evaluate("document.querySelector('.video-background video') === testVideo"))
        self.assertFalse(self.page.evaluate("testVideo.paused"))

    def test_reduced_motion_uses_poster_without_video_download_and_updates_live(self):
        self.page.emulate_media(reduced_motion="reduce")
        self.open_app(video=False)
        expect(self.page.locator(".video-background video")).to_have_count(0)
        expect(self.page.locator(".video-background-poster")).to_be_visible()
        self.assertFalse(any(urlsplit(url).path == VIDEO_PATH for url in self.requests))
        self.assert_fullscreen()
        self.page.emulate_media(reduced_motion="no-preference")
        self.page.wait_for_function("document.querySelector('.video-background video')?.readyState >= 2 && !document.querySelector('.video-background video').paused")
        self.page.evaluate("window.previousVideo = document.querySelector('.video-background video')")
        self.page.emulate_media(reduced_motion="reduce")
        expect(self.page.locator(".video-background video")).to_have_count(0)
        self.assertTrue(self.page.evaluate("previousVideo.paused"))
        self.page.get_by_role("navigation", name="Điều hướng chính").get_by_role("link", name="Giới thiệu", exact=True).click()
        expect(self.page.locator(".about-hero")).to_be_visible()

    def test_failed_video_uses_static_poster_and_app_still_works(self):
        self.page.route(f"**{VIDEO_PATH}", lambda route: route.fulfill(status=404, body="Missing video for test"))
        self.open_app(video=False)
        expect(self.page.locator(".video-background video")).to_have_count(0)
        expect(self.page.locator(".video-background-poster")).to_be_visible()
        self.page.get_by_role("navigation", name="Điều hướng chính").get_by_role("link", name="Tra cứu đô thị", exact=True).click()
        expect(self.page.locator(".city-explorer")).to_be_visible()
        self.page.screenshot(path=str(SCREENSHOTS / "failed-video-fallback.png"))

    def test_autoplay_rejection_does_not_crash_or_add_controls(self):
        self.page.add_init_script("HTMLMediaElement.prototype.play = function() { return Promise.reject(new DOMException('Blocked for test', 'NotAllowedError')); };")
        self.open_app(video=False)
        expect(self.page.locator(".video-background video")).to_have_count(0)
        expect(self.page.locator(".video-background-poster")).to_be_visible()
        expect(self.page.get_by_role("heading", name="Bức tranh phát thải đô thị toàn cầu", exact=True)).to_be_visible()

    def test_native_loop_reuses_the_same_element(self):
        self.open_app()
        self.page.evaluate("""() => {
          window.testVideo = document.querySelector('.video-background video');
          testVideo.currentTime = testVideo.duration - .15;
        }""")
        self.page.wait_for_function("testVideo.currentTime < 1.5 && !testVideo.paused", timeout=10000)
        self.assertTrue(self.page.evaluate("document.querySelector('.video-background video') === testVideo && testVideo.loop"))
        expect(self.page.locator(".video-background video")).to_have_count(1)

    def test_responsive_cover_without_horizontal_overflow(self):
        self.open_app()
        for width, height in ((1440,900), (1024,768), (768,1024), (390,844), (320,680)):
            self.page.set_viewport_size({"width": width, "height": height})
            # Responsive chart containers apply ResizeObserver measurements after the viewport changes.
            self.page.wait_for_function("document.documentElement.scrollWidth <= innerWidth", timeout=5000)
            self.assert_fullscreen()
            expect(self.page.locator(".video-background video")).to_have_css("object-fit", "cover")
            self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Overflow at {width}px")
            self.page.screenshot(path=str(SCREENSHOTS / f"background-{width}.png"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
