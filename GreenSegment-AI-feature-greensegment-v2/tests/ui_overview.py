"""Overview browser acceptance checks against real CSV-backed APIs and real Leaflet.

Run with a Vite dev/preview server: python tests/ui_overview.py
OVERVIEW_UI_URL defaults to http://127.0.0.1:5173. Gemini is never called.
The init script captures Leaflet instances in the browser without production hooks.
"""
import os
import json
from pathlib import Path
import re
import sys
import unittest
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from playwright.sync_api import expect, sync_playwright

from api import advisor_service as advisor, data_service as data
from api.main import app

OVERVIEW_MARKER_COLORS = {0: "#2563eb", 1: "#d97706", 2: "#047857"}

CAPTURE_LEAFLET = """(() => {
  window.__leafletMaps = [];
  let leaflet;
  Object.defineProperty(window, 'L', {
    configurable: true,
    get() { return leaflet; },
    set(value) {
      leaflet = value;
      value.Map.addInitHook(function() { window.__leafletMaps.push(this); });
    },
  });
  window.testMap = () => window.__leafletMaps.filter(map => map._loaded && map._container?.isConnected).at(-1);
  window.testMarkers = () => Object.values(window.testMap()._layers).filter(layer => layer instanceof window.L.CircleMarker);
})()"""


class OverviewBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path=os.environ.get("MARKET_CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            headless=True,
        )
        cls.api = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        cls.api.close()
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={"width": 1440, "height": 1000}, reduced_motion="reduce")
        self.context.add_init_script(CAPTURE_LEAFLET)
        self.page = self.context.new_page()
        self.page_errors = []
        self.page.on("pageerror", lambda error: self.page_errors.append(str(error)))
        self.calls = []
        self.hold_country = None
        self.held_map = None
        self.map_error = False
        self.page.route("**/api/**", self.api_route)
        self.page.route("https://*.tile.openstreetmap.org/**", lambda route: route.abort())
        self.page.goto(os.environ.get("OVERVIEW_UI_URL", "http://127.0.0.1:5173"))
        expect(self.page.locator(".ce-profile-id")).to_have_text("Cụm 0")
        self.wait_data()

    def tearDown(self):
        self.context.close()
        self.assertEqual(self.page_errors, [])
        self.assertFalse(any(method != "GET" for method, _ in self.calls), "Filtering must never invoke Gemini")

    def api_route(self, route):
        request = route.request
        url = urlsplit(request.url)
        self.calls.append((request.method, url.path))
        self.assertEqual(request.method, "GET", "Unexpected AI request")
        if self.map_error and url.path == "/api/cities/map":
            route.fulfill(status=503, json={"detail": "Không tải được điểm đô thị trong kiểm thử."})
            return
        with patch.object(advisor, "_advisor", side_effect=AssertionError("No Gemini during Overview filtering")):
            response = self.api.get(url.path + ("?" + url.query if url.query else ""))
        if url.path == "/api/cities/map" and self.hold_country and parse_qs(url.query).get("country") == [self.hold_country]:
            self.held_map = (route, response)
            return
        route.fulfill(status=response.status_code, content_type="application/json", body=response.content)

    def wait_data(self):
        expect(self.page.locator(".stat-grid")).to_have_attribute("aria-busy", "false")
        cluster = self.page.locator("#cluster-filter").input_value()
        expected = data.map_points(self.page.locator("#country-filter").input_value() or None,
                                   int(cluster) if cluster else None,
                                   self.page.locator("#sector-filter").input_value() or None)["shown"]
        if expected:
            expect(self.page.locator(".overview-map-caption")).to_contain_text("Đang hiển thị")
        else:
            expect(self.page.locator(".map-panel .empty-state")).to_be_visible()
        self.page.wait_for_function("window.testMap() && !window.testMap()._animatingZoom")
        self.page.wait_for_function("count => testMarkers().length === count", arg=expected)

    def markers(self):
        return self.page.evaluate("testMarkers().map(marker => ({...marker.getLatLng(), color: marker.options.fillColor}))")

    def camera(self):
        return self.page.evaluate("({lat: testMap().getCenter().lat, lng: testMap().getCenter().lng, zoom: testMap().getZoom()})")

    def assert_camera(self, expected):
        actual = self.camera()
        self.assertEqual(actual["zoom"], expected["zoom"])
        self.assertAlmostEqual(actual["lat"], expected["lat"], places=6)
        self.assertAlmostEqual(actual["lng"], expected["lng"], places=6)

    def assert_selection(self, map_id, analysis_id):
        expect(self.page.locator("#cluster-filter")).to_have_value(str(map_id))
        group = self.page.get_by_role("group", name="Lọc cụm trên bản đồ")
        expect(group.locator('button[aria-pressed="true"]')).to_have_count(1)
        active = group.get_by_role("button", name="Tất cả 3 cụm", exact=True) if map_id == "" else group.get_by_role("button", name=re.compile(f"^Cụm {map_id} –"))
        expect(active).to_have_attribute("aria-pressed", "true")
        expect(self.page.locator(".ce-profile-id")).to_have_text(f"Cụm {analysis_id}")
        expect(self.page.get_by_role("button", name=f"Chọn Cụm {analysis_id}", exact=True)).to_have_attribute("aria-pressed", "true")
        expect(self.page.locator('.ce-chart-tick[aria-pressed="true"]')).to_have_count(1)
        expect(self.page.locator(".ce-chart-tick")).to_have_count(3)

    def choose_country(self, country):
        self.page.locator("#country-filter").select_option(country)
        self.wait_data()

    def choose_cluster(self, cluster):
        self.page.locator("#cluster-filter").select_option(str(cluster))
        self.wait_data()

    def assert_country_points_visible(self, country, cluster=None):
        expected = data.map_points(country, cluster, None, 5000)
        self.assertEqual(len(self.markers()), expected["shown"])
        self.assertGreater(self.camera()["zoom"], 2)
        self.assertLessEqual(self.camera()["zoom"], 8)
        positions = self.page.evaluate("""() => {
          const map = testMap(), size = map.getSize();
          const overlay = document.querySelector('.map-cluster-overlay').getBoundingClientRect();
          const canvas = map.getContainer().getBoundingClientRect();
          return testMarkers().map(marker => {
            const point = map.latLngToContainerPoint(marker.getLatLng());
            const x = canvas.left + point.x, y = canvas.top + point.y;
            return {visible: point.x >= 10 && point.y >= 10 && point.x <= size.x - 10 && point.y <= size.y - 10,
                    covered: x >= overlay.left && x <= overlay.right && y >= overlay.top && y <= overlay.bottom};
          });
        }""")
        self.assertTrue(all(point["visible"] and not point["covered"] for point in positions), f"Hidden {country} markers")

    def test_initial_selection_dropdown_cards_and_chart_stay_synchronized(self):
        self.assert_selection("", 0)
        self.assertEqual(len(self.markers()), 5000)
        expect(self.page.locator(".overview-map-caption")).to_contain_text("lấy mẫu tối đa 5.000")
        self.assertEqual(self.camera()["zoom"], 2)
        for cluster in range(3):
            self.choose_cluster(cluster)
            self.assert_selection(cluster, cluster)
            colors = {marker["color"] for marker in self.markers()}
            self.assertEqual(colors, {OVERVIEW_MARKER_COLORS[cluster]})
        self.page.get_by_role("group", name="Lọc cụm trên bản đồ").get_by_role("button", name=re.compile("^Cụm 1 –")).click()
        self.wait_data()
        self.assert_selection(1, 1)
        self.page.get_by_role("button", name="Chọn Cụm 0", exact=True).focus()
        self.page.keyboard.press("Enter")
        self.wait_data()
        self.assert_selection(0, 0)
        # A colored segment is also clickable, not just its axis label.
        self.page.locator(".recharts-bar-rectangle").nth(2).click()
        self.wait_data()
        self.assert_selection(2, 2)
        self.page.get_by_role("button", name="Tất cả 3 cụm", exact=True).click()
        self.wait_data()
        self.assert_selection("", 2)
        self.assertEqual({marker["color"] for marker in self.markers()}, set(OVERVIEW_MARKER_COLORS.values()))
        self.page.locator("#cluster-filter").select_option("1")
        self.wait_data()
        self.page.locator("#cluster-filter").select_option("")
        self.wait_data()
        self.assert_selection("", 1)

    def test_country_bounds_and_cluster_scope_remain_global(self):
        for country in ("Cuba", "Japan"):
            self.choose_country(country)
            self.assert_country_points_visible(country)
            expect(self.page.locator(".map-panel .panel-heading")).to_contain_text(f"{country} · Tất cả 3 cụm")
        for cluster in (0, 2):
            self.choose_cluster(cluster)
            self.assert_country_points_visible("Japan", cluster)
            expected_cluster = next(c for c in data.all_clusters() if c["cluster_id"] == cluster)
            expect(self.page.locator(".ce-profile-kpis dd").first).to_have_text(f"{expected_cluster['city_count']:,}".replace(",", "."))
            expect(self.page.locator(".stat-card strong").first).to_have_text(str(len(data.filter_cities(country="Japan", cluster_id=cluster))))
        self.choose_country("Singapore")
        self.assert_country_points_visible("Singapore", 2)
        self.assertEqual(len(self.markers()), 1)

    def test_marker_appearance_zoom_and_canvas_lifecycle(self):
        self.assertEqual({marker["color"] for marker in self.markers()}, set(OVERVIEW_MARKER_COLORS.values()))
        self.assertTrue(self.page.evaluate("testMarkers().every(marker => marker.options.color === '#ffffff' && marker.options.weight === 1.2 && marker.options.fillOpacity === 1 && marker.getRadius() === 3.5)"))
        legend = self.page.locator(".map-legend i").evaluate_all("nodes => nodes.map(node => node.style.backgroundColor)")
        self.assertEqual(legend, ["rgb(37, 99, 235)", "rgb(217, 119, 6)", "rgb(4, 120, 87)"])
        timings = self.page.evaluate("""async () => {
          const map = testMap(), markers = testMarkers();
          const elapsed = [];
          for (const zoom of [3, 5, 8, 2]) {
            const start = performance.now();
            map.setZoom(zoom, {animate: false});
            await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
            elapsed.push({zoom, ms: performance.now() - start});
          }
          return {elapsed, sameMarkers: markers.every((marker, index) => marker === testMarkers()[index])};
        }""")
        self.assertTrue(timings["sameMarkers"], "Zoom must reuse all 5,000 markers")
        self.assertTrue(all(timing["ms"] < 1500 for timing in timings["elapsed"]), timings)
        directory = Path(__file__).resolve().parents[1] / ".local"
        (directory / "overview-marker-timings.json").write_text(json.dumps(timings, indent=2), encoding="utf-8")
        for cluster in (2, 0, 1, "", 2):
            self.choose_cluster(cluster)
            self.assertLessEqual(self.page.evaluate("Object.values(testMap()._layers).filter(layer => layer instanceof L.Canvas).length"), 1)
            self.page.evaluate("() => { testMap().setZoom(8, {animate: false}); }")
            self.assertTrue(self.page.evaluate("testMarkers().every(marker => marker.getRadius() === 4.5)"))

    def test_marker_pointer_hover_restore_tooltip_and_city_click(self):
        self.choose_country("Singapore")
        self.choose_cluster(2)
        point = data.map_points("Singapore", 2, None)["points"][0]
        self.page.locator(".worldmap").scroll_into_view_if_needed()
        position = self.page.evaluate("""() => {
          const map = testMap(), rect = map.getContainer().getBoundingClientRect();
          const point = map.latLngToContainerPoint(testMarkers()[0].getLatLng());
          return {x: rect.left + point.x, y: rect.top + point.y};
        }""")
        self.page.mouse.move(position["x"], position["y"])
        expect(self.page.locator(".leaflet-tooltip")).to_contain_text(point["city_name"])
        expect(self.page.locator(".leaflet-tooltip")).to_contain_text("Singapore · Cụm 2")
        self.assertTrue(self.page.evaluate("testMarkers()[0].getRadius() === 6 && testMarkers()[0].options.weight === 1.8"))
        self.page.mouse.move(0, 0)
        expect(self.page.locator(".leaflet-tooltip")).not_to_be_visible()
        self.assertTrue(self.page.evaluate("testMarkers()[0].getRadius() === 4.5 && testMarkers()[0].options.weight === 1.2"))
        self.page.mouse.click(position["x"], position["y"])
        expect(self.page.locator(".city-hero h2")).to_have_text(point["city_name"])
        expect(self.page.locator(".city-hero")).to_contain_text(f"Mã đô thị {point['city_id']}")

    def test_marker_touch_selection(self):
        self.context.close()
        self.context = self.browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True,
                                                has_touch=True, device_scale_factor=2, reduced_motion="reduce")
        self.context.add_init_script(CAPTURE_LEAFLET)
        self.page = self.context.new_page()
        self.page.on("pageerror", lambda error: self.page_errors.append(str(error)))
        self.page.route("**/api/**", self.api_route)
        self.page.route("https://*.tile.openstreetmap.org/**", lambda route: route.abort())
        self.page.goto(os.environ.get("OVERVIEW_UI_URL", "http://127.0.0.1:5173"))
        self.wait_data()
        self.choose_country("Singapore")
        self.choose_cluster(2)
        point = data.map_points("Singapore", 2, None)["points"][0]
        self.page.locator(".worldmap").scroll_into_view_if_needed()
        position = self.page.evaluate("""() => {
          const map = testMap(), rect = map.getContainer().getBoundingClientRect();
          const point = map.latLngToContainerPoint(testMarkers()[0].getLatLng());
          return {x: rect.left + point.x, y: rect.top + point.y};
        }""")
        self.page.touchscreen.tap(position["x"], position["y"])
        expect(self.page.locator(".city-hero h2")).to_have_text(point["city_name"])

    def test_manual_global_camera_refresh_and_reset(self):
        self.page.evaluate("() => { testMap().setView([38, 105], 5, {animate: false}); }")
        manual = self.camera()
        for cluster in (0, 1, 2, ""):
            self.choose_cluster(cluster)
            self.assert_camera(manual)
        self.page.locator("#sector-filter").select_option("industry")
        self.wait_data()
        self.assert_camera(manual)
        self.page.get_by_role("button", name="Tải lại bản đồ").click()
        self.wait_data()
        self.assert_camera(manual)
        self.choose_country("Cuba")
        self.page.locator("#sector-filter").select_option("")
        self.wait_data()
        self.choose_cluster(1)
        self.page.get_by_role("button", name="Đặt lại bộ lọc").click()
        self.wait_data()
        self.assert_selection("", 1)
        expect(self.page.locator("#country-filter")).to_have_value("")
        expect(self.page.locator("#sector-filter")).to_have_value("")
        self.assert_camera({"lat": 19, "lng": 10, "zoom": 2})
        # Reset must also work while all filters are already empty after manual panning.
        self.page.evaluate("() => { testMap().setView([0, -80], 4, {animate: false}); }")
        self.page.get_by_role("button", name="Đặt lại bộ lọc").click()
        self.wait_data()
        self.assert_camera({"lat": 19, "lng": 10, "zoom": 2})

    def test_empty_results_do_not_move_map_and_controls_still_work(self):
        self.choose_country("Cuba")
        self.choose_cluster(0)
        before = self.camera()
        self.page.locator("#sector-filter").select_option("agriculture")
        self.wait_data()
        expect(self.page.locator(".map-panel .empty-state")).to_be_visible()
        self.assertEqual(len(self.markers()), 0)
        self.assert_camera(before)
        expect(self.page.locator(".stat-card strong").first).to_have_text("0")
        self.page.get_by_role("button", name="Đặt lại bộ lọc").click()
        self.wait_data()
        self.assertEqual(len(self.markers()), 5000)
        self.assert_selection("", 0)

    def test_navigation_preserves_selection_and_refits_country(self):
        self.choose_country("Japan")
        self.choose_cluster(2)
        self.page.get_by_role("button", name="Tất cả 3 cụm", exact=True).click()
        self.wait_data()
        self.page.get_by_role("button", name="Giới thiệu", exact=True).click()
        self.page.get_by_role("button", name="Tổng quan", exact=True).click()
        self.wait_data()
        self.assert_selection("", 2)
        self.assert_country_points_visible("Japan")
        self.page.get_by_role("button", name="Tra cứu đô thị", exact=True).click()
        expect(self.page.locator(".city-explorer")).to_be_visible()
        self.page.get_by_role("button", name="Tổng quan", exact=True).click()
        self.wait_data()
        self.assert_selection("", 2)

    def test_stale_country_response_cannot_replace_new_country(self):
        self.hold_country = "Cuba"
        self.page.locator("#country-filter").select_option("Cuba")
        expect(self.page.locator(".overview-map-caption")).to_contain_text("Đang tải điểm đô thị")
        self.choose_country("Japan")
        self.assertIsNotNone(self.held_map)
        before = self.camera()
        route, response = self.held_map
        route.fulfill(status=response.status_code, content_type="application/json", body=response.content)
        self.assert_country_points_visible("Japan")
        self.assert_camera(before)

    def test_map_error_can_be_retried_without_losing_profile(self):
        self.choose_cluster(1)
        self.map_error = True
        self.page.locator("#country-filter").select_option("Cuba")
        expect(self.page.get_by_role("alert")).to_contain_text("Không tải được điểm đô thị")
        expect(self.page.locator(".overview-map-caption")).to_contain_text("Hãy thử tải lại")
        self.assert_selection(1, 1)
        self.map_error = False
        self.page.get_by_role("button", name="Tải lại bản đồ").click()
        self.wait_data()
        self.assert_country_points_visible("Cuba", 1)

    def test_responsive_controls_and_map_padding(self):
        for width in (1440, 768, 390, 320):
            self.page.set_viewport_size({"width": width, "height": 1000})
            self.choose_country("Cuba")
            self.assert_country_points_visible("Cuba")
            self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"Overflow at {width}px")
            buttons = self.page.locator(".map-cluster-overlay button")
            expect(buttons).to_have_count(4)
            for button in buttons.all():
                self.assertGreaterEqual(button.bounding_box()["height"], 44)
            self.assertTrue(self.page.locator(".ce-exploration-grid").evaluate("el => el.scrollWidth <= el.clientWidth"))
            self.page.locator(".map-panel").scroll_into_view_if_needed()
            directory = Path(__file__).resolve().parents[1] / ".local" / "overview-screenshots"
            directory.mkdir(parents=True, exist_ok=True)
            self.page.screenshot(path=str(directory / f"overview-{width}.png"), full_page=True)
            self.choose_country("")


if __name__ == "__main__":
    unittest.main(verbosity=2)
